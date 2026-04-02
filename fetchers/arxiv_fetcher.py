import re
import tempfile
from pathlib import Path

import arxiv
import pymupdf
import requests

from .base import BaseFetcher, FetchResult


class ArxivFetcher(BaseFetcher):
    def fetch(self, url: str) -> FetchResult:
        arxiv_id = self._extract_id(url)
        search = arxiv.Search(id_list=[arxiv_id])
        paper = next(arxiv.Client().results(search))

        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = self._download_pdf(arxiv_id, tmp_dir)
            text = self._extract_text(pdf_path)

        return FetchResult(
            title=paper.title,
            content=text,
            source_type="paper",
            url=url,
        )

    def _extract_id(self, url: str) -> str:
        # Handles: arxiv.org/abs/2301.07041, arxiv.org/pdf/2301.07041
        match = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", url)
        if match:
            return match.group(0)
        # Handles old-style IDs like hep-ph/9901000
        match = re.search(r"([a-z-]+/\d{7})", url)
        if match:
            return match.group(1)
        raise ValueError(f"Cannot extract arXiv ID from: {url}")

    def _download_pdf(self, arxiv_id: str, tmp_dir: str) -> str:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
        for attempt in range(3):
            try:
                resp = requests.get(pdf_url, timeout=120, stream=True, headers={
                    "User-Agent": "Mozilla/5.0"
                })
                resp.raise_for_status()
                break
            except requests.RequestException:
                if attempt == 2:
                    raise
                import time
                time.sleep(3)
        pdf_path = str(Path(tmp_dir) / f"{arxiv_id.replace('/', '_')}.pdf")
        with open(pdf_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return pdf_path

    def _extract_text(self, pdf_path: str) -> str:
        doc = pymupdf.open(pdf_path)
        pages = []
        for page in doc:
            lines = page.get_text().split("\n")
            filtered = [l for l in lines if not l.strip().isdigit()]
            pages.append("\n".join(filtered))
        doc.close()
        return "\n\n".join(pages)

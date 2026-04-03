import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import pymupdf
import requests

from .base import BaseFetcher, FetchResult


class PdfFetcher(BaseFetcher):
    def fetch(self, url: str) -> FetchResult:
        for attempt in range(3):
            try:
                resp = requests.get(url, timeout=120, headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                })
                resp.raise_for_status()
                break
            except requests.RequestException:
                if attempt == 2:
                    raise
                print(f"  PDF download failed, retrying ({attempt + 1}/3)...")
                time.sleep(3 * (attempt + 1))

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(resp.content)
            pdf_path = f.name

        text = self._extract_text(pdf_path)
        Path(pdf_path).unlink(missing_ok=True)

        title = self._guess_title(text, url)
        return FetchResult(
            title=title,
            content=text,
            source_type="report",
            url=url,
        )

    def fetch_local(self, file_path: str) -> FetchResult:
        text = self._extract_text(file_path)
        title = self._guess_title(text, file_path)
        return FetchResult(
            title=title,
            content=text,
            source_type="report",
            url=file_path,
        )

    def _extract_text(self, pdf_path: str) -> str:
        doc = pymupdf.open(pdf_path)
        pages = []
        for page in doc:
            lines = page.get_text().split("\n")
            # Filter out standalone line numbers (common in review papers)
            filtered = [l for l in lines if not l.strip().isdigit()]
            pages.append("\n".join(filtered))
        doc.close()
        return "\n\n".join(pages)

    def _guess_title(self, text: str, url: str) -> str:
        # Use first non-empty line as title guess
        for line in text.split("\n"):
            line = line.strip()
            if len(line) > 5:
                return line[:200]
        # Fallback to filename from URL
        return Path(urlparse(url).path).stem

"""Save podcast scripts to Notion as sub-pages."""

from datetime import datetime, timezone

import requests


class NotionWriter:
    API_BASE = "https://api.notion.com/v1"

    def __init__(self, token: str, parent_page_id: str):
        self.token = token
        self.parent_page_id = parent_page_id
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }

    def save_scripts(
        self,
        title: str,
        source_url: str,
        source_type: str,
        short_script: str,
        long_script: str,
    ) -> str:
        """Create a Notion sub-page with both scripts. Returns the page URL."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        page_title = f"[{now}] {title}"

        children = self._build_content_blocks(
            source_url, source_type, short_script, long_script
        )

        payload = {
            "parent": {"page_id": self.parent_page_id},
            "properties": {
                "title": {
                    "title": [{"text": {"content": page_title}}]
                }
            },
            "children": children,
        }

        resp = requests.post(
            f"{self.API_BASE}/pages",
            headers=self.headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        page_url = resp.json().get("url", "")
        return page_url

    def _build_content_blocks(
        self,
        source_url: str,
        source_type: str,
        short_script: str,
        long_script: str,
    ) -> list[dict]:
        """Build Notion block children for the page content."""
        blocks = []

        # Metadata section
        blocks.append(self._heading2("信息"))
        blocks.append(self._paragraph(f"来源类型：{source_type}"))
        blocks.append(self._paragraph(f"来源链接：{source_url}"))
        blocks.append(self._divider())

        # Short script
        blocks.append(self._heading2("短稿（500-1000 字）"))
        blocks.extend(self._text_blocks(short_script))
        blocks.append(self._divider())

        # Long script
        blocks.append(self._heading2("长稿（10-12 分钟）"))
        blocks.extend(self._text_blocks(long_script))

        return blocks

    def _heading2(self, text: str) -> dict:
        return {
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": text}}]
            },
        }

    def _paragraph(self, text: str) -> dict:
        return {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": text}}]
            },
        }

    def _divider(self) -> dict:
        return {"object": "block", "type": "divider", "divider": {}}

    def save_batch_comparison(
        self,
        title: str,
        source_url: str,
        variants: list[dict],
    ) -> str:
        """Create a Notion page comparing multiple prompt variants for one paper.

        Args:
            title: Paper title.
            source_url: Source URL.
            variants: List of dicts with keys: name, short, long.

        Returns:
            The Notion page URL.
        """
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        page_title = f"[{now}] {title}"

        blocks = []
        blocks.append(self._heading2("信息"))
        blocks.append(self._paragraph(f"来源链接：{source_url}"))
        blocks.append(self._paragraph(f"Prompt 变体数：{len(variants)}"))
        blocks.append(self._divider())

        for v in variants:
            blocks.append(self._heading1(f"📌 {v['name']}"))
            blocks.append(self._heading2(f"短稿（{v['name']}）"))
            blocks.extend(self._text_blocks(v["short"]))
            blocks.append(self._heading2(f"长稿（{v['name']}）"))
            blocks.extend(self._text_blocks(v["long"]))
            blocks.append(self._divider())

        # Notion API limits: max 100 blocks per request, append rest in batches
        page_id = self._create_page(page_title, blocks[:100])
        for i in range(100, len(blocks), 100):
            self._append_blocks(page_id, blocks[i : i + 100])

        return f"https://www.notion.so/{page_id.replace('-', '')}"

    def _create_page(self, title: str, children: list[dict]) -> str:
        payload = {
            "parent": {"page_id": self.parent_page_id},
            "properties": {
                "title": {
                    "title": [{"text": {"content": title}}]
                }
            },
            "children": children,
        }
        resp = requests.post(
            f"{self.API_BASE}/pages",
            headers=self.headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["id"]

    def _append_blocks(self, page_id: str, children: list[dict]) -> None:
        payload = {"children": children}
        resp = requests.patch(
            f"{self.API_BASE}/blocks/{page_id}/children",
            headers=self.headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()

    def _heading1(self, text: str) -> dict:
        return {
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [{"type": "text", "text": {"content": text}}]
            },
        }

    def _text_blocks(self, text: str) -> list[dict]:
        """Split long text into paragraph blocks (Notion limits rich_text to 2000 chars)."""
        blocks = []
        for paragraph in text.split("\n\n"):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            # Notion API limits each rich_text content to 2000 characters
            for i in range(0, len(paragraph), 2000):
                chunk = paragraph[i : i + 2000]
                blocks.append(self._paragraph(chunk))
        return blocks

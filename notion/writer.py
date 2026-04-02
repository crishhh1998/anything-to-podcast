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

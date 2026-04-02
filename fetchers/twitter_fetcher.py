import json
import subprocess

from .base import BaseFetcher, FetchResult


class TwitterFetcher(BaseFetcher):
    def __init__(self, cookies_path: str = "./cookies.txt"):
        self.cookies_path = cookies_path

    def fetch(self, url: str) -> FetchResult:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--cookies", self.cookies_path, url],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"yt-dlp failed: {result.stderr.strip()}"
            )

        info = json.loads(result.stdout)
        description = info.get("description", "")
        title = info.get("title", description[:100])
        uploader = info.get("uploader", "")

        content = f"Author: {uploader}\n\n{description}"

        return FetchResult(
            title=title,
            content=content,
            source_type="twitter",
            url=url,
        )

import re

import requests

from .base import BaseFetcher, FetchResult


class TwitterFetcher(BaseFetcher):
    def __init__(self, cookies_path: str = "./cookies.txt"):
        self.cookies_path = cookies_path

    def _parse_url(self, url: str) -> tuple[str, str]:
        """Extract username and tweet ID from a Twitter/X URL."""
        m = re.search(r"(?:twitter\.com|x\.com)/(\w+)/status/(\d+)", url)
        if not m:
            raise ValueError(f"Invalid Twitter/X URL: {url}")
        return m.group(1), m.group(2)

    def fetch(self, url: str) -> FetchResult:
        username, tweet_id = self._parse_url(url)
        api_url = f"https://api.fxtwitter.com/{username}/status/{tweet_id}"

        resp = requests.get(api_url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        tweet = data.get("tweet", {})
        author = tweet.get("author", {})
        author_name = author.get("name", "")
        author_handle = author.get("screen_name", username)
        text = tweet.get("text", "")
        title = f"{author_name} (@{author_handle})"

        content = f"Author: {author_name} (@{author_handle})\n\n{text}"

        return FetchResult(
            title=title,
            content=content,
            source_type="twitter",
            url=url,
        )

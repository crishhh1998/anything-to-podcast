import requests

from .base import BaseFetcher, FetchResult


class RedditFetcher(BaseFetcher):
    def fetch(self, url: str) -> FetchResult:
        json_url = url.rstrip("/") + ".json"
        resp = requests.get(
            json_url,
            headers={"User-Agent": "AnythingToPodcast/1.0"},
            params={"raw_json": 1},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        post = data[0]["data"]["children"][0]["data"]
        title = post.get("title", "")
        body = post.get("selftext", "")

        # Collect top-level comments
        comments = []
        for child in data[1]["data"]["children"]:
            if child["kind"] == "t1":
                comment_body = child["data"].get("body", "")
                score = child["data"].get("score", 0)
                comments.append((score, comment_body))

        # Sort by score, take top 20
        comments.sort(key=lambda x: x[0], reverse=True)
        top_comments = [c[1] for c in comments[:20]]

        content_parts = [f"Title: {title}"]
        if body:
            content_parts.append(f"\nPost content:\n{body}")
        if top_comments:
            content_parts.append("\nTop comments:")
            for i, comment in enumerate(top_comments, 1):
                content_parts.append(f"\n[Comment {i}]\n{comment}")

        return FetchResult(
            title=title,
            content="\n".join(content_parts),
            source_type="reddit",
            url=url,
        )

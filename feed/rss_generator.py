import json
import os
from datetime import datetime, timezone
from pathlib import Path

from feedgen.feed import FeedGenerator


EPISODES_DB = "episodes.json"


class RSSGenerator:
    def __init__(self, title: str, description: str, language: str, base_url: str, output_dir: str):
        self.title = title
        self.description = description
        self.language = language
        self.base_url = base_url.rstrip("/")
        self.output_dir = output_dir
        self.db_path = str(Path(output_dir) / EPISODES_DB)

    def add_episode(self, title: str, description: str, audio_path: str, source_url: str) -> None:
        episodes = self._load_episodes()

        filename = Path(audio_path).name
        file_size = os.path.getsize(audio_path)

        episode = {
            "title": title,
            "description": description,
            "filename": filename,
            "file_size": file_size,
            "source_url": source_url,
            "pub_date": datetime.now(timezone.utc).isoformat(),
        }

        episodes.append(episode)
        self._save_episodes(episodes)
        self._generate_feed(episodes)

    def _generate_feed(self, episodes: list[dict]) -> None:
        fg = FeedGenerator()
        fg.load_extension("podcast")

        fg.title(self.title)
        fg.description(self.description)
        fg.language(self.language)
        fg.link(href=self.base_url)

        fg.podcast.itunes_category("Technology")
        fg.podcast.itunes_author(self.title)
        fg.podcast.itunes_explicit("no")

        for ep in reversed(episodes):
            fe = fg.add_entry()
            fe.title(ep["title"])
            fe.description(f'{ep["description"]}\n\nSource: {ep["source_url"]}')
            fe.published(ep["pub_date"])

            audio_url = f'{self.base_url}/episodes/{ep["filename"]}'
            fe.enclosure(audio_url, str(ep["file_size"]), "audio/mpeg")
            fe.guid(audio_url, permalink=True)

        feed_path = str(Path(self.output_dir) / "feed.xml")
        fg.rss_file(feed_path, pretty=True)

    def _load_episodes(self) -> list[dict]:
        if Path(self.db_path).exists():
            with open(self.db_path) as f:
                return json.load(f)
        return []

    def _save_episodes(self, episodes: list[dict]) -> None:
        with open(self.db_path, "w") as f:
            json.dump(episodes, f, ensure_ascii=False, indent=2)

    def list_episodes(self) -> list[dict]:
        return self._load_episodes()

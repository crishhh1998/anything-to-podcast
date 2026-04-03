import json
import os
from datetime import datetime, timezone
from pathlib import Path
from xml.etree.ElementTree import SubElement

from feedgen.feed import FeedGenerator


EPISODES_DB = "episodes.json"
PODCAST_NS = "https://podcastindex.org/namespace/1.0"


class RSSGenerator:
    def __init__(self, title: str, description: str, language: str, base_url: str, output_dir: str, audio_base_url: str = ""):
        self.title = title
        self.description = description
        self.language = language
        self.base_url = base_url.rstrip("/")
        self.audio_base_url = audio_base_url.rstrip("/") if audio_base_url else self.base_url
        self.output_dir = output_dir
        self.db_path = str(Path(output_dir) / EPISODES_DB)

    def add_episode(self, title: str, description: str, source_url: str,
                    audio_filename: str = "", file_size: int = 0,
                    audio_path: str = "", chapters_url: str = "") -> None:
        episodes = self._load_episodes()

        if audio_path and not audio_filename:
            audio_filename = Path(audio_path).name
        if audio_path and not file_size:
            file_size = os.path.getsize(audio_path)
        filename = audio_filename

        episode = {
            "title": title,
            "description": description,
            "filename": filename,
            "file_size": file_size,
            "source_url": source_url,
            "pub_date": datetime.now(timezone.utc).isoformat(),
            "chapters_url": chapters_url,
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
        fg.podcast.itunes_summary(self.description)
        fg.podcast.itunes_owner(name=self.title, email="noreply@example.com")
        fg.image(url=f"{self.base_url}/cover.jpg", title=self.title)

        for ep in reversed(episodes):
            fe = fg.add_entry()
            fe.title(ep["title"])
            fe.description(f'{ep["description"]}\n\nSource: {ep["source_url"]}')
            fe.published(ep["pub_date"])

            audio_url = f'{self.audio_base_url}/episodes/{ep["filename"]}'
            fe.enclosure(audio_url, str(ep["file_size"]), "audio/mpeg")
            fe.guid(audio_url, permalink=True)

        # Generate the base RSS XML
        feed_path = str(Path(self.output_dir) / "feed.xml")
        fg.rss_file(feed_path, pretty=True)

        # Inject podcast:chapters namespace and tags
        self._inject_chapters(feed_path, episodes)

    def _inject_chapters(self, feed_path: str, episodes: list[dict]) -> None:
        """Add <podcast:chapters> tags to the RSS XML.

        feedgen doesn't support the podcast 2.0 namespace natively,
        so we inject it via ElementTree post-processing.
        """
        import xml.etree.ElementTree as ET

        ET.register_namespace("podcast", PODCAST_NS)
        tree = ET.parse(feed_path)
        root = tree.getroot()

        # Add namespace to <rss> tag
        rss = root if root.tag == "rss" else root.find("rss")
        if rss is not None:
            rss.set(f"xmlns:podcast", PODCAST_NS)

        channel = root.find("channel") if root.tag == "rss" else root.find(".//channel")
        if channel is None:
            return

        items = channel.findall("item")
        # episodes are reversed in feed, so reversed episodes match items order
        reversed_episodes = list(reversed(episodes))

        for i, item in enumerate(items):
            if i >= len(reversed_episodes):
                break
            ep = reversed_episodes[i]
            chapters_url = ep.get("chapters_url", "")
            if chapters_url:
                ch_elem = SubElement(item, f"{{{PODCAST_NS}}}chapters")
                ch_elem.set("url", chapters_url)
                ch_elem.set("type", "application/json+chapters")

        tree.write(feed_path, encoding="unicode", xml_declaration=True)

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

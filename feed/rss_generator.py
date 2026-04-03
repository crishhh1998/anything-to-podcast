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
                    audio_path: str = "", chapters_url: str = "",
                    duration_seconds: float = 0.0) -> None:
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
            "duration_seconds": duration_seconds,
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
        fg.podcast.itunes_owner(name=self.title, email="1324982600@qq.com")
        fg.podcast.itunes_type("episodic")
        fg.image(url=f"{self.base_url}/cover.jpg", title=self.title)
        fg.podcast.itunes_image(f"{self.base_url}/cover.jpg")

        for ep in reversed(episodes):
            fe = fg.add_entry()
            fe.title(ep["title"])
            fe.description(ep["description"])
            fe.published(ep["pub_date"])

            audio_url = f'{self.audio_base_url}/episodes/{ep["filename"]}'
            fe.enclosure(audio_url, str(ep["file_size"]), "audio/mpeg")
            fe.guid(audio_url, permalink=True)

            duration_secs = ep.get("duration_seconds", 0)
            if duration_secs:
                total_secs = int(duration_secs)
                h, rem = divmod(total_secs, 3600)
                m, s = divmod(rem, 60)
                duration_str = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
                fe.podcast.itunes_duration(duration_str)

        # Generate the base RSS XML
        feed_path = str(Path(self.output_dir) / "feed.xml")
        fg.rss_file(feed_path, pretty=True)

        # Inject podcast:chapters namespace and tags
        self._inject_chapters(feed_path, episodes)

    def _inject_chapters(self, feed_path: str, episodes: list[dict]) -> None:
        """Add <podcast:chapters> tags and fix namespace prefixes in RSS XML.

        feedgen doesn't support the podcast 2.0 namespace natively,
        so we inject it via ElementTree post-processing.
        Also fixes the iTunes namespace prefix from 'ns0' to 'itunes'.
        """
        import xml.etree.ElementTree as ET

        ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
        ET.register_namespace("itunes", ITUNES_NS)
        ET.register_namespace("podcast", PODCAST_NS)

        tree = ET.parse(feed_path)
        root = tree.getroot()

        channel = root.find("channel") if root.tag == "rss" else root.find(".//channel")
        if channel is None:
            return

        items = channel.findall("item")
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

        # Write with proper namespace declarations
        tree.write(feed_path, encoding="unicode", xml_declaration=True)

        # Ensure exactly one xmlns:podcast declaration on the <rss> tag
        text = Path(feed_path).read_text(encoding="utf-8")
        podcast_decl = f'xmlns:podcast="{PODCAST_NS}"'
        while text.count(podcast_decl) > 1:
            # Remove one duplicate (with optional trailing space)
            text = text.replace(podcast_decl + ' ', '', 1)
        if podcast_decl not in text:
            text = text.replace('<rss ', f'<rss {podcast_decl} ', 1)
        Path(feed_path).write_text(text, encoding="utf-8")

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

#!/usr/bin/env python3
"""Anything to Podcast - Convert URLs to Chinese podcast episodes."""

import argparse
import json
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import yaml

from fetchers import ArxivFetcher, PdfFetcher, RedditFetcher, TwitterFetcher
from fetchers.base import FetchResult
from processor.script_generator import ScriptGenerator, ScriptResult
from tts.edge_tts_engine import EdgeTTSEngine
from feed.rss_generator import RSSGenerator
from storage.oss_uploader import OSSUploader


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path) as f:
        return yaml.safe_load(f)


def detect_source(url: str) -> str:
    """Detect source type from URL or local file path."""
    # Local file
    if Path(url).exists():
        return "local_pdf"

    parsed = urlparse(url)
    host = parsed.hostname or ""

    if "arxiv.org" in host:
        return "arxiv"
    if "reddit.com" in host or "redd.it" in host:
        return "reddit"
    if "twitter.com" in host or "x.com" in host:
        return "twitter"
    if parsed.path.endswith(".pdf"):
        return "pdf"

    # Default to PDF for unknown URLs
    print(f"Warning: cannot detect source type for {url}, treating as PDF")
    return "pdf"


def fetch_content(url: str, source_type: str, config: dict) -> FetchResult:
    """Fetch content based on source type."""
    if source_type == "arxiv":
        return ArxivFetcher().fetch(url)
    elif source_type == "reddit":
        return RedditFetcher().fetch(url)
    elif source_type == "twitter":
        cookies_path = config.get("twitter_cookies", "./cookies.txt")
        return TwitterFetcher(cookies_path=cookies_path).fetch(url)
    elif source_type == "local_pdf":
        return PdfFetcher().fetch_local(url)
    else:
        return PdfFetcher().fetch(url)


def list_prompts(prompts_dir: str = "./prompt_variants") -> list[Path]:
    """List available prompt variant files, sorted by name."""
    return sorted(Path(prompts_dir).glob("*.md"))


def resolve_prompt_file(prompt_arg: str | None, prompts_dir: str = "./prompt_variants") -> str | None:
    """Resolve a prompt argument to a .md file path.

    Accepts: number (e.g. "1", "2"), full name, or file path.
    """
    if not prompt_arg:
        return None
    prompts = list_prompts(prompts_dir)
    # By number
    if prompt_arg.isdigit():
        idx = int(prompt_arg) - 1
        if 0 <= idx < len(prompts):
            return str(prompts[idx])
        print(f"Error: prompt #{prompt_arg} not found, only {len(prompts)} available")
        for i, p in enumerate(prompts, 1):
            print(f"  {i}. {p.stem}")
        sys.exit(1)
    # Direct file path
    path = Path(prompt_arg)
    if path.is_file():
        return str(path)
    # By name match
    for md_file in prompts:
        if prompt_arg in md_file.stem:
            return str(md_file)
    print(f"Error: prompt '{prompt_arg}' not found")
    for i, p in enumerate(prompts, 1):
        print(f"  {i}. {p.stem}")
    sys.exit(1)


def generate_episode(url: str, config: dict, prompt_file: str | None = None,
                     duration: int = 10) -> None:
    """Full pipeline: fetch → script → TTS → RSS."""
    output_dir = config.get("output_dir", "./output")
    episodes_dir = str(Path(output_dir) / "episodes")

    # Step 1: Fetch content
    source_type = detect_source(url)
    print(f"[1/6] Fetching content ({source_type})...")
    result = fetch_content(url, source_type, config)
    print(f"  Title: {result.title}")
    print(f"  Content length: {len(result.content)} chars")

    # Step 2: Generate podcast scripts (short + long) via LLM
    prompt_label = Path(prompt_file).stem if prompt_file else "built-in"
    print(f"[2/6] Generating podcast scripts (prompt: {prompt_label}, duration: {duration}min)...")
    llm_cfg = config["llm"]
    generator = ScriptGenerator(
        base_url=llm_cfg["base_url"],
        api_key=llm_cfg["api_key"],
        model=llm_cfg["model"],
    )
    scripts = generator.generate(result, duration=duration, prompt_file=prompt_file)
    print(f"  Short script: {len(scripts.short)} chars")
    print(f"  Long script: {len(scripts.long)} chars")

    # Step 3: Synthesize audio (from long script)
    print("[3/6] Synthesizing audio (long version)...")
    tts_cfg = config.get("tts", {})
    engine = EdgeTTSEngine(
        voice=tts_cfg.get("voice", "zh-CN-XiaoxiaoNeural"),
        rate=tts_cfg.get("rate", "+0%"),
    )
    tts_result = engine.synthesize(scripts.long, result.title, episodes_dir)
    audio_path = tts_result.audio_path
    print(f"  Audio saved: {audio_path}")
    if tts_result.chapters:
        print(f"  Chapters: {len(tts_result.chapters)}")
        for ch in tts_result.chapters:
            m, s = divmod(int(ch.start_seconds), 60)
            print(f"    {m:02d}:{s:02d} {ch.title}")

    # Step 4: Upload to OSS
    print("[4/6] Uploading to OSS...")
    oss_cfg = config["oss"]
    uploader = OSSUploader(
        access_key_id=oss_cfg["access_key_id"],
        access_key_secret=oss_cfg["access_key_secret"],
        endpoint=oss_cfg["endpoint"],
        bucket=oss_cfg["bucket"],
        base_url=oss_cfg["base_url"],
    )
    filename = Path(audio_path).name
    audio_size = Path(audio_path).stat().st_size
    audio_url = uploader.upload(audio_path, f"episodes/{filename}")
    print(f"  OSS URL: {audio_url}")

    # Upload chapters JSON to OSS if chapters exist
    chapters_url = ""
    if tts_result.chapters:
        chapters_json = {
            "version": "1.2.0",
            "chapters": [
                {"startTime": round(ch.start_seconds, 1), "title": ch.title}
                for ch in tts_result.chapters
            ],
        }
        chapters_filename = Path(filename).stem + "_chapters.json"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(chapters_json, f, ensure_ascii=False)
            chapters_tmp = f.name
        chapters_url = uploader.upload(chapters_tmp, f"episodes/{chapters_filename}")
        Path(chapters_tmp).unlink(missing_ok=True)
        print(f"  Chapters JSON: {chapters_url}")

    # Remove local MP3 from docs/episodes (no longer needed in git)
    Path(audio_path).unlink(missing_ok=True)

    # Step 5: Save scripts to Notion
    print("[5/6] Saving scripts to Notion...")
    notion_cfg = config.get("notion", {})
    if notion_cfg.get("parent_page_id"):
        from notion.writer import NotionWriter
        writer = NotionWriter(
            token=notion_cfg["token"],
            parent_page_id=notion_cfg["parent_page_id"],
        )
        writer.save_scripts(
            title=result.title,
            source_url=url,
            source_type=result.source_type,
            short_script=scripts.short,
            long_script=scripts.long,
        )
        print("  Scripts saved to Notion.")
    else:
        print("  Notion not configured, skipping.")

    # Step 6: Update RSS feed
    print("[6/6] Updating RSS feed...")
    feed_cfg = config.get("feed", {})
    rss = RSSGenerator(
        title=feed_cfg.get("title", "Anything to Podcast"),
        description=feed_cfg.get("description", "自动生成的播客"),
        language=feed_cfg.get("language", "zh-cn"),
        base_url=feed_cfg.get("base_url", "http://localhost:8080"),
        output_dir=output_dir,
        audio_base_url=oss_cfg["base_url"],
    )
    # Build description with chapter timestamps
    desc_parts = [f"Source: {result.source_type} | {result.url}"]
    if tts_result.chapters:
        desc_parts.append("")
        for ch in tts_result.chapters:
            m, s = divmod(int(ch.start_seconds), 60)
            h, m = divmod(m, 60)
            ts = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
            desc_parts.append(f"{ts} {ch.title}")

    rss.add_episode(
        title=result.title,
        description="\n".join(desc_parts),
        audio_filename=filename,
        file_size=audio_size,
        source_url=url,
        chapters_url=chapters_url,
    )
    print("Done! Episode added to feed.")


def list_episodes(config: dict) -> None:
    """List all generated episodes."""
    output_dir = config.get("output_dir", "./output")
    feed_cfg = config.get("feed", {})
    rss = RSSGenerator(
        title=feed_cfg.get("title", ""),
        description="",
        language="",
        base_url="",
        output_dir=output_dir,
    )
    episodes = rss.list_episodes()
    if not episodes:
        print("No episodes yet.")
        return

    for i, ep in enumerate(episodes, 1):
        print(f"{i}. [{ep['pub_date'][:10]}] {ep['title']}")
        print(f"   Source: {ep['source_url']}")
        print(f"   File: {ep['filename']}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Anything to Podcast")
    parser.add_argument("url", nargs="?", help="URL to convert to podcast")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--list", action="store_true", help="List all episodes")
    parser.add_argument("--prompt", metavar="NAME", help="Prompt variant name or .md file path (from prompt_variants/)")
    parser.add_argument("--duration", type=int, default=10, help="Target duration in minutes for long script (default: 10)")
    args = parser.parse_args()

    config = load_config(args.config)

    if args.list:
        list_episodes(config)
    elif args.url:
        prompt_file = resolve_prompt_file(args.prompt)
        generate_episode(args.url, config, prompt_file=prompt_file, duration=args.duration)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

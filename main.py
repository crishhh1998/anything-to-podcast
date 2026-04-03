#!/usr/bin/env python3
"""Anything to Podcast - Convert URLs to Chinese podcast episodes."""

import argparse
import sys
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


def save_to_notion(config: dict, title: str, url: str, source_type: str,
                    short_script: str, long_script: str) -> None:
    """Save scripts to Notion if configured."""
    notion_cfg = config.get("notion", {})
    if not notion_cfg.get("parent_page_id"):
        print("  Notion not configured, skipping.")
        return

    from notion.writer import NotionWriter
    writer = NotionWriter(
        token=notion_cfg["token"],
        parent_page_id=notion_cfg["parent_page_id"],
    )
    writer.save_scripts(
        title=title,
        source_url=url,
        source_type=source_type,
        short_script=short_script,
        long_script=long_script,
    )
    print("  Scripts saved to Notion.")


def test_scripts(url: str, config: dict) -> None:
    """Test mode: fetch → generate scripts → save to Notion. No audio/OSS/RSS."""
    # Step 1: Fetch content
    source_type = detect_source(url)
    print(f"[1/3] Fetching content ({source_type})...")
    result = fetch_content(url, source_type, config)
    print(f"  Title: {result.title}")
    print(f"  Content length: {len(result.content)} chars")

    # Step 2: Generate podcast scripts (short + long) via LLM
    print("[2/3] Generating podcast scripts (short + long)...")
    llm_cfg = config["llm"]
    generator = ScriptGenerator(
        base_url=llm_cfg["base_url"],
        api_key=llm_cfg["api_key"],
        model=llm_cfg["model"],
    )
    scripts = generator.generate(result)
    print(f"  Short script: {len(scripts.short)} chars")
    print(f"  Long script: {len(scripts.long)} chars")

    # Step 3: Save scripts to Notion
    print("[3/3] Saving scripts to Notion...")
    save_to_notion(config, result.title, url, result.source_type,
                   scripts.short, scripts.long)
    print("Done! (test mode — no audio/OSS/RSS)")


def generate_episode(url: str, config: dict) -> None:
    """Full pipeline: fetch → script → TTS → OSS → Notion → RSS."""
    output_dir = config.get("output_dir", "./output")
    episodes_dir = str(Path(output_dir) / "episodes")

    # Step 1: Fetch content
    source_type = detect_source(url)
    print(f"[1/6] Fetching content ({source_type})...")
    result = fetch_content(url, source_type, config)
    print(f"  Title: {result.title}")
    print(f"  Content length: {len(result.content)} chars")

    # Step 2: Generate podcast scripts (short + long) via LLM
    print("[2/6] Generating podcast scripts (short + long)...")
    llm_cfg = config["llm"]
    generator = ScriptGenerator(
        base_url=llm_cfg["base_url"],
        api_key=llm_cfg["api_key"],
        model=llm_cfg["model"],
    )
    scripts = generator.generate(result)
    print(f"  Short script: {len(scripts.short)} chars")
    print(f"  Long script: {len(scripts.long)} chars")

    # Step 3: Synthesize audio (from long script)
    print("[3/6] Synthesizing audio (long version)...")
    tts_cfg = config.get("tts", {})
    engine = EdgeTTSEngine(
        voice=tts_cfg.get("voice", "zh-CN-XiaoxiaoNeural"),
        rate=tts_cfg.get("rate", "+0%"),
    )
    audio_path = engine.synthesize(scripts.long, result.title, episodes_dir)
    print(f"  Audio saved: {audio_path}")

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

    # Remove local MP3 from docs/episodes (no longer needed in git)
    Path(audio_path).unlink(missing_ok=True)

    # Step 5: Save scripts to Notion
    print("[5/6] Saving scripts to Notion...")
    save_to_notion(config, result.title, url, result.source_type,
                   scripts.short, scripts.long)

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
    rss.add_episode(
        title=result.title,
        description=f"Source: {result.source_type} | {result.url}",
        audio_filename=filename,
        file_size=audio_size,
        source_url=url,
    )
    print("Done! Episode added to feed.")


def load_prompt_variants(prompts_dir: str) -> list[tuple[str, str]]:
    """Load prompt variant .md files from a directory.

    Returns:
        List of (variant_name, template_string) sorted by filename.
    """
    prompts_path = Path(prompts_dir)
    if not prompts_path.is_dir():
        print(f"Error: prompt directory not found: {prompts_dir}")
        sys.exit(1)

    variants = []
    for md_file in sorted(prompts_path.glob("*.md")):
        name = md_file.stem
        template = md_file.read_text(encoding="utf-8").strip()
        if "{content}" not in template:
            print(f"Warning: {md_file.name} missing {{content}} placeholder, skipping")
            continue
        variants.append((name, template))

    if not variants:
        print(f"Error: no valid .md prompt files in {prompts_dir}")
        sys.exit(1)

    return variants


def load_urls(urls_file: str) -> list[str]:
    """Load URLs from a text file (one per line, # comments ignored)."""
    urls = []
    for line in Path(urls_file).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)
    if not urls:
        print(f"Error: no URLs found in {urls_file}")
        sys.exit(1)
    return urls


def batch_test(urls_file: str, prompts_dir: str, config: dict) -> None:
    """Batch test: for each paper × each prompt variant, generate short+long scripts and save to Notion."""
    from notion.writer import NotionWriter

    urls = load_urls(urls_file)
    variants = load_prompt_variants(prompts_dir)
    notion_cfg = config.get("notion", {})

    if not notion_cfg.get("parent_page_id"):
        print("Error: notion config required for batch test")
        sys.exit(1)

    writer = NotionWriter(
        token=notion_cfg["token"],
        parent_page_id=notion_cfg["parent_page_id"],
    )

    llm_cfg = config["llm"]
    generator = ScriptGenerator(
        base_url=llm_cfg["base_url"],
        api_key=llm_cfg["api_key"],
        model=llm_cfg["model"],
    )

    total = len(urls)
    print(f"Batch test: {total} papers × {len(variants)} prompt variants")
    print(f"Prompt variants: {', '.join(name for name, _ in variants)}")
    print()

    for i, url in enumerate(urls, 1):
        print(f"=== Paper {i}/{total}: {url} ===")

        # Fetch content once per paper
        source_type = detect_source(url)
        print(f"  [1] Fetching content ({source_type})...")
        result = fetch_content(url, source_type, config)
        print(f"  Title: {result.title}")
        print(f"  Content length: {len(result.content)} chars")

        # Generate scripts for each prompt variant
        variant_results = []
        for j, (name, template) in enumerate(variants, 1):
            print(f"  [2] Generating scripts with prompt: {name} ({j}/{len(variants)})...")
            scripts = generator.generate_with_template(result.content, template)
            print(f"      Short: {len(scripts.short)} chars, Long: {len(scripts.long)} chars")
            variant_results.append({
                "name": name,
                "short": scripts.short,
                "long": scripts.long,
            })

        # Save all variants to one Notion page
        print(f"  [3] Saving to Notion...")
        page_url = writer.save_batch_comparison(
            title=result.title,
            source_url=url,
            variants=variant_results,
        )
        print(f"  Notion page: {page_url}")
        print()

    print(f"Done! {total} papers processed.")


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
    parser.add_argument("--test", action="store_true", help="Test mode: only generate scripts and save to Notion")
    parser.add_argument("--batch", metavar="URLS_FILE", help="Batch test: provide a file with URLs (one per line)")
    parser.add_argument("--prompts", default="./prompt_variants", help="Directory of prompt .md files (for --batch)")
    args = parser.parse_args()

    config = load_config(args.config)

    if args.list:
        list_episodes(config)
    elif args.batch:
        batch_test(args.batch, args.prompts, config)
    elif args.url and args.test:
        test_scripts(args.url, config)
    elif args.url:
        generate_episode(args.url, config)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

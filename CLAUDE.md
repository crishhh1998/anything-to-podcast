# CLAUDE.md

## 使用简体中文进行对话
## 当你觉得我的问题或需求可能描述的不详细，请尝试理解需求，并深度采访我，我确认后，再开始任务。

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Anything to Podcast converts content from various sources (arXiv papers, PDFs, Reddit posts, Twitter/X threads) into Chinese-language podcast episodes. Audio is uploaded to Alibaba Cloud OSS, and an RSS feed is published via GitHub Pages for subscription in Apple Podcasts and similar clients.

## Commands

```bash
# Install dependencies
pip install requests pymupdf arxiv edge-tts openai pyyaml feedgen oss2
brew install ffmpeg

# Primary workflow — all operations go through manage.sh
./manage.sh add <url_or_local_pdf>   # Generate episode + auto-publish via git push
./manage.sh list                      # List all episodes
./manage.sh delete <number>           # Delete episode by index + auto-publish

# Run directly without auto-publish
python main.py <url>
python main.py --list

# Local dev server (serves from output_dir)
python server.py
```

There are no tests or linters configured in this project.

## Architecture

Pipeline: `URL → Fetcher → LLM Script Generator → Edge TTS → OSS Upload → RSS Feed Update`

- **`main.py`** — CLI entry point and pipeline orchestrator. Auto-detects source type from URL, runs the 5-step pipeline (fetch → script → TTS → upload → feed).
- **`fetchers/`** — Content extractors. All inherit from `BaseFetcher` and return a `FetchResult(title, content, source_type, url)`. Source type determines which LLM prompt is used.
- **`processor/script_generator.py`** — Uses OpenAI-compatible API (via `openai` SDK) to convert fetched content into a Chinese podcast script. Has distinct prompts per source type: papers/reports stay close to source material; Reddit/Twitter prompts allow more editorial commentary.
- **`tts/edge_tts_engine.py`** — Converts script text to speech using Microsoft Edge TTS, then re-encodes with ffmpeg to 44.1kHz/128kbps mono MP3 for Apple Podcasts compatibility.
- **`storage/oss_uploader.py`** — Uploads MP3 files to Alibaba Cloud OSS. Local MP3 is deleted after upload.
- **`feed/rss_generator.py`** — Maintains `episodes.json` as the episode database and generates `feed.xml` with iTunes podcast extensions. Audio URLs point to OSS.
- **`manage.sh`** — Wrapper that runs the pipeline then auto-commits and pushes `docs/` to GitHub Pages.
- **`server.py`** — Simple HTTP server for local feed testing.

## Configuration

- `config.yaml` (gitignored) — Contains LLM endpoint, API keys, TTS settings, OSS credentials, feed metadata. Copy from `config.example.yaml`.
- `config.example.yaml` — Template without secrets.
- Twitter fetcher requires a `cookies.txt` file (browser export).

## Key Details

- Output directory is `./docs` (for GitHub Pages). Contains `feed.xml`, `episodes.json`, and `cover.jpg`.
- The LLM client uses the OpenAI SDK but connects to any OpenAI-compatible endpoint (configured via `base_url`).
- `FetchResult.source_type` values: `"paper"`, `"report"`, `"reddit"`, `"twitter"` — these map to different prompt templates in `ScriptGenerator`.
- All text is in Chinese (zh-cn). The project targets Chinese-speaking listeners.

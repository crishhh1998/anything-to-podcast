import asyncio
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import edge_tts
from mutagen.id3 import ID3, CTOC, CHAP, TIT2, CTOCFlags
from mutagen.mp3 import MP3

from .text_preprocessor import preprocess_for_tts


@dataclass
class Chapter:
    title: str
    start_seconds: float


@dataclass
class TTSResult:
    audio_path: str
    chapters: list[Chapter]
    duration_seconds: float = 0.0


def parse_chapters(text: str) -> list[tuple[str, str]]:
    """Parse script text into (chapter_title, chapter_text) pairs.

    Looks for [CHAPTER: title] markers. Text before the first marker
    becomes a chapter titled "开场".
    """
    pattern = r'\[CHAPTER:\s*(.+?)\]'
    parts = re.split(pattern, text)

    chapters = []
    if parts[0].strip():
        chapters.append(("开场", parts[0].strip()))

    for i in range(1, len(parts), 2):
        title = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if body:
            chapters.append((title, body))

    # Fallback: no chapter markers found
    if not chapters:
        chapters.append(("全文", text.strip()))

    return chapters


def _get_mp3_duration(path: str) -> float:
    """Get MP3 duration in seconds using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    return float(result.stdout.strip())


class EdgeTTSEngine:
    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural", rate: str = "+0%"):
        self.voice = voice
        self.rate = rate

    async def _synthesize(self, text: str, output_path: str) -> None:
        text = preprocess_for_tts(text)
        communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
        await communicate.save(output_path)

    def _convert_to_standard_mp3(self, input_path: str, output_path: str) -> None:
        """Convert to 44.1kHz 128kbps MP3 for Apple Podcasts compatibility."""
        subprocess.run(
            ["ffmpeg", "-y", "-i", input_path,
             "-ar", "44100", "-ab", "128k", "-ac", "1",
             output_path],
            capture_output=True, check=True,
        )

    def synthesize(self, text: str, title: str, output_dir: str) -> TTSResult:
        """Synthesize text to MP3 with chapter timestamps.

        Returns TTSResult with the audio path and chapter list.
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        safe_title = re.sub(r"[^\w\u4e00-\u9fff-]", "_", title)[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{safe_title}.mp3"
        output_path = str(Path(output_dir) / filename)

        chapters_data = parse_chapters(text)

        if len(chapters_data) <= 1:
            # No chapters, synthesize as single file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp_path = tmp.name
            asyncio.run(self._synthesize(text, tmp_path))
            self._convert_to_standard_mp3(tmp_path, output_path)
            Path(tmp_path).unlink(missing_ok=True)
            duration = _get_mp3_duration(output_path)
            return TTSResult(audio_path=output_path, chapters=[], duration_seconds=duration)

        # Synthesize each chapter separately
        chapter_files = []
        chapters = []
        cumulative_seconds = 0.0

        with tempfile.TemporaryDirectory() as tmp_dir:
            for i, (ch_title, ch_text) in enumerate(chapters_data):
                raw_path = str(Path(tmp_dir) / f"ch{i}_raw.mp3")
                std_path = str(Path(tmp_dir) / f"ch{i}.mp3")

                asyncio.run(self._synthesize(ch_text, raw_path))
                self._convert_to_standard_mp3(raw_path, std_path)

                chapters.append(Chapter(title=ch_title, start_seconds=cumulative_seconds))
                duration = _get_mp3_duration(std_path)
                cumulative_seconds += duration
                chapter_files.append(std_path)

            # Concatenate all chapter files
            list_file = str(Path(tmp_dir) / "concat.txt")
            with open(list_file, "w") as f:
                for cf in chapter_files:
                    f.write(f"file '{cf}'\n")

            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                 "-i", list_file, "-c", "copy", output_path],
                capture_output=True, check=True,
            )

        # Embed chapter markers into MP3 ID3 tags
        _embed_chapters(output_path, chapters, cumulative_seconds)

        return TTSResult(audio_path=output_path, chapters=chapters, duration_seconds=cumulative_seconds)


def _embed_chapters(mp3_path: str, chapters: list[Chapter], total_seconds: float) -> None:
    """Embed ID3 CHAP/CTOC frames into MP3 for Apple Podcasts chapter support."""
    audio = MP3(mp3_path)
    if audio.tags is None:
        audio.add_tags()
    tags = audio.tags

    total_ms = int(total_seconds * 1000)
    child_ids = []

    for i, ch in enumerate(chapters):
        chap_id = f"chp{i}"
        child_ids.append(chap_id)

        # End time: start of next chapter, or total duration
        if i + 1 < len(chapters):
            end_ms = int(chapters[i + 1].start_seconds * 1000)
        else:
            end_ms = total_ms

        tags.add(CHAP(
            element_id=chap_id,
            start_time=int(ch.start_seconds * 1000),
            end_time=end_ms,
            sub_frames=[TIT2(encoding=3, text=[ch.title])],
        ))

    tags.add(CTOC(
        element_id="toc",
        flags=CTOCFlags.TOP_LEVEL | CTOCFlags.ORDERED,
        child_element_ids=child_ids,
        sub_frames=[TIT2(encoding=3, text=["Table of Contents"])],
    ))

    audio.save()

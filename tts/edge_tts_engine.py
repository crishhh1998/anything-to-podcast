import asyncio
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import edge_tts


class EdgeTTSEngine:
    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural", rate: str = "+0%"):
        self.voice = voice
        self.rate = rate

    async def _synthesize(self, text: str, output_path: str) -> None:
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

    def synthesize(self, text: str, title: str, output_dir: str) -> str:
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        safe_title = re.sub(r"[^\w\u4e00-\u9fff-]", "_", title)[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{safe_title}.mp3"
        output_path = str(Path(output_dir) / filename)

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        asyncio.run(self._synthesize(text, tmp_path))
        self._convert_to_standard_mp3(tmp_path, output_path)
        Path(tmp_path).unlink(missing_ok=True)
        return output_path

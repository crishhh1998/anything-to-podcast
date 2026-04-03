from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI

from fetchers.base import FetchResult
from .prompts import get_prompt

# 中文朗读速度约 300 字/分钟
CHARS_PER_MINUTE = 300


@dataclass
class ScriptResult:
    """Contains both short and long versions of the generated script."""
    short: str
    long: str


def duration_to_chars(minutes: int) -> tuple[int, int]:
    """Convert target duration in minutes to (min_chars, max_chars)."""
    center = minutes * CHARS_PER_MINUTE
    margin = CHARS_PER_MINUTE  # ±1 分钟容差
    return max(300, center - margin), center + margin


class ScriptGenerator:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model

    def generate(self, fetch_result: FetchResult, duration: int = 10,
                 prompt_file: str | None = None) -> ScriptResult:
        """Generate both short and long podcast scripts.

        Args:
            fetch_result: Fetched content.
            duration: Target duration in minutes for the long script.
            prompt_file: Path to a .md prompt template. If None, uses built-in prompts.
        """
        if prompt_file:
            template = Path(prompt_file).read_text(encoding="utf-8").strip()
            base_prompt = template.format(content=fetch_result.content)
            short_script = self._call_llm_raw(
                base_prompt + "\n\n请将以上内容控制在 500-1000 字。"
            )
            lo, hi = duration_to_chars(duration)
            long_script = self._call_llm_raw(
                base_prompt + f"\n\n请将以上内容控制在 {lo}-{hi} 字（约 {duration} 分钟朗读时长）。"
            )
        else:
            short_script = self._call_llm_builtin(fetch_result, "short")
            lo, hi = duration_to_chars(duration)
            long_script = self._call_llm_builtin(fetch_result, "long", duration_hint=(lo, hi, duration))
        return ScriptResult(short=short_script, long=long_script)

    def _call_llm_builtin(self, fetch_result: FetchResult, length: str,
                          duration_hint: tuple[int, int, int] | None = None) -> str:
        prompt_template = get_prompt(fetch_result.source_type, length)
        user_prompt = prompt_template.format(content=fetch_result.content)
        if duration_hint:
            lo, hi, mins = duration_hint
            user_prompt += f"\n\n请将以上内容控制在 {lo}-{hi} 字（约 {mins} 分钟朗读时长）。"
        return self._call_llm_raw(user_prompt)

    def _call_llm_raw(self, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content

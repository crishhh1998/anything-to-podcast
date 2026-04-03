from dataclasses import dataclass
from pathlib import Path

from openai import OpenAI

from fetchers.base import FetchResult
from .prompts import get_prompt

# 中文朗读速度约 300 字/分钟
CHARS_PER_MINUTE = 300

CHAPTER_INSTRUCTION = "在每个内容板块的开头，用 [CHAPTER: 章节标题] 标记（如 [CHAPTER: 背景与动机]），标题简短有概括性。除此标记外不要使用其他格式符号。"


@dataclass
class ScriptResult:
    """Contains both short and long versions of the generated script."""
    short: str
    long: str
    podcast_title: str = ""
    intro: str = ""


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
                base_prompt + f"\n\n请将以上内容控制在 {lo}-{hi} 字（约 {duration} 分钟朗读时长）。{CHAPTER_INSTRUCTION}"
            )
        else:
            short_script = self._call_llm_builtin(fetch_result, "short")
            lo, hi = duration_to_chars(duration)
            long_script = self._call_llm_builtin(fetch_result, "long", duration_hint=(lo, hi, duration))

        podcast_title, intro = self._generate_title_and_intro(
            fetch_result.title, short_script
        )
        return ScriptResult(
            short=short_script, long=long_script,
            podcast_title=podcast_title, intro=intro,
        )

    def _call_llm_builtin(self, fetch_result: FetchResult, length: str,
                          duration_hint: tuple[int, int, int] | None = None) -> str:
        prompt_template = get_prompt(fetch_result.source_type, length)
        user_prompt = prompt_template.format(content=fetch_result.content)
        if duration_hint:
            lo, hi, mins = duration_hint
            user_prompt += f"\n\n请将以上内容控制在 {lo}-{hi} 字（约 {mins} 分钟朗读时长）。"
        return self._call_llm_raw(user_prompt)

    def _generate_title_and_intro(self, original_title: str, short_script: str) -> tuple[str, str]:
        """Generate a podcast-friendly title and 3-sentence intro from the short script."""
        prompt = f"""根据以下信息，生成两样东西：

原始标题：{original_title}

内容摘要：
{short_script}

请生成：
1. 播客标题：格式为"方法/主题简称：一句话说明做了什么"，简洁有力，不超过30字。例如"LoRA：用低秩分解高效微调大模型"
2. 三句话简介：用三句话概括这期内容的核心，让听众快速判断是否感兴趣。

严格按以下格式输出，不要加其他内容：
标题：xxx
简介：xxx"""
        result = self._call_llm_raw(prompt)
        return self._parse_title_and_intro(result, original_title)

    @staticmethod
    def _parse_title_and_intro(text: str, fallback_title: str) -> tuple[str, str]:
        """Parse LLM output into (title, intro)."""
        title = fallback_title
        intro = ""
        for line in text.strip().splitlines():
            line = line.strip()
            if line.startswith("标题：") or line.startswith("标题:"):
                title = line.split("：", 1)[-1].split(":", 1)[-1].strip()
            elif line.startswith("简介：") or line.startswith("简介:"):
                intro = line.split("：", 1)[-1].split(":", 1)[-1].strip()
        return title, intro

    def _call_llm_raw(self, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content

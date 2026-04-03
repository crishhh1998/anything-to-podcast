from dataclasses import dataclass

from openai import OpenAI

from fetchers.base import FetchResult
from .prompts import get_prompt

LENGTH_SUFFIX = {
    "short": "\n\n请将以上内容控制在 500-1000 字。",
    "long": "\n\n请将以上内容控制在 3000-3600 字（约 10-12 分钟朗读时长）。",
}


@dataclass
class ScriptResult:
    """Contains both short and long versions of the generated script."""
    short: str
    long: str


class ScriptGenerator:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model

    def generate(self, fetch_result: FetchResult) -> ScriptResult:
        """Generate both short and long podcast scripts using built-in prompts."""
        short_script = self._call_llm(fetch_result, "short")
        long_script = self._call_llm(fetch_result, "long")
        return ScriptResult(short=short_script, long=long_script)

    def generate_with_template(self, content: str, template: str) -> ScriptResult:
        """Generate both short and long scripts using a custom prompt template.

        Args:
            content: The fetched content text.
            template: Prompt template string with {content} placeholder.
        """
        base_prompt = template.format(content=content)
        short_script = self._call_llm_raw(base_prompt + LENGTH_SUFFIX["short"])
        long_script = self._call_llm_raw(base_prompt + LENGTH_SUFFIX["long"])
        return ScriptResult(short=short_script, long=long_script)

    def _call_llm(self, fetch_result: FetchResult, length: str) -> str:
        prompt_template = get_prompt(fetch_result.source_type, length)
        user_prompt = prompt_template.format(content=fetch_result.content)
        return self._call_llm_raw(user_prompt)

    def _call_llm_raw(self, user_prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content

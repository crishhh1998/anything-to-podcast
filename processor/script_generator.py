from dataclasses import dataclass

from openai import OpenAI

from fetchers.base import FetchResult
from .prompts import get_prompt


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
        """Generate both short and long podcast scripts."""
        short_script = self._call_llm(fetch_result, "short")
        long_script = self._call_llm(fetch_result, "long")
        return ScriptResult(short=short_script, long=long_script)

    def _call_llm(self, fetch_result: FetchResult, length: str) -> str:
        prompt_template = get_prompt(fetch_result.source_type, length)
        user_prompt = prompt_template.format(content=fetch_result.content)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.7,
        )

        return response.choices[0].message.content

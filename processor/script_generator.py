from openai import OpenAI

from fetchers.base import FetchResult

PROMPTS = {
    "paper": """你是一位专业的中文播客主播。请将以下学术论文内容转化为中文播客脚本。

要求：
- 尽量贴近原文内容，保持学术准确性
- 用自然流畅的中文口语表达，适合朗读
- 保留关键的技术术语（可以中英文对照）
- 按照论文结构组织内容：背景、方法、实验、结论
- 开头简要介绍论文标题和主题
- 结尾做简短总结
- 不要加入"大家好"等套话，直接进入内容
- 输出纯文本，不要包含任何标记符号

论文内容：
{content}""",

    "report": """你是一位专业的中文播客主播。请将以下技术报告内容转化为中文播客脚本。

要求：
- 尽量贴近原文内容，保持技术准确性
- 用自然流畅的中文口语表达，适合朗读
- 保留关键的技术术语（可以中英文对照）
- 按照报告的逻辑结构组织内容
- 开头简要介绍报告标题和主题
- 结尾做简短总结
- 不要加入"大家好"等套话，直接进入内容
- 输出纯文本，不要包含任何标记符号

报告内容：
{content}""",

    "reddit": """你是一位专业的中文播客主播。请将以下 Reddit 帖子及评论转化为中文播客脚本。

要求：
- 可以适当拓展背景知识和分析
- 用自然流畅的中文口语表达，适合朗读
- 介绍帖子的核心观点和社区讨论要点
- 对有趣或有价值的评论进行点评
- 可以加入你自己的分析和见解
- 不要加入"大家好"等套话，直接进入内容
- 输出纯文本，不要包含任何标记符号

帖子内容：
{content}""",

    "twitter": """你是一位专业的中文播客主播。请将以下推文内容转化为中文播客脚本。

要求：
- 可以适当拓展背景知识和分析
- 用自然流畅的中文口语表达，适合朗读
- 解释推文的背景和上下文
- 可以加入你自己的分析和见解
- 适当展开讨论相关话题
- 不要加入"大家好"等套话，直接进入内容
- 输出纯文本，不要包含任何标记符号

推文内容：
{content}""",
}


class ScriptGenerator:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model

    def generate(self, fetch_result: FetchResult) -> str:
        prompt_template = PROMPTS.get(fetch_result.source_type, PROMPTS["paper"])
        user_prompt = prompt_template.format(content=fetch_result.content)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.7,
        )

        return response.choices[0].message.content

"""Podcast script generation prompts, organized by source type and length."""

# 短稿：500-1000 字
# 长稿：10-12 分钟朗读，约 3000-3600 字

_BASE_RULES_SHORT = """要求：
- 控制在 500-1000 字
- 提炼核心要点，精简表达
- 用自然流畅的中文口语表达，适合朗读
- 保留关键的技术术语（可以中英文对照）
- 开头简要介绍标题和主题
- 结尾一两句话总结
- 不要加入"大家好"等套话，直接进入内容
- 输出纯文本，不要包含任何标记符号"""

_BASE_RULES_LONG = """要求：
- 控制在 3000-3600 字（约 10-12 分钟朗读时长）
- 用自然流畅的中文口语表达，适合朗读
- 保留关键的技术术语（可以中英文对照）
- 开头简要介绍标题和主题
- 结尾做简短总结
- 不要加入"大家好"等套话，直接进入内容
- 输出纯文本，不要包含任何标记符号"""


PROMPTS = {
    "paper": {
        "short": f"""你是一位专业的中文播客主播。请将以下学术论文内容转化为一篇简短的中文播客脚本。

{_BASE_RULES_SHORT}
- 按照"背景-方法-结论"的精简结构组织
- 尽量贴近原文内容，保持学术准确性

论文内容：
{{content}}""",

        "long": f"""你是一位专业的中文播客主播。请将以下学术论文内容转化为中文播客脚本。

{_BASE_RULES_LONG}
- 按照论文结构组织内容：背景、方法、实验、结论
- 尽量贴近原文内容，保持学术准确性
- 对关键实验结果和数据进行详细说明

论文内容：
{{content}}""",
    },

    "report": {
        "short": f"""你是一位专业的中文播客主播。请将以下技术报告内容转化为一篇简短的中文播客脚本。

{_BASE_RULES_SHORT}
- 按照报告的核心逻辑精简组织
- 尽量贴近原文内容，保持技术准确性

报告内容：
{{content}}""",

        "long": f"""你是一位专业的中文播客主播。请将以下技术报告内容转化为中文播客脚本。

{_BASE_RULES_LONG}
- 按照报告的逻辑结构组织内容
- 尽量贴近原文内容，保持技术准确性
- 对关键数据和结论进行详细阐述

报告内容：
{{content}}""",
    },

    "reddit": {
        "short": f"""你是一位专业的中文播客主播。请将以下 Reddit 帖子及评论转化为一篇简短的中文播客脚本。

{_BASE_RULES_SHORT}
- 聚焦帖子核心观点和最有价值的评论
- 可以适当加入简短分析

帖子内容：
{{content}}""",

        "long": f"""你是一位专业的中文播客主播。请将以下 Reddit 帖子及评论转化为中文播客脚本。

{_BASE_RULES_LONG}
- 介绍帖子的核心观点和社区讨论要点
- 对有趣或有价值的评论进行点评
- 可以适当拓展背景知识和分析
- 可以加入你自己的分析和见解

帖子内容：
{{content}}""",
    },

    "twitter": {
        "short": f"""你是一位专业的中文播客主播。请将以下推文内容转化为一篇简短的中文播客脚本。

{_BASE_RULES_SHORT}
- 简要解释推文的背景和上下文
- 可以加入简短的分析

推文内容：
{{content}}""",

        "long": f"""你是一位专业的中文播客主播。请将以下推文内容转化为中文播客脚本。

{_BASE_RULES_LONG}
- 解释推文的背景和上下文
- 可以加入你自己的分析和见解
- 适当展开讨论相关话题
- 可以适当拓展背景知识和分析

推文内容：
{{content}}""",
    },
}


def get_prompt(source_type: str, length: str) -> str:
    """Get prompt template by source type and length.

    Args:
        source_type: "paper", "report", "reddit", "twitter"
        length: "short" or "long"

    Returns:
        Prompt template string with {content} placeholder.
    """
    prompts = PROMPTS.get(source_type, PROMPTS["paper"])
    return prompts[length]

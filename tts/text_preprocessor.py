"""TTS text preprocessor.

Transforms script text into a form that Edge TTS can pronounce correctly:
- English abbreviations → space-separated letters (e.g. "GPT" → "G P T")
- Known terms → Chinese-friendly pronunciation
- Numbers/units → spoken Chinese form
"""

import re

# 已知术语词典：英文 → TTS 友好的中文/拼读写法
# 长词优先匹配，避免子串冲突
TERM_DICT: dict[str, str] = {
    # 模型名称
    "GPT-4o": "G P T 4 o",
    "GPT-4": "G P T 4",
    "GPT-3.5": "G P T 3.5",
    "GPT": "G P T",
    "DALL-E": "达利",
    "LLaMA": "拉马",
    "BERT": "伯特",
    "CLIP": "克利普",
    "YOLO": "优楼",
    "ResNet": "残差网络 ResNet",
    "ViT": "V i T",
    "GAN": "G A N",
    "VAE": "V A E",
    "DDPM": "D D P M",
    # 技术术语
    "Transformer": "Transformer",
    "transformer": "transformer",
    "Attention": "Attention",
    "attention": "attention",
    "RLHF": "R L H F",
    "DPO": "D P O",
    "PPO": "P P O",
    "SFT": "S F T",
    "GRPO": "G R P O",
    "CoT": "C o T",
    "RAG": "R A G",
    "MoE": "M o E",
    "LoRA": "LoRA",
    "QLoRA": "Q LoRA",
    "PEFT": "P E F T",
    "NLP": "N L P",
    "NLU": "N L U",
    "NLG": "N L G",
    "CV": "C V",
    "LLM": "L L M",
    "LLMs": "L L M s",
    "MLLMs": "M L L M s",
    "MLLM": "M L L M",
    "VLM": "V L M",
    "AGI": "A G I",
    "ASI": "A S I",
    "SOTA": "S O T A",
    "API": "A P I",
    "APIs": "A P I s",
    "GPU": "G P U",
    "GPUs": "G P U s",
    "TPU": "T P U",
    "CPU": "C P U",
    "CUDA": "酷达",
    "FLOPS": "F L O P S",
    "FP16": "F P 16",
    "BF16": "B F 16",
    "INT8": "I N T 8",
    "INT4": "I N T 4",
    "KV cache": "K V 缓存",
    "GGUF": "G G U F",
    # 公司/组织
    "OpenAI": "Open A I",
    "DeepMind": "Deep Mind",
    "DeepSeek": "Deep Seek",
    "HuggingFace": "Hugging Face",
    "Hugging Face": "Hugging Face",
    # 评测
    "MMLU": "M M L U",
    "BLEU": "B L E U",
    "ROUGE": "R O U G E",
    "F1": "F 1",
    # 数据/格式
    "JSON": "J S O N",
    "YAML": "亚莫",
    "XML": "X M L",
    "CSV": "C S V",
    "SQL": "S Q L",
    "HTML": "H T M L",
    "CSS": "C S S",
    "HTTP": "H T T P",
    "HTTPS": "H T T P S",
    "URL": "U R L",
    "SDK": "S D K",
    "CLI": "C L I",
    "IDE": "I D E",
    "CI/CD": "C I C D",
    "AWS": "A W S",
    "GCP": "G C P",
}


def _build_term_pattern() -> re.Pattern:
    """Build a regex that matches all dictionary terms, longest first."""
    # Sort by length descending so longer terms match first
    sorted_terms = sorted(TERM_DICT.keys(), key=len, reverse=True)
    escaped = [re.escape(t) for t in sorted_terms]
    # Use ASCII letter boundaries to avoid issues with Chinese-English mixed text
    pattern = r'(?<![A-Za-z])(' + '|'.join(escaped) + r')(?![A-Za-z])'
    return re.compile(pattern)


_TERM_RE = _build_term_pattern()


def _replace_known_terms(text: str) -> str:
    """Replace known terms with TTS-friendly versions."""
    return _TERM_RE.sub(lambda m: TERM_DICT[m.group(0)], text)


def _expand_unknown_abbreviations(text: str) -> str:
    """Expand remaining all-caps abbreviations (2+ letters) by inserting spaces.

    E.g. "ABCD" → "A B C D". Skips terms already space-separated.
    """
    def _expand(m: re.Match) -> str:
        word = m.group(0)
        # Already space-separated or a known single word, skip
        if ' ' in word:
            return word
        return ' '.join(word)

    # Match 2+ uppercase letters, using ASCII-only boundaries for Chinese-English mixed text
    return re.sub(r'(?<![A-Za-z])[A-Z]{2,}(?![A-Za-z])', _expand, text)


def _normalize_numbers(text: str) -> str:
    """Convert common number patterns to spoken Chinese.

    Handles: percentages, multipliers (10x), and basic large numbers.
    """
    # 10x → 十倍
    text = re.sub(r'(\d+)\s*x(?![A-Za-z])', lambda m: _num_to_chinese(int(m.group(1))) + '倍', text)

    # Keep percentages as-is (TTS handles "50%" reasonably as "百分之五十")

    return text


def _num_to_chinese(n: int) -> str:
    """Simple number to Chinese for small multipliers."""
    simple = {1: '一', 2: '两', 3: '三', 4: '四', 5: '五',
              6: '六', 7: '七', 8: '八', 9: '九', 10: '十',
              100: '一百', 1000: '一千'}
    if n in simple:
        return simple[n]
    return str(n)


def preprocess_for_tts(text: str) -> str:
    """Main entry: preprocess text for better TTS pronunciation."""
    text = _replace_known_terms(text)
    text = _expand_unknown_abbreviations(text)
    text = _normalize_numbers(text)
    return text

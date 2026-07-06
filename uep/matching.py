"""纯函数型 Verifier 的参考判分语义（text_match / choice_match / regex）。

协议不运行评测（不做 Runner），但为了打分行为可跨实现互操作，
纯函数型 Verifier 必须有唯一参考实现（双语行为矩阵：docs/uep-v2-test-spec.md §③）。
执行类（execution）与裁判类（llm_judge）只校验结构，不在本库执行。
"""

import re
import unicodedata

from uep.schema import ChoiceMatchVerifier, Normalization, RegexVerifier, TextMatchVerifier

#: 中文标点 → ASCII 对应（cjk_punct_fold=True 时应用）
_CJK_PUNCT_TABLE = str.maketrans(
    {
        "，": ",",
        "。": ".",
        "！": "!",
        "？": "?",
        "：": ":",
        "；": ";",
        "（": "(",
        "）": ")",
        "、": ",",
        "．": ".",
        "「": '"',
        "」": '"',
        "『": '"',
        "』": '"',
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "《": '"',
        "》": '"',
    }
)


def _width_fold(text: str) -> str:
    """全角 → 半角，仅折叠字母/数字/空格（ＡＢＣ→ABC、１２→12、全角空格→空格）。

    全角标点（如 U+FF0C "，"）不在此折叠——中文标点的归一是独立语义，
    由 ``cjk_punct_fold`` 显式管辖（矩阵用例 #4/#7/#9 的行为边界）。
    """
    out: list[str] = []
    for ch in text:
        code = ord(ch)
        if code == 0x3000:
            out.append(" ")
        elif 0xFF10 <= code <= 0xFF19 or 0xFF21 <= code <= 0xFF3A or 0xFF41 <= code <= 0xFF5A:
            out.append(chr(code - 0xFEE0))
        else:
            out.append(ch)
    return "".join(out)


def apply_normalization(text: str, norm: Normalization) -> str:
    """按规范顺序应用归一化：NFC → 宽度折叠 → 中文标点折叠 → 去首尾空白 → 大小写折叠。"""
    result = unicodedata.normalize(norm.unicode, text)
    if norm.width_fold:
        result = _width_fold(result)
    if norm.cjk_punct_fold:
        result = result.translate(_CJK_PUNCT_TABLE)
    if norm.strip_whitespace:
        result = result.strip()
    if norm.case_fold:
        result = result.casefold()
    return result


def text_match(verifier: TextMatchVerifier, candidate: str) -> bool:
    expected = verifier.expected if isinstance(verifier.expected, list) else [verifier.expected]
    cand = apply_normalization(candidate, verifier.normalize)
    return any(apply_normalization(e, verifier.normalize) == cand for e in expected)


def choice_match(verifier: ChoiceMatchVerifier, candidate_ids: list[str]) -> bool:
    return set(candidate_ids) == set(verifier.answer_ids)


def regex_extract(verifier: RegexVerifier, candidate: str) -> str | None:
    """返回匹配（或指定分组）的文本；不匹配返回 None。"""
    flags = 0
    for flag_char in verifier.flags or "":
        flags |= {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL}.get(flag_char, 0)
    match = re.search(verifier.pattern, candidate, flags)
    if match is None:
        return None
    if verifier.target_group is None:
        return match.group(0)
    return match.group(verifier.target_group)


def render_template(template: str, values: dict[str, str]) -> str:
    """llm_judge 模板渲染参考实现：注入值逐个 NFC，结果整体 NFC（矩阵用例 #10）。"""
    normalized = {k: unicodedata.normalize("NFC", v) for k, v in values.items()}
    return unicodedata.normalize("NFC", template.format(**normalized))

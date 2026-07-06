"""双语行为矩阵（FR-2.7）——docs/uep-v2-test-spec.md §③ 十用例逐行落地。"""

import unicodedata

import pytest

from uep.matching import render_template, text_match
from uep.schema import Normalization, TextMatchVerifier

NFD_CAFE = unicodedata.normalize("NFD", "café")

# (编号, expected, candidate, normalize 参数, 应否匹配)
MATRIX = [
    (1, "café", NFD_CAFE, {}, True),
    (2, "Paris", "paris", {}, False),
    (3, "Paris", "paris", {"case_fold": True}, True),
    (4, "ABC", "ＡＢＣ", {}, True),
    (5, "42", " 42 ", {}, True),
    (6, "北京大学", "北京大学", {}, True),
    (7, "你好，世界", "你好,世界", {}, False),
    (8, "你好，世界", "你好,世界", {"cjk_punct_fold": True}, True),
    (9, "答案是Ａ。", "答案是A.", {"cjk_punct_fold": True}, True),
]


@pytest.mark.fr("FR-2.7")
@pytest.mark.parametrize(("case_no", "expected", "candidate", "params", "should"), MATRIX)
def test_bilingual_matrix(case_no, expected, candidate, params, should):
    verifier = TextMatchVerifier(expected=expected, normalize=Normalization(**params))
    assert text_match(verifier, candidate) is should, f"矩阵用例 #{case_no} 失败"


@pytest.mark.fr("FR-2.7")
def test_case10_judge_template_nfc_preserved():
    template = "问题：{question}\n参考答案：{answer}\n请判分。"
    rendered = render_template(
        template,
        {"question": unicodedata.normalize("NFD", "北京有几个市辖区？café"), "answer": "16"},
    )
    assert unicodedata.is_normalized("NFC", rendered)
    assert "北京有几个市辖区" in rendered
    assert "café" in rendered

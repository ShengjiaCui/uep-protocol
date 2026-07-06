"""lang 元数据与 NFC 规范化（FR-1.2）。"""

import unicodedata

import pytest
from pydantic import ValidationError

from uep.schema import EvalItem


def _base(**overrides: object) -> dict:
    data = {
        "id": "lang_001",
        "lang": ["zh-CN"],
        "task": {"type": "qa", "question": "咖啡的法语是什么？"},
        "verifiers": [{"type": "text_match", "expected": "café"}],
    }
    data.update(overrides)
    return data


@pytest.mark.fr("FR-1.2")
class TestLangAndNormalization:
    def test_content_stored_as_nfc(self):
        nfd_question = unicodedata.normalize("NFD", "café 是什么？")
        item = EvalItem.model_validate(_base(task={"type": "qa", "question": nfd_question}))
        assert unicodedata.is_normalized("NFC", item.task.question)
        assert item.task.question == unicodedata.normalize("NFC", nfd_question)

    def test_mixed_language_tags_ok(self):
        item = EvalItem.model_validate(_base(lang=["zh-CN", "en"]))
        assert item.lang == ["zh-CN", "en"]

    def test_invalid_language_tag_rejected(self):
        with pytest.raises(ValidationError):
            EvalItem.model_validate(_base(lang=["zh_CN"]))

    def test_empty_language_list_rejected(self):
        with pytest.raises(ValidationError):
            EvalItem.model_validate(_base(lang=[]))

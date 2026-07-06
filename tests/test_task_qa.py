"""qa 原型（FR-2.2）。"""

import pytest
from pydantic import ValidationError

from uep.schema import EvalItem


@pytest.mark.fr("FR-2.2")
class TestQaTask:
    def test_valid_qa_item(self):
        item = EvalItem.model_validate(
            {
                "id": "qa_zh_001",
                "lang": ["zh-CN"],
                "task": {"type": "qa", "question": "一年有多少个季度？"},
                "verifiers": [{"type": "text_match", "expected": ["4", "四"]}],
            }
        )
        assert item.task.type == "qa"
        assert item.task.question == "一年有多少个季度？"

    def test_empty_question_rejected(self):
        with pytest.raises(ValidationError):
            EvalItem.model_validate(
                {
                    "id": "qa_bad",
                    "lang": ["en"],
                    "task": {"type": "qa", "question": ""},
                    "verifiers": [{"type": "text_match", "expected": "x"}],
                }
            )

"""choices 原型（FR-2.1）——选项结构、顺序语义与唯一性。"""

import pytest
from pydantic import ValidationError

from uep.schema import ChoicesTask, EvalItem


def _item(options: list[dict], **overrides: object) -> dict:
    data = {
        "id": "choices_zh_001",
        "lang": ["zh-CN"],
        "task": {"type": "choices", "question": "水的化学式是什么？", "options": options},
        "verifiers": [{"type": "choice_match", "answer_ids": ["A"]}],
    }
    data.update(overrides)
    return data


@pytest.mark.fr("FR-2.1")
class TestChoicesTask:
    def test_valid_choices_item(self):
        item = EvalItem.model_validate(
            _item([{"id": "A", "text": "H2O"}, {"id": "B", "text": "CO2"}])
        )
        assert isinstance(item.task, ChoicesTask)
        assert item.task.multi_select is False

    def test_option_order_preserved_through_roundtrip(self):
        options = [{"id": str(i), "text": f"选项{i}"} for i in range(4)]
        item = EvalItem.model_validate(_item(options))
        again = EvalItem.model_validate_json(item.model_dump_json())
        assert [o.id for o in again.task.options] == ["0", "1", "2", "3"]

    def test_less_than_two_options_rejected(self):
        with pytest.raises(ValidationError):
            EvalItem.model_validate(_item([{"id": "A", "text": "唯一"}]))

    def test_duplicate_option_ids_rejected(self):
        with pytest.raises(ValidationError):
            EvalItem.model_validate(_item([{"id": "A", "text": "甲"}, {"id": "A", "text": "乙"}]))

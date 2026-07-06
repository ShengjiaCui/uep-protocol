"""EvalItem 骨架与判别联合校验（FR-1.1）。"""

import pytest
from pydantic import ValidationError

from uep.schema import EvalItem

BASE = {
    "id": "core_001",
    "lang": ["zh-CN"],
    "task": {"type": "qa", "question": "水的化学式是什么？"},
    "verifiers": [{"type": "text_match", "expected": "H2O"}],
}


@pytest.mark.fr("FR-1.1")
class TestSchemaCore:
    def test_minimal_item_roundtrip(self):
        item = EvalItem.model_validate(BASE)
        again = EvalItem.model_validate_json(item.model_dump_json())
        assert again == item
        assert item.uep_version == "2.0"

    def test_unknown_top_level_field_rejected(self):
        with pytest.raises(ValidationError):
            EvalItem.model_validate({**BASE, "runner_specific": 1})

    def test_unknown_task_type_rejected(self):
        with pytest.raises(ValidationError):
            EvalItem.model_validate({**BASE, "task": {"type": "essay", "question": "x"}})

    def test_unsupported_major_version_rejected(self):
        with pytest.raises(ValidationError):
            EvalItem.model_validate({**BASE, "uep_version": "3.0"})

    def test_verifiers_must_be_nonempty(self):
        with pytest.raises(ValidationError):
            EvalItem.model_validate({**BASE, "verifiers": []})

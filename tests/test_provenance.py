"""Provenance 溯源戳与 source_map（FR-1.3）——裁决①"留痕、能还原"的骨架侧。"""

import pytest
from pydantic import ValidationError

from uep.schema import EvalItem, Provenance

PROV = {
    "dataset": "demo-benchmark",
    "adapter": "demo_adapter",
    "adapter_version": "0.1.0",
    "mapping_table": "mappings/demo.yaml",
    "mapping_hash": "sha256:abc123",
    "converted_at": "2026-07-04",
}


def _item(**overrides: object) -> dict:
    data = {
        "id": "prov_001",
        "lang": ["en"],
        "task": {"type": "qa", "question": "What is the capital of France?"},
        "verifiers": [{"type": "text_match", "expected": "Paris"}],
        "source": PROV,
        "source_map": {"task.question": "prompt_text", "verifiers[0].expected": "gold"},
    }
    data.update(overrides)
    return data


@pytest.mark.fr("FR-1.3")
class TestProvenance:
    def test_provenance_and_source_map_roundtrip(self):
        item = EvalItem.model_validate(_item())
        again = EvalItem.model_validate_json(item.model_dump_json())
        assert isinstance(again.source, Provenance)
        assert again.source.mapping_hash == "sha256:abc123"
        assert again.source_map == item.source_map

    def test_incomplete_provenance_rejected(self):
        broken = dict(PROV)
        del broken["mapping_hash"]
        with pytest.raises(ValidationError):
            EvalItem.model_validate(_item(source=broken))

    def test_provenance_optional(self):
        item = EvalItem.model_validate(_item(source=None, source_map=None))
        assert item.source is None

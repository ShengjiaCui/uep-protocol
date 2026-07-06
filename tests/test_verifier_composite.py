"""composite 复合验证器（FR-1.5）——Agent 任务的复合打分表达。"""

import pytest
from pydantic import ValidationError

from uep.schema import CompositeVerifier


def _composite(**overrides: object) -> dict:
    data = {
        "type": "composite",
        "mode": "all_of",
        "children": [
            {"type": "text_match", "expected": "31"},
            {"type": "regex", "pattern": r"\d+"},
        ],
    }
    data.update(overrides)
    return data


@pytest.mark.fr("FR-1.5")
class TestCompositeVerifier:
    def test_all_of_with_two_kinds(self):
        v = CompositeVerifier.model_validate(_composite())
        assert {c.type for c in v.children} == {"text_match", "regex"}

    def test_nested_composite_recursion(self):
        v = CompositeVerifier.model_validate(
            _composite(
                children=[_composite(mode="any_of"), {"type": "text_match", "expected": "x"}]
            )
        )
        assert v.children[0].type == "composite"

    def test_weighted_requires_matching_weights(self):
        with pytest.raises(ValidationError):
            CompositeVerifier.model_validate(_composite(mode="weighted"))
        ok = CompositeVerifier.model_validate(_composite(mode="weighted", weights=[0.7, 0.3]))
        assert ok.weights == [0.7, 0.3]

    def test_weights_forbidden_outside_weighted(self):
        with pytest.raises(ValidationError):
            CompositeVerifier.model_validate(_composite(weights=[0.5, 0.5]))

    def test_minimum_two_children(self):
        with pytest.raises(ValidationError):
            CompositeVerifier.model_validate(
                _composite(children=[{"type": "text_match", "expected": "x"}])
            )

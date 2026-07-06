"""extras 纪律 lint（FR-1.4）——任务本体数据入 extras 即告警（P3）。"""

import pytest

from uep.schema import EvalItem
from uep.validate import lint_extras


def _item(extras: dict) -> EvalItem:
    return EvalItem.model_validate(
        {
            "id": "extras_001",
            "lang": ["zh-CN"],
            "task": {"type": "qa", "question": "长江有多长？"},
            "verifiers": [{"type": "regex", "pattern": r"6\d{3}"}],
            "extras": extras,
        }
    )


@pytest.mark.fr("FR-1.4")
class TestExtrasLint:
    def test_payload_key_in_extras_warns(self):
        issues = lint_extras(_item({"question": "泄漏", "Answer": "也泄漏"}))
        assert len(issues) == 2
        assert all(i.severity == "warning" for i in issues)
        assert {i.field for i in issues} == {"extras.question", "extras.Answer"}

    def test_runner_specific_extras_clean(self):
        assert lint_extras(_item({"lm_eval_task_alias": "demo", "shots": 5})) == []

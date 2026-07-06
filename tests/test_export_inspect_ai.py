"""Inspect AI 样本导出（FR-6.1）——结构正确性与位置字母语义。"""

import pytest
from test_import_choices_real import load_slice

from uep.adapters import hellaswag, humaneval, inspect_ai, mmlu
from uep.schema import EvalItem

_ZH_CHOICES = EvalItem.model_validate(
    {
        "id": "ins_zh_001",
        "lang": ["zh-CN"],
        "task": {
            "type": "choices",
            "question": "水的化学式是什么？",
            "options": [{"id": "A", "text": "H2O"}, {"id": "B", "text": "CO2"}],
        },
        "verifiers": [{"type": "choice_match", "answer_ids": ["A"]}],
    }
)
_ZH_QA = EvalItem.model_validate(
    {
        "id": "ins_qa_001",
        "lang": ["zh-CN"],
        "task": {"type": "qa", "question": "六乘七等于多少？"},
        "verifiers": [{"type": "text_match", "expected": ["42", "四十二"]}],
    }
)


@pytest.mark.fr("FR-6.1")
class TestInspectExport:
    def test_choices_sample_structure(self):
        (sample,) = inspect_ai.export_samples([_ZH_CHOICES])
        assert sample == {
            "id": "ins_zh_001",
            "input": "水的化学式是什么？",
            "choices": ["H2O", "CO2"],
            "target": "A",
        }

    def test_target_is_positional_letter_not_source_id(self):
        """源 id 为下标（"0"–"3"）时 target 仍须是位置字母——框架自行标号。"""
        item = _ZH_CHOICES.model_dump()
        item["task"]["options"] = [{"id": str(i), "text": f"选项{i}"} for i in range(4)]
        item["verifiers"] = [{"type": "choice_match", "answer_ids": ["2"]}]
        (sample,) = inspect_ai.export_samples([EvalItem.model_validate(item)])
        assert sample["target"] == "C"

    def test_qa_sample_keeps_expected_shape(self):
        (sample,) = inspect_ai.export_samples([_ZH_QA])
        assert sample["input"] == "六乘七等于多少？"
        assert sample["target"] == ["42", "四十二"]

    def test_mixed_prototypes_rejected(self):
        with pytest.raises(ValueError, match="同质"):
            inspect_ai.export_samples([_ZH_CHOICES, _ZH_QA])

    def test_real_slices_export(self):
        mmlu_samples = inspect_ai.export_samples(mmlu.import_rows(load_slice("mmlu"))[:10])
        assert len(mmlu_samples) == 10
        assert all(s["target"] in {"A", "B", "C", "D"} for s in mmlu_samples)
        hs_samples = inspect_ai.export_samples(hellaswag.import_rows(load_slice("hellaswag"))[:5])
        assert all(s["target"] in {"A", "B", "C", "D"} for s in hs_samples), "下标 id 须转位置字母"

    def test_jsonl_roundtrip(self):
        import json

        samples = inspect_ai.export_samples([_ZH_CHOICES])
        reparsed = [json.loads(line) for line in inspect_ai.dump_jsonl(samples).splitlines()]
        assert reparsed == samples


@pytest.mark.fr("FR-6.1")
class TestCodegenSamples:
    def test_codegen_sample_carries_execution_payload(self):
        items = humaneval.import_rows(load_slice("humaneval"))[:3]
        samples = inspect_ai.export_samples(items)
        assert len(samples) == 3
        for item, sample in zip(items, samples, strict=True):
            assert sample["input"] == item.task.prompt
            meta = sample["metadata"]
            verifier = item.verifiers[0]
            assert meta["test_code"] == verifier.tests.test_code
            assert meta["entry_point"] == verifier.tests.entry_point
            assert meta["timeout_s"] == verifier.sandbox.timeout_s
            assert meta["language"] == item.task.language

    def test_codegen_requires_execution_verifier(self):
        from uep.schema import EvalItem

        item = humaneval.import_rows(load_slice("humaneval"))[0]
        data = item.model_dump(exclude_none=True)
        data["verifiers"] = [{"type": "regex", "pattern": "x"}]
        with pytest.raises(ValueError):
            inspect_ai.export_samples([EvalItem.model_validate(data)])

    def test_codegen_execution_payload_without_test_code_rejected(self):
        """execution 载荷用 assertions（而非 test_code+entry_point）时——
        TestSuite 校验合法（三选一之一），但 _codegen_sample 缺 test_code/entry_point
        须显式拒绝，不能静默导出坏样本（防御分支覆盖）。"""
        from uep.schema import EvalItem

        item = humaneval.import_rows(load_slice("humaneval"))[0]
        data = item.model_dump(exclude_none=True)
        data["verifiers"][0]["tests"] = {
            "language": "python",
            "assertions": ["x == 1"],
            "harness": "exec",
        }
        with pytest.raises(ValueError, match="test_code"):
            inspect_ai.export_samples([EvalItem.model_validate(data)])

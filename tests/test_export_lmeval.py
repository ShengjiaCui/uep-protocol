"""lm-eval-harness 导出（FR-3.4 的 L1 部分）——任务包结构与数据正确性。

导出物 = 任务 YAML（generate_until + 正则抽取 + exact_match）+ 文档 JSONL。
真实跑分（L2）由 scripts/dogfood_run.py 对 Ollama 执行，不进 pytest。
"""

import json

import pytest
import yaml
from test_import_choices_real import load_slice

from uep.adapters import gsm8k, lmeval, mmlu
from uep.schema import EvalItem

_ZH = EvalItem.model_validate(
    {
        "id": "lmx_zh_001",
        "lang": ["zh-CN"],
        "task": {
            "type": "choices",
            "question": "水的化学式是什么？",
            "options": [{"id": "A", "text": "H2O"}, {"id": "B", "text": "CO2"}],
        },
        "verifiers": [{"type": "choice_match", "answer_ids": ["A"]}],
    }
)
_EN = EvalItem.model_validate(
    {
        "id": "lmx_en_001",
        "lang": ["en"],
        "task": {
            "type": "choices",
            "question": "Which planet is known as the Red Planet?",
            "options": [{"id": "A", "text": "Venus"}, {"id": "B", "text": "Mars"}],
        },
        "verifiers": [{"type": "choice_match", "answer_ids": ["B"]}],
    }
)


def _export(tmp_path, items, name="uep_demo"):
    yaml_path = lmeval.export_task(items, task_name=name, out_dir=tmp_path)
    cfg = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    docs_path = tmp_path / f"{name}.jsonl"
    docs = [json.loads(line) for line in docs_path.read_text(encoding="utf-8").splitlines()]
    return cfg, docs, docs_path


@pytest.mark.fr("FR-3.4")
class TestLmevalExport:
    def test_task_config_structure(self, tmp_path):
        cfg, _, docs_path = _export(tmp_path, [_ZH, _EN])
        assert cfg["task"] == "uep_demo"
        assert cfg["dataset_path"] == "json"
        assert cfg["dataset_kwargs"]["data_files"]["test"] == str(docs_path)
        assert cfg["test_split"] == "test"
        assert cfg["output_type"] == "generate_until"
        assert cfg["doc_to_text"] == "{{prompt}}"
        assert cfg["doc_to_target"] == "{{gold}}"
        assert cfg["metric_list"][0]["metric"] == "exact_match"

    def test_docs_carry_id_prompt_gold(self, tmp_path):
        _, docs, _ = _export(tmp_path, [_ZH, _EN])
        assert [d["id"] for d in docs] == ["lmx_zh_001", "lmx_en_001"]
        zh, en = docs
        assert "水的化学式是什么？" in zh["prompt"]
        assert "H2O" in zh["prompt"] and "CO2" in zh["prompt"]
        assert zh["gold"] == "A"
        assert en["gold"] == "B"

    def test_instruction_language_follows_item_lang(self, tmp_path):
        _, docs, _ = _export(tmp_path, [_ZH, _EN])
        zh, en = docs
        assert "只输出" in zh["prompt"], "中文条目应得到中文作答指令（P5）"
        assert "Respond with" in en["prompt"], "英文条目应得到英文作答指令"

    def test_filter_regex_built_from_actual_option_ids(self, tmp_path):
        cfg, _, _ = _export(tmp_path, [_ZH, _EN])
        steps = cfg["filter_list"][0]["filter"]
        regex_step = next(s for s in steps if s["function"] == "regex")
        assert "A|B" in regex_step["regex_pattern"]
        assert any(s["function"] == "take_first" for s in steps)

    def test_gold_always_among_option_ids(self, tmp_path):
        _, docs, _ = _export(tmp_path, [_ZH, _EN])
        for doc in docs:
            assert doc["gold"], "gold 不得为空"

    def test_real_slice_exports_ten_docs(self, tmp_path):
        items = mmlu.import_rows(load_slice("mmlu"))[:10]
        cfg, docs, _ = _export(tmp_path, items, name="uep_real")
        assert len(docs) == 10
        assert all(doc["gold"] in {"A", "B", "C", "D"} for doc in docs)
        assert cfg["task"] == "uep_real"

    def test_alternation_longest_id_first(self, tmp_path):
        """多字符选项 id（如 "11"）必须排在其前缀（"1"）之前，否则抽取被短 id 抢先。"""
        item = EvalItem.model_validate(
            {
                "id": "lmx_idx_001",
                "lang": ["en"],
                "task": {
                    "type": "choices",
                    "question": "pick",
                    "options": [{"id": str(i), "text": f"opt{i}"} for i in range(12)],
                },
                "verifiers": [{"type": "choice_match", "answer_ids": ["11"]}],
            }
        )
        cfg, _, _ = _export(tmp_path, [item], name="uep_idx")
        pattern = next(s for s in cfg["filter_list"][0]["filter"] if s["function"] == "regex")[
            "regex_pattern"
        ]
        alternation = pattern.split("(", 1)[1].rsplit(")", 1)[0].split("|")
        assert set(alternation[:2]) == {"10", "11"}, "两位 id 必须整体排在一位 id 之前"
        assert alternation.index("11") < alternation.index("1")
        assert alternation.index("10") < alternation.index("0")


_QA_ZH = EvalItem.model_validate(
    {
        "id": "lmq_zh_001",
        "lang": ["zh-CN"],
        "task": {"type": "qa", "question": "小明有 12 个苹果，又买了 30 个，现在共有几个？"},
        "verifiers": [{"type": "text_match", "expected": "42"}],
    }
)
_QA_EN = EvalItem.model_validate(
    {
        "id": "lmq_en_001",
        "lang": ["en"],
        "task": {"type": "qa", "question": "What is six times seven?"},
        "verifiers": [{"type": "text_match", "expected": "42"}],
    }
)


@pytest.mark.fr("FR-3.4")
class TestLmevalExportQa:
    def test_qa_config_and_docs(self, tmp_path):
        cfg, docs, _ = _export(tmp_path, [_QA_ZH, _QA_EN], name="uep_qa_demo")
        assert cfg["output_type"] == "generate_until"
        regex_step = next(s for s in cfg["filter_list"][0]["filter"] if s["function"] == "regex")
        assert regex_step["group_select"] == -1, "qa 取最后一个匹配（求解式收尾约定）"
        assert cfg["metric_list"][0]["regexes_to_ignore"] == [","]
        zh, en = docs
        assert zh["gold"] == "42" and "只输出最终答案" in zh["prompt"]
        assert "final answer" in en["prompt"]

    def test_mixed_prototypes_rejected(self, tmp_path):
        with pytest.raises(ValueError, match="同质"):
            lmeval.export_task([_ZH, _QA_EN], task_name="uep_mixed", out_dir=tmp_path)

    def test_custom_answer_pattern_respected(self, tmp_path):
        yaml_path = lmeval.export_task(
            [_QA_ZH], task_name="uep_pat", out_dir=tmp_path, answer_pattern=r"(\[[^\]]+\])"
        )
        cfg = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        regex_step = next(s for s in cfg["filter_list"][0]["filter"] if s["function"] == "regex")
        assert regex_step["regex_pattern"] == r"(\[[^\]]+\])"

    def test_real_qa_slice_exports(self, tmp_path):
        items = gsm8k.import_rows(load_slice("gsm8k"))[:10]
        cfg, docs, _ = _export(tmp_path, items, name="uep_qa_real")
        assert len(docs) == 10
        assert all(doc["gold"].replace(",", "").lstrip("-").isdigit() for doc in docs)

    def test_trajectory_carries_system_instruction_into_prompt(self, tmp_path):
        """trajectory 在场时是完整题面：system 作答约定必须进 prompt（不丢语义）。"""
        item = EvalItem.model_validate(
            {
                "id": "lmq_traj_001",
                "lang": ["zh"],
                "task": {"type": "qa", "question": "谜面正文"},
                "trajectory": [
                    {"role": "system", "content": "把最终答案用方括号括起来。"},
                    {"role": "user", "content": "谜面正文"},
                ],
                "verifiers": [{"type": "text_match", "expected": "[喜]"}],
            }
        )
        _, docs, _ = _export(tmp_path, [item], name="uep_traj")
        assert "方括号" in docs[0]["prompt"]
        assert "谜面正文" in docs[0]["prompt"]

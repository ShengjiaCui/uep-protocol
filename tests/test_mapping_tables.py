"""声明式映射表机制（FR-3.1，SPEC §7）——模型、受限算子引擎、哈希、注册表。

映射表 = table（规范字段←源字段的纯拷贝）+ transforms（封闭算子集）。
本文件只用合成夹具（单元层）；真实切片的逐数据集断言在 FR-3.3 测试中。
"""

import pytest
from pydantic import ValidationError

from uep.adapters import REGISTRY, banned_format_names, load_mapping
from uep.adapters.engine import (
    LoadedMapping,
    MappingApplyError,
    MappingTable,
    apply_mapping,
    invert_mapping,
)
from uep.schema import ChoicesTask, EvalItem

#: 合成映射——不指向任何真实数据集（单元层夹具，中文内容）
SYNTH_MAPPING = {
    "format": "synthetic:unit",
    "version": "1.0.0",
    "table": {"task.question": "q", "metadata.topic": "topic"},
    "transforms": [
        {"op": "const", "target": "task.type", "value": "choices"},
        {"op": "const", "target": "lang", "value": ["zh-CN"]},
        {"op": "format_id", "template": "synth-{row_idx:03d}"},
        {"op": "options_from_texts", "source": "opts", "id_style": "letters"},
        {"op": "choice_match_from_index", "source": "gold", "id_style": "letters"},
    ],
}
ROW = {"q": "水的化学式是什么？", "topic": "化学", "opts": ["H2O", "CO2", "O2"], "gold": 0}


def _loaded(mapping_dict: dict) -> LoadedMapping:
    return LoadedMapping.from_dict(mapping_dict, name="synthetic.yaml")


@pytest.mark.fr("FR-3.1")
class TestMappingTableModel:
    def test_minimal_table_valid(self):
        table = MappingTable(format="synthetic:min", version="1.0.0", table={"task.question": "q"})
        assert table.roundtrip_exempt == []
        assert table.changelog == []

    def test_unknown_op_rejected(self):
        bad = dict(SYNTH_MAPPING, transforms=[{"op": "exec", "code": "rm -rf /"}])
        with pytest.raises(ValidationError):
            MappingTable.model_validate(bad)

    def test_transform_extra_key_rejected(self):
        bad = dict(
            SYNTH_MAPPING,
            transforms=[{"op": "const", "target": "lang", "value": ["en"], "hack": 1}],
        )
        with pytest.raises(ValidationError):
            MappingTable.model_validate(bad)

    def test_missing_version_rejected(self):
        bad = {k: v for k, v in SYNTH_MAPPING.items() if k != "version"}
        with pytest.raises(ValidationError):
            MappingTable.model_validate(bad)

    def test_covered_source_fields(self):
        table = MappingTable.model_validate(SYNTH_MAPPING)
        assert table.covered_source_fields() == {"q", "topic", "opts", "gold"}


@pytest.mark.fr("FR-3.1")
class TestEngineApply:
    def test_apply_produces_valid_choices_item(self):
        (item,) = apply_mapping([ROW], _loaded(SYNTH_MAPPING), dataset="synthetic", adapter="unit")
        assert isinstance(item, EvalItem)
        assert isinstance(item.task, ChoicesTask)
        assert item.id == "synth-000"
        assert item.lang == ["zh-CN"]
        assert item.task.question == "水的化学式是什么？"
        assert [(o.id, o.text) for o in item.task.options] == [
            ("A", "H2O"),
            ("B", "CO2"),
            ("C", "O2"),
        ]
        assert item.verifiers[0].answer_ids == ["A"]
        assert item.metadata["topic"] == "化学"

    def test_provenance_stamped(self):
        loaded = _loaded(SYNTH_MAPPING)
        (item,) = apply_mapping([ROW], loaded, dataset="synthetic", adapter="unit")
        assert item.source is not None
        assert item.source.dataset == "synthetic"
        assert item.source.adapter == "unit"
        assert item.source.mapping_table == "synthetic.yaml"
        assert item.source.mapping_hash == f"sha256:{loaded.sha256}"
        assert item.source.converted_at  # ISO 日期，非空即可（格式由 Provenance 模型管）

    def test_missing_source_field_fails_loud(self):
        row = {k: v for k, v in ROW.items() if k != "gold"}
        with pytest.raises(MappingApplyError, match="gold"):
            apply_mapping([row], _loaded(SYNTH_MAPPING), dataset="synthetic", adapter="unit")

    def test_invert_restores_source_row(self):
        """还原义务（SPEC §7.4）：同一张表机械反演，恢复全部源字段。"""
        loaded = _loaded(SYNTH_MAPPING)
        items = apply_mapping([ROW], loaded, dataset="synthetic", adapter="unit")
        (restored,) = invert_mapping(items, loaded)
        assert restored == ROW


@pytest.mark.fr("FR-3.1")
class TestNewOperators:
    """扩展算子（接入主流数据集时实证归纳）：独立列选项 / one-hot 答案 / 后缀切分。"""

    def test_options_from_fields_apply_and_invert(self):
        mapping = {
            "format": "synthetic:fields",
            "version": "1.0.0",
            "table": {"task.question": "q"},
            "transforms": [
                {"op": "const", "target": "task.type", "value": "choices"},
                {"op": "const", "target": "lang", "value": ["zh-CN"]},
                {"op": "format_id", "template": "f-{row_idx}"},
                {"op": "options_from_fields", "sources": ["A", "B"]},
                {"op": "choice_match_from_label", "source": "gold"},
            ],
        }
        row = {"q": "下列哪项正确？", "A": "甲说法", "B": "乙说法", "gold": "B"}
        loaded = _loaded(mapping)
        (item,) = apply_mapping([row], loaded, dataset="s", adapter="u")
        assert [(o.id, o.text) for o in item.task.options] == [("A", "甲说法"), ("B", "乙说法")]
        assert item.verifiers[0].answer_ids == ["B"]
        (back,) = invert_mapping([item], loaded)
        assert back == row

    def test_options_from_fields_letters_id_style(self):
        """id_style=letters：非字母字段名（opa/opb…）→ 位置字母 A/B/C，配 index 答案；
        invert 按位置还原到源字段（MedMCQA 形态：选项分离列 + cop 索引正解）。"""
        mapping = {
            "format": "synthetic:fields-letters",
            "version": "1.0.0",
            "table": {"task.question": "q"},
            "transforms": [
                {"op": "const", "target": "task.type", "value": "choices"},
                {"op": "const", "target": "lang", "value": ["en"]},
                {"op": "format_id", "template": "fl-{row_idx}"},
                {
                    "op": "options_from_fields",
                    "sources": ["opa", "opb", "opc"],
                    "id_style": "letters",
                },
                {
                    "op": "choice_match_from_index",
                    "source": "cop",
                    "id_style": "letters",
                    "dtype": "int",
                },
            ],
        }
        row = {"q": "pick", "opa": "x", "opb": "y", "opc": "z", "cop": 1}
        loaded = _loaded(mapping)
        (item,) = apply_mapping([row], loaded, dataset="s", adapter="u")
        assert [o.id for o in item.task.options] == ["A", "B", "C"]  # 字母 id，非字段名
        assert item.verifiers[0].answer_ids == ["B"]  # cop=1 → 位置字母 B
        (back,) = invert_mapping([item], loaded)
        assert back == row  # 按位置还原到 opa/opb/opc（id_style 无关）

    def test_choice_match_from_onehot_apply_and_invert(self):
        mapping = {
            "format": "synthetic:onehot",
            "version": "1.0.0",
            "table": {"task.question": "q"},
            "transforms": [
                {"op": "const", "target": "task.type", "value": "choices"},
                {"op": "const", "target": "lang", "value": ["en"]},
                {"op": "format_id", "template": "o-{row_idx}"},
                {"op": "options_from_texts", "source": "opts", "id_style": "index"},
                {"op": "choice_match_from_onehot", "source": "labels"},
            ],
        }
        row = {"q": "pick one", "opts": ["a", "b", "c"], "labels": [0, 1, 0]}
        loaded = _loaded(mapping)
        (item,) = apply_mapping([row], loaded, dataset="s", adapter="u")
        assert item.verifiers[0].answer_ids == ["1"]
        (back,) = invert_mapping([item], loaded)
        assert back == row

    def test_onehot_requires_exactly_one_hot(self):
        mapping = {
            "format": "synthetic:onehot",
            "version": "1.0.0",
            "table": {},
            "transforms": [{"op": "choice_match_from_onehot", "source": "labels"}],
        }
        with pytest.raises(MappingApplyError, match="one-hot"):
            apply_mapping([{"labels": [1, 1, 0]}], _loaded(mapping), dataset="s", adapter="u")

    def test_execution_from_fields_apply_and_invert(self):
        mapping = {
            "format": "synthetic:exec",
            "version": "1.0.0",
            "table": {"id": "tid", "task.prompt": "q", "metadata.solution": "sol"},
            "transforms": [
                {"op": "const", "target": "task.type", "value": "code_generation"},
                {"op": "const", "target": "task.language", "value": "python"},
                {"op": "const", "target": "lang", "value": ["en"]},
                {
                    "op": "execution_from_fields",
                    "source_test_code": "tests",
                    "source_entry_point": "entry",
                    "language": "python",
                    "harness": "exec",
                },
            ],
        }
        row = {
            "tid": "t1",
            "q": "def f(x): ...",
            "sol": "    return x",
            "tests": "def check(candidate):\n    assert candidate(1) == 1\n",
            "entry": "f",
        }
        loaded = _loaded(mapping)
        (item,) = apply_mapping([row], loaded, dataset="s", adapter="u")
        verifier = item.verifiers[0]
        assert verifier.type == "execution"
        assert verifier.tests.test_code == row["tests"]
        assert verifier.tests.entry_point == "f"
        assert verifier.sandbox.network is False  # 沙箱默认值自含
        (back,) = invert_mapping([item], loaded)
        assert back == row

    def test_execution_from_patch_fields_apply_and_invert(self):
        mapping = {
            "format": "synthetic:patch",
            "version": "1.0.0",
            "table": {
                "id": "iid",
                "task.repo": "repo",
                "task.base_commit": "bc",
                "task.problem_statement": "ps",
            },
            "transforms": [
                {"op": "const", "target": "task.type", "value": "patch_repair"},
                {"op": "const", "target": "lang", "value": ["zh-CN"]},
                {
                    "op": "execution_from_patch_fields",
                    "source_test_patch": "tp",
                    "source_fail_to_pass": "f2p",
                    "source_pass_to_pass": "p2p",
                    "language": "python",
                },
            ],
        }
        row = {
            "iid": "p1",
            "repo": "org/repo",
            "bc": "c0ffee",
            "ps": "修复登录空格问题。",
            "tp": "diff --git a/x.py b/x.py\n",
            "f2p": '["t.py::test_a", "t.py::test_b"]',
            "p2p": '["t.py::test_c"]',
        }
        loaded = _loaded(mapping)
        (item,) = apply_mapping([row], loaded, dataset="s", adapter="u")
        verifier = item.verifiers[0]
        assert verifier.tests.fail_to_pass == ["t.py::test_a", "t.py::test_b"]
        assert verifier.tests.pass_to_pass == ["t.py::test_c"]
        assert verifier.tests.harness == "pytest"
        (back,) = invert_mapping([item], loaded)
        assert back == row, "JSON 字符串清单须按源格式字节还原"

    def test_relevance_from_qrels_apply_and_invert(self):
        mapping = {
            "format": "synthetic:retrieval",
            "version": "1.0.0",
            "table": {"id": "_id", "task.query": "text"},
            "transforms": [
                {"op": "const", "target": "task.type", "value": "retrieval"},
                {"op": "const", "target": "lang", "value": ["zh-CN"]},
                {"op": "const", "target": "task.corpus", "value": {"uri": "ref:corpus"}},
                {"op": "relevance_from_qrels", "source": "qrels", "id_dtype": "int"},
            ],
        }
        row = {
            "_id": "7",
            "text": "支流查询",
            "qrels": [
                {"corpus-id": 31715818, "score": 1},
                {"corpus-id": 14717500, "score": 2},
            ],
        }
        loaded = _loaded(mapping)
        (item,) = apply_mapping([row], loaded, dataset="s", adapter="u")
        verifier = item.verifiers[0]
        assert verifier.type == "retrieval"
        assert [(r.doc_id, r.grade) for r in verifier.relevance] == [
            ("31715818", 1),
            ("14717500", 2),
        ]
        assert verifier.metrics == ["ndcg@10"]
        (back,) = invert_mapping([item], loaded)
        assert back == row, "qrels 源形状（int id）须还原"

    def test_text_match_from_split_apply_and_invert(self):
        mapping = {
            "format": "synthetic:split",
            "version": "1.0.0",
            "table": {"task.question": "q", "metadata.solution": "ans"},
            "transforms": [
                {"op": "const", "target": "task.type", "value": "qa"},
                {"op": "const", "target": "lang", "value": ["en"]},
                {"op": "format_id", "template": "s-{row_idx}"},
                {"op": "text_match_from_split", "source": "ans", "separator": "#### "},
            ],
        }
        row = {"q": "1+1=?", "ans": "one plus one is two\n#### 2"}
        loaded = _loaded(mapping)
        (item,) = apply_mapping([row], loaded, dataset="s", adapter="u")
        assert item.verifiers[0].expected == "2"
        assert item.metadata["solution"].endswith("#### 2")
        (back,) = invert_mapping([item], loaded)  # 完整原答案经 metadata 表拷贝还原
        assert back == row


@pytest.mark.fr("FR-3.1")
class TestRegistry:
    def test_choices_adapters_registered(self):
        names = {info.name for info in REGISTRY}
        assert {"mmlu", "arc", "hellaswag", "openai_evals", "lmeval"} <= names

    def test_mapping_files_load_with_stable_hash(self):
        with_tables = [info for info in REGISTRY if info.mapping_file is not None]
        assert len(with_tables) >= 4, "转换适配器必须携带映射表"
        for info in with_tables:
            first = load_mapping(info.name)
            second = load_mapping(info.name)
            assert first.mapping.format, info.name
            assert first.mapping.version.count(".") == 2, "版本须为 semver"
            assert first.sha256 == second.sha256
            assert len(first.sha256) == 64

    def test_banned_names_generated_from_registry(self):
        banned = banned_format_names()
        assert {"mmlu", "arc", "hellaswag"} <= banned
        assert all(name == name.lower() for name in banned)

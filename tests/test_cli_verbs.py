"""七个管理动词（FR-5.1–5.7）——题库查看与组卷。

语义从 JTBD 收敛（行动计划 3.1：不做通用数据框）：
- 只读：list（逐行概览）/ show（单条详情）/ stats（分布统计）；
- 组卷：filter / slice / sample / merge——产物一律是新数据集目录
  （items.jsonl + manifest.json 机械汇总），立即可 validate / export。
"""

import json

import pytest
from test_import_choices_real import load_slice

from uep.cli import main
from uep.dataset_io import read_items
from uep.schema import EvalItem, Manifest

_CSV_ZH = "question,answer\n水的化学式是什么？,H2O\n中国的首都是哪里？,北京\n"


@pytest.fixture()
def zh_items_file(tmp_path):
    """2 条中文 qa（经 convert 动词落盘，id 为 item-0000/item-0001）。"""
    src = tmp_path / "quiz.csv"
    src.write_text(_CSV_ZH, encoding="utf-8")
    out = tmp_path / "zh_ds"
    code = main(
        [
            "convert",
            str(src),
            "--from",
            "csv",
            "-o",
            str(out),
            "--license",
            "unknown",
            "--content-lang",
            "zh-CN",
        ]
    )
    assert code == 0
    return out / "items.jsonl"


@pytest.fixture()
def en_items_file(tmp_path):
    """5 条英文 choices（真实切片前 5 行经 convert 动词落盘）。"""
    rows = load_slice("mmlu")[:5]
    src = tmp_path / "rows.jsonl"
    src.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )
    out = tmp_path / "en_ds"
    assert main(["convert", str(src), "--from", "mmlu", "-o", str(out), "--license", "MIT"]) == 0
    return out / "items.jsonl"


@pytest.fixture()
def mixed_items_file(zh_items_file, en_items_file, tmp_path):
    """7 条双语混合库（merge 产物——fixture 本身即 FR-5.6 的正路径）。"""
    out = tmp_path / "mixed"
    code = main(
        [
            "merge",
            str(zh_items_file),
            str(en_items_file),
            "-o",
            str(out),
            "--name",
            "mixed",
            "--license",
            "unknown",
        ]
    )
    assert code == 0
    return out / "items.jsonl"


@pytest.mark.fr("FR-5.1")
class TestList:
    def test_one_line_per_item_with_id_type_lang_and_gist(self, zh_items_file, capsys):
        assert main(["list", str(zh_items_file)]) == 0
        lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
        assert len(lines) == 3, "2 条目行 + 1 汇总行"
        assert "item-0000" in lines[0]
        assert "qa" in lines[0]
        assert "zh-CN" in lines[0]
        assert "水的化学式" in lines[0]
        assert "共 2 条" in lines[-1]

    def test_missing_file_is_usage_error(self, tmp_path, capsys):
        assert main(["list", str(tmp_path / "nope.jsonl")]) == 2
        assert "不存在" in capsys.readouterr().err


@pytest.mark.fr("FR-5.2")
class TestShow:
    def test_prints_full_item_as_roundtrippable_json(self, zh_items_file, capsys):
        assert main(["show", str(zh_items_file), "item-0001"]) == 0
        item = EvalItem.model_validate_json(capsys.readouterr().out)
        assert item.task.question == "中国的首都是哪里？"
        assert item.verifiers[0].expected == "北京"

    def test_unknown_id_fails_bilingually(self, zh_items_file, capsys):
        assert main(["show", str(zh_items_file), "ghost"]) == 1
        assert "未找到条目" in capsys.readouterr().err
        assert main(["show", str(zh_items_file), "ghost", "--lang", "en"]) == 1
        assert "not found" in capsys.readouterr().err


@pytest.mark.fr("FR-5.3")
class TestFilter:
    def test_by_task_type_writes_validatable_dataset(self, mixed_items_file, tmp_path):
        out = tmp_path / "only_qa"
        assert main(["filter", str(mixed_items_file), "-o", str(out), "--type", "qa"]) == 0
        manifest = Manifest.model_validate_json((out / "manifest.json").read_text(encoding="utf-8"))
        assert manifest.task_types == {"qa": 2}
        assert manifest.languages == ["zh-CN"]
        assert main(["validate", str(out / "items.jsonl")]) == 0

    def test_task_lang_uses_bcp47_prefix_matching(self, mixed_items_file, tmp_path):
        out = tmp_path / "zh_only"
        assert main(["filter", str(mixed_items_file), "-o", str(out), "--task-lang", "zh"]) == 0
        items = read_items(out / "items.jsonl")
        assert len(items) == 2, "--task-lang zh 须命中 zh-CN（RFC 4647 前缀匹配）"
        assert all(item.lang == ["zh-CN"] for item in items)

    def test_predicates_combine_with_and(self, mixed_items_file, tmp_path):
        out = tmp_path / "en_choices"
        code = main(
            [
                "filter",
                str(mixed_items_file),
                "-o",
                str(out),
                "--type",
                "choices",
                "--task-lang",
                "en",
            ]
        )
        assert code == 0
        assert len(read_items(out / "items.jsonl")) == 5

    def test_no_predicate_is_usage_error(self, mixed_items_file, tmp_path, capsys):
        assert main(["filter", str(mixed_items_file), "-o", str(tmp_path / "x")]) == 2
        assert "筛选条件" in capsys.readouterr().err

    def test_empty_result_refuses_to_write(self, mixed_items_file, tmp_path, capsys):
        out = tmp_path / "none"
        assert main(["filter", str(mixed_items_file), "-o", str(out), "--type", "retrieval"]) == 1
        assert "为空" in capsys.readouterr().err
        assert not (out / "items.jsonl").exists()


@pytest.mark.fr("FR-5.4")
class TestSlice:
    def test_half_open_range_preserves_order(self, en_items_file, tmp_path):
        source_ids = [item.id for item in read_items(en_items_file)]
        out = tmp_path / "sl"
        assert main(["slice", str(en_items_file), "-o", str(out), "--range", "1:3"]) == 0
        assert [item.id for item in read_items(out / "items.jsonl")] == source_ids[1:3]

    def test_stop_beyond_end_is_tolerated(self, en_items_file, tmp_path):
        out = tmp_path / "tail"
        assert main(["slice", str(en_items_file), "-o", str(out), "--range", "3:99"]) == 0
        assert len(read_items(out / "items.jsonl")) == 2

    def test_malformed_range_is_usage_error(self, en_items_file, tmp_path, capsys):
        for bad in ("3", "abc:1", "3:1"):
            code = main(["slice", str(en_items_file), "-o", str(tmp_path / "x"), "--range", bad])
            assert code == 2
        assert "START:STOP" in capsys.readouterr().err


@pytest.mark.fr("FR-5.5")
class TestSample:
    def test_same_seed_reproduces_same_subsequence(self, en_items_file, tmp_path):
        out_a, out_b = tmp_path / "a", tmp_path / "b"
        assert (
            main(["sample", str(en_items_file), "-o", str(out_a), "--n", "3", "--seed", "7"]) == 0
        )
        assert (
            main(["sample", str(en_items_file), "-o", str(out_b), "--n", "3", "--seed", "7"]) == 0
        )
        ids_a = [item.id for item in read_items(out_a / "items.jsonl")]
        ids_b = [item.id for item in read_items(out_b / "items.jsonl")]
        assert ids_a == ids_b, "同 seed 必须逐条复现"
        source_ids = [item.id for item in read_items(en_items_file)]
        picked = set(ids_a)
        assert [item_id for item_id in source_ids if item_id in picked] == ids_a, "抽样保持原库顺序"

    def test_seed_is_reported_for_provenance(self, en_items_file, tmp_path, capsys):
        assert main(["sample", str(en_items_file), "-o", str(tmp_path / "s"), "--n", "2"]) == 0
        assert "seed=0" in capsys.readouterr().out

    def test_oversample_fails(self, en_items_file, tmp_path, capsys):
        assert main(["sample", str(en_items_file), "-o", str(tmp_path / "x"), "--n", "99"]) == 1
        assert "超过" in capsys.readouterr().err


@pytest.mark.fr("FR-5.6")
class TestMerge:
    def test_manifest_aggregates_both_sources(self, mixed_items_file):
        manifest_path = mixed_items_file.parent / "manifest.json"
        manifest = Manifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        assert manifest.size == 7
        assert manifest.task_types == {"choices": 5, "qa": 2}
        assert manifest.languages == ["en", "zh-CN"]
        assert main(["validate", str(mixed_items_file)]) == 0

    def test_id_conflict_fails_loudly_without_writing(self, zh_items_file, tmp_path, capsys):
        out = tmp_path / "dup"
        assert main(["merge", str(zh_items_file), str(zh_items_file), "-o", str(out)]) == 1
        err = capsys.readouterr().err
        assert "item-0000" in err, "冲突清单必须点名"
        assert not (out / "items.jsonl").exists(), "冲突时绝不落盘"

    def test_single_input_is_usage_error(self, zh_items_file, tmp_path, capsys):
        assert main(["merge", str(zh_items_file), "-o", str(tmp_path / "x")]) == 2
        assert "至少" in capsys.readouterr().err


@pytest.mark.fr("FR-5.7")
class TestStats:
    def test_reports_size_and_three_distributions(self, mixed_items_file, capsys):
        assert main(["stats", str(mixed_items_file)]) == 0
        out = capsys.readouterr().out
        assert "7" in out
        assert "choices=5" in out and "qa=2" in out
        assert "en=5" in out and "zh-CN=2" in out
        assert "choice_match=5" in out and "text_match=2" in out

    def test_labels_switch_to_english(self, mixed_items_file, capsys):
        assert main(["stats", str(mixed_items_file), "--lang", "en"]) == 0
        out = capsys.readouterr().out
        assert "items" in out
        assert "task types" in out

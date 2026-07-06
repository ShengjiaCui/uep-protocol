"""``uep conform``（FR-6.2）——一致性工具包：给"新建 benchmark 参考我们"的创建者自查。

三层检查：schema 合法（读入即校验）/ 试金石可消费（打分意图对标准消费者自明）/
manifest 与条目机械一致。custom 原型属受控逃生舱，计数跳过、不判失败；
清单缺失=跳过并提示（items.jsonl 单独分发是合法形态）。
"""

import json

import pytest

from uep.cli import main

_CSV_ZH = "question,answer\n水的化学式是什么？,H2O\n中国的首都是哪里？,北京\n"


def _make_dataset(tmp_path):
    src = tmp_path / "quiz.csv"
    src.write_text(_CSV_ZH, encoding="utf-8")
    out = tmp_path / "ds"
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
    return out


def _write_items(tmp_path, *items):
    path = tmp_path / "items.jsonl"
    path.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in items), encoding="utf-8"
    )
    return path


@pytest.mark.fr("FR-6.2")
class TestConform:
    def test_good_dataset_passes_all_checks(self, tmp_path, capsys):
        out = _make_dataset(tmp_path)
        assert main(["conform", str(out / "items.jsonl")]) == 0
        text = capsys.readouterr().out
        assert "schema" in text
        assert "试金石" in text
        assert "清单" in text
        assert "✗" not in text

    def test_touchstone_failure_names_item_and_fails(self, tmp_path, capsys):
        # schema 合法但打分意图对标准消费者不自明（qa 无 text_match）
        path = _write_items(
            tmp_path,
            {
                "id": "odd-001",
                "lang": ["zh-CN"],
                "task": {"type": "qa", "question": "今天星期几？"},
                "verifiers": [{"type": "regex", "pattern": "星期."}],
            },
        )
        assert main(["conform", str(path)]) == 1
        assert "odd-001" in capsys.readouterr().err

    def test_manifest_mismatch_fails(self, tmp_path, capsys):
        out = _make_dataset(tmp_path)
        manifest_path = out / "manifest.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        data["size"] = 3
        data["task_types"] = {"qa": 3}
        manifest_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        assert main(["conform", str(out / "items.jsonl")]) == 1
        err = capsys.readouterr().err
        assert "size" in err

    def test_missing_manifest_skips_with_note(self, tmp_path, capsys):
        out = _make_dataset(tmp_path)
        (out / "manifest.json").unlink()
        assert main(["conform", str(out / "items.jsonl")]) == 0
        assert "跳过" in capsys.readouterr().out

    def test_custom_items_skipped_not_failed(self, tmp_path, capsys):
        path = _write_items(
            tmp_path,
            {
                "id": "c-1",
                "lang": ["zh-CN"],
                "task": {"type": "custom", "schema_ref": "proposal-001", "payload": {"k": 1}},
                "verifiers": [{"type": "regex", "pattern": "ok"}],
            },
        )
        assert main(["conform", str(path)]) == 0
        assert "custom" in capsys.readouterr().out

    def test_labels_switch_to_english(self, tmp_path, capsys):
        out = _make_dataset(tmp_path)
        assert main(["conform", str(out / "items.jsonl"), "--lang", "en"]) == 0
        text = capsys.readouterr().out
        assert "touchstone" in text
        assert "conformance passed" in text

    def test_bad_items_file_is_schema_failure(self, tmp_path, capsys):
        path = tmp_path / "items.jsonl"
        path.write_text('{"id": "x"}\n', encoding="utf-8")
        assert main(["conform", str(path)]) == 1
        assert "校验失败" in capsys.readouterr().err

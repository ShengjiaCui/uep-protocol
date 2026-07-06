"""``uep convert``（FR-5.9）——源格式 → items.jsonl + manifest.json 落盘。

任务 #8 缺口的兑现：适配器从库级 API 升为用户可用动词（测试规格书 §⑤ 前提）。
"""

import json

import pytest
from test_import_choices_real import load_slice

from uep.cli import main
from uep.dataset_io import read_items
from uep.schema import Manifest

_CSV_ZH = "question,answer\n水的化学式是什么？,H2O\n中国的首都是哪里？,北京\n"


def _write_csv(tmp_path):
    src = tmp_path / "quiz.csv"
    src.write_text(_CSV_ZH, encoding="utf-8")
    return src


@pytest.mark.fr("FR-5.9")
class TestConvertCsv:
    def test_csv_to_dataset_dir(self, tmp_path):
        out = tmp_path / "ds"
        code = main(
            [
                "convert",
                str(_write_csv(tmp_path)),
                "--from",
                "csv",
                "-o",
                str(out),
                "--name",
                "quiz",
                "--license",
                "unknown",
                "--content-lang",
                "zh-CN",
            ]
        )
        assert code == 0
        items = read_items(out / "items.jsonl")
        assert len(items) == 2
        assert items[0].task.question == "水的化学式是什么？"
        assert items[0].verifiers[0].expected == "H2O"
        assert items[1].verifiers[0].expected == "北京"
        manifest = Manifest.model_validate_json((out / "manifest.json").read_text(encoding="utf-8"))
        assert manifest.size == 2
        assert manifest.task_types == {"qa": 2}
        assert manifest.languages == ["zh-CN"]
        assert manifest.license == "unknown"
        assert manifest.contains_pii is None, "未给 --contains-pii 时须保持未声明"

    def test_contains_pii_flag_reaches_manifest(self, tmp_path):
        out = tmp_path / "ds_pii"
        code = main(
            [
                "convert",
                str(_write_csv(tmp_path)),
                "--from",
                "csv",
                "-o",
                str(out),
                "--license",
                "unknown",
                "--content-lang",
                "zh-CN",
                "--contains-pii",
                "false",
            ]
        )
        assert code == 0
        manifest = Manifest.model_validate_json((out / "manifest.json").read_text(encoding="utf-8"))
        assert manifest.contains_pii is False

    def test_converted_dataset_passes_validate_verb(self, tmp_path):
        out = tmp_path / "ds"
        assert (
            main(
                [
                    "convert",
                    str(_write_csv(tmp_path)),
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
            == 0
        )
        assert main(["validate", str(out / "items.jsonl")]) == 0
        assert main(["validate", str(out / "manifest.json")]) == 0

    def test_unknown_format_rejected_bilingually(self, tmp_path, capsys):
        src = _write_csv(tmp_path)
        assert main(["convert", str(src), "--from", "nope", "-o", str(tmp_path / "x")]) == 2
        assert "未知源格式" in capsys.readouterr().err
        assert (
            main(["convert", str(src), "--from", "nope", "-o", str(tmp_path / "x"), "--lang", "en"])
            == 2
        )
        assert "unknown source format" in capsys.readouterr().err


@pytest.mark.fr("FR-5.9")
def test_registry_format_rows_to_dataset(tmp_path):
    """注册表格式（源行 JSONL）→ 落盘：真实切片前 5 行经同一动词走通。"""
    rows = load_slice("mmlu")[:5]
    src = tmp_path / "rows.jsonl"
    src.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8"
    )
    out = tmp_path / "ds"
    code = main(
        ["convert", str(src), "--from", "mmlu", "-o", str(out), "--name", "m5", "--license", "MIT"]
    )
    assert code == 0
    manifest = Manifest.model_validate_json((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest.task_types == {"choices": 5}
    assert manifest.languages == ["en"]
    items = read_items(out / "items.jsonl")
    assert items[0].source is not None, "溯源戳须随落盘保留"

"""``uep export``（FR-5.10）——items.jsonl → Runner 任务包（五分钟路径后半程）。"""

import json

import pytest
import yaml

from uep.cli import main

_CSV_ZH = "question,answer\n六乘七等于多少？,42\n十减三等于多少？,7\n"


@pytest.fixture()
def qa_dataset(tmp_path):
    src = tmp_path / "quiz.csv"
    src.write_text(_CSV_ZH, encoding="utf-8")
    out = tmp_path / "ds"
    assert (
        main(
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
        == 0
    )
    return out / "items.jsonl"


@pytest.mark.fr("FR-5.10")
class TestExportVerb:
    def test_export_lmeval_task_package(self, qa_dataset, tmp_path):
        out = tmp_path / "pkg"
        code = main(
            ["export", str(qa_dataset), "--to", "lmeval", "-o", str(out), "--task-name", "uep_quiz"]
        )
        assert code == 0
        cfg = yaml.safe_load((out / "uep_quiz.yaml").read_text(encoding="utf-8"))
        assert cfg["task"] == "uep_quiz"
        docs = [
            json.loads(line)
            for line in (out / "uep_quiz.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        assert len(docs) == 2 and docs[0]["gold"] == "42"

    def test_export_inspect_samples(self, qa_dataset, tmp_path):
        out = tmp_path / "ins"
        code = main(
            [
                "export",
                str(qa_dataset),
                "--to",
                "inspect_ai",
                "-o",
                str(out),
                "--task-name",
                "uep_quiz",
            ]
        )
        assert code == 0
        samples = [
            json.loads(line)
            for line in (out / "uep_quiz.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        assert samples[0]["target"] == "42"
        assert "六乘七" in samples[0]["input"]

    def test_two_runner_exports_from_same_dataset(self, qa_dataset, tmp_path):
        """五分钟协议的硬指标：同一数据集导出两种 Runner 格式（§⑤）。"""
        assert main(["export", str(qa_dataset), "--to", "lmeval", "-o", str(tmp_path / "a")]) == 0
        assert (
            main(["export", str(qa_dataset), "--to", "inspect_ai", "-o", str(tmp_path / "b")]) == 0
        )

    def test_unknown_target_rejected_bilingually(self, qa_dataset, tmp_path, capsys):
        assert main(["export", str(qa_dataset), "--to", "nope", "-o", str(tmp_path / "x")]) == 2
        assert "未知导出目标" in capsys.readouterr().err

    def test_invalid_items_file_rejected(self, tmp_path, capsys):
        bad = tmp_path / "bad.jsonl"
        bad.write_text('{"id": "x"}\n', encoding="utf-8")
        assert main(["export", str(bad), "--to", "lmeval", "-o", str(tmp_path / "x")]) == 1

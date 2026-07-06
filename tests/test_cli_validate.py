"""`uep validate` CLI（FR-4.1）——行/字段级报错、zh/en 双语、Manifest 分流。"""

import json

import pytest

from uep.cli import main

VALID_ITEM = {
    "id": "cli_001",
    "lang": ["zh-CN"],
    "task": {"type": "qa", "question": "天空通常是什么颜色？"},
    "verifiers": [{"type": "text_match", "expected": "蓝色"}],
}


def _jsonl(tmp_path, name, records):
    path = tmp_path / name
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records), encoding="utf-8")
    return path


@pytest.mark.fr("FR-4.1")
class TestCliValidate:
    def test_valid_file_passes(self, tmp_path, capsys):
        path = _jsonl(tmp_path, "items.jsonl", [VALID_ITEM])
        assert main(["validate", str(path)]) == 0
        assert "校验通过" in capsys.readouterr().out

    def test_error_reports_line_and_field_zh(self, tmp_path, capsys):
        broken = {**VALID_ITEM, "verifiers": []}
        path = _jsonl(tmp_path, "items.jsonl", [VALID_ITEM, broken])
        assert main(["validate", str(path)]) == 1
        err = capsys.readouterr().err
        assert "第 2 行" in err
        assert "verifiers" in err

    def test_error_reports_line_and_field_en(self, tmp_path, capsys):
        broken = {**VALID_ITEM, "verifiers": []}
        path = _jsonl(tmp_path, "items.jsonl", [broken])
        assert main(["validate", str(path), "--lang", "en"]) == 1
        err = capsys.readouterr().err
        assert "line 1" in err
        assert "verifiers" in err

    def test_manifest_path_routed_to_manifest_validation(self, tmp_path, capsys):
        manifest = {"name": "demo", "license": "unknown", "languages": ["en"], "size": 0}
        path = tmp_path / "manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        assert main(["validate", str(path)]) == 0

    def test_missing_file_returns_usage_error(self, tmp_path):
        assert main(["validate", str(tmp_path / "nope.jsonl")]) == 2

    def test_extras_warning_does_not_fail(self, tmp_path, capsys):
        noisy = {**VALID_ITEM, "extras": {"question": "泄漏的本体数据"}}
        path = _jsonl(tmp_path, "items.jsonl", [noisy])
        assert main(["validate", str(path)]) == 0
        assert "extras.question" in capsys.readouterr().out

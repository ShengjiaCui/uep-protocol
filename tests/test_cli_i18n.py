"""FR-5.8：CLI 双语（zh/en）——目录机械平权 + 语言解析优先级 + 动词行为抽查。

平权靠机制不靠自觉：MESSAGES 每键必须 zh/en 齐备且占位符集合一致，
漏译或占位符笔误在 CI 当场红（与禁名 lint 同一哲学）。
"""

import string

import pytest

from uep.cli import main
from uep.i18n import MESSAGES, resolve_lang


def _placeholders(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


@pytest.mark.fr("FR-5.8")
class TestCatalogParity:
    def test_every_key_has_nonempty_zh_and_en(self):
        for key, entry in MESSAGES.items():
            assert set(entry) == {"zh", "en"}, f"{key} 语言不齐"
            assert entry["zh"].strip() and entry["en"].strip(), f"{key} 有空文案"

    def test_placeholders_match_across_languages(self):
        for key, entry in MESSAGES.items():
            assert _placeholders(entry["zh"]) == _placeholders(
                entry["en"]
            ), f"{key} 两语占位符不一致"

    def test_validate_texts_live_in_catalog(self):
        """validate 的存量文案必须并入目录（双语收口，不留私仓）。"""
        assert "validate.ok" in MESSAGES
        assert "validate.summary" in MESSAGES


@pytest.mark.fr("FR-5.8")
class TestLangResolution:
    def test_default_is_zh(self, monkeypatch):
        monkeypatch.delenv("UEP_LANG", raising=False)
        assert resolve_lang(None) == "zh"

    def test_env_var_switches_default(self, monkeypatch):
        monkeypatch.setenv("UEP_LANG", "en")
        assert resolve_lang(None) == "en"

    def test_flag_beats_env(self, monkeypatch):
        monkeypatch.setenv("UEP_LANG", "en")
        assert resolve_lang("zh") == "zh"

    def test_unknown_value_falls_back_to_zh(self, monkeypatch):
        monkeypatch.delenv("UEP_LANG", raising=False)
        assert resolve_lang("fr") == "zh"


@pytest.mark.fr("FR-5.8")
class TestValidateVerbBilingual:
    def test_success_line_switches_language(self, tmp_path, capsys, monkeypatch):
        monkeypatch.delenv("UEP_LANG", raising=False)
        src = tmp_path / "q.csv"
        src.write_text("question,answer\n天空是什么颜色？,蓝色\n", encoding="utf-8")
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
        capsys.readouterr()
        assert main(["validate", str(out / "items.jsonl")]) == 0
        assert "校验通过" in capsys.readouterr().out
        assert main(["validate", str(out / "items.jsonl"), "--lang", "en"]) == 0
        assert "validation passed" in capsys.readouterr().out

    def test_missing_file_error_switches_language(self, tmp_path, capsys):
        assert main(["validate", str(tmp_path / "nope.jsonl")]) == 2
        assert "文件不存在" in capsys.readouterr().err
        assert main(["validate", str(tmp_path / "nope.jsonl"), "--lang", "en"]) == 2
        assert "file not found" in capsys.readouterr().err

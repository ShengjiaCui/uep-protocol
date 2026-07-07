from pathlib import Path

import pytest

from scripts.crossrunner_compare import parse_inspect_log, parse_lmeval_samples

FIX = Path(__file__).parent / "fixtures" / "crossrunner"


class TestParseLmevalSamples:
    def test_maps_uep_id_to_correctness(self):
        result = parse_lmeval_samples(FIX / "lmeval_samples.jsonl")
        assert result == {"mmlu-test-0000": True, "mmlu-test-0001": False}

    def test_accepts_str_path(self):
        result = parse_lmeval_samples(str(FIX / "lmeval_samples.jsonl"))
        assert result == {"mmlu-test-0000": True, "mmlu-test-0001": False}


class TestParseInspectLog:
    def test_maps_uep_id_to_correctness(self):
        result = parse_inspect_log(FIX / "inspect_log.json")
        assert result == {"mmlu-test-0000": True, "mmlu-test-0001": False}

    def test_empty_samples_returns_empty(self, tmp_path):
        log = tmp_path / "empty.json"
        log.write_text('{"samples": []}', encoding="utf-8")
        assert parse_inspect_log(log) == {}

    def test_errored_sample_null_scores_raises(self, tmp_path):
        # inspect 日志 schema 允许实跑报错样本 scores=null；对分须 fail-loud 而非崩溃/静默
        log = tmp_path / "errored.json"
        log.write_text('{"samples": [{"id": "x", "scores": null}]}', encoding="utf-8")
        with pytest.raises(ValueError):
            parse_inspect_log(log)

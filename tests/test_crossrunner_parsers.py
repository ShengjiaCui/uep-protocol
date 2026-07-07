from pathlib import Path

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

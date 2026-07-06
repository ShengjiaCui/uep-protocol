"""OpenAI Evals 双向往返（FR-3.2，关卡 2）——真实切片 ≥100 条逐条语义等价。

X →import→ UEP →export→ X'，等价判定按测试规格书 §② 规程
（键序无关、数组顺序有关、NFC、数值按值、缺失≠null、豁免须声明）。
切片为真实中文数据——双语平权（P5）直接在真实中文上受检。
"""

import hashlib
import json
import unicodedata
from pathlib import Path

import pytest

from uep.adapters import openai_evals
from uep.equivalence import diff_paths, normalize_tree, semantically_equal
from uep.schema import QaTask

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "scripts" / "slices.lock.json"
SLICE_PATH = ROOT / "data" / "real" / "openai_evals.jsonl"
DATASET = "openai/evals:Chinese_character_riddles"


def load_rows() -> list[dict]:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))["openai_evals"]
    assert SLICE_PATH.exists(), "缺切片——先运行: .venv/bin/python scripts/fetch_slices.py"
    raw = SLICE_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == lock["sha256"], "切片与锁不符，重新获取"
    return openai_evals.read_samples(raw.decode("utf-8"))


def _has_cjk(text: str) -> bool:
    return any("一" <= ch <= "鿿" for ch in text)


@pytest.mark.fr("FR-3.2")
class TestRealSliceRoundtrip:
    def test_import_produces_valid_qa_items(self):
        rows = load_rows()
        assert len(rows) >= 100, "往返测试须 ≥100 条真实切片（测试规格书 §②）"
        items = openai_evals.import_rows(rows, dataset=DATASET, lang=["zh"])
        assert len(items) == len(rows)
        for row, item in zip(rows, items, strict=True):
            assert isinstance(item.task, QaTask)
            assert item.trajectory is not None and len(item.trajectory) == len(row["input"])
            assert item.task.question == unicodedata.normalize("NFC", row["input"][-1]["content"])
        assert any(_has_cjk(item.task.question) for item in items), "真实中文内容应在场"

    def test_roundtrip_semantically_equal_per_item(self):
        """逐条等价；失败输出条目 id + 字段路径级 diff（规程要求的失败形态）。"""
        rows = load_rows()
        items = openai_evals.import_rows(rows, dataset=DATASET, lang=["zh"])
        restored = openai_evals.export_rows(items)
        for row, item, back in zip(rows, items, restored, strict=True):
            diffs = diff_paths(normalize_tree(row), normalize_tree(back))
            assert not diffs, f"{item.id} 往返不等价:\n" + "\n".join(diffs[:8])

    def test_reexported_jsonl_reparses_identically(self):
        """导出物写为规范 JSONL 后重读，与导出树等价（序列化不引入漂移）。"""
        rows = load_rows()
        restored = openai_evals.export_rows(
            openai_evals.import_rows(rows, dataset=DATASET, lang=["zh"])
        )
        reparsed = openai_evals.read_samples(openai_evals.dump_samples(restored))
        assert reparsed == restored


@pytest.mark.fr("FR-3.2")
class TestEquivalenceProcedure:
    """规程本身的行为合同（测试规格书 §② 判定表，合成用例）。"""

    def test_key_order_irrelevant(self):
        assert semantically_equal({"a": 1, "b": 2}, {"b": 2, "a": 1})

    def test_array_order_significant(self):
        assert not semantically_equal({"x": [1, 2]}, {"x": [2, 1]})

    def test_strings_compare_after_nfc(self):
        nfd = unicodedata.normalize("NFD", "café谜底")
        assert semantically_equal({"s": nfd}, {"s": "café谜底"})

    def test_numbers_compare_by_value(self):
        assert semantically_equal({"n": 1}, {"n": 1.0})

    def test_missing_key_not_equal_to_null(self):
        assert not semantically_equal({"a": None}, {})
        diffs = diff_paths(normalize_tree({"a": None}), normalize_tree({}))
        assert any("仅左侧存在" in d for d in diffs)

    def test_exemption_only_when_declared(self):
        left, right = {"q": "谜面", "debug": 1}, {"q": "谜面", "debug": 2}
        assert not semantically_equal(left, right)
        assert semantically_equal(left, right, exempt=frozenset({"debug"}))

    def test_diff_reports_field_path(self):
        left = {"input": [{"role": "user", "content": "甲"}]}
        right = {"input": [{"role": "user", "content": "乙"}]}
        diffs = diff_paths(normalize_tree(left), normalize_tree(right))
        assert diffs and diffs[0].startswith("input[0].content:")

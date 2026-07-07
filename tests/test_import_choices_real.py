"""真实切片导入（FR-3.3）——三个 choices 数据集各 100 条全量过协议 + 无损反演。

切片由 ``scripts/fetch_slices.py`` 获取并以 sha256 锁定（数据本体不入库）；
文件缺失即**失败**并提示获取命令——按测试规格书 §⑦，FR 验收测试不允许 skip。
"""

import hashlib
import json
from pathlib import Path

import pytest

from uep.adapters import (
    arc,
    ceval,
    commonsense_qa,
    gsm8k,
    hellaswag,
    hendrycks_math,
    load_mapping,
    medmcqa,
    mmlu,
    mmlu_pro,
    svamp,
    truthful_qa,
)
from uep.equivalence import diff_paths, normalize_tree
from uep.schema import ChoicesTask, QaTask

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "real"
LOCK_PATH = ROOT / "scripts" / "slices.lock.json"
FETCH_HINT = "先运行: .venv/bin/python scripts/fetch_slices.py"


def load_slice(name: str) -> list[dict]:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    path = DATA_DIR / f"{name}.jsonl"
    assert path.exists(), f"缺真实切片 {path.name}——{FETCH_HINT}"
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == lock[name]["sha256"], f"{name} 切片与锁不符（数据被改动？）——{FETCH_HINT}"
    return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]


ADAPTERS = [
    ("mmlu", mmlu),
    ("mmlu_pro", mmlu_pro),  # A2 纵深：10 选一（复用现有算子，0 新增）
    ("medmcqa", medmcqa),  # A2 纵深：医学 4 选一（opa–opd 分离字段）
    ("arc", arc),
    ("hellaswag", hellaswag),
    ("commonsense_qa", commonsense_qa),
    ("truthful_qa", truthful_qa),
    ("ceval", ceval),  # 中文真实数据（CC-BY-NC-SA：仅本地验证，摘录不入库）
]


@pytest.mark.fr("FR-3.3")
@pytest.mark.parametrize(("name", "adapter"), ADAPTERS, ids=[n for n, _ in ADAPTERS])
class TestRealChoicesImport:
    def test_full_slice_imports_and_validates(self, name, adapter):
        rows = load_slice(name)
        assert len(rows) >= 100, "集成层切片须 ≥100 条（行动计划·验证材料策略）"
        items = adapter.import_rows(rows)
        assert len(items) == len(rows)
        assert all(isinstance(item.task, ChoicesTask) for item in items)
        ids = [item.id for item in items]
        assert len(set(ids)) == len(ids), "条目 id 必须数据集内唯一"

    def test_answers_reference_existing_options(self, name, adapter):
        for item in adapter.import_rows(load_slice(name)):
            option_ids = {o.id for o in item.task.options}
            answer_ids = set(item.verifiers[0].answer_ids)
            assert answer_ids <= option_ids, f"{item.id}: 答案 {answer_ids} ⊄ 选项 {option_ids}"

    def test_provenance_stamped_on_every_item(self, name, adapter):
        loaded = load_mapping(name)
        for item in adapter.import_rows(load_slice(name)):
            assert item.source is not None
            assert item.source.mapping_table == loaded.name
            assert item.source.mapping_hash == f"sha256:{loaded.sha256}"

    def test_mapping_covers_all_source_fields(self, name, adapter):
        """源字段全覆盖——还原能力的前提（裁决①"有留痕，能还原"）。"""
        covered = load_mapping(name).mapping.covered_source_fields()
        for row in load_slice(name):
            missing = set(row) - covered
            assert not missing, f"映射表未覆盖源字段（会丢信息）: {sorted(missing)}"

    def test_lossless_reexport(self, name, adapter):
        """invert(import(row)) 与源行语义等价（NFC 后逐字段，测试规格书 §② 规程）。"""
        rows = load_slice(name)
        restored = adapter.export_rows(adapter.import_rows(rows))
        for idx, (row, back) in enumerate(zip(rows, restored, strict=True)):
            diffs = diff_paths(normalize_tree(row), normalize_tree(back))
            assert not diffs, f"第 {idx} 行还原不等价: {diffs[:5]}"


@pytest.mark.fr("FR-3.3")
class TestQaRealImport:
    """qa 原型的真实切片（首个非选择题数据集，最终答案后缀约定）。"""

    def test_full_slice_imports_with_numeric_expected(self):
        rows = load_slice("gsm8k")
        assert len(rows) >= 100
        items = gsm8k.import_rows(rows)
        assert len(items) == len(rows)
        for item in items:
            assert isinstance(item.task, QaTask)
            verifier = item.verifiers[0]
            assert verifier.type == "text_match"
            digits = verifier.expected.replace(",", "").lstrip("-")
            assert digits.isdigit(), f"{item.id}: 参考答案非数值 {verifier.expected!r}"
            assert item.metadata["solution"].rstrip().endswith(verifier.expected)

    def test_mapping_covers_all_source_fields(self):
        covered = load_mapping("gsm8k").mapping.covered_source_fields()
        for row in load_slice("gsm8k"):
            missing = set(row) - covered
            assert not missing, f"映射表未覆盖源字段: {sorted(missing)}"

    def test_lossless_reexport(self):
        rows = load_slice("gsm8k")
        restored = gsm8k.export_rows(gsm8k.import_rows(rows))
        for idx, (row, back) in enumerate(zip(rows, restored, strict=True)):
            diffs = diff_paths(normalize_tree(row), normalize_tree(back))
            assert not diffs, f"第 {idx} 行还原不等价: {diffs[:5]}"


#: A2 纵深新增 qa 集（gsm8k 有数值-solution 专属断言见上；这里是通用全闸门）
QA_ADAPTERS = [
    ("svamp", svamp),  # 算术应用题（Answer 即 ideal）
    ("math", hendrycks_math),  # 竞赛数学（\boxed{} 提取最终答案）
]


@pytest.mark.fr("FR-3.3")
@pytest.mark.parametrize(("name", "adapter"), QA_ADAPTERS, ids=[n for n, _ in QA_ADAPTERS])
class TestQaRealImportParametrized:
    def test_full_slice_imports_and_validates(self, name, adapter):
        rows = load_slice(name)
        assert len(rows) >= 100
        items = adapter.import_rows(rows)
        assert len(items) == len(rows)
        assert all(isinstance(item.task, QaTask) for item in items)
        ids = [item.id for item in items]
        assert len(set(ids)) == len(ids), "条目 id 必须数据集内唯一"

    def test_mapping_covers_all_source_fields(self, name, adapter):
        covered = load_mapping(name).mapping.covered_source_fields()
        for row in load_slice(name):
            missing = set(row) - covered
            assert not missing, f"映射表未覆盖源字段: {sorted(missing)}"

    def test_lossless_reexport(self, name, adapter):
        rows = load_slice(name)
        restored = adapter.export_rows(adapter.import_rows(rows))
        for idx, (row, back) in enumerate(zip(rows, restored, strict=True)):
            diffs = diff_paths(normalize_tree(row), normalize_tree(back))
            assert not diffs, f"第 {idx} 行还原不等价: {diffs[:5]}"

"""HumanEval 真实切片导入（FR-2.3 集成层）——含**载荷干跑**：P2 自含性的机械证明。

干跑 = 仅用条目自身（task.prompt + metadata 参考解 + Verifier 载荷）拼装程序，
子进程执行应通过——证明"单独拿出即完整可执行规格"不是口号。
不调用任何模型（协议不做 Runner）；参考解为数据集自带的已知正确解。
"""

import subprocess
import sys

import pytest
from test_import_choices_real import load_slice

from uep.adapters import humaneval, load_mapping
from uep.equivalence import diff_paths, normalize_tree
from uep.schema import CodeGenerationTask

DRY_RUN_COUNT = 10


def _program(item) -> str:
    """全部素材取自条目本身——不回查源文件（自含性的构造性证明）。"""
    verifier = item.verifiers[0]
    return (
        item.task.prompt
        + item.metadata["canonical_solution"]
        + "\n"
        + verifier.tests.test_code
        + f"\ncheck({verifier.tests.entry_point})\n"
    )


@pytest.mark.fr("FR-2.3")
class TestCodegenRealImport:
    def test_full_slice_imports_and_validates(self):
        rows = load_slice("humaneval")
        assert len(rows) >= 100
        items = humaneval.import_rows(rows)
        assert len(items) == len(rows)
        assert all(isinstance(item.task, CodeGenerationTask) for item in items)
        ids = [item.id for item in items]
        assert len(set(ids)) == len(ids)
        for item in items:
            assert item.verifiers[0].tests.test_code, f"{item.id}: 载荷缺失"
            assert item.verifiers[0].tests.entry_point, f"{item.id}: 入口缺失"

    def test_mapping_covers_all_source_fields(self):
        covered = load_mapping("humaneval").mapping.covered_source_fields()
        for row in load_slice("humaneval"):
            missing = set(row) - covered
            assert not missing, f"映射表未覆盖源字段: {sorted(missing)}"

    def test_lossless_reexport(self):
        rows = load_slice("humaneval")
        restored = humaneval.export_rows(humaneval.import_rows(rows))
        for idx, (row, back) in enumerate(zip(rows, restored, strict=True)):
            diffs = diff_paths(normalize_tree(row), normalize_tree(back))
            assert not diffs, f"第 {idx} 行还原不等价: {diffs[:5]}"

    def test_payload_dry_run_grades_reference_solution(self):
        """前 10 条：条目自含素材拼装的程序在子进程通过（沙箱超时约束）。"""
        items = humaneval.import_rows(load_slice("humaneval"))[:DRY_RUN_COUNT]
        for item in items:
            timeout = item.verifiers[0].sandbox.timeout_s
            result = subprocess.run(
                [sys.executable, "-c", _program(item)],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            assert result.returncode == 0, f"{item.id} 干跑失败:\n{result.stderr[-800:]}"

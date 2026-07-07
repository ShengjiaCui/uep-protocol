"""RewardBench 真实切片导入（FR-3.3 集成层，custom 逃生舱）——成对偏好。

UEP 无成对偏好一等原型（A2 普查头号缺口）→ task.type=custom + schema_ref 挂
§8 演进提案（docs/proposals/2026-07-pairwise-preference.md）。本测试验证：
custom 任务合法往返、一致性检查按逃生舱跳过（不判失败）。
无黄金文件：custom 不在试金石辖区（无渲染消费者），非许可原因。
"""

import pytest
from test_import_choices_real import load_slice

from uep.adapters import load_mapping, rewardbench
from uep.conformance import check_touchstones
from uep.equivalence import diff_paths, normalize_tree
from uep.schema import CustomTask

_SCHEMA_REF = "proposal:2026-07-pairwise-preference"


@pytest.mark.fr("FR-3.3")
class TestRewardBenchRealImport:
    def test_full_slice_imports_and_validates(self):
        rows = load_slice("rewardbench")
        assert len(rows) >= 100
        items = rewardbench.import_rows(rows)
        assert len(items) == len(rows)
        assert all(isinstance(item.task, CustomTask) for item in items)
        assert all(item.task.schema_ref == _SCHEMA_REF for item in items)
        ids = [item.id for item in items]
        assert len(set(ids)) == len(ids)

    def test_pair_in_payload_answer_only_in_verifier(self):
        """P2：候选对进 payload，偏好真值（chosen 胜）只存 Verifier。"""
        for item in rewardbench.import_rows(load_slice("rewardbench")):
            assert {"prompt", "chosen", "rejected"} <= set(item.task.payload)
            verifier = item.verifiers[0]
            assert verifier.type == "choice_match" and verifier.answer_ids == ["chosen"]

    def test_conformance_skips_custom_escape_hatch(self):
        """受控逃生舱：一致性检查跳过 custom（不判失败），skipped 计数=条数。"""
        items = rewardbench.import_rows(load_slice("rewardbench"))
        result = check_touchstones(items)
        assert result.status == "pass"
        assert result.skipped == len(items)
        assert not result.problems

    def test_mapping_covers_all_source_fields(self):
        covered = load_mapping("rewardbench").mapping.covered_source_fields()
        for row in load_slice("rewardbench"):
            missing = set(row) - covered
            assert not missing, f"映射表未覆盖源字段: {sorted(missing)}"

    def test_lossless_reexport(self):
        rows = load_slice("rewardbench")
        restored = rewardbench.export_rows(rewardbench.import_rows(rows))
        for idx, (row, back) in enumerate(zip(rows, restored, strict=True)):
            diffs = diff_paths(normalize_tree(row), normalize_tree(back))
            assert not diffs, f"第 {idx} 行还原不等价: {diffs[:5]}"

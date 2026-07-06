"""SWE-bench_Lite 真实切片导入（FR-2.4 集成层）——判分三要素结构完备 + 无损反演。

许可注意：HF 卡片未声明许可（上游仓库 MIT）——切片仅本地验证，内容摘录不入库
（无黄金文件，同 C-Eval 处理）。仓库级修复无法像 codegen 那样本地干跑
（需 checkout 仓库+环境），结构完备性断言即本原型的载荷证明边界。
"""

import json

import pytest
from test_import_choices_real import load_slice

from uep.adapters import load_mapping, swebench
from uep.equivalence import diff_paths, normalize_tree
from uep.schema import PatchRepairTask

_DIFF_HEADERS = ("diff --git", "--- ", "+++ ")


@pytest.mark.fr("FR-2.4")
class TestPatchRealImport:
    def test_full_slice_imports_and_validates(self):
        rows = load_slice("swebench")
        assert len(rows) >= 100
        items = swebench.import_rows(rows)
        assert len(items) == len(rows)
        assert all(isinstance(item.task, PatchRepairTask) for item in items)
        ids = [item.id for item in items]
        assert len(set(ids)) == len(ids)

    def test_grading_payload_structurally_complete(self):
        """判分三要素逐条完备：diff 形态的 test_patch + 非空败转胜清单 + 环境事实。"""
        for item in swebench.import_rows(load_slice("swebench")):
            tests = item.verifiers[0].tests
            assert tests.test_patch and tests.test_patch.startswith(
                _DIFF_HEADERS
            ), f"{item.id}: test_patch 不是 diff 形态"
            assert tests.fail_to_pass, f"{item.id}: 败转胜清单为空，无法判分"
            assert tests.harness == "pytest"
            assert item.context.setup["environment_setup_commit"], f"{item.id}: 缺环境基准"

    def test_mapping_covers_all_source_fields(self):
        covered = load_mapping("swebench").mapping.covered_source_fields()
        for row in load_slice("swebench"):
            missing = set(row) - covered
            assert not missing, f"映射表未覆盖源字段（会丢信息）: {sorted(missing)}"

    def test_lossless_reexport(self):
        """含 JSON 编码清单的字节还原（list_encoding=json_string 的真实数据检验）。"""
        rows = load_slice("swebench")
        restored = swebench.export_rows(swebench.import_rows(rows))
        for idx, (row, back) in enumerate(zip(rows, restored, strict=True)):
            diffs = diff_paths(normalize_tree(row), normalize_tree(back))
            assert not diffs, f"第 {idx} 行还原不等价: {diffs[:5]}"

    def test_reference_patch_kept_out_of_verifier(self):
        """金补丁是参考解不是判分载荷：应在 metadata，不在 Verifier（P2 边界）。"""
        for item in swebench.import_rows(load_slice("swebench"))[:10]:
            assert item.metadata["patch"].startswith(_DIFF_HEADERS)
            dumped = json.dumps(item.verifiers[0].model_dump(), ensure_ascii=False)
            assert item.metadata["patch"] not in dumped

"""patch 试金石断言集（FR-2.6 同构复制）——真实切片全绿。

黄金文件豁免：切片许可未声明（HF 卡片空白），内容摘录不入库——
与 C-Eval 同等处理；断言集仍在本地切片全量运行。
"""

import pytest
from test_import_choices_real import load_slice
from test_task_patch import _ZH

from touchstones import TouchstoneError
from touchstones.check_patch import CheckedPatch, check
from uep.adapters import swebench
from uep.schema import EvalItem


@pytest.mark.fr("FR-2.6")
class TestCheckPatchAssertions:
    def test_assertion_set_on_full_real_slice(self):
        """检查单自含：仓库基准/三要素/沙箱逐项与条目一致；text 复现判分要点。"""
        items = swebench.import_rows(load_slice("swebench"))
        for item in items:
            checked = check(item)
            tests = item.verifiers[0].tests
            # ① 仓库基准与题面一致且非空
            assert checked.repo == item.task.repo and checked.repo
            assert checked.base_commit == item.task.base_commit and checked.base_commit
            assert checked.problem_statement == item.task.problem_statement
            # ② 三要素逐字节来自 Verifier（单一事实源）
            assert checked.test_patch == tests.test_patch
            assert checked.fail_to_pass == tests.fail_to_pass
            assert checked.pass_to_pass == tests.pass_to_pass
            # ③ 环境基准带出 + 沙箱自含
            assert checked.environment_ref
            assert checked.timeout_s > 0 and checked.network is False
            # ④ text 含仓库、基准、全部败转胜清单与测试变更
            assert checked.repo in checked.text and checked.base_commit in checked.text
            for test_id in checked.fail_to_pass:
                assert test_id in checked.text
            assert checked.test_patch in checked.text

    def test_synthetic_zh_item_checks(self):
        checked = check(EvalItem.model_validate(_ZH))
        assert isinstance(checked, CheckedPatch)
        assert "登录页" in checked.text
        assert checked.environment_ref == "def456"

    def test_non_patch_item_rejected(self):
        qa = {
            "id": "cp_bad_001",
            "lang": ["zh-CN"],
            "task": {"type": "qa", "question": "一加一等于几？"},
            "verifiers": [{"type": "text_match", "expected": "2"}],
        }
        with pytest.raises(TouchstoneError):
            check(EvalItem.model_validate(qa))

    def test_payload_without_patch_grading_rejected(self):
        """test_code 型载荷对修复判分不完整（合法条目 ≠ 可判修复）。"""
        bad = EvalItem.model_validate(_ZH).model_dump()
        bad["verifiers"][0]["tests"] = {
            "language": "python",
            "test_code": "def check(candidate):\n    assert candidate() == 1\n",
        }
        with pytest.raises(TouchstoneError, match="载荷不完整"):
            check(EvalItem.model_validate(bad))

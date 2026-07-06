"""patch_repair + 修复判分载荷（FR-2.4）——单元层双语夹具。

字段依 2026-07-04 提案（docs/proposals/2026-07-patch-grading-fields.md，用户批准）：
test_patch / fail_to_pass / pass_to_pass 进 TestSuite；自含性规则同步扩展。
"""

import pytest
from pydantic import ValidationError

from uep.schema import EvalItem, ExecutionVerifier, PatchRepairTask

_ZH = {
    "id": "patch_zh_001",
    "lang": ["zh-CN"],
    "task": {
        "type": "patch_repair",
        "repo": "example/webapp",
        "base_commit": "abc123",
        "problem_statement": "登录页在用户名含空格时报 500，应返回校验错误。",
    },
    "context": {"setup": {"environment_setup_commit": "def456"}},
    "verifiers": [
        {
            "type": "execution",
            "tests": {
                "language": "python",
                "harness": "pytest",
                "test_patch": 'diff --git a/tests/test_login.py b/tests/test_login.py\n--- a/tests/test_login.py\n+++ b/tests/test_login.py\n@@ -1,3 +1,6 @@\n+def test_space_in_username():\n+    assert login("a b") is None\n',
                "fail_to_pass": ["tests/test_login.py::test_space_in_username"],
                "pass_to_pass": ["tests/test_login.py::test_normal_login"],
            },
        }
    ],
}


@pytest.mark.fr("FR-2.4")
class TestPatchPrototype:
    def test_zh_item_valid_and_payload_self_contained(self):
        item = EvalItem.model_validate(_ZH)
        assert isinstance(item.task, PatchRepairTask)
        verifier = item.verifiers[0]
        assert isinstance(verifier, ExecutionVerifier)
        assert verifier.tests.test_patch.startswith("diff --git")
        assert verifier.tests.fail_to_pass, "败转胜清单是修复判分的必要载荷"
        assert verifier.tests.pass_to_pass
        assert verifier.sandbox.network is False
        assert item.context.setup["environment_setup_commit"] == "def456"

    def test_test_patch_without_fail_to_pass_rejected(self):
        bad = EvalItem.model_validate(_ZH).model_dump()
        bad["verifiers"][0]["tests"]["fail_to_pass"] = []
        bad["verifiers"][0]["tests"]["pass_to_pass"] = []
        with pytest.raises(ValidationError, match="自含"):
            EvalItem.model_validate(bad)

    def test_fail_to_pass_without_test_patch_rejected(self):
        bad = EvalItem.model_validate(_ZH).model_dump()
        bad["verifiers"][0]["tests"]["test_patch"] = None
        with pytest.raises(ValidationError, match="自含"):
            EvalItem.model_validate(bad)

    def test_legacy_payload_forms_still_valid(self):
        """向后兼容：test_code 或 assertions 单独成立（既有数据不破坏）。"""
        item = EvalItem.model_validate(_ZH).model_dump()
        item["verifiers"][0]["tests"] = {
            "language": "python",
            "test_code": "def check(candidate):\n    assert candidate() == 1\n",
        }
        assert EvalItem.model_validate(item).verifiers[0].tests.test_code

    def test_serialization_roundtrip_lossless(self):
        item = EvalItem.model_validate(_ZH)
        again = EvalItem.model_validate_json(item.model_dump_json())
        assert again.model_dump() == item.model_dump()

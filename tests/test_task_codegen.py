"""code_generation + execution 自含（FR-2.3）——单元层双语夹具。

协议承诺（P2）：TestSuite 单独拿出即完整可执行规格——载荷必须在 Verifier 内。
真实切片的载荷干跑证明在 tests/test_import_codegen_real.py。
"""

import pytest
from pydantic import ValidationError

from uep.schema import CodeGenerationTask, EvalItem, ExecutionVerifier

_ZH = {
    "id": "codegen_zh_001",
    "lang": ["zh-CN"],
    "task": {
        "type": "code_generation",
        "prompt": "实现函数 jia(a, b)，返回两数之和。",
        "language": "python",
    },
    "verifiers": [
        {
            "type": "execution",
            "tests": {
                "language": "python",
                "test_code": "def check(candidate):\n    assert candidate(1, 2) == 3\n",
                "entry_point": "jia",
                "harness": "exec",
            },
        }
    ],
}

_EN = {
    "id": "codegen_en_001",
    "lang": ["en"],
    "task": {
        "type": "code_generation",
        "prompt": "Complete the function double(x) that returns x * 2.",
        "language": "python",
        "starter_code": "def double(x):\n    ...",
    },
    "verifiers": [
        {
            "type": "execution",
            "tests": {
                "language": "python",
                "assertions": ["double(3) == 6", "double(0) == 0"],
                "harness": "exec",
            },
        }
    ],
}


@pytest.mark.fr("FR-2.3")
class TestCodegenPrototype:
    def test_zh_item_valid_and_payload_self_contained(self):
        item = EvalItem.model_validate(_ZH)
        assert isinstance(item.task, CodeGenerationTask)
        verifier = item.verifiers[0]
        assert isinstance(verifier, ExecutionVerifier)
        assert verifier.tests.test_code, "载荷必须自含（P2）"
        assert verifier.tests.entry_point == "jia"
        # 沙箱默认值随 Verifier 就位——单独拿出即可执行
        assert verifier.sandbox.timeout_s == 30
        assert verifier.sandbox.network is False

    def test_en_item_with_starter_code_and_assertions(self):
        item = EvalItem.model_validate(_EN)
        assert item.task.starter_code is not None
        assert item.verifiers[0].tests.assertions == ["double(3) == 6", "double(0) == 0"]

    def test_testsuite_without_payload_rejected(self):
        bad = dict(_ZH, verifiers=[{"type": "execution", "tests": {"language": "python"}}])
        with pytest.raises(ValidationError, match="自含"):
            EvalItem.model_validate(bad)

    def test_serialization_roundtrip_lossless(self):
        item = EvalItem.model_validate(_ZH)
        again = EvalItem.model_validate_json(item.model_dump_json())
        assert again.model_dump() == item.model_dump()

"""execution 试金石断言集（FR-2.6 同构复制，测试规格书 §①）——真实切片全绿 + 黄金文件。

黄金文件维护：``UEP_UPDATE_GOLDENS=1 pytest tests/test_touchstones_execution.py``。
"""

import os
from pathlib import Path

import pytest
from test_import_choices_real import load_slice

from touchstones import TouchstoneError
from touchstones.pack_execution import PackedExecution, pack
from uep.adapters import humaneval, humaneval_plus, mbpp
from uep.schema import EvalItem

GOLDEN_PATH = Path(__file__).parent / "golden" / "execution" / "humaneval.txt"
MBPP_GOLDEN_PATH = Path(__file__).parent / "golden" / "execution" / "mbpp.txt"

_SYNTH_ZH = EvalItem.model_validate(
    {
        "id": "pack_zh_001",
        "lang": ["zh-CN"],
        "task": {
            "type": "code_generation",
            "prompt": "实现函数 cheng(a, b)，返回两数之积。",
            "language": "python",
        },
        "verifiers": [
            {
                "type": "execution",
                "tests": {
                    "language": "python",
                    "test_code": "def check(candidate):\n    assert candidate(2, 3) == 6\n",
                    "entry_point": "cheng",
                    "harness": "exec",
                },
            }
        ],
    }
)


@pytest.mark.fr("FR-2.6")
class TestPackExecutionAssertions:
    def test_assertion_set_on_full_real_slice(self):
        """打包物自含：题面/载荷/入口/沙箱逐项与条目一致（断言集同构 §①）。"""
        items = humaneval.import_rows(load_slice("humaneval"))
        for item in items:
            packed = pack(item)
            verifier = item.verifiers[0]
            # ① 题面一致且非空
            assert packed.prompt == item.task.prompt and packed.prompt
            # ② 载荷逐字节来自 Verifier（单一事实源）
            assert packed.test_code == verifier.tests.test_code
            assert packed.entry_point == verifier.tests.entry_point
            # ③ 入口函数确实定义在题面中（载荷与题面互洽）
            assert f"def {packed.entry_point}(" in packed.prompt
            # ④ 沙箱参数自含 + text 含题面与载荷
            assert packed.timeout_s > 0 and packed.network is False
            assert packed.prompt in packed.text and packed.test_code in packed.text

    def test_synthetic_zh_item_packs(self):
        packed = pack(_SYNTH_ZH)
        assert isinstance(packed, PackedExecution)
        assert packed.entry_point == "cheng"
        assert "两数之积" in packed.text

    def test_non_codegen_rejected(self):
        qa = EvalItem.model_validate(
            {
                "id": "pack_bad_001",
                "lang": ["zh-CN"],
                "task": {"type": "qa", "question": "一加一等于几？"},
                "verifiers": [{"type": "text_match", "expected": "2"}],
            }
        )
        with pytest.raises(TouchstoneError):
            pack(qa)

    def test_missing_execution_verifier_rejected(self):
        bad = _SYNTH_ZH.model_dump()
        bad["verifiers"] = [{"type": "text_match", "expected": "6"}]
        with pytest.raises(TouchstoneError):
            pack(EvalItem.model_validate(bad))

    def test_language_mismatch_rejected(self):
        bad = _SYNTH_ZH.model_dump()
        bad["verifiers"][0]["tests"]["language"] = "javascript"
        with pytest.raises(TouchstoneError, match="语言"):
            pack(EvalItem.model_validate(bad))


@pytest.mark.fr("FR-2.6")
class TestPackExecutionMbppAssertions:
    """MBPP 断言列表路径（execution_from_assertion_list）——与 HumanEval 的 test_code 路径并列受检。"""

    def test_assertion_set_on_full_real_slice(self):
        items = mbpp.import_rows(load_slice("mbpp"))
        for item in items:
            packed = pack(item)
            verifier = item.verifiers[0]
            # ① 题面一致且非空
            assert packed.prompt == item.task.prompt and packed.prompt
            # ② 载荷来自 Verifier：断言列表路径，无 test_code/entry_point
            assert packed.assertions == verifier.tests.assertions
            assert packed.test_code is None and packed.entry_point is None
            assert packed.harness == "exec"
            # ③ 沙箱参数自含 + text 含题面与全部断言
            assert packed.timeout_s > 0 and packed.network is False
            assert packed.prompt in packed.text
            for assertion in packed.assertions:
                assert assertion in packed.text


@pytest.mark.fr("FR-2.6")
class TestPackExecutionHumanEvalPlusAssertions:
    """HumanEval+ test_code 路径——EvalPlus 加强载荷（8–80KB）无黄金（体量非许可原因），
    载荷逐字节保真在全量真实切片由断言集核验（顶替黄金职责）。"""

    def test_assertion_set_on_full_real_slice(self):
        items = humaneval_plus.import_rows(load_slice("humaneval_plus"))
        for item in items:
            packed = pack(item)
            verifier = item.verifiers[0]
            # ① 题面一致且非空
            assert packed.prompt == item.task.prompt and packed.prompt
            # ② 载荷逐字节来自 Verifier（顶替黄金：加强 test 载荷全量保真）
            assert packed.test_code == verifier.tests.test_code
            assert packed.entry_point == verifier.tests.entry_point
            assert packed.harness == "exec"
            # ③ 沙箱自含 + text 含题面与载荷
            assert packed.timeout_s > 0 and packed.network is False
            assert packed.prompt in packed.text and packed.test_code in packed.text


@pytest.mark.fr("FR-2.6")
def test_golden_file_byte_exact():
    """真实切片前 5 条的打包渲染与黄金文件逐字节一致。"""
    items = humaneval.import_rows(load_slice("humaneval"))[:5]
    blocks = [f"### {item.id}\n{pack(item).text}\n" for item in items]
    blob = "\n".join(blocks).encode("utf-8")
    if os.environ.get("UEP_UPDATE_GOLDENS") == "1":
        GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN_PATH.write_bytes(blob)
    assert GOLDEN_PATH.exists(), "缺黄金文件——UEP_UPDATE_GOLDENS=1 生成并提交评审"
    assert GOLDEN_PATH.read_bytes() == blob


@pytest.mark.fr("FR-2.6")
def test_mbpp_golden_file_byte_exact():
    """MBPP 真实切片前 5 条（断言列表路径）的打包渲染与黄金文件逐字节一致（CC-BY-4.0 可入库）。"""
    items = mbpp.import_rows(load_slice("mbpp"))[:5]
    blocks = [f"### {item.id}\n{pack(item).text}\n" for item in items]
    blob = "\n".join(blocks).encode("utf-8")
    if os.environ.get("UEP_UPDATE_GOLDENS") == "1":
        MBPP_GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        MBPP_GOLDEN_PATH.write_bytes(blob)
    assert MBPP_GOLDEN_PATH.exists(), "缺黄金文件——UEP_UPDATE_GOLDENS=1 生成并提交评审"
    assert MBPP_GOLDEN_PATH.read_bytes() == blob

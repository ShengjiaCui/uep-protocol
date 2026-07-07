import subprocess
import sys

import pytest

from scripts.build_zh_codegen import build_items
from scripts.zh_codegen_problems import PROBLEMS
from uep.schema import CodeGenerationTask, ExecutionVerifier


class TestNativeDataset:
    def test_at_least_twenty_valid_codegen_items(self):
        items = build_items()
        assert len(items) >= 20
        for it in items:
            assert isinstance(it.task, CodeGenerationTask)
            assert it.task.language == "python"
            assert any(t == "zh" or t.startswith("zh-") for t in it.lang)
            v = next(v for v in it.verifiers if isinstance(v, ExecutionVerifier))
            assert v.tests.test_code and v.tests.entry_point

    def test_ids_unique(self):
        ids = [it.id for it in build_items()]
        assert len(ids) == len(set(ids))

    def test_prompts_are_chinese(self):
        # 题面 docstring 须含中日韩统一表意文字（原生中文 codegen 的实证）
        for it in build_items():
            assert any("一" <= ch <= "鿿" for ch in it.task.prompt), it.id


class TestReferenceSolutionsPass:
    """每题标准解必须通过自己的 test_code——证明测试可满足、不误判（P2 构造性证明）。"""

    @pytest.mark.parametrize("p", PROBLEMS, ids=[p["id"] for p in PROBLEMS])
    def test_reference_solution_passes_own_tests(self, p):
        program = p["solution"] + "\n\n" + p["test_code"] + f"\ncheck({p['entry_point']})\n"
        r = subprocess.run([sys.executable, "-c", program], capture_output=True, timeout=15)
        assert r.returncode == 0, f"{p['id']} 参考解未过自测: {r.stderr.decode()[:300]}"

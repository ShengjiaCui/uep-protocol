#!/usr/bin/env python3
"""UEP code_generation → Inspect AI 判分任务（Runner 侧实验脚本，不属协议包）。

判分语义 = UEP execution Verifier 载荷：候选代码 + test_code + check(entry_point)
在本地沙箱执行，退出码 0 记 1 分。用法见 scripts/dogfood_codegen.py。

注意：sandbox="local" 为宿主机子进程执行、无隔离——仅限本地 dogfooding；
不可信代码来源须改用 docker sandbox。
"""

import os
import re
from typing import Any

from inspect_ai import Task, task
from inspect_ai.dataset import Sample, json_dataset
from inspect_ai.scorer import CORRECT, INCORRECT, Score, Target, accuracy, scorer, stderr
from inspect_ai.solver import TaskState, generate
from inspect_ai.util import sandbox

_FENCE = re.compile(r"```(?:python)?\n(.*?)```", re.S)


def _extract_code(completion: str) -> str:
    """模型答案里剥出代码：有 ``` 围栏取首个围栏内文本，否则原样。"""
    blocks = _FENCE.findall(completion)
    return blocks[0] if blocks else completion


def _record_to_sample(record: dict[str, Any]) -> Sample:
    """行 → Sample（API 校准，见脚本头/report 偏差记录①）。

    ``inspect_ai.dataset.FieldSpec(metadata=[...])`` 只探顶层字段
    （``record.get(name)``），但 Task 1 导出的样本形状是
    ``{..., "metadata": {test_code, entry_point, timeout_s, language}}``
    ——嵌套一层。用 FieldSpec 会让 scorer 拿到全 None 的 metadata（静默
    误判而非报错），故改手写 record→Sample 直取嵌套 metadata dict。
    """
    return Sample(
        input=record["input"],
        id=record["id"],
        metadata=record.get("metadata") or {},
    )


@scorer(metrics=[accuracy(), stderr()])
def uep_execution_scorer():
    async def score(state: TaskState, target: Target) -> Score:
        meta = state.metadata
        assert meta["language"] == "python", f"非 python 载荷: {meta['language']}"
        candidate = _extract_code(state.output.completion)
        # HumanEval 约定：prompt=签名+docstring，候选常为补全体；
        # 候选若已含完整 def 则独立成程序，否则拼接 prompt。
        program = (
            (candidate if "def " in candidate else state.input_text + candidate)
            + "\n\n"
            + meta["test_code"]
            + f"\ncheck({meta['entry_point']})\n"
        )
        try:
            result = await sandbox().exec(
                ["python", "-c", program], timeout=int(meta["timeout_s"])
            )
            ok = result.success
            if not ok:
                explanation = result.stderr[:500] if result.stderr else None
                return Score(value=INCORRECT, explanation=explanation)
            return Score(value=CORRECT)
        except Exception as e:
            return Score(value=INCORRECT, explanation=f"harness: {e!r}")

    return score


@task
def uep_codegen() -> Task:
    samples_path = os.environ["UEP_SAMPLES"]  # dogfood_codegen.py 注入
    return Task(
        dataset=json_dataset(samples_path, _record_to_sample),
        solver=generate(),
        scorer=uep_execution_scorer(),
        sandbox="local",
    )

#!/usr/bin/env python3
"""UEP choices/qa → Inspect AI 判分任务（A3 Runner 侧实验脚本，不属协议包）。

对分第二棒 Runner，对应 A1 的 inspect_codegen_task.py：
- choices：multiple_choice() 求解 + choice() 判分（生成式，模型输出 "ANSWER: X" 再解析）；
- qa：generate() + 自定义 uep_numeric_match scorer（数值抽取复用 crossrunner_extract，
  语义对齐 lm-eval 侧"最后一个数值"，把 qa 偏差隔离到"仅提示模板差异"）。

环境变量（编排器 crossrunner_compare.py 注入）：
    UEP_XR_TASK = choices | qa   —— 切任务原型
    UEP_SAMPLES = 样本 jsonl 路径 —— inspect_ai.export_samples 的产物
"""

import os
import sys
from pathlib import Path
from typing import Any

from inspect_ai import Task, task
from inspect_ai.dataset import Sample, json_dataset
from inspect_ai.scorer import (
    CORRECT,
    INCORRECT,
    Score,
    Target,
    accuracy,
    choice,
    scorer,
    stderr,
)
from inspect_ai.solver import TaskState, generate, multiple_choice

# 独立进程（inspect eval）加载本文件；确保仓根在 path 以导入纯抽取模块
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.crossrunner_extract import extract_number  # noqa: E402


def _choices_record_to_sample(record: dict[str, Any]) -> Sample:
    """choices 样本 → Inspect Sample（target 为位置字母，见 inspect_ai 导出器）。"""
    return Sample(
        id=record["id"],
        input=record["input"],
        choices=list(record["choices"]),
        target=record["target"],
    )


def _qa_record_to_sample(record: dict[str, Any]) -> Sample:
    """qa 样本 → Inspect Sample（target 为参考答案，可为 str 或 list）。"""
    return Sample(id=record["id"], input=record["input"], target=record["target"])


@scorer(metrics=[accuracy(), stderr()])
def uep_numeric_match():
    """数值判分：抽取候选与参考的最后一个数值比对（对齐 lm-eval 抽取规则）。"""

    async def score(state: TaskState, target: Target) -> Score:
        got = extract_number(state.output.completion)
        gold = extract_number(target.text) or target.text
        ok = got is not None and got == gold
        return Score(
            value=CORRECT if ok else INCORRECT,
            answer=got,
            explanation=None if ok else f"got={got!r} gold={gold!r}",
        )

    return score


@task
def uep_crossrunner() -> Task:
    kind = os.environ["UEP_XR_TASK"]  # choices | qa
    samples_path = os.environ["UEP_SAMPLES"]
    if kind == "choices":
        return Task(
            dataset=json_dataset(samples_path, _choices_record_to_sample),
            solver=multiple_choice(),
            scorer=choice(),
        )
    if kind == "qa":
        return Task(
            dataset=json_dataset(samples_path, _qa_record_to_sample),
            solver=generate(),
            scorer=uep_numeric_match(),
        )
    raise ValueError(f"UEP_XR_TASK 须为 choices|qa，得到 {kind!r}")

"""UEP → Inspect AI 样本导出（FR-6.1，第二棒 Runner——裁决②）。

Inspect 样本形态（JSONL）：
- choices → ``{id, input, choices:[选项文本], target: 位置字母}``——Inspect 框架
  自行给选项标 A/B/C…，故 target 是**位置**字母，与源选项 id 解耦
  （源 id 为 "0"–"3" 的数据集同样导出 A–D）；
- qa → ``{id, input, target: str | list[str]}``（多参考答案形状保持）。
任务包须同质（全 choices 或全 qa，与 lm-eval 导出同规）。
"""

import json
import string
from collections.abc import Iterable
from typing import Any

from uep.schema import (
    ChoiceMatchVerifier,
    ChoicesTask,
    CodeGenerationTask,
    EvalItem,
    ExecutionVerifier,
    QaTask,
    TextMatchVerifier,
)

_LETTERS = string.ascii_uppercase


def _choices_sample(item: EvalItem) -> dict[str, Any]:
    verifier = next((v for v in item.verifiers if isinstance(v, ChoiceMatchVerifier)), None)
    if verifier is None:
        raise ValueError(f"{item.id}: choices 导出需要 choice_match Verifier")
    option_ids = [option.id for option in item.task.options]
    if len(option_ids) > len(_LETTERS):
        raise ValueError(f"{item.id}: 选项数超出位置字母上限 {len(_LETTERS)}")
    letters = []
    for answer_id in verifier.answer_ids:
        try:
            position = option_ids.index(answer_id)
        except ValueError:
            raise ValueError(f"{item.id}: 答案 {answer_id!r} 不在选项 id 中") from None
        letters.append(_LETTERS[position])
    return {
        "id": item.id,
        "input": item.task.question,
        "choices": [option.text for option in item.task.options],
        "target": letters[0] if len(letters) == 1 else letters,
    }


def _qa_sample(item: EvalItem) -> dict[str, Any]:
    verifier = next((v for v in item.verifiers if isinstance(v, TextMatchVerifier)), None)
    if verifier is None:
        raise ValueError(f"{item.id}: qa 导出需要 text_match Verifier")
    expected = verifier.expected
    return {
        "id": item.id,
        "input": item.task.question,
        "target": expected if isinstance(expected, str) else list(expected),
    }


def _codegen_sample(item: EvalItem) -> dict[str, Any]:
    verifier = next((v for v in item.verifiers if isinstance(v, ExecutionVerifier)), None)
    if verifier is None:
        raise ValueError(f"{item.id}: codegen 条目缺 execution Verifier")
    if verifier.tests.test_code is None or verifier.tests.entry_point is None:
        raise ValueError(f"{item.id}: execution 载荷缺 test_code/entry_point")
    return {
        "id": item.id,
        "input": item.task.prompt,
        "target": "",
        "metadata": {
            "test_code": verifier.tests.test_code,
            "entry_point": verifier.tests.entry_point,
            "timeout_s": verifier.sandbox.timeout_s,
            "language": item.task.language,
        },
    }


def export_samples(items: Iterable[EvalItem]) -> list[dict[str, Any]]:
    """条目 → Inspect 样本字典列表（同质校验）。"""
    items = list(items)
    if not items:
        raise ValueError("导出条目为空")
    task_types = {type(item.task) for item in items}
    if task_types == {ChoicesTask}:
        return [_choices_sample(item) for item in items]
    if task_types == {QaTask}:
        return [_qa_sample(item) for item in items]
    if task_types == {CodeGenerationTask}:
        return [_codegen_sample(item) for item in items]
    names = sorted(t.__name__ for t in task_types)
    raise ValueError(f"任务包须同质（全 choices 或全 qa），得到 {names}")


def dump_jsonl(samples: Iterable[dict[str, Any]]) -> str:
    """样本 → 规范 JSONL（UTF-8 原文不转义）。"""
    return "".join(json.dumps(sample, ensure_ascii=False) + "\n" for sample in samples)

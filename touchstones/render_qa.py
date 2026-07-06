"""qa 原型试金石（FR-2.6）——只依赖协议类型的独立渲染程序。

合同（测试规格书 §① 风格）：输入为任何通过 ``uep validate`` 的 qa 条目，
输出结构化渲染物；本文件源码不得出现任何已接入格式/数据集名（禁名 lint 强制）。
``text`` 为完整题面（trajectory 在场时含全部文本消息——作答约定是题面的一部分），
参考答案单独在 ``expected``，绝不进 text。
"""

from dataclasses import dataclass

from touchstones import TouchstoneError
from uep.schema import EvalItem, QaTask, TextMatchVerifier

__all__ = ["RenderedQa", "TouchstoneError", "render"]


@dataclass(frozen=True)
class RenderedQa:
    question: str
    context_lines: list[str]  # trajectory 文本消息（"[role] 内容"，保序）；无轨迹则空
    expected: list[str]  # 参考答案（str|list 归一为列表，保序）
    text: str  # 人类可读完整题面（不含答案）


def render(item: EvalItem) -> RenderedQa:
    task = item.task
    if not isinstance(task, QaTask):
        raise TouchstoneError(f"{item.id}: 试金石仅接受 qa 条目，得到 {task.type!r}")
    verifier = next((v for v in item.verifiers if isinstance(v, TextMatchVerifier)), None)
    if verifier is None:
        raise TouchstoneError(f"{item.id}: 缺 text_match Verifier（打分意图不完整）")
    expected = (
        [verifier.expected] if isinstance(verifier.expected, str) else list(verifier.expected)
    )
    if not expected or not all(expected):
        raise TouchstoneError(f"{item.id}: 参考答案为空（打分意图不完整）")

    context_lines = [
        f"[{step.role}] {step.content}"
        for step in item.trajectory or []
        if isinstance(step.content, str) and step.content
    ]
    if context_lines:
        text = "\n".join(context_lines)
        if task.question not in text:  # 轨迹未含题干时补上，保证题面完整
            text = f"{text}\n{task.question}"
    else:
        text = task.question
    return RenderedQa(
        question=task.question, context_lines=context_lines, expected=expected, text=text
    )

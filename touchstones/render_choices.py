"""choices 原型试金石（FR-2.6）——只依赖协议类型的独立渲染程序。

合同（测试规格书 §①）：输入为任何通过 ``uep validate`` 的 choices 条目，
输出结构化渲染物；本文件源码不得出现任何已接入格式/数据集名（禁名 lint 强制）。
``text`` 为提示式渲染（题干 + 全部选项，不含答案）；答案单独在 ``correct_ids``。
"""

from dataclasses import dataclass

from touchstones import TouchstoneError
from uep.schema import ChoiceMatchVerifier, ChoicesTask, EvalItem

__all__ = ["RenderedChoice", "TouchstoneError", "render"]


@dataclass(frozen=True)
class RenderedChoice:
    question: str
    options: list[tuple[str, str]]  # (id, text)，顺序与条目一致——顺序是语义
    correct_ids: list[str]
    text: str  # 人类可读提示式渲染


def render(item: EvalItem) -> RenderedChoice:
    task = item.task
    if not isinstance(task, ChoicesTask):
        raise TouchstoneError(f"{item.id}: 试金石仅接受 choices 条目，得到 {task.type!r}")
    verifier = next((v for v in item.verifiers if isinstance(v, ChoiceMatchVerifier)), None)
    if verifier is None:
        raise TouchstoneError(f"{item.id}: 缺 choice_match Verifier（打分意图不完整）")
    options = [(option.id, option.text) for option in task.options]
    option_ids = {option.id for option in task.options}
    unknown = set(verifier.answer_ids) - option_ids
    if unknown:
        raise TouchstoneError(f"{item.id}: 答案 {sorted(unknown)} 不在选项 id 集合中")
    lines = [task.question, ""]
    lines += [f"{option_id}. {text}" for option_id, text in options]
    return RenderedChoice(
        question=task.question,
        options=options,
        correct_ids=list(verifier.answer_ids),
        text="\n".join(lines),
    )

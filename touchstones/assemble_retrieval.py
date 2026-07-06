"""retrieval 判分载荷试金石（FR-2.6 同构复制）——只依赖协议类型。

合同：输入为任何通过 ``uep validate``、含 ``retrieval`` Verifier 的 retrieval
条目，输出自含组装单 ``AssembledRetrieval``（查询、语料引用或内联计数、
相关性标注、指标）。内联语料时相关性 id 必须落在文档集合内（互洽校验）。
本文件源码不得出现任何已接入格式/数据集名（禁名 lint 强制）。
"""

from dataclasses import dataclass

from touchstones import TouchstoneError
from uep.schema import EvalItem, RetrievalTask, RetrievalVerifier


@dataclass(frozen=True)
class AssembledRetrieval:
    query: str
    corpus_ref: str | None  # 引用式语料 uri
    doc_count: int | None  # 内联语料文档数
    relevance: list[tuple[str, int]]  # (doc_id, grade)
    metrics: list[str]
    text: str  # 人类可读组装单


def assemble(item: EvalItem) -> AssembledRetrieval:
    task = item.task
    if not isinstance(task, RetrievalTask):
        raise TouchstoneError(f"{item.id}: 检索试金石仅接受 retrieval，得到 {task.type!r}")
    verifier = next((v for v in item.verifiers if isinstance(v, RetrievalVerifier)), None)
    if verifier is None:
        raise TouchstoneError(f"{item.id}: 缺 retrieval Verifier（打分意图不完整）")
    relevance = [(label.doc_id, label.grade) for label in verifier.relevance]
    doc_count: int | None = None
    if task.corpus.docs is not None:
        doc_count = len(task.corpus.docs)
        doc_ids = {doc.doc_id for doc in task.corpus.docs}
        unknown = {doc_id for doc_id, _ in relevance} - doc_ids
        if unknown:
            raise TouchstoneError(f"{item.id}: 相关性 id {sorted(unknown)} 不在内联语料中")
    corpus_line = (
        f"corpus: {task.corpus.uri}" if task.corpus.uri else f"corpus: 内联 {doc_count} 篇"
    )
    lines = [
        task.query,
        "",
        "=== 判分载荷（自含） ===",
        corpus_line,
        f"metrics: {', '.join(verifier.metrics)}",
        "relevance:",
        *[f"  - {doc_id} (grade={grade})" for doc_id, grade in relevance],
    ]
    return AssembledRetrieval(
        query=task.query,
        corpus_ref=task.corpus.uri,
        doc_count=doc_count,
        relevance=relevance,
        metrics=list(verifier.metrics),
        text="\n".join(lines),
    )

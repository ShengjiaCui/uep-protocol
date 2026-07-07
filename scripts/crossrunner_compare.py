#!/usr/bin/env python3
"""双 Runner 分数级对分（A3，Runner 侧实验脚本，不属协议包）。

compare() 为纯函数：两个 Runner 的逐条判分 dict → 一致性报告。
编排 main() 见后续任务。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

#: inspect_ai 的 Score.value CORRECT 哨兵；纯 JSON 解析 Inspect 日志，不引 inspect_ai 依赖
_INSPECT_CORRECT = "C"


@dataclass(frozen=True)
class ConsistencyReport:
    label_a: str
    label_b: str
    n: int
    acc_a: float
    acc_b: float
    both_correct: int
    both_wrong: int
    a_only: int
    b_only: int
    agreement_rate: float
    delta: float
    disagreements: list[str] = field(default_factory=list)


def compare(
    a: dict[str, bool], b: dict[str, bool], *, label_a: str, label_b: str
) -> ConsistencyReport:
    """两个 Runner 的 {id: 判对?} → 一致性报告。id 集合须一致（同条目同条数）。"""
    if not a or not b:
        raise ValueError("对分输入为空——两个 Runner 都需有判分结果")
    if a.keys() != b.keys():
        missing_in_b = sorted(a.keys() - b.keys())
        missing_in_a = sorted(b.keys() - a.keys())
        raise ValueError(
            f"两 Runner 条目不一致：{label_b} 缺 {missing_in_b[:5]}；{label_a} 缺 {missing_in_a[:5]}"
        )
    ids = sorted(a.keys())
    n = len(ids)
    both_correct = sum(1 for i in ids if a[i] and b[i])
    both_wrong = sum(1 for i in ids if not a[i] and not b[i])
    a_only = sum(1 for i in ids if a[i] and not b[i])
    b_only = sum(1 for i in ids if not a[i] and b[i])
    disagreements = [i for i in ids if a[i] != b[i]]
    return ConsistencyReport(
        label_a=label_a,
        label_b=label_b,
        n=n,
        acc_a=sum(a.values()) / n,
        acc_b=sum(b.values()) / n,
        both_correct=both_correct,
        both_wrong=both_wrong,
        a_only=a_only,
        b_only=b_only,
        agreement_rate=(both_correct + both_wrong) / n,
        delta=sum(a.values()) / n - sum(b.values()) / n,
        disagreements=disagreements,
    )


def parse_lmeval_samples(path: str | Path, *, metric_key: str = "exact_match") -> dict[str, bool]:
    """lm-eval --log_samples 的 samples_*.jsonl → {uep_id: 判对?}。

    每行含原始 doc（我们导出的 {id, prompt, gold}）与逐条 metric 值（config
    metric=exact_match，值 1.0/0.0）。
    """
    result: dict[str, bool] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        result[row["doc"]["id"]] = bool(row[metric_key])
    return result


def parse_inspect_log(path: str | Path) -> dict[str, bool]:
    """Inspect --log-format json 的日志 → {uep_id: 判对?}。

    纯 JSON 解析（不引 inspect_ai）：每 sample 取唯一 scorer 的 value，
    == "C"（CORRECT 哨兵）记 True。
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    result: dict[str, bool] = {}
    for sample in data.get("samples") or []:
        scores = sample["scores"]
        first_score = next(iter(scores.values()))
        result[str(sample["id"])] = first_score["value"] == _INSPECT_CORRECT
    return result

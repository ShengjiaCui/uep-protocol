#!/usr/bin/env python3
"""qa 数值抽取（A3 Runner 侧纯逻辑，不属协议包）。

语义须对齐 uep/adapters/lmeval.py::_DEFAULT_QA_PATTERN 的 lm-eval 侧抽取：
正则匹配数值、取**最后一个**（求解式输出的收尾约定）、去千分位逗号。
拆成独立纯模块是为可测——Inspect 任务文件顶层必须导入 @task/@scorer 装饰器，
无法在无 inspect_ai 的 pytest 环境里被导入；本模块仅依赖 stdlib，可被单测覆盖。
"""

from __future__ import annotations

import re

#: 与 lmeval 侧 _DEFAULT_QA_PATTERN 同语义（Runner 侧自定义，不 import 协议私有名）
_NUMBER = re.compile(r"(-?\d[\d,]*(?:\.\d+)?)")


def extract_number(text: str | None) -> str | None:
    """抽取文本中最后一个数值（去千分位逗号）；无匹配返回 None。"""
    matches = _NUMBER.findall(text or "")
    if not matches:
        return None
    return matches[-1].replace(",", "")

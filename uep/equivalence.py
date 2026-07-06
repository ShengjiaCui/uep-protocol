"""往返语义等价判定（测试规格书 §②，关卡 2 的机制）。

等价 ⇔ ``diff_paths(normalize(X), normalize(X')) == []``：
键序无关（dict 比较天然）、数组顺序**有关**、字符串 NFC 后比、数值按值
（``1 == 1.0``）、缺失键 ≠ null；豁免字段仅允许映射表 ``roundtrip_exempt``
显式声明（留痕），在 normalize 阶段剔除。
"""

import unicodedata
from typing import Any


def normalize_tree(value: Any, exempt: frozenset[str] = frozenset(), path: str = "") -> Any:
    """递归规范化解析后的 JSON 树；exempt 为点分字段路径集（列表元素不计入路径）。"""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if child_path in exempt:
                continue
            out[key] = normalize_tree(child, exempt, child_path)
        return out
    if isinstance(value, list):
        return [normalize_tree(child, exempt, path) for child in value]
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    return value


def diff_paths(x: Any, y: Any, path: str = "") -> list[str]:
    """字段路径级差异清单（失败输出用）；空列表 = 等价。输入应已 normalize。"""
    label = path or "<root>"
    if isinstance(x, bool) != isinstance(y, bool):
        return [f"{label}: 布尔与数值不等价（{x!r} ≠ {y!r}）"]
    if isinstance(x, dict) or isinstance(y, dict):
        if not (isinstance(x, dict) and isinstance(y, dict)):
            return [f"{label}: 类型 {type(x).__name__} ≠ {type(y).__name__}"]
        diffs: list[str] = []
        for key in sorted(set(x) | set(y)):
            key_path = f"{path}.{key}" if path else key
            if key not in x:
                diffs.append(f"{key_path}: 仅右侧存在（缺失键 ≠ null）")
            elif key not in y:
                diffs.append(f"{key_path}: 仅左侧存在（缺失键 ≠ null）")
            else:
                diffs.extend(diff_paths(x[key], y[key], key_path))
        return diffs
    if isinstance(x, list) or isinstance(y, list):
        if not (isinstance(x, list) and isinstance(y, list)):
            return [f"{label}: 类型 {type(x).__name__} ≠ {type(y).__name__}"]
        if len(x) != len(y):
            return [f"{label}: 数组长度 {len(x)} ≠ {len(y)}（顺序与个数是语义）"]
        diffs = []
        for idx, (a, b) in enumerate(zip(x, y, strict=True)):
            diffs.extend(diff_paths(a, b, f"{path}[{idx}]"))
        return diffs
    if x != y:
        return [f"{label}: {x!r} ≠ {y!r}"]
    return []


def semantically_equal(x: Any, y: Any, exempt: frozenset[str] = frozenset()) -> bool:
    """便捷入口：normalize 后无差异即等价。"""
    return not diff_paths(normalize_tree(x, exempt), normalize_tree(y, exempt))

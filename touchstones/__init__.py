"""试金石程序包——不含任何数据集名字的通用消费者（SPEC FR-2.6）。

本包全部源码受禁名 lint 约束（tests/test_no_dataset_names.py，阶段 1.3 落地）：
出现任何已接入格式/数据集名即 CI 红。"通用性"由机器裁判，不靠自觉。
"""


class TouchstoneError(ValueError):
    """条目不满足试金石前提（原型不符、缺对应 Verifier、载荷越界）。"""

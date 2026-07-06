# 【UEP 原型评审卡】原型：code_generation + execution（TestSuite）　协议版本：2.0.0-draft　日期：2026-07-04

> L3 人本验证（测试规格书 §⑥)。本原型是全项目设计风险最高点——"Verifier 自含打分全部载荷"（P2）
> 的真正考验；L1 已含**载荷干跑**证明：10 条真实条目仅用自身素材拼装程序、子进程判分通过。

## 1. 定义表（照抄 SPEC §3.3 与 §5）

**task（type="code_generation"）**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `prompt` | str | 题面（含签名/文档串等） |
| `language` | str | 目标语言，如 `"python"` |
| `starter_code` | str? | 起始代码 |

**execution Verifier**：`tests: TestSuite` + `sandbox: Sandbox`（载荷自含）

| TestSuite 字段 | 说明 | Sandbox 字段 | 默认 |
|------|------|------|------|
| `language` | 载荷语言（须与任务一致） | `timeout_s` | 30 |
| `test_code` / `assertions` | 二选一必有（P2 强制） | `network` | false |
| `entry_point` | 被测入口 | `memory_mb` | 512 |
| `harness` | `"pytest"` \| `"exec"` | `image` | – |

## 2. 样例（经试金石 `touchstones/pack_execution.py` 打包）

**英文样例（真实切片：HumanEval/0）**

```
from typing import List

def has_close_elements(numbers: List[float], threshold: float) -> bool:
    """ Check if in given list of numbers, are any two numbers closer ... """

=== 判分载荷（自含） ===
language: python · harness: exec · entry_point: has_close_elements
sandbox: timeout=30s network=False memory=512MB

METADATA = {...}
def check(candidate):
    assert candidate([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.3) == True
    ...
```
（完整版见 `tests/golden/execution/humaneval.txt`）

**中文样例（合成夹具 `pack_zh_001`）**

```
实现函数 cheng(a, b)，返回两数之积。

=== 判分载荷（自含） ===
language: python · harness: exec · entry_point: cheng
sandbox: timeout=30s network=False memory=512MB

def check(candidate):
    assert candidate(2, 3) == 6
```

> ⚠️ 与 choices 卡同款偏离：中文样例为合成夹具（中文真实 codegen 数据集待物色，
> 如 HumanEval 衍生中文集需先核许可）。

## 3. 评审问题（评审人作答）

- **Q1** 字段命名（`prompt`/`test_code`/`assertions`/`entry_point`/`harness`/`sandbox`）在你的领域自然吗？哪个别扭？
  答：
- **Q2** 你见过的代码评测数据（含多文件/依赖安装/非 Python），有装不进 TestSuite{`files`,`setup`} 结构的吗？
  答：
- **Q3** 哪个字段你第一眼理解错了？
  答：
- **Q4** 缺了什么必要信息（如判分粒度 pass@k、部分分）？
  答：
- **Q5** 结论：通过 / 有条件通过（条件：＿＿）/ 打回
  答：**通过**（用户终签，2026-07-06）

> **第一轮评审性质注记**：Q1–Q4 未逐项作答。终签依据 = HumanEval 100 条真实切片
> 全量断言 + **P2 自含性构造性证明**（干跑：仅用条目自身素材拼装程序子进程判分
> 10/10）+ 黄金文件（MIT 入库）。外部领域评审人第二轮随同行征询进行，
> 届时按模板另行作答 Q1–Q4。

## 4. 评审人：jason（用户本人；领域背景：AI 从业者 / 项目负责人）　日期：2026-07-06

## 5. 用户终签：**jason，2026-07-06**（会话指令原文："签字 testsuite/patch/retrieval"）

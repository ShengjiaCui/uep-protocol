# 原生中文 codegen 样例集报告（2026-07）

> UEP **原生创建**（非从第三方转换）的 20 条中文题面 Python 代码生成题，自写、
> Apache-2.0、**数据本体入库** `examples/zh-codegen/`。经 `uep validate` + `uep conform`
> 自查、并走 A1 判分闭环（Inspect 本地沙箱）实跑出 **pass@1 = 1.00**（gemma3:27b，贪婪，n=20）。
> **两个目的**：实证"新建 benchmark 创建者"用户故事（UEP 原生创作比手写 items.jsonl 省事），
> 并补中文 codegen 空缺（此前无合格许可候选，见 A1 判分闭环报告的债务登记）。

复现见文末；数据集与自测有单元测试背书（`tests/test_zh_codegen.py`，含 20 条参考解自测）。

---

## 一、动机

A1 判分闭环调研中发现：**中文 codegen 无合格许可候选**（CodeFuseEval HF 未声明许可、
GitHub NOASSERTION；humaneval-zh 类无可靠许可发布）——想要一个能自由使用的中文代码
生成评测集，只能自建。这恰好是检验 UEP 另一条价值主张的机会：**新建一个 UEP 原生
benchmark，是否比手写 JSONL 省事？** 本轮一箭双雕。

## 二、数据集（20 题，全 Apache-2.0 自写，入库）

题面全中文（英文函数签名 + 中文 docstring，HumanEval 形态），覆盖多主题、入门到中等难度：

| 主题 | 题目 |
|------|------|
| 字符串 | 回文判断 / 元音计数 / 反转单词 / 变位词 / 括号匹配 / 单词首字母大写 |
| 列表 | 两数之和 / 去重保序 / 展平 / 零移末尾 / 二分查找 / 合并有序表 |
| 数学 | 阶乘 / 斐波那契 / 素数 / 最大公约数 / 各位数字和 / 十进制转二进制 |
| 字典/DP/栈 | 词频统计 / 最大子数组和 |

每题自含 `execution` Verifier（`test_code` 用 HumanEval `check(candidate)` 约定），
判分载荷完整——单独拿出即可执行判分（协议原则 P2）。

## 三、创建成本：为什么"比自造 JSONL 省事"

| 量 | 值 |
|----|----|
| 作者源（`scripts/zh_codegen_problems.py`） | 510 行 = 每题 **5 字段**（id / 中文题面 / 入口函数名 / 参考解 / test_code）× 20 |
| 构建器（`scripts/build_zh_codegen.py`，**写一次复用**） | 66 行 |
| 生成 `items.jsonl` | 20 条，17 KB |

**作者只写题目内容**（题面 + 入口 + 参考解 + 测试）。以下协议骨架**全部由 schema +
构建器机械补全，作者一个字没碰**：

- `uep_version`、`lang` 规范化（`zh` → `zh-CN`）、`task` 判别式与类型字段；
- `verifier` 类型、`TestSuite` 结构（`files`/`assertions`/`harness`）、`Sandbox`
  默认（`timeout_s`/`network`/`memory_mb`）；
- `evidence`/`metadata`/`extras` 默认、JSON 序列化 + NFC 归一化；
- `manifest.json` 全部字段（`name`/`license`/`languages`/`task_types`/`size` 从条目机械汇总）。

**"省事"的准确含义**：不是行数更少（`items.jsonl` 每条压成一行，行数反而少）——而是
**作者只碰内容、零协议结构负担**。手写等价 `items.jsonl` 要为每条手工构造 ~865 字节的
稠密嵌套 JSON、20 次重复上述全部骨架，易错且无校验；UEP 原生路径把这一切交给 schema
与一个一次性的 66 行构建器，且产物即刻通过 `validate`/`conform`。

## 四、质量闸门（四重，均可复现）

1. **参考解自测**（`tests/test_zh_codegen.py::TestReferenceSolutionsPass`，20 条）：每题
   标准解必须通过自己的 `test_code`——证明测试**可满足、不误判**（P2 构造性证明）。全过。
2. **判分负对照**（`TestNegativeControl`，20 条）：对每题喂一个"返回 None"的桩解，**必被
   判错（非零退出）**——证明无题是"橡皮图章"，每题 `test_code` 真判分。全过。
3. **对抗式测试强化**：一轮多视角对抗评审**主动构造错误解去骗过测试**，揪出 4 处弱测试
   （`set(s)==set(t)` 骗过变位词、`str.title()` 骗过首字母大写、`isalpha` 漏数字、素数
   题唯一合数 15 漏偶合数）→ 逐一补判别用例，复核**这些错误解现已全部被判错**。测试从
   "参考解能过"升级为"能拒常见错解"。
4. **`uep validate`**（0 错 0 警）+ **`uep conform`**（schema 合法 20 条 / 试金石可消费 /
   清单机械一致）——三层全过。

## 五、真实 pass@1

| 指标 | 值 |
|------|----|
| pass@1 | **1.00**（20/20） |
| 模型 | 本地 Ollama `gemma3:27b`，**贪婪解码**（temperature=0，A3 教训：Inspect 不传温度会被 Ollama 默认 temp=1.0 采样） |
| 判分 | 复用 A1 `inspect_codegen_task.py`（本地沙箱执行 `候选 + test_code + check(entry_point)`），零改动 |
| 复核 | 抽查模型输出为**真实完整函数**（非空/非橡皮图章）；负对照证 scorer 会判错 |

**这个 1.00 经得起推敲**：它是在测试**经对抗式强化（可拒 4 类常见错解）之后**测得的
——gemma3 仍全过，说明它的解是**真正确**，不是蒙混弱测试。负对照进一步证明每题会判错。

**如实框定**：pass@1=1.00 说明这 20 题在 gemma3:27b（能力较强的 27B 模型）能力范围内
——它们是**入门到中等难度**，目的是**验证原生创建 → conform → 判分全管线打通**，
不是区分强模型。**难度校准**（加入能拉开分差的难题）是自然的后续工作，不在本轮。

## 六、一处设计观察（登记，不本轮改）

原生创作的条目 `source=None`——UEP 的 `Provenance` 6 个字段（`dataset`/`adapter`/
`mapping_table`/`mapping_hash`/`converted_at` 等）**全是"转换"痕迹**，为从第三方转换而设，
原生创作没有映射来源可填。当前把创作信息记在 `metadata.authored="native"` + manifest
的 `name`/`license`。**候选 SPEC 演进**：为原生创作补一类溯源字段（作者/创建时间/许可）。
改它要动 `uep/` 协议包，越出 A5 红线（原生数据/构建/判分只进 examples/、scripts/），
故仅登记、走 §8 演进机制另议。

## 七、诚实边界

- **作者=Claude，非受控人类研究**：创建成本是"作者只碰内容"的结构性证据，不是对人类
  创作者耗时的测量；题目质量未经社区评审（但过了自测 + conform + 负对照 + 独立评审）。
- **n=20 小样、单模型**：pass@1 是管线忠实性与数据集合法性的证明，非模型能力排行。
- **难度未校准**：见第五节，强模型满分，区分度是后续工作。

## 八、复现命令

```bash
# 1) 从简洁作者源生成 UEP 数据集（items.jsonl + manifest.json）
python scripts/build_zh_codegen.py

# 2) 自查：校验 + 一致性三层
python -m uep.cli validate examples/zh-codegen/items.jsonl
python -m uep.cli conform  examples/zh-codegen/items.jsonl

# 3) 参考解自测（20 条，证明测试可满足）
.venv/bin/python -m pytest tests/test_zh_codegen.py -q

# 4) A1 判分闭环实跑 pass@1（贪婪；前置：.venv-inspect + Ollama 可达）
python scripts/dogfood_codegen.py --items examples/zh-codegen/items.jsonl --limit 20 --model gemma3:27b
```

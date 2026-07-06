# UEP v2 测试规格书

> **状态**：**已签字生效**（2026-07-04 用户 "go"）——与 SPEC 共同构成阶段 1 开工基线。文档 v1.0。
> **地位**：验证金字塔的**断言级落地**。上游：SPEC（`docs/uep-v2-spec.md`，FR 清单见其 §10）、行动计划 0.4。
> 本文写到"拿来即可编码"的粒度；实现测试与本文冲突时，修测试。

---

## ① 试金石断言规格（FR-2.6）

**合同**：试金石程序只依赖协议类型，输入为"任何通过 `uep validate` 的条目集合"，输出为结构化渲染物。**源码禁止出现任何已接入格式/数据集名**。

阶段 1 交付 `touchstones/render_choices.py`：

```
render(item: EvalItem) -> RenderedChoice
RenderedChoice = {question: str, options: list[(id, text)], correct_ids: list[str], text: str}
```

**断言集**（对每条 choices 条目）：
1. `question == item.task.question` 且非空；
2. `options` 数量与顺序 == `item.task.options`（顺序是语义，不得重排）；
3. `correct_ids` 取自 `choice_match` Verifier，且 ⊆ 选项 id 集合；
4. `text`（人类可读渲染）包含题干与全部选项文本；
5. 对三个真实切片数据集各取前 5 条：渲染结果与黄金文件（`tests/golden/choices/*.txt`）逐字节一致。

**禁名 lint（`tests/test_no_dataset_names.py`）**：扫描 `touchstones/` 与 `uep/`（适配器目录除外）全部 `.py` 源码，命中注册表内任何格式名（不区分大小写）即失败；黑名单由适配器注册表**动态生成**，不手写。

**通过标准**：全部已接入 choices 数据集（真实切片）× 断言集全绿 + 禁名 lint 绿。阶段 2 起每新增原型复制同构规格（`render_qa` / `pack_execution` / `check_patch` / `assemble_retrieval`）。

## ② 语义等价判定规程（FR-3.2，关卡 2）

**定义**：`X →import→ UEP →export→ X'`，等价当且仅当 `normalize(X) == normalize(X')`，其中 normalize 对解析后的 JSON 树递归应用：

| 规则 | 判定 |
|------|------|
| 对象键序 | 无关（按 dict 比较） |
| 数组顺序 | **有关**（数据顺序是语义） |
| 字符串 | NFC 后比较（Unicode 等价，非字节等价） |
| 数值 | 解析后数值相等（`1 == 1.0`） |
| 缺失键 vs null | **不等价**，除非映射表声明了默认值 |
| 豁免字段 | 仅允许映射表 `roundtrip_exempt` 显式声明（留痕），豁免字段跳过比较 |

**测试形态**：OpenAI Evals 真实切片 ≥100 条；逐条断言等价，失败时输出条目 id + 字段路径级 diff。

## ③ 双语行为矩阵（FR-2.7）

`text_match.normalize` 的参数化用例表（`tests/test_verifier_cjk.py`，每行一个用例）：

| # | expected | 候选 | 参数 | 判定 |
|---|----------|------|------|:---:|
| 1 | `café`(NFC) | `café`(NFD) | 默认 | ✓ |
| 2 | `Paris` | `paris` | `case_fold=false`（默认） | ✗ |
| 3 | `Paris` | `paris` | `case_fold=true` | ✓ |
| 4 | `ABC` | `ＡＢＣ`（全角） | `width_fold=true`（默认） | ✓ |
| 5 | `42` | ` 42 ` | `strip_whitespace=true`（默认） | ✓ |
| 6 | `北京大学` | `北京大学` | 默认（无空格中文不误判） | ✓ |
| 7 | `你好，世界` | `你好,世界` | `cjk_punct_fold=false`（默认） | ✗ |
| 8 | `你好，世界` | `你好,世界` | `cjk_punct_fold=true` | ✓ |
| 9 | `答案是Ａ。` | `答案是A.` | `width_fold=true, cjk_punct_fold=true` | ✓ |
| 10 | 中文内容注入 `llm_judge` 模板占位符 | — | 渲染后 NFC 保持、无乱码 | ✓ |

每个原型的测试夹具必含 ≥1 条全中文条目 + ≥1 条中英混语条目（进各原型测试文件，此处为矩阵总纲）。

## ④ 骨架容纳探针表达清单（FR-1.6）

**样例**：新造一条"多轮工具使用 Agent"合成评测项（公开常识场景、中英混语、零参考旧数据）。**八项表达清单**，逐项存在性断言：

1. `context.environment` 有运行时标识；
2. `context.setup` 有声明式初始化配置；
3. `trajectory` ≥4 步；
4. 涵盖 ≥3 种 `role`（user/assistant/tool）；
5. 含完整 `tool_call` + `tool_result` 对；
6. ≥1 步含 `state_delta`；
7. `verifiers` 为 `composite`（含 ≥2 个异类子验证器，其中 1 个为载荷完整的 `execution`——只验证表达不执行）；
8. 中文与英文内容字段并存且 NFC 无损。

**断言**：`model_validate` 通过 + 八项逐验 + 序列化往返（model→JSON→model）无损。

## ⑤ L2 五分钟上手协议（FR-3.4 的 L2 部分，关卡 3）

- **前置允许**：已装 Python ≥3.10 与 uv；已 clone 仓库；网络可用。模型/数据下载耗时**不计入**；
- **计时窗**：受试者拿到任务卡 → 一份陌生 CSV 转成 UEP → 导出两种 Runner 格式 → 两者通过格式校验（干跑）。**≤5:00 通过**；
- **真实跑分**（Ollama `--limit 3`）单独记录，不计入五分钟（受模型速度影响，非协议易用性）；
- **任务卡**：中英双语各一页，仅含目标陈述，不含操作步骤（步骤靠 README 自己找——这正是被测物）；
- **记录表**：起止时间、卡点清单、一句话主观评价；失败则修文档后允许换人重测一次；
- **受试者**：第一轮=用户本人；零背景者缺位时延至外部接触点阶段补测（计划降级路径）。

## ⑥ L3 原型评审卡模板（每原型一页）

```
【UEP 原型评审卡】原型：____  协议版本：____  日期：____
1. 定义表：字段 | 类型 | 说明（照抄 SPEC §3 对应节）
2. 样例渲染：中文样例 ×1 + 英文样例 ×1（真实切片，经试金石渲染）
3. 评审问题（领域实践者作答）：
   Q1 字段命名在你的领域看着自然吗？哪个别扭？
   Q2 你领域常见的数据有装不进这个结构的吗？举例。
   Q3 哪个字段你第一眼理解错了？
   Q4 缺了什么你认为必要的信息？
   Q5 结论：通过 / 有条件通过（条件：__）/ 打回
4. 评审人：姓名/领域背景/日期    5. 用户终签：____
```

口述理解测试（附加）：给未接触者看一条渲染后的条目，能口述"这条评测在考什么、怎么算对"即通过。

## ⑦ 覆盖率闸门（FR-0.2）与映射元测试（FR-0.1）

- **覆盖率**：`make check` 内 `pytest --cov=uep --cov=touchstones --cov-fail-under=80`；`scripts/` 豁免；
- **映射元测试**：解析 SPEC §10 表格提取 FR 号与所属阶段；维护 `ACTIVE_PHASES` 配置（当前 `{1}`，随阶段推进更新）；凡 FR 属激活阶段而无对应 `@pytest.mark.fr` 标记 → 失败并列出缺失清单；标记存在但测试被 skip → 同样失败（防空壳）。

---

## 与 FR 的对应

本书 ①–⑦ 分别落地 FR-2.6 / FR-3.2 / FR-2.7 / FR-1.6 / FR-3.4(L2) / L3 流程 / FR-0.1–0.2；其余 FR 的验收测试按 SPEC §10 路径直接实现，无需额外规格。

*文档 v0.1（2026-07-04）· 待用户签字。*

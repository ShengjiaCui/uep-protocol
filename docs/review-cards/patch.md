# 【UEP 原型评审卡】原型：patch_repair + 修复判分载荷　协议版本：2.0.0-draft　日期：2026-07-04

> L3 人本验证（测试规格书 §⑥）。判分三字段经 §8 提案流程加入（docs/proposals/
> 2026-07-patch-grading-fields.md，2026-07-04 用户批准"稳扎稳打"落地）。

## 1. 定义表（照抄 SPEC §3.4 与 §5 修订后）

**task（type="patch_repair"）**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `repo` | str | 仓库标识 |
| `base_commit` | str | 基准提交 |
| `problem_statement` | str | 问题描述 |

**execution Verifier 修复判分三要素（TestSuite 内）**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `test_patch` | str? | 判分用测试变更（unified diff） |
| `fail_to_pass` | list[str] | 须由失败转通过的测试标识 |
| `pass_to_pass` | list[str] | 须保持通过的回归测试标识 |

载荷合法 ⇔ `test_code` / `assertions` / (`test_patch`+`fail_to_pass`) 三者其一。
环境基准（如 environment_setup_commit）走 `context.setup`（环境事实，不入 Verifier）。

## 2. 样例（经试金石 `touchstones/check_patch.py` 检查单渲染）

**中文样例（合成夹具 `patch_zh_001`）**

```
repo: example/webapp @ abc123

登录页在用户名含空格时报 500，应返回校验错误。

=== 判分载荷（自含） ===
harness: pytest · env_ref: def456
sandbox: timeout=30s network=False memory=512MB
fail_to_pass:
  - tests/test_login.py::test_space_in_username
pass_to_pass:
  - tests/test_login.py::test_normal_login

diff --git a/tests/test_login.py b/tests/test_login.py
--- a/tests/test_login.py
+++ b/tests/test_login.py
```

**英文样例（真实切片）**：SWE-bench_Lite test 前 100 条已全量通过断言集
（结构完备/单一事实源/无损反演）——因该数据集 HF 卡片**未声明许可**，
内容摘录不入本卡与黄金文件（与 C-Eval 同等的从严处理）；评审时可在本地运行
`pytest tests/test_check_patch.py` 现场查看真实渲染。

## 3. 评审问题（评审人作答）

- **Q1** 字段命名（`test_patch`/`fail_to_pass`/`pass_to_pass`/`base_commit`）在你的领域自然吗？哪个别扭？
  答：
- **Q2** 你见过的仓库级评测数据（多语言仓库、非 pytest 测试栈、需容器镜像），有装不进这个结构的吗？
  答：
- **Q3** 哪个字段你第一眼理解错了？
  答：
- **Q4** 缺了什么必要信息（如镜像标识、依赖锁、多补丁序列）？
  答：
- **Q5** 结论：通过 / 有条件通过（条件：＿＿）/ 打回
  答：**通过**（用户终签，2026-07-06）

> **第一轮评审性质注记**：Q1–Q4 未逐项作答。终签依据 = SWE-bench_Lite 100 条
> 真实切片 12 字段全覆盖 + 无损反演（含 JSON 字符串清单字节还原）+ **§8 演进机制
> 实弹**（判分三字段 test_patch/fail_to_pass/pass_to_pass 经提案获用户批准入
> SPEC v1.1）+ 金补丁边界有测试（参考解入 metadata 不入 Verifier）。
> 外部领域评审人第二轮随同行征询进行，届时按模板另行作答 Q1–Q4。

## 4. 评审人：jason（用户本人；领域背景：AI 从业者 / 项目负责人）　日期：2026-07-06

## 5. 用户终签：**jason，2026-07-06**（会话指令原文："签字 testsuite/patch/retrieval"）

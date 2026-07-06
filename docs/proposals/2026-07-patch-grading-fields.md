# 提案：TestSuite 增补仓库级修复判分字段（SPEC §8 流程）

**日期**：2026-07-04　**状态**：待裁决　**影响**：SPEC §5 TestSuite（协议处 2.0.0-draft，属草案期修订；定稿后同类变更须 minor+1）

## 动机

`patch_repair` 原型（SPEC §3.4）的判分载荷在业界有确定形态（SWE-bench 判分协议）：

1. **test_patch**——判分用测试变更（unified diff，先应用再跑测试）；
2. **FAIL_TO_PASS**——修复后必须"由失败转通过"的测试标识列表；
3. **PASS_TO_PASS**——必须保持通过的回归测试标识列表。

现行 TestSuite（`test_code/assertions/files/setup/entry_point/harness`）无处安放：
两组语义相反的测试清单塞进同一个 `assertions` 需要前缀编码=语义走私；diff 伪装成
`files` 丢失"这是待应用补丁"的语义。P2（Verifier 自含载荷）要求它们必须进 Verifier，
不得散落 metadata。

## 提案字段（全部可选，不破坏既有数据）

| TestSuite 新字段 | 类型 | 说明 |
|------|------|------|
| `test_patch` | str? | 判分用测试变更（unified diff） |
| `fail_to_pass` | list[str] | 须由失败转通过的测试标识（如 pytest node id） |
| `pass_to_pass` | list[str] | 须保持通过的回归测试标识 |

**自含性规则同步扩展**：TestSuite 载荷合法 ⇔ `test_code` 或 `assertions` 或
（`test_patch` 且 `fail_to_pass`）三者其一（P2 校验器强制）。
命名照搬领域术语 snake_case 化（判据 P6：优先专业——SWE-bench harness 原词）。
`environment_setup_commit` 不入 Verifier：属环境事实，走既有 `context.setup`（dict）。

## 实证（§8 要求 ≥2 个真实数据集）

- **SWE-bench / SWE-bench_Lite / SWE-bench_Verified**（princeton-nlp，同 schema 家族，
  本日实测 datasets-server：12 源字段含 `test_patch/FAIL_TO_PASS/PASS_TO_PASS`）；
- **Multi-SWE-bench**（多语言仓库修复，沿用同款 F2P/P2P 判分语义）。

## 示例（中文题面，缩略）

```json
{"uep_version":"2.0","id":"demo_patch_zh_001","lang":["zh-CN"],
 "task":{"type":"patch_repair","repo":"example/webapp","base_commit":"abc123",
   "problem_statement":"登录页在用户名含空格时报 500，应返回校验错误。"},
 "context":{"setup":{"environment_setup_commit":"def456"}},
 "verifiers":[{"type":"execution",
   "tests":{"language":"python","harness":"pytest",
     "test_patch":"diff --git a/tests/test_login.py ...",
     "fail_to_pass":["tests/test_login.py::test_space_in_username"],
     "pass_to_pass":["tests/test_login.py::test_normal_login"]}}]}
```

## 待裁决

- [ ] **通过**（按上表实现，SPEC §5 同步修订）
- [ ] 有条件通过（条件：＿＿）
- [ ] 打回（理由：＿＿）

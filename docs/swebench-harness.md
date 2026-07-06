# UEP patch_repair → SWE-bench 官方 harness 对接说明

UEP 不做 Runner：patch 判分的执行环境（每仓库 docker 镜像）由官方 harness 提供。

对接路径：
1. UEP 条目经适配器 `export_rows(items)` 无损还原为源行（instance_id、test_patch、
   FAIL_TO_PASS/PASS_TO_PASS 等官方字段——往返测试保证语义等价，JSON 字符串清单
   字节级还原）；
2. 还原行写回 jsonl 即为官方 `swebench.harness.run_evaluation` 的数据输入；
   模型补丁（predictions）由你的 Runner 产生；
3. 协议侧保证：判分三要素在 Verifier 内自含且机械可校验（diff 结构 + 选择器格式，
   touchstones/check_patch.py）。

**边界（如实）**：本仓库不运行 docker 判分环境；"patch 全闭环出分"依赖官方
harness 的环境矩阵。协议交付的是载荷完整性、可校验性、与官方输入格式的无损互换。

## 机械可校验的范围（本次新增，2026-07-06）

`touchstones/check_patch.py::check()` 在读取 Verifier 后新增两项结构校验，
拒绝对结构非法的载荷：

- **test_patch 是合法 unified diff**：须同时含文件头（`--- ` / `+++ `）与至少一个
  hunk 头（`@@ -N[,M] +N[,M] @@`）；否则抛 `TouchstoneError`（消息含 `diff`）。
- **fail_to_pass / pass_to_pass 选择器格式合法**：
  - 含 `::` 的（pytest 节点 id，如 `path/to/file.py::test_name[参数化 id]`）按
    结构化正则严格校验；
  - 不含 `::` 的（如 unittest 方法名+类路径 `test_x (mod.Cls)`、或用例文档字符串
    描述这类无统一语法的历史形态）按真实切片（100 条）实测结果放宽为最小机械
    约束：非空、无首尾空白/控制字符、可打印 ASCII——不强解具体语法。无 `::` 的选择器仅做编码级底线校验（非结构校验）。
  - 任一非法项抛 `TouchstoneError`（消息含"选择器"）。

放宽依据：对本地 100 条真实切片统计，4886 个选择器中 284 个为 pytest 节点 id
（含 `::`），其余 4602 个为无 `::` 的 unittest 风格/文档字符串描述（如
`test_override_file_upload_permissions (test_utils.tests.OverrideSettingsTests)`、
`Bug #13174.`）；这部分不具备统一结构语法，但全部满足非空、无首尾空白、可打印
ASCII——因此校验对其只做这一层最小约束，避免在没有真实语法基准时过度收紧。

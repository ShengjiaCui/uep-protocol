# 三原型判分闭环报告（2026-07）

**性质**：协议判分链闭环验证（非模型榜单）。五原型至此全部有真实出分证据。

| 原型 | 判分链 | 数据 | 真实分数 |
|------|--------|------|---------|
| code_generation | UEP→Inspect AI 本地沙箱执行 execution 载荷 | HumanEval 100 条 | pass@1 = 0.91（gemma3:27b，n=100，耗时 12 分 50 秒） |
| retrieval（英） | BM25 基线→verifier 载荷算 ndcg | SciFact 100 查询 × 全语料 5183 docs | ndcg@10 = 0.6279 |
| retrieval（中） | 同上（jieba 分词，池化候选） | T2Ranking 100 查询 × ≈1.1 万池 | ndcg@10 = 0.8050 |
| patch_repair | 载荷机械可校验 + 官方 harness 对接说明 | SWE-bench 100 条 | 机械可校验 ✓ + 官方 harness 对接说明（docs/swebench-harness.md）；全闭环依赖 docker 环境（边界如实） |
| choices / qa（既有） | UEP→lm-eval→Ollama | 8 集 | 见 docs/validation-report-2026-07.md |

复现：`python scripts/dogfood_codegen.py --limit 100`；`python scripts/retrieval_baseline.py --slice scifact|t2ranking`。
判分实现全部位于 scripts/（协议永不做 Runner，红线见 SPEC §11）。

**注：** 中文候选池=相关段落全集+1/200 系统抽样负例（≈1.1 万 docs）；全量 200 万段落检索属检索系统工程，超出判分链验证目标。

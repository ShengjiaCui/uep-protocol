PY := .venv/bin/python

.PHONY: check fmt demo phase1-exit phase2-exit phase3-exit phase4-exit

# 资格线四关卡端到端演示（goals §6，一条命令复现；需先 fetch_slices）
demo:
	$(PY) scripts/demo_gates.py

check:
	$(PY) -m ruff check uep touchstones tests
	$(PY) -m black --check uep touchstones tests
	$(PY) -m pytest -q --cov=uep --cov=touchstones --cov-fail-under=80

fmt:
	$(PY) -m ruff check --fix uep touchstones tests
	$(PY) -m black uep touchstones tests

# 阶段 1 出口闸门：激活阶段 1 的 FR 强制映射（缺测试即红）
phase1-exit:
	UEP_ACTIVE_PHASES=1 $(MAKE) check

# 阶段 2 出口闸门：红名单即阶段 2 待办清单
phase2-exit:
	UEP_ACTIVE_PHASES=1,2 $(MAKE) check

# 阶段 3 出口闸门：管理面动词 + convert/export + CLI 双语全绑测试
phase3-exit:
	UEP_ACTIVE_PHASES=1,2,3 $(MAKE) check

# 阶段 4 出口闸门：一致性工具包等对外准备 FR 全绑测试
phase4-exit:
	UEP_ACTIVE_PHASES=1,2,3,4 $(MAKE) check

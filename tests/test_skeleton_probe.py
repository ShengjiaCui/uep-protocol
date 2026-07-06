"""骨架容纳探针（FR-1.6）——真实形态的多轮工具 Agent 评测项，仅用骨架表达。

八项表达清单见 docs/uep-v2-test-spec.md §④。样例为合成数据（公开常识场景），零参考旧项目。
"""

import pytest

from uep.schema import EvalItem

AGENT_ITEM = {
    "id": "probe_agent_001",
    "lang": ["zh-CN", "en"],
    "task": {
        "type": "qa",
        "question": "查询北京当前气温并报告 / Query Beijing's current temperature and report.",
    },
    "context": {
        "environment": "python:3.12-slim",
        "setup": {"tools": ["weather_api"], "region": "cn-north"},
    },
    "trajectory": [
        {"role": "user", "content": "北京现在多少度？"},
        {
            "role": "assistant",
            "tool_call": {"name": "weather_api.get", "arguments": {"city": "Beijing"}},
        },
        {"role": "tool", "tool_result": {"temp_c": 31}, "state_delta": {"api_calls": 1}},
        {"role": "assistant", "content": "北京当前气温 31°C。"},
    ],
    "verifiers": [
        {
            "type": "composite",
            "mode": "all_of",
            "children": [
                {"type": "text_match", "expected": "31"},
                {
                    "type": "execution",
                    "tests": {
                        "language": "python",
                        "assertions": ["assert '31' in answer"],
                        "harness": "exec",
                    },
                    "sandbox": {"timeout_s": 5, "memory_mb": 128},
                },
            ],
        }
    ],
}


@pytest.mark.fr("FR-1.6")
def test_skeleton_holds_multi_turn_tool_agent():
    item = EvalItem.model_validate(AGENT_ITEM)

    assert item.context.environment  # ① 运行时标识
    assert isinstance(item.context.setup, dict)  # ② 声明式初始化
    assert len(item.trajectory) >= 4  # ③ 多轮
    assert {s.role for s in item.trajectory} >= {"user", "assistant", "tool"}  # ④ ≥3 种角色
    assert any(s.tool_call for s in item.trajectory)  # ⑤ 工具调用……
    assert any(s.tool_result is not None for s in item.trajectory)  # ……与返回
    assert any(s.state_delta for s in item.trajectory)  # ⑥ 状态变化痕迹
    composite = item.verifiers[0]
    assert composite.type == "composite"  # ⑦ 复合验证……
    assert len({c.type for c in composite.children}) >= 2
    execution = next(c for c in composite.children if c.type == "execution")
    assert execution.tests.assertions or execution.tests.test_code  # ……execution 载荷完整
    assert "北京" in item.trajectory[0].content  # ⑧ 中英并存……
    assert "Query" in item.task.question

    again = EvalItem.model_validate_json(item.model_dump_json())  # 序列化往返无损
    assert again == item

"""UEP → lm-eval-harness 任务包导出（FR-3.4）。

产物：``<task_name>.yaml``（generate_until + 正则抽取 + exact_match）
与 ``<task_name>.jsonl``（每行 ``{id, prompt, gold}``）。

设计取舍：
- 走 generate_until 而非 multiple_choice——后者依赖 loglikelihood，
  OpenAI 兼容 chat 端点（Ollama）普遍不提供 echo+logprobs；
- 任务包须同质（全 choices 或全 qa）：两者抽取语义不同——choices 取
  首个选项 id（正则从**实际 id 集合**动态构建，最长优先防 "1" 抢 "11"），
  qa 取最后一个匹配（求解式输出的收尾约定），模式可由调用方覆写；
- prompt 复用试金石渲染（同一渲染语义，单一事实源），作答指令随条目
  lang 中英切换（P5：打分行为对两种语言同样正确）。
"""

import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

from touchstones.render_choices import render
from uep.schema import ChoicesTask, EvalItem, QaTask, TextMatchVerifier

_CHOICES_INSTRUCTION_ZH = "只输出正确选项的标号，不要解释。答案："
_CHOICES_INSTRUCTION_EN = "Respond with the id of the correct option only, no explanation. Answer:"
_QA_INSTRUCTION_ZH = "只输出最终答案，不要解释。答案："
_QA_INSTRUCTION_EN = "Respond with the final answer only, no explanation. Answer:"
#: qa 默认抽取：输出中最后一个数值（求解式回答的收尾约定）
_DEFAULT_QA_PATTERN = r"(-?\d[\d,]*(?:\.\d+)?)"


def _is_zh(item: EvalItem) -> bool:
    return any(tag == "zh" or tag.startswith("zh-") for tag in item.lang)


def _choices_payload(
    items: list[EvalItem],
) -> tuple[list[dict[str, str]], dict[str, Any], dict[str, Any]]:
    docs: list[dict[str, str]] = []
    option_ids: set[str] = set()
    for item in items:
        rendered = render(item)
        option_ids.update(oid for oid, _ in rendered.options)
        instruction = _CHOICES_INSTRUCTION_ZH if _is_zh(item) else _CHOICES_INSTRUCTION_EN
        docs.append(
            {
                "id": item.id,
                "prompt": f"{rendered.text}\n\n{instruction}",
                "gold": ",".join(rendered.correct_ids),
            }
        )
    ordered = sorted(option_ids, key=lambda oid: (-len(oid), oid))  # 最长优先
    alternation = "|".join(re.escape(oid) for oid in ordered)
    extraction = {"pattern": rf"\b({alternation})\b", "group_select": 0, "ignore": None}
    gen_kwargs = {"until": ["\n\n"], "max_gen_toks": 64}  # 选项标号回答很短
    return docs, extraction, gen_kwargs


def _qa_prompt_body(item: EvalItem) -> str:
    """trajectory 在场时它才是完整题面（含 system 作答约定）；question 是退化视图。"""
    if item.trajectory:
        parts = [
            step.content
            for step in item.trajectory
            if step.role in ("system", "user") and isinstance(step.content, str)
        ]
        if parts:
            return "\n\n".join(parts)
    return item.task.question


def _qa_payload(
    items: list[EvalItem], answer_pattern: str | None
) -> tuple[list[dict[str, str]], dict[str, Any], dict[str, Any]]:
    docs: list[dict[str, str]] = []
    for item in items:
        verifier = next((v for v in item.verifiers if isinstance(v, TextMatchVerifier)), None)
        if verifier is None:
            raise ValueError(f"{item.id}: qa 导出需要 text_match Verifier")
        expected = verifier.expected
        gold = expected[0] if isinstance(expected, list) else expected
        instruction = _QA_INSTRUCTION_ZH if _is_zh(item) else _QA_INSTRUCTION_EN
        docs.append(
            {
                "id": item.id,
                "prompt": f"{_qa_prompt_body(item)}\n\n{instruction}",
                "gold": gold,
            }
        )
    extraction = {
        "pattern": answer_pattern or _DEFAULT_QA_PATTERN,
        "group_select": -1,  # 取最后一个匹配
        "ignore": [","],  # 千分位逗号不参与比对
    }
    # 求解式回答需要推理长度；"\n\n" 会截断分段推理，qa 不设停止串
    gen_kwargs = {"until": [], "max_gen_toks": 256}
    return docs, extraction, gen_kwargs


def export_task(
    items: Iterable[EvalItem],
    *,
    task_name: str,
    out_dir: Path,
    answer_pattern: str | None = None,
) -> Path:
    """写出任务包，返回任务 YAML 路径。items 须同质（全 choices 或全 qa）。"""
    items = list(items)
    if not items:
        raise ValueError("导出条目为空")
    task_types = {type(item.task) for item in items}
    if task_types == {ChoicesTask}:
        docs, extraction, gen_kwargs = _choices_payload(items)
    elif task_types == {QaTask}:
        docs, extraction, gen_kwargs = _qa_payload(items, answer_pattern)
    else:
        names = sorted(t.__name__ for t in task_types)
        raise ValueError(f"任务包须同质（全 choices 或全 qa），得到 {names}")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    docs_path = out_dir / f"{task_name}.jsonl"
    docs_path.write_text(
        "".join(json.dumps(doc, ensure_ascii=False) + "\n" for doc in docs), encoding="utf-8"
    )

    metric: dict[str, Any] = {
        "metric": "exact_match",
        "aggregation": "mean",
        "higher_is_better": True,
        "ignore_case": True,
    }
    if extraction["ignore"]:
        metric["regexes_to_ignore"] = extraction["ignore"]
    config = {
        "task": task_name,
        "dataset_path": "json",
        "dataset_kwargs": {"data_files": {"test": str(docs_path)}},
        "test_split": "test",
        "output_type": "generate_until",
        "doc_to_text": "{{prompt}}",
        "doc_to_target": "{{gold}}",
        "generation_kwargs": {**gen_kwargs, "do_sample": False, "temperature": 0.0},
        "filter_list": [
            {
                "name": "extract-id",
                "filter": [
                    {
                        "function": "regex",
                        "regex_pattern": extraction["pattern"],
                        "group_select": extraction["group_select"],
                    },
                    {"function": "take_first"},
                ],
            }
        ],
        "metric_list": [metric],
        "num_fewshot": 0,
    }
    yaml_path = out_dir / f"{task_name}.yaml"
    yaml_path.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return yaml_path

"""声明式映射表引擎（SPEC §7）——mapping.yaml 的模型、受限算子与应用/反演。

设计约束：
- 算子是封闭集合（``op`` 判别联合 + ``extra="forbid"``）：YAML 只能声明"用哪个算子"，
  写不进任何代码；新增算子必须改本文件并过 SPEC 评审。
- 每个算子自带 ``invert()``：还原义务（§7.4）由同一张表机械反演兑现，
  不依赖适配器作者自觉；const/format_id 等 UEP 侧生成物在反演时自然丢弃。
- 本模块不出现任何具体格式/数据集名（禁名 lint 辖区）；具体名只进注册表与 mapping.yaml。
"""

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import Field

from uep import __version__
from uep.schema import EvalItem, UepModel

_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


class MappingApplyError(ValueError):
    """映射应用/反演失败（源字段缺失、类型不符）——fail fast，带行号与字段。"""


def get_path(obj: Any, path: str) -> Any:
    """点分路径取值（``choices.text``）；缺失即报错，不静默兜底。"""
    cur = obj
    for seg in path.split("."):
        if not isinstance(cur, dict) or seg not in cur:
            raise MappingApplyError(f"源字段缺失: {path!r}（在段 {seg!r} 处）")
        cur = cur[seg]
    return cur


def set_path(obj: dict[str, Any], path: str, value: Any) -> None:
    """点分路径写值，中间层自动建 dict（仅用于构建期的本地字典）。"""
    segs = path.split(".")
    cur = obj
    for seg in segs[:-1]:
        cur = cur.setdefault(seg, {})
    cur[segs[-1]] = value


def _first_verifier(item: dict[str, Any], vtype: str) -> dict[str, Any]:
    for verifier in item.get("verifiers", []):
        if verifier.get("type") == vtype:
            return verifier
    raise MappingApplyError(f"条目缺少 {vtype} Verifier，无法反演")


# ---------------------------------------------------------------- 受限算子（封闭集合）


class ConstTransform(UepModel):
    """写入字面量（UEP 侧生成，不来自源行；反演时丢弃）。"""

    op: Literal["const"]
    target: str = Field(min_length=1)
    value: Any

    def apply(self, data: dict[str, Any], row: dict[str, Any], row_idx: int) -> None:
        set_path(data, self.target, self.value)

    def invert(self, out: dict[str, Any], item: dict[str, Any]) -> None:
        return None


class FormatIdTransform(UepModel):
    """按模板生成条目 id（可用源行字段与 ``{row_idx}``；反演时丢弃）。"""

    op: Literal["format_id"]
    target: str = "id"
    template: str = Field(min_length=1)

    def apply(self, data: dict[str, Any], row: dict[str, Any], row_idx: int) -> None:
        try:
            set_path(data, self.target, self.template.format(row_idx=row_idx, **row))
        except (KeyError, IndexError) as exc:
            raise MappingApplyError(f"id 模板字段缺失: {exc}") from exc

    def invert(self, out: dict[str, Any], item: dict[str, Any]) -> None:
        return None


class OptionsFromTextsTransform(UepModel):
    """源选项文本列表 → ``task.options``；id 按 letters/index 生成。"""

    op: Literal["options_from_texts"]
    source: str = Field(min_length=1)
    target: str = "task.options"
    id_style: Literal["letters", "index"]

    def _ids(self, count: int) -> list[str]:
        if self.id_style == "letters":
            if count > len(_LETTERS):
                raise MappingApplyError(f"选项数 {count} 超出字母 id 上限 {len(_LETTERS)}")
            return list(_LETTERS[:count])
        return [str(i) for i in range(count)]

    def apply(self, data: dict[str, Any], row: dict[str, Any], row_idx: int) -> None:
        texts = get_path(row, self.source)
        if not isinstance(texts, list):
            raise MappingApplyError(
                f"{self.source!r} 应为选项文本列表，得到 {type(texts).__name__}"
            )
        ids = self._ids(len(texts))
        pairs = zip(ids, texts, strict=True)
        set_path(data, self.target, [{"id": i, "text": t} for i, t in pairs])

    def invert(self, out: dict[str, Any], item: dict[str, Any]) -> None:
        options = get_path(item, self.target)
        set_path(out, self.source, [o["text"] for o in options])


class OptionsFromPairsTransform(UepModel):
    """平行的标签列表 + 文本列表 → ``task.options``（保留源标签为 id）。"""

    op: Literal["options_from_pairs"]
    source_labels: str = Field(min_length=1)
    source_texts: str = Field(min_length=1)
    target: str = "task.options"

    def apply(self, data: dict[str, Any], row: dict[str, Any], row_idx: int) -> None:
        labels = get_path(row, self.source_labels)
        texts = get_path(row, self.source_texts)
        if len(labels) != len(texts):
            raise MappingApplyError(
                f"标签/文本长度不一致: {len(labels)} vs {len(texts)}"
                f"（{self.source_labels} / {self.source_texts}）"
            )
        pairs = zip(labels, texts, strict=True)
        set_path(data, self.target, [{"id": la, "text": t} for la, t in pairs])

    def invert(self, out: dict[str, Any], item: dict[str, Any]) -> None:
        options = get_path(item, self.target)
        set_path(out, self.source_labels, [o["id"] for o in options])
        set_path(out, self.source_texts, [o["text"] for o in options])


class OptionsFromFieldsTransform(UepModel):
    """独立列选项（每个选项一个源字段，字段名即选项 id）→ ``task.options``。"""

    op: Literal["options_from_fields"]
    sources: list[str] = Field(min_length=2)
    target: str = "task.options"

    def apply(self, data: dict[str, Any], row: dict[str, Any], row_idx: int) -> None:
        options = [{"id": field, "text": get_path(row, field)} for field in self.sources]
        set_path(data, self.target, options)

    def invert(self, out: dict[str, Any], item: dict[str, Any]) -> None:
        for option in get_path(item, self.target):
            set_path(out, option["id"], option["text"])


class ChoiceMatchFromIndexTransform(UepModel):
    """源答案下标 → ``choice_match`` Verifier（正确答案只存 Verifier，P2）。"""

    op: Literal["choice_match_from_index"]
    source: str = Field(min_length=1)
    id_style: Literal["letters", "index"]
    dtype: Literal["int", "str"] = "int"  # 反演时恢复源类型（有的源下标是字符串）

    def apply(self, data: dict[str, Any], row: dict[str, Any], row_idx: int) -> None:
        raw = get_path(row, self.source)
        try:
            idx = int(raw)
        except (TypeError, ValueError) as exc:
            raise MappingApplyError(f"{self.source!r} 不是选项下标: {raw!r}") from exc
        if self.id_style == "letters":
            if idx >= len(_LETTERS) or idx < 0:
                raise MappingApplyError(f"下标 {idx} 超出字母 id 范围")
            answer_id = _LETTERS[idx]
        else:
            answer_id = str(idx)
        verifiers = data.setdefault("verifiers", [])
        verifiers.append({"type": "choice_match", "answer_ids": [answer_id]})

    def invert(self, out: dict[str, Any], item: dict[str, Any]) -> None:
        answer_id = _first_verifier(item, "choice_match")["answer_ids"][0]
        idx = _LETTERS.index(answer_id) if self.id_style == "letters" else int(answer_id)
        set_path(out, self.source, idx if self.dtype == "int" else str(idx))


class ChoiceMatchFromLabelTransform(UepModel):
    """源答案标签（与选项标签同一命名空间）→ ``choice_match`` Verifier。"""

    op: Literal["choice_match_from_label"]
    source: str = Field(min_length=1)

    def apply(self, data: dict[str, Any], row: dict[str, Any], row_idx: int) -> None:
        label = get_path(row, self.source)
        if not isinstance(label, str) or not label:
            raise MappingApplyError(f"{self.source!r} 应为非空字符串标签，得到 {label!r}")
        verifiers = data.setdefault("verifiers", [])
        verifiers.append({"type": "choice_match", "answer_ids": [label]})

    def invert(self, out: dict[str, Any], item: dict[str, Any]) -> None:
        answer_id = _first_verifier(item, "choice_match")["answer_ids"][0]
        set_path(out, self.source, answer_id)


class ExecutionFromFieldsTransform(UepModel):
    """源测试代码/入口字段 → 自含 ``execution`` Verifier（载荷+沙箱默认值，P2）。

    ``language``/``harness`` 是字面值（源格式的既定事实），非源路径。
    """

    op: Literal["execution_from_fields"]
    source_test_code: str = Field(min_length=1)
    source_entry_point: str | None = None
    language: str = Field(min_length=1)
    harness: Literal["pytest", "exec"] = "exec"

    def apply(self, data: dict[str, Any], row: dict[str, Any], row_idx: int) -> None:
        tests: dict[str, Any] = {
            "language": self.language,
            "test_code": get_path(row, self.source_test_code),
            "harness": self.harness,
        }
        if self.source_entry_point:
            tests["entry_point"] = get_path(row, self.source_entry_point)
        verifiers = data.setdefault("verifiers", [])
        verifiers.append({"type": "execution", "tests": tests})

    def invert(self, out: dict[str, Any], item: dict[str, Any]) -> None:
        verifier = _first_verifier(item, "execution")
        set_path(out, self.source_test_code, verifier["tests"]["test_code"])
        if self.source_entry_point:
            set_path(out, self.source_entry_point, verifier["tests"]["entry_point"])


class ExecutionFromPatchFieldsTransform(UepModel):
    """仓库级修复判分载荷 → ``execution`` Verifier（test_patch + 败转胜/回归清单）。

    源清单常为 JSON 编码字符串（如 ``'["t::a", "t::b"]'``）；``list_encoding``
    声明源形状，反演按原形状还原（json_string 用 json.dumps 默认格式重编码）。
    """

    op: Literal["execution_from_patch_fields"]
    source_test_patch: str = Field(min_length=1)
    source_fail_to_pass: str = Field(min_length=1)
    source_pass_to_pass: str | None = None
    language: str = Field(min_length=1)
    harness: Literal["pytest", "exec"] = "pytest"
    list_encoding: Literal["json_string", "list"] = "json_string"

    def _decode(self, raw: Any, path: str) -> list[str]:
        if self.list_encoding == "list":
            value = raw
        else:
            if not isinstance(raw, str):
                raise MappingApplyError(f"{path!r} 应为 JSON 字符串，得到 {type(raw).__name__}")
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise MappingApplyError(f"{path!r} 不是合法 JSON: {exc}") from exc
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise MappingApplyError(f"{path!r} 应为字符串列表，得到 {value!r}")
        return value

    def _encode(self, value: list[str]) -> Any:
        return json.dumps(value) if self.list_encoding == "json_string" else value

    def apply(self, data: dict[str, Any], row: dict[str, Any], row_idx: int) -> None:
        tests: dict[str, Any] = {
            "language": self.language,
            "harness": self.harness,
            "test_patch": get_path(row, self.source_test_patch),
            "fail_to_pass": self._decode(
                get_path(row, self.source_fail_to_pass), self.source_fail_to_pass
            ),
        }
        if self.source_pass_to_pass:
            tests["pass_to_pass"] = self._decode(
                get_path(row, self.source_pass_to_pass), self.source_pass_to_pass
            )
        verifiers = data.setdefault("verifiers", [])
        verifiers.append({"type": "execution", "tests": tests})

    def invert(self, out: dict[str, Any], item: dict[str, Any]) -> None:
        tests = _first_verifier(item, "execution")["tests"]
        set_path(out, self.source_test_patch, tests["test_patch"])
        set_path(out, self.source_fail_to_pass, self._encode(tests["fail_to_pass"]))
        if self.source_pass_to_pass:
            set_path(out, self.source_pass_to_pass, self._encode(tests["pass_to_pass"]))


class ChoiceMatchFromOnehotTransform(UepModel):
    """one-hot 标签列表（恰一个 1）→ ``choice_match``（id 为下标字符串）。"""

    op: Literal["choice_match_from_onehot"]
    source: str = Field(min_length=1)
    options_target: str = "task.options"  # 反演时由此取选项数还原 one-hot 长度

    def apply(self, data: dict[str, Any], row: dict[str, Any], row_idx: int) -> None:
        labels = get_path(row, self.source)
        hot = [i for i, flag in enumerate(labels) if flag == 1]
        if len(hot) != 1:
            raise MappingApplyError(f"{self.source!r} 应为恰含一个 1 的 one-hot，得到 {labels!r}")
        verifiers = data.setdefault("verifiers", [])
        verifiers.append({"type": "choice_match", "answer_ids": [str(hot[0])]})

    def invert(self, out: dict[str, Any], item: dict[str, Any]) -> None:
        idx = int(_first_verifier(item, "choice_match")["answer_ids"][0])
        count = len(get_path(item, self.options_target))
        set_path(out, self.source, [1 if i == idx else 0 for i in range(count)])


class RelevanceFromQrelsTransform(UepModel):
    """行内 qrels 清单 → ``retrieval`` Verifier 的 relevance（协议侧 doc_id 为 str）。"""

    op: Literal["relevance_from_qrels"]
    source: str = Field(min_length=1)
    doc_id_key: str = "corpus-id"
    grade_key: str = "score"
    id_dtype: Literal["int", "str"] = "str"  # 反演时恢复源 id 类型
    metrics: list[str] = Field(default_factory=lambda: ["ndcg@10"])

    def apply(self, data: dict[str, Any], row: dict[str, Any], row_idx: int) -> None:
        qrels = get_path(row, self.source)
        if not isinstance(qrels, list) or not qrels:
            raise MappingApplyError(f"{self.source!r} 应为非空 qrels 列表，得到 {qrels!r}")
        relevance = []
        for entry in qrels:
            if self.doc_id_key not in entry or self.grade_key not in entry:
                raise MappingApplyError(
                    f"{self.source!r} 条目缺 {self.doc_id_key!r}/{self.grade_key!r}: {entry!r}"
                )
            relevance.append(
                {"doc_id": str(entry[self.doc_id_key]), "grade": entry[self.grade_key]}
            )
        verifiers = data.setdefault("verifiers", [])
        verifiers.append({"type": "retrieval", "relevance": relevance, "metrics": self.metrics})

    def invert(self, out: dict[str, Any], item: dict[str, Any]) -> None:
        verifier = _first_verifier(item, "retrieval")
        qrels = []
        for label in verifier["relevance"]:
            doc_id = int(label["doc_id"]) if self.id_dtype == "int" else label["doc_id"]
            qrels.append({self.doc_id_key: doc_id, self.grade_key: label["grade"]})
        set_path(out, self.source, qrels)


class TextMatchFromSplitTransform(UepModel):
    """取源字段中分隔符之后的尾段 → ``text_match``（如求解过程末尾的最终答案）。

    派生字段：反演为 no-op——完整原文须另经 table 拷贝保存（如 metadata.solution），
    否则映射不满足"源字段全覆盖"断言。
    """

    op: Literal["text_match_from_split"]
    source: str = Field(min_length=1)
    separator: str = Field(min_length=1)

    def apply(self, data: dict[str, Any], row: dict[str, Any], row_idx: int) -> None:
        raw = get_path(row, self.source)
        if not isinstance(raw, str) or self.separator not in raw:
            raise MappingApplyError(f"{self.source!r} 缺少分隔符 {self.separator!r}: {raw!r}")
        expected = raw.split(self.separator)[-1].strip()
        if not expected:
            raise MappingApplyError(f"{self.source!r} 分隔符后为空，无法提取参考答案")
        verifiers = data.setdefault("verifiers", [])
        verifiers.append({"type": "text_match", "expected": expected})

    def invert(self, out: dict[str, Any], item: dict[str, Any]) -> None:
        return None


class TextMatchFromIdealTransform(UepModel):
    """参考答案（str 或 list[str]）→ ``text_match`` Verifier；形状无损保持以支持往返。"""

    op: Literal["text_match_from_ideal"]
    source: str = Field(min_length=1)

    def apply(self, data: dict[str, Any], row: dict[str, Any], row_idx: int) -> None:
        ideal = get_path(row, self.source)
        if not isinstance(ideal, str | list):
            raise MappingApplyError(
                f"{self.source!r} 应为 str 或 list，得到 {type(ideal).__name__}"
            )
        verifiers = data.setdefault("verifiers", [])
        verifiers.append({"type": "text_match", "expected": ideal})

    def invert(self, out: dict[str, Any], item: dict[str, Any]) -> None:
        expected = _first_verifier(item, "text_match")["expected"]
        set_path(out, self.source, expected)


class StepsFromMessagesTransform(UepModel):
    """chat 消息列表 → ``trajectory`` Steps（role/content 一一对应，可反演）。"""

    op: Literal["steps_from_messages"]
    source: str = Field(min_length=1)
    target: str = "trajectory"

    def apply(self, data: dict[str, Any], row: dict[str, Any], row_idx: int) -> None:
        messages = get_path(row, self.source)
        steps = []
        for message in messages:
            unmapped = set(message) - {"role", "content"}
            if unmapped:
                raise MappingApplyError(f"消息含未映射键（会丢信息，拒绝转换）: {sorted(unmapped)}")
            steps.append({"role": message["role"], "content": message["content"]})
        set_path(data, self.target, steps)

    def invert(self, out: dict[str, Any], item: dict[str, Any]) -> None:
        steps = get_path(item, self.target)
        messages = [{"role": s["role"], "content": s["content"]} for s in steps]
        set_path(out, self.source, messages)


class QuestionFromLastUserTransform(UepModel):
    """最后一条 user 消息 → ``task.question``（qa 退化视图；派生字段，反演丢弃）。"""

    op: Literal["question_from_last_user"]
    source: str = Field(min_length=1)
    target: str = "task.question"

    def apply(self, data: dict[str, Any], row: dict[str, Any], row_idx: int) -> None:
        messages = get_path(row, self.source)
        user_messages = [m for m in messages if m.get("role") == "user"]
        if not user_messages:
            raise MappingApplyError("无 user 消息，无法派生题面")
        content = user_messages[-1]["content"]
        if not isinstance(content, str):
            raise MappingApplyError(f"user 消息内容应为字符串，得到 {type(content).__name__}")
        set_path(data, self.target, content)

    def invert(self, out: dict[str, Any], item: dict[str, Any]) -> None:
        return None


Transform = Annotated[
    ConstTransform
    | FormatIdTransform
    | OptionsFromTextsTransform
    | OptionsFromPairsTransform
    | OptionsFromFieldsTransform
    | ChoiceMatchFromIndexTransform
    | ChoiceMatchFromLabelTransform
    | ChoiceMatchFromOnehotTransform
    | ExecutionFromFieldsTransform
    | ExecutionFromPatchFieldsTransform
    | RelevanceFromQrelsTransform
    | TextMatchFromSplitTransform
    | TextMatchFromIdealTransform
    | StepsFromMessagesTransform
    | QuestionFromLastUserTransform,
    Field(discriminator="op"),
]


# ---------------------------------------------------------------- 映射表模型与加载


class MappingTable(UepModel):
    """mapping.yaml 的结构（SPEC §7.1）：一等维护物，进评审、留 changelog。"""

    format: str = Field(min_length=1)
    version: str = Field(min_length=1)
    table: dict[str, str] = Field(default_factory=dict)
    transforms: list[Transform] = Field(default_factory=list)
    roundtrip_exempt: list[str] = Field(default_factory=list)
    changelog: list[str] = Field(default_factory=list)

    def covered_source_fields(self) -> set[str]:
        """映射消费到的源顶层字段——供"源字段全覆盖"断言（还原能力的前提）。"""
        fields = {src.split(".")[0] for src in self.table.values()}
        for transform in self.transforms:
            # 约定：算子中名为 sources / source* 的字段即源字段路径——新算子自动纳入审计
            for field_name in type(transform).model_fields:
                if field_name == "sources":
                    for src in getattr(transform, field_name) or []:
                        fields.add(src.split(".")[0])
                elif field_name.startswith("source"):
                    src = getattr(transform, field_name)
                    if src:
                        fields.add(src.split(".")[0])
        return fields


@dataclass(frozen=True)
class LoadedMapping:
    """已加载映射 + 内容哈希（哈希进 Provenance.mapping_hash，变更即可见）。"""

    mapping: MappingTable
    name: str
    sha256: str

    @classmethod
    def from_dict(cls, data: dict[str, Any], *, name: str) -> "LoadedMapping":
        canonical = json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return cls(MappingTable.model_validate(data), name, hashlib.sha256(canonical).hexdigest())

    @classmethod
    def from_file(cls, path: Path) -> "LoadedMapping":
        raw = path.read_bytes()
        data = yaml.safe_load(raw)
        return cls(MappingTable.model_validate(data), path.name, hashlib.sha256(raw).hexdigest())


# ---------------------------------------------------------------- 应用与反演


def apply_mapping(
    rows: Iterable[dict[str, Any]],
    loaded: LoadedMapping,
    *,
    dataset: str,
    adapter: str,
    extra_fields: dict[str, Any] | None = None,
) -> list[EvalItem]:
    """源行 → EvalItem：table 拷贝 → 算子按序执行 → 盖 Provenance 溯源戳 → 校验。"""
    items: list[EvalItem] = []
    for row_idx, row in enumerate(rows):
        data: dict[str, Any] = {}
        try:
            for canonical, source in loaded.mapping.table.items():
                set_path(data, canonical, get_path(row, source))
            for transform in loaded.mapping.transforms:
                transform.apply(data, row, row_idx)
        except MappingApplyError as exc:
            raise MappingApplyError(f"第 {row_idx} 行: {exc}") from exc
        if extra_fields:
            data.update(extra_fields)
        data["source"] = {
            "dataset": dataset,
            "adapter": adapter,
            "adapter_version": __version__,
            "mapping_table": loaded.name,
            "mapping_hash": f"sha256:{loaded.sha256}",
            "converted_at": date.today().isoformat(),
        }
        items.append(EvalItem.model_validate(data))
    return items


def invert_mapping(
    items: Iterable[EvalItem | dict[str, Any]], loaded: LoadedMapping
) -> list[dict[str, Any]]:
    """EvalItem → 源行（还原义务，SPEC §7.4）：按同一张表反演；UEP 侧生成物自然丢弃。"""
    rows: list[dict[str, Any]] = []
    for item in items:
        item_dict = item.model_dump(mode="json") if isinstance(item, EvalItem) else item
        out: dict[str, Any] = {}
        for canonical, source in loaded.mapping.table.items():
            set_path(out, source, get_path(item_dict, canonical))
        for transform in loaded.mapping.transforms:
            transform.invert(out, item_dict)
        rows.append(out)
    return rows

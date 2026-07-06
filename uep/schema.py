"""UEP v2 协议 Schema——SPEC（docs/uep-v2-spec.md）§2–§6 的 Pydantic 实现。

clean-room 设计要点：
- 题面归 task、打分归 verifiers：正确答案只存在于 Verifier（P2 自含，单一事实源）；
- 全部内容字符串入库即 NFC 规范化（P5），协议层不做默认 ASCII 化/大小写折叠；
- ``extra="forbid"``：未知字段一律拒绝——协议之外的信息只允许进 ``extras``（P3 纪律辖区）。
"""

import re
import unicodedata
from typing import Annotated, Any, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    field_validator,
    model_validator,
)

from uep import SUPPORTED_PROTOCOL


def _nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


#: 内容字符串：入库即 NFC（SPEC §2 文本规范化）
NFCStr = Annotated[str, AfterValidator(_nfc)]

_LANG_RE = re.compile(r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{1,8})*$")
_VERSION_RE = re.compile(r"^\d+\.\d+$")


def _check_lang(tag: str) -> str:
    if not _LANG_RE.match(tag):
        raise ValueError(f"非法 BCP-47 语言标签 / invalid BCP-47 tag: {tag!r}")
    return tag


LangTag = Annotated[str, AfterValidator(_check_lang)]


def _check_protocol_version(value: str) -> str:
    if not _VERSION_RE.match(value):
        raise ValueError(f"协议版本须为 major.minor / bad version: {value!r}")
    if value.split(".")[0] != SUPPORTED_PROTOCOL.split(".")[0]:
        raise ValueError(
            f"协议大版本不受支持 / unsupported major: {value!r} (supported {SUPPORTED_PROTOCOL})"
        )
    return value


ProtocolVersion = Annotated[str, AfterValidator(_check_protocol_version)]


class UepModel(BaseModel):
    """协议基模型：未知字段一律拒绝。"""

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------- 任务原型（SPEC §3）


class QaTask(UepModel):
    type: Literal["qa"] = "qa"
    question: NFCStr = Field(min_length=1)


class ChoiceOption(UepModel):
    id: str = Field(min_length=1)
    text: NFCStr


class ChoicesTask(UepModel):
    type: Literal["choices"] = "choices"
    question: NFCStr = Field(min_length=1)
    options: list[ChoiceOption] = Field(min_length=2)
    multi_select: bool = False

    @field_validator("options")
    @classmethod
    def _unique_ids(cls, options: list[ChoiceOption]) -> list[ChoiceOption]:
        ids = [o.id for o in options]
        if len(ids) != len(set(ids)):
            raise ValueError("选项 id 重复 / duplicate option ids")
        return options


class CodeGenerationTask(UepModel):
    type: Literal["code_generation"] = "code_generation"
    prompt: NFCStr = Field(min_length=1)
    language: str = Field(min_length=1)
    starter_code: NFCStr | None = None


class PatchRepairTask(UepModel):
    type: Literal["patch_repair"] = "patch_repair"
    repo: str = Field(min_length=1)
    base_commit: str = Field(min_length=1)
    problem_statement: NFCStr = Field(min_length=1)


class CorpusDoc(UepModel):
    doc_id: str = Field(min_length=1)
    title: NFCStr | None = None
    text: NFCStr


class Corpus(UepModel):
    """语料：引用式（uri）或内联（docs），二选一（大语料必须引用式防 OOM）。"""

    uri: str | None = None
    docs: list[CorpusDoc] | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> "Corpus":
        if (self.uri is None) == (self.docs is None):
            raise ValueError("corpus 须且只须提供 uri 或 docs 之一 / exactly one of uri|docs")
        return self


class RetrievalTask(UepModel):
    type: Literal["retrieval"] = "retrieval"
    query: NFCStr = Field(min_length=1)
    corpus: Corpus


class CustomTask(UepModel):
    """受控逃生舱（SPEC §3.6）：必须挂已登记的原型提案 ID。"""

    type: Literal["custom"] = "custom"
    schema_ref: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)


Task = Annotated[
    QaTask | ChoicesTask | CodeGenerationTask | PatchRepairTask | RetrievalTask | CustomTask,
    Field(discriminator="type"),
]


# ---------------------------------------------------------------- 环境与轨迹（SPEC §4）


class Asset(UepModel):
    uri: str = Field(min_length=1)
    media_type: str | None = None
    lang: LangTag | None = None


class Context(UepModel):
    environment: str | None = None
    setup: NFCStr | dict[str, Any] | None = None
    assets: list[Asset] = Field(default_factory=list)


class ToolCall(UepModel):
    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class Step(UepModel):
    role: Literal["user", "assistant", "system", "tool"]
    content: NFCStr | dict[str, Any] | None = None
    tool_call: ToolCall | None = None
    tool_result: Any = None
    state_delta: dict[str, Any] | None = None
    at: float | None = None


class Evidence(UepModel):
    source: str = Field(min_length=1)
    span: list[int] | list[str] | None = None
    content: NFCStr


# ---------------------------------------------------------------- 留痕（SPEC §7）


class Provenance(UepModel):
    dataset: str = Field(min_length=1)
    adapter: str = Field(min_length=1)
    adapter_version: str = Field(min_length=1)
    mapping_table: str = Field(min_length=1)
    mapping_hash: str = Field(min_length=1)
    converted_at: str = Field(min_length=1, description="ISO 8601 日期或时间")


# ---------------------------------------------------------------- Verifier（SPEC §5）


class Normalization(UepModel):
    """text_match 归一化参数——双语安全默认（SPEC §5）。"""

    unicode: Literal["NFC"] = "NFC"
    case_fold: bool = False
    strip_whitespace: bool = True
    width_fold: bool = True
    cjk_punct_fold: bool = False


class ChoiceMatchVerifier(UepModel):
    type: Literal["choice_match"] = "choice_match"
    answer_ids: list[str] = Field(min_length=1)


class TextMatchVerifier(UepModel):
    type: Literal["text_match"] = "text_match"
    expected: NFCStr | list[NFCStr]
    normalize: Normalization = Field(default_factory=Normalization)


class RegexVerifier(UepModel):
    type: Literal["regex"] = "regex"
    pattern: str = Field(min_length=1)
    flags: str | None = None
    target_group: int | str | None = None

    @field_validator("pattern")
    @classmethod
    def _compilable(cls, pattern: str) -> str:
        re.compile(pattern)
        return pattern


class FileSpec(UepModel):
    path: str = Field(min_length=1)
    content: str


class TestSuite(UepModel):
    language: str = Field(min_length=1)
    setup: str | None = None
    files: list[FileSpec] = Field(default_factory=list)
    test_code: str | None = None
    assertions: list[str] = Field(default_factory=list)
    entry_point: str | None = None
    harness: Literal["pytest", "exec"] = "pytest"
    # 仓库级修复判分三要素（2026-07-04 提案批准：docs/proposals/2026-07-patch-grading-fields.md）
    test_patch: NFCStr | None = None
    fail_to_pass: list[str] = Field(default_factory=list)
    pass_to_pass: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _has_payload(self) -> "TestSuite":
        has_patch_grading = bool(self.test_patch) and bool(self.fail_to_pass)
        if not self.test_code and not self.assertions and not has_patch_grading:
            raise ValueError(
                "TestSuite 必须携带 test_code、assertions 或 test_patch+fail_to_pass"
                "（Verifier 自含，P2）"
            )
        return self


class Sandbox(UepModel):
    timeout_s: int = Field(default=30, gt=0)
    network: bool = False
    memory_mb: int = Field(default=512, gt=0)
    image: str | None = None


class ExecutionVerifier(UepModel):
    type: Literal["execution"] = "execution"
    tests: TestSuite
    sandbox: Sandbox = Field(default_factory=Sandbox)


class RelevanceLabel(UepModel):
    doc_id: str = Field(min_length=1)
    grade: int = Field(ge=0)


class RetrievalVerifier(UepModel):
    type: Literal["retrieval"] = "retrieval"
    relevance: list[RelevanceLabel] = Field(min_length=1)
    metrics: list[str] = Field(default_factory=lambda: ["ndcg@10"])


class JudgeModel(UepModel):
    provider: str = Field(min_length=1)
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)


class LlmJudgeVerifier(UepModel):
    type: Literal["llm_judge"] = "llm_judge"
    model: JudgeModel
    prompt_template: NFCStr = Field(min_length=1)
    template_hash: str = Field(min_length=1)
    temperature: float = 0.0
    rubric: NFCStr | None = None


class CompositeVerifier(UepModel):
    """复合验证（Agent 任务常态，SPEC §5）。"""

    type: Literal["composite"] = "composite"
    mode: Literal["all_of", "any_of", "weighted"]
    children: list["Verifier"] = Field(min_length=2)
    weights: list[float] | None = None

    @model_validator(mode="after")
    def _weights_match(self) -> "CompositeVerifier":
        if self.mode == "weighted":
            if not self.weights or len(self.weights) != len(self.children):
                raise ValueError("weighted 模式须提供与 children 等长的 weights")
        elif self.weights is not None:
            raise ValueError("仅 weighted 模式允许 weights")
        return self


Verifier = Annotated[
    ChoiceMatchVerifier
    | TextMatchVerifier
    | RegexVerifier
    | ExecutionVerifier
    | RetrievalVerifier
    | LlmJudgeVerifier
    | CompositeVerifier,
    Field(discriminator="type"),
]

CompositeVerifier.model_rebuild()


# ---------------------------------------------------------------- EvalItem（SPEC §2）


class EvalItem(UepModel):
    uep_version: ProtocolVersion = SUPPORTED_PROTOCOL
    id: str = Field(min_length=1)
    lang: list[LangTag] = Field(min_length=1)
    task: Task
    context: Context | None = None
    trajectory: list[Step] | None = None
    verifiers: list[Verifier] = Field(min_length=1)
    evidence: list[Evidence] = Field(default_factory=list)
    source: Provenance | None = None
    source_map: dict[str, str] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    extras: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------- Manifest（SPEC §6）


class Origin(UepModel):
    format: str = Field(min_length=1)
    uri: str | None = None


class Description(UepModel):
    zh: NFCStr | None = None
    en: NFCStr | None = None


class Manifest(UepModel):
    uep_version: ProtocolVersion = SUPPORTED_PROTOCOL
    name: str = Field(min_length=1)
    license: str = Field(min_length=1, description="SPDX 标识；不明确须显式 'unknown'")
    contains_pii: StrictBool | None = Field(
        default=None,
        description="是否含个人敏感信息；缺省=未声明（三态合规位，旧 NFR4 承接；"
        "严格布尔——合规声明不接受 'yes'/1 等方言强转）",
    )
    languages: list[LangTag] = Field(min_length=1)
    task_types: dict[str, int] = Field(default_factory=dict)
    size: int = Field(ge=0)
    origin: Origin | None = None
    provenance: Provenance | None = None
    description: Description | None = None

    @model_validator(mode="after")
    def _sizes_consistent(self) -> "Manifest":
        if self.task_types and sum(self.task_types.values()) != self.size:
            raise ValueError("task_types 计数之和须等于 size / task_types must sum to size")
        return self

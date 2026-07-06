"""UEP 命令行入口（argparse，零额外依赖）。

动词：
    uep validate <items.jsonl | manifest.json>      # 校验（manifest.json 文件名自动分流）
    uep convert  <源文件> --from <格式> -o <目录>    # 落盘 items.jsonl + manifest.json
    uep export   <items.jsonl> --to <目标> -o <目录> # Runner 任务包
    管理面（FR-5.1–5.7）：
    uep list / show / stats                          # 只读查看
    uep filter / slice / sample / merge -o <目录>    # 组卷——产物即新数据集，可再 validate/export

格式/目标名不写死在本文件（禁名 lint）：一律来自适配器注册表，按模块能力分发
（``import_csv``/``import_rows`` 导入；``export_task``/``export_samples`` 导出）。
数据语义在 uep/dataset_ops.py（纯函数）；本文件只做参数、IO 与双语文案。
"""

import argparse
import importlib
import json
import re
import sys
from pathlib import Path

from pydantic import ValidationError

from uep import SUPPORTED_PROTOCOL, __version__
from uep.adapters import REGISTRY
from uep.conformance import check_manifest, check_touchstones
from uep.dataset_io import read_items, write_dataset
from uep.dataset_ops import (
    dataset_stats,
    filter_items,
    item_gist,
    merge_items,
    sample_items,
    slice_items,
)
from uep.i18n import resolve_lang, t
from uep.schema import Manifest
from uep.validate import validate_items_jsonl, validate_manifest


def _add_lang(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--lang", choices=["zh", "en"], default=None, help="输出语言 / output language"
    )


def _registry_info(name: str):
    return next((info for info in REGISTRY if info.name == name), None)


def _load_items(path_str: str, lang: str) -> tuple[list | None, int]:
    """读入条目文件；失败已打印双语报错，返回 (None, 退出码)。"""
    path = Path(path_str)
    if not path.exists():
        print(t("io.missing", lang, path=path), file=sys.stderr)
        return None, 2
    try:
        return read_items(path), 0
    except ValueError as exc:
        print(t("io.invalid_items", lang, detail=exc), file=sys.stderr)
        return None, 1


def _run_validate(args: argparse.Namespace, lang: str) -> int:
    path = Path(args.path)
    if not path.exists():
        print(t("io.missing", lang, path=path), file=sys.stderr)
        return 2
    issues = validate_manifest(path) if path.name == "manifest.json" else validate_items_jsonl(path)
    for issue in issues:
        stream = sys.stderr if issue.severity == "error" else sys.stdout
        print(issue.render(lang), file=stream)
    errors = sum(1 for issue in issues if issue.severity == "error")
    warnings = sum(1 for issue in issues if issue.severity == "warning")
    if errors:
        print(t("validate.summary", lang, errors=errors, warnings=warnings), file=sys.stderr)
        return 1
    print(t("validate.ok", lang) + " · " + t("validate.summary", lang, errors=0, warnings=warnings))
    return 0


def _run_convert(args: argparse.Namespace, lang: str) -> int:
    source = Path(args.input)
    if not source.exists():
        print(t("io.missing", lang, path=source), file=sys.stderr)
        return 2
    info = _registry_info(args.source_format)
    known = ", ".join(sorted(entry.name for entry in REGISTRY))
    if info is None:
        print(
            t("convert.unknown_format", lang, name=args.source_format, known=known),
            file=sys.stderr,
        )
        return 2
    module = importlib.import_module(info.module)
    if hasattr(module, "import_csv"):
        items = module.import_csv(
            source,
            question_col=args.question_col,
            answer_col=args.answer_col,
            content_lang=args.content_lang,
        )
    elif hasattr(module, "import_rows"):
        rows = [
            json.loads(line)
            for line in source.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        try:
            items = module.import_rows(rows)
        except TypeError:
            print(t("convert.unsupported", lang, name=info.name), file=sys.stderr)
            return 2
    else:
        print(t("convert.unsupported", lang, name=info.name), file=sys.stderr)
        return 2
    out_dir = Path(args.out)
    contains_pii = None if args.contains_pii is None else args.contains_pii == "true"
    items_path, manifest_path = write_dataset(
        items,
        out_dir,
        name=args.name or out_dir.name,
        license=args.license,
        contains_pii=contains_pii,
    )
    print(t("convert.ok", lang, count=len(items), items=items_path, manifest=manifest_path))
    return 0


def _run_export(args: argparse.Namespace, lang: str) -> int:
    items, code = _load_items(args.input, lang)
    if items is None:
        return code
    items_file = Path(args.input)
    info = _registry_info(args.target)
    known = ", ".join(sorted(entry.name for entry in REGISTRY if entry.mapping_file is None))
    if info is None:
        print(t("export.unknown_target", lang, name=args.target, known=known), file=sys.stderr)
        return 2
    module = importlib.import_module(info.module)
    task_name = args.task_name or items_file.parent.name or "uep_task"
    out_dir = Path(args.out)
    try:
        if hasattr(module, "export_task"):
            path = module.export_task(
                items, task_name=task_name, out_dir=out_dir, answer_pattern=args.answer_pattern
            )
        elif hasattr(module, "export_samples"):
            samples = module.export_samples(items)
            out_dir.mkdir(parents=True, exist_ok=True)
            path = out_dir / f"{task_name}.jsonl"
            path.write_text(module.dump_jsonl(samples), encoding="utf-8")
        else:
            print(t("export.unknown_target", lang, name=args.target, known=known), file=sys.stderr)
            return 2
    except ValueError as exc:
        print(t("export.failed", lang, detail=exc), file=sys.stderr)
        return 1
    print(t("export.ok", lang, path=path))
    return 0


# ---------------------------------------------------------------- 管理面（FR-5.1–5.7）

_RANGE = re.compile(r"^(\d+):(\d+)$")


def _write_dataset_dir(items: list, args: argparse.Namespace, lang: str) -> int:
    """组卷动词共用尾巴：空结果拒写（exit 1）；否则落盘新数据集并汇报。"""
    if not items:
        print(t("verbs.empty", lang), file=sys.stderr)
        return 1
    out_dir = Path(args.out)
    items_path, manifest_path = write_dataset(
        items, out_dir, name=args.name or out_dir.name, license=args.license
    )
    print(t("dataset.wrote", lang, count=len(items), items=items_path, manifest=manifest_path))
    return 0


def _run_list(args: argparse.Namespace, lang: str) -> int:
    items, code = _load_items(args.input, lang)
    if items is None:
        return code
    for item in items:
        print(f"{item.id}\t{item.task.type}\t{','.join(item.lang)}\t{item_gist(item)}")
    print(t("list.total", lang, n=len(items)))
    return 0


def _run_show(args: argparse.Namespace, lang: str) -> int:
    items, code = _load_items(args.input, lang)
    if items is None:
        return code
    for item in items:
        if item.id == args.item_id:
            payload = json.loads(item.model_dump_json(exclude_none=True))
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
    print(t("show.not_found", lang, id=args.item_id), file=sys.stderr)
    return 1


def _run_filter(args: argparse.Namespace, lang: str) -> int:
    if args.task_type is None and args.task_lang is None:
        print(t("filter.no_predicate", lang), file=sys.stderr)
        return 2
    items, code = _load_items(args.input, lang)
    if items is None:
        return code
    kept = filter_items(items, task_type=args.task_type, lang=args.task_lang)
    return _write_dataset_dir(kept, args, lang)


def _run_slice(args: argparse.Namespace, lang: str) -> int:
    match = _RANGE.match(args.range)
    if not match or int(match.group(1)) >= int(match.group(2)):
        print(t("slice.bad_range", lang, value=args.range), file=sys.stderr)
        return 2
    items, code = _load_items(args.input, lang)
    if items is None:
        return code
    return _write_dataset_dir(
        slice_items(items, int(match.group(1)), int(match.group(2))), args, lang
    )


def _run_sample(args: argparse.Namespace, lang: str) -> int:
    if args.n < 1:
        print(t("sample.bad_n", lang, n=args.n), file=sys.stderr)
        return 2
    items, code = _load_items(args.input, lang)
    if items is None:
        return code
    if args.n > len(items):
        print(t("sample.too_large", lang, n=args.n, size=len(items)), file=sys.stderr)
        return 1
    print(t("sample.seed", lang, seed=args.seed))
    return _write_dataset_dir(sample_items(items, args.n, args.seed), args, lang)


def _run_merge(args: argparse.Namespace, lang: str) -> int:
    if len(args.inputs) < 2:
        print(t("merge.need_two", lang), file=sys.stderr)
        return 2
    groups = []
    for path in args.inputs:
        items, code = _load_items(path, lang)
        if items is None:
            return code
        groups.append(items)
    merged, conflicts = merge_items(groups)
    if conflicts:
        print(t("merge.conflict", lang, ids=", ".join(conflicts)), file=sys.stderr)
        return 1
    return _write_dataset_dir(merged, args, lang)


def _report_touchstones(items: list, lang: str) -> bool:
    """打印试金石检查结果；返回是否失败。"""
    result = check_touchstones(items)
    note = " " + t("conform.custom_note", lang, n=result.skipped) if result.skipped else ""
    if result.status == "pass":
        print(t("conform.touchstones.pass", lang) + note)
        return False
    print(t("conform.touchstones.fail", lang, n=len(result.problems)) + note, file=sys.stderr)
    for problem in result.problems[:20]:
        print(f"  - {problem}", file=sys.stderr)
    return True


def _report_manifest(items: list, manifest_path: Path, lang: str) -> bool:
    """打印清单检查结果；返回是否失败。缺清单=跳过（items 单独分发合法）。"""
    if not manifest_path.exists():
        print(t("conform.manifest.skip", lang, path=manifest_path))
        return False
    try:
        manifest = Manifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    except ValidationError as exc:
        print(t("conform.manifest.invalid", lang, detail=exc), file=sys.stderr)
        return True
    result = check_manifest(items, manifest)
    if result.status == "pass":
        print(t("conform.manifest.pass", lang))
        return False
    print(t("conform.manifest.fail", lang), file=sys.stderr)
    for problem in result.problems:
        print(f"  - {problem}", file=sys.stderr)
    return True


def _run_conform(args: argparse.Namespace, lang: str) -> int:
    items, code = _load_items(args.input, lang)
    if items is None:
        return code
    print(t("conform.schema.pass", lang, n=len(items)))
    failed = _report_touchstones(items, lang)
    failed = _report_manifest(items, Path(args.input).parent / "manifest.json", lang) or failed
    if failed:
        print(t("conform.fail", lang), file=sys.stderr)
        return 1
    print(t("conform.ok", lang))
    return 0


def _run_stats(args: argparse.Namespace, lang: str) -> int:
    items, code = _load_items(args.input, lang)
    if items is None:
        return code
    stats = dataset_stats(items)
    print(t("stats.size", lang, n=len(items)))
    for key in ("task_types", "languages", "verifiers"):
        detail = ", ".join(
            f"{name}={count}"
            for name, count in sorted(stats[key].items(), key=lambda kv: (-kv[1], kv[0]))
        )
        print(t(f"stats.{key}", lang, detail=detail))
    return 0


def _add_dataset_out_args(parser: argparse.ArgumentParser) -> None:
    """组卷动词共用输出参数（与 convert 同一套约定）。"""
    parser.add_argument("-o", "--out", required=True, help="输出目录")
    parser.add_argument("--name", default=None, help="数据集名（默认取输出目录名）")
    parser.add_argument("--license", default="unknown", help="SPDX 标识；不明确须显式 unknown")


def _add_verb_parsers(sub) -> None:
    p_list = sub.add_parser("list", help="逐行概览条目（id/类型/语言/题面摘要）")
    p_list.add_argument("input")
    _add_lang(p_list)

    p_show = sub.add_parser("show", help="按 id 显示单条完整 JSON")
    p_show.add_argument("input")
    p_show.add_argument("item_id")
    _add_lang(p_show)

    p_filter = sub.add_parser("filter", help="按谓词筛出新数据集（AND 组合）")
    p_filter.add_argument("input")
    p_filter.add_argument("--type", dest="task_type", default=None, help="任务类型")
    p_filter.add_argument("--task-lang", default=None, help="条目语言（BCP-47 前缀匹配）")
    _add_dataset_out_args(p_filter)
    _add_lang(p_filter)

    p_slice = sub.add_parser("slice", help="按半开区间切出新数据集")
    p_slice.add_argument("input")
    p_slice.add_argument("--range", required=True, help="START:STOP（0 起，半开）")
    _add_dataset_out_args(p_slice)
    _add_lang(p_slice)

    p_sample = sub.add_parser("sample", help="定 seed 随机抽样出新数据集（保原库顺序）")
    p_sample.add_argument("input")
    p_sample.add_argument("--n", type=int, required=True, help="抽样条数")
    p_sample.add_argument("--seed", type=int, default=0, help="随机种子（默认 0，可复现）")
    _add_dataset_out_args(p_sample)
    _add_lang(p_sample)

    p_merge = sub.add_parser("merge", help="合并多个条目文件（id 冲突即拒绝）")
    p_merge.add_argument("inputs", nargs="+")
    _add_dataset_out_args(p_merge)
    _add_lang(p_merge)

    p_stats = sub.add_parser("stats", help="统计条目数与类型/语言/验证器分布")
    p_stats.add_argument("input")
    _add_lang(p_stats)

    p_conform = sub.add_parser("conform", help="一致性检查（schema+试金石可消费+清单一致）")
    p_conform.add_argument("input")
    _add_lang(p_conform)


_HANDLERS = {
    "validate": _run_validate,
    "convert": _run_convert,
    "export": _run_export,
    "list": _run_list,
    "show": _run_show,
    "filter": _run_filter,
    "slice": _run_slice,
    "sample": _run_sample,
    "merge": _run_merge,
    "stats": _run_stats,
    "conform": _run_conform,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="uep",
        description=f"UEP v2 CLI（protocol {SUPPORTED_PROTOCOL}, package {__version__}）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="校验条目 JSONL 或 manifest.json")
    p_validate.add_argument("path")
    _add_lang(p_validate)

    p_convert = sub.add_parser("convert", help="源格式 → items.jsonl + manifest.json")
    p_convert.add_argument("input")
    p_convert.add_argument("--from", dest="source_format", required=True, help="源格式名（注册表）")
    p_convert.add_argument("-o", "--out", required=True, help="输出目录")
    p_convert.add_argument("--name", default=None, help="数据集名（默认取输出目录名）")
    p_convert.add_argument("--license", default="unknown", help="SPDX 标识；不明确须显式 unknown")
    p_convert.add_argument("--content-lang", default="en", help="条目内容语言（BCP-47）")
    p_convert.add_argument(
        "--contains-pii",
        dest="contains_pii",
        choices=["true", "false"],
        default=None,
        help="是否含个人敏感信息（缺省=未声明）",
    )
    p_convert.add_argument("--question-col", default="question", help="题面列名（表格源）")
    p_convert.add_argument("--answer-col", default="answer", help="答案列名（表格源）")
    _add_lang(p_convert)

    p_export = sub.add_parser("export", help="items.jsonl → Runner 任务包")
    p_export.add_argument("input")
    p_export.add_argument("--to", dest="target", required=True, help="导出目标名（注册表）")
    p_export.add_argument("-o", "--out", required=True, help="输出目录")
    p_export.add_argument("--task-name", default=None, help="任务名（默认取数据集目录名）")
    p_export.add_argument("--answer-pattern", default=None, help="qa 答案抽取正则（可覆写）")
    _add_lang(p_export)

    _add_verb_parsers(sub)

    args = parser.parse_args(argv)
    lang = resolve_lang(args.lang)
    return _HANDLERS[args.command](args, lang)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

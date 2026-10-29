#!/usr/bin/env python3
"""Deterministic preview/apply helper for managed AGENTS.md blocks.

Owned by the core-init-project skill bundle. It never embeds template
content: every managed block is defined by the caller through a template
file that stays with its owning skill. The helper only compares marker
pairs, renders separate diffs, and writes exclusively the explicitly
confirmed selection. It touches no provider, MCP, .gitignore or other
configuration file and uses only the Python standard library.
"""
from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

TARGET_FILENAME = "AGENTS.md"
MANAGED_BLOCK_NAMES = ("CORE-INIT-PROJECT", "SERENA-GORTEX-PROJECT")
STATUS_CURRENT = "current"
STATUS_PRESENT = "present"
STATUS_DRIFT = "drift"
STATUS_MISSING = "missing"
STATUS_BROKEN = "broken"
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_CONFIRMATION_MISMATCH = 3
EXIT_BLOCKED_MARKERS = 4
EXIT_WRITE_ERROR = 5


def marker_pair(name):
    return ("<!-- " + name + ":START -->", "<!-- " + name + ":END -->")


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_target(path):
    if path.is_symlink():
        raise ValueError("Refusing to read through symlink: " + str(path))
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def check_target_path(path):
    if path.is_symlink():
        raise ValueError('Refusing symlink target')
    resolved = path.resolve(strict=False)
    if resolved.parent == Path.home().resolve() or resolved.parent == Path(resolved.anchor):
        raise ValueError('Refusing global/home/root AGENTS.md')
    if resolved.is_dir():
        raise ValueError("Target must be a file, not a directory: " + str(resolved))
    if resolved == Path.home().resolve() or resolved == Path(resolved.anchor):
        raise ValueError("Refusing home or filesystem root as target: " + str(resolved))
    if resolved.name != TARGET_FILENAME:
        raise ValueError("Target must be named " + TARGET_FILENAME + ": " + str(resolved))
    return resolved


def find_occurrences(text, marker):
    positions = []
    start = 0
    while True:
        found = text.find(marker, start)
        if found < 0:
            return positions
        positions.append(found)
        start = found + len(marker)


def analyze_block(text, name):
    """Return status and, for one valid pair, the exact marker span."""
    start_marker, end_marker = marker_pair(name)
    starts = find_occurrences(text, start_marker)
    ends = find_occurrences(text, end_marker)
    mentions = [line for line in text.splitlines() if name in line and ('<!--' in line or ':START' in line or ':END' in line)]
    if any(line.strip() not in (start_marker, end_marker) for line in mentions):
        return dict(name=name, status=STATUS_BROKEN, reason='damaged marker')
    if not starts and not ends:
        return {"name": name, "status": STATUS_MISSING}
    if len(starts) == 1 and len(ends) == 1 and starts[0] < ends[0]:
        return {
            "name": name,
            "status": STATUS_PRESENT,
            "span": (starts[0], ends[0] + len(end_marker)),
        }
    detail = []
    if len(starts) > 1:
        detail.append("duplicate START marker")
    if len(ends) > 1:
        detail.append("duplicate END marker")
    if len(starts) == 1 and len(ends) == 1 and starts[0] > ends[0]:
        detail.append("reversed marker order")
    if len(starts) != len(ends):
        detail.append("unpaired marker")
    return {
        "name": name,
        "status": STATUS_BROKEN,
        "reason": "; ".join(detail) or "invalid marker layout",
    }


def load_template(name, template_path):
    with template_path.open("r", encoding="utf-8", newline="") as handle:
        template = handle.read()
    start_marker, end_marker = marker_pair(name)
    if template.count(start_marker) != 1 or template.count(end_marker) != 1:
        raise ValueError(
            "Template for " + name + " must contain its marker pair exactly once: "
            + str(template_path)
        )
    if template.find(start_marker) > template.find(end_marker):
        raise ValueError("Template for " + name + " has reversed markers: " + str(template_path))
    for other in MANAGED_BLOCK_NAMES:
        if other == name:
            continue
        if any(marker in template for marker in marker_pair(other)):
            raise ValueError(
                "Template for " + name + " must not nest foreign markers: " + str(template_path)
            )
    # Use exactly the marker-bounded segment so comparison and replacement
    # stay byte-stable regardless of surrounding lines in the template file.
    span_start = template.find(start_marker)
    span_end = template.find(end_marker) + len(end_marker)
    if analyze_block(template, name)['status'] == STATUS_BROKEN:
        raise ValueError('Damaged template markers: ' + str(template_path))
    return template[span_start:span_end]


def validate_no_cross_nesting(text, analyses):
    """A valid span must not contain any foreign managed marker."""
    for analysis in analyses:
        span = analysis.get("span")
        if span is None:
            continue
        for other in analyses:
            if other["name"] == analysis["name"]:
                continue
            for marker in marker_pair(other["name"]):
                if marker in text[span[0]:span[1]]:
                    raise ValueError(
                        "nested managed markers: " + other["name"] + " inside "
                        + analysis["name"] + " span"
                    )


def append_block(text, template):
    if text == "":
        return template
    newline = '\r\n' if '\r\n' in text else '\n'
    if not text.endswith('\n'):
        text = text + newline
    return text + newline + template


def plan_result(text, blocks, selection):
    analyses = [analyze_block(text, name) for name in MANAGED_BLOCK_NAMES]
    validate_no_cross_nesting(text, analyses)
    if any(entry['status'] == STATUS_BROKEN for entry in analyses):
        raise ValueError("blocked-markers: damaged managed marker layout")
    known = dict(blocks)
    if any(name not in known for name in selection):
        raise ValueError("Unknown selection")
    report = []
    replacements = []
    additions = []
    for name, template in blocks:
        analysis = next(entry for entry in analyses if entry['name'] == name)
        span = analysis.get('span')
        if span:
            old = text[span[0]:span[1]]
            template = preserve_newlines(old, template)
            status = STATUS_CURRENT if old == template else STATUS_DRIFT
            candidate = text[:span[0]] + template + text[span[1]:]
            if name in selection:
                replacements.append((span[0], span[1], template))
        else:
            status = STATUS_MISSING
            template = preserve_newlines(text, template)
            candidate = append_block(text, template)
            if name in selection:
                additions.append(template)
        report.append(dict(name=name, status=status, selected=name in selection,
                           diff=render_diff(text, candidate, name)))
    result = text
    for start, end, template in sorted(replacements, reverse=True):
        result = result[:start] + template + result[end:]
    for template in additions:
        result = append_block(result, template)
    return result, report


def render_diff(text, result, name):
    if text == result:
        return ""
    return "".join(
        line if line.endswith('\n') else line + '\n\\ No newline at end of file\n'
        for line in difflib.unified_diff(
            text.splitlines(keepends=True),
            result.splitlines(keepends=True),
            fromfile=name + " (current)",
            tofile=name + " (proposed)",
            n=2,
        )
    )


def preserve_newlines(original, updated):
    if "\r\n" in original:
        return updated.replace("\r\n", "\n").replace("\n", "\r\n")
    return updated


def safe_write(path, text):
    if path.is_symlink():
        raise ValueError("Refusing to write through symlink: " + str(path))
    descriptor, temporary_name = tempfile.mkstemp(
        prefix="." + path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    temporary_path = Path(temporary_name)
    try:
        if path.exists():
            os.fchmod(descriptor, path.stat().st_mode & 0o777)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def confirmation_token(target_sha, selection, result_sha):
    payload = json.dumps(
        {
            "target_sha256": target_sha,
            "selected": sorted(selection),
            "result_sha256": result_sha,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_parser():
    parser = argparse.ArgumentParser(
        description="Deterministic managed-block reconcile for AGENTS.md"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(sub):
        sub.add_argument("--target", required=True, type=Path, help="absolute AGENTS.md path")
        sub.add_argument(
            "--block",
            action="append",
            default=[],
            metavar="NAME=TEMPLATE",
            help="managed block name and template file, repeatable",
        )
        sub.add_argument(
            "--select",
            default="",
            help="comma-separated block names, 'none' or empty for no selection",
        )

    subparsers.add_parser("preview", help="read-only diff preview and confirmation token")
    subparsers.add_parser("apply", help="write exactly the confirmed selection").add_argument(
        "--confirm", required=True, help="confirmation token from preview"
    )
    extract = subparsers.add_parser(
        "extract-template", help="Read a managed-block template from its owning Python module"
    )
    extract.add_argument("--source", required=True, type=Path)
    extract.add_argument("--name", required=True)
    add_common(subparsers.choices["preview"])
    add_common(subparsers.choices["apply"])
    return parser


def parse_selection(raw, blocks):
    names = set(name for name, _template in blocks)
    if not raw or raw.strip().lower() == "none":
        return []
    selection = [part.strip() for part in raw.split(",") if part.strip()]
    unknown = [name for name in selection if name not in names]
    if unknown:
        raise ValueError("Unknown selected block(s): " + ", ".join(sorted(unknown)))
    return sorted(set(selection))


def load_blocks(block_args):
    if not block_args:
        raise ValueError("At least one --block NAME=TEMPLATE is required")
    blocks = []
    seen = set()
    for item in block_args:
        if "=" not in item:
            raise ValueError("Invalid --block (expected NAME=TEMPLATE): " + item)
        name, template_path = item.split("=", 1)
        name = name.strip()
        if name not in MANAGED_BLOCK_NAMES or name in seen:
            raise ValueError("Invalid or duplicate block name: " + str(name))
        seen.add(name)
        blocks.append((name, load_template(name, Path(template_path))))
    return blocks


def run_preview_or_apply(args, write):
    target = check_target_path(args.target)
    blocks = load_blocks(args.block)
    selection = parse_selection(args.select, blocks)
    text = read_target(target) if target.exists() else ""
    result, report = plan_result(text, blocks, selection)
    evidence = [(str(Path(item.split('=', 1)[1]).resolve()),
                 sha256_text(read_target(Path(item.split('=', 1)[1]))))
                for item in args.block]
    token = confirmation_token(sha256_text(repr((str(target), target.exists(), text, blocks, evidence))), selection, sha256_text(result))
    if write and token != args.confirm:
        print(
            json.dumps(
                {
                    "target": str(target),
                    "written": False,
                    "error": "confirmation-mismatch: token does not bind this target "
                    "content and selection (wrong token or drifted target)",
                }
            )
        )
        return EXIT_CONFIRMATION_MISMATCH
    broken = [entry for entry in report if entry["status"] == STATUS_BROKEN]
    if broken and write:
        print(
            json.dumps(
                {
                    "target": str(target),
                    "written": False,
                    "error": "blocked-markers",
                    "blocks": report,
                }
            )
        )
        return EXIT_BLOCKED_MARKERS
    changed = result != text
    written = False
    if write and changed:
        encoded = result
        current = read_target(target) if target.exists() else ''
        if current != text or load_blocks(args.block) != blocks:
            raise ValueError('Source or target drift before write')
        safe_write(target, encoded)
        if read_target(target) != encoded:
            print(
                json.dumps(
                    {"target": str(target), "written": False, "error": "verify-failed"}
                )
            )
            return EXIT_WRITE_ERROR
        written = True
        result = encoded
    diffs = {}
    for entry in report:
        diffs[entry['name']] = entry['diff']
    output = {
        "target": str(target),
        "selected": selection,
        "blocks": report,
        "token": token,
        "written": written,
        "changed_planned": changed,
        "diffs": diffs,
    }
    print(json.dumps(output, indent=2))
    return EXIT_OK


def resolve_template_constant(source, name):
    """Resolve a module-level string, optionally an f-string over plain names."""
    tree = ast.parse(source.read_text(encoding="utf-8"))
    constants = {}
    assignments = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
        ):
            assignments[node.targets[0].id] = node.value
    for node_name, value in assignments.items():
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            constants[node_name] = value.value

    def evaluate(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name) and node.id in constants:
            return constants[node.id]
        if isinstance(node, ast.JoinedStr):
            parts = []
            for part in node.values:
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    parts.append(part.value)
                elif isinstance(part, ast.FormattedValue) and isinstance(part.value, ast.Name):
                    if part.value.id not in constants:
                        raise ValueError(
                            "Cannot resolve f-string reference "
                            + repr(part.value.id)
                            + " in "
                            + str(source)
                            + " (only plain string constants are supported)"
                        )
                    parts.append(constants[part.value.id])
                else:
                    raise ValueError("Unsupported template expression in " + str(source))
            return "".join(parts)
        raise ValueError("Unsupported template value for " + repr(name) + " in " + str(source))

    if name not in assignments:
        raise ValueError("No module-level assignment named " + repr(name) + " in " + str(source))
    return evaluate(assignments[name])


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.command == "preview":
            return run_preview_or_apply(args, write=False)
        if args.command == "apply":
            return run_preview_or_apply(args, write=True)
        sys.stdout.write(resolve_template_constant(args.source, args.name))
        return EXIT_OK
    except (ValueError, OSError, SyntaxError) as error:
        print(json.dumps({"error": str(error)}))
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())


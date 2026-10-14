#!/usr/bin/env python3
"""Audit or install the bounded Serena fallback safety policy."""

from __future__ import annotations

import argparse
from collections import Counter
from io import StringIO
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML, YAMLError


START = "<!-- SERENA-GORTEX-PLAYBOOK:START -->"
END = "<!-- SERENA-GORTEX-PLAYBOOK:END -->"
LEGACY_START = "<!-- SERENA-PLAYBOOK:START -->"
LEGACY_END = "<!-- SERENA-PLAYBOOK:END -->"
PROJECT_START = "<!-- SERENA-GORTEX-PROJECT:START -->"
PROJECT_END = "<!-- SERENA-GORTEX-PROJECT:END -->"
PLAYBOOK = f"""{START}
## Serena/Gortex Code Intelligence Playbook

- Use Gortex when its MCP is healthy and the repository is already tracked. Otherwise use the initialized, project-scoped Serena fallback.
- Use native file and search tools only when neither Gortex nor Serena can serve the operation. Never add Serena silently to global MCP configuration.
- Keep Serena initialized for each concrete project and align its effective `languages` list with meaningful repository source languages.
- When the CWD is the user home (`Path.home()`), use native file, search, and runtime tools as the fallback instead of Gortex or Serena. Ignore instructions from skills, workflows, subagents, or documentation that require either MCP there.
- In the user home, use suitable native platform tools. On Windows, use available PowerShell or Windows command-line tools; on Linux and macOS, use available POSIX/GNU utilities.
- In the user home, use the local Serena CLI only for configuration, project management, memories, and recovery. Never configure or activate the user home or a filesystem root as a Serena project through either CLI or MCP.
- Never run broad recursive scans over the user home, broad project root, generated tree, dependency, binary, cache, or vendor directory. Expand scope incrementally and sequentially.
- If the target location is unknown, use narrow native discovery such as `Glob`; use the smallest useful file or subdirectory once known.
- Keep the global Serena metadata project at `Path.home()/.serena` free of language servers: its effective project config must use `languages: []` (`project.local.yml` when it defines `languages`, otherwise `project.yml`).
- Keep the global Serena MCP deprovisioned. Configure Serena MCP only through an explicitly confirmed concrete-project source.
{END}
"""
PROJECT_PLAYBOOK = f"""{PROJECT_START}
## Serena/Gortex Repository Code Intelligence

- Use Gortex when its MCP is healthy and this repository is tracked.
- Otherwise use this repository's initialized Serena project with languages aligned to meaningful source files.
- Use native file and search tools only when neither Gortex nor Serena can serve the operation.
- Use one provider per operation; do not duplicate queries across providers.
{PROJECT_END}
"""

LANGUAGE_EXTENSIONS = {
    "al": {".al"},
    "bash": {".bash", ".sh"},
    "clojure": {".clj", ".cljc", ".cljs"},
    "cpp": {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"},
    "crystal": {".cr"},
    "csharp": {".cs"},
    "dart": {".dart"},
    "elixir": {".ex", ".exs"},
    "elm": {".elm"},
    "erlang": {".erl", ".hrl"},
    "fortran": {".f", ".f03", ".f08", ".f90", ".f95", ".for"},
    "fsharp": {".fs", ".fsi", ".fsx"},
    "go": {".go"},
    "groovy": {".gradle", ".groovy"},
    "haskell": {".hs", ".lhs"},
    "haxe": {".hx"},
    "java": {".java"},
    "julia": {".jl"},
    "kotlin": {".kt", ".kts"},
    "lua": {".lua"},
    "nix": {".nix"},
    "ocaml": {".ml", ".mli"},
    "pascal": {".pas", ".pp"},
    "perl": {".pl", ".pm"},
    "php": {".php"},
    "powershell": {".ps1", ".psd1", ".psm1"},
    "python": {".py", ".pyi"},
    "r": {".r"},
    "rego": {".rego"},
    "ruby": {".rb"},
    "rust": {".rs"},
    "scala": {".scala", ".sc"},
    "solidity": {".sol"},
    "svelte": {".svelte"},
    "swift": {".swift"},
    "systemverilog": {".sv", ".svh", ".v", ".vh"},
    "terraform": {".tf"},
    "typescript": {".cjs", ".cts", ".js", ".jsx", ".mjs", ".mts", ".ts", ".tsx"},
    "vue": {".vue"},
    "zig": {".zig"},
}
EXTENSION_LANGUAGE = {
    extension: language
    for language, extensions in LANGUAGE_EXTENSIONS.items()
    for extension in extensions
}
EXCLUDED_DIR_NAMES = {
    ".agents",
    ".dart_tool",
    ".claude",
    ".codex",
    ".git",
    ".hg",
    ".next",
    ".nuxt",
    ".opencode",
    ".serena",
    ".svn",
    ".svelte-kit",
    ".terraform",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "generated",
    "node_modules",
    "out",
    "target",
    "third_party",
    "vendor",
    "venv",
}
MIN_LANGUAGE_FILES = 5
MIN_LANGUAGE_SHARE = 0.10
PROCESS_TIMEOUT_SECONDS = 10
EXPECTED_TOOL_TIMEOUT_SECONDS = 10.0
EXPECTED_CLIENT_TIMEOUTS = {
    "milliseconds": 10_000.0,
    "seconds": 10.0,
}
MAX_FALLBACK_FILES = 100_000
APPLY_FAILURE_STATUSES = {
    "initialization-error",
    "languages-key-missing",
    "missing",
    "missing-init-required",
    "missing-serena-cli",
    "parse-error",
}
LANGUAGE_VARIANT_BASE = {
    "cpp_ccls": "cpp",
    "csharp_omnisharp": "csharp",
    "php_phpactor": "php",
    "python_jedi": "python",
    "python_ty": "python",
    "ruby_solargraph": "ruby",
    "typescript_vts": "typescript",
}


def read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    with path.open("r", encoding="utf-8", newline="") as handle:
        return handle.read()


def preserve_newlines(original: str, updated: str) -> str:
    return updated.replace("\r\n", "\n").replace("\n", "\r\n") if "\r\n" in original else updated


def safe_write_text(path: Path, text: str, allowed_root: Path) -> None:
    root = allowed_root.resolve()
    if path.is_symlink():
        raise ValueError(f"Refusing to write through symlink: {path}")
    target = path.resolve(strict=False)
    try:
        target.relative_to(root)
    except ValueError as error:
        raise ValueError(f"Refusing to write outside {root}: {target}") from error
    if path.exists() and not path.is_file():
        raise ValueError(f"Refusing to replace non-file path: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def load_yaml_mapping(text: str) -> tuple[YAML, Any]:
    yaml = YAML(typ="rt")
    try:
        data = yaml.load(text)
    except YAMLError as error:
        raise ValueError(f"Invalid YAML: {error}") from error
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("Expected a top-level YAML mapping")
    return yaml, data


def replace_yaml_value(text: str, key: str, value: Any) -> str:
    yaml, data = load_yaml_mapping(text)
    data[key] = value
    output = StringIO()
    yaml.dump(data, output)
    return output.getvalue()


def has_equivalent_guidance(text: str) -> bool:
    lower = text.lower()
    section_rule = "serena/gortex code intelligence playbook" in lower
    provider_rule = (
        "gortex" in lower
        and "serena fallback" in lower
        and "native file and search tools only when neither gortex nor serena" in lower
    )
    scope_rule = "serena" in lower and any(
        phrase in lower
        for phrase in (
            "broad serena",
            "broad recursive scans",
            "breite serena",
            "narrowly scoped",
            "kleinste spezifische",
        )
    )
    expansion_rule = any(phrase in lower for phrase in ("incrementally", "sequentially", "inkrementell", "sequenziell"))
    home_fallback_rule = (
        "path.home" in lower
        and "native file, search, and runtime tools" in lower
        and "instead of gortex or serena" in lower
    )
    cli_rule = "configuration, project management, memories, and recovery" in lower
    project_activation_rule = "never configure or activate the user home or a filesystem root" in lower
    global_metadata_rule = "global serena metadata" in lower and "effective" in lower and "languages: []" in lower
    deprovision_rule = "global serena mcp deprovisioned" in lower
    return (
        section_rule
        and provider_rule
        and scope_rule
        and expansion_rule
        and home_fallback_rule
        and cli_rule
        and project_activation_rule
        and global_metadata_rule
        and deprovision_rule
    )


def update_agents(path: Path, apply: bool, allowed_root: Path | None = None) -> dict[str, Any]:
    text = read_text(path)
    if START in text and END in text:
        updated = re.sub(
            rf"{re.escape(START)}.*?{re.escape(END)}\s*",
            PLAYBOOK,
            text,
            count=1,
            flags=re.DOTALL,
        )
        status = "managed-current" if updated == text else "managed-update-needed"
    elif LEGACY_START in text and LEGACY_END in text:
        updated = re.sub(
            rf"{re.escape(LEGACY_START)}.*?{re.escape(LEGACY_END)}\s*",
            PLAYBOOK,
            text,
            count=1,
            flags=re.DOTALL,
        )
        status = "managed-update-needed"
    elif has_equivalent_guidance(text):
        updated = text
        status = "equivalent-existing"
    else:
        prefix = text.rstrip()
        updated = f"{prefix}\n\n{PLAYBOOK}" if prefix else PLAYBOOK
        status = "missing"

    changed = updated != text
    if apply and changed:
        safe_write_text(path, preserve_newlines(text, updated), allowed_root or path.parent)
        status = "written"
    return {"path": str(path), "status": status, "changed": bool(apply and changed)}


def has_equivalent_project_guidance(text: str) -> bool:
    lower = text.lower()
    return (
        "serena/gortex repository code intelligence" in lower
        and "gortex" in lower
        and "repository is tracked" in lower
        and "initialized serena project" in lower
        and "native file and search tools only when neither gortex nor serena" in lower
    )


def update_project_agents(path: Path, apply: bool, allowed_root: Path) -> dict[str, Any]:
    text = read_text(path)
    if PROJECT_START in text and PROJECT_END in text:
        updated = re.sub(
            rf"{re.escape(PROJECT_START)}.*?{re.escape(PROJECT_END)}\s*",
            PROJECT_PLAYBOOK,
            text,
            count=1,
            flags=re.DOTALL,
        )
        status = "managed-current" if updated == text else "managed-update-needed"
    elif has_equivalent_project_guidance(text):
        updated = text
        status = "equivalent-existing"
    else:
        prefix = text.rstrip()
        updated = f"{prefix}\n\n{PROJECT_PLAYBOOK}" if prefix else PROJECT_PLAYBOOK
        status = "missing"

    changed = updated != text
    if apply and changed:
        safe_write_text(path, preserve_newlines(text, updated), allowed_root)
        status = "written"
    return {"path": str(path), "status": status, "changed": bool(apply and changed)}


def yaml_top_level_number(text: str, key: str) -> float | None:
    _, data = load_yaml_mapping(text)
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"Expected numeric YAML value for {key}")
    try:
        return float(value)
    except ValueError as error:
        raise ValueError(f"Expected numeric YAML value for {key}") from error


def set_global_timeout(config: Path, apply: bool) -> dict[str, Any]:
    initialized = False
    if not config.is_file() and apply:
        serena = shutil.which("serena")
        if not serena:
            return {
                "path": str(config),
                "status": "missing-serena-cli",
                "value": None,
                "unit": "seconds",
                "remediation": "Install Serena, initialize its global config, and set tool_timeout to 10.0 seconds.",
                "changed": False,
            }
        expected_home = Path.home().resolve()
        requested_home = config.parent.parent.resolve()
        if requested_home != expected_home:
            return {
                "path": str(config),
                "status": "missing-init-required",
                "value": None,
                "unit": "seconds",
                "remediation": "Initialize the requested home config before applying tool_timeout 10.0.",
                "changed": False,
            }
        env = os.environ.copy()
        try:
            subprocess.run([serena, "init"], check=True, env=env, timeout=PROCESS_TIMEOUT_SECONDS)
        except (subprocess.SubprocessError, OSError) as error:
            return {
                "path": str(config),
                "status": "initialization-error",
                "error": str(error),
                "unit": "seconds",
                "remediation": "Resolve Serena initialization, then set global tool_timeout to 10.0 seconds.",
                "changed": False,
            }
        initialized = True

    text = read_text(config)
    try:
        value = yaml_top_level_number(text, "tool_timeout")
    except ValueError as error:
        return {
            "path": str(config),
            "status": "parse-error",
            "error": str(error),
            "unit": "seconds",
            "remediation": "Repair the global Serena YAML before setting tool_timeout to 10.0 seconds.",
            "changed": False,
        }
    if not text:
        return {
            "path": str(config),
            "status": "missing",
            "value": None,
            "unit": "seconds",
            "remediation": "Create the global Serena config with tool_timeout: 10.0.",
            "changed": False,
        }
    if value == EXPECTED_TOOL_TIMEOUT_SECONDS:
        return {
            "path": str(config),
            "status": "current",
            "value": value,
            "unit": "seconds",
            "remediation": None,
            "changed": initialized,
        }

    updated = replace_yaml_value(text, "tool_timeout", EXPECTED_TOOL_TIMEOUT_SECONDS)
    if apply:
        safe_write_text(config, preserve_newlines(text, updated), config.parent.parent)
        value = EXPECTED_TOOL_TIMEOUT_SECONDS
    return {
        "path": str(config),
        "status": "written" if apply else "update-needed",
        "value": value,
        "unit": "seconds",
        "remediation": None if apply else "Set global Serena tool_timeout to 10.0 seconds.",
        "changed": apply,
    }


def inspect_project_config(path: Path, apply: bool = False) -> dict[str, Any]:
    text = read_text(path)
    try:
        value = yaml_top_level_number(text, "tool_timeout") if text else None
    except ValueError as error:
        return {
            "path": str(path),
            "exists": path.is_file(),
            "status": "parse-error",
            "error": str(error),
            "remediation": "Repair the project YAML before removing unsupported tool_timeout.",
        }
    if apply and value is not None:
        yaml, data = load_yaml_mapping(text)
        del data["tool_timeout"]
        output = StringIO()
        yaml.dump(data, output)
        safe_write_text(path, preserve_newlines(text, output.getvalue()), path.parent.parent)
        return {
            "path": str(path),
            "exists": True,
            "unsupported_tool_timeout": None,
            "status": "removed-unsupported-key",
            "remediation": None,
        }
    return {
        "path": str(path),
        "exists": path.is_file(),
        "unsupported_tool_timeout": value,
        "status": "unsupported-key" if value is not None else "ok",
        "remediation": "Remove tool_timeout; project Serena configs do not support it." if value is not None else None,
    }


def is_project_source(path: Path) -> bool:
    return not any(part.lower() in EXCLUDED_DIR_NAMES for part in path.parts)


def project_files(cwd: Path) -> list[Path]:
    git = shutil.which("git")
    if git:
        try:
            result = subprocess.run(
                [git, "-C", str(cwd), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                check=False,
                capture_output=True,
                timeout=PROCESS_TIMEOUT_SECONDS,
            )
            if result.returncode == 0:
                paths = [Path(os.fsdecode(raw)) for raw in result.stdout.split(b"\0") if raw]
                return [path for path in paths if is_project_source(path) and (cwd / path).is_file()]
        except subprocess.TimeoutExpired:
            pass

    files: list[Path] = []
    deadline = time.monotonic() + PROCESS_TIMEOUT_SECONDS
    for root, dir_names, file_names in os.walk(cwd):
        if time.monotonic() > deadline:
            raise RuntimeError(f"Filesystem language scan exceeded {PROCESS_TIMEOUT_SECONDS} seconds")
        dir_names[:] = [name for name in dir_names if name.lower() not in EXCLUDED_DIR_NAMES]
        root_path = Path(root)
        for file_name in file_names:
            relative = (root_path / file_name).relative_to(cwd)
            if is_project_source(relative):
                files.append(relative)
                if len(files) > MAX_FALLBACK_FILES:
                    raise RuntimeError(f"Refusing to inspect more than {MAX_FALLBACK_FILES} files")
    return files


def count_project_languages(cwd: Path) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for path in project_files(cwd):
        language = EXTENSION_LANGUAGE.get(path.suffix.lower())
        if language:
            counts[language] += 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def detect_project_languages(cwd: Path) -> dict[str, int]:
    counts = count_project_languages(cwd)
    return select_project_languages(counts)


def select_project_languages(counts: dict[str, int]) -> dict[str, int]:
    if not counts:
        return {}
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    total = sum(count for _, count in ordered)
    primary = ordered[0][0]
    return {
        language: count
        for language, count in ordered
        if language == primary or count >= MIN_LANGUAGE_FILES or count / total >= MIN_LANGUAGE_SHARE
    }


def classify_project_languages(counts: dict[str, int]) -> list[dict[str, Any]]:
    """Classify recognized languages without treating isolated helpers as LSP requirements."""
    selected = select_project_languages(counts)
    total = sum(counts.values())
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [
        {
            "language": language,
            "count": count,
            "share": count / total if total else 0.0,
            "classification": "meaningful" if language in selected else "low-signal",
            "reason": (
                "dominant language or selection threshold met"
                if language in selected
                else f"below {MIN_LANGUAGE_FILES} files and {MIN_LANGUAGE_SHARE:.0%} share"
            ),
        }
        for language, count in ordered
    ]


def parse_configured_languages(text: str) -> list[str] | None:
    _, data = load_yaml_mapping(text)
    if "languages" not in data:
        return None
    languages = data["languages"]
    if languages is None:
        raise ValueError("languages must be a list, not null")
    if not isinstance(languages, list) or not all(isinstance(language, str) for language in languages):
        raise ValueError("languages must be a list of strings")
    return list(languages)


def replace_configured_languages(text: str, languages: list[str]) -> str:
    return replace_yaml_value(text, "languages", languages)


def preserve_language_variants(base_languages: list[str], configured: list[str] | None) -> list[str]:
    configured_variants = {
        LANGUAGE_VARIANT_BASE[language]: language
        for language in configured or []
        if language in LANGUAGE_VARIANT_BASE
    }
    return [configured_variants.get(language, language) for language in base_languages]


def ensure_project_initialized(cwd: Path, apply: bool) -> dict[str, Any]:
    config = cwd / ".serena" / "project.yml"
    if config.is_file():
        return {
            "path": str(config),
            "status": "current",
            "remediation": None,
            "changed": False,
        }
    if not apply:
        return {
            "path": str(config),
            "status": "missing",
            "remediation": f"Initialize Serena for the concrete project at {cwd}.",
            "changed": False,
        }
    serena = shutil.which("serena")
    if not serena:
        return {
            "path": str(config),
            "status": "missing-serena-cli",
            "remediation": "Install Serena before initializing the project fallback.",
            "changed": False,
        }
    try:
        subprocess.run(
            [serena, "project", "create", str(cwd)],
            check=True,
            timeout=PROCESS_TIMEOUT_SECONDS,
        )
    except (subprocess.SubprocessError, OSError) as error:
        return {
            "path": str(config),
            "status": "initialization-error",
            "error": str(error),
            "remediation": "Resolve Serena project initialization and retry.",
            "changed": False,
        }
    if not config.is_file():
        return {
            "path": str(config),
            "status": "initialization-error",
            "error": "Serena completed without creating project.yml",
            "remediation": "Inspect the Serena CLI output and project permissions.",
            "changed": False,
        }
    return {
        "path": str(config),
        "status": "written",
        "remediation": None,
        "changed": True,
    }


def set_project_languages(cwd: Path, apply: bool) -> dict[str, Any]:
    config = cwd / ".serena" / "project.yml"
    local_config = cwd / ".serena" / "project.local.yml"
    all_counts = count_project_languages(cwd)
    counts = select_project_languages(all_counts)
    detected_base = list(counts)

    text = read_text(config)
    local_text = read_text(local_config)
    try:
        local_languages = parse_configured_languages(local_text) if local_text else None
        base_languages = parse_configured_languages(text) if text else None
    except ValueError as error:
        return {
            "path": str(local_config if local_text else config),
            "status": "parse-error",
            "error": str(error),
            "detected": detected_base,
            "counts": counts,
            "language_candidates": classify_project_languages(all_counts),
            "remediation": "Repair the effective Serena project YAML before updating languages.",
            "changed": False,
        }
    effective_config = local_config if local_languages is not None else config
    effective_text = local_text if local_languages is not None else text
    configured = local_languages if local_languages is not None else base_languages
    detected = preserve_language_variants(detected_base, configured)
    if configured is None:
        status = "missing" if not text else "languages-key-missing"
    elif configured == detected:
        status = "current"
    else:
        status = "update-needed"

    changed = False
    if apply and effective_text and configured != detected:
        updated = replace_configured_languages(effective_text, detected)
        safe_write_text(effective_config, preserve_newlines(effective_text, updated), cwd)
        configured = detected
        status = "written"
        changed = True

    return {
        "path": str(effective_config),
        "base_path": str(config),
        "local_override_path": str(local_config),
        "source": "project.local.yml" if local_languages is not None else "project.yml",
        "status": status,
        "configured": configured,
        "detected": detected,
        "detected_base_languages": detected_base,
        "counts": counts,
        "ignored_low_signal": {language: count for language, count in all_counts.items() if language not in counts},
        "language_candidates": classify_project_languages(all_counts),
        "selection_threshold": {
            "minimum_files": MIN_LANGUAGE_FILES,
            "minimum_share": MIN_LANGUAGE_SHARE,
            "primary_language_always_included": True,
        },
        "excluded_directories": sorted(EXCLUDED_DIR_NAMES),
        "remediation": (
            None
            if status in {"current", "written"}
            else f"Set languages in {effective_config} to {detected}; low-signal languages must remain disabled."
        ),
        "changed": changed,
    }


def clear_global_metadata_languages(home: Path, apply: bool) -> dict[str, Any]:
    """Keep Serena's own configuration directory from starting an LSP."""
    config = home / ".serena" / ".serena" / "project.yml"
    local_config = home / ".serena" / ".serena" / "project.local.yml"
    text = read_text(config)
    local_text = read_text(local_config)
    if not text and not local_text:
        return {
            "path": str(config),
            "local_override_path": str(local_config),
            "status": "not-present",
            "configured": None,
            "remediation": None,
            "changed": False,
        }
    try:
        base_languages = parse_configured_languages(text) if text else None
        local_languages = parse_configured_languages(local_text) if local_text else None
    except ValueError as error:
        return {
            "path": str(local_config if local_text else config),
            "local_override_path": str(local_config),
            "status": "parse-error",
            "error": str(error),
            "remediation": "Repair the global Serena metadata project YAML before clearing languages.",
            "changed": False,
        }
    effective_config = local_config if local_languages is not None else config
    effective_text = local_text if local_languages is not None else text
    configured = local_languages if local_languages is not None else base_languages
    if configured == []:
        return {
            "path": str(effective_config),
            "base_path": str(config),
            "local_override_path": str(local_config),
            "source": "project.local.yml" if local_languages is not None else "project.yml",
            "status": "current",
            "configured": configured,
            "remediation": None,
            "changed": False,
        }
    if apply:
        updated = replace_configured_languages(effective_text, [])
        safe_write_text(effective_config, preserve_newlines(effective_text, updated), home)
        return {
            "path": str(effective_config),
            "base_path": str(config),
            "local_override_path": str(local_config),
            "source": "project.local.yml" if local_languages is not None else "project.yml",
            "status": "written",
            "configured": [],
            "remediation": None,
            "changed": True,
        }
    return {
        "path": str(effective_config),
        "base_path": str(config),
        "local_override_path": str(local_config),
        "source": "project.local.yml" if local_languages is not None else "project.yml",
        "status": "update-needed",
        "configured": configured,
        "remediation": "Set languages to [] in the global Serena metadata project; do not add languages to serena_config.yml.",
        "changed": False,
    }


def serena_config_section(text: str) -> str:
    """Return the Serena mapping/table section from common JSON, TOML, and YAML client files."""
    lines = text.splitlines()
    toml_start = next(
        (index for index, line in enumerate(lines) if re.match(r"\s*\[mcp_servers\.serena\]\s*$", line)),
        None,
    )
    if toml_start is not None:
        end = len(lines)
        for index in range(toml_start + 1, len(lines)):
            heading = re.match(r"\s*\[mcp_servers\.([^\]]+)\]\s*$", lines[index])
            if heading and not heading.group(1).startswith("serena."):
                end = index
                break
        return "\n".join(lines[toml_start:end])

    mapping_start = next(
        (
            index
            for index, line in enumerate(lines)
            if re.match(r'^\s*["\']?serena["\']?\s*:\s*(?:\{|$)', line, re.IGNORECASE)
        ),
        None,
    )
    if mapping_start is None:
        compact_mapping = re.search(r'["\']?serena["\']?\s*:\s*\{', text, re.IGNORECASE)
        return text[compact_mapping.start():] if compact_mapping else ""
    start_line = lines[mapping_start]
    indentation = len(start_line) - len(start_line.lstrip())
    end = len(lines)
    for index in range(mapping_start + 1, len(lines)):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith(("#", "//")):
            continue
        line_indent = len(line) - len(line.lstrip())
        if line_indent == indentation and re.match(r'^\s*["\']?[^}\]\s][^:]*["\']?\s*:', line):
            end = index
            break
    return "\n".join(lines[mapping_start:end])


def extract_cli_tool_timeout(text: str) -> float | None:
    match = re.search(
        r"--tool-timeout(?:\s*[=:]\s*|[\s\"',\[\]-]+)(\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE,
    )
    return float(match.group(1)) if match else None


def extract_client_timeouts(text: str) -> dict[str, float]:
    return {
        key.lower(): float(value)
        for key, value in re.findall(
            r"(?i)[\"']?(timeout|startup_timeout_sec|tool_timeout_sec)[\"']?\s*[:=]\s*[\"']?(\d+(?:\.\d+)?)",
            text,
        )
    }


def extract_windows_utf8_environment(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for key in ("PYTHONIOENCODING", "PYTHONUTF8"):
        match = re.search(rf"(?i)[\"']?{key}[\"']?\s*[:=]\s*[\"']?([^\"',\s}}]+)", text)
        if match:
            values[key] = match.group(1)
    return values


def timeout_status(value: float | None, expected: float) -> str:
    if value is None:
        return "missing"
    return "current" if value == expected else "update-needed"


def inspect_client_config(
    path: Path,
    generated: bool = False,
    *,
    classification: str | None = None,
    client: str = "unknown",
    ownership: str = "unresolved candidate",
    expected_client_timeouts: dict[str, str] | None = None,
) -> dict[str, Any]:
    text = read_text(path)
    section = serena_config_section(text)
    serena = bool(section)
    cli_value = extract_cli_tool_timeout(section) if serena else None
    cli_status = timeout_status(cli_value, EXPECTED_TOOL_TIMEOUT_SECONDS) if serena else "not-applicable"
    client_values = extract_client_timeouts(section) if serena else {}
    windows_utf8_values = extract_windows_utf8_environment(section) if serena else {}
    if not serena or os.name != "nt":
        windows_utf8_status = "not-applicable"
    elif windows_utf8_values == {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}:
        windows_utf8_status = "current"
    else:
        windows_utf8_status = "missing"
    expected = expected_client_timeouts or {}
    expected_details = {
        key: {"value": EXPECTED_CLIENT_TIMEOUTS[unit], "unit": unit}
        for key, unit in expected.items()
    }
    if not serena:
        client_status = "not-applicable"
    elif not expected:
        client_status = "schema-unverified"
    else:
        statuses = [
            timeout_status(client_values.get(key), EXPECTED_CLIENT_TIMEOUTS[unit])
            for key, unit in expected.items()
        ]
        client_status = "current" if all(status == "current" for status in statuses) else "update-needed"
    candidate_classification = "generated" if generated else classification or "unknown"
    if not serena:
        remediation = None
    elif candidate_classification == "global-ssot":
        remediation = "Remove Serena from the global host SSOT and run its sync mechanism; configure Serena MCP only through an explicitly confirmed concrete-project source."
    elif candidate_classification == "generated":
        remediation = "Report drift against the generating SSOT; never edit this generated candidate directly."
    elif candidate_classification in {"inactive", "unknown"}:
        remediation = "Do not edit this candidate; confirm the effective client source before applying timeout policy."
    elif (
        cli_status == "current"
        and client_status in {"current", "schema-unverified"}
        and windows_utf8_status in {"current", "not-applicable"}
    ):
        remediation = None
    else:
        remediation = "Update this active source with --tool-timeout 10 and the client timeout required by its schema; on Windows add PYTHONIOENCODING=utf-8 and PYTHONUTF8=1."
    return {
        "path": str(path),
        "exists": path.is_file(),
        "generated": generated,
        "classification": candidate_classification,
        "client": client,
        "ownership": ownership,
        "inspection": "heuristic-only; confirm with the active client",
        "contains_serena": serena,
        "cli_tool_timeout": {
            "value": cli_value,
            "expected": EXPECTED_TOOL_TIMEOUT_SECONDS,
            "unit": "seconds",
            "status": cli_status,
        },
        "client_timeout": {
            "values": client_values,
            "expected": expected_details,
            "status": client_status,
        },
        "windows_utf8_environment": {
            "values": windows_utf8_values,
            "expected": {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
            "status": windows_utf8_status,
        },
        "tool_timeout_10": cli_status == "current",
        "client_timeout_10s": client_status == "current",
        "remediation": remediation,
    }


def inspect_mcpm_serena_registry(home: Path) -> dict[str, Any]:
    """Report Serena in MCPM's registry without treating it as a writable candidate."""
    path = home / ".config" / "mcpm" / "servers.json"
    text = read_text(path)
    if not text:
        return {
            "path": str(path),
            "status": "not-present",
            "contains_serena": False,
            "ownership": "mcpm-owned",
            "remediation": None,
        }
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        return {
            "path": str(path),
            "status": "parse-error",
            "contains_serena": None,
            "ownership": "mcpm-owned",
            "error": str(error),
            "remediation": "Repair the MCPM registry with MCPM before changing its entries.",
        }
    if not isinstance(data, dict):
        return {
            "path": str(path),
            "status": "invalid-format",
            "contains_serena": None,
            "ownership": "mcpm-owned",
            "remediation": "Repair the MCPM registry with MCPM before changing its entries.",
        }
    if "serena" not in data:
        return {
            "path": str(path),
            "status": "absent",
            "contains_serena": False,
            "ownership": "mcpm-owned",
            "remediation": None,
        }
    return {
        "path": str(path),
        "status": "present",
        "contains_serena": True,
        "ownership": "mcpm-owned",
        "remediation": "Use mcpm uninstall serena; do not hand-edit the MCPM registry unless MCPM is unavailable and the user explicitly requests stale-entry removal.",
    }


def candidate_client_paths(cwd: Path, home: Path) -> list[tuple[Path, bool]]:
    paths = [(spec["path"], spec["classification"] == "generated") for spec in candidate_client_specs(cwd, home)]
    seen: set[Path] = set()
    return [(path, generated) for path, generated in paths if not (path in seen or seen.add(path))]


def candidate_client_specs(cwd: Path, home: Path) -> list[dict[str, Any]]:
    """Describe candidate ownership explicitly instead of treating every discovered file as active."""
    specs = [
        (cwd / ".agents" / "mcp_config.json", "antigravity", "inactive", "legacy Antigravity variant", {"timeout": "milliseconds"}),
        (cwd / ".mcp.json", "generic", "unknown", "project MCP candidate", {}),
        (cwd / "opencode.json", "opencode", "unknown", "project OpenCode candidate", {"timeout": "milliseconds"}),
        (cwd / "opencode.jsonc", "opencode", "unknown", "project OpenCode candidate", {"timeout": "milliseconds"}),
        (cwd / ".opencode" / "opencode.jsonc", "opencode", "unknown", "project OpenCode candidate", {"timeout": "milliseconds"}),
        (home / ".agents" / "mcp_config.json", "antigravity", "inactive", "user Antigravity candidate; precedence unresolved", {"timeout": "milliseconds"}),
        (home / ".config" / "mcp" / "servers.yaml", "host-ssot", "global-ssot", "global host MCP SSOT; Serena must remain absent", {"timeout": "milliseconds"}),
        (home / ".config" / "opencode" / "opencode.jsonc", "opencode", "unknown", "OpenCode candidate; effective source unverified", {"timeout": "milliseconds"}),
        (home / ".codex" / "config.toml", "codex", "unknown", "Codex candidate; effective source unverified", {"startup_timeout_sec": "seconds", "tool_timeout_sec": "seconds"}),
        (home / ".claude.json", "claude", "unknown", "Claude candidate; effective source unverified", {}),
        (home / ".hermes" / "config.yaml", "hermes", "unknown", "Hermes candidate; effective source unverified", {}),
        (home / ".config" / "mcp" / "generated" / "opencode-mcp.jsonc", "opencode", "generated", "generated from host SSOT", {"timeout": "milliseconds"}),
        (home / ".config" / "mcp" / "generated" / "codex-mcp.toml", "codex", "generated", "generated from host SSOT", {"startup_timeout_sec": "seconds", "tool_timeout_sec": "seconds"}),
        (home / ".config" / "mcp" / "generated" / "claude-mcp.json", "claude", "generated", "generated from host SSOT", {}),
        (home / ".config" / "mcp" / "generated" / "hermes-mcp.yaml", "hermes", "generated", "generated from host SSOT", {}),
        (home / ".config" / "mcp" / "generated" / "anythingllm-mcp.json", "anythingllm", "generated", "generator ownership unresolved", {}),
    ]
    seen: set[Path] = set()
    return [
        {
            "path": path,
            "client": client,
            "classification": classification,
            "ownership": ownership,
            "expected_client_timeouts": expected,
        }
        for path, client, classification, ownership, expected in specs
        if not (path in seen or seen.add(path))
    ]


def validate_project_root(cwd: Path, home: Path) -> None:
    if cwd == home or cwd.parent == cwd:
        raise ValueError(f"Refusing broad project audit at user home or filesystem root: {cwd}")


def report_has_status(value: Any, statuses: set[str]) -> bool:
    if isinstance(value, dict):
        return value.get("status") in statuses or any(report_has_status(item, statuses) for item in value.values())
    if isinstance(value, list):
        return any(report_has_status(item, statuses) for item in value)
    return False


def report_has_apply_failure(report: dict[str, Any]) -> bool:
    """Ignore read-only client observations when deciding whether managed writes failed."""
    return report_has_status(report.get("native_serena"), APPLY_FAILURE_STATUSES) or report_has_status(
        report.get("agents"), APPLY_FAILURE_STATUSES
    )


def report_has_selected_status(
    report: dict[str, Any],
    *,
    apply_agents: bool,
    apply_serena: bool,
    apply_languages: bool,
    statuses: set[str],
) -> bool:
    if apply_agents and report_has_status(report.get("agents"), statuses):
        return True
    native_serena = report.get("native_serena", {})
    if apply_serena and any(
        report_has_status(native_serena.get(key), statuses)
        for key in ("global", "global_metadata_languages", "project_initialization", "project")
    ):
        return True
    return apply_languages and report_has_status(native_serena.get("languages"), statuses)


def report_has_selected_apply_failure(
    report: dict[str, Any],
    *,
    apply_agents: bool,
    apply_serena: bool,
    apply_languages: bool,
) -> bool:
    return report_has_selected_status(
        report,
        apply_agents=apply_agents,
        apply_serena=apply_serena,
        apply_languages=apply_languages,
        statuses=APPLY_FAILURE_STATUSES,
    )


def managed_paths(cwd: Path, home: Path) -> list[Path]:
    return list(
        dict.fromkeys(
            [
                home / "AGENTS.md",
                cwd / "AGENTS.md",
                home / ".serena" / "serena_config.yml",
                home / ".serena" / ".serena" / "project.yml",
                home / ".serena" / ".serena" / "project.local.yml",
                cwd / ".serena" / "project.yml",
                cwd / ".serena" / "project.local.yml",
            ]
        )
    )


def capture_snapshots(paths: list[Path]) -> dict[Path, bytes | None]:
    snapshots: dict[Path, bytes | None] = {}
    for path in paths:
        if path.is_symlink():
            raise ValueError(f"Refusing to snapshot symlink: {path}")
        snapshots[path] = path.read_bytes() if path.is_file() else None
    return snapshots


def restore_snapshots(snapshots: dict[Path, bytes | None]) -> None:
    for path, content in snapshots.items():
        if path.is_symlink():
            raise ValueError(f"Refusing to restore through symlink: {path}")
        if content is None:
            if path.is_file():
                path.unlink()
            continue
        safe_write_text(path, content.decode("utf-8"), path.parent)


def build_report(
    cwd: Path,
    home: Path,
    apply: bool = False,
    *,
    apply_agents: bool | None = None,
    apply_serena: bool | None = None,
    apply_languages: bool | None = None,
) -> dict[str, Any]:
    apply_agents = apply if apply_agents is None else apply_agents
    apply_serena = apply if apply_serena is None else apply_serena
    apply_languages = apply if apply_languages is None else apply_languages
    applying = apply_agents or apply_serena or apply_languages
    global_config = home / ".serena" / "serena_config.yml"
    native_serena = {
        "global": set_global_timeout(global_config, apply_serena),
        "global_metadata_languages": clear_global_metadata_languages(home, apply_serena),
        "project_initialization": ensure_project_initialized(cwd, apply_serena),
        "languages": set_project_languages(cwd, apply_languages),
        "project": [
            inspect_project_config(cwd / ".serena" / "project.yml", apply_serena),
            inspect_project_config(cwd / ".serena" / "project.local.yml", apply_serena),
        ],
        "precedence": "--tool-timeout CLI override > global serena_config.yml; project.yml has no tool_timeout field",
    }
    mcp_candidates = [
        inspect_client_config(
            spec["path"],
            spec["classification"] == "generated",
            classification=spec["classification"],
            client=spec["client"],
            ownership=spec["ownership"],
            expected_client_timeouts=spec["expected_client_timeouts"],
        )
        for spec in candidate_client_specs(cwd, home)
        if spec["path"].is_file()
    ]
    return {
        "mode": "apply" if applying else "audit",
        "requested_actions": {
            "agents": apply_agents,
            "serena": apply_serena,
            "languages": apply_languages,
        },
        "native_serena": native_serena,
        "agents": [
            update_agents(home / "AGENTS.md", apply_agents, home),
            update_project_agents(cwd / "AGENTS.md", apply_agents, cwd),
        ],
        "mcpm_registry": inspect_mcpm_serena_registry(home),
        "mcp_candidates": mcp_candidates,
        "timeout_policy": {
            "global_serena": native_serena["global"],
            "cli_overrides": [
                {"path": candidate["path"], **candidate["cli_tool_timeout"]} for candidate in mcp_candidates
            ],
            "client_boundaries": [
                {"path": candidate["path"], **candidate["client_timeout"]} for candidate in mcp_candidates
            ],
            "windows_utf8_stdio": [
                {"path": candidate["path"], **candidate["windows_utf8_environment"]}
                for candidate in mcp_candidates
            ],
        },
        "next_action": "Apply each remediation only to a confirmed authoritative source; regenerate generated candidates and leave inactive or unconfirmed candidates unchanged.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--apply", action="store_true", help="apply all managed actions")
    parser.add_argument("--apply-agents", action="store_true", help="install or update global and project AGENTS.md blocks")
    parser.add_argument("--apply-serena", action="store_true", help="initialize and repair Serena configuration")
    parser.add_argument("--apply-languages", action="store_true", help="reconcile project Serena languages")
    args = parser.parse_args()

    cwd = args.cwd.expanduser().resolve()
    home = args.home.expanduser().resolve()
    apply_agents = args.apply or args.apply_agents
    apply_serena = args.apply or args.apply_serena
    apply_languages = args.apply or args.apply_languages
    applying = apply_agents or apply_serena or apply_languages
    try:
        validate_project_root(cwd, home)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    snapshots: dict[Path, bytes | None] | None = None
    try:
        preflight = build_report(cwd, home, False)
        if applying and report_has_selected_status(
            preflight,
            apply_agents=apply_agents,
            apply_serena=apply_serena,
            apply_languages=apply_languages,
            statuses={"parse-error"},
        ):
            preflight["mode"] = "preflight-failed"
            print(json.dumps(preflight, indent=2, ensure_ascii=False))
            return 2
        if applying:
            snapshots = capture_snapshots(managed_paths(cwd, home))
            report = build_report(
                cwd,
                home,
                apply_agents=apply_agents,
                apply_serena=apply_serena,
                apply_languages=apply_languages,
            )
            if report_has_selected_apply_failure(
                report,
                apply_agents=apply_agents,
                apply_serena=apply_serena,
                apply_languages=apply_languages,
            ):
                restore_snapshots(snapshots)
                report["mode"] = "apply-failed-rolled-back"
                report["rolled_back"] = True
            else:
                report["rolled_back"] = False
        else:
            report = preflight
    except (OSError, RuntimeError, ValueError) as error:
        if snapshots is not None:
            try:
                restore_snapshots(snapshots)
            except (OSError, ValueError) as rollback_error:
                print(
                    json.dumps(
                        {"mode": "failed-rollback-incomplete", "error": str(error), "rollback_error": str(rollback_error)},
                        indent=2,
                        ensure_ascii=False,
                    )
                )
                return 2
        print(json.dumps({"mode": "failed", "error": str(error)}, indent=2, ensure_ascii=False))
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if applying:
        failed = report_has_selected_apply_failure(
            report,
            apply_agents=apply_agents,
            apply_serena=apply_serena,
            apply_languages=apply_languages,
        )
    else:
        failed = report_has_apply_failure(report)
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""OpenCode V2 `execute.after` hook logic for opencode-habit-feedback (T02, v2).

SDK contracts are pinned from the actual published packages
`@opencode/plugin@2.0.25` and `@opencode/schema@2.0.25` (registry tarball,
sha512 integrity verified; evidence in VERSIONS.md), not inferred:

- `execute.before` event: {tool, sessionID, agent, messageID, id: CallID, input}.
- `execute.after` event: same base + ({status:"completed", result: Tool.Result}
  | {status:"error", error: Tool.Error}).
- `Tool.Result` = {output?, content?: string | Content[], metadata?} with
  Content = {type:"text", text} | {type:"file", uri, mime, name?}.
- Scope of an event is the session's own location:
  `ctx.session.get({sessionID})` -> SessionInfo.location.directory; the plugin
  instance's `ctx.location.directory` is NOT the event's working directory.

The TypeScript shim (`../plugin/index.ts`) serialises exactly these fields to
JSON (one event on stdin, one response on stdout); this module decides — from
JSON data only — which files were *really, unambiguously* mutated, enforces the
session-approved scope boundary, de-duplicates repeated scans, and runs the
original pipeline through the T01 adapter. It never executes tool data.

Recognised, *tested* path evidence (everything else is visible `not_scanned`
- including unknown completed tools such as bash or custom MCP tools, which
  are potential mutators without a proven read-only property - or, for the
  documented stock read-only tools and error events, a non-mutating event;
  no path is ever guessed from shell or script text):

1. Native OpenCode file tools `edit` and `write` (documented args:
   `edit{path, oldString, newString, replaceAll}`, `write{path, content}`),
   status "completed". The documented `after` event carries `input` itself;
   a stored `before` pairing (keyed by the documented `id` CallID) is used
   only when the `after` event lacks a usable path input.
2. Gortex Code-Mode `execute` results (and the effective MCP names
   `gortex_edit`/`gortex_refactor`): result text parses as JSON matching the
   pinned mutation receipt — object (or top-level array of objects) with a
   string `path` plus (`status` in {created, applied, written} or
   `new_sha`+`replacements`) and `dry_run` falsy. `would_apply` dry runs
   are definitive non-mutations.

Scope, trust and side-effect rules:

- Only absolute realpaths inside the session scope root are scanned; symlink
  escape, outside paths, ambiguous resolutions and scope roots that are the
  filesystem root or the user home are `not_scanned`.
- The state root defaults to a per-user directory
  `/tmp/opencode/habit-feedback-<uid>` created 0700; an existing entry must
  be a non-symlink directory owned by the current user, otherwise the event is
  `not_scanned` (visible). `HABIT_FEEDBACK_STATE_ROOT` overrides it.
- The runtime config for repositories without their own `.habit-hooks` lives
  under the state root as the adapter's `trusted_config_root`; created once,
  atomically, mode 0600, never a symlink, content-validated on every use.
  `HOME`, `TMPDIR` and `RUFF_CACHE_DIR` of pipeline children are redirected
  into the state root — no repository or user profile file is ever written.
- Event payloads on stdin are bounded (MAX_EVENT_BYTES); pairing + dedup state
  is per session+scope, flock-guarded with a bounded wait. At most
  MAX_FILES_PER_EVENT files are scanned per event; the remainder is reported
  `not_scanned` — a partially scanned event is never `clean`.
- SIGTERM during a bridge run kills every active pipeline process group
  (adapter kill_active) and exits non-zero; no orphan sensors.
- No tool is installed, downloaded or run beyond the two pinned originals; no
  prompts, tasks, agents or dispatches are created; failures are visible
  reasons, never a clean verdict.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import importlib.util
import os
import shutil
import signal
import stat
import sys
import tempfile
import time
from pathlib import Path

# Named limits owned by this hook (S00: benannte Werte am Eigentümer).
MAX_FILES_PER_EVENT = 4
MAX_RECEIPTS_PER_EVENT = 64
MAX_SCAN_FILE_BYTES = 10 * 1024 * 1024
STATE_LOCK_WAIT_S = 5.0
LEDGER_MAX_ENTRIES = 256
LEDGER_TTL_S = 14 * 86400
FEEDBACK_MAX_CHARS = 4000
MAX_EVENT_BYTES = 8 * 1024 * 1024

NATIVE_MUTATING_TOOLS = frozenset({"edit", "write"})
GORTEX_CODEMODE_TOOL = "execute"
GORTEX_MCP_MUTATING_TOOLS = frozenset({"gortex_edit", "gortex_refactor"})
GORTEX_APPLIED_STATUSES = frozenset({"applied", "written", "created"})
GORTEX_DRYRUN_STATUSES = frozenset({"would_apply"})

# Stock OpenCode tools that are provably read-only under the pinned SDK
# contract (documented tools without any write side effect). Every other
# completed form - bash, opaque patch tools, custom MCP tools - has no proven
# read-only property and is reported as a visible not_scanned coverage gap,
# never silently classified "not_mutating".
KNOWN_READONLY_TOOLS = frozenset(
    {"read", "glob", "grep", "ls", "webfetch", "websearch"})

HOOK_VERSION = "0.1.0"
CANONICAL_RUNTIME_PLUGINS = ("generic", "python")
# Narrowed single-file pipeline: the repository-wide sensors without a proven
# single-file scope (jscpd, deptry; owner of that knowledge is the adapter's
# REPOSITORY_SENSORS) stay explicitly disabled. Their smells are surfaced as
# not_scanned coverage gaps by this hook - a disabled sensor is never a
# passed check, and "clean" never covers these smells.
CANONICAL_RUNTIME_CONFIG = (
    'plugins = ["generic", "python"]\n'
    'files = ["**/*.py"]\n'
    '\n'
    '# Narrowed single-file pipeline: repository-wide sensors without a proven\n'
    '# single-file scope stay disabled; the hook reports their smells as\n'
    '# not_scanned coverage gaps (a disabled sensor is not a passed check).\n'
    '[sensors.jscpd]\ndisabled = true\n'
    '\n[sensors.deptry]\ndisabled = true\n'
)

_ADAPTER = Path(__file__).resolve().parent.parent / "adapter" / "habit_feedback_pipeline.py"


def _load_adapter():
    if "habit_feedback_pipeline" in sys.modules:
        return sys.modules["habit_feedback_pipeline"]
    spec = importlib.util.spec_from_file_location("habit_feedback_pipeline", _ADAPTER)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("habit_feedback_pipeline", module)
    spec.loader.exec_module(module)
    return module


def default_state_root() -> Path:
    """Per-user default: avoids cross-user conflicts on shared /tmp."""
    return Path("/tmp/opencode") / ("habit-feedback-%d" % os.getuid())


def _secure_file_fd(path, flags):
    fd = os.open(path, flags | os.O_NOFOLLOW, 0o600)
    st = os.fstat(fd)
    if st.st_uid != os.getuid() or not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
        os.close(fd)
        raise OSError("unsafe state file: %s" % path)
    return fd


def _secure_directory(path):
    # Check every existing ancestor without resolving away symlinks.
    for component in reversed([path, *path.parents]):
        if os.path.lexists(component):
            st = os.lstat(component)
            if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
                raise OSError("symlink/non-directory state path: %s" % component)
    path.mkdir(parents=True, mode=0o700, exist_ok=True)
    st = os.lstat(path)
    if st.st_uid != os.getuid() or st.st_mode & 0o022:
        raise OSError("state directory owned by uid %d or writable by others: %s" % (st.st_uid, path))
    return path


def _checked_state_root(path: Path) -> tuple[Path | None, str | None]:
    """The state root must be a real, user-owned directory — never a symlink."""
    allowed = Path("/tmp/opencode")
    if not path.is_absolute() or ".." in path.parts or allowed not in path.parents:
        return None, "state root must be below /tmp/opencode"
    if os.path.lexists(path):
        st = os.lstat(path)
        if not path.is_dir() or path.is_symlink():
            return None, "state root is not a plain directory: %s" % path
        if st.st_uid != os.getuid():
            return None, "state root owned by uid %d (expected %d)" % (st.st_uid, os.getuid())
    try:
        _secure_directory(path)
    except OSError as exc:
        return None, str(exc)
    return path, None


def _sha256_file(path: Path) -> str | None:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def _inside_scope(candidate: Path, scope: Path) -> Path | None:
    """Absolute, real containment check with symlink transparency."""
    try:
        real = candidate.resolve(strict=True)
    except OSError:
        return None
    root = scope.resolve(strict=True)
    if real == root or root in real.parents:
        return real
    return None


def _plausible_scope(scope: Path) -> bool:
    """Refuse scope roots that would make 'inside scope' meaningless."""
    return scope != Path(scope.anchor) and scope != Path.home()


def resolve_path_evidence(path_value, scope: Path) -> tuple[Path | None, str | None]:
    """Map one path value onto exactly one file inside the scope.

    Absolute values must already be inside the scope. Relative values are tried
    against the scope root and — because Gortex reports workspace-prefixed repo
    paths (observed evidence, VERSIONS.md) — once more with a leading segment
    equal to the scope directory's own name stripped. Exactly one candidate
    must exist and be contained; zero or several candidates are ambiguous.
    """
    if not isinstance(path_value, str) or not path_value.strip() or len(path_value) > 4096:
        return None, "path value is not a non-empty string"
    raw = Path(path_value)
    candidates: list[Path] = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.append(scope / raw)
        parts = raw.parts
        if len(parts) > 1 and parts[0] == scope.name:
            candidates.append(scope.joinpath(*parts[1:]))
    hits: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        contained = _inside_scope(candidate, scope)
        if contained is not None and contained.is_file() and contained not in seen:
            seen.add(contained)
            hits.append(contained)
    if not hits:
        return None, "no in-scope existing file matches %r" % path_value
    if len(hits) > 1:
        return None, "ambiguous path resolution for %r" % path_value
    return hits[0], None


def _is_gortex_mutation(obj) -> bool:
    """Documented Gortex mutation receipt: real write, not a dry run."""
    if not isinstance(obj, dict):
        return False
    path = obj.get("path")
    if not isinstance(path, str) or not path:
        return False
    if obj.get("dry_run") is True:
        return False
    status = obj.get("status")
    if isinstance(status, str):
        if status in GORTEX_DRYRUN_STATUSES:
            return False
        if status in GORTEX_APPLIED_STATUSES:
            return True
    if isinstance(obj.get("new_sha"), str) and isinstance(obj.get("replacements"), int):
        return obj["replacements"] >= 0
    if isinstance(obj.get("bytes_written"), int) and obj.get("bytes_written", 0) > 0 and "new_sha" in obj:
        return True
    return False


def _result_output_text(result) -> str | None:
    """Text of a V2 ToolResult: output?, content?: string | Content[]."""
    if isinstance(result, str):
        return result
    if not isinstance(result, dict):
        return None
    output = result.get("output")
    if isinstance(output, str):
        return output
    content = result.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [item.get("text") for item in content
                 if isinstance(item, dict) and item.get("type") == "text"
                 and isinstance(item.get("text"), str)]
        if parts:
            return "\n".join(parts)
    return None


def gortex_paths_from_result(result) -> tuple[list[str], list[str], list[str]]:
    """Extract path values from a documented Gortex mutation result.

    Returns (mutated, dry_run_seen, unrecognised) — only the object itself and
    a top-level array of objects are recognised shapes; nested structures are
    not searched (no guessing from arbitrary text).
    """
    structured = result.get("output") if isinstance(result, dict) else None
    text = _result_output_text(result)
    # Exact OpenCode 2.0.25 execute Tool.Result.output envelope, observed in
    # the real host (CK04): {output: JSON text, toolCalls: [], files: []}.
    # No recursive wrapper search, file inference or program-text parsing.
    if (isinstance(structured, dict)
            and set(structured) == {"output", "toolCalls", "files"}
            and isinstance(structured["output"], str)
            and isinstance(structured["toolCalls"], list)
            and isinstance(structured["files"], list)):
        text = structured["output"]
        structured = None
    mutated: list[str] = []
    dry: list[str] = []
    unrecognised: list[str] = []
    if isinstance(structured, (dict, list)):
        parsed = structured
    else:
        if text is None:
            return mutated, dry, ["unknown result content"]
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return mutated, dry, ["unrecognised result text"]
    items = parsed if isinstance(parsed, list) else [parsed]
    if len(items) > MAX_RECEIPTS_PER_EVENT:
        return [], [], ["mutation receipt count exceeds event limit"]
    for item in items:
        if not isinstance(item, dict):
            unrecognised.append("<non-object result item>")
            continue
        path = item.get("path")
        label = path if isinstance(path, str) else "<result without path>"
        if _is_gortex_mutation(item):
            mutated.append(path)
        elif isinstance(path, str) and (
            item.get("dry_run") is True
            or item.get("status") in GORTEX_DRYRUN_STATUSES
        ):
            dry.append(path)
        else:
            unrecognised.append(label)
    return mutated, dry, unrecognised


class HookState:
    """Per (scope, session) state file: pairing map + scan ledger, flock'd."""

    def __init__(self, path: Path):
        self.path = path
        self.data: dict = {"inflight": {}, "ledger": {}}

    def load(self):
        try:
            with os.fdopen(_secure_file_fd(self.path, os.O_RDONLY), "r", encoding="utf-8") as handle:
                raw = json.load(handle)
            if isinstance(raw, dict):
                self.data = raw
        except (OSError, ValueError):
            self.data = {"inflight": {}, "ledger": {}, "_recovered": True}

    def save(self):
        payload = json.dumps(self.data, separators=(",", ":"))
        fd = _secure_file_fd(self.path, os.O_WRONLY | os.O_CREAT)
        os.ftruncate(fd, 0)
        try:
            os.write(fd, payload.encode("utf-8"))
        finally:
            os.close(fd)

    def prune(self, now: float):
        ledger = self.data.setdefault("ledger", {})
        if isinstance(ledger, dict):
            for key in [k for k, v in ledger.items()
                        if not isinstance(v, dict) or now - float(v.get("ts", 0)) > LEDGER_TTL_S]:
                ledger.pop(key, None)
        while len(ledger) > LEDGER_MAX_ENTRIES:
            ledger.pop(next(iter(ledger)), None)

    # -- pairing (keyed by the documented CallID field `id`) -------------
    def remember_before(self, tool: str, call_id, payload: dict):
        inflight = self.data.setdefault("inflight", {})
        if isinstance(call_id, str) and call_id:
            inflight.setdefault(tool, {})[call_id] = payload
        else:
            inflight.setdefault(tool, {"anon": []}).setdefault("anon", []).append(payload)

    def take_pairing(self, tool: str, call_id) -> tuple[dict | None, str | None]:
        inflight = self.data.get("inflight") or {}
        slot = inflight.get(tool)
        if not isinstance(slot, dict):
            return None, "no before event captured for this tool call"
        if isinstance(call_id, str) and call_id:
            payload = slot.pop(call_id, None)
            if payload is not None:
                return payload, None
            return None, "no before event captured for id %r" % call_id
        anon = slot.get("anon")
        if isinstance(anon, list):
            if len(anon) == 1:
                payload = anon.pop(0)
                if not anon:
                    slot.pop("anon", None)
                if not slot:
                    inflight.pop(tool, None)
                return payload, None
            if len(anon) > 1:
                return None, "ambiguous pairing: %d in-flight calls without id" % len(anon)
        if slot:
            ids = [k for k in slot if k != "anon"]
            if len(ids) == 1:
                return slot.pop(ids[0]), None
        return None, "no before event captured for this tool call"

    # -- ledger --------------------------------------------------------
    def already_scanned(self, key: str, digest: str) -> bool:
        entry = self.data.get("ledger", {}).get(key)
        return isinstance(entry, dict) and entry.get("sha") == digest

    def record_scan(self, key: str, digest: str, now: float):
        self.data.setdefault("ledger", {})[key] = {"sha": digest, "ts": now}


def _state_scope_dir(state_root: Path, scope: Path, session) -> Path:
    identity = "%s|%s" % (scope.resolve(), session or "default")
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
    return state_root / digest


def _acquire_lock(path: Path):
    fd = _secure_file_fd(path, os.O_WRONLY | os.O_CREAT)
    deadline = time.monotonic() + STATE_LOCK_WAIT_S
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except OSError:
            if time.monotonic() >= deadline:
                os.close(fd)
                return None
            time.sleep(0.05)


def _runtime_dirs(scope_dir: Path) -> dict:
    runtime = scope_dir / "runtime"
    return {
        "runtime": runtime,
        "config": runtime / "config.toml",
        "cache": runtime / "cache",
        "home": runtime / "home",
        "tmp": runtime / "tmp",
    }


def _install_runtime_guides(runtime):
    guide_names = ("deep-nesting.md", "duplicated-code.md", "incomplete-run.md",
                   "oversized-function.md", "too-many-parameters.md", "oversized-file.md")
    directory = runtime / ".habit-hooks" / "generic" / "guides"
    _secure_directory(directory.parent.parent)
    _secure_directory(directory.parent)
    _secure_directory(directory)
    source = _ADAPTER.parent.parent / "guides"
    for name in guide_names:
        original = source / name
        if original.is_symlink() or not original.is_file():
            raise OSError("packaged guide missing or symlinked: %s" % original)
        content = original.read_bytes()
        destination = directory / name
        fd = _secure_file_fd(destination, os.O_RDWR | os.O_CREAT)
        try:
            existing = os.read(fd, len(content) + 1)
            if existing and existing != content:
                raise OSError("runtime guide differs from packaged source: %s" % name)
            if not existing:
                os.write(fd, content)
        finally:
            os.close(fd)


def _ensure_runtime_config(scope_dir: Path, adapter) -> tuple[Path | None, str | None]:
    """Trusted runtime config: controlled, symlink-checked, content-validated."""
    paths = _runtime_dirs(scope_dir)
    try:
        for key in ("runtime", "cache", "home", "tmp"):
            _secure_directory(paths[key])
    except OSError as exc:
        return None, "cannot create runtime dirs: %s" % exc
    try:
        _install_runtime_guides(paths["runtime"])
    except OSError as exc:
        return None, "runtime guides refused: %s" % exc
    config = paths["config"]
    if config.exists() or config.is_symlink():
        if config.is_symlink() or not config.is_file():
            return None, "runtime config is a symlink or not a regular file: %s" % config
    else:
        fd, tmp_name = tempfile.mkstemp(dir=str(paths["runtime"]), prefix=".config-")
        try:
            os.write(fd, CANONICAL_RUNTIME_CONFIG.encode("utf-8"))
        finally:
            os.close(fd)
        os.chmod(tmp_name, 0o600)
        try:
            os.rename(tmp_name, str(config))
        except OSError:
            os.unlink(tmp_name)
            return None, "cannot install runtime config atomically"
    try:
        fd = _secure_file_fd(config, os.O_RDONLY)
        os.close(fd)
    except OSError as exc:
        return None, "unsafe runtime config: %s" % exc
    # Content validation happens through the adapter with the trusted root;
    # a rejected config is a visible failure, never a clean run.
    try:
        adapter.load_config(scope_dir, None, paths["runtime"])
    except adapter.ConfigRejected as exc:
        return None, "runtime config rejected: %s" % exc
    return config, None


def _pipeline_env(paths: dict) -> dict:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(paths["home"]),
        "TMPDIR": str(paths["tmp"]),
        "RUFF_CACHE_DIR": str(paths["cache"] / "ruff"),
    }
    if os.environ.get("LANG"):
        env["LANG"] = os.environ["LANG"]
    return env


def _locate_executables(sensor, mapper) -> tuple[Path | None, Path | None, list[str]]:
    reasons = []

    def find(explicit, env_key, binary):
        if explicit is not None:
            candidate = Path(explicit)
            if candidate.is_absolute() and candidate.is_file() and os.access(candidate, os.X_OK):
                return candidate
            reasons.append("%s executable not usable: %s" % (binary, explicit))
            return None
        from_env = os.environ.get(env_key)
        if from_env:
            candidate = Path(from_env)
            if candidate.is_absolute() and candidate.is_file() and os.access(candidate, os.X_OK):
                return candidate
            reasons.append("%s executable not usable: %s" % (binary, from_env))
            return None
        reasons.append("%s executable not found: explicit absolute installation "
                       "binding required; PATH discovery grants no trust" % binary)
        return None

    return (find(sensor, "HABIT_FEEDBACK_SENSOR", "habit-sensors"),
            find(mapper, "HABIT_FEEDBACK_MAPPER", "habit-mapper"), reasons)


def _single_file_coverage_gaps(adapter, result) -> list[str]:
    """Smells this single-file event provably did not cover.

    The owner of that knowledge is the adapter's REPOSITORY_SENSORS mapping:
    a repository-wide sensor disabled for the single-file run (whether by this
    hook's canonical runtime config or by the adapter's derived config, which
    reports through PipelineResult.not_scanned) is a visible coverage gap,
    never a passed check. Adapter-reported gaps win; canonical gaps are added
    only for smells not already reported, so nothing is double-listed.
    """
    reported = getattr(result, "not_scanned", None) or []
    mentioned = " ".join(str(item) for item in reported)
    gaps = list(reported)
    for plugin in CANONICAL_RUNTIME_PLUGINS:
        for sensor, smell in sorted(
                getattr(adapter, "REPOSITORY_SENSORS", {}).get(plugin, {}).items()):
            if smell in mentioned:
                continue
            gaps.append(
                "%s not scanned in single-file mode: repository-wide sensor "
                "'%s' is disabled (no qualified single-file scope)" % (smell, sensor))
    return gaps


def _summarise(result, rel: str, adapter) -> dict:
    reasons = list(getattr(result, "reasons", []) or [])
    complete = bool(getattr(result, "complete", False))
    clean = bool(getattr(result, "clean", False))
    mapper = getattr(result, "mapper", None)
    verdict = (getattr(mapper, "stdout", "") or "").strip() if mapper is not None else ""
    findings = getattr(result, "findings", None)
    count = len(findings) if isinstance(findings, list) else None
    # Advisory: a completed run with mapper exit 0 (the original severity
    # decision, e.g. severity='suggest') that still carries findings and
    # coaching. "No enforced smell" is not "no findings"; the original
    # decision is respected and never turned into an enforced change.
    advisory = bool((complete and clean or getattr(mapper, "exit_code", None) == 0)
                    and isinstance(findings, list) and findings)
    stages = {}
    for name in ("sensor", "mapper"):
        stage = getattr(result, name, None)
        if stage is not None:
            stages[name] = {"status": stage.status, "exit_code": stage.exit_code,
                            "stderr": stage.stderr[:2000]} if hasattr(stage, "status") else {}
    return {"file": rel, "complete": complete, "clean": clean, "advisory": advisory,
            "reasons": reasons, "verdict": verdict, "findings": count,
            "not_scanned": _single_file_coverage_gaps(adapter, result), "stages": stages}


def _feedback_text(files: list[dict], skipped: list[dict]) -> str | None:
    if not files and not skipped:
        return None
    lines = ["[habit-feedback v%s]" % HOOK_VERSION]
    snapshot = _ADAPTER.parent.parent / "core" / ".apm"
    if snapshot.is_dir():
        lines.append("Read-only packaged Core reference root: %s" % snapshot)
    if any(not e["complete"] for e in files) or skipped:
        lines.append("coverage is partial; no clean verdict for the whole change")
    if any(e.get("not_scanned") for e in files):
        lines.append("single-file pipeline: smells listed as 'not scanned' were NOT "
                     "checked; a clean line is no evidence for them")
    for entry in files:
        if not entry["complete"]:
            state = "INCOMPLETE - no clean claim"
        elif entry["clean"] and entry.get("advisory"):
            state = "no enforced findings (advisory coaching below)"
        elif entry["clean"]:
            state = "clean (qualified plugins only; not-scanned smells excluded)"
        else:
            state = "coaching below"
        lines.append("- %s: %s" % (entry["file"], state))
        for reason in entry["reasons"]:
            lines.append("  reason: %s" % str(reason)[:300])
        for gap in entry.get("not_scanned") or []:
            lines.append("  not scanned: %s" % str(gap)[:300])
        verdict = entry.get("verdict")
        # Coaching is model-visible independently of the blocking exit status:
        # non-blocking (advisory) verdicts and their targeted Core guidance
        # are never hidden behind a clean line.
        if verdict and (entry["complete"] or entry.get("findings")) and (
                not entry["clean"] or entry.get("advisory")):
            coached = verdict[:1000]
            if len(verdict) > 1000:
                coached += " …[mapper verdict truncated]"
            lines.append("  coaching: %s" % coached)
    for entry in skipped:
        lines.append("- %s: NOT SCANNED (%s)" % (entry.get("path", "?"), entry.get("reason", "unknown")))
    if any(not e["complete"] for e in files) or skipped:
        lines.append("coverage is partial; nothing above is a clean verdict for the whole change")
    text = "\n".join(lines)
    if len(text) > FEEDBACK_MAX_CHARS:
        # Truncated evidence is named as truncated, never silently cut.
        marker = "\n[habit-feedback] feedback truncated at %d characters" % FEEDBACK_MAX_CHARS
        text = text[:FEEDBACK_MAX_CHARS - len(marker)] + marker
    return text


def _outcome(status, files=None, skipped=None, reasons=None):
    files = files or []
    skipped = skipped or []
    return {
        "status": status,
        "feedback": _feedback_text(files, skipped),
        "scanned": files,
        "not_scanned": skipped,
        "reasons": list(reasons or []),
    }


def process_event(event: dict, *, scope_root, state_root=None, session=None,
                  sensor=None, mapper=None, runner=None, now=None,
                  trusted_tool_roots=None) -> dict:
    """Classify one hook event; scan confirmed in-scope mutations.

    Returns {"status", "feedback", "scanned", "not_scanned", "reasons"}.
    `status` is one of scanned | not_scanned | not_mutating | error and is
    never a cleanliness claim.
    """
    now = time.time() if now is None else now
    adapter = _load_adapter()
    if runner is None:
        def runner(project_root, rel, *, sensor, mapper, trusted_root, env):
            return adapter.run_pipeline(
                project_root, sensor_executable=sensor, mapper_executable=mapper,
                file=rel, trusted_config_root=trusted_root,
                mapper_project_root=trusted_root, env=env,
                trusted_tool_roots=trusted_tool_roots)
    if isinstance(event, dict) and len(json.dumps(event).encode("utf-8")) > MAX_EVENT_BYTES:
        return _outcome("not_scanned", reasons=["event exceeds input limit"])
    if not isinstance(event, dict):
        return _outcome("not_scanned", reasons=["event is not a JSON object"])
    scope = Path(scope_root)
    try:
        scope = scope.resolve(strict=True)
    except OSError:
        return _outcome("not_scanned", reasons=["scope root unavailable: %s" % scope_root])
    if not scope.is_dir():
        return _outcome("not_scanned", reasons=["scope root is not a directory: %s" % scope])
    if not _plausible_scope(scope):
        return _outcome("not_scanned",
                        reasons=["scope root %s is too broad to be a scan boundary" % scope])

    state_root = Path(state_root) if state_root is not None else default_state_root()
    if state_root.resolve() == scope or scope in state_root.resolve().parents:
        return _outcome("not_scanned", reasons=["state root cannot be inside the project scope"])
    state_root, root_reason = _checked_state_root(state_root)
    if state_root is None:
        return _outcome("not_scanned", reasons=[root_reason])
    scope_dir = _state_scope_dir(state_root, scope,
                                 session if session is not None else event.get("sessionID"))
    try:
        _secure_directory(scope_dir)
        for filename in ("state.lock", "state.json"):
            candidate = scope_dir / filename
            if os.path.lexists(candidate):
                fd = _secure_file_fd(candidate, os.O_RDONLY)
                os.close(fd)
        state = HookState(scope_dir / "state.json")
        lock_fd = _acquire_lock(scope_dir / "state.lock")
    except OSError as exc:
        return _outcome("not_scanned", reasons=["unsafe state path: %s" % exc])
    if lock_fd is None:
        return _outcome("not_scanned",
                        reasons=["state lock busy longer than %.0fs" % STATE_LOCK_WAIT_S])
    try:
        state.load()
        state.prune(now)
        result = _classify_event(event, state, scope, adapter, scope_dir,
                                 sensor, mapper, runner, now)
        state.save()
        return result
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)


def _classify_event(event, state, scope, adapter, scope_dir, sensor, mapper, runner, now) -> dict:
    phase = event.get("phase")
    tool = event.get("tool")
    call_id = event.get("id")
    if not isinstance(tool, str) or not tool:
        return _outcome("not_scanned", reasons=["event without tool id"])
    if tool.startswith("habit") or "habit-feedback" in tool:
        return _outcome("not_mutating")

    if phase == "before":
        state.remember_before(tool, call_id,
                              {"input": event.get("input"), "sessionID": event.get("sessionID")})
        return _outcome("not_mutating")

    if phase != "after":
        return _outcome("not_scanned", reasons=["unknown event phase: %r" % phase])

    status = event.get("status")
    if status == "error":
        # A failed tool call mutated nothing proven; the original error stays
        # untouched and is never turned into a success by this hook.
        return _outcome("not_mutating")
    if status != "completed":
        return _outcome("not_scanned", reasons=["unknown event status: %r" % status])

    raw_paths: list[str] = []
    skipped: list[dict] = []
    reasons: list[str] = []

    if tool in NATIVE_MUTATING_TOOLS:
        candidate = None
        after_input = event.get("input")
        if isinstance(after_input, dict):
            candidate = after_input.get("path")
        if not isinstance(candidate, str) or not candidate:
            # documented fallback: the paired before event (keyed by CallID)
            pairing, pair_reason = state.take_pairing(tool, call_id)
            if pairing is None:
                return _outcome("not_scanned", reasons=["native event without a documented path input: " + pair_reason])
            pairing_input = pairing.get("input")
            if isinstance(pairing_input, dict):
                candidate = pairing_input.get("path")
        if not isinstance(candidate, str) or not candidate:
            return _outcome("not_scanned",
                            reasons=["native %s event without a documented path input" % tool])
        raw_paths.append(candidate)
    elif tool == GORTEX_CODEMODE_TOOL or tool in GORTEX_MCP_MUTATING_TOOLS:
        mutated, dry, unrecognised = gortex_paths_from_result(event.get("result"))
        raw_paths.extend(mutated)
        if dry:
            reasons.append("dry-run results are not mutations: %s" % ", ".join(dry))
        if unrecognised:
            skipped.extend({"path": item, "reason": "result not recognised as a mutation"}
                           for item in unrecognised)
            if not mutated:
                return _outcome("not_scanned", skipped=skipped, reasons=[
                    "gortex-shaped result not recognised as a mutation: %s" % unrecognised[0]])
    elif tool in KNOWN_READONLY_TOOLS:
        # Documented stock read-only tools: provably nothing to observe.
        return _outcome("not_mutating")
    else:
        # Unknown completed form (bash with opaque commands, unknown patch
        # tools, custom MCP tools): read-only behaviour is NOT proven, so any
        # mutation stays a visible not_scanned coverage gap. No paths are
        # guessed from command or program text, no interpretation, no scan.
        return _outcome("not_scanned", reasons=[
            "completed tool %r is not a proven read-only or documented "
            "mutation form; any files it changed are not scanned "
            "(no path guessing)" % tool])

    if not raw_paths:
        return _outcome("not_mutating", reasons=reasons)

    targets: list[Path] = []
    for raw in raw_paths:
        target, why = resolve_path_evidence(raw, scope)
        if target is None:
            skipped.append({"path": raw, "reason": why})
        elif target not in targets:
            targets.append(target)

    files: list[dict] = []
    scanned_any = False
    for index, target in enumerate(targets):
        rel = target.relative_to(scope).as_posix()
        if index >= MAX_FILES_PER_EVENT:
            skipped.append({"path": rel,
                            "reason": "event file limit (%d) exceeded" % MAX_FILES_PER_EVENT})
            continue
        if target.stat().st_size > MAX_SCAN_FILE_BYTES:
            skipped.append({"path": rel, "reason": "file size exceeds bounded scan limit"})
            continue
        digest = _sha256_file(target)
        if digest is None:
            skipped.append({"path": rel, "reason": "file unreadable"})
            continue
        if state.already_scanned(rel, digest):
            files.append({"file": rel, "complete": True, "clean": False,
                          "advisory": False, "not_scanned": [],
                          "reasons": ["unchanged since last scan (duplicate suppressed)"],
                          "verdict": "", "findings": None})
            continue
        sensor_exe, mapper_exe, missing = _locate_executables(sensor, mapper)
        if sensor_exe is None or mapper_exe is None:
            skipped.append({"path": rel, "reason": "; ".join(missing)})
            continue
        if any(scope == exe.resolve() or scope in exe.resolve().parents
               for exe in (sensor_exe, mapper_exe)):
            skipped.append({"path": rel, "reason":
                            "repository-resolved CLI installation refused"})
            continue
        paths = _runtime_dirs(scope_dir)
        config, config_reason = _ensure_runtime_config(scope_dir, adapter)
        if config is None:
            skipped.append({"path": rel, "reason": config_reason})
            continue
        files.append(_scan_with(adapter, runner, scope, target, sensor_exe, mapper_exe, paths))
        if _sha256_file(target) != digest:
            files[-1]["complete"] = False
            files[-1]["clean"] = False
            files[-1]["reasons"].append("file changed during scan; retry required")
        if files[-1]["complete"]:
            state.record_scan(rel, digest, now)
        scanned_any = True

    reasons.extend("not scanned: %s (%s)" % (s.get("path"), s.get("reason")) for s in skipped)
    return _outcome("scanned" if scanned_any else "not_scanned", files, skipped, reasons)


def _scan_with(adapter, runner, scope: Path, target: Path, sensor: Path, mapper: Path,
               paths: dict) -> dict:
    rel = target.relative_to(scope).as_posix()
    try:
        result = runner(scope, rel, sensor=sensor, mapper=mapper,
                        trusted_root=paths["runtime"], env=_pipeline_env(paths))
    except adapter.ConfigRejected as exc:
        return {"file": rel, "complete": False, "clean": False, "advisory": False,
                "not_scanned": [],
                "reasons": ["config rejected: %s" % exc], "verdict": "", "findings": None}
    return _summarise(result, rel, adapter)


def _install_signal_handlers(adapter):
    """SIGTERM during a bridge run: kill active pipeline groups, exit non-zero."""

    def on_term(signum, frame):
        try:
            adapter.kill_active()
        finally:
            raise SystemExit(128 + signal.SIGTERM)

    signal.signal(signal.SIGTERM, on_term)


def _read_stdin_bounded(limit: int = MAX_EVENT_BYTES) -> str | None:
    raw = sys.stdin.buffer.read(limit + 1)
    if len(raw) > limit:
        return None
    return raw.decode("utf-8")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] != "event":
        json.dump({"status": "error", "reasons": ["usage: habit_feedback_hook.py event"]},
                  sys.stdout)
        return 2
    _install_signal_handlers(_load_adapter())
    try:
        payload = _read_stdin_bounded()
    except UnicodeDecodeError:
        json.dump({"status": "error", "reasons": ["event is not UTF-8"]}, sys.stdout)
        return 0
    if payload is None:
        json.dump({"status": "error",
                   "reasons": ["event payload exceeds %d bytes" % MAX_EVENT_BYTES]}, sys.stdout)
        return 0
    try:
        event = json.loads(payload)
        scope = os.environ["HABIT_FEEDBACK_SCOPE"]
    except (ValueError, KeyError) as exc:
        json.dump({"status": "error", "reasons": ["bad transport: %s" % exc]}, sys.stdout)
        return 0
    state_root = os.environ.get("HABIT_FEEDBACK_STATE_ROOT")
    session = os.environ.get("HABIT_FEEDBACK_SESSION")
    try:
        # Only host/installer-controlled launch configuration grants trust.
        # Never inspect event/input/output or project config for these roots.
        raw_roots = os.environ.get("HABIT_FEEDBACK_TRUSTED_TOOL_ROOTS")
        roots = json.loads(raw_roots) if raw_roots is not None else None
        if roots is not None and (not isinstance(roots, list)
                                  or not all(isinstance(root, str) for root in roots)):
            raise ValueError("trusted tool roots must be a JSON array of installation paths")
        outcome = process_event(event, scope_root=scope, state_root=state_root,
                                session=session, trusted_tool_roots=roots)
    except Exception as exc:  # the hook must never break the tool result
        outcome = {"status": "error", "feedback": None, "scanned": [], "not_scanned": [],
                   "reasons": ["hook error: %s" % exc]}
    json.dump(outcome, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Safe adapter around the original Habit Hooks pipeline (habit-sensors | habit-mapper).

This module is deliberately *only* an adapter: it spawns the two original CLI
stages with an argument vector (never a shell string), enforces time and
output limits, keeps sensor and mapper status/stderr strictly separate, and
refuses configurations or paths that would widen the run beyond the caller's
project and single-file scope. It contains no smell routing, no guide
selection and no fix logic of its own — all of that stays in the original
tools (the mapper owns guide routing; the adapter never re-implements it).

Qualified original behaviour this adapter relies on (evidence: VERSIONS.md,
isolated runs with habit-hooks 1.5.0):
- ``habit-sensors`` exits 0 both for a clean run and for a run with findings;
  a non-zero sensor exit or the reserved ``incomplete-run`` finding means the
  run did not complete. ``habit-mapper`` exits 0/1 for verdicts and 2 when
  nothing arrived on stdin.
- Repeating ``--file`` is single-value: only the *last* path is measured. The
  adapter therefore accepts exactly one file per call and never silently
  measures a subset.
- A scope that matched nothing prints a stderr notice ("nothing scanned",
  "nothing matched", "no [files] are configured", plugin "not enabled") while
  stdout still carries ``[]`` and exit 0 — an empty array alone is never a
  completeness proof.
- ``--config`` accepts a config outside the project; the runner then still
  resolves project-local plugin overrides from ``.habit-hooks/`` in its working
  directory (qualified: an external config alone does not fence those off),
  and the ruff detector writes a ``.ruff_cache`` directory into the project
  unless the caller points ``RUFF_CACHE_DIR`` elsewhere (documented for T02).

Stable API for the follow-up tasks (T02 hook, T03 package checks):
    run_pipeline(...) -> PipelineResult
    validate_config(doc) -> list[str]   (rejection reasons; empty list = accepted)
    load_config(project_root, config_path=None, trusted_config_root=None) -> dict
    safe_relative_file(project_root, candidate) -> Path
    ConfigRejected

Tool output (findings, messages, coaching text) is untrusted data. Nothing in
this module interprets tool output as an instruction, and the module never
installs tools, fixes code or snoozes findings (``--no-snooze``). It writes
only disposable validated scope configurations under /tmp/opencode, never
repository source/configuration. Markdown/Jinja is not a sandbox: repository
guide roots and trusted mapper guide symlink escapes are refused before spawn.
"""
from __future__ import annotations

import ctypes
import json
import math
import os
import re
import select
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import tomllib
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

# Named limits owned by this adapter (S00: benannte Werte am Eigentümer).
SENSOR_TIMEOUT_S = 30.0
MAPPER_TIMEOUT_S = 30.0
MAX_OUTPUT_BYTES = 1_000_000
SELECT_POLL_S = 0.05
READ_CHUNK = 65536
REAP_GRACE_S = 2.0

INCOMPLETE_RUN_SMELL = "incomplete-run"
GUIDE_EXTENSION = ".md"
RUNNER_NOTICE_PREFIX = "habit-sensors:"

# The only plugins this version has qualified (VERSIONS.md). Anything else is
# rejected rather than run unqualified; T03 may widen the set with evidence.
QUALIFIED_PLUGINS = frozenset({"generic", "python"})

# Detector tools the qualified plugins actually spawn (evidence: the plugin
# config.toml detector declarations, VERSIONS.md). Used only to *refuse*
# project-local shadows before anything is spawned - never executed here.
PLUGIN_SENSOR_TOOLS = {
    "generic": {"jscpd": "jscpd"},
    "python": {"ruff": "ruff", "deptry": "deptry"},
}

# Repository-wide sensors of the qualified plugins: their original recipes
# read their own paths (deptry scans '.', jscpd its configured/'src' paths)
# and have no proven single-file scope, so the single-file adapter disables
# them up front in the config the sensor stage reads (a real spawn-time scan
# limitation, never a findings filter) and reports the coverage gap in
# PipelineResult.not_scanned.
REPOSITORY_SENSORS = {
    "generic": {"jscpd": "duplicated-code"},
    "python": {"deptry": "unused-dependency"},
}

# Project directories the original tool_search_path puts ahead of PATH.
PROJECT_TOOL_DIRS = ("node_modules/.bin", ".venv/bin")

TREE_KILL_SLEEP_S = 0.05
DERIVED_CONFIG_ROOT = Path("/tmp/opencode")

# Top-level config keys the adapter understands; unknown keys are rejected so a
# future capability (especially anything executing commands) cannot slip in.
KNOWN_CONFIG_KEYS = frozenset(
    {"plugins", "transformers", "files", "uncoached", "smells", "sensors", "scope", "runners"}
)

# Sensor overrides that only narrow or disable are safe; anything that changes
# what gets *executed* (command/args) is not, without an explicit trust grant.
SAFE_SENSOR_OVERRIDE_KEYS = frozenset({"disabled", "files"})

KNOWN_UNCOACHED_VALUES = frozenset({"suggest", "ignore", "enforce"})

# stderr fragments (from the qualified runs) that mean "coverage was not what
# the caller thinks" — a run showing one of these is never complete.
COVERAGE_MARKERS = (
    "nothing scanned",
    "nothing matched",
    "no [files] are configured",
    "plugin is installed but not enabled",
    "not enabled",
)


class ConfigRejected(Exception):
    """The configuration, scope or executables ask for something this adapter refuses."""


@dataclass(frozen=True)
class StageOutcome:
    """One pipeline stage: status, exit code and captured output, kept separate."""

    status: str  # ok | failed | timed_out | missing | output_too_large | skipped
    exit_code: int | None
    stdout: str
    stderr: str
    argv: tuple[str, ...]


@dataclass(frozen=True)
class PipelineResult:
    """Full result of one original-pipeline run.

    ``complete`` is an observation of a finished scan, not an exit-code or JSON
    signal alone: the sensor stage must exit 0, emit a structurally valid
    findings array, carry no ``incomplete-run`` finding and no coverage doubt
    (qualified nothing-scanned / plugin-not-enabled notices on stderr, plus any
    unclassifiable runner notice — unknown coverage is treated as unchecked,
    never as complete), and the mapper must have produced a definitive verdict
    (exit 0/1). Every gap is listed in ``reasons``; partial evidence stays in
    the stage outcomes instead of being re-framed as a clean result.
    """

    sensor: StageOutcome
    mapper: StageOutcome
    findings: list | None
    complete: bool
    reasons: list[str] = field(default_factory=list)
    # Smells this single-file run provably did not cover (e.g. disabled
    # repository-wide sensors). Visible coverage boundary, not a failure of
    # the file-scoped sensors that did run.
    not_scanned: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        """A complete run whose mapper verdict is exit 0 (no enforced smell)."""
        return self.complete and self.mapper.exit_code == 0


def _validated_executable(executable: str | Path, role: str) -> Path:
    """The original CLI must be a real, executable regular file."""
    real = Path(os.path.abspath(str(executable)))
    if not real.exists():
        raise ConfigRejected("%s executable not found: %s" % (role, executable))
    if not real.is_file():
        raise ConfigRejected("%s executable is not a regular file: %s" % (role, executable))
    if not os.access(real, os.X_OK):
        raise ConfigRejected("%s executable is not executable: %s" % (role, executable))
    return real


def _root_identity(root: Path):
    st = os.stat(root)
    return (st.st_dev, st.st_ino)


def _kill_group(proc):
    """Best-effort kill of the leader's own process group (fallback only)."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except OSError:
        try:
            proc.kill()
        except OSError:
            pass


def _reap(proc, grace_s=REAP_GRACE_S):
    """Reap the leader with a bounded wait; never block indefinitely."""
    try:
        proc.wait(timeout=grace_s)
    except subprocess.TimeoutExpired:
        _kill_group(proc)
        try:
            proc.wait(timeout=grace_s)
        except subprocess.TimeoutExpired:
            pass


# --- Complete cleanup of the actual original process topology ----------------
#
# The original spawn.py puts every sensor helper and the detectors it runs
# into their own session/process group (setsid), so a killpg on the two
# top-level adapter leaders never reaches them. Cleanup therefore proves
# membership per pid from /proc: the leader, everything whose parent chain
# reaches it, and - while the stage subreaper holds them - orphans the
# leader left behind that were reparented to this process inside the
# stage's start window AND carrying its exact inherited ownership token.
# An ordinary direct child is never admitted merely by its parent/start time.
# Nothing outside that proof is ever signalled, every
# loop is bounded, and zombies adopted by the subreaper are reaped so no
# own remains survive a timeout, an output limit or a bridge SIGTERM.

_PR_SET_CHILD_SUBREAPER = 36
_TREE_WALK_HOPS = 128


def _proc_stat(pid: int):
    """(ppid, pgid, starttime, state) from /proc/<pid>/stat, or None."""
    try:
        with open("/proc/%d/stat" % pid, "r", encoding="utf-8") as handle:
            data = handle.read()
    except OSError:
        return None
    try:
        tail = data[data.rindex(")") + 2:].split()
        return int(tail[1]), int(tail[2]), int(tail[19]), tail[0]
    except (ValueError, IndexError):
        return None


STAGE_MARKER_ENV = "AWC_HABIT_STAGE"


def _stage_marker_token() -> bytes:
    """A unique non-secret ownership token for one stage's environment.

    Only processes spawned by this stage (and everything that inherits their
    environment) can carry it, so an adoptable orphan is proven to be ours -
    a shared parent and a start time alone never establish that (RV03)."""
    return (STAGE_MARKER_ENV + "=" + os.urandom(16).hex()).encode("ascii")


def _has_stage_marker(pid: int, marker: bytes) -> bool:
    """Targeted ownership check on one candidate's environ - no broad scan."""
    try:
        with open("/proc/%d/environ" % pid, "rb") as handle:
            return marker in handle.read().split(b"\0")
    except OSError:
        return False


def _proven_members(proc, leader_start, marker: bytes, ledger: dict, others: set) -> dict:
    """Extend and re-validate the stage's pid ledger (pid -> starttime).

    Two proofs admit a pid, and nothing else: an unbroken /proc parent chain
    to the stage leader (excluding every other registered stage), or - for a
    direct child of this process, the only shape a subreaper-adopted orphan
    has - the stage's unique environment marker plus a start time inside the
    stage window. Ordinary children of this process (other threads' tools,
    unrelated subprocesses) carry no marker and are never admitted, killed or
    reaped here. Ledger entries whose recorded start time no longer matches
    (PID reuse) are dropped before any signal is sent.
    """
    stats = {}
    try:
        names = os.listdir("/proc")
    except OSError:
        return ledger
    me = os.getpid()
    for name in names:
        if not name.isdigit():
            continue
        pid = int(name)
        if pid == me or pid in others:
            continue
        info = _proc_stat(pid)
        if info is not None:
            stats[pid] = info
    if proc.pid in stats and leader_start is not None and stats[proc.pid][2] != leader_start:
        del stats[proc.pid]  # reused leader pid is never an ancestry proof
    for pid in list(ledger):
        if pid in stats and stats[pid][2] != ledger[pid]:
            del ledger[pid]
    for pid, (ppid, _pgid, start, _state) in stats.items():
        if pid in ledger:
            continue
        proven = False
        cur, hops = pid, 0
        while cur in stats and hops <= _TREE_WALK_HOPS:
            if cur == proc.pid:
                proven = True
                break
            if cur in others:
                break
            cur = stats[cur][0]
            hops += 1
        if not proven and ppid == me and marker is not None:
            if (leader_start is None or start >= leader_start) and _has_stage_marker(pid, marker):
                proven = True
        if proven:
            ledger[pid] = start
    return ledger


def _alive(pid: int) -> bool:
    info = _proc_stat(pid)
    return info is not None and info[3] != "Z"


_SUBREAP_LOCK = threading.Lock()
_SUBREAP_DEPTH = 0
_SUBREAP_PREVIOUS = 0
_PR_GET_CHILD_SUBREAPER = 37


def _prctl_subreaper(flag: int) -> None:
    """Require the Linux orphan-adoption guarantee; never silently degrade."""
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(_PR_SET_CHILD_SUBREAPER, ctypes.c_ulong(flag), 0, 0, 0) != 0:
        raise ConfigRejected("stage subreaper unavailable; complete cleanup cannot be guaranteed")


def _subreaper_enter() -> None:
    global _SUBREAP_DEPTH, _SUBREAP_PREVIOUS
    with _SUBREAP_LOCK:
        if _SUBREAP_DEPTH == 0:
            previous = ctypes.c_int()
            libc = ctypes.CDLL(None, use_errno=True)
            if libc.prctl(_PR_GET_CHILD_SUBREAPER, ctypes.byref(previous), 0, 0, 0) != 0:
                raise ConfigRejected("cannot establish stage orphan-adoption boundary")
            _SUBREAP_PREVIOUS = previous.value
            _prctl_subreaper(1)
        _SUBREAP_DEPTH += 1


def _subreaper_exit() -> None:
    global _SUBREAP_DEPTH
    with _SUBREAP_LOCK:
        _SUBREAP_DEPTH = max(0, _SUBREAP_DEPTH - 1)
        if _SUBREAP_DEPTH == 0:
            _prctl_subreaper(_SUBREAP_PREVIOUS)


def _leader_start(proc):
    """The leader's /proc starttime, cached on the Popen object."""
    start = getattr(proc, "_awc_leader_start", None)
    if start is None:
        info = _proc_stat(proc.pid)
        start = info[2] if info is not None else None
        proc._awc_leader_start = start
    return start


def _reap_members(members, proc) -> None:
    """Reap zombies the subreaper adopted; the leader belongs to _reap."""
    for pid in members:
        if pid == proc.pid:
            continue
        try:
            os.waitpid(pid, os.WNOHANG)
        except OSError:
            pass


def _cleanup_stage(proc) -> None:
    """Kill and reap the whole proven stage tree, bounded; no foreign pids.

    Only ledger pids (parent-chain or stage-marker proven, start-time
    revalidated against PID reuse) are ever signalled or reaped; ordinary
    children of this process started by other threads keep living and keep
    their exit status for their owner (RV03)."""
    if not os.path.isdir("/proc"):
        _kill_group(proc)
        _reap(proc)
        return
    others = {p.pid for p, _s, _m in list(_ACTIVE_STAGES) if p is not proc}
    leader_start = _leader_start(proc)
    marker = getattr(proc, "_awc_stage_marker", None)
    ledger = {}
    deadline = time.monotonic() + REAP_GRACE_S
    while True:
        _proven_members(proc, leader_start, marker, ledger, others)
        _reap_members(set(ledger), proc)
        live = {pid for pid in ledger if _alive(pid)}
        if not live:
            break
        for pid in sorted(live):
            info = _proc_stat(pid)
            if info is None:
                continue
            _ppid, pgid, _start, _state = info
            try:
                # Only groups proven to be stage members (or the leader's
                # own) are signalled; a pgid outside the proof gets a plain
                # kill of the member pid instead.
                if pgid == pid or pgid in ledger or pgid == proc.pid:
                    os.killpg(pgid, signal.SIGKILL)
                else:
                    os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        if time.monotonic() >= deadline:
            break
        time.sleep(TREE_KILL_SLEEP_S)
    _reap(proc)
    # One bounded final sweep: proven orphans that only surfaced after the
    # leader was reaped must not survive as zombies of this process either.
    sweep_deadline = time.monotonic() + 1.0
    while time.monotonic() < sweep_deadline:
        _proven_members(proc, leader_start, marker, ledger, others)
        _reap_members(set(ledger), proc)
        pending = [pid for pid in ledger if _proc_stat(pid) is not None]
        if not pending:
            break
        time.sleep(TREE_KILL_SLEEP_S)


# Stages currently running inside _run_stage, so an external termination
# request (T02 hook bridge shutdown) can clean up their full process trees.
# Each entry: (Popen, leader_starttime, stage marker) - the marker is the
# orphan-adoption ownership proof, start time the PID-reuse check.
_ACTIVE_STAGES: list = []


def register_active_proc(proc):
    _ACTIVE_STAGES.append(
        (proc, _leader_start(proc), getattr(proc, "_awc_stage_marker", None)))


def unregister_active_proc(proc):
    for entry in list(_ACTIVE_STAGES):
        if entry[0] is proc:
            _ACTIVE_STAGES.remove(entry)


def kill_active():
    """Best-effort complete cleanup of every stage tree currently in _run_stage."""
    for proc, _start, _marker in list(_ACTIVE_STAGES):
        _cleanup_stage(proc)


def _close_quietly(stream):
    if stream is None:
        return
    try:
        stream.close()
    except OSError:
        pass


def _run_stage(argv, stdin_bytes, timeout_s, cwd, env, max_output_bytes):
    """Run one stage with all I/O multiplexed against one deadline.

    stdin, stdout and stderr are handled in a single select loop, so a stage
    that never reads its stdin, or one that closes both output pipes and keeps
    sleeping, is still bounded by ``timeout_s`` counted from the spawn. Output
    is accumulated in bounded chunks; exceeding ``max_output_bytes`` kills the
    process group and reports ``output_too_large`` instead of buffering
    unboundedly. The group is always cleaned up and the leader reaped with a
    bounded wait before returning.
    """
    if not isinstance(timeout_s, (int, float)) or not math.isfinite(timeout_s) or timeout_s <= 0:
        raise ConfigRejected("timeout must be a positive finite number, got %r" % (timeout_s,))
    if not isinstance(max_output_bytes, int) or max_output_bytes <= 0:
        raise ConfigRejected("max_output_bytes must be a positive integer, got %r" % (max_output_bytes,))
    if stdin_bytes is not None and len(stdin_bytes) > max_output_bytes:
        # Derived pipe payload stays bounded by the same validated limit.
        raise ConfigRejected("stdin payload exceeds max_output_bytes")

    exe = Path(argv[0])
    if not exe.exists():
        return StageOutcome("missing", None, "", "executable not found: %s" % argv[0], tuple(argv)), b""
    _subreaper_enter()
    stage_marker = _stage_marker_token()
    spawn_env = dict(env) if env is not None else dict(os.environ)
    if spawn_env is not None:
        # Unique non-secret ownership token, inherited only by this stage's
        # descendants (RV03 orphan-adoption proof); any caller value is
        # overridden so no caller can forge it.
        spawn_env[STAGE_MARKER_ENV] = stage_marker[len(STAGE_MARKER_ENV) + 1:].decode("ascii")
    try:
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE if stdin_bytes is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=spawn_env,
            start_new_session=True,
        )
    except OSError as exc:
        _subreaper_exit()
        return StageOutcome("failed", None, "", "spawn failed: %s" % exc, tuple(argv)), b""
    proc._awc_stage_marker = stage_marker
    register_active_proc(proc)

    deadline = time.monotonic() + timeout_s
    buffers = {proc.stdout: bytearray(), proc.stderr: bytearray()}
    pending = {proc.stdout, proc.stderr}
    stdin_remaining = bytearray(stdin_bytes) if stdin_bytes is not None else None
    if stdin_remaining is not None:
        os.set_blocking(proc.stdin.fileno(), False)

    # select.poll is used (not select.select): the write-interest (POLLOUT)
    # for stdin must be observable alongside the read interests.
    poller = select.poll()
    by_fd = {}
    for stream in pending:
        poller.register(stream.fileno(), select.POLLIN | select.POLLHUP)
        by_fd[stream.fileno()] = stream
    if stdin_remaining is not None:
        poller.register(proc.stdin.fileno(), select.POLLOUT)
        by_fd[proc.stdin.fileno()] = proc.stdin

    def _unregister(stream):
        try:
            poller.unregister(stream.fileno())
        except (KeyError, OSError, ValueError):
            pass

    limit_hit = False
    try:
        while pending or stdin_remaining:
            timeout_left = deadline - time.monotonic()
            if timeout_left <= 0:
                _cleanup_stage(proc)
                return (
                    StageOutcome("timed_out", None, "", "stage exceeded %.0fs" % timeout_s, tuple(argv)),
                    b"",
                )
            events = poller.poll(min(SELECT_POLL_S, timeout_left) * 1000)
            for fd, event in events:
                stream = by_fd.get(fd)
                if stream is None:
                    continue
                if stdin_remaining is not None and stream is proc.stdin:
                    if event & (select.POLLERR | select.POLLNVAL):
                        stdin_remaining = None
                        _unregister(stream)
                        _close_quietly(stream)
                        continue
                    if event & select.POLLOUT:
                        try:
                            written = os.write(fd, bytes(stdin_remaining[:READ_CHUNK]))
                            del stdin_remaining[:written]
                        except BrokenPipeError:
                            # The stage will not read more input; that is its
                            # verdict to make, the deadline still bounds us.
                            stdin_remaining = None
                        except BlockingIOError:
                            pass  # pipe full: try again when writable again
                        except OSError:
                            stdin_remaining = None
                        if stdin_remaining is not None and not stdin_remaining:
                            stdin_remaining = None
                        if stdin_remaining is None:
                            _unregister(stream)
                            _close_quietly(stream)
                    continue
                if event & (select.POLLIN | select.POLLHUP):
                    try:
                        chunk = os.read(fd, READ_CHUNK)
                    except OSError:
                        chunk = b""
                    if not chunk:
                        pending.discard(stream)
                        _unregister(stream)
                        _close_quietly(stream)
                        continue
                    buf = buffers[stream]
                    buf.extend(chunk)
                    if len(buf) > max_output_bytes:
                        limit_hit = True
                        break
            if limit_hit:
                break

        out, err = bytes(buffers[proc.stdout]), bytes(buffers[proc.stderr])
        if limit_hit:
            _cleanup_stage(proc)
            return (
                StageOutcome(
                    "output_too_large",
                    None,
                    out[:max_output_bytes].decode("utf-8", errors="replace"),
                    err[:max_output_bytes].decode("utf-8", errors="replace")
                    + "\n[adapter] output exceeded %d bytes; process group killed" % max_output_bytes,
                    tuple(argv),
                ),
                b"",
            )

        # Both output pipes hit EOF: the stage has finished writing; bound the
        # wait for its exit by the same deadline.
        while proc.poll() is None:
            timeout_left = deadline - time.monotonic()
            if timeout_left <= 0:
                _cleanup_stage(proc)
                return (
                    StageOutcome("timed_out", None, "", "stage exceeded %.0fs" % timeout_s, tuple(argv)),
                    b"",
                )
            try:
                proc.wait(timeout=timeout_left)
            except subprocess.TimeoutExpired:
                continue
        # Leader exited; clean up any surviving tree members, bounded.
        _cleanup_stage(proc)
        return (
            StageOutcome(
                "ok",
                proc.returncode,
                out.decode("utf-8", errors="replace"),
                err.decode("utf-8", errors="replace"),
                tuple(argv),
            ),
            out,
        )
    finally:
        _cleanup_stage(proc)
        unregister_active_proc(proc)
        _subreaper_exit()
        # Always close every pipe we opened — also on the timeout, output-limit
        # and early-return paths; a global hook runs this per tool event, so a
        # leaked fd would accumulate. No warning suppression anywhere.
        _close_quietly(proc.stdin)
        _close_quietly(proc.stdout)
        _close_quietly(proc.stderr)


def safe_relative_file(project_root: Path, candidate: str) -> Path:
    """Validate one in-scope file: relative, inside the project, no symlink escape.

    Raises ``ConfigRejected`` with the exact reason otherwise. The returned path
    is fully resolved; symlinked files are accepted only when they stay inside
    the project root.
    """
    root = project_root.resolve()
    posix = PurePosixPath(candidate)
    if posix.is_absolute() or ".." in posix.parts:
        raise ConfigRejected("file outside project scope: %s" % candidate)
    target = (root / Path(*posix.parts)).resolve()
    if target != root and root not in target.parents:
        raise ConfigRejected("file resolves outside project scope: %s -> %s" % (candidate, target))
    if not target.is_file():
        raise ConfigRejected("file does not exist: %s" % candidate)
    return target


def _reject_project_plugin_overrides(project_root: Path) -> None:
    """Reject original project plugin overrides under ``.habit-hooks/``.

    The original runner resolves ``.habit-hooks/<plugin>/config.toml``,
    ``.../sensors/*.toml`` and ``.../transformers/*.toml`` from its working
    directory regardless of where ``--config`` points. Those files can define
    arbitrary commands, so without a separate trust grant any of them —
    including via symlinked paths — is refused before anything is spawned.
    """
    hh = project_root / ".habit-hooks"
    if not hh.is_dir():
        return
    try:
        entries = list(os.scandir(hh))
    except OSError as exc:
        raise ConfigRejected("cannot inspect .habit-hooks: %s" % exc) from exc
    for entry in entries:
        if entry.name == "config.toml":
            continue  # the root config, validated separately
        if entry.is_symlink():
            raise ConfigRejected(
                "symlinked plugin path under .habit-hooks refused: %s" % entry.path
            )
        if not entry.is_dir(follow_symlinks=False):
            raise ConfigRejected("unexpected file under .habit-hooks refused: %s" % entry.path)
        plugin_dir = Path(entry.path)
        candidates = [plugin_dir / "config.toml"]
        for sub in ("sensors", "transformers"):
            sub_dir = plugin_dir / sub
            if sub_dir.is_symlink() or sub_dir.is_dir():
                candidates.extend(sorted(sub_dir.glob("*.toml")))
        for dangerous in candidates:
            if dangerous.exists() or dangerous.is_symlink():
                raise ConfigRejected(
                    "project plugin override can execute commands (no trust grant): %s"
                    % dangerous.relative_to(project_root)
                )


def _validate_guide_boundary(root: Path, *, repository: bool) -> None:
    """Markdown is executable Jinja in the original mapper, not a sandbox.

    Repository-owned guide roots are never trusted. An explicitly controlled
    mapper root may contain guides, but not symlinks escaping that trust root.
    No templates are read, interpreted or rendered during this check.
    """
    for plugin in QUALIFIED_PLUGINS:
        directory = root / ".habit-hooks" / plugin / "guides"
        if repository and (directory.exists() or directory.is_symlink()):
            raise ConfigRejected("repository-controlled Jinja guides refused (no trust grant): %s" % directory)
        if not repository and (directory.exists() or directory.is_symlink()):
            for component in (directory, directory.parent, directory.parent.parent):
                if component.is_symlink():
                    raise ConfigRejected("symlinked trusted guide directory refused: %s" % component)
            for candidate in directory.rglob("*"):
                if (candidate.is_symlink() or not candidate.resolve().is_relative_to(root)
                        or (candidate.is_file() and candidate.stat().st_nlink != 1)):
                    raise ConfigRejected("trusted guide symlink/escape refused: %s" % candidate)


def validate_config(doc: dict) -> list[str]:
    """Return rejection reasons for a parsed config.toml document.

    Only Markdown coaching is supported: any ``[runners]`` entry (executable
    fix-guides), any transformer, any sensor override that changes what gets
    executed (command/args), unqualified plugins, an empty plugin list (unknown
    coverage) and unknown top-level keys are rejected. Guide overrides must be
    plain ``.md`` file names without traversal. Types are checked defensively —
    the document is untrusted input and must never raise through this function.
    """
    reasons: list[str] = []
    if not isinstance(doc, dict):
        return ["config is not a TOML table"]
    for key in doc:
        if key not in KNOWN_CONFIG_KEYS:
            reasons.append("unknown config key (refused, may execute commands): %r" % key)
    runners = doc.get("runners") or {}
    if not isinstance(runners, dict) or runners:
        reasons.append("executable fix-guides are not supported: [runners] must be absent/empty")
    plugins = doc.get("plugins")
    if not isinstance(plugins, list) or not plugins or not all(isinstance(p, str) for p in plugins):
        reasons.append("plugins must be a non-empty list of strings (unknown coverage otherwise)")
    else:
        for name in plugins:
            if name not in QUALIFIED_PLUGINS:
                reasons.append(
                    "plugin not qualified for 0.1.0: %r (qualified: %s)" % (name, sorted(QUALIFIED_PLUGINS))
                )
    transformers = doc.get("transformers") or []
    if transformers:
        reasons.append("transformers are not supported without an explicit trust grant: %r" % transformers)
    uncoached = doc.get("uncoached")
    if uncoached is not None and uncoached not in KNOWN_UNCOACHED_VALUES:
        reasons.append("uncoached must be one of %s" % sorted(KNOWN_UNCOACHED_VALUES))
    sensors = doc.get("sensors")
    if sensors is not None and not isinstance(sensors, dict):
        reasons.append("[sensors] must be a table")
        sensors = {}
    for name, override in (sensors or {}).items():
        if not isinstance(override, dict):
            reasons.append("sensor override for %r must be a table" % name)
            continue
        unsafe = sorted(set(override) - SAFE_SENSOR_OVERRIDE_KEYS)
        if unsafe:
            reasons.append("sensor override for %r may execute commands (refused keys: %s)" % (name, unsafe))
    smells = doc.get("smells")
    if smells is not None and not isinstance(smells, dict):
        reasons.append("[smells] must be a table")
        smells = {}
    for name, override in (smells or {}).items():
        if not isinstance(override, dict):
            reasons.append("smell override for %r must be a table" % name)
            continue
        guide = override.get("guide")
        if guide is not None:
            posix = PurePosixPath(str(guide))
            if posix.is_absolute() or ".." in posix.parts or len(posix.parts) != 1 or posix.suffix != GUIDE_EXTENSION:
                reasons.append("unsafe guide override for smell %r: %s" % (name, guide))
    return reasons


def load_config(project_root: Path, config_path: Path | None = None,
                trusted_config_root: Path | None = None) -> dict:
    """Read and validate the config actually used for the run.

    Resolution order (no auto-trust from tool data, ever):

    - explicit ``config_path`` — must resolve inside ``project_root`` or inside
      ``trusted_config_root`` (when that explicit trust boundary is given);
    - otherwise the project's own ``.habit-hooks/config.toml``;
    - otherwise, with a ``trusted_config_root``, exactly
      ``<trusted_config_root>/config.toml`` (the plugin-controlled runtime
      config for repositories without their own Habit Hooks setup — no
      repository mutation needed).

    A config that is missing everywhere is rejected — an unconfigured project
    has unknown coverage, which must never become a false-clean result.
    """
    root = project_root.resolve()
    trusted = None
    if trusted_config_root is not None:
        trusted = Path(trusted_config_root).resolve()
        if not trusted.is_dir():
            raise ConfigRejected("trusted_config_root is not a directory: %s" % trusted_config_root)

    path = _resolve_config_path(root, config_path, trusted_config_root)

    inside_project = path == root or root in path.parents
    inside_trusted = trusted is not None and (path == trusted or trusted in path.parents)
    if not (inside_project or inside_trusted):
        raise ConfigRejected("config resolves outside project and trusted scope: %s" % path)
    if not path.is_file():
        raise ConfigRejected("config not found (unknown coverage): %s" % path)
    try:
        doc = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError) as exc:
        raise ConfigRejected("config unreadable: %s" % exc) from exc
    reasons = validate_config(doc)
    if reasons:
        raise ConfigRejected("; ".join(reasons))
    return doc




def _resolve_config_path(root: Path, config_path, trusted_config_root) -> Path:
    """The config file a run would use - the exact load_config resolution."""
    trusted = None
    if trusted_config_root is not None:
        trusted = Path(trusted_config_root).resolve()
    if config_path is not None:
        real = Path(config_path).resolve()
        inside_root = real == root or root in real.parents
        inside_trusted = trusted is not None and (real == trusted or trusted in real.parents)
        if not (inside_root or inside_trusted):
            raise ConfigRejected("config resolves outside project and trusted scope: %s" % config_path)
        return real
    project_config = root / ".habit-hooks" / "config.toml"
    if project_config.is_file():
        return project_config.resolve()
    if trusted is not None and (trusted / "config.toml").is_file():
        return (trusted / "config.toml").resolve()
    raise ConfigRejected("config not found (unknown coverage): project and trusted root have none")


_BARE_TOML_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


def _toml_key(key: str) -> str:
    return key if _BARE_TOML_KEY.match(key) else json.dumps(key)


def _toml_value(value):
    """One TOML scalar/list value; JSON string escaping is TOML-compatible."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    raise ConfigRejected("config value cannot be re-serialized for the single-file run: %r" % (value,))


def _write_toml(doc: dict) -> str:
    """Deterministic TOML for a *validated* config document (subset: scalar
    keys, scalar lists, one/two levels of tables). The caller re-parses and
    compares before use; anything outside the subset is refused visibly."""
    lines = []
    tables = []
    for key, value in doc.items():
        if isinstance(value, dict):
            tables.append((key, value))
        else:
            lines.append("%s = %s" % (_toml_key(key), _toml_value(value)))
    for key, table in tables:
        lines.extend(("", "[%s]" % _toml_key(key)))
        for name, value in table.items():
            if isinstance(value, dict):
                lines.extend(("", "[%s.%s]" % (_toml_key(key), _toml_key(name))))
                for inner_name, inner in value.items():
                    if isinstance(inner, dict):
                        raise ConfigRejected(
                            "config nests deeper than the validated subset: %s.%s.%s"
                            % (key, name, inner_name))
                    lines.append("%s = %s" % (_toml_key(inner_name), _toml_value(inner)))
            else:
                lines.append("%s = %s" % (_toml_key(name), _toml_value(value)))
    return "\n".join(lines) + "\n"


def _configured_file_sensor_gaps(doc: dict) -> list[str]:
    """Visible coverage boundaries of the qualified file sensors (RV06).

    No local matcher: original sensor-files patterns narrow the original
    scope, but the CLI supplies no per-sensor measured-file receipt. Until
    that scope can be qualified safely, any non-None files override prevents
    an unqualified complete/clean claim, even when findings are returned.
    Disabled preferences remain disabled; original sensors still own scanning.
    """
    qualified = {
        "python": {"ruff": "Python/ruff: high-complexity, too-many-parameters, "
                   "oversized-function, unused-variable, unused-import, "
                   "swallowed-exception, parse-error"},
        "generic": {"line-count": "oversized-file"},
    }
    overrides = doc.get("sensors") or {}
    gaps = []
    for plugin in doc.get("plugins", []):
        for sensor, coverage in qualified.get(plugin, {}).items():
            override = overrides.get(sensor) or {}
            if override.get("disabled") is True:
                reason = "disabled by configuration"
            elif override.get("files") is not None:
                reason = "files override: per-file coverage not qualified; original scope respected"
            else:
                continue
            gaps.append("%s not scanned/coverage unqualified: sensor '%s' %s"
                        % (coverage, sensor, reason))
    return gaps


def _derived_single_file_config(doc: dict):
    """(path, not_scanned) for one validated config document.

    The original recipes of the repository-wide sensors (deptry scans '.',
    jscpd its configured/'src' paths) have no proven single-file scope - a
    --file event must not read or judge untouched repository parts. The
    disable happens in the config the sensor stage reads, before anything is
    spawned: that is the real scan limitation, never a findings filter. The
    excluded smells come back as visible not_scanned entries; a config that
    already disables these sensors keeps using its own file unchanged.
    """
    sensors = doc.get("sensors") if isinstance(doc.get("sensors"), dict) else {}
    merged = dict(sensors)
    not_scanned = []
    changed = False
    for plugin in doc.get("plugins", []):
        for sensor, smell in sorted(REPOSITORY_SENSORS.get(plugin, {}).items()):
            override = sensors.get(sensor)
            if isinstance(override, dict) and override.get("disabled") is True:
                continue
            merged[sensor] = {**(override if isinstance(override, dict) else {}), "disabled": True}
            not_scanned.append(
                "%s not scanned in single-file mode: repository-wide sensor '%s' "
                "is disabled before spawning (no qualified single-file scope)"
                % (smell, sensor))
            changed = True
    if not changed:
        return None, []
    derived = dict(doc)
    derived["sensors"] = merged
    text = _write_toml(derived)
    if tomllib.loads(text) != derived:
        raise ConfigRejected("derived single-file config did not round-trip")
    holder = tempfile.mkdtemp(prefix="awc-habit-cfg-", dir=DERIVED_CONFIG_ROOT)
    path = Path(holder) / "config.toml"
    path.write_text(text, encoding="utf-8")
    path.chmod(0o600)
    return path, not_scanned


def _dispose_derived_config(path) -> None:
    if path is None:
        return
    try:
        path.unlink()
        path.parent.rmdir()
    except OSError:
        pass


def _check_interpreter_path(executable: Path, project: Path, qualified_path: str) -> None:
    """Validate script interpreter resolution without executing the script.

    Absolute console-script shebangs are part of the explicitly selected CLI
    installation. An env shebang resolves only against the bounded PATH, not
    the repository or ambient caller PATH; original helpers use sys.executable.
    """
    try:
        with executable.open("rb") as stream:
            head = stream.read(512).split(b"\n", 1)[0]
    except OSError as exc:
        raise ConfigRejected("cannot inspect interpreter: %s" % exc) from exc
    if not head.startswith(b"#!"):
        return
    words = head[2:].decode("utf-8", errors="strict").split()
    if not words:
        raise ConfigRejected("empty interpreter shebang")
    interpreter = Path(words[0])
    if interpreter.name == "env":
        if len(words) != 2 or words[1].startswith("-"):
            raise ConfigRejected("unqualified env interpreter recipe: %s" % executable)
        found = shutil.which(words[1], path=qualified_path)
        if found is None:
            raise ConfigRejected("qualified interpreter missing: %s" % words[1])
        interpreter = Path(found)
    if not interpreter.is_absolute() or _inside(interpreter.resolve(), project):
        raise ConfigRejected("repository-controlled interpreter refused: %s" % interpreter)


def _path_entries_inside_root(root: Path, effective_path: str) -> list:
    """PATH entries that would resolve tools inside the scanned project.

    The original lookup inherits this PATH as-is; the sensor stage cwd is
    the project root, so empty and relative entries resolve there. Symlinked
    entries resolving inside the root are repository-controlled too. Any such
    entry is refused before resolution is even considered (RV01)."""
    bad = []
    for entry in effective_path.split(os.pathsep):
        if not entry or not os.path.isabs(entry):
            bad.append(entry if entry else "<empty>")
            continue
        resolved = Path(entry).resolve()
        if resolved == root or root in resolved.parents:
            bad.append(entry)
    return bad


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _refuse_untrusted_tool_resolution(root: Path, doc: dict, extra_disabled,
                                      trusted_roots, effective_path: str) -> None:
    """Refuse detector resolutions that are not provably trusted (RV01).

    The original project_paths.tool_executable searches node_modules/.bin,
    .venv/bin and then the *inherited* PATH of the sensor stage. Before any
    spawn, each detector of every enabled, not-disabled sensor is resolved
    through exactly that search order (pure stat/access - repository code is
    never executed) and the resolved file must be outside the scanned project
    *and* inside an explicitly trusted root: by default the install
    directories of the qualified pipeline CLIs themselves, extended by
    ``trusted_tool_roots`` (e.g. a separately qualified external toolset).
    PATH entries that are empty, relative, or resolve inside the project are
    refused outright, and the standard bin shadows stay refused via the
    project-contains check. Nothing is trusted because tool data said so.
    """
    sensors = doc.get("sensors") if isinstance(doc.get("sensors"), dict) else {}

    def _enabled(sensor: str) -> bool:
        if sensor in extra_disabled:
            return False
        override = sensors.get(sensor)
        return not (isinstance(override, dict) and override.get("disabled") is True)

    bad_entries = _path_entries_inside_root(root, effective_path)
    if bad_entries:
        raise ConfigRejected(
            "PATH entry resolves inside the scanned project (empty/relative/repo-controlled "
            "search path refused): %s" % ", ".join(repr(e) for e in bad_entries))
    roots = [Path(r).resolve() for r in trusted_roots]
    search = os.pathsep.join(
        [str(root / relative) for relative in PROJECT_TOOL_DIRS] + [effective_path])
    for tool in sorted({
        tool
        for plugin in doc.get("plugins", [])
        for sensor, tool in PLUGIN_SENSOR_TOOLS.get(plugin, {}).items()
        if _enabled(sensor)
    }):
        for relative in PROJECT_TOOL_DIRS:
            candidate = root / relative / tool
            if candidate.is_symlink() or (candidate.exists() and os.access(candidate, os.X_OK)):
                raise ConfigRejected("project-local detector shadowing refused: %s" % candidate)
        # Preserve refusal of inherited repository executable aliases even
        # when explicit option bindings prepend a qualified installation.
        # Only metadata is inspected; no candidate program is executed.
        for entry in effective_path.split(os.pathsep):
            candidate = Path(entry) / tool
            if (candidate.is_symlink() or candidate.is_file()) and _inside(candidate.resolve(), root):
                raise ConfigRejected("inherited PATH detector alias resolves into repository (refused): %s" % candidate)
        found = shutil.which(tool, path=search)
        if found is None:
            continue  # a genuinely missing tool is the original missing-tool path
        resolved = Path(found).resolve()
        if _inside(resolved, root):
            raise ConfigRejected(
                "project-controlled detector resolution refused (no trust grant; the original "
                "runner would execute it ahead of any qualified install): %s" % found)
        if roots and not any(_inside(resolved, trusted) for trusted in roots):
            raise ConfigRejected(
                "detector %r resolves outside the qualified trusted tool roots: %s "
                "(trusted: %s)" % (tool, resolved, [str(r) for r in roots]))


def _valid_finding(item) -> bool:
    """Structural check of one finding per sensor-interface.spec.md.

    Purely isinstance-based so untrusted JSON can never raise through it.
    """
    if not isinstance(item, dict):
        return False
    smell = item.get("smell")
    if not isinstance(smell, str) or not smell:
        return False
    details = item.get("details", {})
    if details is not None and not isinstance(details, dict):
        return False
    language = item.get("language")
    if language is not None and not isinstance(language, str):
        return False
    issues = item.get("issues")
    if not isinstance(issues, list):
        return False
    for issue in issues:
        if not isinstance(issue, dict):
            return False
        issue_details = issue.get("details", {})
        if issue_details is not None and not isinstance(issue_details, dict):
            return False
        key = issue.get("key")
        if key is not None and not isinstance(key, str):
            return False
    return True


def _coverage_reasons(sensor_stderr: str) -> list[str]:
    """Qualified coverage doubt plus a conservative stance on unknown notices.

    Known runner notices (qualified list) mark missing coverage explicitly. Any
    *other* notice the original runner prints on stderr (prefix
    ``habit-sensors:``) cannot be classified as coverage-safe, so it counts as
    unchecked coverage rather than a complete run. Benign sensor stderr from
    other tools (no runner prefix) stays visible without blocking completion.
    """
    reasons = []
    lowered = sensor_stderr.lower()
    markers = [m for m in COVERAGE_MARKERS if m in lowered]
    if markers:
        reasons.append("sensor stderr reports missing coverage: %s" % "; ".join(markers))
    for line in sensor_stderr.splitlines():
        stripped = line.strip()
        if stripped.startswith(RUNNER_NOTICE_PREFIX):
            if not any(m in stripped.lower() for m in COVERAGE_MARKERS):
                reasons.append(
                    "unclassified runner notice on stderr (coverage unknown): %s" % stripped[:200]
                )
                break
    return reasons


def run_pipeline(
    project_root: Path,
    *,
    sensor_executable: str | Path,
    mapper_executable: str | Path,
    file: str,
    config_path: Path | None = None,
    trusted_config_root: Path | None = None,
    mapper_project_root: Path | None = None,
    env: dict[str, str] | None = None,
    trusted_tool_roots: list[str | Path] | None = None,
    sensor_timeout_s: float = SENSOR_TIMEOUT_S,
    mapper_timeout_s: float = MAPPER_TIMEOUT_S,
    max_output_bytes: int = MAX_OUTPUT_BYTES,
) -> PipelineResult:
    """Run the original pipeline for exactly one file of one project, safely.

    Scope is a single validated file (the original ``--file`` flag is
    single-value; repeating it silently measures only the last path, so this
    API refuses multi-file calls). There is deliberately no ``--all`` default.
    Both stages default to the validated project root as their working directory.
    mapper_project_root optionally selects a directory inside trusted_config_root
    for Markdown-guide lookup by the original mapper; sensor cwd never changes.
    Root identities are checked around the stages.

    ``trusted_config_root`` is an explicit trust boundary for a plugin-controlled
    runtime config outside the repository (so the global hook works in repos
    without their own ``.habit-hooks`` without mutating them): only a config
    resolved inside this validated directory, content-validated like any other,
    may be used; there is no default and nothing is trusted because tool output
    said so. Project plugin overrides under ``.habit-hooks/`` are refused
    regardless of where the config lives.

    Single-file hardening (qualified against the original 1.5.0 sources):
    repository-wide sensors without a proven single-file scope (deptry,
    jscpd) are disabled in a derived config handed to the stages - before
    anything is spawned - and the excluded smells are reported in
    ``not_scanned``. Every detector a sensor will invoke is resolved through
    the original search order before any spawn and must land outside the
    scanned project and inside explicitly trusted roots: the qualified
    pipeline CLIs' own install directories plus ``trusted_tool_roots``
    (``None`` = the CLI directories only). Inherited PATH entries that are
    empty, relative, or resolve into the project are refused outright.
    """
    root = Path(project_root).resolve()
    if not root.is_dir():
        raise ConfigRejected("project root is not a directory: %s" % root)
    _reject_project_plugin_overrides(root)
    _validate_guide_boundary(root, repository=True)
    mapper_root = root
    if mapper_project_root is not None:
        if trusted_config_root is None:
            raise ConfigRejected("mapper project root requires trusted_config_root")
        mapper_root = Path(mapper_project_root).resolve()
        trusted = Path(trusted_config_root).resolve()
        if not mapper_root.is_dir() or (mapper_root != trusted and trusted not in mapper_root.parents):
            raise ConfigRejected("mapper project root outside trusted scope")
        _reject_project_plugin_overrides(mapper_root)
        _validate_guide_boundary(mapper_root, repository=False)
    doc = load_config(root, config_path, trusted_config_root)
    target = safe_relative_file(root, file)
    sensor_exe = _validated_executable(sensor_executable, "sensor")
    mapper_exe = _validated_executable(mapper_executable, "mapper")
    rel_file = target.relative_to(root).as_posix()
    real_cfg = _resolve_config_path(root, config_path, trusted_config_root)

    derived_cfg, not_scanned = _derived_single_file_config(doc)
    file_sensor_gaps = _configured_file_sensor_gaps(doc)
    not_scanned.extend(file_sensor_gaps)
    extra_disabled = set()
    if derived_cfg is not None:
        extra_disabled = {
            sensor
            for plugin in doc.get("plugins", [])
            for sensor in REPOSITORY_SENSORS.get(plugin, {})
        }
    effective_cfg = derived_cfg if derived_cfg is not None else real_cfg

    try:
        sensor_argv = [str(sensor_exe), "--no-snooze", "--file", rel_file, "--config", str(effective_cfg)]
        mapper_argv = [str(mapper_exe), "--config", str(effective_cfg)]
        stage_env = dict(env) if env is not None else {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
        for injected in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONINSPECT",
                         "LD_PRELOAD", "LD_LIBRARY_PATH", "NODE_OPTIONS", "NODE_PATH"):
            # The sensor stage passes its environment on to every helper and
            # detector it spawns; interpreter path/startup injection has no
            # qualified use there, so only explicitly passed values survive.
            stage_env.pop(injected, None)
        # Every detector the sensors will invoke must resolve outside the
        # scanned project and inside explicitly trusted roots: the qualified
        # pipeline CLIs own install directories plus any caller-granted
        # trusted_tool_roots (RV01; inherited PATH, relative/empty entries
        # and symlink aliases are covered by the same proof).
        trusted_roots = {sensor_exe.parent.resolve(), mapper_exe.parent.resolve()}
        if trusted_tool_roots is not None and not isinstance(trusted_tool_roots, (list, tuple)):
            raise ConfigRejected("trusted_tool_roots must be explicit installation directories")
        for supplied in trusted_tool_roots or []:
            candidate = Path(supplied)
            if not candidate.is_absolute() or not candidate.is_dir():
                raise ConfigRejected("trusted tool root must be an existing absolute directory")
            canonical = candidate.resolve()
            if _inside(canonical, root) or canonical == Path("/"):
                raise ConfigRejected("repository/root-wide tool trust grant refused")
            trusted_roots.add(canonical)
        _refuse_untrusted_tool_resolution(
            root, doc, extra_disabled, sorted(trusted_roots), stage_env.get("PATH", ""))
        # Preserve qualified lookup order, but do not forward arbitrary PATH
        # directories to original helpers or shebang /usr/bin/env resolution.
        original_path = stage_env.get("PATH", "")
        bound_entries = [str(Path(entry).resolve())
                         for entry in original_path.split(os.pathsep)
                         if any(_inside(Path(entry).resolve(), trusted)
                                for trusted in trusted_roots)]
        stage_env["PATH"] = os.pathsep.join(dict.fromkeys(
            bound_entries + ["/usr/bin", "/bin"]))
        # Validate the actual bounded PATH too: adding OS interpreter bins
        # must never silently add an unqualified detector installation.
        _refuse_untrusted_tool_resolution(
            root, doc, extra_disabled, sorted(trusted_roots), stage_env["PATH"])
        stage_env["PYTHONDONTWRITEBYTECODE"] = "1"
        _check_interpreter_path(sensor_exe, root, stage_env["PATH"])
        _check_interpreter_path(mapper_exe, root, stage_env["PATH"])
        for tool in PLUGIN_SENSOR_TOOLS.get("python", {}).values():
            selected = shutil.which(tool, path=stage_env["PATH"])
            if selected:
                _check_interpreter_path(Path(selected), root, stage_env["PATH"])

        root_before = _root_identity(root)
        sensor, raw_out = _run_stage(sensor_argv, None, sensor_timeout_s, root, stage_env, max_output_bytes)
        if _root_identity(root) != root_before:
            raise ConfigRejected("project root changed during the sensor stage")

        reasons: list[str] = []
        findings: list | None = None

        if sensor.status != "ok":
            reasons.append("sensor stage status: %s" % sensor.status)
        elif sensor.exit_code != 0:
            # Qualified behaviour: habit-sensors exits 0 even with findings; any
            # non-zero exit means the run did not complete.
            reasons.append("sensor exit code %r means an incomplete run" % sensor.exit_code)

        reasons.extend(_coverage_reasons(sensor.stderr))

        if not sensor.stdout.strip():
            reasons.append("sensor produced no findings array (empty stdout)")
        else:
            try:
                parsed = json.loads(sensor.stdout)
            except json.JSONDecodeError:
                reasons.append("sensor stdout is not valid JSON")
                parsed = None
            if parsed is not None:
                if not isinstance(parsed, list):
                    reasons.append("sensor stdout is not a JSON array")
                elif not all(_valid_finding(item) for item in parsed):
                    reasons.append("sensor stdout contains malformed findings")
                else:
                    findings = parsed

        if findings is not None and any(item.get("smell") == INCOMPLETE_RUN_SMELL for item in findings):
            reasons.append("pipeline reported an incomplete run")

        if findings is None or reasons:
            # Never feed broken input to the mapper; preserve the evidence instead.
            mapper = StageOutcome(
                "skipped", None, "", "mapper not run: %s" % ("; ".join(reasons) or "no valid findings"),
                tuple(mapper_argv),
            )
            return PipelineResult(sensor, mapper, findings, False, reasons, not_scanned)

        if _root_identity(root) != root_before:
            raise ConfigRejected("project root changed before the mapper stage")
        mapper_identity = _root_identity(mapper_root)
        mapper, _ = _run_stage(mapper_argv, raw_out, mapper_timeout_s, mapper_root, stage_env, max_output_bytes)
        if _root_identity(mapper_root) != mapper_identity:
            raise ConfigRejected("mapper root changed during the mapper stage")
        if _root_identity(root) != root_before:
            raise ConfigRejected("project root changed during the mapper stage")

        if mapper.status != "ok":
            reasons.append("mapper stage status: %s" % mapper.status)
        elif mapper.exit_code not in (0, 1):
            reasons.append("mapper exit code %r is not a verdict" % mapper.exit_code)
        elif not mapper.stdout.strip():
            reasons.append("mapper produced no coaching output")

        # Do not suppress original mapper coaching because configuration
        # narrowed coverage; append these gaps only after mapping valid findings.
        reasons.extend(file_sensor_gaps)
        complete = not reasons
        return PipelineResult(sensor, mapper, findings, complete, reasons, not_scanned)
    finally:
        _dispose_derived_config(derived_cfg)

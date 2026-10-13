# Qualified, pinned toolchain (evidence 2026-10-13)

Actual package and runtime evidence collected in the isolated toolchain
`/tmp/opencode/agentic-workflow-core-ci` (first-time isolated setup is plan-authorised;
nothing was installed into a user profile).

## Core pipeline (PyPI, python >=3.11)

| Package | Pinned version | Evidence |
|---|---|---|
| habit-hooks | 1.5.0 | `pip install habit-hooks==1.5.0`; `habit-sensors --version` → "habit-hooks v1.5.0"; extras available: all, java, php, python, ruby, typescript (there is **no** `generic` extra — the generic plugin arrives as a plain dependency) |
| habit-hooks-generic | 1.5.0 | resolved and installed with core |
| habit-hooks-python | 1.5.0 | resolved via the `python` extra |
| Jinja2 / MarkupSafe / pathspec / attrs | 3.1.6 / 3.0.4 / 1.1.1 / 26.1.0 | `pip freeze` of the same install |
| Python runtime | 3.13 (isolated venv) | pipeline runs and exits per spec (0 clean, 1 enforced, 2 incomplete) |

## Qualified detectors (file hook: ruff; explicit repository scans: optional deptry/jscpd)

| Detector | Pinned version | Evidence |
|---|---|---|
| ruff | 0.14.5 | installed; `ruff --version`; emits `too-many-parameters` (PLR0913) through the python plugin |
| deptry | 0.23.1 | installed qualification; disabled/not_scanned in automatic file mode, optional for separately authorised repository scans |
| jscpd | 5.4.1 (npm) | installed under the isolated node prefix; **jscpd 0.5.x–0.6.x is broken on current node** (codemirror `ERR_PACKAGE_PATH_NOT_EXPORTED`) — do not pin those |
| Node runtime | v22.23.3 | isolated `…/node/bin/node` |

Historical raw-tool qualification (isolated project; not the automatic scoped hook):
`habit-sensors --all | habit-mapper` coaches `too-many-parameters` and exits 1;
a missing detector yields a stderr notice plus the reserved `incomplete-run`
finding and exit 1; empty stdin to `habit-mapper` exits 2; `[]` with exit 0
prints the clean verdict. A jscpd run without a `src/` directory fails its
sensor (fallback config expects `src`) — visible, not silent.

Additional qualified behaviour (attempt-02, isolated runs in
`/tmp/opencode/habit-qualify2`):

- `habit-sensors --file` exits **0** both with findings and when clean; the
  mapper carries the verdict (exit 1). Any non-zero sensor exit therefore
  means an incomplete run.
- Repeating `--file a --file b` measures **only `b`** — single-value flag.
  The adapter accepts exactly one file per call.
- A scope matching nothing (or no `[files]` configured, or a detected language
  whose plugin is not enabled) prints a stderr notice ("nothing scanned",
  "nothing matched", "no [files] are configured", "not enabled") while stdout
  still shows `[]` with exit 0 — the adapter treats those markers as missing
  coverage, never as a complete clean run.
- End-to-end through this adapter with the real CLIs: findings file →
  `complete=True`, mapper exit 1; clean file → `complete=True`, `clean=True`.

Qualified original semantics for the global hook (attempt-03, isolated runs
in `/tmp/opencode/habit-qualify3` and `-qualify4`):

- `--config` accepts a config outside the project. The runner then still
  resolves project-local plugin overrides from `.habit-hooks/` in its working
  directory (a stray `sensors/*.toml` alone is inert until a plugin
  `config.toml` lists it, but a vendored plugin config executes commands) —
  the adapter therefore refuses any `.habit-hooks/<plugin>/` override,
  including via symlink, before spawning.
- Unconfigured project + external trusted config: `--config <external>` with
  `--file <rel>` measured the file correctly (exit 0, findings on stdout).
- The ruff detector writes a `.ruff_cache/` directory into the project cwd
  unless `RUFF_CACHE_DIR` points elsewhere. The adapter passes `env` through
  unchanged; T02/T03 must set `RUFF_CACHE_DIR` (and similar detector caches)
  to a runtime temp directory to keep the "no repository mutation" contract.
  Verified: with `RUFF_CACHE_DIR` redirected, the project directory stayed
  untouched.

## OpenCode V2 SDK contract (T02, evidence 2026-10-13)

| Item | Version / source | Evidence |
|---|---|---|
| OpenCode (host) | v2.0.25 | `opencode --version` on the host |
| Plugin hook API | Exact npm @opencode/plugin/schema/client 2.0.25 | Primary evidence: published dist/promise/tool.d.ts, schema dist/tool.d.ts and client dist/promise/generated/types.d.ts. before/after both carry tool, sessionID, agent, messageID, id (CallID), input. Completed result is an OBJECT with output?, content?: string or text/file Content[], metadata?. Error events have error instead of result. SessionGetInput={sessionID}; SessionInfo.location.directory is the event-session checkout, not the plugin instance location. No V1 ToolResult inference. |

Registry tarballs were downloaded exclusively under /tmp/opencode/opencode-plugin-sdk,
and each SHA512 was verified against registry dist.integrity before extraction:

- plugin 2.0.25: sha512-CdGaTps7W1QlMsgisPAQMVLV8g5eedV02I21blf6jf73VKoBivUIrKnXyXsjl68ePDsAZG6DX7oXieC8tdPWKw==
- schema 2.0.25: sha512-z064XvBBmdDQLCUYjBinGeCqdbDK3DZ49raFFrzE95eIth3qBkU2Q872VLSqCCLLgDcwKZuRNrwSFNtcc4xvcw==
- client 2.0.25: sha512-ur/LTb/1ANOskbGM3ZMDurpK8q0BIQuWys/MD499/Eodv6PzybM9hJY4cKJMyD2lNqu9v3349IsV1mj7gCdt7w==

For CK02, isolated SDK/typecheck prerequisites exist under
/tmp/opencode/opencode-plugin-sdk/runtime: @opencode/plugin 2.0.25,
TypeScript 5.9.3, @types/node 22.19.1 (npm --ignore-scripts, no user/repo installs).
CK02 asserts exact plugin/schema/client versions and typechecks the actual shim
in strict NodeNext mode; Node 22.23.3 executes it via native type stripping.

Official V2 sources: https://opencode.ai/v2/docs/build/plugins and /v2/docs/tools.
Context7 corroborates hook registration but had mixed V1/V2 ToolResult examples;
the exact npm package types above are authoritative, not the mixed snippets.

Mapper guide qualification: installed habit-hooks 1.5.0 mapper.py lines 52–57,
113–118 and resolve.py lines 141–156 select guides relative to mapper cwd, NOT
the external config's directory. The hook therefore installs only the six
packaged Markdown guides (six after the manual RV06 line-count coaching check) under its checked runtime and uses the optional
mapper_project_root (must be inside trusted_config_root). Default pipeline cwd
behaviour remains unchanged and is checked by CK01. CK02 runs the original
mapper with a stub sensor and observes Core guidance; T03/CK04 additionally
observes the packed plugin in the real host and real sensor/mapper pipeline,
including pre-spawn exclusion of jscpd/deptry and project inventory checks.

- Native tool args (V2 docs): edit{path, oldString, newString, replaceAll}, write{path, content}.
- Gortex daemon v0.64.4 actual mutation receipts: `{status:"created"|"applied", path:"<repo-prefixed>", new_sha, bytes_written?, replacements?, mutation_receipt, reindexed}`; dry run `{status:"would_apply", dry_run:true, ...}`. Fixtures pinned in CK02. Direct structured output and JSON text-content variants are tested; arbitrary nested wrappers are explicitly not_scanned.

## Single-file safety qualifications (review-repair round 1, isolated runs in
/tmp/opencode/g03-p02-r01-t01-fix; real habit-sensors/habit-mapper 1.5.0)

- **Detector resolution order (RV01):** original
  `habit_hooks/project_paths.py:tool_search_path/tool_executable` puts
  `node_modules/.bin` and `.venv/bin` ahead of any qualified PATH, for ruff,
  deptry and jscpd alike. Reproduced with a marker detector: it executed and
  the run reported clean. The adapter therefore refuses, before any spawn and
  without executing repository code, any project-local shadow (regular
  executable or symlink) of a detector an enabled, not-disabled sensor will
  invoke; the original detectors themselves are unchanged, and qualified
  global tool paths keep working when no shadow exists.
- **Repository-wide sensors have no single-file scope (RV02):** the original
  generic `jscpd` recipe reads its configured/`src` paths and python `deptry`
  scans `.` regardless of `--file`; reproduced with duplicated
  `src/unrelated_*.py` files that produced `duplicated-code` findings for a
  `target.py` event. Single-file runs now hand both stages a derived config
  (validated original + `[sensors.jscpd/deptry] disabled = true`) — a real
  pre-spawn scan limitation, not a findings filter — and report the excluded
  smells `duplicated-code`/`unused-dependency` in the new
  `PipelineResult.not_scanned`. File-scoped original sensors (ruff via
  `${files}`, line-count) keep running unchanged.
- **Separated sensor process groups (RV03):** original
  `habit_hooks/sensors/spawn.py` starts every helper/detector with its own
  session (setsid); a top-level `killpg` never reaches them. Reproduced with
  a controlled sleeping detector: `run_pipeline(sensor_timeout_s=2)` returned
  `timed_out` while the detector (own PGID) stayed alive. The adapter now
  proves membership per pid from /proc (parent chains, start times, a stage
  subreaper for adopted orphans) and kills/reaps the whole proven tree on
  timeout, output limit and bridge SIGTERM (`kill_active`); with the real
  sleeper plus child, no own process remained after cleanup.
- Stage environments drop `PYTHONPATH`/`PYTHONHOME` before spawning: the
  sensor stage forwards its environment to every helper/detector, and
  interpreter path injection has no qualified use there.

## Review round-two qualification (2026-10-13)

Round-one ownership/trust claims above are historical and were insufficient:
project/tools/ruff on inherited PATH executed, and a new unrelated direct child
was killed/reaped by the start-window heuristic. Both exact reviewer result.json
files were freshly read before repairing this boundary. Current implementation
binds actual detector resolution to CLI install directories or explicit
trusted_tool_roots, bounds subprocess PATH and validates interpreter resolution.
Stage orphan ownership requires an exact per-stage non-secret inherited token,
not a common parent/start window; PID identity is revalidated by start time.

Fresh CK01: 84 tests, including real habit-sensors 1.5.0 helper/detector tests
for parent-exit race, byte overflow, timeout plus unrelated child, and SIGTERM
shutdown. Supplemental real-pipeline marker reproduction: absolute project/tools,
relative tools, empty PATH entry and symlink alias all refused, no marker;
qualified global ruff works, explicitly trusted external sleeper works and its
whole detached tree disappears while unrelated owners retain exit statuses.
Logs: /tmp/opencode/t01-round2-CK01.log and t01-round2-repro.log.
Current T03 SDK-host tests explicitly bind absolute original CI sensor/mapper
paths and separate controlled detector directories via the documented launch
JSON/API argument. Absolute project/tools, relative/empty PATH entries and
external symlink aliases never execute markers. Original helper timeout1.5s,
overflow, parent-exit race and bridge TERM have actual PID/PGID/starttime and
real delegated signal/reap tapes. Ordinary children created before/during/after
stage start keep living and retain owner exit statuses; concurrent original
pipelines keep disjoint ownership. Old 76 cases remain manifest-checked.
Pins of original core, Python/generic plugins and detectors are unchanged.
Existing cross-task fixtures without a separate detector trust grant require
T02/T03 adaptation and fresh packaging/host verification, not weakened guards.

## Manual RV06 qualification (same 1.5.0 pins)

Original loader/model/execution suppress disabled sensors and narrow each
sensor with its files override without emitting a missing-coverage notice
for every excluded sensor. Fresh review reproduced Ruff disabled/narrowed as
false-clean on an eight-parameter target, both in the adapter and packed host.
Current adapter reports disabled Ruff/line-count rule coverage explicitly.
Any non-None files override is conservatively coverage-unqualified, without
inventing a matcher or changing the requested original scope. The mapper still
handles valid findings before these gaps prevent complete/clean claims.

CK01 now has 88 tests; four new real-original cases cover disabled/narrowed
Ruff, disabled/narrowed line-count and enabled Core-coaching control, including
a matching-pattern conservative control. CK02 remains 103 tests OK. Evidence:
/tmp/opencode/t01-rv06-CK01.log, t01-rv06-CK02.log and t01-rv06-repro.log.
Fresh packed SDK-host/next-provider evidence requires T03 to rebuild/rebind
the package after this source change; no such host claim comes from CK01.

## Language coverage in 0.1.0

- Automatic qualified file-scoped subset: **python** (ruff) + **generic**
  (file-scoped parts such as line-count and warning-comment).
- Excluded in file mode: duplicated-code/jscpd and unused-dependency/deptry.
  Their qualification pins are for optional, separately authorised repository
  scans; no repository-wide coverage is claimed by a file event.
- Explicitly not qualified/covered in this version: java, php, ruby, typescript
  plugins (they exist as extras but were neither installed nor exercised);
  unknown smells surface via the mapper's `uncoached` policy instead of being
  silently dropped.

## Review-round qualified narrow scope and guide trust

The automatic single-file pipeline runs the original file-scoped sensors,
including ruff. Original jscpd and deptry recipes discover repository paths;
they are disabled before dispatch, not post-filtered. CK04 records the actual
original CLI entry point/config/helper spawns with adjacent unrelated duplicate
files, a manifest and external jscpd path: no jscpd/deptry helper is spawned.
Coverage gaps remain visible to the local provider. Their versions above are
qualification pins for optional explicit repository scans, not automatic-hook
prerequisites; CK04 also proves operation with both absent from PATH.

Original habit_hooks/resolve.py first() loads guide files under mapper cwd,
and the original renderer uses Jinja, not a sandbox. The adapter now refuses
repository guide roots and trusted-root symlink escapes before spawning. The
hook uses only reviewed packaged guides in its controlled mapper root; .md
alone grants no execution trust. CK04 hostile Jinja sentinel/override/symlink
cases cause no marker execution; public adapter guards are tested separately.

Original setsid helper topology is tested with explicitly TRUSTED temporary
detectors outside the repo, not disabled production guards: actual timeout,
output overflow, leader-exit race and SDK bridge SIGTERM leave zero recorded
own processes/zombies. PID/PGID/starttime and preserved pre-stage control
process evidence are in CK04 review-repros/process-evidence.json.

## Explicit manual RV06 effective-coverage qualification

Original generic/sensors/line-count.py emits oversized-file above 200 lines;
Original sensor execution narrows its existing scope for per-sensor files.
The CLI provides no measured-file receipt for an overridden sensor. Disabled
ruff and line-count are named unmeasured; non-None files overrides remain
conservatively coverage-unqualified without implementing a second matcher.
Preferences and original severity are not overwritten. Actual valid findings
and original-mapper coaching still render alongside gaps, including partial
line-count suggest findings with mapper exit 0. CK04 observes original bridge
machine not_scanned/complete/clean, SDK content and next provider messages in
two projects. Enabled ruff and oversized-file controls still detect; all prior
90 security/options/lifetime cases remain meaningful. This manual authority
is separate from the already exhausted two automatic review repair rounds.

## Consumers

- Adapter: `adapter/habit_feedback_pipeline.py` spawns exactly these two
  original CLIs; it pins nothing itself and installs nothing.
- T03 CK04 uses the existing isolated prerequisites and freshly checks original
  package/CLI versions, Node 22.23.3, host 2.0.25, plugin/schema/client SDK target
  2.0.25 and plugin tarball SHA512 against the registry metadata. Explicit setup
  offline-installs only the built 0.1.0 plugin tarball; normal hooks/checks do not
  download or install prerequisites. Scoped original sensors run with redirected
  HOME/TMPDIR/RUFF_CACHE_DIR, with per-toolcall project inventory equality;
  jscpd/deptry are not dispatched and need not exist on PATH.
- Original Python ruff_sensor.py selects C901, PLR0913, PLR0915, F841, F401,
  BLE001; it does NOT select a deep-nesting rule. CK04 therefore uses actual
  high-complexity detection and modularizes while preserving all twelve total
  branches. No deep-nesting detection coverage is inferred from a packaged guide.
- Actual execute Tool.Result.output envelope has output (JSON string), toolCalls
  (array), files (array); the exact shape is qualified by a separate real observer
  plugin and replay tests. Other nested forms remain not_scanned. Contract details
  and the explicit replay/end-to-end distinction are in sdk-contract.md.

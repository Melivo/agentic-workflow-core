# opencode-habit-feedback (canonical source, 0.1.0)

Canonical source under .apm/. No second manually maintained package source.
CK03 builds and inspects the tarball; CK04 exercises its offline npm-installed
bytes in the actual isolated OpenCode 2.0.25 host. No publish or global/user
activation has occurred.

## Responsibilities

- Original habit-sensors and habit-mapper own detection, smell routing and
  guide rendering; the plugin contains no replacement detector or template engine.
- adapter/habit_feedback_pipeline.py owns bounded argument-vector processes,
  exactly-one-file scope, config/path validation, separate stage status/stderr,
  and full process-tree kill/reap/pipe cleanup. It installs nothing, fixes
  nothing and uses --no-snooze. Executable project overrides are refused,
  including project-local detector shadows (node_modules/.bin, .venv/bin,
  symlinks included) which the original tool search would otherwise execute
  ahead of any qualified install. Repository-wide sensors without a proven
  single-file scope (deptry, jscpd) are disabled before spawning via a derived
  config; the excluded smells are reported in PipelineResult.not_scanned
  instead of being silently filtered out of findings.
- hook/habit_feedback_hook.py owns JSON event classification, checked runtime
  configuration, per-session/checkout state and bounded feedback. Python stdlib only.
- plugin/index.ts owns the typed OpenCode-V2 hook and process transport. It is
  an ESM module using fileURLToPath(import.meta.url). It imports SDK types only,
  and its exported object satisfies Plugin.Plugin from the actual 2.0.25 SDK.

## Actual SDK contract

Pinned registry sources and integrity receipts are documented in VERSIONS.md.
Both execute.before and execute.after expose tool, sessionID, agent, messageID,
id (Tool.CallID) and input. Completed after events have result; error after events
have error. The after hook therefore uses its own input directly, not guessed
callID fields or order-dependent before/after pairing. The before hook is a no-op.

Tool.Result is an object with output?, content?: string | Content[], metadata?.
Content parts are text or file parts. Feedback is appended to content (model-visible)
while original content parts, metadata and structured output stay untouched.
Error events are untouched; bridge failures do not change an error into success.

Event scope comes from ctx.session.get({sessionID}).location.directory, NOT
ctx.location.directory (plugin instance location) or a process.cwd fallback.
Absent/invalid session locations are visibly not scanned.

Supported mutations:

- Native edit/write: documented input.path, successful completed event.
- Gortex mutation receipts in structured output or JSON text content: explicit
  path and the tested created/applied/written receipt, not dry-run would_apply.
  A single receipt or top-level array is supported, including the exact live
  2.0.25 execute output envelope {output: JSON-text, toolCalls: array, files: array}.
  No arbitrary nested-wrapper search. Unknown forms are visibly not_scanned;
  mixed batches retain a partial-coverage warning. See sdk-contract.md.
- No parsing of shell commands or Code Mode program text to infer paths.
  No repository-wide fallback scan.
- Unknown completed tool forms (bash with opaque commands, unknown patch or
  custom MCP tools) have no proven read-only property: they are reported as a
  visible not_scanned coverage gap naming the tool, without any path guessing.
  Only the documented stock read-only tools (read, glob, grep, ls, webfetch,
  websearch) and error events stay unobtrusively non-mutating; Gortex dry runs
  trigger no scan-warning flood.
- Advisory (non-blocking) mapper verdicts - the original severity decision,
  e.g. severity='suggest' with mapper exit 0 - are never presented as "clean":
  the entry is marked "no enforced findings (advisory coaching below)" and the
  full mapper coaching including the targeted Core guide stays model-visible.
  "No enforced findings" is explicitly not "no findings"; the original
  severity decision is respected and never turned into an enforced change.
  Single-file coverage gaps (duplicated-code, unused-dependency) ride along in
  the machine-readable scanned entry (advisory, not_scanned) and in the
  feedback text; truncated feedback/verdicts are named as truncated.

## Runtime trust and safety

Default state root: /tmp/opencode/habit-feedback-<uid>. Explicit trusted test
roots below /tmp/opencode may be set through HABIT_FEEDBACK_STATE_ROOT; roots
inside the scanned project are refused. Root/ancestor symlinks,
foreign ownership, writable roots, symlinked scope/state/lock/runtime paths and
hardlinked state files are refused. Root/checkout/session keys are kept separate.
Linux flock serialises each key with a five-second lock wait. File hashes suppress
unchanged completed scans; incomplete scans are retryable, not cached clean.
At most four files per event are scanned; the remainder is explicitly not_scanned.
Receipt batches over 64 entries and files over 10 MiB are refused visibly; a file
changing during its scan prevents a clean verdict and is not cached as complete.
The partial-coverage warning precedes potentially truncated coaching output.

Runtime config is generated under the checked root, mode 0600, content-validated
through the adapter; no .habit-hooks config or other project file is written.
HOME, TMPDIR and RUFF_CACHE_DIR for child tools point under runtime state.
Project-owned plugin/sensor/transformer executable overrides remain refused.
Six packaged Markdown Core guides are copied to the trusted mapper runtime's
.habit-hooks/generic/guides allowlist. The original mapper discovers and renders
these; no guide-routing code is reimplemented. Mapper cwd is deliberately this
trusted runtime, while sensors retain the actual project cwd. Markdown is NOT a
sandbox: the original mapper uses executable Jinja templates. Repository-owned
guide directories are refused before spawning even for the public adapter API;
trusted mapper guide directories/files may not be symlinks, hardlink aliases or
escape their root.
Guide overrides must be a single filename. Trust comes from the controlled
reviewed runtime/template source, never from the .md suffix or repository data.

The process bridge bounds UTF-8 input (8 MiB), stdout (1 MiB), stderr tail (64 KiB),
execution (120 seconds) and appended feedback (4000 characters). Failure, nonzero
exit, invalid JSON, output overrun, missing module/tool and timeout are visible.
Timeout sends SIGTERM to the bridge group; Python proves and ends the whole
stage process tree — including the separated setsid groups the original
spawn.py creates for helpers/detectors — via /proc parent chains, start times
and a stage subreaper, then reaps adopted orphans; SIGKILL follows after two
seconds if necessary.
The JS hook awaits close before reporting. SIGKILL/external catastrophic host
termination is not a guaranteed cooperative-cleanup boundary.

## Adapter API (T01-compatible defaults)

run_pipeline(project_root, *, sensor_executable, mapper_executable, file,
config_path=None, trusted_config_root=None, mapper_project_root=None, env=None,
trusted_tool_roots=None,
sensor_timeout_s=30, mapper_timeout_s=30, max_output_bytes=1000000)
returns PipelineResult with sensor, mapper, findings, complete, reasons,
not_scanned and clean. not_scanned lists smells the single-file run provably
did not cover (repository-wide sensors disabled before spawning: currently
duplicated-code and unused-dependency whenever the config enables them);
complete/clean never claim that excluded coverage.

mapper_project_root is optional and must resolve inside trusted_config_root;
without it both stages retain the original project cwd. The hook sets it to the
checked mapper runtime so guide overrides work without repository writes.
Existing callers remain valid; unchanged CK01 tests check the default contract.

complete means an observed finished scan, not an empty findings array/exit code
alone. Coverage notices, missing tools and incomplete runs are never false-clean.
clean is a mapper verdict within qualified coverage, not universal language coverage.

## Round-two executable and process ownership boundary

Inherited PATH is not a trust grant. Before spawning, the adapter models the
original detector lookup order (project bins then PATH), refuses empty/relative
or repository-resolving entries and resolves symlinks without executing code.
Actual detector files must be inside the explicitly selected CLI install
directories or additional caller-supplied trusted_tool_roots. The latter are
installation grants, never repository config, tool output or event fields.
Separately qualified detector environments must provide that API argument.

Persistent plugin options (SDK 2.0.25 ctx.options): the global user/harness
plugin registration may supply sensor, mapper, python, trustedToolRoots and
stateRoot. sensor/mapper/python/stateRoot are absolute path strings;
trustedToolRoots is an array of existing absolute qualified installation
directories (not a JSON string in options). Example options object:

    {"sensor":"/qualified/install/bin/habit-sensors",
     "mapper":"/qualified/install/bin/habit-mapper",
     "python":"/qualified/install/bin/python3",
     "trustedToolRoots":["/qualified/separate-detectors/bin"],
     "stateRoot":"/tmp/opencode/habit-feedback-owned"}

Known options override their corresponding HABIT_FEEDBACK_* launch variables;
omitted options retain the explicit environment fallback. Invalid present
options never silently fall back. Missing CLI bindings stay visibly not_scanned.
The default bridge interpreter is /usr/bin/python3 (no PATH-based interpreter
selection); explicit Python aliases resolving into the event repository are
refused before spawn. Values are never echoed in option-validation errors.
Each plugin instance snapshots its own options/fallbacks; only its child env
receives them, never process.env or other plugin instances. Qualified CLI
installation directories and explicit detector roots are added to that child's
lookup PATH so no shell/login environment change is needed; inherited lookup
entries remain present for the adapter's unsafe-PATH guards. Event payload,
metadata and repository strings cannot supply options or grants. Root/owner/
symlink/state guards are unchanged. Configuration provenance is user/harness
controlled global registration; ctx.options by itself is NOT a provenance
attestation or permission to accept repository-provided configuration. No
normal-run install/download/init, global config write or registration occurs.

Hook launch policy (T02 round two): HABIT_FEEDBACK_SENSOR and
HABIT_FEEDBACK_MAPPER must name explicitly qualified absolute CLI files outside
all event repositories (or equivalent explicit process_event sensor/mapper
arguments). No PATH-only CLI discovery. The CLI installation directories are
trusted by that explicit choice, not by tool/event data. Additional separately
qualified detector directories are provided ONLY by the installer/host launch
configuration as HABIT_FEEDBACK_TRUSTED_TOOL_ROOTS, a JSON array of existing
absolute installation directories, e.g. ["/trusted/installation/bin"]. The TS
bridge forwards this launch binding; Python passes it as trusted_tool_roots to
the original adapter. Direct process_event callers may supply the optional
trusted_tool_roots keyword. Tool input/output/metadata, session locations,
project config and arbitrary PATH entries cannot grant trust. Repository/root
wide grants and repository-resolved CLI aliases are refused visibly; no
repository executable is run to check a version. PATH remains lookup evidence,
not authorization; unsafe relative/empty/repository aliases are rejected, not
silently sanitized. Normal hook runs never install or qualify tools.

T03 isolated host policy: explicitly set SENSOR and MAPPER to the prepared
qualified original CLI absolute paths. If a controlled detector resides in a
separate owned fixture installation, bind ONLY that installation directory in
HABIT_FEEDBACK_TRUSTED_TOOL_ROOTS (JSON); never the fixture project, /tmp or a
broad workspace. Existing CI installation is
/tmp/opencode/agentic-workflow-core-ci/venv/bin; process-local stub tests bind
this known installation explicitly without mutating global process environment.
Global runtime setup must analogously bind its own verified installed paths;
this document does not authorize global setup.
The subprocess PATH retains only those qualified directories plus OS
/usr/bin and /bin for interpreter resolution; environment library/startup
injection variables are removed and script interpreter paths checked.

Stage cleanup never treats all newly started direct children as its own. A
unique non-secret AWC_HABIT_STAGE environment token is installed only in that
stage. Parent ancestry proves live descendants; a targeted exact token check
on direct-child orphan candidates proves adoption ownership. Recorded start
times reject PID reuse; only proven identities are signalled/reaped. Concurrent
stages and ordinary independent children retain their processes and exit
statuses. Real-original tests cover detached groups, parent exit, overflow and
SIGTERM at the adapter shutdown boundary. Actual SDK-host revalidation remains
T02/T03 work, not a claim of this adapter-only check.

## Effective per-file coverage (manual RV06 repair)

A permitted disabled override for ruff or line-count is respected and reported
in PipelineResult.not_scanned with its affected rule coverage. A non-None
files override is conservatively reported as per-file coverage unqualified: no
second glob matcher is used, and the original recipe/scope remains unchanged.
This applies even to a pattern that may include the target; the CLI provides
no per-sensor measured-file receipt to qualify that claim at this boundary.

Such gaps make complete=false and clean=false, without dropping valid
findings or preventing the original mapper from coaching the measured subset.
Hook metadata and tool feedback retain the gaps; useful original coaching is
still shown when a configured partial run has findings. A mapper exit 0 alone
cannot turn an unmeasured Ruff/line-count rule into a clean claim. Existing
repository-sensor exclusions remain separately listed. No override is forced
on, no repository-wide fallback scan is introduced.

## Verification and limits

CK02 executes the real TypeScript shim through isolated Node 22.23.3 type stripping,
strictly typechecks it against @opencode/plugin/schema/client 2.0.25, and exercises
stdlib bridge logic with explicitly marked STUB sensor/mapper doubles. An isolated
original-mapper check proves Core-guide resolution without project writes.
Two checkout sessions under one plugin instance, result-content preservation,
parallelism, state conflicts, malformed/oversized payloads and timeout sensor
reaping are tested. This is not the full OpenCode-host/real-sensor CK04 evidence.

Qualified tools/languages remain those in VERSIONS.md: Python + generic; other
language plugins are unqualified. CK04 observes actual packed-host calls and
checks the complete project file/directory inventory around every toolcall:
only the documented native edit/write target may change, no detector cache or
configuration writes. In single-file mode the repository-wide jscpd/deptry
sensors are disabled before spawning and reported as not_scanned (see
VERSIONS.md); no clean claim is derived from that excluded coverage. No automatic install/download, fix/snooze, prompt/agent/
task dispatch, provider switch, release or global activation.

The scoped original pipeline excludes the repository-wide jscpd and deptry
sensors. Their pinned tools are optional for separately, explicitly authorised
repository scans, never a default file-hook prerequisite. CK04 also runs the
original file-scoped pipeline with neither executable on PATH. It reports
duplicated-code and unused-dependency as not_scanned rather than claiming
general duplication/dependency coverage.

## Reproducible packaging and isolated verification

Run from the producer repository, with the prepared AWC_CI_WORKSPACE toolchain:

    python3 -B scripts/check_habit_feedback.py package
    python3 -B scripts/check_habit_feedback.py setup
    python3 -B scripts/check_habit_feedback.py integration
    python3 -B -m unittest discover -s tests -p "test_habit_feedback*.py" -v

setup is an explicit, separate offline scratch-install action under /tmp/opencode.
Missing/stale setup blocks integration; checks never silently install prerequisites.
package makes two byte-identical npm pack archives in fresh producers. It compiles
canonical TS with pinned TypeScript 5.9.3 into root/plugin JS exports, checks every
archive byte against an exact source allowlist and embeds inventory.json hashes.
Source main/exports describe the generated package, not a direct source-directory
install. No build/install/postinstall/downloader scripts are shipped. SDK peer
@opencode/plugin 2.0.25 is optional; runtime imports are standard Node modules only.

Core references are build-time byte-identical snapshots under core/.apm/, including
the exact transitive links, provenance and MIT notices. The explicit CORE_FILES
allowlist in the producer is the only selection source; broken/new links fail
inspection instead of triggering an unbounded copy. These are derived snapshots,
not a second edited methodology. Feedback exposes the installed snapshot path
so Core reference files are available outside producer paths. MIT LICENSE is
copied exactly; Habit Hooks remains an external separately licensed MIT tool.

CK04 uses a deterministic 127.0.0.1 HTTP provider, not a paid model or mock host.
The actual host executes native write/edit tools in two isolated projects and
returns original-mapper Core coaching to a subsequent provider HTTP request.
It observes successful rechecks, original errors, missing tools, refused configs/
executable overrides, unknown/no-file execute forms, same-version package
replacement/reload, deactivation and removal. Behavior-preserving modularization
keeps twelve total branches and agrees on 8192 inputs. A lower-branch but wrong
change is deliberately rejected by the independent fixture safety net despite
clean sensor metrics. A legitimate eight-argument protocol warning changes
neither its signature nor its source; the hook never fixes files.

Gortex receipts are authentic recorded-run forms replayed through the actual
execute tool with an explicitly rebound fixture path. This is a CONTRACT REPLAY,
not a fresh daemon mutation or full Gortex-MCP end-to-end proof. The out-of-scope
original receipt remains not_scanned. No hidden tracking prerequisite is created.
Lifecycle update means replacement of the same pinned 0.1.0 package and real
watcher reload; no unbuilt/unpublished future-version upgrade is claimed.

Review regressions additionally exercise real SDK-host events for twelve
regular/symlink detector shadows, actual suggest-severity coaching, disabled
repository helpers beside unrelated duplicate files and an external jscpd path,
and controlled opaque bash/patch/MCP events (these fixture tools execute no
command or input program). A trusted original-CLI observer records the effective
config and actual helper dispatch; it does not replace detection or filter
findings. PID/starttime/PGID records from the actual original helpers verify
timeout, output overflow, leader-exit race and real bridge-SIGTERM cleanup with
zero own survivors, including detached child sessions. Ordinary subprocesses
started in independent owner threads before, during and after stage start
remain alive and their own owners obtain exit status -15 after intentional
termination. Delegated real kill/killpg/waitpid tapes contain no unrelated ID.
Two concurrent original pipelines in the same adapter process keep disjoint
owned groups: the second tree remains alive after the first timeout, and both
then reap their own descendants. Controlled lifetime-test detectors are explicitly trusted outside
repositories; no production trust guard is switched off. This is bounded Linux
process-tree evidence, not an OS sandbox or a guarantee after catastrophic kill.

Round-two SDK-host cases also preserve the prior 76-case manifest and add
project/tools first on PATH, relative entries, empty cwd entries, directory
and executable symlink aliases outside the standard bins. No marker or
repository program is run for qualification; the original CI CLIs are absolute
and explicitly selected. Separate lifetime-fixture detector roots receive only
explicit reviewed installation grants, never a grant inferred from PATH.

After independent review, a user installer may persist the verified absolute
sensor/mapper/python/stateRoot and optional trustedToolRoots array in the
existing V2 global package/options registration, without shell/login changes.
Equivalent explicit HABIT_FEEDBACK_* launch fallbacks remain supported. Only
separately verified detector installations need additional roots; examples
above are shapes, not commands to trust arbitrary directories. No repository, home, /tmp or broad workspace
roots are appropriate grants. This package does not perform that user setup.

CK04 additionally exercises the persistent GLOBAL isolated package/options
object in two actual sandbox locations with no sensor/mapper/Python/state/trust
launch variables and only OS PATH. Original coaching and metadata reach the
provider. Before/after observer plugins hash the same isolated process.env
without recording its values; both concurrent location instances preserve that
fingerprint and receive no environment grant. Invalid present options produce
visible NOT SCANNED, not a fallback or clean verdict. This is not user activation.

Manual RV06 qualification respects original per-sensor preferences: disabled
ruff/line-count and non-None files overrides produce named not_scanned gaps
and no false complete/clean for unmeasured rules. No sensor is force-enabled
and no local pattern matcher is added. Even matching overrides remain
conservatively unqualified until a real per-sensor measured-file receipt is
available. Actual measured findings and original advisory severity remain
visible with their guide alongside partial-coverage warnings. CK04 exercises
ten preference/control cases in each of two actual projects, observing the
unchanged original bridge machine outcome, SDK content and next HTTP request.
The oversized-file Core guide references existing M02; it adds no second
methodology or detector/routing logic. This is an explicitly authorised manual
step, not a third automatic review round.

docs checks later T04 commands/conditional links and still requires manual
content review; it is neither a release gate nor an independent quality review.

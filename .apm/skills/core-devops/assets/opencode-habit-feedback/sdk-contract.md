# Qualified OpenCode V2 contract — 2.0.25 only

Primary SDK sources are the integrity-verified npm @opencode/plugin, schema and
client packages, exactly 2.0.25 (SHA512 receipts in VERSIONS.md). Live CLI help
and the isolated 2.0.25 host's /openapi.json additionally qualify server calls.
No inferred V1 /serve contract and no automatic move to 2.0.27.

- Plugin.Plugin is {id, setup(ctx)}. setup returns optional cleanup.
- ctx.tool.hook("execute.after", callback) returns a disposable registration.
- Event base: tool, sessionID, agent, messageID, id, input.
- Completed event: status="completed", result={output?, content?, metadata?}.
- Error event: status="error", error. It is left unchanged.
- content is string or text/file parts. Append feedback there; preserve original
  parts, structured output and metadata. No prompt, task or agent dispatch.
- ctx.session.get({sessionID}).location.directory is the event-session scope.
  Plugin-instance ctx.location is not a substitute.
- Native write input: {path,content}. Native edit: {path,oldString,newString,
  replaceAll?}. Successful live tools, not source-string inference, qualify paths.

## Actual CodeMode output envelope

A separate observer plugin in the actual isolated host recorded this before the
feedback hook. execute returning a receipt produced:


    result.output = {output: "<JSON return value>", toolCalls: [], files: []}
    result.content = [{type:"text", text:"<JSON return value>"}]
    result.metadata = {toolCalls: []}

The adapter accepts exactly the three output-envelope keys with string output
and array toolCalls/files, then parses that string once as a flat receipt or
receipt array. It does not infer mutations from files, toolCalls, program text,
arbitrary nesting or unrecognised wrappers. Unknown forms remain not_scanned.

Gortex receipt fixtures originate from real tracked-run mutations (commit-285,
commit-287). CK04 returns a path-rebased receipt through the actual execute tool
as an explicitly labelled CONTRACT REPLAY. This is not a new daemon write in
/tmp and not proof of a complete live Gortex MCP transport. Actual Gortex writes
outside registered repository roots are refused; no tracking/daemon fallback.

## Package and isolated host

The producer emits root index.js and plugin/index.js ESM from canonical TS.
OpenCode local plugin directories resolve a root entry; the npm export is also
./index.js. SDK imports are type-only and erased. The exact SDK peer is optional
because the host supplies its runtime; consumers get no install/download hooks.

The local-only provider uses documented @opencode/ai/providers/openai-compatible
with a 127.0.0.1 HTTP endpoint. Own servers are started with serve --hostname
127.0.0.1 --port <allocated>, not the user's background service. All host config,
state, caches and data are isolated. Generated host authentication stays in
memory and is redacted in persisted logs. Explicit setup installs the tarball;
normal integration/hook runs do not install tools or packages.

Executable trust is user/harness-controlled configuration, not a tool-event
field. Persistent V2 global registration may use
{package: installedPackage, options: {sensor, mapper, python, trustedToolRoots,
stateRoot}}. The four path values are qualified absolute strings;
trustedToolRoots is an array, not JSON text. Actual ctx.options snapshots bind
only the instance bridge child. No process.env or other plugin instance is
mutated. Omitted options retain corresponding explicit launch fallbacks;
invalid present options never fall back. Absolute HABIT_FEEDBACK_SENSOR/MAPPER
remain optional launch alternatives for qualified original CLI installations.
An optional HABIT_FEEDBACK_TRUSTED_TOOL_ROOTS JSON string grants only separately
verified owned installation directories. The shim transports it as launch
configuration; event input/output, project config, session location and arbitrary
PATH values cannot grant trust. Current tests refuse repository PATH aliases
while preserving original results and model-visible coverage warnings. Every
inherited lookup slot for an active detector is metadata-checked for aliases
into the repository even when options prepend a qualified CLI directory;
this preserves the previous warning boundary without executing candidates.

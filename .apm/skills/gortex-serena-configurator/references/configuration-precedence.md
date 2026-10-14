# Gortex-First and Serena Fallback Precedence

## Provider Precedence

Use Gortex first when its MCP is healthy and the active repository is already tracked. If either condition is false, use a prepared project-scoped Serena server. Use native repository and file tools only when neither provider can serve the operation.

Keep Gortex as the primary code-intelligence provider. The skill owns the readiness check and explicit transition to project-scoped Serena, not a change of primary provider. Maintain Serena initialization, project languages, and MCP exposure so the fallback is usable before an outage. Do not add Serena globally, alter Gortex tracking without selection, or query providers in parallel.

At every invocation, audit both provider states before asking which remediations to apply. Gortex tracking, global `AGENTS.md`, Serena initialization/MCP exposure, and Serena language reconciliation are separate selectable mutations.

## Verified Native Serena Behavior

For current Serena versions, the effective tool timeout is:

1. `serena start-mcp-server --tool-timeout <seconds>` when provided.
2. `<home>/.serena/serena_config.yml` key `tool_timeout` otherwise.
3. Serena's built-in default when the global key is absent.

The MCP factory loads the global Serena config and then assigns the CLI value when `tool_timeout` is not `None`. Therefore the CLI option overrides the global file for that server process.

`<cwd>/.serena/project.yml` and `project.local.yml` do not currently support `tool_timeout`. `ProjectConfig` supports project fields such as `symbol_info_budget`, `language_backend`, and `line_ending`, but not the tool execution timeout. `project.local.yml` overrides supported keys from `project.yml`; it cannot introduce unsupported keys.

Consequences:

- Do not write `tool_timeout` into project Serena YAML.
- Use global `tool_timeout: 10.0` for Serena invocations without a CLI override, including CLI recovery operations.
- Use `--tool-timeout 10` for a specific MCP process when its launch command must be self-contained.
- Keeping both is intentional only when both ordinary Serena CLI calls and MCP-server calls must independently enforce the policy.

## Separate MCP Client Timeout

The MCP client's `timeout` is not Serena's `tool_timeout`. Configure both when required:

- Serena `--tool-timeout 10`: seconds allowed for a Serena tool execution.
- OpenCode `timeout: 10000`: milliseconds used by OpenCode for its local MCP operation/startup boundary.
- Other clients may use seconds, milliseconds, or separate startup and tool-call fields. Verify the client's schema before writing.

The bundled script reports candidate client files heuristically. It does not use those regex results as authority because JSONC/TOML schemas and Serena block locations differ by client. Candidate parsing is discovery only: classify each path as active source, inactive candidate, generated projection, symlink projection, or unknown before writing. Confirm effective values with the active client's MCP listing or debug configuration before editing.

## Windows UTF-8 Stdio

On Windows, a locally installed Serena process can complete work but fail while printing Unicode status output through a CP1252 console. Configure this only on the confirmed active source for a local Serena MCP server:

```yaml
environment:
  PYTHONIOENCODING: utf-8
  PYTHONUTF8: "1"
```

This environment is separate from `--tool-timeout` and the MCP client timeout. Apply it to the SSOT, run its sync mechanism when applicable, and restart the client. Do not patch generated fragments or inactive candidates. Use the same two variables for direct Serena CLI recovery on Windows.

## Global Metadata Language Servers

`<home>/.serena/serena_config.yml` is Serena's global configuration, not a project language list. Do not add `languages` to it and do not disable its valid `language_backend: LSP` setting globally.

If Serena has registered its own configuration directory as a project, its effective configuration is `<home>/.serena/.serena/project.local.yml` when that file defines `languages`; otherwise it is `<home>/.serena/.serena/project.yml`. Keep the effective list at `languages: []` so the global metadata directory never starts an LSP. Real project language servers remain configured only in their own `.serena/project.yml` or winning `project.local.yml`.

## Source, Projection, and Candidate Ownership

Only the authoritative source of truth may be edited. A path is authoritative only when one of these is true:

1. The active client reports that exact file or entry as the effective Serena MCP source.
2. A known sync system documents the file as its host SSOT, such as `<home>/.config/mcp/servers.yaml` before generated client fragments are produced.
3. The user explicitly assigns that source path as the deliverable for the current task.

Generated fragments, symlinked skill projections, packaged runtime copies, and copied client snippets are projections. Use them to understand what a client may see, but edit their upstream SSOT instead. If the upstream SSOT is unavailable or ambiguous, report the projection and stop rather than hand-patching it. Do not edit both a source and its projection in one pass; that creates false convergence and hides sync drift.

Candidate files are weaker than projections. They are paths discovered by regex, naming convention, or broad config search that might contain Serena configuration. Treat them as `inactive candidate` unless the active client or owning sync system proves they are used.

## Project Versus User Client Config

Project/user precedence belongs to the MCP client, not Serena. Do not generalize one client's merge rule to another.

Use this decision order:

1. Identify the active client.
2. Ask the client to show its effective MCP servers when it has such a command.
3. Locate the source that owns the effective Serena entry.
4. If the file is generated, find and edit its SSOT instead.
5. Apply the 10-second values only to the winning source.
6. Re-run generation/sync and inspect the effective client view.

Typical candidate paths that may become authoritative after confirmation include:

- Host SSOT: `<home>/.config/mcp/servers.yaml`
- OpenCode: `<home>/.config/opencode/opencode.jsonc` or a project OpenCode config
- Codex: `<home>/.codex/config.toml` or a project-specific source
- Claude: `<home>/.claude.json` and project entries managed by Claude

Treat paths under `<home>/.config/mcp/generated/` as generated unless proven otherwise.

## Deprovisioned Global MCP

An absent Serena entry in the host SSOT, MCPM registry, generated fragments, and global client configuration is a valid deprovisioned state. Do not re-add it merely because Serena CLI remains installed or a project has Serena metadata.

Project-level Serena MCP configuration remains possible when the user explicitly requests it. Apply timeout and UTF-8 settings only to that confirmed project-level source.

MCPM owns `<home>/.config/mcpm/servers.json`; remove a Serena entry with `mcpm uninstall serena`. Edit the registry manually only if MCPM is unavailable, the entry is clearly stale, and the user explicitly requests removal.

## AGENTS.md Scope

Audit both `<home>/AGENTS.md` and `<cwd>/AGENTS.md`. User-home Serena safety belongs only in the global file; the project file receives a separate repository-specific provider and readiness block. Avoid duplicate text:

- Replace the `SERENA-GORTEX-PLAYBOOK` managed block when present.
- Migrate a legacy `SERENA-PLAYBOOK` block in place instead of appending a duplicate.
- Preserve an equivalent existing Serena/Gortex section outside the managed block.
- Append the managed section only where no equivalent guidance exists.
- Replace the `SERENA-GORTEX-PROJECT` block in the project file when present.
- Preserve equivalent unmarked project guidance; otherwise append the project block.

## Project Language Servers

Serena reads project languages from `<cwd>/.serena/project.yml`. If `<cwd>/.serena/project.local.yml` defines `languages`, that local value overrides the base project value. Update only the winning file.

Select languages from meaningful project source files:

1. Prefer `git ls-files --cached --others --exclude-standard` so ignored files are absent.
2. Fall back to a non-symlink-following filesystem walk when Git is unavailable.
3. Exclude Serena/agent metadata, dependencies, generated output, build output, caches, and vendor trees.
4. Count recognized programming-language extensions. Do not auto-enable JSON, YAML, TOML, or Markdown LSPs merely because project metadata exists.
5. Always keep the dominant recognized language.
6. Keep a secondary language only with at least five files or at least 10% of recognized source files.
7. Order enabled languages by descending file count, then language name for deterministic ties.
8. Preserve explicitly configured backend variants (`typescript_vts`, `python_jedi`, `python_ty`, `cpp_ccls`, `csharp_omnisharp`, `ruby_solargraph`, or `php_phpactor`) when their base language remains selected.

The threshold prevents isolated helpers from starting extra language servers. For example, two documentation-generator Python scripts in a repository with 89 TypeScript files are reported as low signal and do not enable Python. A small project with two TypeScript and one Python source file keeps both because Python represents one-third of recognized source files.

If no meaningful source language exists, use `languages: []` in an already valid Serena project config. Do not write `languages:` with a null value and do not invent a fallback language. Restart Serena after changing the language list because language servers are selected during project initialization.

## Source Evidence

The behavior above is grounded in current Serena source:

- `serena/config/serena_config.py`: `SerenaConfig.tool_timeout`, global config path resolution, and `ProjectConfig` fields.
- `serena/config/serena_config.py`: `project.local.yml` overrides supported project keys, including `languages`, from `project.yml`.
- `serena/cli.py`: `--tool-timeout` is documented as an override and passed to the MCP factory.
- `serena/mcp.py`: a non-null CLI timeout is assigned after loading the default/global config.

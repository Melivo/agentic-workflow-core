---
name: gortex-serena-configurator
description: Configure a Gortex-first, Serena-second, native-tools-third code-intelligence chain for a concrete repository. Use when checking or adding Gortex tracking, auditing the global Serena/Gortex AGENTS.md policy, initializing a project-scoped Serena fallback, reconciling Serena languages with repository sources, or repairing provider readiness.
---

# Gortex And Serena Configurator

Use one provider per operation. Prefer Gortex only when its MCP is healthy and the active repository is tracked, then Serena, then native tools.

## Provider Order

1. Use Gortex when its MCP is healthy and the repository is already tracked.
2. Use project-scoped Serena when Gortex is unavailable, unhealthy, or does not track the repository.
3. Use native file and search tools only when neither Gortex nor Serena can serve the operation.
4. Bound Serena to the concrete project. Never activate a user home, filesystem root, or broad parent directory.
5. Return to Gortex when it becomes available. Do not duplicate a query across providers merely to compare results.

Keep Gortex as the configured primary code-intelligence provider; Serena is the prepared project fallback. A fallback does not require changing the primary provider.

## Invocation Preflight

1. Resolve the concrete repository root and refuse the user home or a filesystem root.
2. Audit Gortex MCP health and repository tracking without changing either.
3. Always audit Serena CLI availability, project initialization, effective project languages, and the active project's MCP exposure before selecting a provider.
4. Ask one structured multi-select question unless the user's request already selects the actions. Offer these choices:
   - `Serena prüfen/einrichten (Empfohlen)`: initialize or repair the project-scoped Serena fallback and its authoritative MCP source.
   - `Serena-Sprachen abgleichen (Empfohlen)`: detect meaningful repository languages and reconcile the effective project config.
   - `AGENTS.md prüfen`: audit or install the managed global and repository Serena/Gortex sections.
   - `Repository in Gortex tracken`: add tracking only after this explicit selection.
5. Treat the selected choices as authorization only for those mutations. Keep all unselected checks read-only.

When no structured question tool exists, ask the same four choices in one concise numbered question and allow multiple selections.

## Required Fallback Policy

- Inspect both `<home>/AGENTS.md` and `<project>/AGENTS.md`. Preserve equivalent complete guidance, update managed blocks in place, and append only missing sections. Migrate the legacy global `SERENA-PLAYBOOK` block without duplication.
- Keep Home safety rules in the global block. Write only repository provider order and Serena readiness rules to the project block.
- In the user home, use native file, search, and runtime tools instead of Gortex or Serena. Use the local Serena CLI there only for configuration, project management, memories, and recovery.
- Keep the effective global metadata project config at `languages: []`: use `<home>/.serena/.serena/project.local.yml` when it defines `languages`, otherwise `<home>/.serena/.serena/project.yml`.
- Do not add `languages` to `<home>/.serena/serena_config.yml`. `language_backend: LSP` remains valid globally; real projects own their language lists.
- Keep global Serena MCP configuration deprovisioned. Ensure the active project has an authoritative project-scoped Serena MCP entry.
- Select the dominant source language and retain a secondary language only at five files or 10% of recognized source files. Preserve configured backend variants when their base language remains selected.
- Modify Gortex tracking only when `Repository in Gortex tracken` was selected. Never remove tracking or change index state implicitly.

## Workflow

1. Read `references/configuration-precedence.md`, then run `python scripts/serena_safety.py --cwd <project> --home <home>` for the mandatory read-only baseline.
2. Ask the invocation preflight question and map selected actions to `--apply-agents`, `--apply-serena`, and `--apply-languages`. `--apply` remains the explicit all-managed-actions shortcut.
3. For selected Gortex tracking, use the configured Gortex MCP tracking operation and verify that the repository becomes ready. Do not use a CLI fallback when the active profile requires native Gortex MCP.
4. For selected Serena setup, initialize the concrete project when missing, verify the authoritative project MCP source, and keep Gortex as the primary provider.
5. For selected language reconciliation, apply the detected language set to the effective `project.local.yml` or `project.yml`.
6. Patch only a confirmed MCP SSOT. Regenerate client projections instead of editing generated files.
7. Re-run the audit. Restart Serena after configuration or language changes and inspect the active client's effective MCP listing when available.
8. Report readiness separately for Gortex, Serena, native fallback, global guidance, and languages.

## Precedence And Ownership

- `serena start-mcp-server --tool-timeout 10` overrides global `tool_timeout: 10.0`.
- Never write `tool_timeout` in project YAML; current Serena project schemas do not support it.
- `project.local.yml` wins over `project.yml` for `languages`; update only the winning file.
- OpenCode `timeout` is milliseconds (`10000`); Serena CLI timeouts are seconds (`10`). Apply client values only to an authoritative project-level MCP source.
- On Windows, set `PYTHONIOENCODING=utf-8` and `PYTHONUTF8=1` in the active local MCP source, then regenerate projections.

## Guardrails

- Never scan the whole home, a broad repository root, dependencies, generated output, binaries, caches, or vendor directories with Serena.
- Never launch broad Serena calls in parallel.
- Never overwrite an entire `AGENTS.md`; preserve an equivalent section, replace the current or legacy managed block, or append only when complete guidance is absent.
- Never create a partial global Serena config. Initialize it with Serena before setting `tool_timeout`.
- Never edit generated projections, runtime copies, or symlinks when an upstream source exists.
- Do not hand-edit an MCPM registry. Use its owner CLI after explicit authorization.
- Snapshot every managed file and roll back selected writes if initialization, parsing, or writing fails.

## Serena Recovery

- After one Serena timeout, retry once with a narrower request.
- After a second timeout, use the local Serena CLI from the concrete workspace.
- Stop only a confirmed stale `serena ... start-mcp-server` process, restart the client session, then retry.

## Resources

- `references/configuration-precedence.md`: verified provider, timeout, client, project-language, and ownership rules.
- `scripts/serena_safety.py`: audit and selectively authorized managed writes.
- `scripts/test_serena_safety.py`: regression tests for the audit utility.

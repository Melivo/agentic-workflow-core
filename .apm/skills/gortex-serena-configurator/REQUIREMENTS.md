# Requirements

## Runtime and platform

- Python 3.10 or newer on Windows, Linux, or macOS.
- `ruamel.yaml>=0.18,<0.20` is the YAML implementation imported by the
  bundled audit script and is declared in `scripts/requirements.txt`.
- PyYAML (`import yaml`) is not imported by this source snapshot and is not a
  substitute for `ruamel.yaml`. It is needed only if a separately selected,
  user-authorized Serena or client integration requires it.
- Primary Gortex use is performed through the runtime's configured Gortex MCP and does not depend on the bundled script.
- Read-only Serena fallback audit mode requires no Serena or MCP-client CLI.

## Optional user-authorized Serena fallback branches

- The Serena CLI is required only when an explicit `--apply-serena` or `--apply` run must
  initialize a missing Serena global or project configuration.
- A relevant MCP-client CLI is required only when the user authorizes
  effective-configuration verification or an owner-mediated client change.
- The MCPM CLI is required only for a user-authorized MCPM-owned removal; its
  registry must not otherwise be edited directly.
- `git` is optional and is used only for bounded project-file discovery. The
  script falls back to a non-symlink-following local walk when Git is absent.
- The script does not track repositories in Gortex, modify a Gortex index, or
  switch code-intelligence providers. Those remain separate, explicitly authorized actions.

## Permissions and local access

- Read access is required only for the explicitly supplied project and home
  roots and this skill's bundled files.
- Write access is required only for paths selected by an explicit,
  user-authorized selective apply run: the managed home and project
  `AGENTS.md` files, applicable Serena global or metadata configuration, and
  the winning project Serena configuration.
- Client or MCP source writes are optional and permitted only after the active
  client and authoritative source of truth are confirmed and the user
  authorizes that path. Generated projections, symlinks, and ambiguous
  candidates remain read-only.
- Temporary-directory write access is required only while performing atomic
  writes or tests. No administrative or broad filesystem permission is
  required.

## Network, credentials, and package boundary

- No network access or credential is required by the bundled audit or tests.
- No sibling skill, user-specific absolute path, or external script is a
  runtime dependency.
- Do not package `__pycache__`, `.pyc`, `.pyo`, or `.pyd` artifacts.

## Local verification

```text
python -m unittest discover -s scripts -p "test_serena_safety.py"
```

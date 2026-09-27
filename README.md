# Agentic Workflow Core

Agentic Workflow Core ist ein portables Microsoft-APM-Paket für OpenCode und Codex. Die kanonische Paketquelle liegt unter `.apm/`; generierte Projektionen in `.agents/`, `.opencode/` oder `.codex/` werden nicht manuell gepflegt.

## Voraussetzungen

- Microsoft Agent Package Manager (APM)
- ein unterstütztes Zielharness (OpenCode oder Codex)
- Gortex als primäre Repository-Code-Intelligence
- projektbezogen konfiguriertes Serena nur als erlaubter Fallback

Das Manifest deklariert ausschließlich die externe APM-Abhängigkeit `Melivo/apm-package/skills/gortex-serena-configurator`. `skill-creator` und `context-debloater` sind lokale Authoring-Werkzeuge und keine Paketabhängigkeiten.

## Installation

Projektbezogen für OpenCode und Codex:

```bash
apm install Melivo/agentic-workflow-core --target opencode,codex
```

APM schreibt die aufgelösten Versionen nach `apm.lock.yaml` und projiziert Skills und Agenten in die Zielharness-Verzeichnisse. Prüfe Änderungen vor einer dauerhaften Installation mit demselben Befehl plus `--dry-run`.

## Namens- und Paketvertrag

Jedes paketeigene Skillbundle liegt unter `.apm/skills/core-<name>/`. Verzeichnisname und `name` im `SKILL.md`-Frontmatter müssen identisch sein. Das gemeinsame interne Bundle liegt unter `.apm/skills/core-shared/` und verwendet `name: core-shared`. Die externe Abhängigkeit `gortex-serena-configurator` wird weder kopiert noch in das `core-`-Schema umbenannt.

Bestätigte Pläne unter `.agentic-workflow/plans/` sind versionierbare Quellen. Temporäre Laufzustände unter `.agentic-workflow/runs/` werden ignoriert und niemals in den bestätigten Plan zurückgeschrieben.

## Autorisierungsgrenzen

Das Paket autorisiert keine impliziten Nebenwirkungen. Insbesondere gelten getrennte, ausdrückliche Freigaben für:

- Build, Compile, Bundle und Packaging,
- Installation einschließlich `apm install`,
- Commit, Push, Tag, Release und Deployment,
- destruktive Aktionen.

Build-, Compile-, Packaging- und Installationsbefehle werden nur nach ausdrücklicher Freigabe ausgeführt. Fachagenten bearbeiten genau einen zugewiesenen Task innerhalb seines Scopes und starten keine eigenen Subagenten.

## Kanonische Paketoberfläche

Die öffentliche Workflowkette besteht ausschließlich aus diesen paketeigenen Skills:

1. [`core-brainstorm`](.apm/skills/core-brainstorm/SKILL.md) — optionale Klärung vor der Planung,
2. [`core-plan`](.apm/skills/core-plan/SKILL.md) — Erstellung genau eines bestätigten `plan/v1`,
3. [`core-execute`](.apm/skills/core-execute/SKILL.md) — einziger öffentlicher Ausführungsworkflow,
4. [`core-review`](.apm/skills/core-review/SKILL.md) — unabhängige Prüfung in frischem Kontext ohne eigene Korrekturen.

```text
core-brainstorm? → core-plan → core-execute ↔ core-review
```

Die Fachmethoden [`core-architecture`](.apm/skills/core-architecture/SKILL.md), [`core-backend`](.apm/skills/core-backend/SKILL.md), [`core-database`](.apm/skills/core-database/SKILL.md), [`core-debug`](.apm/skills/core-debug/SKILL.md), [`core-docs`](.apm/skills/core-docs/SKILL.md), [`core-frontend`](.apm/skills/core-frontend/SKILL.md), [`core-mobile`](.apm/skills/core-mobile/SKILL.md), [`core-refactor`](.apm/skills/core-refactor/SKILL.md), [`core-repo-audit`](.apm/skills/core-repo-audit/SKILL.md), [`core-research`](.apm/skills/core-research/SKILL.md) und [`core-tf-infra`](.apm/skills/core-tf-infra/SKILL.md) werden nur innerhalb ihres bestätigten Scopes verwendet. Einrichtung und Pflege übernehmen [`core-init-mcps`](.apm/skills/core-init-mcps/SKILL.md), [`core-init-project`](.apm/skills/core-init-project/SKILL.md) und [`core-user2agent-instructions`](.apm/skills/core-user2agent-instructions/SKILL.md). Ein optionaler Schritt mit [`core-scm`](.apm/skills/core-scm/SKILL.md) folgt erst nach bestandenem Review und gesonderter Autorisierung.

Das interne Bundle [`core-shared`](.apm/skills/core-shared/SKILL.md) bündelt die kanonischen [Workflow-](.apm/skills/core-shared/references/workflow-contract.md), [Artefakt-](.apm/skills/core-shared/references/artifact-contract.md), [Toolrouting-](.apm/skills/core-shared/references/tool-routing.md) und [Verifikationsverträge](.apm/skills/core-shared/references/verification.md). Diese Verweise zeigen ausschließlich auf versionierte Paketartefakte unter `.apm/`.

## Lizenz

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE).

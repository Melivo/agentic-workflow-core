# Agentic Workflow Core

Agentic Workflow Core ist ein portables Microsoft-APM-Paket für OpenCode und Codex. Die kanonische Paketquelle liegt unter `.apm/`; generierte Projektionen in `.agents/`, `.opencode/` oder `.codex/` werden nicht manuell gepflegt.

## Voraussetzungen

- Microsoft Agent Package Manager (APM)
- ein unterstütztes Zielharness (OpenCode oder Codex) oder gemeinsame Agent-Skills
- Gortex als primäre Repository-Code-Intelligence
- projektbezogen konfiguriertes Serena nur als erlaubter Fallback

Das Manifest deklariert ausschließlich die externe APM-Abhängigkeit `Melivo/apm-package/skills/gortex-serena-configurator`. `skill-creator` und `context-debloater` sind lokale Authoring-Werkzeuge und keine Paketabhängigkeiten.

## Installation

Global ausschließlich im gemeinsamen Skill-Verzeichnis `~/.agents/skills/`:

```bash
apm install Melivo/agentic-workflow-core --global --target agent-skills --only apm
apm install Melivo/agentic-workflow-core --global --target agent-skills --only apm --update
```

`--only apm` trennt die Skill-Installation von MCP-Konfiguration; `agent-skills` unterstützt selbst keine MCPs. Unter APM 0.31 hat `apm update` keinen entsprechenden Filter, daher verwendet das Update-Beispiel den unterstützten Installationsschalter `--update`.

Dieser Modus installiert Skills, keine harnessspezifischen Agentendefinitionen oder MCP-Konfiguration. OpenCode kann die gemeinsamen Skills nutzen; zusätzliche Kopien unter `~/.config/opencode/skills/` sind nicht erforderlich. Setze im globalen Verbrauchsmanifest `targets: [agent-skills]`, damit spätere Updates bei diesem Ziel bleiben. MCPs und native Fachagenten bleiben getrennt konfigurierte Voraussetzungen.

Optional projektbezogen für ausdrücklich ausgewählte OpenCode-/Codex-Ziele:

```bash
apm install Melivo/agentic-workflow-core --target opencode,codex
```

APM schreibt die aufgelösten Versionen nach `apm.lock.yaml` und projiziert Skills und Agenten in die Zielharness-Verzeichnisse. Prüfe Änderungen vor einer dauerhaften Installation mit demselben Befehl plus `--dry-run`.

## Installierbares Bundle erzeugen

Packe aus einem sauberen **Producer-Checkout dieses Repositories**, nicht aus einem Verbrauchsprojekt, das Core als Abhängigkeit installiert hat. APM 0.31 kann in einem Verbraucher-Bundle auf dessen nicht mitgelieferten `apm_modules`-Cache verweisende Links behalten.

```bash
# In einer separaten Producer-Arbeitskopie; nicht im Benutzerprofil.
# Alle deklarierten Producer-Ziele für einen konsistenten Audit vorbereiten.
apm install --only apm
apm audit --ci
apm pack --offline --target agent-skills --output ./dist
# In einem separaten Verbrauchsverzeichnis:
apm install /path/to/dist/agentic-workflow-core-0.1.0 --target agent-skills
```

Für eine ZIP-Datei ergänze beim Packen `--archive`. Bei der Installation eines lokalen Bundles ist `--only apm` nicht erlaubt; das Bundle wird ohne Dependency-Auflösung direkt installiert.

Das Pack-Ziel ist in APM 0.31/0.33 zwar als deprecated markiert, hier aber absichtlich gesetzt: Ohne den Schalter kann APM `pack.target: minimal` schreiben und die Bundle-Installation mit `KeyError: minimal` abbrechen. Nutze in diesen Versionen das geprüfte Standardformat; `--format apm` ist kein Ersatz für das installierbare Plugin-Bundle.

Der Abnahmecheck muss Installation, alle 22 Core-Bundles, auflösbare interne Methoden-/Vertragslinks und beide Lizenzhinweise prüfen. Ein erfolgreicher Pack- oder Install-Exitcode allein genügt nicht. Die Paket-MIT-Lizenz liegt dafür zusätzlich im mitgelieferten Bundle `core-shared/LICENSE`; Clairvoyance-Hinweise bleiben unter `core-architecture/THIRD_PARTY_NOTICES.md`. Native Agentendefinitionen werden bei `agent-skills` nicht installiert.

## Namens- und Paketvertrag

Jedes paketeigene Skillbundle liegt unter `.apm/skills/core-<name>/`. Verzeichnisname und `name` im `SKILL.md`-Frontmatter müssen identisch sein. Das gemeinsame interne Bundle liegt unter `.apm/skills/core-shared/` und verwendet `name: core-shared`. Die externe Abhängigkeit `gortex-serena-configurator` wird weder kopiert noch in das `core-`-Schema umbenannt.

In diesem Repository bleibt das gesamte Verzeichnis `.agentic-workflow/` lokal und wird von Git ignoriert, einschließlich Plänen und Laufartefakten. Laufstatus und Nachweise werden niemals in den bestätigten Plan zurückgeschrieben.

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

Die Fachmethoden [`core-architecture`](.apm/skills/core-architecture/SKILL.md), [`core-backend`](.apm/skills/core-backend/SKILL.md), [`core-database`](.apm/skills/core-database/SKILL.md), [`core-debug`](.apm/skills/core-debug/SKILL.md), [`core-docs`](.apm/skills/core-docs/SKILL.md), [`core-frontend`](.apm/skills/core-frontend/SKILL.md), [`core-mobile`](.apm/skills/core-mobile/SKILL.md), [`core-refactor`](.apm/skills/core-refactor/SKILL.md), [`core-repo-audit`](.apm/skills/core-repo-audit/SKILL.md), [`core-research`](.apm/skills/core-research/SKILL.md) und [`core-tf-infra`](.apm/skills/core-tf-infra/SKILL.md) werden nur innerhalb ihres bestätigten Scopes verwendet. Einrichtung und Pflege übernehmen [`core-init-mcps`](.apm/skills/core-init-mcps/SKILL.md), [`core-init-project`](.apm/skills/core-init-project/SKILL.md) und [`core-user2agent-instructions`](.apm/skills/core-user2agent-instructions/SKILL.md). Für ausdrücklich etappenbasierte Vorhaben besitzt [`core-milestone`](.apm/skills/core-milestone/SKILL.md) Ziel, unveränderliche Definitionen und den aktualisierbaren Auswahl-/Nachweisindex; [`core-handoff`](.apm/skills/core-handoff/SKILL.md) unterstützt autorisierte Sitzungs- und Etappenübergaben, ohne selbst Status zu verwalten. Diese unterstützenden Skills schaffen keinen alternativen Kernlebenszyklus. Ein optionaler Schritt mit [`core-scm`](.apm/skills/core-scm/SKILL.md) folgt erst nach bestandenem Review und gesonderter Autorisierung.

Das interne Bundle [`core-shared`](.apm/skills/core-shared/SKILL.md) bündelt die kanonischen [Workflow-](.apm/skills/core-shared/references/workflow-contract.md), [Artefakt-](.apm/skills/core-shared/references/artifact-contract.md), [Toolrouting-](.apm/skills/core-shared/references/tool-routing.md) und [Verifikationsverträge](.apm/skills/core-shared/references/verification.md). Diese Verweise zeigen ausschließlich auf versionierte Paketartefakte unter `.apm/`.

## Ziele und versionierte Etappen

Eine einfache Änderung braucht kein Zielartefakt und keine Etappenstruktur: ein bestätigter `plan/v1` genügt. Nur ausdrücklich gewählte mehrstufige Vorhaben verwenden die getrennten Formate `goal/v1`, `milestone-definition/v1` und `milestone-index/v1`. `core-milestone` besitzt `.agentic-workflow/goals/G01/goal.md`, die unveränderlichen Definitionen unter `milestones/` und `index.yaml`; der Index hält die ausdrücklich bestätigte Auswahl und exakte Plan-, Run- und Abschlussverweise, nicht einen zweiten Aufgabenstatus. Die kanonischen [Ziel-](.apm/skills/core-milestone/references/goal-format.md), [Definitions-](.apm/skills/core-milestone/references/milestone-format.md) und [Indexformate](.apm/skills/core-milestone/references/milestone-index-format.md) bestimmen Details.

Beispiel: `.agentic-workflow/goals/G01/milestones/M02-v1.yaml` bleibt nach Bestätigung unverändert. Eine inhaltliche Änderung erzeugt nach Prüfung und ausdrücklicher Bestätigung `M02-v2.yaml`; erst eine ebenfalls bestätigte Indexauswahl macht diese Fassung aktuell. Ein gepinnter Plan wie `plan-G01-M02-v1-p01.md` bleibt an v1 gebunden. Ein Ersatzplan für v2 wird `plan-G01-M02-v2-p01.md` (oder `p02` als Ersatz derselben Fassung); Namen ersetzen keine exakten Pfadbezüge oder Freigaben. Ein eigenständiger neuer Lauf erhält eine neue Run-ID, z. B. `run-G01-M02-v2-p01-r01/`; Resume und Review-Reparaturen behalten dieselbe Run-ID. Taskversuche sind getrennte, unveränderliche Nachweise wie `tasks/T01/attempt-01.yaml`.

Versionswechsel übertragen weder Planbindung noch Erfolg: historische Abschlussnachweise bleiben an v1, und ihre Wiederverwendung für v2 verlangt eine ausdrückliche Prüfung gegen neue Kriterien und Abhängigkeiten. Abhängige Etappen bleiben bei alten Versionsbezügen blockiert, bis passende Ersatzdefinitionen bestätigt sind. Eine höhere Versionsdatei wird nicht automatisch ausgewählt; eine neue Version erteilt keine Folgefreigabe. Das frühere `milestone/v1` ist nur über seinen ausdrücklich benannten Pfad lesbar, ohne automatische Migration oder Vermischung. Beim Handoff werden Ziel-, Index-, Definitions-, Plan- und anwendbare Runpfade geprüft; der Prompt selbst erteilt keine Freigabe.

## Interne Designmethoden und aktuelle MCP-Fähigkeiten

Die [SWE-Basis und situative Auswahl](.apm/skills/core-architecture/references/design-baseline.md) bündelt klare Verantwortlichkeiten, stabile Schnittstellen, Information Hiding, begründete Abhängigkeiten und Testbarkeit. Coding-Skills berücksichtigen diese Basis und prüfen zum Abschluss die betroffenen Module. Clairvoyance-Methoden sind intern konsolidiert und werden nur bei konkreten Signalen vertieft, nicht als obligatorischer Komplettscan. Ihr Laden startet keinen Architekturworkflow und erlaubt keine ungeplanten Refactorings.

Die [Provenienz](.apm/skills/core-architecture/PROVENANCE.md) dokumentiert alle 16 Quellskills; der [MIT-Hinweis](.apm/skills/core-architecture/THIRD_PARTY_NOTICES.md) begleitet die Adaptionen. Separat installierte Clairvoyance- oder SWE-Skills sind nicht erforderlich. Der private UNLICENSED-SWE-Skill wurde nicht übernommen.

Das [Toolrouting](.apm/skills/core-shared/references/tool-routing.md) nutzt geeignete aktuell verfügbare MCP-Fähigkeiten anhand konkreten Bedarfs und gezielter Discovery. Providerpriorität, Projektscope, Freshness, Autorisierung und erlaubte Fallbacks bleiben maßgeblich; Verfügbarkeit autorisiert keine Nebenwirkungen.

## Lizenz

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE).

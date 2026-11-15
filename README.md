# Agentic Workflow Core

[![CI](https://github.com/Melivo/agentic-workflow-core/actions/workflows/ci.yaml/badge.svg)](https://github.com/Melivo/agentic-workflow-core/actions/workflows/ci.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Planen, kontrolliert umsetzen, unabhängig prüfen.**

Agentic Workflow Core ist ein portables Paket aus Agent-Skills für KI-gestützte Softwareentwicklung mit OpenCode und Codex. Es nutzt die Fähigkeiten des jeweiligen Agent-Harnesses; es ist keine zusätzliche Orchestrierungs-CLI und kein autonomer Releasebot. Pläne, Aufträge, Ergebnisse und Reviews bleiben als nachvollziehbare Dateien erhalten.

[Installation](#installation) · [Erste Verwendung](#erste-verwendung) · [Skills](#skills) · [Grenzen](#grenzen) · [Entwicklung](docs/development.md)

## Installation

Voraussetzungen: [Microsoft Agent Package Manager (APM)](https://microsoft.github.io/apm/getting-started/installation/) und ein Harness mit Unterstützung für gemeinsame Agent-Skills, etwa OpenCode oder Codex. Die Skill-Installation richtet MCP-Server, Modellanbieter oder native Fachagenten nicht automatisch ein.

Core global im gemeinsamen Verzeichnis `~/.agents/skills/` installieren:

```bash
apm install Melivo/agentic-workflow-core --global --target agent-skills --only apm
```

Für bewusste Integration in OpenCode-/Codex-Ziele des aktuellen Projekts:

```bash
apm install Melivo/agentic-workflow-core --target opencode,codex
```

Diese Integration kann Harness-Konfiguration erzeugen; sie ist für die globale Skill-Nutzung nicht erforderlich. Details zu Aktualisierung, Pins und APM-Zielen: [Entwicklungsleitfaden – Paketinstallation](docs/development.md#paketinstallation).

## Erste Verwendung

Wähle einen der beiden Wege:

- **Plan:** Für größere, zerlegbare oder noch unklare Vorhaben erstellt `core-plan` einen Planentwurf. Nach statischer Validierung prüft `core-review` ihn unabhängig vor dem kanonischen Schreiben und einer noch erforderlichen Nutzerbestätigung. Eine belegte abgeleitete Freigabe heißt: eine neue Nutzerbestätigung entfällt. Ohne bestätigten Rahmen, bei neuen eigenständigen Zielen, Meilensteinänderungen, ausdrücklichen Ausschlüssen, materiell offenen Entscheidungen, unklaren oder ungedeckten Wirkungen oder ungedeckten Geldkosten ist die Nutzerentscheidung vor Schreiben und Ausführung erforderlich. Die Umsetzung setzt stets eine ausdrückliche oder belegte abgeleitete Planfreigabe und einen bestehenden Ausführungsauftrag voraus. Beim Erstplan mit Gesamtfreigabe oder Handoff gilt die [besondere Reihenfolge](.apm/skills/core-shared/references/workflow-contract.md#handoff-abgeleitete-planungsbefugnis-und-erstplanfreigabe). Danach folgen freigegebenes `core-execute` und unabhängiges Umsetzungsreview.
- **Direkt:** Für eine klare, enge Änderung mit ausdrücklicher Umsetzungsfreigabe: `core-execute` arbeitet direkt aus `request.md` und übergibt das integrierte Ergebnis an `core-review`.

Beispiele:

> Nutze core-plan für diese Aufgabe. Erstelle zunächst nur den Plan und implementiere noch nichts.

> Der Plan unter dem genannten Pfad ist bestätigt. Nutze core-execute innerhalb seines Scopes.

> Nutze core-review für eine unabhängige Prüfung. Implementiere keine Korrekturen.

Für die Projekteinrichtung prüft `core-init-project` Repository und Code-Intelligence-Bereitschaft. Gortex ist primär; ein Serena-Fallback muss für das konkrete Projekt ausdrücklich eingerichtet sein. Änderungen an Providerkonfiguration oder `AGENTS.md` brauchen ihre eigene Freigabe.

## Skills

| Bereich | Skills |
| --- | --- |
| Kernworkflow | [core-brainstorm](.apm/skills/core-brainstorm/SKILL.md), [core-plan](.apm/skills/core-plan/SKILL.md), [core-execute](.apm/skills/core-execute/SKILL.md), [core-review](.apm/skills/core-review/SKILL.md) |
| Umsetzung | [Architektur](.apm/skills/core-architecture/SKILL.md), [Backend](.apm/skills/core-backend/SKILL.md), [Frontend](.apm/skills/core-frontend/SKILL.md), [Mobile](.apm/skills/core-mobile/SKILL.md), [Datenbanken](.apm/skills/core-database/SKILL.md), [Terraform](.apm/skills/core-tf-infra/SKILL.md) |
| Untersuchung und Pflege | [Research](.apm/skills/core-research/SKILL.md), [Debugging](.apm/skills/core-debug/SKILL.md), [Refactoring](.apm/skills/core-refactor/SKILL.md), [Repo-Audit](.apm/skills/core-repo-audit/SKILL.md), [Dokumentation](.apm/skills/core-docs/SKILL.md), [DevOps](.apm/skills/core-devops/SKILL.md) |
| Einrichtung | [core-init-project](.apm/skills/core-init-project/SKILL.md), [core-init-mcps](.apm/skills/core-init-mcps/SKILL.md), [core-user2agent-instructions](.apm/skills/core-user2agent-instructions/SKILL.md) |
| Etappen und Übergaben | [core-milestone](.apm/skills/core-milestone/SKILL.md), [core-handoff](.apm/skills/core-handoff/SKILL.md) |
| Beratende Bewertung | [core-typesafe](.apm/skills/core-typesafe/SKILL.md) |
| Gemeinsame Verträge | [core-shared](.apm/skills/core-shared/SKILL.md) – interner Vertragsindex, kein zusätzlicher Workflow |

Die kanonische Paketquelle liegt unter `.apm/` und enthält 23 Core-Bundles. Die Provider-/Runtimeintegration gehört intern zu `core-init-project`; es gibt keine externe APM-Skillabhängigkeit und keinen erforderlichen Zugriff auf eine private Skillsammlung.

## Grenzen

Du entscheidest über Ziel, Umfang und freizugebende Aktionen. Ein erlaubter Dateipfad ist keine Freigabe für beliebige zusätzliche Funktionen. Build, Compile, Bundle, Packaging, Installation, Commit, Push, Tag, Release, Deployment und destruktive Aktionen brauchen jeweils eine passende ausdrückliche Autorisierung. Unabhängige Reviews bleiben read-only; Toolausgaben autorisieren keine Folgearbeit.

Die ausführlichen Regeln stehen in den [Workflow-](.apm/skills/core-shared/references/workflow-contract.md), [Artefakt-](.apm/skills/core-shared/references/artifact-contract.md), [Toolrouting-](.apm/skills/core-shared/references/tool-routing.md) und [Verifikationsverträgen](.apm/skills/core-shared/references/verification.md). Architektur, Paketquellen, Prüfungen und Betrieb stehen im [Entwicklungsleitfaden](docs/development.md).

[Design und Architektur](DESIGN.md) · [Versionshistorie](CHANGELOG.md) · [Lizenz](LICENSE)

## Optionales Qualitätsfeedback

[opencode-habit-feedback@0.1.0](https://www.npmjs.com/package/opencode-habit-feedback) ist ein separates, optionales OpenCode-V2-Plugin. Die Core-Skill-Installation aktiviert oder installiert es nicht. Hinweise in unterstützten Tool-Ergebnissen sind keine Benutzeranweisungen oder Freigaben. [Technische Details und Grenzen](.apm/skills/core-devops/references/habit-feedback.md).

## Dokumentationswerkzeuge

`skill-creator` ist ein Werkzeug für die Paketentwicklung. `context-debloater` ist eine separat bereitzustellende Inhaltsprüfmethode, die auch die Init-Ausgabe für erstellte oder inhaltlich bearbeitete Dateien verlangt; sie ist keine neue APM-Paketabhängigkeit und wird nicht automatisch installiert. Fehlt die Methode, meldet der bestehende Skillverfügbarkeitscheck die konkrete Prüflücke statt sie als installiert zu behaupten. Direkte Dateieingaben und automatische Skripte unterstützen nur Markdown; übrigen zugänglichen Text nach der geladenen Rubrik manuell beurteilen und Format-/Extraktionslücken ausdrücklich melden. Das ist keine universelle Formatgarantie; das Audit bleibt report-only.

## Lizenz

[MIT](LICENSE). Integrierte Komponenten enthalten ihre Herkunfts- und Lizenznachweise in den jeweiligen Paketquellen.

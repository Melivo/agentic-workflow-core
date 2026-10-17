# Agentic Workflow Core

[![CI](https://github.com/Melivo/agentic-workflow-core/actions/workflows/ci.yaml/badge.svg)](https://github.com/Melivo/agentic-workflow-core/actions/workflows/ci.yaml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Planen, kontrolliert umsetzen, unabhängig prüfen.**

Agentic Workflow Core ist ein portables Paket aus Agent-Skills für KI-gestützte Softwareentwicklung mit OpenCode und Codex. Ein unabhängiges Planreview prüft den Entwurf vor deiner Bestätigung; nach der Umsetzung prüft ein getrenntes Umsetzungsreview die integrierte Änderung. Entscheidungen, Fortschritt und Nachweise bleiben in nachvollziehbaren Dateien erhalten – nicht ausschließlich im Chatverlauf.

Core ist keine zusätzliche Orchestrierungs-CLI und kein autonomer Releasebot. Es nutzt die Fähigkeiten des jeweiligen Agent-Harnesses, also der Umgebung, in der der KI-Agent arbeitet. Du entscheidest über Ziel, Umfang und freizugebende Aktionen.

[Installation](#installation) · [Erste Verwendung](#erste-verwendung) · [Skills](#welche-skills-sind-enthalten) · [Qualitätsfeedback](#optionales-qualitätsfeedback) · [Entwicklung](#entwicklung-und-prüfungen)

## Was Core bietet

- **Einen durchgängigen Ablauf:** optionales Brainstorming, Planreview vor deiner Bestätigung, Umsetzung und unabhängiges Umsetzungsreview.
- **Passende Fachmethoden:** Architektur, Backend, Frontend, Mobile, Datenbanken, Terraform, Debugging und Refactoring.
- **Überprüfbare Übergaben:** Pläne, Task-Ergebnisse und Reviews mit festen Formaten.
- **Wiederaufnahme:** Arbeit anhand ihrer Artefakte in einer neuen Sitzung fortsetzen.
- **Klare Grenzen:** keine ungeplanten Umbauten, stillen Installationen oder automatisch freigegebenen Veröffentlichungen.
- **Gemeinsame Skills:** einmal installieren statt unnötiger Kopien für jedes Repository oder Harness.

Die kanonische Paketquelle liegt unter `.apm/`. Sie enthält **22 Core-Bundles** und den mitgelieferten `gortex-serena-configurator`. Es gibt **keine externe APM-Skillabhängigkeit und keinen erforderlichen Zugriff auf eine private Skillsammlung**.

## Installation

### Voraussetzungen

- [Microsoft Agent Package Manager (APM)](https://microsoft.github.io/apm/getting-started/installation/).
- Ein Harness, das gemeinsame Agent-Skills erkennt, etwa OpenCode oder Codex.
- Für die Repositoryarbeit: Gortex als primäre Code-Intelligence und bei Bedarf ein ausdrücklich eingerichteter, **projektspezifischer** Serena-Fallback.

MCP-Server, Modellanbieter und native Fachagenten sind getrennte Voraussetzungen. Die Skill-Installation richtet sie nicht automatisch ein.

### Global installieren

Installiere Core einmal im gemeinsamen Verzeichnis `~/.agents/skills/`:

```bash
apm install Melivo/agentic-workflow-core --global --target agent-skills --only apm
```

Vorab zeigt derselbe Befehl mit zusätzlichem `--dry-run` die geplanten Änderungen.

**Aktualisieren:**

```bash
apm install Melivo/agentic-workflow-core --global --target agent-skills --only apm --update
```

| Option | Wirkung |
| --- | --- |
| `--global` | Benutzerbereich statt des aktuellen Repositorys |
| `--target agent-skills` | gemeinsames Skill-Verzeichnis statt zusätzlicher Harness-Kopien |
| `--only apm` | APM-Pakete installieren; MCP-Konfiguration getrennt halten |

Setze auch im globalen Verbrauchsmanifest `~/.apm/apm.yml` `targets: [agent-skills]`, damit spätere Installationen bei diesem Ziel bleiben. APM hält aufgelöste Paketstände in `apm.lock.yaml` fest. Für reproduzierbare Stände kannst du die Quelle mit `#<commit-sha>` pinnen; ein Update überspringt einen solchen Pin nicht automatisch.

Unter APM 0.31 verwendet dieses Beispiel `install --update`, weil `apm update` keinen entsprechenden `--only apm`-Filter anbietet. Ein vorhandenes Release-Tag enthält nicht automatisch neuere Änderungen auf `main`.

### Optional: projektbezogene Harness-Integration

Für bewusst ausgewählte OpenCode-/Codex-Ziele im aktuellen Projekt:

```bash
apm install Melivo/agentic-workflow-core --target opencode,codex
```

Dieser Modus integriert auch die vorgesehenen Agentendefinitionen und kann Harness-Konfiguration erzeugen. Er ist kein notwendiger Zusatz zur globalen Skill-Installation. Generierte `.agents/`, `.opencode/` und `.codex/` werden nicht von Hand gepflegt.

## Erste Verwendung

Der normale Implementierungsablauf:

```text
core-brainstorm? → core-plan → Planreview → deine Freigabe → core-execute ↔ Umsetzungsreview → Abschluss
```

1. **Projekt prüfen:** `core-init-project` prüft Repository und Code-Intelligence-Bereitschaft. Änderungen an Providerkonfiguration oder `AGENTS.md` brauchen ihre eigene Freigabe.
2. **Ziel beschreiben:** gewünschtes Verhalten, betroffene Bereiche und Grenzen nennen. Bei materiellen Unklarheiten hilft `core-brainstorm`.
3. **Planreview und bestätigen:** `core-plan` erstellt einen `plan/v1` mit Aufgaben, Abhängigkeiten, Akzeptanzkriterien und Checks. `core-review` prüft den Entwurf in frischem Kontext als kurze Textantwort – ohne Run oder `review/v1`. Ein Review-pass macht ihn nur bestätigungsfähig; erst deine ausdrückliche Bestätigung erlaubt die Umsetzung.
4. **Umsetzen:** `core-execute` arbeitet den eindeutig identifizierten, bestätigten Plan ab und koordiniert passende Fachagenten.
5. **Unabhängig prüfen:** Danach bewertet `core-review` in frischem Kontext die integrierte Gesamtänderung. Das Umsetzungsreview bleibt read-only; Korrekturen gehören zurück in die Umsetzung, nicht in das Review.

Du kannst Skills in normaler Sprache anfordern; die Auswahl- oder Aufrufoberfläche hängt vom Harness ab. Beispiele:

> Nutze core-plan für die beschriebene Fehlerkorrektur. Erstelle zunächst nur den Plan und implementiere noch nichts.

> Der Plan unter dem genannten Pfad ist bestätigt. Nutze core-execute, um ihn innerhalb seines Scopes auszuführen.

> Nutze core-review für eine unabhängige Prüfung. Implementiere dabei keine Korrekturen.

**Scope und Freigabe:** Ein erlaubter Dateipfad ist keine Freigabe für beliebige zusätzliche Funktionen. Plan und Umsetzung bleiben am ursprünglichen Ziel und dessen Kriterien; Folgearbeit berücksichtigt den kumulativen Umfang. Bevorzugt wird die kleinste hinreichende Lösung. Build, Compile, Bundle, Packaging, Installation, Commit, Push, Tag, Release, Deployment und destruktive Aktionen benötigen jeweils eine passende ausdrückliche Autorisierung. Fachagenten arbeiten innerhalb ihres Taskscopes und starten keine eigenen Subagenten.

### Größere Vorhaben und Sitzungswechsel

Für einfache Vorhaben ist **keine zusätzliche Zielstruktur** nötig: Ein bestätigter Plan genügt. Nur bei ausdrücklich gewählter Etappenplanung verwaltet `core-milestone` Gesamtziel und Meilensteine; `core-handoff` erstellt den Übergabeprompt für eine neue Sitzung.

Definitionen sind versioniert und nach Bestätigung unveränderlich. Resume behält dieselbe Run-ID. Versionswechsel übernehmen weder alte Freigaben noch Abschlussnachweise automatisch. Details: [Artefaktvertrag](.apm/skills/core-shared/references/artifact-contract.md).

## Welche Skills sind enthalten?

| Bereich | Skills |
| --- | --- |
| Kernworkflow | [core-brainstorm](.apm/skills/core-brainstorm/SKILL.md), [core-plan](.apm/skills/core-plan/SKILL.md), [core-execute](.apm/skills/core-execute/SKILL.md), [core-review](.apm/skills/core-review/SKILL.md) |
| Fachliche Umsetzung | [Architektur](.apm/skills/core-architecture/SKILL.md), [Backend](.apm/skills/core-backend/SKILL.md), [Frontend](.apm/skills/core-frontend/SKILL.md), [Mobile](.apm/skills/core-mobile/SKILL.md), [Datenbanken](.apm/skills/core-database/SKILL.md), [Terraform](.apm/skills/core-tf-infra/SKILL.md) |
| Untersuchung und Pflege | [Research](.apm/skills/core-research/SKILL.md), [Debugging](.apm/skills/core-debug/SKILL.md), [Refactoring](.apm/skills/core-refactor/SKILL.md), [Repo-Audit](.apm/skills/core-repo-audit/SKILL.md), [Dokumentation](.apm/skills/core-docs/SKILL.md), [DevOps/SCM](.apm/skills/core-devops/SKILL.md) |
| Einrichtung | [core-init-project](.apm/skills/core-init-project/SKILL.md), [core-init-mcps](.apm/skills/core-init-mcps/SKILL.md), [core-user2agent-instructions](.apm/skills/core-user2agent-instructions/SKILL.md) |
| Etappen und Übergaben | [core-milestone](.apm/skills/core-milestone/SKILL.md), [core-handoff](.apm/skills/core-handoff/SKILL.md) |
| Gemeinsame Verträge | [core-shared](.apm/skills/core-shared/SKILL.md): interner Vertragsindex, kein zusätzlicher öffentlicher Workflow |
| Code-Intelligence | [gortex-serena-configurator](.apm/skills/gortex-serena-configurator/SKILL.md): Gortex zuerst, projektspezifisches Serena als Fallback, danach erlaubte native Werkzeuge |

Der Konfigurator enthält seine Skripte, Originaltests und MIT-Lizenz. Seine Skill-ID bleibt erhalten; ein globaler Serena-MCP wird nicht eingerichtet. Das optionale Konfigurationsskript benötigt Python und `ruamel.yaml` gemäß seinen [Anforderungen](.apm/skills/gortex-serena-configurator/REQUIREMENTS.md).

Die [SWE-Basis](.apm/skills/core-architecture/references/design-baseline.md) beschreibt den verbindlichen Sollzustand für Softwaredesign: klare Verantwortlichkeiten, hohe Kohäsion, Abstraktion und Information Hiding, stabile Verträge und begründete Kopplung. Die [Hintergrundreferenz](.apm/skills/core-architecture/references/principles-background.md) erläutert Herkunft und Grenzen. Vorhandene Projektarchitektur und begründete Ausnahmen bleiben maßgeblich; Core verlangt weder künstliche Abstraktionen noch ungeplante Umbauten.

## Optionales Qualitätsfeedback

[opencode-habit-feedback@0.1.0](https://www.npmjs.com/package/opencode-habit-feedback) ist als separates npm-Paket veröffentlicht. Es verbindet OpenCode V2 mit den **Original-Sensoren und dem Original-Mapper von Habit Hooks**. Für andere Core-Verbraucher ist das Plugin optional; die APM-Skill-Installation aktiviert es nicht automatisch.

Bei unterstützten Dateiänderungen hängt es passende Core-Coaching-Anweisungen an das Tool-Ergebnis an. Das Modell erhält diese Hinweise dort, nicht als zusätzliche Benutzernachricht. Installation, Werkzeugbindung und Registrierung als OpenCode-V2-Eintrag `{package, options}` im `plugins`-Array sind eigene Einrichtungsschritte. Bestehende Plugins bleiben erhalten; der Laufzeit-Hook installiert nichts.

**Grenzen:**

- Qualifiziert ist der Linux-Einzeldatei-Pfad mit Python-/generischen Sensoren und Ruff; Versionen stehen in [VERSIONS.md](.apm/skills/core-devops/assets/opencode-habit-feedback/VERSIONS.md).
- Repositoryweite Sensoren wie jscpd und deptry werden im automatischen Dateihook vor dem Start ausgeschlossen.
- Nicht unterstützte Toolformen, deaktivierte Sensoren und nicht qualifizierte Sensor-Scopes erscheinen als `not_scanned`, nicht als falsches „alles sauber“.
- Tool-Ausgaben sind keine Benutzeranweisungen und autorisieren weder neue Tasks noch zusätzliche Wirkungen.
- Statische Checks und kontrollierte Hosttests belegen keine zuverlässige Befolgung durch ein Sprachmodell und keinen allgemeinen Qualitätsgewinn.

[Technische Optionen, Sicherheitsgrenzen und Prüfkommandos](.apm/skills/core-devops/references/habit-feedback.md).

## Entwicklung und Prüfungen

```text
.apm/skills/       Kanonische Skills, Methoden, Verträge und Ressourcen
.apm/agents/       Native Fachagentenprofile
scripts/          Prüfungen, Toolchain und Paket-/Releasewerkzeuge
tests/            Vertrags-, Sicherheits- und Integrationstests
.github/workflows/ CI und getrennte Releasekette
DESIGN.md         Detaillierte Architektur und Workflowverträge
```

Core-Skills liegen unter `.apm/skills/core-<name>/`; der quelltreu migrierte Begleitskill unter `.apm/skills/gortex-serena-configurator/`. Ordnername und Frontmatter-`name` stimmen überein. `.agentic-workflow/` enthält lokale Pläne und Run-Artefakte und wird in diesem Repository von Git ignoriert. Bestätigte Pläne werden nicht mit Laufstatus überschrieben.

### Lokale Prüfungen und Paketabnahme

Die lokalen und CI-Aufgaben verwenden `mise` 2026.10.11 und Python 3.13.14. Weitere Versionen und Integritätswerte: [ci_toolchain.json](scripts/ci_toolchain.json), [requirements-ci.txt](scripts/requirements-ci.txt) und [Habit-Testtoolchain](scripts/habit-ci/package.json).

```bash
# Einmaliges, ausdrücklich freigegebenes Setup im isolierten Arbeitsbereich
mise run tools:setup

# Prüfungen ohne automatische Installation
mise run check
mise run version:check
mise run release:test
mise run workflows:check
mise run docs:check
```

`tools:setup` lädt und installiert gepinnte Werkzeuge ausschließlich in den isolierten Arbeitsbereich. Die Prüftasks installieren nichts automatisch. Die qualifizierte Entwicklungs- und CI-Laufzeit ist Linux x64; daraus folgt keine universelle Betriebssystemfreigabe.

Die vollständige Abnahme `mise run acceptance` führt diese Prüfungen zusammen und baut zusätzlich ein Paket, das sie in einem frischen Scratch-Verbraucher installiert und kontrolliert. Sie hat daher ausdrückliche Paket- und Installationswirkung. Geprüft werden Quellen, Lizenzhinweise, alle Core-Bundles, der vollständige Konfigurator und relative Links. Ein Exitcode allein genügt nicht; temporäre Reports ersetzen keine dauerhaft gesicherten Ausführungsnachweise.

### Installierbares Bundle erzeugen

Nutze nach freigegebenem Werkzeugsetup den geprüften Producer aus einem sauberen Checkout dieses Repositories:

```bash
python3 -B scripts/build_core_package.py verify --output /tmp/opencode/core-package
```

Der Befehl baut und prüft ein ZIP isoliert und installiert es zur Abnahme in einem frischen Verbraucher. Nicht aus einem Verbrauchsprojekt mit dessen `apm_modules`-Cache packen: Sonst können nicht portable Cache-Verweise im Bundle bleiben.

Ein geprüftes lokales ZIP lässt sich anschließend separat installieren:

```bash
apm install /path/to/agentic-workflow-core-X.Y.Z.zip --global --target agent-skills
```

Bei lokalen Bundles ist `--only apm` nicht erlaubt. Für manuelles Packen mit APM 0.31/0.33 bleibt `--target agent-skills` ausdrücklich gesetzt: Das Standardziel `minimal` kann dort eine nicht installierbare Ausgabe erzeugen. Der Producer verwendet das geprüfte Plugin-Bundle-Format, nicht `--format apm`.

### GitHub-CI und Releasefreigabe

[CI](.github/workflows/ci.yaml) prüft Pull Requests und Pushes auf `main` über dieselben Tasks wie lokal. Sie braucht keine private Skill-Abhängigkeit, erhält nur lesende Repositoryrechte und keine Veröffentlichungssecrets.

Die getrennte [Releasekette](.github/workflows/release.yaml) ist standardmäßig deaktiviert: `RELEASE_PR_AUTOMATION_ENABLED` und `RELEASE_PUBLICATION_ENABLED` müssen für ihre jeweiligen Wirkungen exakt `true` sein. Release Please darf einen Release-PR vorschlagen; es gibt kein automatisches Merge. Veröffentlichung setzt einen bewusst gemergten, geprüften Release-PR und die Bedingungen in [release_guard.py](scripts/release_guard.py) voraus. Ein normaler Push ist keine Releasefreigabe.

Versionsregel für 0.x: Fehlerkorrektur → Patch; neue Funktion oder inkompatible Änderung → Minor. Der Wechsel auf `1.0.0` braucht eine gesonderte Entscheidung. Fehlgeschlagene, fehlende oder laufende Checks blockieren die Veröffentlichung; bestehende Tags und Assets werden nicht beiläufig überschrieben. App-Authentifizierung und Branchschutz sind vom Betreiber separat einzurichten.

## Weiterführende Dokumentation

- [Design und Architektur](DESIGN.md)
- [Workflowvertrag: Autorisierung, Scope und Übergaben](.apm/skills/core-shared/references/workflow-contract.md)
- [Artefaktvertrag: Pläne, Runs, Reviews und Resume](.apm/skills/core-shared/references/artifact-contract.md)
- [Toolrouting: Providerreihenfolge und Fallbacks](.apm/skills/core-shared/references/tool-routing.md)
- [Verifikation: Nachweise und unabhängiges Review](.apm/skills/core-shared/references/verification.md)
- [Versionshistorie](CHANGELOG.md)

`skill-creator` und `context-debloater` sind Werkzeuge für die Paketentwicklung, keine zusätzlichen Verbraucherabhängigkeiten. Native Fachagenten werden über die Profile des Harnesses genutzt; eine zusätzliche Orchestrierungs-CLI ist nicht vorgesehen.

## Lizenz

[MIT](LICENSE). Der Konfigurator enthält seine eigene [MIT-Lizenz](.apm/skills/gortex-serena-configurator/LICENSE) und [Herkunftsdokumentation](.apm/skills/gortex-serena-configurator/PROVENANCE.md). Hinweise auf adaptierte Architekturmethoden stehen in [THIRD_PARTY_NOTICES.md](.apm/skills/core-architecture/THIRD_PARTY_NOTICES.md).

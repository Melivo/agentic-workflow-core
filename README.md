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

## Lokale Prüfungen und Paketabnahme

Die wiederholbaren lokalen und CI-Einstiegspunkte verwenden `mise` 2026.10.6. `mise run tools:setup` lädt und installiert die geprüften Werkzeuge — Python 3.13.14, Node.js 22.23.3, PyYAML 6.0.3, APM 0.31.0, Release Please 17.11.2, actionlint 1.7.12 und ShellCheck 0.11.0 — ausschließlich in den isolierten Projektarbeitsbereich. Der Setup-Schritt verändert weder globale Werkzeuge noch die Quellen. Er muss vor den Prüfungen ausdrücklich gestartet werden; die Prüftasks installieren nichts automatisch.

```bash
mise run tools:setup
mise run check
mise run version:check
mise run release:test
mise run workflows:check
mise run docs:check
```

`check`, `version:check`, `release:test`, `workflows:check` und `docs:check` sind Prüfungen ohne Paketinstallation. `mise run acceptance` führt diese Abnahmen zusammen und schließt mit `scripts/build_core_package.py verify` ab: Der Producer baut das ZIP isoliert, anschließend wird es in einem frischen Scratch-Verbraucher installiert und verifiziert. Diese Abnahme hat daher ausdrücklich Paket- und Installationswirkung innerhalb der temporären Arbeitsbereiche. Reports und Archive dort sind temporär. Bei einer bestätigten Ausführung hält `core-execute` die vollständigen Originalausgaben sowie die benötigten Paket-/Archivnachweise dauerhaft im Runverzeichnis fest; ein `/tmp`-Pfad allein ist kein dauerhafter Beleg. Die geprüfte Laufzeit ist Linux x64 und belegt keine universelle plattformübergreifende Laufzeit.

## GitHub-CI und Releasefreigabe

Die normale CI läuft für Pull Requests und Pushes auf `main` mit nur lesendem `GITHUB_TOKEN`; sie erhält weder den App-Schlüssel noch Veröffentlichungsrechte. Die Releasekette ist getrennt und standardmäßig aus: Die Repositoryvariablen `RELEASE_PR_AUTOMATION_ENABLED` und `RELEASE_PUBLICATION_ENABLED` müssen jeweils exakt `true` sein. Fehlend oder anders geschrieben bleiben sie aus. Eine Einrichtung oder ein gesetztes Gate allein startet keine Freigabe durch diesen Leitfaden.

Vor einer späteren Aktivierung richtet ein Administrator die gemeinsame GitHub App einmal ein und installiert sie nur für dieses Repository. Die Workflowdatei verlangt die Repositoryvariablen `APP_CLIENT_ID`, `RELEASE_BOT_LOGIN`, `RELEASE_MAINTAINERS` und `RELEASE_REQUIRED_CHECKS`; der private App-Schlüssel wird vom Benutzer als Repositorysecret `APP_PRIVATE_KEY` hinterlegt. Die App benötigt nur die verwendeten Repositoryrechte: `contents` zum Lesen/Schreiben von Releaseinhalten, `pull requests` zum Erstellen/Lesen des Release-PR und `issues` für Release-Please-Labels; `checks: read` wird für die Veröffentlichungsprüfung benötigt. Normale CI bekommt diese App-Rechte nicht. Erforderliche Statusprüfungen und Branchschutzregeln werden repositoryseitig eingerichtet; Bot-Bypass ist nicht vorgesehen. Der Releasebot darf nicht zugleich ein freigegebener Maintainer sein. Schlüsselrotation ist eine manuelle App-/GitHub-Secretpflege; sie ist getrennt von den kurzlebigen App-Tokens, die erst unmittelbar vor den jeweiligen Providerzugriffen repo-begrenzt angefordert und am Jobende widerrufen werden.

Die Kette reagiert nur auf erfolgreiche CI-Pushes dieses Repositories auf `main`. Release Please darf einen Release-PR öffnen oder aktualisieren, aber erzeugt dabei keine Tags oder Releases. Veröffentlichung wartet auf einen bewusst von einem konfigurierten Maintainer gemergten Release-PR, passende Pflichtchecks auf den exakten Commits und die erfolgreiche Paketabnahme des Merge-Commits. Es gibt kein automatisches Merge. Versionsentscheidungen folgen im 0.x-Bereich: Fix → Patch, neue Funktion oder inkompatible Änderung → Minor; bei gemischten Änderungen gilt der höchste Sprung. Der Wechsel zu `1.0.0` benötigt eine gesonderte Entscheidung.

Bei Fehlern, fehlenden oder laufenden Prüfungen, Versions-/Commitkonflikten oder einem unvollständigen Paket wird gestoppt. Bereits vorhandene Tags oder Assets werden nicht gelöscht oder überschrieben; identische, vollständig geprüfte Ergebnisse sind idempotent, abweichende Teilzustände erfordern manuelle Klärung. Das Paketarchiv des Workflows wird nur einen Tag aufbewahrt; für einen Retry daher nicht auf ein altes Archiv vertrauen. Wenn der ursprüngliche Release-Workflowlauf vorhanden ist, innerhalb von 30 Tagen liegt und sein Quell-SHA weiterhin der beabsichtigte Commit ist, den vollständigen Lauf erneut ausführen — in der GitHub-Oberfläche **Re-run all jobs** oder mit der exakten Run-ID `gh run rerun <run-id>` (ohne `--failed`). GitHub verwendet dabei denselben ursprünglichen `GITHUB_SHA`/`GITHUB_REF`; Jobs bauen das Paket neu, prüfen die aktuellen Freigabegates erneut und minten benötigte Tokens frisch. GitHub erlaubt höchstens 50 Wiederholungen pro Workflowlauf und verwendet die Berechtigungen des ursprünglichen Auslösers. Ein Retry von Release prüft nicht rückwirkend einen anderen Commit: Der `release-pr`-Job überspringt die Wirkung, wenn der Quell-Commit nicht mehr der aktuelle `main`-Tip ist. In diesem Fall den passenden aktuellen erfolgreichen CI-Push-/Release-Lauf verwenden, nicht einen manuellen `workflow_dispatch` oder einen Teiljobretry als Ersatz.

GitHub garantiert in einer Concurrency-Gruppe mit `cancel-in-progress: false` nicht, dass mehrere wartende Läufe erhalten bleiben: ein neuer wartender Lauf kann den älteren wartenden verdrängen. Existiert für die gewünschte Quelle kein verwendbarer Original-Release-Lauf, ist das ein Blocker; erst eine separat freigegebene Codeänderung oder ein neuer regulärer CI-Push kann einen neuen Lauf erzeugen. Der vollständige Retry ist ein externer GitHub-Aktionseffekt und muss ausdrücklich autorisiert werden. Diese Konfiguration wurde lokal/offline geprüft; Live-CI, App-Authentifizierung, Repositoryvariablen/-secrets, Branchschutz und Veröffentlichung sind damit nicht live bestätigt. Sie müssen später repositoryseitig durch den Benutzer beziehungsweise Administrator eingerichtet und geprüft werden.

## Installierbares Bundle erzeugen

Packe aus einem sauberen **Producer-Checkout dieses Repositories**, nicht aus einem Verbrauchsprojekt, das Core als Abhängigkeit installiert hat. APM 0.31 kann in einem Verbraucher-Bundle auf dessen nicht mitgelieferten `apm_modules`-Cache verweisende Links behalten.

```bash
# In einer separaten Producer-Arbeitskopie; nicht im Benutzerprofil.
# Alle deklarierten Producer-Ziele für einen konsistenten Audit vorbereiten.
apm install --only apm
apm audit --ci
apm pack --offline --target agent-skills --output ./dist
# In einem separaten Verbrauchsverzeichnis:
apm install /path/to/dist/agentic-workflow-core-X.Y.Z --target agent-skills
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

Die Fachmethoden [`core-architecture`](.apm/skills/core-architecture/SKILL.md), [`core-backend`](.apm/skills/core-backend/SKILL.md), [`core-database`](.apm/skills/core-database/SKILL.md), [`core-debug`](.apm/skills/core-debug/SKILL.md), [`core-docs`](.apm/skills/core-docs/SKILL.md), [`core-frontend`](.apm/skills/core-frontend/SKILL.md), [`core-mobile`](.apm/skills/core-mobile/SKILL.md), [`core-refactor`](.apm/skills/core-refactor/SKILL.md), [`core-repo-audit`](.apm/skills/core-repo-audit/SKILL.md), [`core-research`](.apm/skills/core-research/SKILL.md) und [`core-tf-infra`](.apm/skills/core-tf-infra/SKILL.md) werden nur innerhalb ihres bestätigten Scopes verwendet. Einrichtung und Pflege übernehmen [`core-init-mcps`](.apm/skills/core-init-mcps/SKILL.md), [`core-init-project`](.apm/skills/core-init-project/SKILL.md) und [`core-user2agent-instructions`](.apm/skills/core-user2agent-instructions/SKILL.md). Für ausdrücklich etappenbasierte Vorhaben besitzt [`core-milestone`](.apm/skills/core-milestone/SKILL.md) Ziel, unveränderliche Definitionen und den aktualisierbaren Auswahl-/Nachweisindex; [`core-handoff`](.apm/skills/core-handoff/SKILL.md) unterstützt autorisierte Sitzungs- und Etappenübergaben, ohne selbst Status zu verwalten. Diese unterstützenden Skills schaffen keinen alternativen Kernlebenszyklus. Eigenständige, klar benannte Git-/Releaseaufträge übernimmt [`core-devops`](.apm/skills/core-devops/SKILL.md) nach ausdrücklicher Freigabe, ohne dass dafür ein Implementierungsplan nötig ist. Geplante Automationseinrichtung gehört dagegen in einen bestätigten Task über `core-plan`/`core-execute`. Releases nach Codeänderungen folgen erst auf ein bestandenes Review.

Das interne Bundle [`core-shared`](.apm/skills/core-shared/SKILL.md) bündelt die kanonischen [Workflow-](.apm/skills/core-shared/references/workflow-contract.md), [Artefakt-](.apm/skills/core-shared/references/artifact-contract.md), [Toolrouting-](.apm/skills/core-shared/references/tool-routing.md) und [Verifikationsverträge](.apm/skills/core-shared/references/verification.md). Diese Verweise zeigen ausschließlich auf versionierte Paketartefakte unter `.apm/`.

## Optionale Habit-Feedback-Integration

`core-devops` dokumentiert eine optionale Habit-Hooks-Integration mit den Original-Sensoren und dem Original-Mapper. Das geprüfte Paket `opencode-habit-feedback@0.1.0` ist noch nicht veröffentlicht; globale Benutzerinstallation und Aktivierung sind noch nicht erfolgt. Andere Core-Verbraucher nutzen die Integration freiwillig. Nach Veröffentlichung und ausdrücklicher Freigabe wird es als additiver OpenCode-V2-Eintrag `{package, options}` im bestehenden globalen `plugins`-Array eingerichtet; alle vorhandenen Plugin-Einträge bleiben erhalten. Die Optionswerte binden nur die jeweiligen Child-Prozesse und erfordern keine persönliche Shell-/Login-Umgebungsänderung. Installation/Registrierung sind getrennte Benutzeraktionen; der Laufzeit-Hook installiert nichts.

Für den automatischen Einzeldatei-Hook sind Python-/generische Dateisensoren mit ruff qualifiziert. jscpd und deptry werden vor dem Spawn deaktiviert, weil kein Einzeldatei-Scope belegt ist; ihre Versionspins gelten nur für getrennte, ausdrücklich autorisierte Repository-Scans. Auch erlaubte deaktivierte Ruff-/line-count-Sensoren und nicht-None-`files`-Overrides werden als `not_scanned` ausgewiesen; Overrides bleiben ohne qualifizierten Messbeleg konservativ ungeprüft, ohne Sensorpräferenzen zu überschreiben oder einen eigenen Matcher einzuführen. Gültige Findings und Originalmapper-Coaching der tatsächlich gemessenen Teilmenge, einschließlich Advisory-Coaching, bleiben sichtbar; ungemessene Abdeckung wird weder als clean noch als complete dargestellt. Die isolierte Hostqualifikation umfasst 110 Fälle, darunter alle 90 zuvor geprüften Fälle und 20 RV06-Fälle; sie ist keine Garantie für allgemeine LLM-Beobachtungsqualität. Das verspricht weder alle Sprachen noch Vollabdeckung oder Aktivierung in jedem Repository; eine repositoryseitige Deaktivierung wird sichtbar gemeldet. Andere Core-Verbraucher nutzen die Integration freiwillig. Die [Habit-Feedback-Nutzungsreferenz](.apm/skills/core-devops/references/habit-feedback.md) enthält das genaue JSONC-Optionsobjekt, Grenzen und Prüfkommandos.

## Ziele und versionierte Etappen

Eine einfache Änderung braucht kein Zielartefakt und keine Etappenstruktur: ein bestätigter `plan/v1` genügt. Nur ausdrücklich gewählte mehrstufige Vorhaben verwenden die getrennten Formate `goal/v1`, `milestone-definition/v1` und `milestone-index/v1`. `core-milestone` besitzt `.agentic-workflow/goals/G01/goal.md`, die unveränderlichen Definitionen unter `milestones/` und `index.yaml`; der Index hält die ausdrücklich bestätigte Auswahl und exakte Plan-, Run- und Abschlussverweise, nicht einen zweiten Aufgabenstatus. Die kanonischen [Ziel-](.apm/skills/core-milestone/references/goal-format.md), [Definitions-](.apm/skills/core-milestone/references/milestone-format.md) und [Indexformate](.apm/skills/core-milestone/references/milestone-index-format.md) bestimmen Details.

Beispiel: `.agentic-workflow/goals/G01/milestones/M02-v1.yaml` bleibt nach Bestätigung unverändert. Eine inhaltliche Änderung erzeugt nach Prüfung und ausdrücklicher Bestätigung `M02-v2.yaml`; erst eine ebenfalls bestätigte Indexauswahl macht diese Fassung aktuell. Ein gepinnter Plan wie `plan-G01-M02-v1-p01.md` bleibt an v1 gebunden. Ein Ersatzplan für v2 wird `plan-G01-M02-v2-p01.md` (oder `p02` als Ersatz derselben Fassung); Namen ersetzen keine exakten Pfadbezüge oder Freigaben. Ein eigenständiger neuer Lauf erhält eine neue Run-ID, z. B. `run-G01-M02-v2-p01-r01/`; Resume und Review-Reparaturen behalten dieselbe Run-ID. Taskversuche sind getrennte, unveränderliche Nachweise wie `tasks/T01/attempt-01.yaml`.

Versionswechsel übertragen weder Planbindung noch Erfolg: historische Abschlussnachweise bleiben an v1, und ihre Wiederverwendung für v2 verlangt eine ausdrückliche Prüfung gegen neue Kriterien und Abhängigkeiten. Abhängige Etappen bleiben bei alten Versionsbezügen blockiert, bis passende Ersatzdefinitionen bestätigt sind. Eine höhere Versionsdatei wird nicht automatisch ausgewählt; eine neue Version erteilt keine Folgefreigabe. Das frühere `milestone/v1` ist nur über seinen ausdrücklich benannten Pfad lesbar, ohne automatische Migration oder Vermischung. Beim Handoff werden Ziel-, Index-, Definitions-, Plan- und anwendbare Runpfade geprüft; der Prompt selbst erteilt keine Freigabe.

## Interne Designmethoden und aktuelle MCP-Fähigkeiten

Die [SWE-Basis und situative Auswahl](.apm/skills/core-architecture/references/design-baseline.md) bündelt klare Verantwortlichkeiten, stabile Schnittstellen, Information Hiding, begründete Abhängigkeiten und Testbarkeit. `core-plan` wendet S00 bei Coding-Vorhaben bereits auf Lösungswahl, Taskgrenzen und überprüfbare Akzeptanz-/Checkabdeckung an; `core-execute` übergibt die Referenz an den zuständigen Fachskill. Coding-Skills wenden sie vor der ersten Codeänderung auf den bestätigten, betroffenen Bereich an und belegen die Abschlussprüfung in den vorhandenen Ergebnisfeldern. Clairvoyance-Methoden sind intern konsolidiert und werden nur bei konkreten Signalen vertieft, nicht als obligatorischer Komplettscan. Ihr Laden startet keinen Architekturworkflow und erlaubt keine ungeplanten Refactorings.

Die fünf Prinzipien sind in S00 ein verbindlicher Sollzustand: Austauschbarkeit bedeutet, eine vertragskonforme Alternative bei stabilem Vertrag ohne Anpassung unabhängiger Verbraucher einzusetzen, und bedeutsame Werte liegen als benannte Konstante beim verantwortlichen Eigentümer. Die Grundlage gilt übergreifend für Code, Tools, Pakete, Einrichtung und Automation, auch in Planung und Ausführung; reine Informations- oder Bereitschaftsprüfungen lösen keine Installation, Änderung oder Vollscans aus. Die ausführliche [Hintergrundreferenz](.apm/skills/core-architecture/references/principles-background.md) erklärt Herkunft, Prinzipienbild und Nachweisgrenzen und wird nur bei Auslegungsbedarf geladen. Statische Checks und kontrollierte Beispieltests belegen kein Verhalten eines Agenten oder Sprachmodells. Die optionale Habit-Feedback-Integration ist eine getrennt geprüfte Ergänzung; ihr Paket ist noch nicht veröffentlicht und global nicht aktiviert. Sie ändert weder die hier beschriebenen Workflowgrenzen noch begründet sie eine Pflichtabhängigkeit.

Die [Provenienz](.apm/skills/core-architecture/PROVENANCE.md) dokumentiert alle 16 Quellskills; der [MIT-Hinweis](.apm/skills/core-architecture/THIRD_PARTY_NOTICES.md) begleitet die Adaptionen. Separat installierte Clairvoyance- oder SWE-Skills sind nicht erforderlich. Der private UNLICENSED-SWE-Skill wurde nicht übernommen.

Das [Toolrouting](.apm/skills/core-shared/references/tool-routing.md) nutzt geeignete aktuell verfügbare MCP-Fähigkeiten anhand konkreten Bedarfs und gezielter Discovery. Providerpriorität, Projektscope, Freshness, Autorisierung und erlaubte Fallbacks bleiben maßgeblich; Verfügbarkeit autorisiert keine Nebenwirkungen.

## Lizenz

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE).

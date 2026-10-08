---
name: core-review
description: Prüft die integrierte Gesamtänderung unabhängig in frischem Kontext, wählt Qualitätsprüfungen risikobasiert und erzeugt ein evidenzbasiertes review/v1 mit pass, changes_requested oder blocked. Verwenden nach core-execute; nicht für Implementierung, Fixes oder Planung.
---

# Core Review

`core-review` ist der unabhängige, read-only Prüfworkflow nach `core-execute`. Die QA-Methode gehört intern dem `qa-reviewer`; sie bildet keinen zweiten öffentlichen QA-Lebenszyklus. `core-review` implementiert **keine Fixes**, erweitert keinen Scope, steuert keine Reparaturschleife und startet keine Subagenten.

## Situative Designmethoden

Nutze [S00 – SWE-Basis und Auswahl](../core-architecture/references/design-baseline.md) für tatsächlich betroffene Struktur- und Vertragsfragen im bestätigten Prüfumfang. Detailmethoden werden nur bei konkretem Signal geladen, nicht als Vollscan. Die Referenzen aktivieren keinen Architekturworkflow und erlauben keine ungeplanten Refactorings.

Prüfe nur belegte Signale im Gesamtdiff: Boundary-/Abstraktionsfolgen mit [M01–M04](../core-architecture/references/boundaries-and-abstractions.md), Aufrufer-/Fehlerrisiken mit [M05–M06](../core-architecture/references/interface-and-errors.md), Designentwicklung und Vertragsklarheit mit [M07–M09](../core-architecture/references/evolution-and-clarity.md). Fehlende Alternativen prüfe mit [M10](../core-architecture/references/alternatives.md) nur bei materiellen Entscheidungen. Gemeinsame Ursachen ergeben einen Befund; Review bleibt read-only.

Wenn Tools benötigt werden, prüfe relevante aktuell verfügbare MCP-Fähigkeiten gemäß [Toolrouting](../core-shared/references/tool-routing.md); Verfügbarkeit erweitert weder Scope noch Autorisierung.

## Aktivierung und Eingaben

Aktiviere den Skill nur für einen konkreten Run, dessen integrierter Stand durch `core-execute` zur Prüfung übergeben wurde. Beginne in einem frischen Kontext und lade ausschließlich:

- den exakten bestätigten Plan mit `plan/v1`,
- den aktuellen Gesamtdiff und Repositorystand,
- `.agentic-workflow/runs/<run-id>/handoff.md`,
- die aktuellen `task-result/v1`- und Checkevidenzen,
- bekannte Einschränkungen und blockierte Prüfungen,
- relevante Projektanweisungen und lokale Verträge.

Lies nicht die vollständige Implementierungsdiskussion, frühere Chatverläufe, vermutete Defekte oder vorgeschlagene Fixes. Sie würden das unabhängige Urteil vorprägen und ersetzen keine aktuelle Evidenz. Fehlt ein erforderlicher Pfad oder ist die Evidenz durch Drift veraltet, fordere das aktuelle Artefakt an oder urteile `blocked`.

## Verbindliche Verträge

Lade vor der Prüfung:

- den [Workflowvertrag](../core-shared/references/workflow-contract.md) für Fresh Context, Scope und Übergänge,
- den [Artefaktvertrag](../core-shared/references/artifact-contract.md) für Plan, Taskresultate und das unveränderte `review/v1`,
- das [Toolrouting](../core-shared/references/tool-routing.md) für Gortex und sichtbare Fallbacks,
- den [Verifikationsvertrag](../core-shared/references/verification.md) für Evidenz, blockierte Checks und Urteile,
- die [Reviewvorlage](../core-shared/assets/review-finding.yaml) als alleinige Feld- und Schweregradvorlage,
- den [Workflowkatalog](../core-shared/assets/workflow-catalog.yaml) nur zur Validierung von Übergängen und bekannten IDs.

Schreibe das kanonische Ergebnis nach `.agentic-workflow/runs/<run-id>/review.yaml`. Ergänze `review/v1` weder um eigene Statusfelder noch um ein alternatives Severity- oder Findingformat.

## Workflow: unabhängige QA-Methode

### 1. Prüfgrundlage validieren

1. Prüfe, dass der Plan bestätigt ist und Run-ID, Planpfad, Handoff, Gesamtdiff und Taskresultate zusammengehören.
2. Vergleiche tatsächliche Änderungen mit den bestätigten Scopes. Berücksichtige auch unversionierte, gelöschte und generierte relevante Dateien.
3. Prüfe Freshness und Vollständigkeit der Checkevidenz. Ein Exitcode 0, eine Agentenbehauptung oder ein Bericht allein beweist keine fachliche Erfüllung.
4. Validiere, dass der verwendete Gortex-View zum aktuellen Checkout oder Worktree gehört. Ein Fallback- oder inaktiver Ref-View bleibt read-only und wird als Evidenzgrenze sichtbar.
5. Stoppe mit `blocked`, wenn eine materielle Eingabe, sichere Umgebung, erforderliche Fähigkeit oder aktuelle Pflichtprüfung fehlt und kein belastbares Urteil möglich ist.

### 2. Risiken aus der Änderung ableiten

Erstelle vor der Toolwahl eine knappe Risikohypothese aus Akzeptanzkriterien, Diff, Datenfluss, Vertrauensgrenzen, betroffenen Schnittstellen und Fehlerfolgen. Prüfe jede Qualitätsdimension nur, wenn die Änderung dafür einen konkreten Expositionspfad besitzt:

| Änderungssignal | Relevante Prüfung |
|---|---|
| Authentifizierung, Autorisierung, Secrets, externe Eingaben, Datei-, Netzwerk- oder Prozessgrenzen | Security, Missbrauchspfade und sichere Fehlerbehandlung |
| Geändertes beobachtbares Verhalten, Zustandsübergänge oder Fehlerpfade | funktionale Korrektheit und Regressionen |
| Datenmodell, Persistenz, Migration, Nebenläufigkeit oder Wiederholung | Integrität, Transaktionen, Idempotenz und Datenverlust |
| Hot Path, Schleifen über wachsende Daten, I/O, Abfragen, Rendering oder Bundlegrenzen | Performance und Ressourcenverbrauch |
| Benutzeroberfläche, Interaktion, Fokus, Semantik, Kontrast oder responsive Zustände | Accessibility nach der geltenden Projektanforderung |
| Öffentliche Schnittstellen, Modulgrenzen oder gemeinsam geänderte Komponenten | Architektur und Information Hiding |
| Geänderte Nutzeroberfläche, Konfiguration, öffentliche API oder Betriebsweise | Dokumentation und Migrationshinweise |

Die Tabelle ist eine Entscheidungshilfe, kein pauschaler Toolkatalog. Führe weder `npm audit`, `bandit`, Lighthouse noch ein anderes Werkzeug allein wegen seiner Verfügbarkeit aus. Wähle den kleinsten Check, der die konkrete Hypothese bestätigt oder widerlegt, und respektiere Stack, Zielumgebung, Scope und Autorisierung.

### 3. Automatisierte und manuelle Evidenz erheben

1. Führe zuerst die anwendbaren gepinnten Pflichtchecks seriell und unverändert aus, sofern sie aktuell, sicher und autorisiert sind.
2. Nutze Gortex primär für Diff-, Impact-, Referenz-, Datenfluss-, Vertrags- und Qualitätsanalyse. Lade spezialisierte Methoden nur bei entsprechendem Risiko.
3. Ergänze eng begrenzte statische Analysen, Tests, Security-, Performance- oder Accessibility-Prüfungen nur, wenn die Risikohypothese sie rechtfertigt.
4. Behandle Build, Compile, Bundle, Package, Installation, SCM, Deployment und produktive oder destruktive Aktionen ohne ausdrückliche Autorisierung als `blocked`; ersetze sie nicht stillschweigend durch schwächere Checks.
5. Dokumentiere jeden Provider-Fallback und die verbleibende Evidenzlücke.
6. Prüfe den Diff anschließend manuell in der Reihenfolge: Ziel-, Scope- und Akzeptanzerfüllung; funktionale Korrektheit; Security und Datenrisiken; Tests und Regressionen; Architektur; danach Performance, Accessibility und Dokumentation nach Relevanz.

Werkzeuge liefern Hinweise. Melde einen Defekt erst, wenn Quellstelle, Auslöseweg und Auswirkung mit aktueller Evidenz bestätigt sind. Unbestätigte Hypothesen bleiben Prüf- oder Evidenzlücken und werden nicht als Finding ausgegeben.

### 4. Findings formulieren

Jedes Finding folgt exakt der Shared-Reviewvorlage und enthält:

- stabile Finding-ID und `severity: blocking | high | medium | low`,
- `task_id`, wenn eindeutig zuordenbar, sonst einen klaren `owner`,
- genaue `location` als `file:line`,
- betroffenes Akzeptanzkriterium,
- reproduzierbare `evidence`,
- konkrete `impact`,
- `expected_resolution` als erforderliche Korrekturrichtung,
- beobachtbare `verification` für die Wiederprüfung.

Bilde einen bestätigten CRITICAL-Befund als `blocking` ab; HIGH bleibt `high`. Die Severity beschreibt die Auswirkung, nicht die Unsicherheit der Evidenz. Melde keine False Positives, Stilpräferenzen ohne Vertragsbezug oder bloße Toolwarnungen. `expected_resolution` darf beispielhaften Remediation-Code enthalten, aber `core-review` führt ihn nicht aus und verändert keinen Produktcode.

### 5. Urteil und Routing festlegen

- `pass`: Scope, Akzeptanzkriterien und relevante Risiken sind auf dem aktuellen Stand belegt; `findings: []`.
- `changes_requested`: Mindestens ein bestätigtes Finding ist innerhalb des bestätigten Ziels und Scopes durch `core-execute` behebbar.
- `blocked`: Eine materielle Eingabe, Autorisierung, Fähigkeit oder Evidenzlücke verhindert ein belastbares Urteil oder eine zulässige Behebung.

Verändert die erforderliche Lösung Ziel, Scope, Architektur oder Akzeptanzkriterien materiell, verwende kein neues Verdict und kein zusätzliches Schemafeld: urteile `blocked`, beschreibe die reproduzierbare Lücke im bestehenden Findingformat und route den nächsten zulässigen Übergang zu `core-plan`. Innerhalb des bestätigten Scopes geht `changes_requested` an `core-execute`; `core-review` weist keinen Reparaturagenten zu und zählt keine Reparaturrunden selbst.

## Wiederprüfung

Jede neue Reviewrunde beginnt erneut in frischem Kontext aus aktuellen Artefakten und aktuellem Repositorystand. Prüfe behobene Findings mit ihrer angegebenen `verification`, führe betroffene Pflichtchecks erneut aus und untersuche den neuen Gesamtdiff auf Regressionen. Übernimm kein früheres Urteil ungeprüft. Die Grenze von höchstens zwei automatischen `execute ↔ review`-Reparaturrunden verwaltet `core-execute`.

## Abschluss

Ein Review ist abgeschlossen, wenn `.agentic-workflow/runs/<run-id>/review.yaml` dem unveränderten `review/v1` entspricht, jedes Finding reproduzierbar ist, das Urteil aus aktueller Evidenz folgt und der nächste Übergang eindeutig ist. Berichte zusätzlich knapp:

- geprüfte Risiken und bewusst nicht aktivierte Prüfdimensionen,
- ausgeführte und blockierte Checks mit Grund,
- verwendete Fallbacks und verbleibendes Restrisiko,
- exakten Reviewartefaktpfad.

Diese Zusammenfassung ist kein zweiter Statusspeicher. Implementiere keine Fixes, ändere keine Plan- oder Runstatusdateien und starte keine Subagenten.

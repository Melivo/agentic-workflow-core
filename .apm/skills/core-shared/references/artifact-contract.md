# Artefaktvertrag

Repositorydateien übertragen den Workflowkontext. Dieses Dokument definiert Eigentum und Mindestformate; es ist selbst weder Laufzustand noch Eventhistorie.

## Kanonische Pfade und Eigentümer

| Information | Kanonische Source of Truth | Eigentümer |
|---|---|---|
| Systemdesign des Pakets | `DESIGN.md` | Architekturentscheidung |
| Gesamtziel und gemeinsame bestätigte Entscheidungen | `.agentic-workflow/goals/<goal-id>/goal.md` mit `goal/v1` | `core-milestone` |
| Unveränderliche Etappendefinition und Version | `.agentic-workflow/goals/<goal-id>/milestones/<milestone-id>-v<version>.yaml` mit `milestone-definition/v1` | `core-milestone` |
| Versionsauswahl, aktuelle Etappe und Nachweisreferenzen | `.agentic-workflow/goals/<goal-id>/index.yaml` mit `milestone-index/v1` | `core-milestone` |
| Ziel, Scope und Taskgraph | `.agentic-workflow/plans/<plan-name>.md` mit `plan/v1` | `core-plan` |
| aktueller Resume-Zustand | `.agentic-workflow/runs/<run-id>/state.yaml` | `core-execute` |
| Task- und Checkevidenz | neue Versuche: `.agentic-workflow/runs/<run-id>/tasks/<task-id>/attempt-<nn>.yaml` mit `task-result/v1`; bestehende `.agentic-workflow/runs/<run-id>/tasks/<task-id>.yaml` bleiben lesbarer Legacy-Pfad | `core-execute` persistiert die Ergebnisse read-only Agenten; ein ausdrücklich schreibender Agent darf ausschließlich seine Ergebnisdatei gemäß Taskresultatausnahme ändern |
| Kontext für Review oder Resume | `.agentic-workflow/runs/<run-id>/handoff.md` | `core-execute` |
| Urteil und Findings | `.agentic-workflow/runs/<run-id>/review.yaml` mit `review/v1` | `core-review` |
| Produktstand | Repository und aktueller Git-Diff | Repository |

Der bestätigte Plan bleibt unverändert. `state.yaml` enthält nur den aktuellen Resume-Zustand, keine Eventhistorie. `handoff.md` wird ersetzt statt angehängt. Honcho und Tool-Memories sind keine Sources of Truth. Ziel, Definition, Index, bestätigter Plan, Runzustand, Taskversuche und Review bleiben getrennte Artefakte mit den unten ausgewiesenen Eigentümern; Task-/Reviewstatus wird nicht in Ziel oder Definition kopiert. Einfache Vorhaben ohne Etappenstruktur benötigen weder Ziel noch Index.

Für eine Etappenplanung sind die kanonischen Formate [goal/v1](../../core-milestone/references/goal-format.md), [milestone-definition/v1](../../core-milestone/references/milestone-format.md) und [milestone-index/v1](../../core-milestone/references/milestone-index-format.md). Diese Quellen sind maßgeblich; dieser Vertrag fasst Eigentum und Workflowbezüge zusammen. `milestone/v1` ist nur Legacy-Leseformat.

## `plan/v1`

Der bestätigte Plan ist ein Markdown-Dokument mit genau einem eingebetteten, validierbaren Taskgraphen. Sein Kernformat bleibt:

```yaml
schema: plan/v1
status: Confirmed
tasks:
  - id: T01
    title: Ergebnisorientierter Titel
    agent: backend-engineer
    task: Selbstständiger Auftrag für einen frischen Kontext
    context_paths: [src/example/, tests/example/]
    scope: [src/example/, tests/example/]
    dependencies: []
    required_mcps: [gortex]
    optional_mcps: [context7]
    acceptance:
      - id: AC01
        description: Beobachtbares Ergebnis
    checks:
      - id: CK01
        covers: [AC01]
        command: ["pytest", "tests/example/test_api.py"]
        cwd: "."
        pass: "Exitcode 0 und erwartete fachliche Beobachtung"
```

Jeder Task hat genau einen registrierten Agenten. `context_paths` und `scope` bleiben getrennt; leeres `scope` bedeutet read-only. Abhängigkeiten sind der einzige Ordnungsmechanismus. Jedes Akzeptanzkriterium wird durch mindestens einen Check gedeckt. Materielle Unsicherheit verhindert `Confirmed`.

## Runzustand

`.agentic-workflow/runs/<run-id>/state.yaml` darf nur die für Wiederaufnahme erforderliche aktuelle Sicht enthalten: `run_id`, exakten `plan_path`, aktuellen Laufzustand, integrierte beziehungsweise ausführbare Task-IDs und die Anzahl bereits verwendeter automatischer Review-Reparaturrunden. Es dupliziert weder Taskevidenz noch Findings oder Planinhalt und führt kein Ereignisjournal.

## `task-result/v1`

```yaml
schema: task-result/v1
task_id: T01
attempt: 1
status: completed | partial | blocked | failed
changed_paths: []
acceptance:
  - id: AC01
    status: pass | fail | not_checked
    evidence: konkrete Beobachtung oder Artefaktpfad
checks:
  - id: CK01
    status: pass | fail | blocked
    command: ["pytest", "tests/example/test_api.py"]
    cwd: "."
    exit_code: 0
    evidence: kurze relevante Ausgabe
limitations: []
```

`changed_paths` entspricht den tatsächlichen Änderungen. Ein Exitcode ersetzt keine fachliche Beobachtung. Fehlende aktuelle Pflichtcheckevidenz führt zu `partial` oder `blocked`. `core-execute` persistiert die Rückgabe eines read-only Agenten in dessen Taskresultat; der Agent selbst erhält dadurch keine Schreibrechte an Produkt- oder Runartefakten. Ist der zugewiesene Agent ausdrücklich für Änderungen vorgesehen, darf er als eng begrenzte Ausnahme nur genau seine eigene Ergebnisdatei schreiben, nicht Plan, Runstatus, Handoff oder Review.

Ein neuer Versuch wird als neue, unveränderliche Datei unter `tasks/<task-id>/attempt-<nn>.yaml` abgelegt (`nn` mindestens zweistellig, fortlaufend und innerhalb dieses Runs/Tasks eindeutig). Frühere Versuche bleiben erhalten; ein Retry darf sie nicht überschreiben oder umdeuten. `attempt` im `task-result/v1` beschreibt dieselbe fortlaufende Kennung. Bestehende `tasks/<task-id>.yaml` werden als Legacy-Ergebnis weiter gelesen; es gibt keine automatische Umbenennung oder Migration. Fehlende, doppelte oder widersprüchliche Versuchsbezüge blockieren Wiederverwendung.

## Handoff

Das Handoff verwendet [`../assets/handoff.md`](../assets/handoff.md). Bei Etappenplanung referenziert es zusätzlich exakte Ziel-, Index- und Definitionspfade samt Ziel-ID, Milestone-ID und Versionsnummer. Es referenziert Plan, Run, Repositorystand, Taskresultate, Prüfevidenz und Einschränkungen, kopiert aber keinen konkurrierenden Status. Empfänger laden die referenzierten Artefakte und den aktuellen Repositorystand in frischem Kontext. Veraltete Pfade/Versionen, widersprüchliche IDs oder ein nicht zur Definition gebundener Plan blockieren; Dateinamen und neueste Version ersetzen weder Auswahl noch Bestätigung.

## `review/v1`

Das Review verwendet [`../assets/review-finding.yaml`](../assets/review-finding.yaml). Ein Finding enthält reproduzierbare Evidenz, Owner, Ort, Auswirkung, erwartete Behebung und Wiederprüfung. `task_id` wird gesetzt, wenn eine eindeutige Zuordnung möglich ist; ein Querschnittsfinding erhält mindestens einen klaren `owner` und Bereich.

Die Schweregrade bleiben `blocking | high | medium | low`; ein CRITICAL-Befund wird als `blocking` abgebildet, HIGH bleibt `high`. Materielle Änderungen an Ziel, Scope, Architektur oder Akzeptanz werden an `core-plan` zurückgegeben und nicht durch zusätzliche Schemafelder verschleiert.

## Aufbewahrung und Integrität

Bestätigte Ziel-, Definitions- und Planfassungen bleiben unverändert; eine geänderte Zielsetzung benötigt ein bestätigtes Nachfolgeziel, eine geänderte Etappendefinition eine bestätigte neue Version und Auswahl. Dateiname, IDs und exakte Pfade müssen übereinstimmen: G-ID ist projektweit eindeutig; M-ID ist innerhalb des Ziels eindeutig; Versionsnummer ist positive Ganzzahl; Plan `pNN` und Run `rNN` haben mindestens zwei Stellen. Namensschema: `plan-G01-M02-v1-p01.md` und `run-G01-M02-v1-p01-r01/`. Kollidierende Namen, Pfad-/Inhaltswidersprüche, Wiederverwendung belegter Nummern oder doppelte ID-Versionen blockieren; Namen beweisen keine Freigabe. Resume und Review-Reparaturen behalten die Run-ID; ein eigenständiger neuer Lauf erhöht `r`, ein Ersatzplan erhöht `p`.

Run-Artefakte sind normalerweise gitignoriert. Bewahre Ziel, ausgewählte und referenzierte Definitionsversionen, Index, bestätigte Pläne, state.yaml, Taskversuche, Review und verknüpfte Originalprüfevidenz so lange auf, wie Ziel oder spätere Übergaben auf sie angewiesen sind; referenzabhängige Artefakte sind zu erhalten und aufzubewahren und werden nicht pauschal nach Runabschluss gelöscht. Veraltete, nicht mehr referenzierte Artefakte dürfen nur nach Prüfung ihrer Referenzen behandelt werden. Artefakte enthalten keine Secrets und werden vor Wiederverwendung gegen Repositorydrift geprüft. Der vollständige Legacy-Einstieg `milestone/v1` ist lesbar, ohne Migration oder Vermischung mit getrennten Formaten.

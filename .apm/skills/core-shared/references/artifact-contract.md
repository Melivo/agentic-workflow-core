# Artefaktvertrag

Repositorydateien übertragen den Workflowkontext. Dieses Dokument definiert Eigentum und Mindestformate; es ist selbst weder Laufzustand noch Eventhistorie.

## Kanonische Pfade und Eigentümer

| Information | Kanonische Source of Truth | Eigentümer |
|---|---|---|
| Systemdesign des Pakets | `DESIGN.md` | Architekturentscheidung |
| Ziel, Scope und Taskgraph | `.agentic-workflow/plans/<plan-name>.md` mit `plan/v1` | `core-plan` |
| aktueller Resume-Zustand | `.agentic-workflow/runs/<run-id>/state.yaml` | `core-execute` |
| Task- und Checkevidenz | `.agentic-workflow/runs/<run-id>/tasks/<task-id>.yaml` mit `task-result/v1` | zugewiesener Fachagent, validiert durch `core-execute` |
| Kontext für Review oder Resume | `.agentic-workflow/runs/<run-id>/handoff.md` | `core-execute` |
| Urteil und Findings | `.agentic-workflow/runs/<run-id>/review.yaml` mit `review/v1` | `core-review` |
| Produktstand | Repository und aktueller Git-Diff | Repository |

Der bestätigte Plan bleibt unverändert. `state.yaml` enthält nur den aktuellen Resume-Zustand, keine Eventhistorie. `handoff.md` wird ersetzt statt angehängt. Honcho und Tool-Memories sind keine Sources of Truth.

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

`changed_paths` entspricht den tatsächlichen Änderungen. Ein Exitcode ersetzt keine fachliche Beobachtung. Fehlende aktuelle Pflichtcheckevidenz führt zu `partial` oder `blocked`.

## Handoff

Das Handoff verwendet [`../assets/handoff.md`](../assets/handoff.md). Es referenziert den exakten Plan, Run, Repositorystand, Taskresultate, Prüfevidenz und Einschränkungen, kopiert aber keinen konkurrierenden Status. Empfänger laden die referenzierten Artefakte und den aktuellen Repositorystand in frischem Kontext.

## `review/v1`

Das Review verwendet [`../assets/review-finding.yaml`](../assets/review-finding.yaml). Ein Finding enthält reproduzierbare Evidenz, Owner, Ort, Auswirkung, erwartete Behebung und Wiederprüfung. `task_id` wird gesetzt, wenn eine eindeutige Zuordnung möglich ist; ein Querschnittsfinding erhält mindestens einen klaren `owner` und Bereich.

Die Schweregrade bleiben `blocking | high | medium | low`; ein CRITICAL-Befund wird als `blocking` abgebildet, HIGH bleibt `high`. Materielle Änderungen an Ziel, Scope, Architektur oder Akzeptanz werden an `core-plan` zurückgegeben und nicht durch zusätzliche Schemafelder verschleiert.

## Aufbewahrung und Integrität

Bestätigte Pläne dürfen versioniert werden. Run-Artefakte sind normalerweise gitignoriert und nach Abschluss entbehrlich. Artefakte referenzieren exakte Pfade und IDs, enthalten keine Secrets und werden vor Wiederverwendung gegen Repositorydrift geprüft.

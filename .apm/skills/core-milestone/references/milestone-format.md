# Milestone-Definitionsformat

Neue Etappenplanung trennt das bestätigte [Ziel](goal-format.md), unveränderliche Definitionsversionen und den aktualisierbaren [Index](milestone-index-format.md). `core-milestone` besitzt diese Workflow-Artefakte; Definitionen sind weder Detailpläne noch Runzustand. Lade dieses Format für Erstellung, Ersatz oder Prüfung einer konkreten Definition und bei ausdrücklich benanntem Legacy-Einstieg.

## Vollständige Definitionsbeispiele

Die erste Definition liegt unter `.agentic-workflow/goals/G01/milestones/M01-v1.yaml`:

```yaml
schema: milestone-definition/v1
id: M01
version: 1
approval: user-confirmed
goal_path: .agentic-workflow/goals/G01/goal.md
title: Erste nutzbare Etappe
outcome: Die vereinbarte Grundlage ist nutzbar
scope: [src/example/, tests/example/]
dependencies: []
acceptance:
  - id: MAC01
    description: Die Grundlage erfüllt den bestätigten Vertrag
```

Die darauf aufbauende Definition liegt unter `.agentic-workflow/goals/G01/milestones/M02-v1.yaml`:

```yaml
schema: milestone-definition/v1
id: M02
version: 1
approval: user-confirmed
goal_path: .agentic-workflow/goals/G01/goal.md
title: Grundlage erweitern
outcome: Die Erweiterung nutzt die überprüfte Grundlage
scope: [src/example/, tests/example/]
dependencies:
  - id: M01
    version: 1
    definition_path: .agentic-workflow/goals/G01/milestones/M01-v1.yaml
acceptance:
  - id: MAC01
    description: Die Erweiterung erfüllt ihren bestätigten Vertrag
```

## Identität, Felder und Freigabe

- `schema`, `id`, `version`, `approval`, `goal_path`, `title`, `outcome`, `scope`, `dependencies` und `acceptance` sind Pflichtfelder; jedes YAML-Artefakt enthält genau eine Definition.
- IDs haben die Form `M` plus mindestens zwei Ziffern; sie sind innerhalb des Ziels eindeutig. `version` ist eine positive ganze Zahl, im Dateinamen `v1`, `v2` usw. Für dieselbe ID entsteht pro bestätigter inhaltlicher Änderung die nächste unbenutzte höhere Version; Lücken nach abgebrochenem Schreiben werden nicht durch Überschreiben geschlossen.
- Pfade sind exakt und projektrelativ. Ziel-ID aus `goal_path`, Milestone-ID und Versionsnummer müssen mit dem tatsächlichen Dateipfad übereinstimmen. Eine optionale Selbstreferenz `definition_path` muss denselben Pfad enthalten. Dateiname oder Änderungsdatum ersetzt keine Auswahl.
- `approval: user-confirmed` dokumentiert die tatsächliche ausdrückliche Bestätigung des exakten Inhalts. Ein selbst gesetztes Feld, Dateipfad oder Handoff beweist sie nicht und autorisiert weder Planbestätigung noch Ausführung.
- `scope` ist die bestätigte Etappengrenze, keine Mutationsfreigabe. Der bestätigte Plan bestimmt konkrete Schreibscopes innerhalb dieser Grenze. Leerer Scope ist bei einer ausdrücklich read-only Etappe zulässig.
- Outcome, Titel und Kriterien sind nicht leer. Kriterien-IDs sind innerhalb der Definitionsversion eindeutig; etwa `MAC01`. Gleiche IDs in anderen Etappen oder Ersatzversionen übertragen keine Erfüllung.
- Abhängigkeiten pinnen `id`, `version` und `definition_path` innerhalb desselben Gesamtziels. Die referenzierten Dateien müssen existieren und dieselben Werte enthalten. Unbekannte, doppelte, zyklische oder auf sich selbst verweisende Abhängigkeiten blockieren. Prüfe den Graphen über alle tatsächlich referenzierten Definitionsversionen, nicht nur Dateinamen.
- Gemeinsame bestätigte Entscheidungen und Nicht-Ziele kommen aus der Zieldatei. Optionales `decision_refs: []` pinnt zusätzlich benötigte bestätigte Designquellen; fehlende oder widersprüchliche Quellen blockieren. Keine Gesprächsrekonstruktion oder neue Grundsatzentscheidung.
- Definitionen enthalten keinen fortgeschriebenen `status`, `run_status`, `task_status`, keine Findings und keine Plan-/Run-/Abschlusslisten. Diese Referenzen besitzt der Index; Originalstatus und Evidenz bleiben in Plan-/Run-/Review-Artefakten.

## Ersatz und historische Integrität

Bestätigte Definitionen bleiben unveränderlich. Eine Ersatzdefinition oder Versionsauswahl benötigt ausdrückliche Bestätigung. Schreibe etwa `M02-v2.yaml` an einen freien Pfad, prüfe sie vollständig und wähle sie erst dann im Index aus; das Dateivorhandensein allein genügt nicht. Das Ziel bleibt unverändert, solange sich nur der Weg ändert. Eine materielle Ziel-/Leitplankenänderung benötigt das bestätigte Nachfolgeziel gemäß Ziel-Format.

Ein Versionswechsel verändert weder alte Definition noch Plan, Run oder Review. Abschlussnachweise gelten nicht automatisch für eine Ersatzversion. Prüfe betroffene Kriterien, Designquellen und Abhängigkeiten; eine neue Kriterienfassung darf einen alten Abschluss nicht erben. Bei Wiederverwendung müssen Originalnachweise auch die neue Fassung auf aktuellem Stand nachweisbar decken. Die ausdrückliche Prüfung wird als neuer versionsgebundener Abschlussverweis mit exaktem `revalidation_path` im Index verknüpft, nicht als Kopie alter Statuswerte. Ohne diese Prüfung bleibt der neue Abschluss unverifiziert.

Ist eine abhängige Definition auf `M01-v1` gepinnt, bleibt dieser Bezug bei Auswahl von `M01-v2` erhalten. Für aktive Folgearbeit muss ihre Abhängigkeit mit der Indexauswahl vereinbar sein; eine geänderte Abhängigkeit erfordert eine bestätigte neue Folgeetappen-Version. Historische Definitionen werden nicht umgeschrieben. Laufende Runs bleiben an ihren bisherigen Plan gebunden: vor Fortsetzung sicheren Haltepunkt herstellen, betroffenen Versionsbezug klären und gegebenenfalls einen Ersatzplan bestätigen; kein automatisches Resume unter der neuen Version.

## Legacy: milestone/v1 ausschließlich lesen

Bereits vorhandene `.agentic-workflow/milestones/<name>.yaml` bleiben über den exakten Eingabepfad lesbar. Das folgende frühere Format ist kein Neuanlageformat und wird nicht automatisch migriert, umbenannt oder mit den getrennten Formaten vermischt:

```yaml
schema: milestone/v1
id: G01
goal: Beobachtbares Gesamtziel
non_goals: []
constraints: []
decisions: []
decision_refs: []
goal_acceptance:
  - id: GAC01
    description: Überprüfbares Ergebnis des gesamten Vorhabens
    evidence_paths: []
current_milestone: M01
milestones:
  - id: M01
    title: Erste nutzbare Etappe
    outcome: Beobachtbarer Nutzen
    scope: [src/example/, tests/example/]
    dependencies: []
    acceptance:
      - id: MAC01
        description: Überprüfbare Abschlussbedingung dieser Etappe
    plan_paths: []
    run_paths: []
    completion_refs: []
```

Der Legacy-Leser prüft eindeutige IDs/Kriterien, existierende azyklische Abhängigkeiten und `current_milestone` als existierende ID oder null. Er liest bestätigte Entscheidungen und relevante `decision_refs` sowie die exakten Plan-/Run-/Reviewnachweise neu. Die bisherige `plan_paths`-Ablösereihenfolge und `run_paths` auf state.yaml bleiben interpretierbar; leere Listen bedeuten keine Planung/Ausführung. Fehlende Nachweise ergeben „Abschluss nicht verifizierbar“, nicht erfundene Ersatzbelege. Keine Definitionsversion wird aus Legacy-IDs ergänzt. Eine gewünschte Migration ist ein eigener ausdrücklich autorisierter Auftrag.

## Aufbewahrung und Fehlergrenze

Erhalte Ziel, jede referenzierte Definitionsversion, bestätigte Designquellen, Pläne, Runzustände, Task-/Checkevidenz und Reviews, solange dieses Vorhaben oder spätere Übergaben darauf angewiesen sind. Verwende Originalartefakte statt eines zweiten Statusspeichers; historische Abschlüsse werden nicht durch jede neue Repositoryänderung pauschal verworfen. Relevanz und Drift werden vor Wiederverwendung geprüft.

Vor jedem erlaubten Schreiben lade den konkreten Pfad neu und vergleiche ihn mit der geprüften Ausgangsfassung. Bei konkurrierender Änderung oder Pfadkollision stoppe ohne fremde Inhalte zu überschreiben. Das Index-Format definiert die Reihenfolge und die sichere Wiederaufnahme bei Teilfehlern.

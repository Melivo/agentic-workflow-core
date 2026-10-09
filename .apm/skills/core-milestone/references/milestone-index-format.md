# Milestone-Indexformat

`core-milestone` besitzt `.agentic-workflow/goals/<goal-id>/index.yaml` mit `milestone-index/v1`. Der Index ist die einzige Auswahlquelle für Definitionsversionen und die aktuelle Etappe. Er verknüpft Originalnachweise, ist aber weder Task-Scheduler noch Kopie von Runstatus, Findings oder Evidenz. Lade dieses Format für Auswahl, Abschlussverknüpfung und Wiederaufnahme. Die unveränderlichen Inhalte liegen im [Ziel](goal-format.md) und den [Definitionen](milestone-format.md).

## Vollständiges Beispiel

Das Beispiel referenziert genau die Definitionen `M01-v1` und `M02-v1` aus dem Definitionsformat. Die genannten Ergebnisdateien illustrieren die Beziehungen; erst ihre tatsächliche Prüfung erlaubt Abschluss oder aktuelle Folgearbeit. Beispiele sind keine realen Freigaben oder Prüfnachweise.

```yaml
schema: milestone-index/v1
goal_path: .agentic-workflow/goals/G01/goal.md
revision: 1
milestones:
  - id: M01
    version: 1
    definition_path: .agentic-workflow/goals/G01/milestones/M01-v1.yaml
    selected: true
    selection_approval: user-confirmed
    current: false
    plan_paths:
      - .agentic-workflow/plans/plan-G01-M01-v1-p01.md
    run_paths:
      - .agentic-workflow/runs/run-G01-M01-v1-p01-r01/state.yaml
    completion_refs:
      - version: 1
        definition_path: .agentic-workflow/goals/G01/milestones/M01-v1.yaml
        acceptance_ids: [MAC01]
        plan_path: .agentic-workflow/plans/plan-G01-M01-v1-p01.md
        run_path: .agentic-workflow/runs/run-G01-M01-v1-p01-r01/state.yaml
        review_path: .agentic-workflow/runs/run-G01-M01-v1-p01-r01/review.yaml
        evidence_paths:
          - .agentic-workflow/runs/run-G01-M01-v1-p01-r01/tasks/T01.yaml
  - id: M02
    version: 1
    definition_path: .agentic-workflow/goals/G01/milestones/M02-v1.yaml
    selected: true
    selection_approval: user-confirmed
    current: true
    current_approval: user-confirmed
    plan_paths: []
    run_paths: []
    completion_refs: []
goal_completion_refs: []
```

## Auswahl und Referenzintegrität

- Pflichtfelder sind `schema`, `goal_path`, positive ganzzahlige `revision`, `milestones` als nicht leere Liste und `goal_completion_refs` als Liste. Alle Pfade sind projektrelativ. Der Indexpfad und der Zielpfad müssen dieselbe projektweit eindeutige G-ID besitzen; die Zieldatei muss existieren und diese ID bestätigen.
- Jeder Eintrag besitzt `id`, positive ganzzahlige `version`, `definition_path`, boolesche `selected`/`current`, `selection_approval`, `plan_paths`, `run_paths` und `completion_refs`. Einträge sind nach `(id, version)` eindeutig. Name, Werte und tatsächlich gelesene Definition müssen übereinstimmen. Die M-ID ist innerhalb des Ziels eindeutig, mehrere historische Versionen derselben ID sind zulässig.
- Pro M-ID gibt es genau eine ausgewählte Version (`selected: true`); andere vorhandene Einträge bleiben historische Referenzen mit `selected: false` und `current: false`. Unreferenzierte Dateien oder die höchste Nummer sind keine automatische Auswahl. Soll eine Etappe entfallen, ist das eine ausdrückliche Etappengrenzen-/Abhängigkeitsentscheidung, kein heimliches Entfernen eines Eintrags.
- Höchstens ein Eintrag hat `current: true`; er muss ausgewählt und durch `current_approval: user-confirmed` ausdrücklich freigegeben sein. Kein aktueller Eintrag bedeutet keine freigegebene aktive Etappe. Erstmalige Auswahl kann mit dem bestätigten Gesamtentwurf erfolgen; jeder spätere Wechsel benötigt ausdrückliche Freigabe.
- `selection_approval` und `current_approval` dokumentieren bestätigte Entscheidungen; ihre bloße Existenz beweist keine neue Freigabe. Die bestätigte schriftliche Fassung ist beim Wiedereinstieg zu prüfen. Handoff, Goal-Prompt, Dateiname, Toolverfügbarkeit und Run-pass erteilen keine Folgefreigabe.
- Aktuelle Arbeit setzt nachweisbar abgeschlossene Abhängigkeiten voraus. Jede gepinnte ID-Version der aktuellen Definition muss existieren und zur ausgewählten Version der betreffenden M-ID passen. Bei anderer Auswahl oder fehlenden Abschlussnachweisen stoppe; ändere die abhängige Definition nicht automatisch. Prüfe Zyklen, Selbstreferenzen, doppelte/fehlende Einträge und Dateipfad-/Inhaltswidersprüche vor jeder Auswahl.
- `plan_paths` enthält ausschließlich bestätigte Pläne für genau diese Definitionsversion in ihrer Ablösereihenfolge; der letzte ist maßgeblich. `run_paths` verweist auf deren originale state.yaml-Dateien. Resume und Review-Reparaturen behalten dieselbe Run-ID. Ein Ersatzplan erhöht p, ein eigenständiger neuer Run erhöht r gemäß Ziel-Format; ein Name beweist keine Bestätigung.
- Im Plan müssen Ziel, Index, ID, Version und Definitionspfad eindeutig gepinnt sein. Der Run verweist auf genau diesen Plan. Start/Resume prüft Auswahl und Planbindung neu; materielle Änderung bedeutet Planentscheidung, nicht Änderung des bestätigten Plans.
- Zusätzliche Felder für duplizierte Task-/Runzustände, Findings, kopierte Checkausgaben oder Ereignisjournale sind nicht zulässig. Laufblocker werden aus Originalruns gelesen. Übersichtszustände sind aus Auswahl und aktuell gültigen Nachweisen abgeleitet, nicht zusätzlich gespeichert.

## Abschluss- und Gesamtzielnachweise

`completion_refs` gehört zur ID-Version seines Eintrags. Jeder Verweis pinnt `version`, `definition_path`, nicht leere `acceptance_ids` sowie exakte `plan_path`, `run_path`, `review_path` und nicht leere `evidence_paths`. Alle Kriterien müssen zur gepinnten Definition gehören; gemeinsam müssen gültige Abschlussverweise deren sämtliche Kriterien abdecken. Originalplan, Run, Review und Task-/Checkevidenz müssen nachweisbar zusammengehören und erhalten bleiben.

Ein Run-Abschluss mit aktuellem Review-pass genügt nur, wenn auch über den Taskgraphen hinausgehende Milestone-Kriterien belegt sind. Prüfe Originalstatus, Akzeptanz-/Checkevidenz und relevante Repositorydrift; vorhandene Pfade oder eine alte Erfolgsmeldung allein genügen nicht. Fehlende Abdeckung geht zur Planentscheidung, statt Kriterien zu verkleinern. Fehlt eine erforderliche Datei, melde „Abschluss nicht verifizierbar“. Nach verifiziertem Etappenabschluss wird `current` auf false gesetzt; Folgearbeit bleibt bis zur ausdrücklichen Freigabe nur vorgeschlagen.

Für eine neue Definition gilt: Abschlussnachweise werden nicht automatisch übernommen. Historische Verweise bleiben am früheren Eintrag erhalten. Wiederverwendung erfordert eine ausdrückliche Prüfung gegen sämtliche betroffenen neuen Kriterien und Abhängigkeiten auf aktuellem Stand. Ein neuer Abschlussverweis pinnt dann die neue Definition, die Originalnachweise und zusätzlich `revalidation_path` auf die vorhandene schriftliche Task-/Checkevidenz dieser Prüfung. Er deklariert keine Zugehörigkeit des alten Plans zu einer neuen Version; diese Ausnahme ist nur mit belegtem Versionsvergleich und der neuen Abnahme zulässig. Ohne passenden Prüfscope oder belegte Abdeckung bleibt der Ersatzabschluss unverifiziert. Es entsteht kein separates Pflichtdossier.

`goal_completion_refs` ist zunächst leer. Bei Gesamterfolg verknüpft core-milestone hier `acceptance_ids` aus goal_acceptance, `goal_path` und nicht leere `evidence_paths` auf aktuelle Originalprüfungen oder den hier belegten versionsgebundenen Etappenabschluss. Erweitere keine unveränderliche Zieldatei. Alle ausgewählten Etappen und alle Gesamtzielkriterien müssen belegt erfüllt sein; historische Abschlüsse abgelöster Versionen genügen nicht automatisch. Gesamtprüflücken werden gemeldet, nicht als Gesamterfolg umgedeutet.

## Bestätigter Versionswechsel

Eine Ersatzdefinition und ihre Versionsauswahl benötigen ausdrückliche Bestätigung. Prüfe die Auswirkung auf Gesamtziel, aktuelle Arbeit, Kriterien und abhängige Etappen; ein Zielwechsel benötigt ein Nachfolgeziel, keine Änderung von goal.md. Schreibe und prüfe die bestätigte Ersatzdefinition an einem freien Pfad. Erst anschließend füge ihren Eintrag mit leeren Plan-/Run-/Abschlusslisten hinzu und ändere die ausdrücklich bestätigte Auswahl. Historische Einträge und ihre Originalnachweise bleiben erhalten.

Bei laufendem Run zuerst einen sicheren Haltepunkt durch Execute herstellen. Auswahl oder Definition dürfen keine laufende Mutation umdeuten. Ein versionsgebundener alter Plan kann nicht unter der neuen Auswahl fortgesetzt werden; bestehende Run-/Review-Artefakte werden nicht umgeschrieben. Route erforderliche Ersatzplanung zum Eigentümer. Betroffene Folgeetappen mit alten Abhängigkeiten bleiben blockiert, bis passende Ersatzdefinitionen bestätigt sind. Keine pauschale Invalidierung unabhängiger historischer Evidenz und keine automatische Folgefreigabe.

## Schreibreihenfolge, Konkurrenz und Wiederaufnahme

1. Lade vor jeder Mutation Ziel, Definitionsversionen und Index neu. Prüfe exakte IDs/Pfade, vorhandene Bestätigungen und den versionsgebundenen Abhängigkeitsgraphen; fehlende/widersprüchliche Eingaben blockieren.
2. Notiere die geprüfte Ausgangsfassung des Index einschließlich revision und Inhaltsvergleich. Ein Zähler allein erkennt keine fremden Änderungen; prüfe auch den Inhalt und nutze eine bedingte atomare Schreiboperation gegen diese Ausgangsfassung. Kann die verwendete Operation diesen Schutz nicht gewährleisten, stoppe statt Konkurrenzsicherheit zu behaupten.
3. Schreibe ausschließlich bestätigte neue Ziele/Definitionen an freie Pfade mit Nicht-Überschreiben-Guard. Prüfe Inhalte, Namensbezüge und alle benötigten Referenzen, bevor der Index sie auswählt.
4. Aktualisiere den Index zuletzt, atomar und nur bei unveränderter geprüfter Ausgangsfassung; erhöhe revision um eins. Bearbeite nur bestätigte Auswahl/Freigabe oder belegte Referenzverknüpfungen. Eine Nachweisaktualisierung autorisiert keine neue Etappe.
5. Bei Schreib-/Prüffehler stoppe. Bereits geschriebene neue Dateien bleiben unreferenzierte Teilresultate, keine freigegebene Version. Nicht automatisch auswählen, löschen, umbenennen oder fremde Änderungen zurückrollen. Bei unklarem Index-Schreibergebnis zuerst neu lesen, niemals blind erneut schreiben.
6. Eine spätere autorisierte Wiederaufnahme liest die wirklichen Dateien neu und vergleicht sie mit dem bestätigten Inhalt. Nur passende bestätigte Teilresultate dürfen nach erneuter Prüfung verknüpft werden. Bei konkurrierender Änderung oder Kollision benenne die exakten Dateien und benötigte Entscheidung; fehlende Inhalte werden nicht aus Chat oder Memories rekonstruiert.

Solange Ziel oder spätere Übergaben auf Referenzen angewiesen sind, bleiben Zieldatei, historische Definitionen, Designquellen und Originalnachweise erhalten. Ein separates Handoff ist ein Wegweiser, keine neue Index- oder Freigabequelle. Legacy milestone/v1 wird gemäß Definitionsformat ausschließlich gelesen; keine automatische Migration oder Vermischung.

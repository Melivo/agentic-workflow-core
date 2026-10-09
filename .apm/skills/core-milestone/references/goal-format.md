# Ziel-Format

Ein ausdrücklich gewähltes Vorhaben mit mehreren Etappen besitzt genau ein bestätigtes Ziel unter .agentic-workflow/goals/<goal-id>/goal.md. Dieses Format definiert goal/v1; core-milestone besitzt das Artefakt. Einfache Vorhaben ohne Etappen benötigen keine Zielstruktur und bleiben bei einem bestätigten plan/v1.

## Beispiel

```yaml
schema: goal/v1
id: G01
approval: user-confirmed
goal: Ein beobachtbares, gemeinsames Ergebnis
non_goals:
  - Nicht Teil des vereinbarten Vorhabens
constraints:
  - Bestehende Sicherheits- und Plattformgrenzen erhalten
decisions:
  - decision: Bestehende Schnittstelle beibehalten
    rationale: Bestätigte gemeinsame Leitplanke
goal_acceptance:
  - id: GAC01
    description: Das Gesamtziel ist durch die benannten Originalnachweise erfüllt
```

`approval: user-confirmed` dokumentiert die zuvor ausdrücklich eingeholte Bestätigung des exakten Zielinhalts; das Feld allein beweist keine Freigabe. Es ersetzt weder die Bestätigung des einzelnen Plans noch die Ausführungsfreigabe. Lade bei Wiederaufnahme die bestätigte schriftliche Fassung; fehlende Bestätigung darf nicht aus Dateinamen, Gesprächsrekonstruktion oder Memories abgeleitet werden. goal_acceptance enthält eindeutige GACnn-Kriterien, die das Gesamtziel beschreiben und nicht aus Etappenkriterien abgeleitet werden. decisions enthält nur bestätigte gemeinsame Entscheidungen mit knapper Begründung; übernimm verworfene Alternativen und Quellen nur, soweit sie die Entscheidung nachvollziehbar machen. Keine offene Annahme wird als Entscheidung ausgegeben.

Optionales `decision_refs: []` enthält exakte projektrelative Pfade zu bestätigten Designquellen. Separate Designdateien sind keine Pflicht. Referenzierte Quellen müssen vorhanden und mit dem bestätigten Inhalt vereinbar sein; andernfalls stoppe. Gesamtziel-Abschlussnachweise werden als `goal_completion_refs` im [Index](milestone-index-format.md) verknüpft, nicht nachträglich in die unveränderliche Zieldatei geschrieben.

`goal.md` enthält genau einen YAML-Block mit `schema: goal/v1`; dies ist der maßgebliche Datenblock. Erläuternde Prosa darf ihn erklären, aber keine konkurrierenden Ziel-, Entscheidungs- oder Kriterienwerte definieren. Pfade sind relativ zur Projektwurzel, nicht zum Dateiverzeichnis.

## Eigentum, Identität und Änderung

- id hat die Form G plus mindestens zwei Ziffern, etwa G01; es ist projektweit eindeutig und wird nie wiederverwendet. Die Datei liegt genau unter .agentic-workflow/goals/G01/goal.md.
- Die Zieldatei hält Gesamtziel, Nicht-Ziele, Leitplanken, bestätigte gemeinsame Entscheidungen und Gesamtzielkriterien fest. Fortschritt, aktuelle Etappe, Plan-/Runstatus und Findings gehören nicht hierher.
- Nach Bestätigung bleibt der Inhalt unverändert. Eine tatsächlich geänderte Zielsetzung benötigt eine ausdrücklich bestätigte Nachfolge-Zieldatei mit neuer projektweit eindeutiger ID; überschreibe oder benenne das frühere Ziel nicht um. Bewahre die historische Zieldatei solange Referenzen auf sie bestehen.
- Änderungen an erläuternden oder entscheidungsrelevanten Feldern gelten ebenfalls als Zieländerung. Bei unsicherer Reichweite stoppen und die notwendige Bestätigung klären.
- Relative Referenzen in Plänen und Definitionen müssen auf genau diese Zieldatei zeigen. Die ID und der exakte Pfad sind gemeinsam maßgeblich; Änderungsdatum oder „neueste Datei“ ist keine Auswahl.

Ein neues Ziel erzeugt noch keinen Milestone, Plan, Run oder Dispatch. Erst die bestätigte Zielstruktur und die ausdrücklich bestätigte Auswahl erlauben Etappenarbeit. Zielbestätigung autorisiert weder Planbestätigung noch Ausführung.

## Namensschema und Beziehungen

Für G01 liegen Ziel, Index und Definitionen exakt unter `.agentic-workflow/goals/G01/goal.md`, `.agentic-workflow/goals/G01/index.yaml` und `.agentic-workflow/goals/G01/milestones/M02-v1.yaml`. `G01` ist projektweit eindeutig; `M02` ist nur innerhalb dieses Ziels eindeutig. ID, positiver ganzzahliger Versionswert und exakter relativer Pfad müssen übereinstimmen. Ziel-, Milestone-, Plan- und Runnummern haben mindestens zwei Ziffern, ohne künstliche Obergrenze; Versionsnummern sind positive ganze Zahlen und werden als `v1`, `v2` usw. ohne Auffüllung geschrieben. Bestehende Dateien werden nicht automatisch umbenannt.

Der Index wählt eine bestätigte ID-Version aus und verknüpft Plan-, Run- und Abschlussnachweise mit genau dieser Fassung. Ein Planname folgt `plan-G01-M02-v1-p01.md`; sein Lauf heißt `run-G01-M02-v1-p01-r01/`. `p01` ist die Planfassung, `r01` ein neuer Lauf; Resume und Review-Reparaturen behalten dieselbe Run-ID. Namen helfen bei der Prüfung, ersetzen aber weder exakte Pfade noch Bestätigung.

Siehe [Definitionsformat](milestone-format.md) für unveränderliche Milestone-Versionen und [Indexformat](milestone-index-format.md) für Auswahl- und Nachweisverweise. Diese Formate besitzen getrennte Daten; keines ist ein Ersatz für die jeweils anderen. Das frühere `milestone/v1` bleibt ausschließlich lesbar; es wird weder automatisch migriert noch mit den getrennten Formaten vermischt.

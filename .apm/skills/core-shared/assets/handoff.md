# Handoff

> Kompakte Kontextübergabe; keine Status-, Plan- oder Evidenzquelle. Diese Datei wird für jede neue Übergabe vollständig ersetzt.

## Ziel

- Nächster Workflow: `<core-execute | core-review>`
- Zweck: `<konkretes Ergebnis der nächsten Phase>`
- Run-ID: `<run-id oder nicht anwendbar>`

## Kanonische Eingaben

- Ziel: `<goal-id und exakter Pfad zu goal/v1 oder nicht anwendbar>`
- Index: `<exakter Pfad zu milestone-index/v1 oder nicht anwendbar>`
- Milestone: `<milestone-id, Versionsnummer und exakter Definitionspfad zu milestone-definition/v1 oder nicht anwendbar>`
- Bestätigter Plan: `<exakter Pfad zu plan/v1>`
- Runzustand: `<exakter Pfad zu state.yaml oder nicht anwendbar>`
- Repositorystand/Diff: `<reproduzierbare Referenz auf aktuellen Stand>`
- Taskresultate: `<exakte Pfade zu unveränderlichen task-result/v1-Versuchen oder lesbaren Legacy-Ergebnissen>`
- Review: `<exakter Pfad zu review.yaml oder nicht anwendbar>`

## Relevante Rahmenbedingungen

- `<bestätigter Planabschnitt oder belegte Projektinvariante>`
- `<Run-pass ist kein Etappen-/Gesamtabschluss; Folgefreigabe wird nicht durch Handoff erteilt>`

## Aktuelle Evidenz

- `<Akzeptanz- oder Check-ID>`: `<Pfad zur aktuellen Evidenz und kurze beobachtbare Aussage>`

## Bekannte Einschränkungen

- `<offene Evidenzlücke, blockierte Prüfung oder keine>`

## Fresh-Context-Anweisung

Lade die oben referenzierten Artefakte und den aktuellen Repositorystand neu. Verwende weder die Implementierungsdiskussion noch Chatverlauf, Honcho oder Provider-Memories als Source of Truth. Prüfe Pfade, Drift und Freshness vor Wiederverwendung vorhandener Evidenz.

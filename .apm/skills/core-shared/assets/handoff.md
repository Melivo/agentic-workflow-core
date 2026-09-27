# Handoff

> Kompakte Kontextübergabe; keine Status-, Plan- oder Evidenzquelle. Diese Datei wird für jede neue Übergabe vollständig ersetzt.

## Ziel

- Nächster Workflow: `<core-execute | core-review>`
- Zweck: `<konkretes Ergebnis der nächsten Phase>`
- Run-ID: `<run-id oder nicht anwendbar>`

## Kanonische Eingaben

- Bestätigter Plan: `<exakter Pfad zu plan/v1>`
- Runzustand: `<exakter Pfad zu state.yaml oder nicht anwendbar>`
- Repositorystand/Diff: `<reproduzierbare Referenz auf aktuellen Stand>`
- Taskresultate: `<exakte Pfade zu task-result/v1-Artefakten>`
- Review: `<exakter Pfad zu review.yaml oder nicht anwendbar>`

## Relevante Rahmenbedingungen

- `<bestätigter Planabschnitt oder belegte Projektinvariante>`

## Aktuelle Evidenz

- `<Akzeptanz- oder Check-ID>`: `<Pfad zur aktuellen Evidenz und kurze beobachtbare Aussage>`

## Bekannte Einschränkungen

- `<offene Evidenzlücke, blockierte Prüfung oder keine>`

## Fresh-Context-Anweisung

Lade die oben referenzierten Artefakte und den aktuellen Repositorystand neu. Verwende weder die Implementierungsdiskussion noch Chatverlauf, Honcho oder Provider-Memories als Source of Truth. Prüfe Pfade, Drift und Freshness vor Wiederverwendung vorhandener Evidenz.

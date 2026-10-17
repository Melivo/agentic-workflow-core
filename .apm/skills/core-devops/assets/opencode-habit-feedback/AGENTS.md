# OpenCode Habit Feedback

## Purpose

Originale Habit-Sensoren und den Original-Mapper begrenzt an OpenCode V2 anbinden.

## Ownership

- `adapter/` besitzt Prozessausführung, Ein-Datei-Scope und Vertrauensprüfungen.
- `hook/` besitzt Ereignisklassifikation, Zustand und begrenztes Feedback.
- `plugin/` besitzt den typisierten SDK-Hook und den Transport.
- `guides/` enthält die freigegebenen Mapper-Vorlagen, keine eigene Erkennung.

## Local Contracts

[README.md](README.md), [SDK-Vertrag](sdk-contract.md) und
[VERSIONS.md](VERSIONS.md) sind die bestehenden Detailquellen.
Erkennung und Routing bleiben bei den Originalwerkzeugen. Ungeprüfte Bereiche
werden als `not_scanned` gemeldet, nicht als sauber.

## Work Guidance

Keine Projektprogramme oder Projektvorlagen als vertrauenswürdig übernehmen.
Ein-Datei-Scope, Prozessbaum-Bereinigung, Zustandsisolation und unveränderte
Originalresultate erhalten. Laufzeithooks installieren und reparieren nichts.
Abgeleitete Pakete und Core-Snapshots nicht als zweite Quelle pflegen.

## Verification

Bestehende Prüfungen und ihre Grenzen stehen im
[Verifikationsabschnitt](README.md#verification-and-limits).
[check_habit_feedback.py](https://github.com/Melivo/agentic-workflow-core/blob/main/scripts/check_habit_feedback.py)
trennt Paketbau, Scratch-Installation und Hostintegration. Solche Wirkungen
benötigen weiterhin eigene Freigaben; Stubtests sind kein Hostnachweis.

## Child DOX Index

- No child DOX guides.

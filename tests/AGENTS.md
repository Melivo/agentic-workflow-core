# Vertrags- und Integrationstests

## Purpose

Workflowverträge, Portabilität, Sicherheit sowie Paket- und Integrationsgrenzen
mit den vorhandenen Regressionstests prüfen.

## Ownership

Dieser Bereich besitzt Tests und Szenariodaten. Produktionsverträge bleiben
unter [.apm/skills/](../.apm/skills/AGENTS.md), Prüf- und Paketwerkzeuge unter
[scripts/](../scripts/AGENTS.md). Die Konfigurator-Originaltests bleiben beim
[mitgelieferten Konfigurator](../.apm/skills/gortex-serena-configurator/AGENTS.md).

## Local Contracts

[ci_contract_targets.json](../scripts/ci_contract_targets.json) bestimmt die
Vertragsgruppen; [mise.toml](../mise.toml) die gemeinsamen Prüfeinstiege.
Szenariodaten liegen in `core_scenario_cases.json`; die Abdeckung
`S-dox-projektdokumentation` verlangt Positiv- und Negativfälle der DOX-Docsregeln,
Mutationstests entfernen die kanonischen DOX-Sätze nur im Speicher
und führen dort die früheren Drift-only-Klauseln von core-docs wieder ein. Paket- und Hosttests
benötigen ihre dokumentierte isolierte Toolchain. Pakettests verlangen den
quellengebundenen DOX-Skillindex, prüfen seine Links und weisen fehlende,
veränderte oder nicht aus den Quellen stammende Indexdateien zurück.

## Work Guidance

Tests mit dem fachlich verantwortlichen Vertrag abgleichen, nicht zur bloßen
Beseitigung eines Fehlers abschwächen. Kontrollierte Stubs, echte Werkzeuge
und tatsächliche Hostintegration in Nachweisen klar unterscheiden.
Keine globalen Provider oder Benutzerkonfiguration als Testnebenwirkung ändern.
`test_project_block_reconcile.py` führt den Init-Helper in temporären Projekten
aus und prüft Auswahl, Vorschau-/Bestätigungsbindung, Markerfehler, Fakten- und
Byteerhaltung sowie den diff-freien Zweitlauf ohne Provideraktionen.

## Verification

`mise run check` aus der Repositorywurzel führt Vertrags- und
Portabilitätsprüfungen mit der vorbereiteten Toolchain aus. Paketbau und
Scratch-Installationen bleiben gesondert freigabepflichtig; ein fehlendes
Werkzeug ist kein bestandener Test.

## Child DOX Index

- No child DOX guides.

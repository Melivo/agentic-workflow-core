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
Szenariodaten liegen in `core_scenario_cases.json`. Paket- und Hosttests
benötigen ihre dokumentierte isolierte Toolchain. Pakettests verlangen den
quellengebundenen DOX-Skillindex, prüfen seine Links und weisen fehlende,
veränderte oder nicht aus den Quellen stammende Indexdateien zurück.

## Work Guidance

Tests mit dem fachlich verantwortlichen Vertrag abgleichen, nicht zur bloßen
Beseitigung eines Fehlers abschwächen. Kontrollierte Stubs, echte Werkzeuge
und tatsächliche Hostintegration in Nachweisen klar unterscheiden.
Keine globalen Provider oder Benutzerkonfiguration als Testnebenwirkung ändern.

## Verification

`mise run check` aus der Repositorywurzel führt Vertrags- und
Portabilitätsprüfungen mit der vorbereiteten Toolchain aus. Paketbau und
Scratch-Installationen bleiben gesondert freigabepflichtig; ein fehlendes
Werkzeug ist kein bestandener Test.

## Child DOX Index

- No child DOX guides.

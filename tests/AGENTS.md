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
`S-dox-projektdokumentation` und die `g04-*`-Abdeckungen (Autorisierungsrahmen,
Aufwand/Geldkosten, Reparaturfortsetzung, Sicherheitsannahmen, Delegation,
Katalog ohne starres Limit) verlangen Positiv- und Negativfälle ihrer Regeln,
Mutationstests entfernen die kanonischen DOX-Sätze nur im Speicher
und führen dort die früheren Drift-only-Klauseln von core-docs wieder ein. Paket- und Hosttests
benötigen ihre dokumentierte isolierte Toolchain. Ersatzplantests verbinden
die vorhandenen Rahmen-/Ziel-/Kosten-/Wirkungsfixtures mit den konkreten
Ablaufquellen und weisen die Wiedereinfügung alter zwingender
Bestätigungsklauseln auch bei erhaltener positiver Rahmenprosa zurück. Pakettests verlangen den
quellengebundenen DOX-Skillindex, prüfen seine Links und weisen fehlende,
veränderte oder nicht aus den Quellen stammende Indexdateien zurück; die
synthetischen Archiv-/Installationsfixtures decken zusätzlich Aufnahme und
Ablehnung fehlender oder verkürzter `core-shared/THIRD_PARTY_NOTICES.md`-Notice
samt Report-Lizinventar ab, ohne realen Paketbau. Satzbasierte Positiv-/Negativfälle
und In-Memory-Mutationen sichern die kanonischen Messvergleichsklauseln (Auslöser,
gleiche Methode/Daten/Umgebung, Rauschen, fehlende Evidenz, unabhängige Grenzen)
statisch, ohne neuen Szenario- oder Orakelmechanismus.

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

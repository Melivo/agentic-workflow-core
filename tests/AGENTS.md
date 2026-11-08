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
und führen dort die früheren Drift-only-Klauseln von core-docs wieder ein.
Paket- und Hosttests benötigen ihre dokumentierte isolierte Toolchain.
Ersatzplantests verbinden
die vorhandenen Rahmen-/Ziel-/Kosten-/Wirkungsfixtures mit den konkreten
Ablaufquellen und weisen die Wiedereinfügung alter zwingender
Bestätigungsklauseln auch bei erhaltener positiver Rahmenprosa zurück.
Pakettests verlangen den quellengebundenen DOX-Skillindex, prüfen seine Links
und weisen fehlende,
veränderte oder nicht aus den Quellen stammende Indexdateien zurück; die
synthetischen Archiv-/Installationsfixtures decken zusätzlich Aufnahme und
Ablehnung fehlender oder verkürzter `core-shared/THIRD_PARTY_NOTICES.md`-Notice
samt Report-Lizinventar ab, ohne realen Paketbau. Satzbasierte Positiv-/Negativfälle
und In-Memory-Mutationen sichern die kanonischen Messvergleichsklauseln (Auslöser,
gleiche Methode/Daten/Umgebung, Rauschen, fehlende Evidenz, unabhängige Grenzen)
statisch, ohne neuen Szenario- oder Orakelmechanismus. Die Abdeckungen
`execute-direkt-eingang`, `execute-freigabevorrang` und `execute-zusatzdelegation`
modellieren exklusive Plan-/Direkteingänge samt Legacy-`plan_path`, verlorene oder
gebundene Planarbeit, Scopegrenzen, Resume-/Reviewgrundlage, Freigabe ohne
Änderungsauftrag sowie Owner-/Dispatchgrenzen; In-Memory-Mutationen entfernen die
Direktklauseln, fügen Ausweitungen ein oder kehren die Negativklausel zur
Freigabe ohne Änderungsauftrag um. Das belegt statische Konsistenz,
keine reale Agentenbefolgung. `test_core_contracts.py` lädt zusätzlich den
Habit-Producer pfadbezogen (ohne main/package/stage) und prüft dessen
bestehendes `check_links` auf der `CORE_FILES`-Snapshotmenge im Speicher,
positiv und mit entferntem `direct-mode.md`; das ist SDK-/TypeScript-unabhängig.
Der M02-Methodenerhaltstest nutzt `link_findings` aus
`check_design_principles.py` für Ziele und Anker von `method-preservation.md`
samt direktem bedingtem Einstieg aus `core-shared/SKILL.md`; `workflow-contract.md`
und `core-devops/SKILL.md` brauchen nur ihre Geltungs-/Autorenbedingungen, keine
eigene Linkkante. In-Memory-Mutationen brechen Anker, Ziele außerhalb `core-*`,
private Laufzeitpfade, Einstieg, Einstiegsbedingungen sowie Autoritäts- und
Rechteklauseln. Das ist statische Konsistenz, keine M05-Abnahme.

Die Handoff-Abdeckungen `handoff-planungsbefugnis`, `handoff-erstplan-halt`
und `handoff-sichtbare-anzeige` verwenden dieselben Szenariodaten und
Prüfhelpers: bestätigte Auswahl und Abhängigkeiten, begrenzte Indexänderung,
eine statisch validierte Draft-Datei, unabhängiges Review, vollständige Anzeige
und neue Erstplanfreigabe bleiben getrennt. In-Memory-Mutationen entfernen
Quellklauseln oder ergänzen widersprechende Freigabe-/Anzeigebehauptungen.
Native Anzeige, anderer Harness, OS-Fallback und Headless-/Fehlerfall sind
modellierte Beziehungen, keine tatsächlichen GUI- oder Modellnachweise.
Execute-Draft-Ablehnung und technische Ersatzplanregeln bleiben separat geprüft.

Die M04-Auswahltests sichern den gemeinsamen Zusatzmethodenvertrag mit
Positiv-/Negativklauseln und In-Memory-Mutationen sowie alle zwölf Profilowner,
Shared-Einstiege und lokale Link-/Ankerziele über vorhandene Prüfhelpers ab.
Externe Lesegrenzen werden nur als Vertragstext geprüft; weder echte
Methodenverfügbarkeit noch Modellbefolgung oder M05-Praxisabnahme folgen daraus.

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

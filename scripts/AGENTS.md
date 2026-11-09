# Prüf- und Paketwerkzeuge

## Purpose

Gemeinsame lokale und CI-Prüfungen sowie getrennte Paket- und Releasewerkzeuge
bereitstellen.

## Ownership

Dieser Bereich besitzt Bootstrap, Prüfer, Toolchain-Pins, Paketproducer und
Releaseentscheidungen. `habit-ci/` besitzt die gepinnte SDK-Testtoolchain;
`package.json` und Lockdatei halten die private Release-Toolchain.
Die Workflowverkabelung bleibt unter
[.github/workflows/](../.github/workflows/AGENTS.md).

## Local Contracts

- [mise.toml](../mise.toml) definiert die gemeinsamen Einstiegspunkte.
- [ci_toolchain.json](ci_toolchain.json) und Requirements/Lockdateien bestimmen
  Versionen und Integrität; keine stillen Installationen in Prüftasks.
- mise ist ein systemverwalteter Taskrunner: `mise.min_version` in
  `ci_toolchain.json` ist das zentrale Minimum und muss `min_version` in
  `mise.toml` entsprechen. Stabile neuere Systemupdates nicht durch exakte
  Host-Pins blockieren; RPM-Binary weder ersetzen noch herunterstufen.
  Bootstrap vergleicht die drei Versionsteile numerisch, lehnt fehlende,
  fehlgeschlagene, ungültige und Vorabversionsabfragen ab und meldet beobachtete
  Version und Minimum als `RUNTIME`. Python und alle anderen Pins bleiben exakt.
- [ci_contract_targets.json](ci_contract_targets.json) ordnet Vertragsgruppen zu.
- `check_core_contracts.py` prüft den
  [DOX-Vertrag](../.apm/skills/core-shared/references/workflow-contract.md#projektdokumentation-und-dox)
  über Klauselmuster in den Gruppen `shared`, `workflows` und `domains` sowie
  über modellierte `kind: docs`-Beziehungen (Baumzustand, Setupfreigabe, Belege,
  Secret- und Scopegrenzen). Zusätzlich prüft er das Fehlen des starren
  Reparaturlimits im Katalog und die evidenzbasierte Reparaturfortsetzung
  (neue Erkenntnis oder unterscheidbare prüfbare Hypothese, keine starre
  Rundenzahl) sowie die G04-Klauseln zu Aufwand/Geldkosten, Sicherheitsannahmen
  und delegierter Testbedienung. Das ist statische Konsistenz, kein Nachweis
  tatsächlicher Agentenbefolgung oder der Qualität realer Guides. Die Gruppe
  `workflows` prüft die Ersatzplan-Ablaufklauseln quellengebunden vom gemeinsamen
  Vertrag über Plan/Execute/Review bis Milestone und Goal-/Startprompt sowie die
  öffentlichen Verbraucher README.md und DESIGN.md, einschließlich
  widersprechender alter pauschaler Bestätigungsgates; situationsabhängige
  Nutzerbestätigung bleibt zulässig. `DIRECT_SOURCES` bindet zusätzlich die
  Direktmodus-, Freigabevorrang- und Zusatzdelegationsklauseln an Execute,
  `direct-mode.md`, Review, Workflow-/Artefakt-/Benutzeranweisungsvertrag und
  Handoff, einschließlich der quellengebundenen Negativklausel, dass bloßes
  „keine Freigabe nötig“ ohne Änderungsauftrag keine Ausführung autorisiert, und
  weist unverneinte Ausweitungen zurück; der Katalog muss für
  `core-execute` Plan- und `text`-Eingang ohne Planausgabe sowie die Eskalation
  an `core-plan` führen.
- `HANDOFF_SOURCES` bindet die Erstplan- und Gesamtfreigaberegeln an Workflow-,
  Artefakt-, Ziel-, Definitions-, Index-, Plan-, Review-, Execute-, Prompt-,
  Anzeige- und Routingquellen und weist den alten zwingenden
  Einzelplanhalt (`HANDOFF_LEGACY`) sowie Ausweitungen zurück. `kind: prompt`
  modelliert mit `purpose` `handoff-first-plan` oder `stage-first-plan` dieselbe
  Draft-Datei, getrennte Qualitäts-/Deckungsbelege (`coverage_gap`, Sicherheitsmaßnahmen
  nur per exaktem Rahmenabgleich) und den
  Planlink: `goal-covered` ersetzt nur `handoff-planning`, echte
  `user-confirmed`-Aktivierungen bleiben; `check_index` verlangt für
  `goal-covered` einen verknüpften Plan. `validate_plan` bleibt ausschließlich
  für ausführbare Confirmed-Pläne. Die Prüfung zeigt keine Pläne an und erteilt
  keine Autorisierung. Die `workflows`-Gruppe prüft zusätzlich quellenlokale
  Freigaberahmen-Klauseln (Reichweite, Klärung vor dem Schreiben, Einschränkungen)
  und den Stopgrund `planning_only`; Mutationen weisen unzulässige Erweiterung
  und unbegründete Verengung zurück. Das bleibt statische Konsistenz.
- `check_habit_feedback.py` führt in `CORE_FILES` die geschlossene transitive
  Markdown-Linkmenge des Core-Snapshots; neu verlinkte Quellen wie
  `core-execute/references/direct-mode.md` gehören als exakter Eintrag hinein.
- Der Paketproducer prüft den kanonischen DOX-Skillindex und alle Skilldateien
  bytegenau sowie relative Links innerhalb der Installation. Die Lizenzprüfung
  bindet `core-shared/LICENSE` und die Third-Party-Notices (`core-architecture`
  sowie `core-shared` mit vollständigem OMA-MIT-Hinweis) an die Quellen und weist
  sie im Paketreport unter `licenses` aus. Repositorywerkzeuge
  werden aus portablen Guides über ihre Repositoryquellen referenziert.
- Releaseentscheidungen liegen in `release_guard.py` und `publish_release.py`,
  nicht in einer zweiten Implementierung im Workflow.

## Work Guidance

Setup, reine Prüfung, Paketbau und Veröffentlichung als getrennte Wirkungen
behandeln. Isolierten `AWC_CI_WORKSPACE` nutzen; keine globalen Werkzeuge oder
Benutzerkonfiguration beiläufig ändern. Versions- und Hashquellen gemeinsam
mit ihren vorhandenen Tests konsistent halten.

## Verification

Aus der Repositorywurzel: `mise run check`, `mise run version:check`,
`mise run release:test`, `mise run workflows:check` und `mise run docs:check`.
`tools:setup` installiert; `acceptance` baut und installiert ein Testpaket.
Keine dieser zusätzlichen Wirkungen aus einer Dokumentationsänderung ableiten.

## Child DOX Index

- No child DOX guides.

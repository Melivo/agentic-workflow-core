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
- `typesafe_collection.py` ist eine getrennte, explizit bediente minimierte Vergleichssammlung; CLI und Datenstandard stehen in der [Operationsreferenz](../docs/operations/typesafe-collection.md). Die einzige Implementierung liegt im portablen `core-typesafe`-Bundle; dieses Repositoryskript lädt sie lediglich kompatibel. Der vorhandene Runtimecheck bleibt an seinen historischen Pi-Quellhash gebunden und verweigert ungeprüfte neue Runtimebytes; daraus folgt keine neue Betriebsabnahme.
- Das portable `core-typesafe`-Bundle enthält `build_request`, `finalize_response` und den bestehenden HTTPS-Transport; die Modul-API verbindet sich nicht selbst mit MCP-Tools. Harnessintegration und optionale Toolverfügbarkeit werden im [TypeSafe-Vertrag](../.apm/skills/core-shared/references/typesafe-contract.md) beschrieben, nicht durch ein neues Runner- oder Setupskript.
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
  Vertrag über Plan/Execute/Review bis Milestone. Für Erstplan- und
  Gesamtfreigaberegeln erfasst `HANDOFF_SOURCES` die jeweiligen Ownerquellen
  einschließlich des verbleibenden Startprompts. Die öffentlichen Verbraucher
  README.md und DESIGN.md prüft sie ebenfalls, einschließlich
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
- `check_completion_ref` akzeptiert sichere projektrelative Originalquellen und
  Vorgängerrun-Evidenz gemäß Indexvertrag. Plan-/Run-/Reviewbindung und
  Versionsrevalidierung bleiben getrennte Prüfungen; Pfadsyntax belegt weder
  Dateiexistenz noch inhaltliche Kriterienerfüllung.
- `check_habit_feedback.py` führt in `CORE_FILES` die geschlossene transitive
  Markdown-Linkmenge des Core-Snapshots; neu verlinkte Quellen wie
  `core-execute/references/direct-mode.md` gehören als exakter Eintrag hinein.
  Die direkt verlinkten Owner-/Collectorquellen `typesafe_owner.py` und
  `typesafe_collection.py` gehören ebenso exakt ins statische Link-/Byteinventar.
  Die Default- und Fehlerklauseln des regulären Planreview-Versuchs prüft
  `check_core_contracts.py` quellengebunden, ohne Modellaufruf oder Agentengarantie.
  Die direkten Bildreferenzziele `image_probe.py` und `cases.json` sind darin
  bytegebundene statische Quellen, kein ausführbares Evaluationsbundle;
  Bildfixtures bleiben im vollständigen kanonischen `core-typesafe`-Bundle.
- Der Paketproducer prüft den kanonischen DOX-Skillindex und alle Skilldateien
  bytegenau sowie relative Links innerhalb der Installation. Die Lizenzprüfung
  bindet `core-shared/LICENSE` und die Third-Party-Notices (`core-architecture`
  sowie `core-shared` mit vollständigem OMA-MIT-Hinweis) an die Quellen und weist
  sie im Paketreport unter `licenses` aus. Repositorywerkzeuge
  werden aus portablen Guides über ihre Repositoryquellen referenziert.
- `release_guard.CORE_BUNDLES` besitzt das Sollinventar für Paketprüfer und Report
  (23, einschließlich `core-typesafe`). Dokumentierte Bundlezahlen und
  Bestandstests müssen mit dem kanonischen Quelleninventar übereinstimmen.
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

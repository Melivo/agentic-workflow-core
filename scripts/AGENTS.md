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
- [ci_contract_targets.json](ci_contract_targets.json) ordnet Vertragsgruppen zu.
- Der Paketproducer prüft den kanonischen DOX-Skillindex und alle Skilldateien
  bytegenau sowie relative Links innerhalb der Installation. Repositorywerkzeuge
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

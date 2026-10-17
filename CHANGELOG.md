# Changelog

## Unreleased — M02 (nicht veröffentlicht)

- Ergänzt reproduzierbare lokale/CI-Prüfungen und eine standardmäßig deaktivierte, getrennte Release-PR- und Veröffentlichungskette. GitHub-Livebetrieb und App-Einrichtung sind nicht bestätigt.

## [0.6.1](https://github.com/Melivo/agentic-workflow-core/compare/v0.6.0...v0.6.1) (2026-10-17)


### Bug Fixes

* **init:** prepare configurator runtime before project audit ([c2f7ab9](https://github.com/Melivo/agentic-workflow-core/commit/c2f7ab972b9ffeb19c93b903da68170f6e188973))

## [0.6.0](https://github.com/Melivo/agentic-workflow-core/compare/v0.5.0...v0.6.0) (2026-10-17)


### Features

* **ci:** add reproducible checks and gated release automation ([0f4d377](https://github.com/Melivo/agentic-workflow-core/commit/0f4d37729fa8937cc4dc15fa85db0e6fc62ac440))
* **core:** add scoped Habit Hooks feedback plugin ([be589ce](https://github.com/Melivo/agentic-workflow-core/commit/be589ce5aa170026bb32328a2cad5695f53e0ba5))
* **core:** distinguish behavior requirements from implementation decisions ([891a1ce](https://github.com/Melivo/agentic-workflow-core/commit/891a1ce1383729c87d26e8f0e6c8c4a542c9fcc6))
* **core:** enforce goal-bound scope and independent plan reviews ([104430c](https://github.com/Melivo/agentic-workflow-core/commit/104430c384312b0547f4b89af3371380dac3296f))
* **core:** enforce portable cross-domain design principles ([c198395](https://github.com/Melivo/agentic-workflow-core/commit/c19839565058d0ce1f888060ffac893f7acb0d05))
* **core:** migrate Gortex Serena configurator into canonical package ([d003415](https://github.com/Melivo/agentic-workflow-core/commit/d0034153b754309c70109d2d611c304a491bb794))


### Bug Fixes

* **ci:** prepare pinned Habit feedback test toolchain ([546beae](https://github.com/Melivo/agentic-workflow-core/commit/546beae56d7f6d4871ddedc9523547df2861a0dc))
* **ci:** preserve documentation contracts across README rewrites ([9624a13](https://github.com/Melivo/agentic-workflow-core/commit/9624a135a54a8fa9c065aced60387dc3976c27dc))
* **init:** exclude private workflow and Serena artifacts ([c26526d](https://github.com/Melivo/agentic-workflow-core/commit/c26526d0f2210dc68e322edf6e68134bdcc35d15))
* **release:** allow publisher to complete pull request labels ([447f889](https://github.com/Melivo/agentic-workflow-core/commit/447f8899428660acdbc9b3c291871f65e2a9bb40))
* **tests:** preserve optional local OpenCode config state ([8860d96](https://github.com/Melivo/agentic-workflow-core/commit/8860d961587c65f943d180a3d9fde5c3d9869535))

## 0.5.0 (2026-10-17)

- Core-Planung trennt fachliche Verhaltensanforderungen von technischen
  Umsetzungsentscheidungen und ihren Freigabegrenzen.
- DOX-Tree mit lokalen Zuständigkeiten und direkten Kindindizes sowie
  aktualisiertes Core-Routing für dieses Repository ergänzt.
- Pauschalen Git-Ausschluss für AGENTS.md entfernt; private Workflowartefakte
  und Serena-Zustand bleiben ausgeschlossen.
- Projekt-Init schützt lokale Workflow- und Serena-Artefakte vor versehentlicher
  Versionierung.
- Mise 2026.10.11 über lokale Prüfungen und CI hinweg einheitlich gepinnt.
- Paketverifikation prüft den DOX-Skillindex quellengebunden; DOX-Links bleiben
  auch nach der APM-Installation auflösbar.

## [0.4.0](https://github.com/Melivo/agentic-workflow-core/compare/v0.3.1...v0.4.0) (2026-10-15)

### Features (0.4.0)

- **core:** integrate routed research into debug, plan, execute and review workflows

## [0.3.1](https://github.com/Melivo/agentic-workflow-core/compare/v0.3.0...v0.3.1) (2026-10-14)

### Bug Fixes (0.3.1)

- **release:** allow publisher to complete pull request labels ([447f889](https://github.com/Melivo/agentic-workflow-core/commit/447f8899428660acdbc9b3c291871f65e2a9bb40))

## [0.3.0](https://github.com/Melivo/agentic-workflow-core/compare/v0.2.1...v0.3.0) (2026-10-14)

### Features (0.3.0)

- **ci:** add reproducible checks and gated release automation ([0f4d377](https://github.com/Melivo/agentic-workflow-core/commit/0f4d37729fa8937cc4dc15fa85db0e6fc62ac440))
- **core:** add scoped Habit Hooks feedback plugin ([be589ce](https://github.com/Melivo/agentic-workflow-core/commit/be589ce5aa170026bb32328a2cad5695f53e0ba5))
- **core:** enforce portable cross-domain design principles ([c198395](https://github.com/Melivo/agentic-workflow-core/commit/c19839565058d0ce1f888060ffac893f7acb0d05))
- **core:** migrate Gortex Serena configurator into canonical package ([d003415](https://github.com/Melivo/agentic-workflow-core/commit/d0034153b754309c70109d2d611c304a491bb794))

### Bug Fixes (0.3.0)

- **ci:** prepare pinned Habit feedback test toolchain ([546beae](https://github.com/Melivo/agentic-workflow-core/commit/546beae56d7f6d4871ddedc9523547df2861a0dc))
- **ci:** preserve documentation contracts across README rewrites ([9624a13](https://github.com/Melivo/agentic-workflow-core/commit/9624a135a54a8fa9c065aced60387dc3976c27dc))
- **tests:** preserve optional local OpenCode config state ([8860d96](https://github.com/Melivo/agentic-workflow-core/commit/8860d961587c65f943d180a3d9fde5c3d9869535))

## 0.2.1

- Fehlerkorrektur (Patchrelease).

## 0.2.0

- Paket `core-devops` hinzugefügt.

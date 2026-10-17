# Gortex-/Serena-Konfigurator

## Purpose

Den Gortex-first-Preflight und ausdrücklich ausgewählte Serena-Einrichtung
für ein konkretes Projekt bereitstellen.

## Ownership

Dieser Bereich besitzt den mitgelieferten Konfigurator samt Skripten,
Originaltests und Herkunftsnachweisen. Beim Inline-Aufruf durch
[core-init-project](../core-init-project/SKILL.md) bleibt dessen Projektblock
bei diesem aufrufenden Skill.

## Local Contracts

- [SKILL.md](SKILL.md) definiert Auswahl und Autorisierung.
- [Konfigurationsrangfolge](references/configuration-precedence.md) bestimmt
  Quelle, Projektscope, Sprachen und Timeout-Einheiten.
- [REQUIREMENTS.md](REQUIREMENTS.md) und
  [requirements.txt](scripts/requirements.txt) benennen Laufzeitabhängigkeiten.
- [PROVENANCE.md](PROVENANCE.md) und `LICENSE` erhalten.

## Work Guidance

Ohne ausgewählte Schreibaktion bleibt der Audit read-only. Nur die bestätigte
Konfigurationsquelle ändern, keine generierten Projektionen. Kein globales
Serena-MCP und kein automatisches Gortex-Tracking einrichten. Fehlende
Abhängigkeiten sichtbar melden; ihre Installation ist keine Auditwirkung.

## Verification

Vorhandene Regressionstests:
[Originaltests](scripts/test_serena_safety.py) und
[Repositoryintegration](https://github.com/Melivo/agentic-workflow-core/blob/main/tests/test_gortex_serena_configurator.py).
Repositoryprüfungen über `mise run check` aus der Wurzel; ein Konfigurationsaudit
benötigt die dokumentierten Python-Abhängigkeiten.

## Child DOX Index

- No child DOX guides.

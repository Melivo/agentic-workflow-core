# Kanonische Skills

## Purpose

Die Core-Workflows, Fachmethoden und ihre unmittelbar benötigten Ressourcen
als portable Skill-Bundles bereitstellen. Dieser Guide gilt ausschließlich für
die `core-*`-Skills und `gortex-serena-configurator` dieses Pakets, nicht für
andere daneben installierte Skills.

## Ownership

Dieser Bereich besitzt die `core-*`-Bundles und den mitgelieferten
Konfigurator. Jeder Skill behält Ablauf, Scope und Fachmethodik in seiner
`SKILL.md`. Referenzen und Assets bleiben beim fachlich verantwortlichen Bundle.
Gemeinsame Verträge, Konfigurator und ausführbares Feedbackpaket haben die
unten verlinkten eigenen Guides.

## Local Contracts

- [core-shared](core-shared/SKILL.md) verlinkt die gemeinsamen Verträge.
- Verzeichnisname und Frontmatter-`name` eines Skills stimmen überein.
- Kanonische Quellen nicht durch Änderungen installierter Harnesskopien ersetzen.
- Herkunfts- und Lizenznachweise bei übernommenen Ressourcen erhalten.

## Work Guidance

Nur die für den Auftrag passende Methodik und Referenzen laden. Keine
Workflowzustände in Skills oder Provider-Memories ablegen. Änderungen an
Verträgen, Vorlagen und konsumierenden Skills gemeinsam auf Konsistenz prüfen,
ohne unautorisierte Folgeworkflows zu starten.
`core-init-project` prüft vor dem Konfigurator-Audit dessen deklarierte
Python-Laufzeitabhängigkeiten; eine isolierte Einrichtung benötigt eine eigene
ausdrückliche Installationsfreigabe.

## Verification

`mise run check` aus der Repositorywurzel prüft die bestehenden Verträge;
`mise run docs:check` die Dokumentationsgruppe. Paketbau und Testinstallation
sind getrennte Wirkungen, siehe
[Repository-README](https://github.com/Melivo/agentic-workflow-core/blob/main/README.md).
Installierte Verbraucher führen diese Repositoryprüfungen nicht automatisch aus.

## Child DOX Index

- [core-shared](core-shared/AGENTS.md) — gemeinsame Verträge und Vorlagen.
- [Konfigurator](gortex-serena-configurator/AGENTS.md) — Provider-Preflight und
  ausdrücklich ausgewählte Einrichtung.
- [Habit Feedback](core-devops/assets/opencode-habit-feedback/AGENTS.md) —
  eigenständiges OpenCode-Plugin mit Adapter, Hook und Mapper-Guides.

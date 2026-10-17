# Kanonische Paketquelle

## Purpose

Die installierbaren Skill-Bundles und nativen Fachagentenprofile des Pakets
besitzen; installierte Harnessprojektionen sind keine zweite Quelle.

## Ownership

Dieser Bereich besitzt die Paketquellen unter `skills/` und `agents/`.
Paketmanifest und übergreifende Projektdokumentation bleiben in der
Repositorywurzel; Prüf-, Build- und Releasewerkzeuge bleiben unter
[scripts/](../scripts/AGENTS.md).

## Local Contracts

- [apm.yml](../apm.yml) definiert Paketidentität, Ziele und Abhängigkeiten.
- Die [gemeinsamen Verträge](skills/core-shared/SKILL.md) bestimmen Autorisierung,
  Artefakte, Toolrouting und Verifikation.
- Fremde Ressourcen behalten ihre Herkunfts- und Lizenznachweise.

## Work Guidance

Quellen statt generierter oder installierter Kopien ändern. Skillmethodik und
Rollenprofile getrennt halten; keine zusätzliche Orchestrierungs-CLI einführen.
Modell-, Provider- und Paketinstallationsänderungen brauchen einen passenden
Auftrag und sind keine automatische Folge einer Quellenänderung.

## Verification

Gemeinsame Einstiegspunkte stehen in [mise.toml](../mise.toml).
`mise run check` prüft die bestehenden Verträge mit vorbereiteter Toolchain;
Paketabnahme über `acceptance` baut und installiert zusätzlich und benötigt
eine gesonderte Freigabe.

## Child DOX Index

- [Skills](skills/AGENTS.md) — Workflows, Fachmethoden und ihre Ressourcen.
- [Fachagenten](agents/AGENTS.md) — native Rollenprofile und Skillzuordnung.

# CI und Releaseautomation

## Purpose

Unprivilegierte Änderungsprüfungen und privilegierte Releasewirkungen getrennt
orchestrieren.

## Ownership

Dieser Bereich besitzt Auslöser, Jobabhängigkeiten, Rechte und Artefaktübergaben
von [ci.yaml](ci.yaml) und [release.yaml](release.yaml).
Fachliche Releaseentscheidungen bleiben bei den
[Werkzeugen unter scripts/](../../scripts/AGENTS.md).

## Local Contracts

- CI nutzt die gemeinsamen Tasks aus [mise.toml](../../mise.toml), nur lesende
  Repositoryrechte und keine Veröffentlichungssecrets.
- Release-PR und Veröffentlichung haben getrennte Schalter:
  `RELEASE_PR_AUTOMATION_ENABLED` und `RELEASE_PUBLICATION_ENABLED`.
- Fehlende oder nicht exakt auf `true` gesetzte Schalter erlauben keine Wirkung.
- Veröffentlichung prüft den exakten Merge-Commit sowie Paketversion und Hash;
  ein normaler Push ist keine Releasefreigabe.

## Work Guidance

Untrusted PR-Ausführung nicht mit privilegierten Releasejobs vermischen.
Gepinnte Actions, minimale Jobrechte, getrennte Identitäten und geprüfte
Artefaktübergaben erhalten. Keine Secrets ausgeben; bestehende Tags und
Releaseassets nicht beiläufig überschreiben.

## Verification

Aus der Repositorywurzel: `mise run workflows:check` für Actionlint und die
Workflowtests; `mise run release:test` für die Release-/Pakettests.
Eine Guide-Änderung autorisiert weder Workflowauslösung noch Veröffentlichung.

## Child DOX Index

- No child DOX guides.

# Agentic Workflow Core

Die kanonische Paketquelle liegt unter `.apm/`. Verwende die passenden Skills aus `.apm/skills/core-*/`; installierte Harness-Kopien sind keine Paketquelle.

## Verträge

- [Workflowvertrag](.apm/skills/core-shared/references/workflow-contract.md): Autorisierung, Rückfragen, Scope und Abschluss.
- [Artefaktvertrag](.apm/skills/core-shared/references/artifact-contract.md): Plan, Run, Review und Wiederaufnahme.
- [Toolrouting](.apm/skills/core-shared/references/tool-routing.md): Gortex zuerst, ausdrücklich eingerichtetes projektspezifisches Serena als Fallback, danach native Werkzeuge.
- [Verifikation](.apm/skills/core-shared/references/verification.md): aktuelle Nachweise und Grenzen der Qualitätsprüfungen.

## Arbeit im Projekt

<!-- CORE-INIT-PROJECT:START -->
## Projektbasis

- Quellen: Markdown-Skills und YAML-Verträge unter `.apm/skills/`, native Fachagentenprofile unter `.apm/agents/`. Prüf- und Paketwerkzeuge liegen unter `scripts/`, Vertragstests unter `tests/`.
- Task Runner: `mise`; qualifizierte Prüflaufzeit: Linux x64 mit Python 3.13.14.
- Checks: `mise run check`, `mise run version:check`, `mise run release:test`, `mise run workflows:check` und `mise run docs:check`.
- `mise run tools:setup` installiert Werkzeuge; `mise run acceptance` baut und installiert zusätzlich ein Testpaket. Diese Wirkungen benötigen eine ausdrückliche Freigabe.
- Code-Intelligence: Gortex → ausdrücklich eingerichtetes projektspezifisches Serena → native Werkzeuge, jeweils gemäß Toolrouting. Keine automatische Providerinstallation oder Änderung am Tracking.

## Core-Routing und Übergaben

- **Einstieg:** Bei materiell unklarer Richtung `core-brainstorm`, bei klarem Vorhaben ohne Plan `core-plan`, für ausdrücklich gewünschte Ausführung oder Wiederaufnahme eines bestätigten Plans `core-execute`, bei Sitzungswechsel `core-handoff`. `core-milestone` nur für ausdrücklich gewählte Etappenplanung. Empfehlungen starten keinen Workflow und erteilen keine Freigabe.
- **Autorisierte Arbeit:** Innerhalb bestehender Freigabe erforderliche Prüfungen und unabhängiges `core-review` in frischem Kontext durchführen; nicht bei „Implementierung fertig“ enden. Interne Übergänge brauchen keine erneute Bestätigung. Neue Ziele, Scopeänderungen, Folgeetappen und gesondert freigabepflichtige Aktionen benötigen eigene Autorisierung. Reparatur- und Stopgrenzen des zuständigen Skills gelten.
- **Etappenabschluss:** Nach Run-pass eine etwaige Milestone-Bindung prüfen. Zusätzliche Kriterienprüfung und Indexnachweise gehören ausschließlich `core-milestone` und benötigen bestehende Autorisierung. Run-pass ist kein Etappen- oder Gesamtzielabschluss. Nach verifiziertem Milestone-Abschluss zwingend `core-handoff` mit den exakten Originalartefakten ausführen und den kopierbaren Startprompt im Chat ausgeben. Danach vor Auswahl, Planung oder Start der Folgeetappe stoppen. Eine zusätzliche Handoff-Datei braucht einen separat bestätigten Zielpfad. Bei nachweislich erfülltem Gesamtziel stattdessen den belegten Abschluss ohne erfundene Folgearbeit ausgeben. Ohne Etappenbindung entfällt dieser Zusatzschritt.
- **Fachmethoden:** Passende Methoden bedarfsabhängig innerhalb des autorisierten Workflows nutzen. Brainstorm und Plan verwenden Research, Architecture und Refactor-Safety-Net bei Bedarf inline. Ausschließlich Execute dispatcht Fachagenten und weist begrenztes Debugging zu. Für Backend, Frontend, Mobile, Datenbanken und Terraform die entsprechenden `core-*`-Methoden nutzen; Dokumentationsbedarf früh berücksichtigen. Keine pauschalen Agentenkaskaden.
- **Wiedereinstieg:** Ausdrücklich referenzierte Originalartefakte und aktuellen Repositorystand neu lesen. Keine Auswahl anhand vermeintlich neuester Dateinummern. Bei Sitzungswechsel über den zuständigen Eigentümer einen sicheren Haltepunkt herstellen und `core-handoff` anbieten. Fehlende Pfade oder Freigaben klären, nicht aus Chat oder Memory rekonstruieren. Ein Handoff erteilt keine Start- oder Folgefreigabe.
<!-- CORE-INIT-PROJECT:END -->

Pläne und Laufartefakte liegen unter `.agentic-workflow/`. Nutze für Fachagenten die nativen Harness-Profile; starte keine zusätzliche Orchestrierungs-CLI. Verändere keine Modell- oder Providerkonfiguration ohne passenden Auftrag.

Kein Build, Compile, Bundle, Packaging, keine Installation, SCM-Operation oder Veröffentlichung ohne ausdrückliche Freigabe. Schreibe verständlich auf Deutsch und erkläre notwendige Fachbegriffe kurz auf CS50-Einstiegsniveau.

<!-- DOX:START -->
## DOX framework

- DOX is highly performant AGENTS.md hierarchy installed here
- Agent must follow DOX instructions across any edits

### Core Contract

- AGENTS.md files are binding work contracts for their subtrees
- Work products, source materials, instructions, records, assets, and durable
  docs must stay understandable from the nearest applicable AGENTS.md plus every
  parent AGENTS.md above it

### Read Before Editing

1. Read the root AGENTS.md
2. Identify every file or folder you expect to touch
3. Walk from the repository root to each target path
4. Read every AGENTS.md found along each route
5. If a parent AGENTS.md lists a child AGENTS.md whose scope contains the path,
   read that child and continue from there
6. Use the nearest AGENTS.md as the local contract and parent docs for repo-wide
   rules
7. If docs conflict, the closer doc controls local work details, but no child
   doc may weaken DOX

Do not rely on memory. Re-read the applicable DOX chain in the current session
before editing.

### Update After Editing

Every meaningful change requires a DOX pass before the task is done.

Update the closest owning AGENTS.md when a change affects:

- purpose, scope, ownership, or responsibilities
- durable structure, contracts, workflows, or operating rules
- required inputs, outputs, permissions, constraints, side effects, or artifacts
- user preferences about behavior, communication, process, organization, or
  quality
- AGENTS.md creation, deletion, move, rename, or index contents

Update parent docs when parent-level structure, ownership, workflow, or child
index changes. Update child docs when parent changes alter local rules. Remove
stale or contradictory text immediately. Small edits that do not change behavior
or contracts may leave docs unchanged, but the DOX pass still must happen.

### Hierarchy

- Root AGENTS.md is the DOX rail: project-wide instructions, global preferences,
  durable workflow rules, and the top-level Child DOX Index
- Child AGENTS.md files own domain-specific instructions and their own Child DOX
  Index
- Each parent explains what its direct children cover and what stays owned by
  the parent
- The closer a doc is to the work, the more specific and practical it must be

### Child Doc Shape

- Create a child AGENTS.md when a folder becomes a durable boundary with its own
  purpose, rules, responsibilities, workflow, materials, or quality standards
- Work Guidance must reflect the current standards of the project or user
  instructions; if there are no specific standards or instructions yet, leave it
  empty
- Verification must reflect an existing check; if no verification framework
  exists yet, leave it empty and update it when one exists

Default section order:

- Purpose
- Ownership
- Local Contracts
- Work Guidance
- Verification
- Child DOX Index

### Style

- Keep docs concise, current, and operational
- Document stable contracts, not diary entries
- Put broad rules in parent docs and concrete details in child docs
- Prefer direct bullets with explicit names
- Do not duplicate rules across many files unless each scope needs a local
  version
- Delete stale notes instead of explaining history
- Trim obvious statements, repeated rules, misplaced detail, and warnings for
  risks that no longer exist

### Closeout

1. Re-check changed paths against the DOX chain
2. Update nearest owning docs and any affected parents or children
3. Refresh every affected Child DOX Index
4. Remove stale or contradictory text
5. Run existing verification when relevant
6. Report any docs intentionally left unchanged and why

### User Preferences

When the user requests a durable behavior change, record it here or in the
relevant child AGENTS.md

### Child DOX Index

- [Paketquelle](.apm/AGENTS.md) — kanonische Skills und native Fachagentenprofile.
- [Werkzeuge](scripts/AGENTS.md) — Prüfungen, Toolchain, Paket- und Releasewerkzeuge.
- [Tests](tests/AGENTS.md) — Vertrags-, Sicherheits- und Integrationstests.
- [CI und Releases](.github/workflows/AGENTS.md) — Workflowauslöser, Rechte und
  Artefaktübergaben; fachliche Entscheidungen bleiben bei den Werkzeugen.
<!-- DOX:END -->

<!--
MIT License

Copyright (c) 2026 Agent Zero

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
-->

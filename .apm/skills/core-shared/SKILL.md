---
name: core-shared
description: Interner, domänenunabhängiger Vertragsindex für die vier Core-Workflows und ihre Artefakt-, Tool-, Verifikations- und Benutzeranweisungsgrenzen; kein öffentlicher Workflow.
---

# Shared Workflow Kernel

Dieses Bundle ist ein interner Index. Es führt keinen Workflow aus, dispatcht keine Agenten und speichert keinen Plan-, Run- oder Reviewstatus. Lade nur die für den aktuellen Verbraucher erforderlichen Verträge und Vorlagen.

## Verwendung

1. Bestimme die benötigte gemeinsame Grenze.
2. Lade genau die direkt verlinkte Referenz beziehungsweise Vorlage.
3. Belasse Workflow-Schritte, Frameworkwissen und Fachmethodik beim zuständigen `core-*`-Skill.
4. Verwende die kanonischen Repositoryartefakte als Sources of Truth; dieses Bundle ist keine zweite Orchestrierungs- oder Statusquelle.

## Verträge

- [Workflowvertrag](references/workflow-contract.md) — Autorisierung, Abbruch, Wiederaufnahme und Fresh-Context-Übergaben.
- [Artefaktvertrag](references/artifact-contract.md) — Eigentümer, Namens-/ID-Integrität, Aufbewahrung und Formate von Ziel, Definition, Index, Plan, Run, Handoff, Taskversuch, Taskresultat und Review.
- [Toolrouting](references/tool-routing.md) — Capability-basierte Providerauswahl und Fallbackgrenzen.
- [Verifikation](references/verification.md) — Evidenz, Pflichtchecks, blockierte Prüfungen und Reviewurteile.
- [Benutzeranweisungen](references/user-instructions-contract.md) — sichere Synchronisierung manueller `AGENTS.md`-Inhalte.

## Vorlagen und Routingmetadaten

- [Workflowkatalog](assets/workflow-catalog.yaml)
- [Handoffvorlage](assets/handoff.md)
- [Review-Findingvorlage](assets/review-finding.yaml)

Die Assets werden kopiert oder als Validierungsgrundlage gelesen. Sie ersetzen weder den bestätigten `plan/v1` noch `.agentic-workflow/runs/<run-id>/state.yaml`, Taskresultate oder `review.yaml`.

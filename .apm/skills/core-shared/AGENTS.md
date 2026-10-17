# Gemeinsame Core-Verträge

## Purpose

Gemeinsame Verträge und Vorlagen für die Core-Workflows bündeln.

## Ownership

Dieser Bereich besitzt `references/` und `assets/` für gemeinsame Grenzen.
[SKILL.md](SKILL.md) ist nur der interne Index; konkrete Abläufe und
Fachmethodik bleiben bei den konsumierenden Skills.

## Local Contracts

- [Workflowvertrag](references/workflow-contract.md): Freigaben und Scope.
- [Artefaktvertrag](references/artifact-contract.md): Formate und Eigentümer.
- [Toolrouting](references/tool-routing.md): Provider- und Fallbackgrenzen.
- [Verifikation](references/verification.md): Nachweise und Reviewgrenzen.
- [Benutzeranweisungen](references/user-instructions-contract.md): sichere
  Änderungen an manuellen Anweisungen.

## Work Guidance

Vertragsänderungen mit den betroffenen Verbrauchern und Vorlagen abgleichen.
Katalog und Assets sind kein Plan-, Run- oder Statusspeicher. Fachmethodik
nicht in den gemeinsamen Index verschieben.

## Verification

Bestehende Vertragsprüfungen: `mise run check` aus der Repositorywurzel.
Die betroffenen Gruppen stehen in
[ci_contract_targets.json](https://github.com/Melivo/agentic-workflow-core/blob/main/scripts/ci_contract_targets.json).

## Child DOX Index

- No child DOX guides.

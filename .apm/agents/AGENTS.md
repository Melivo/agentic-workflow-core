# Native Fachagentenprofile

## Purpose

Native Rollen für die vom Harness gestarteten Fachagenten bereitstellen.

## Ownership

Dieser Bereich besitzt Rollen, Ein-/Ausgaben und Scope der `.agent.md`-Profile.
Die Fachmethodik bleibt beim jeweils im Profil genannten Skill unter
[skills/](../skills/AGENTS.md); Workflowfreigaben bleiben beim aufrufenden Workflow.

## Local Contracts

- Profile verweisen auf ihren Eigentümer-Skill statt dessen Methodik zu kopieren.
- `docs-curator` nutzt für dauerhafte Dokumentation den gemeinsamen
  [DOX-Vertrag](../skills/core-shared/references/workflow-contract.md#projektdokumentation-und-dox)
  und die vorhandene Guide-Hierarchie; das Profil ergänzt keine zweite Methode.
- Fachagenten verwalten keinen eigenen Workflowzustand und starten keine Subagenten.
- Review bleibt unabhängig und implementiert keine Korrekturen; siehe
  [QA-Profil](qa-reviewer.agent.md).

## Work Guidance

Rollenänderungen mit dem zugehörigen Skill konsistent halten. Modell- und
Providerkonfiguration nicht ohne passenden Auftrag ändern. Generierte
Harnesskopien sind keine zweite Profilquelle.

## Verification

Die bestehenden Profil- und Paketverträge werden über `mise run check` aus der
Repositorywurzel geprüft; Einstieg:
[check_core_contracts.py](https://github.com/Melivo/agentic-workflow-core/blob/main/scripts/check_core_contracts.py).

## Child DOX Index

- No child DOX guides.

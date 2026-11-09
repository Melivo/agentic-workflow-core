# Gemeinsame Core-Verträge

## Purpose

Gemeinsame Verträge und Vorlagen für die Core-Workflows bündeln.

## Ownership

Dieser Bereich besitzt `references/` und `assets/` für gemeinsame Grenzen.
[SKILL.md](SKILL.md) ist nur der interne Index; konkrete Abläufe und
Fachmethodik bleiben bei den konsumierenden Skills.

## Local Contracts

- [Workflowvertrag](references/workflow-contract.md): Freigaben und Scope.
- [Artefaktvertrag](references/artifact-contract.md): Formate und Eigentümer, einschließlich request.md und unterscheidbarer Run-Eingangsreferenzen.
- [Toolrouting](references/tool-routing.md): Provider- und
  Fallbackgrenzen sowie die gemeinsame Auswahlregel für ergänzende
  Fachmethoden.
- [Verifikation](references/verification.md): Nachweise, Reviewgrenzen und bedarfsabhängige
  Messvergleich-Klarstellung.
- [TypeSafe-Vertrag](references/typesafe-contract.md): bedingte Bewertungs- und Datenprotokollgrenzen; keine aktive Phase.
- [Third-Party-Notices](THIRD_PARTY_NOTICES.md): gepinnte fremde Quellen und vollständige
  Lizenztexte der Vertragsübernahmen, derzeit die OMA-Messvergleich-Adaption.
- [Benutzeranweisungen](references/user-instructions-contract.md): sichere
  Änderungen an manuellen Anweisungen.
- [Methodenerhalt](references/method-preservation.md): bedingter Referenzindex
  für übernommene Methoden, Rechtegrenzen und Nichtübernahmen.
- [Projektdokumentation und DOX](references/workflow-contract.md#projektdokumentation-und-dox):
  gemeinsame Dokumentationsabdeckung, Baumprüfung und Setupgrenzen.

## Work Guidance

Vertragsänderungen mit den betroffenen Verbrauchern und Vorlagen abgleichen.
Katalog und Assets sind kein Plan-, Run- oder Statusspeicher. Fachmethodik
nicht in den gemeinsamen Index verschieben.

Toolrouting begrenzt native Projektermittlung auf Pfad-/Namenssuche vor
Projektzuordnung; bekannte Projekte behalten ihre Providerfolge und die
Home-Ausnahme bleibt separat. Serena-Readiness ist rein lesend, keine
Einrichtungs- oder Sprachabgleichfreigabe.

## Verification

Bestehende Vertragsprüfungen: `mise run check` aus der Repositorywurzel.
Die betroffenen Gruppen stehen in
[ci_contract_targets.json](https://github.com/Melivo/agentic-workflow-core/blob/main/scripts/ci_contract_targets.json).

## Child DOX Index

- No child DOX guides.

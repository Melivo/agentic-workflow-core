# Core Init Project

## Purpose

Repository-Preflight, verwaltete Projektanweisungen und die interne
Gortex-/Serena-Providerintegration für genau ein konkretes Projekt bereitstellen.

## Ownership

Dieses Bundle besitzt den öffentlichen Einstieg `SKILL.md`, den
stdlib-only-Blockabgleich, die internen Provider-Skripte und -Referenzen sowie
deren Originaltests und Herkunftsnachweise. Globale Benutzeranweisungen bleiben
bei `core-user2agent-instructions`; der Merge erzeugt keine neue globale
Schreibberechtigung. Übergeordnete Skillindizes und allgemeine Paketdokumentation
gehören ihren bisherigen Eigentümern.

## Local Contracts

- [SKILL.md](SKILL.md) ist der einzige öffentliche Skill-Einstieg.
- [Provider-Einrichtung](references/provider-setup.md) wird nur für
  Provider-Readiness, Laufzeitauflösung oder ausdrücklich ausgewählte
  Provideraktionen geladen.
- [Konfigurationsrangfolge](references/configuration-precedence.md) und
  [REQUIREMENTS.md](REQUIREMENTS.md) bleiben die fachlichen Besitzquellen.
- `scripts/serena_safety.py` besitzt die Provider-Audit-/Applylogik und die
  Serena/Gortex-Vorlagen; `scripts/reconcile_blocks.py` bleibt unabhängig und
  benötigt nur die Python-Standardbibliothek.
- `LICENSE` und [PROVENANCE.md](PROVENANCE.md) bleiben im Bundle.

## Work Guidance

Nur das konkrete Projekt initialisieren. Provideraktionen und Laufzeiteinrichtung
sind getrennt ausdrücklich zu autorisieren; Read-only-Probes installieren nichts.
Interpreter, Version und Import werden im tatsächlichen Runner geprüft. Bestehende
Current-/Legacy-Sprachschlüssel, Override-, Konflikt-, Home- und Applyschutzregeln
bleiben erhalten. Der reine Blockabgleich führt weder Provideraudit noch
`ruamel.yaml`-Auflösung aus.

Native Pfad-/Namenssuche vor Projektzuordnung ermittelt ausschließlich das
Projekt; unbekannte Dateien im bekannten Projekt bleiben in der Providerfolge.
Home-Ausnahme und rein lesende Readiness bleiben erhalten. Serena-Initialisierung,
Sprachabgleich und MCP-Konfiguration brauchen jeweils konkrete Projektfreigabe.
Markdownlint-Fallbacks werden nach `configuration-precedence.md` mit gelesener,
eindeutig zugeordneter Konfigurationsquelle belegt, nicht als privater Hostpfad
oder unaufgelöste „zentrale Config“ ins Paket übernommen.

Die Routingvorlage besitzt die endungsunabhängige Textprüfungspflicht mit
`context-debloater`: Skripte nur für unterstütztes Markdown, übrigen zugänglichen
Text nach geladener Rubrik manuell prüfen; Format-/Leselücken berichten.
Das Audit bleibt report-only und begründet keine Installation oder Kürzung.

## Verification

- Repositoryintegration: `tests/test_core_init_provider.py`.
- Originaltests: `scripts/test_serena_safety.py`.
- Blockabgleich: `tests/test_project_block_reconcile.py`.
- Paket- und Releaseverbraucher prüfen dieses eine Bundle einschließlich interner
  Providerdateien und weisen die frühere Standalone-Payload ab.

## Child DOX Index

- No child DOX guides.

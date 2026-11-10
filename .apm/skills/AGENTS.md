# Kanonische Skills

## Purpose

Die Core-Workflows, Fachmethoden und ihre unmittelbar benötigten Ressourcen
als portable Skill-Bundles bereitstellen. Dieser Guide gilt ausschließlich für
die `core-*`-Skills dieses Pakets, nicht für andere daneben installierte Skills.

## Ownership

Dieser Bereich besitzt die `core-*`-Bundles. Jeder Skill behält Ablauf, Scope
und Fachmethodik in seiner `SKILL.md`. Referenzen und Assets bleiben beim
fachlich verantwortlichen Bundle. Gemeinsame Verträge und ausführbares
Feedbackpaket haben die unten verlinkten eigenen Guides; Provider- und
Runtimeintegration ist eine interne Referenz von `core-init-project`. `core-execute` lädt Direktmodusdetails bedingt aus
`core-execute/references/direct-mode.md`; der gemeinsame Direktvertrag bleibt in
`core-shared`.

## Local Contracts

- [core-shared](core-shared/SKILL.md) verlinkt die gemeinsamen Verträge; die
  verbindliche [Auswahlregel für ergänzende Fachmethoden](core-shared/references/tool-routing.md#fachmethoden-erganzend-auswahlen)
  gilt für Fachagenten neben ihrem Eigentümer-Skill. Der TypeSafe-Vertrag gilt bei jedem Core-Planreview für den regulären minimierten
  Beobachtungsversuch sowie bei passenden Design-, Integrations- oder Evaluationsaufträgen;
  offene Beobachtung blockiert weder normales Review noch Produktarbeit.
- Verzeichnisname und Frontmatter-`name` eines Skills stimmen überein.
- Kanonische Quellen nicht durch Änderungen installierter Harnesskopien ersetzen.
- Herkunfts- und Lizenznachweise bei übernommenen Ressourcen erhalten.
- [Methodenerhalt](core-shared/references/method-preservation.md): bedingter Referenzindex für übernommene Fremdmethoden; keine zentrale Fachmethodik.

## Work Guidance

Nur die für den Auftrag passende Methodik und Referenzen laden. Keine
Workflowzustände in Skills oder Provider-Memories ablegen. Änderungen an
Verträgen, Vorlagen und konsumierenden Skills gemeinsam auf Konsistenz prüfen,
ohne unautorisierte Folgeworkflows zu starten. Dauerhafte Projektdokumentation
folgt der zuständigen Root-to-Target-AGENTS-Kette und dem gemeinsamen
[DOX-Vertrag](core-shared/references/workflow-contract.md#projektdokumentation-und-dox);
die einzelnen Skills beschreiben nur ihre jeweiligen Arbeitsschritte.
`core-init-project` lädt seine Provider- und Runtime-Methodik bei Bedarf aus
`core-init-project/references/provider-setup.md`; eine isolierte Einrichtung
benötigt eine passende ausdrückliche Installationsfreigabe. Der selektive
Abgleich verwalteter `AGENTS.md`-Blöcke läuft über den deterministischen Helper
im selben Bundle; Core-Routing und Serena/Gortex-Playbook bleiben bei ihren
Eigentümern und werden nicht dupliziert.

Bei Releaseautomation gilt in `core-devops` die
[Bestandsaufnahme vor Rückfragen](core-devops/references/ci-and-releases.md#releasebestand-zuerst-ermitteln);
belegte Releasekonventionen werden nicht erneut abgefragt.

## Verification

`mise run check` aus der Repositorywurzel prüft die bestehenden Verträge;
`mise run docs:check` die Dokumentationsgruppe. Paketbau und Testinstallation
sind getrennte Wirkungen, siehe
[Repository-README](https://github.com/Melivo/agentic-workflow-core/blob/main/README.md).
Installierte Verbraucher führen diese Repositoryprüfungen nicht automatisch aus.

## Child DOX Index

- [core-shared](core-shared/AGENTS.md) — gemeinsame Verträge und Vorlagen.
- [core-init-project](core-init-project/AGENTS.md) — Repository-Preflight,
  verwaltete Projektanweisungen und interne Providerintegration.
- [core-typesafe](core-typesafe/AGENTS.md) — portable, beratende TypeSafe-Bewertung
  mit drei Profilen; regulärer Planreview-Versuch bleibt daten- und kostenfreigabegebunden.
- [Habit Feedback](core-devops/assets/opencode-habit-feedback/AGENTS.md) —
  eigenständiges OpenCode-Plugin mit Adapter, Hook und Mapper-Guides.

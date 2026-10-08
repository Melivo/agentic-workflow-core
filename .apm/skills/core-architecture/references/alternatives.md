# Proportionaler Alternativenvergleich

Diese Fachmethode ändert weder Workflowsteuerung noch Autorisierung. Sie startet keine Agenten und erzeugt keinen zusätzlichen Plan. Eine Empfehlung außerhalb bestätigter Grenzen wird zurückgegeben, nicht implementiert.

<a id="m10--alternativenvergleich"></a>
## M10 — Alternativenvergleich

**Auslöser:** Eine materielle Boundary-, Vertrags- oder schwer reversible Entscheidung hat mehrere plausible Wege; oder die bisherige Richtung beruht auf einer ungeprüften tragenden Annahme.

**Inputs/Evidenz:** Entscheidungsfrage, bestätigte Anforderungen/Nicht-Ziele, heutige Verträge und Eigentümer, Qualitätsattribute, Risiko/Reversibilität und Repositoryevidenz. Unbestätigte Produktentscheidungen nicht als Annahmen einbauen.

**Methode:**

1. Formuliere das Problem lösungsneutral. Vergleiche mindestens zwei mechanistisch unterschiedliche Wege, bei Tragfähigkeit einschließlich Status quo. Ein anderer Klassenname oder Parameter ist keine echte Alternative; dieselbe sinnvolle Schnittstelle schließt unterschiedliche Daten-/Eigentumsmodelle aber nicht aus.
2. Wenn die erste Idee bereits verankert ist, nutze optional ein **Pre-Mortem**: unterstelle ihr Scheitern, benenne eine konkrete strukturelle Ursache und die tragende Annahme; entwirf einen vollständigen anderen Weg ohne diese Annahme. Das ist eine Denkstütze, keine isolierte unabhängige Evaluation. Kein eigener Dispatch und keine neue Agentensteuerung.
3. Vergleiche Aufruferaufwand, Vertragseinfachheit, heutige Anwendungsfälle, Information Hiding, Abhängigkeiten, Implementierungs-/Testbarkeit und relevante Performance-/Security-/Datenrisiken. Prioritäten stammen aus der konkreten Anforderung, nicht einer universellen Rangfolge. Beschreibe Migration, Rückfallgrenze und Kosten qualitativ, wenn Messungen fehlen.
4. Prüfe gemeinsame Schwächen auf eine einfachere dritte Richtung, ohne zwingende Synthese. Wähle die einfachste passende Lösung mit sichtbaren Trade-offs und verbleibenden Annahmen.

**Ausnahmen/Stopgrenzen:** Keine Pflichtübung für triviale reversible Entscheidungen, etablierte kontextpassende Konventionen oder einen Bugfix ohne Vertrags-/Boundary-Wirkung. Keine Zeit-/Investitionsquote oder spekulative Generalisierung. Fehlt eine materielle Produktentscheidung oder bestätigt keine Evidenz die zentrale Annahme, stoppe die Festlegung und benenne den engen Klärungs-/Validierungsschritt. Materielle Planänderungen gehören zu core-plan; Umsetzung bleibt eigener autorisierter Task.

**Ergebnis/Abschluss:** Optionen, konkrete Auswahlkriterien, Empfehlung, Nachteile/Risiken, Vertrags-/Migrationsfolgen und beobachtbare Validierungsschritte. ADR nur für langlebige/schwer reversible Entscheidungen am autorisierten Pfad, nicht für jeden Vergleich. Ohne unabhängige Verhaltensevaluation keine Behauptung von Isolation, Kosteneinsparung oder überlegenem Agentenverhalten.

Adaptiert aus Clairvoyance (MIT, Cody Bromley 2026), einschließlich Pre-Mortem-Fallback: [Provenienz](../PROVENANCE.md), [Lizenz](../THIRD_PARTY_NOTICES.md).

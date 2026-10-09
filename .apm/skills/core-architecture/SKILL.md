---
name: core-architecture
description: Fachmethode für proportionale Architekturentscheidungen zu Modulgrenzen, Verträgen, Information Hiding und schwer reversiblen technischen Richtungen. Verwenden, wenn eine Entscheidung mehrere Komponenten, Eigentümer oder Qualitätsattribute betrifft; nicht für Produktplanung, lokale Refactorings, Featureimplementierung oder Bugfixes.
---

# Core Architecture

`core-architecture` ist eine Fachmethode für den `architecture-reviewer`, kein öffentlicher Workflow. Sie besitzt weder Produktplanung noch Dispatch, Scheduling oder Integration. Der Agent erweitert den bestätigten Scope nicht und startet keine Subagenten.

## Situative Designmethoden

Nutze [S00 – SWE-Basis und Auswahl](references/design-baseline.md) für tatsächlich betroffene Struktur- und Vertragsfragen im bestätigten Prüfumfang. Detailmethoden werden nur bei konkretem Signal geladen, nicht als Vollscan. Die Referenzen aktivieren keinen Architekturworkflow und erlauben keine ungeplanten Refactorings.

Prüfe Wissenseigentum, versteckte Kopplung oder redundante Schichten mit [M01–M04](references/boundaries-and-abstractions.md); unnötige Aufruferentscheidungen oder Fehlerflächen mit [M05–M06](references/interface-and-errors.md). Bei materiellen Richtungsentscheidungen nutze [M10](references/alternatives.md).

Wenn Tools benötigt werden, prüfe relevante aktuell verfügbare MCP-Fähigkeiten gemäß [Toolrouting](../core-shared/references/tool-routing.md); Verfügbarkeit erweitert weder Scope noch Autorisierung.

## Aktivierung und Grenzen

Aktiviere die Methode nur, wenn eine technische Entscheidung mindestens eines dieser Merkmale hat:

- sie verändert eine System-, Modul-, Service-, Daten- oder Eigentums-**Boundary**,
- sie legt einen öffentlichen Vertrag, eine Abhängigkeitsrichtung oder eine langfristige Konvention fest,
- sie ist teuer rückgängig zu machen oder beeinflusst mehrere Komponenten,
- mehrere Qualitätsattribute oder Stakeholderinteressen stehen in einem materiellen Trade-off.

Eine große Datei, ein vertrautes Pattern oder eine theoretisch „sauberere“ Struktur ist allein keine Architekturfrage. Lokale, verhaltensbewahrende Strukturarbeit gehört zu `core-refactor`; Produktziel, Featureumfang, Priorisierung und Taskgraph gehören zu `core-plan`; unklarer oder fehlerhafter Istzustand gehört zu `core-debug`.

## Eingaben und Verträge

Erwarte die konkrete Entscheidungsfrage, Scope und Nicht-Ziele, aktuelle Repositoryevidenz, relevante Qualitätsattribute, bestehende Verträge sowie Akzeptanz- oder Validierungskriterien. Lade bedarfsgerecht:

- den [Workflowvertrag](../core-shared/references/workflow-contract.md) für Autorität, Scope und materielle Planänderungen,
- den [Artefaktvertrag](../core-shared/references/artifact-contract.md), wenn eine langlebige Entscheidung oder ein Handoff entsteht,
- das [Toolrouting](../core-shared/references/tool-routing.md) für Gortex und sichtbare Fallbacks,
- den [Verifikationsvertrag](../core-shared/references/verification.md) für beobachtbare Entscheidungsevidenz.

Bestehende Projektinvarianten und dokumentierte Entscheidungen haben Vorrang vor Paketdefaults. Fehlt eine materielle Produktentscheidung, route sie an `core-plan`, statt sie als Architekturannahme zu erfinden.

## Proportionale Methode

Wähle die leichteste Methode, die Risiko und Reversibilität abdeckt:

| Entscheidung | Ausreichende Methode | Erwarteter Nachweis |
|---|---|---|
| lokal, reversibel, durch bestehende Konvention entschieden | kurze Boundary-Diagnose | betroffene Wissensgrenze, geltende Konvention, Verifikation |
| materiell oder mit mehreren plausiblen Richtungen | mindestens zwei mechanistisch unterschiedliche Optionen | Trade-offs, Risiken, Kosten und begründete Empfehlung |
| qualitätsattribut- oder risikogetrieben | szenariobasierte Analyse | Auslöser, Betriebszustand, erwartete Reaktion und messbare Grenze |
| langlebig, organisationsübergreifend oder schwer reversibel | ADR | Kontext, Optionen, Entscheidung, Folgen und Validierungsplan |

Erzeuge keine ADR-Pflicht für triviale oder vollständig reversible Entscheidungen. Dokumentiere eine langlebige Entscheidung genau einmal am vom Auftrag bestimmten Pfad; ein Bericht oder ADR ist kein zweiter Plan und enthält keinen Runstatus.

## Boundary- und Information-Hiding-Prüfung

Nutze die kanonischen [M01–M04](references/boundaries-and-abstractions.md) anhand des belegten Signals: unabhängig veränderliches Wissen und dessen Owner, interne versus öffentliche Verträge, sichtbare und versteckte Kopplung sowie Interfacekosten und unterschiedliche Abstraktionsebenen. Wähle nur die benötigte Methode; Dateigröße und Delegation allein sind kein Defekt.

Bewahre öffentliche Verträge oder beschreibe ihre explizite Evolution. Gewünschte Verhaltensänderungen sind keine verdeckten Architekturkorrekturen; materielle Folgen werden weiterhin an core-plan zurückgegeben.

## Workflow: Repositoryanalyse und Entscheidung

1. Lokalisiere mit Gortex die betroffenen Symbole, Verträge, Abhängigkeiten, Aufrufer und gemeinsame Änderungssignale.
2. Trenne belegte Fakten, Annahmen und offene Evidenzlücken. Ein Fallback folgt dem `core-shared`-Toolrouting und wird sichtbar benannt.
3. Formuliere die kleinste tatsächliche Entscheidungsfrage und die relevanten Qualitätsattribute.
4. Wende die proportionale Methode an. Bei materiellen Entscheidungen vergleiche mindestens zwei echte Alternativen einschließlich „Status quo“, wenn dieser tragfähig ist.
5. Empfiehl eine Richtung mit Trade-offs, Risiken, Migrations- beziehungsweise Rückfallgrenze und überprüfbaren Validierungsschritten.
6. Prüfe, ob die Empfehlung Ziel, Scope, Architektur oder Akzeptanz des bestätigten `plan/v1` materiell ändert. Falls ja, gib sie an `core-plan` zurück; implementiere sie nicht stillschweigend.

Brainstorm oder Plan können diese Fachmethode inline bei konkretem Boundary-, langlebigem Vertrags- oder schwer reversiblen Entscheidungssignal einsetzen; sie erzeugt keinen eigenen Dispatch. Bei Etappenplanung bleiben bestätigte Ziel-/Definitionsversionen unverändert; nötige Ziel-/Scopeänderungen gehen zur Bestätigung an `core-milestone` und in einen Plan. Eine ausdrücklich autorisierte Implementierung bleibt ein separater Task des zuständigen Domainagenten. `core-architecture` selbst plant kein Produkt, zerlegt keine Features und steuert keine Ausführung.

## Routing entdeckter Arbeit

- Neues Nutzerverhalten, Featureumfang oder Priorisierung → `core-plan` und zuständiger Domainagent.
- Fehlerhaftes beobachtbares Verhalten oder unklare Ursache → `core-debug` beziehungsweise `debug-investigator`.
- Rein verhaltensbewahrende lokale Strukturänderung → `core-refactor` beziehungsweise `refactor-engineer`.
- Security-, Datenbank-, Infrastruktur-, Frontend-, Backend- oder Mobile-Implementierung → zuständiger Fachagent innerhalb eines bestätigten Tasks.

Halte diese Punkte als offene Folgearbeit fest. Vermische sie nicht mit der Architekturentscheidung und erweitere dafür weder Scope noch Autorisierung.

## Ergebnis

Liefere Status, Entscheidungsfrage, Evidenz und Annahmen, verwendete Methodentiefe, Optionen, Empfehlung, Trade-offs, Risiken, Validierungsschritte, betroffene Verträge und geroutete Folgearbeit.

- `completed`: Entscheidung ist proportional begründet und mit überprüfbaren Schritten belegt.
- `partial`: Eine nutzbare Analyse liegt vor, aber benannte Evidenz oder Entscheidung fehlt.
- `blocked`: Eine materielle Produktentscheidung, erforderliche Repositoryevidenz oder Autorisierung fehlt.
- `failed`: Die vereinbarte Analyse konnte nicht sicher abgeschlossen werden; nenne Ursache und nächsten engen Schritt.

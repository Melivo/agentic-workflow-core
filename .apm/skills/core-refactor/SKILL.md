---
name: core-refactor
description: Fachmethode für verhaltensbewahrende Strukturverbesserungen mit Safety Net, Characterization Tests und kleinen überprüfbaren Transformationen. Verwenden für gezielte technische Schulden oder Hotspots; nicht für Features, Bugfixes, Architekturentscheidungen oder Performanceoptimierung als Ziel.
---

# Core Refactor

`core-refactor` ist eine Fachmethode für den `refactor-engineer`, kein öffentlicher Workflow. Ziel ist bessere Lesbarkeit und Änderbarkeit bei unverändertem beobachtbarem Verhalten. Der Agent erweitert den bestätigten Scope nicht und startet keine Subagenten.

## Situative Designmethoden

Lade bei Coding-Arbeit [S00 – SWE-Basis und Auswahl](../core-architecture/references/design-baseline.md) als gemeinsame Grundlage und prüfe zum Abschluss die tatsächlich betroffenen Module; benenne nicht anwendbare Punkte. Detailmethoden werden nur bei konkretem Signal geladen, nicht als Vollscan. Die Referenzen aktivieren keinen Architekturworkflow und erlauben keine ungeplanten Refactorings.

Wähle bei unklarer Komplexität, gekoppelten Änderungen oder redundanten Schichten [M01–M04](../core-architecture/references/boundaries-and-abstractions.md); bei Interface-/Fehlerlast [M05–M06](../core-architecture/references/interface-and-errors.md); bei Sonderfällen, Wiederholung oder Verständlichkeitsproblemen [M07–M09](../core-architecture/references/evolution-and-clarity.md). Safety Net, getrennte Charakterisierung und unverändertes Verhalten haben Vorrang.

Wenn Tools benötigt werden, prüfe relevante aktuell verfügbare MCP-Fähigkeiten gemäß [Toolrouting](../core-shared/references/tool-routing.md); Verfügbarkeit erweitert weder Scope noch Autorisierung.

## Unverhandelbare Trennung

Ordne jede beabsichtigte Änderung vor der Mutation genau einer Arbeitsart zu:

| Arbeitsart | Erlaubtes Ziel | Eigentümer und Trennung |
|---|---|---|
| Characterization Tests | aktuelles, auch überraschendes Verhalten beobachtbar festhalten | eigener Vorbereitungsschritt; währenddessen bleibt Produktionscode eingefroren |
| Refactoring | interne Struktur bei identischem Verbrauchervertrag verbessern | eigener Task; bestehende Tests und Charakterisierung bleiben während der Produktionsänderung unverändert |
| Feature | neues oder erweitertes Verhalten schaffen | an `core-plan` und den zuständigen Domainagenten routen; nicht als Refactoring tarnen |
| Bugfix | Istverhalten in erwartetes Verhalten ändern | an `core-debug` beziehungsweise `debug-investigator` routen; Regressionstest und Fix nicht einmischen |
| Architekturentscheidung | Boundary, Vertrag, Eigentümerschaft oder Konvention materiell ändern | an `core-architecture` beziehungsweise `architecture-reviewer` routen |

Characterization Tests sind ein Safety Net, kein Beweis dafür, dass das aktuelle Verhalten fachlich richtig ist. Sie pinnen den beobachteten Istzustand vor einer Strukturänderung. Auch ohne Commitautorisierung bleiben Testvorbereitung, Produktionsrefactoring, Feature und Bugfix als getrennte Tasks und Ergebnisabschnitte nachvollziehbar; SCM-Schritte gehören ausschließlich zu `core-scm` nach ausdrücklicher Autorisierung.

## Verhaltenserhaltung

Behandle als beobachtbares Verhalten mindestens:

- öffentliche APIs, Rückgaben, Ausnahmen und Fehlerformen,
- persistierte Daten, Serialisierung, Protokolle und externe Seiteneffekte,
- Reihenfolge, Idempotenz, Nebenwirkungen und relevante Interaktionen,
- dokumentierte Verträge sowie faktisch genutzte, repositorybelegte Verbrauchererwartungen.

Ein schnellerer Ablauf ist kein Refactoringserfolg, wenn Timing oder Ressourcenwirkung Teil eines Verbrauchervertrags ist. Performanceoptimierung, API-Bereinigung und „offensichtliche“ Fehlerkorrekturen ändern Verhalten und bleiben außerhalb dieses Skills.

## Eingaben und Verträge

Erwarte Zielpfade, Motivation, Schreibscope, vorhandene Tests und Checks, Projektkonventionen sowie bekannte Verträge. Lade bedarfsgerecht:

- den [Workflowvertrag](../core-shared/references/workflow-contract.md) für Scope, Planintegrität und Routing materieller Änderungen,
- den [Artefaktvertrag](../core-shared/references/artifact-contract.md) für `task-result/v1` und Handoffs,
- das [Toolrouting](../core-shared/references/tool-routing.md) für Gortex-Impact, semantische Mutation und sichtbare Fallbacks,
- den [Verifikationsvertrag](../core-shared/references/verification.md) für aktuelle Checkevidenz und blockierte Prüfungen.

Die Zielform folgt Sprachidiom, Codeebene und bestehender Repositorykonvention. Eine neue Konvention oder Boundary benötigt zuerst eine Architekturentscheidung.

## Workflow

### 1. Safety Net diagnostizieren

1. Lokalisiere Ziel, Aufrufer, Verträge und relevante Tests mit Gortex.
2. Prüfe Abdeckung des betroffenen Verhaltens, Aussagekraft der Assertions, Determinismus und – wenn vorhanden – Mutation Strength.
3. Klassifiziere das Safety Net als ausreichend, schwach oder fehlend. Ein grüner Test ohne relevante Beobachtung ist kein ausreichendes Netz.
4. Liegt kein belastbares Netz vor, stoppe Produktionsrefactoring und führe ausschließlich den getrennten Characterization-Test-Schritt aus.

### 2. Aktuelles Verhalten charakterisieren

1. Finde eine Testnaht an einer stabilen beobachtbaren Boundary.
2. Erfasse repräsentative Eingaben, Ausgaben, Fehler und Seiteneffekte des **aktuellen** Verhaltens. Golden Master oder Snapshot ist nur geeignet, wenn die Ausgabe deterministisch, prüfbar und frei von Secrets ist.
3. Ändere in diesem Schritt keinen Produktionscode außer einer separat autorisierten minimalen mechanischen Testnaht; eine solche Voraussetzung bleibt als eigener Schritt sichtbar.
4. Führe die Characterization Tests wiederholt aus und belege Stabilität. Fachlich verdächtiges Verhalten wird als mögliches Bugfinding geroutet, nicht im Erwartungswert „korrigiert“.
5. Friere die bestätigte Charakterisierung für den folgenden Refactoring-Schritt ein.

### 3. Ziel nach Risiko und Nutzen wählen

Priorisiere Hotspots anhand von Komplexität, Churn, Kopplung und konkretem Änderungsdruck statt nach Smell-Ästhetik. Refactore keinen kalten oder bald zu löschenden Code ohne belegten Nutzen. Definiere vorab die lesbare Zielform und mindestens eine passende Strukturmetrik; Metriken bleiben Proxies.

### 4. Kleine Transformationen ausführen

Zerlege die Arbeit in benannte, einzeln rücknehmbare Transformationen, beispielsweise semantisches Umbenennen, Funktion extrahieren, Bedingung vereinfachen oder Verantwortung verschieben. Für jeden Schritt:

1. Prüfe mit Gortex Impact, Verträge und Scope.
2. Verwende bevorzugt semantische Refactorings oder deterministische Transformationen statt blinder Textersetzung.
3. Führe genau eine kleine Strukturänderung aus; ändere keine Tests gleichzeitig.
4. Führe Gortex Change Detection aus und gleiche tatsächliche Pfade mit dem bestätigten Scope ab.
5. Führe die unveränderten relevanten Tests und gepinnten Checks auf aktuellem Stand aus.
6. Bei Fehlschlag: nicht weiterstapeln. Verwirf die unbewiesene Transformation sicher oder dokumentiere die blockierende Voraussetzung nach dem Mikado-Prinzip.

Fehlt ein sicherer schreibender Gortex-View oder eine zulässige semantische Mutation, blockiere den Schritt sichtbar; ein read-only Fallback autorisiert keine freie Schreibalternative.

## Routing statt Vermischung

- Entdeckter Defekt: Ort, reproduzierbare Evidenz und Auswirkung notieren; an `debug-investigator` routen. Kein Fix im Refactoring.
- Gewünschtes neues Verhalten: als Feature an `core-plan` und den zuständigen Domainagenten routen.
- Erforderliche neue Boundary, Abhängigkeitsregel oder Konvention: an `architecture-reviewer` routen.
- Fehlendes oder flakiges Safety Net: als getrennte Voraussetzung behandeln; Produktionscode bleibt bis zu belastbarer Evidenz unverändert.

Ein Feature darf durch ein vorausgehendes Refactoring vorbereitet werden, aber Vorbereitung und Verhaltenserweiterung bleiben getrennte Tasks, Mutationen, Checks und Ergebnisse.

## Abschluss und Evidenz

Vergleiche vor und nach dem Refactoring mindestens:

- alle relevanten Verhaltenstests und Vertragschecks,
- gewählte Strukturmetriken wie Komplexität, Größe oder Kopplung,
- einen begründeten Lesbarkeitsbefund anhand der tatsächlichen Zielform.

Eine bessere Metrik bei schlechterer Lesbarkeit ist ein Fehlschlag. Liefere Status, geänderte Pfade, Safety-Net-Befund, Characterization-Evidenz, benannte Transformationen, Checkresultate, Vorher-/Nachher-Delta, Lesbarkeitsurteil und geroutete Folgearbeit.

- `completed`: Verhalten ist aktuell als unverändert belegt und Struktur sowie Lesbarkeit sind verbessert.
- `partial`: Safety Net oder Voraussetzungen sind erstellt, die Strukturänderung ist aber bewusst zurückgestellt.
- `blocked`: Verifikationspfad, sichere Mutation, Scope oder erforderliche Architekturentscheidung fehlt.
- `failed`: Eine Transformation konnte nicht verhaltensneutral abgeschlossen werden; nenne Ursache und sicheren nächsten Schritt.

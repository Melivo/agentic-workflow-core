---
name: core-frontend
description: Implementiert Web-Oberflächen, Komponenten, Interaktionen und frontendseitige Integration anhand vorhandener Design- und Projektverträge. Verwenden für React-, Next.js- oder Angular-Projekte; nicht für ein Redesign, einen Frameworkwechsel oder neue Clientabhängigkeiten ohne bestätigte Entscheidung.
---

# Core Frontend

`core-frontend` ist die Fachmethode des `frontend-engineer`, kein öffentlicher Workflow. Der Skill implementiert nur den bestätigten Taskscope, startet keine Subagenten und übernimmt weder Produktplanung noch unabhängiges Review.

## Situative Designmethoden

Lade bei Coding-Arbeit [S00 – SWE-Basis und Auswahl](../core-architecture/references/design-baseline.md) als gemeinsame Grundlage und prüfe zum Abschluss die tatsächlich betroffenen Module; benenne nicht anwendbare Punkte. Detailmethoden werden nur bei konkretem Signal geladen, nicht als Vollscan. Die Referenzen aktivieren keinen Architekturworkflow und erlauben keine ungeplanten Refactorings.

Bei unklaren Komponenten-/Zustandsgrenzen oder redundanten Wrappern nutze [M01–M04](../core-architecture/references/boundaries-and-abstractions.md); bei schwer nutzbaren Props, wiederholtem Setup oder Fehlerpfaden [M05–M06](../core-architecture/references/interface-and-errors.md). Bei angeflickten Zuständen oder irreführenden Namen nutze [M07–M09](../core-architecture/references/evolution-and-clarity.md).

Wenn Tools benötigt werden, prüfe relevante aktuell verfügbare MCP-Fähigkeiten gemäß [Toolrouting](../core-shared/references/tool-routing.md); Verfügbarkeit erweitert weder Scope noch Autorisierung.

## Eingaben und Autorität

Erwarte Task, `context_paths`, Schreibscope, Akzeptanzkriterien, gepinnte Checks sowie vorhandene UI-, Design- und API-Verträge. Ermittle vor Änderungen Framework und Version, Renderingmodell, Komponentenbibliothek, Stylingansatz, Browserziele, Teststil und bestehende Seiten- oder Featuregrenzen aus dem Repository.

Ein vorhandenes `DESIGN.md`, Design Tokens, Komponentenbibliotheken und belegte Projektkonventionen sind projektspezifische Vorgaben und haben Vorrang vor Paketdefaults. Bewahre etablierte Typografie, Farben, Spacing, Komponenten-APIs, Breakpoints, Interaktionsmuster und Inhaltskonventionen. Fehlt eine materielle visuelle Entscheidung, route sie an die zuständige Design- oder Planungsmethode, statt ein neues Designsystem zu erfinden.

Für mutierende Aufgaben gelten der [Workflowvertrag](../core-shared/references/workflow-contract.md) für Autorisierung und Scope sowie der [Verifikationsvertrag](../core-shared/references/verification.md) für Impact, Post-edit-Prüfung und aktuelle Evidenz. Lade das [Toolrouting](../core-shared/references/tool-routing.md) nur, wenn Code-Intelligence oder aktuelle externe Dokumentation benötigt wird.

## Bedingte Frameworkreferenzen

Lade genau die Referenz, deren Stack im aktuellen Projekt belegt ist:

| Auslöser | Referenz |
|---|---|
| React; bei belegtem Next.js zusätzlich dessen Rendering- und Routingregeln | [React und Next.js](references/react-nextjs.md) |
| Angular | [Angular](references/angular.md) |
| anderer oder nicht eindeutig belegter Web-Stack | keine dieser Referenzen; folge Repositorycode und offiziellen Projektverträgen |

Lade keine Frameworkreferenz vorsorglich und übertrage keine Konvention zwischen Stacks. Nutze Context7 nur bei einer konkreten, aktuellen Bibliotheks-, Framework-, SDK- oder API-Frage; Repositorybefunde und allgemeine UI-Grundsätze benötigen es nicht.

## UI-Invarianten

### Accessibility

- Verwende semantische native Elemente und zugängliche Namen; ARIA ergänzt fehlende Semantik, ersetzt sie nicht.
- Erhalte vollständige Tastaturbedienung, sichtbaren Fokus, logische Fokusreihenfolge und sinnvolle Fokusführung bei Navigation, Dialogen und dynamischen Zuständen.
- Kommuniziere Status, Fehler und Validierung nicht ausschließlich über Farbe. Berücksichtige Kontrast, Zoom, Textvergrößerung, Screenreader und reduzierte Bewegung; ein strengerer Projektstandard als WCAG 2.2 AA hat Vorrang.
- Prüfe Loading-, Empty-, Error-, Disabled- und Success-Zustände sowie relevante Eingabefehler beobachtbar.

### Responsive-Verhalten

- Implementiere mobile-first und inhaltsgetrieben; eine Desktopansicht allein erfüllt den Task nicht.
- Verwende vorhandene Container, Breakpoints und Layoutprimitiven. Führe keine konkurrierende Breakpoint-Skala ein.
- Verhindere unbeabsichtigtes horizontales Scrollen und prüfe Reflow, lange lokalisierte Inhalte, Zoom, Touchziele, Navigation und informationsreiche Ansichten auf den relevanten Viewports.
- Nutze progressive Verbesserung. Kerninhalt und Kernaktion bleiben ohne Hover und auf grober Zeigereingabe erreichbar.

## Workflow

1. **Projektkontext feststellen:** Lokalisiere mit Gortex Einstiegspunkte, Komponenten, Design Tokens, `DESIGN.md`, Datenverträge, Tests und Aufrufer. Prüfe, dass der View dem aktuellen Checkout entspricht.
2. **Vorrang und Scope bestätigen:** Ordne jede Änderung einem Akzeptanzkriterium zu. Stoppe bei unbestätigtem Redesign, Frameworkwechsel, neuer Abhängigkeit oder materieller API- beziehungsweise Architekturentscheidung.
3. **Referenz bedingt laden:** Lade ausschließlich die durch den belegten Stack ausgelöste Frameworkreferenz.
4. **Impact prüfen:** Ermittle vor Mutation Abhängigkeiten, öffentliche Props oder Inputs, Routing-, Rendering- und Stylingfolgen sowie betroffene Tests.
5. **Kleinste konsistente Änderung umsetzen:** Verwende bestehende Komponenten und Tokens, trenne Server-/Client- und Zustandsgrenzen gemäß Projektkonvention und bereinige Listener, Requests, Timer und Subscriptions im passenden Lifecycle.
6. **Post-edit prüfen:** Führe Gortex Change Detection aus, gleiche tatsächliche Pfade mit dem Scope ab und prüfe geänderte Signaturen und Verträge.
7. **Verifizieren:** Führe nur autorisierte, gepinnte Checks aus. Belege neben Funktion auch Accessibility und Responsive-Verhalten an den betroffenen Zuständen; ein Exitcode allein genügt nicht. Ein Build benötigt ausdrückliche Autorisierung.

## Ergebnis

Liefere Status, Zusammenfassung, geänderte Pfade, angewandte Design- und Projektkonventionen, geladene Frameworkreferenz, UI-/Accessibility-/Responsive-Evidenz, Checkresultate und Einschränkungen.

- `completed`: Scope, Kriterien und Pflichtchecks sind aktuell belegt.
- `partial`: Eine nutzbare Änderung liegt vor, aber benannte Evidenz oder ein nicht blockierender Teil fehlt.
- `blocked`: Eine erforderliche Designentscheidung, Autorisierung, Eingabe oder sichere Prüfmethode fehlt.
- `failed`: Umsetzung oder Prüfung schlug fehl; nenne beobachtete Teilwirkung und sicheren nächsten Schritt.

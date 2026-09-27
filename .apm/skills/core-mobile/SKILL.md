---
name: core-mobile
description: Implementiert Flutter-, React-Native- und native Swift-iOS-Aufgaben innerhalb belegter Plattform-, Design- und Lifecycle-Verträge. Verwenden für mobile UI, State, Navigation, Plattformintegration und Lokalisierung; nicht für einen Frameworkwechsel, neue native Plattformen oder generierte ARB-Lokalisierungsausgaben.
---

# Core Mobile

`core-mobile` ist die Fachmethode des `mobile-engineer`, kein öffentlicher Workflow. Der Skill arbeitet ausschließlich im bestätigten Taskscope, startet keine Subagenten und lädt nur die zum belegten Zielstack passende Plattformreferenz.

## Eingaben und Autorität

Erwarte Task, `context_paths`, Schreibscope, Zielplattformen, Akzeptanzkriterien, gepinnte Checks sowie vorhandene Design-, API-, Persistenz- und Lokalisierungsverträge. Ermittle vor Änderungen Framework und Version, unterstützte Betriebssysteme, Projektarchitektur, State-, Navigation-, Networking-, Storage-, Test- und Generierungsstrategie.

Bestehende Projektkonventionen, ein vorhandenes `DESIGN.md`, Design Tokens, Komponentenbibliotheken und Plattformentscheidungen haben Vorrang vor Paketdefaults. Bewahre vorhandene Architektur- und Zustandsgrenzen. Ein Frameworkwechsel, eine neue Abhängigkeit, eine zusätzliche Source of Truth oder eine neue native Plattform benötigt eine bestätigte Entscheidung.

Für mutierende Aufgaben gelten der [Workflowvertrag](../core-shared/references/workflow-contract.md) für Scope und Autorisierung sowie der [Verifikationsvertrag](../core-shared/references/verification.md) für Impact, Post-edit-Prüfung und aktuelle Evidenz. Lade das [Toolrouting](../core-shared/references/tool-routing.md) nur für benötigte Code-Intelligence oder eine konkrete aktuelle Dokumentationsfrage.

## Genau eine passende Plattformreferenz laden

| Belegter Zielstack | Referenz |
|---|---|
| Flutter/Dart | [Flutter](references/flutter.md) |
| React Native | [React Native](references/react-native.md) |
| native iOS mit Swift/SwiftUI | [Swift iOS](references/swift-ios.md) |

Lade keine andere Plattformreferenz vorsorglich. Bei einem ausdrücklich bestätigten, stackübergreifenden Task darf jede tatsächlich betroffene Referenz geladen werden; dokumentiere dann die getrennten Plattformwirkungen. Für Kotlin-native oder Jetpack Compose enthält dieses Bundle keine Referenz: stoppe bei fehlender zuständiger Methode, statt Flutter- oder React-Native-Regeln zu übertragen.

## Plattformübergreifende Invarianten

### Accessibility und adaptive UI

- Verwende native Semantik und Rollen des belegten Frameworks. Erhalte Screenreader-Namen, Fokusreihenfolge, dynamische Typografie beziehungsweise Textskalierung, Kontrast, reduzierte Bewegung und ausreichend große Interaktionsziele.
- Implementiere responsive und adaptive Layouts für die bestätigten Geräteklassen, Ausrichtungen, Fenstergrößen, Safe Areas, Eingabemethoden und lange lokalisierte Inhalte. Starre Geräteabmessungen sind kein Layoutvertrag.
- Befolge Material Design 3 auf Android und iOS HIG auf iOS, soweit das bestehende Designsystem keine strengere belegte Projektentscheidung trifft.

### Lifecycle, Nebenläufigkeit und Ressourcen

- Binde Start, Pause, Resume, Hintergrund, Navigation und Zerstörung an den Lifecycle des belegten Stacks.
- Dispose Controller, Listener, Streams, Observer, Timer und native Handles deterministisch. Breche strukturierte Tasks und Requests ab, wenn ihr Owner endet oder ihr Ergebnis nicht mehr gültig ist.
- Verhindere UI-Updates nach Disposal, veraltete asynchrone Ergebnisse und doppelte Registrierung. Erhalte zustandsrelevante Daten nur über die vorhandene Lifecycle- und Persistenzstrategie.

### ARB als Source of Truth

Wenn das Projekt ARB-basierte Lokalisierung verwendet, sind die ARB-Quelldateien die einzige zu editierende Source of Truth für UI-Strings:

- Ändere ausschließlich die zuständigen `.arb`-Quelldateien, einschließlich erforderlicher Placeholder- und Metadatenfelder.
- Ändere niemals generierten Lokalisierungscode oder generierte Ressourcen direkt.
- Bewahre Schlüssel, Placeholdertypen, Plural-/Select-Semantik, Escaping und Locale-Abdeckung gemäß Projektkonvention.
- Führe Generierung, Build oder Compile nur bei ausdrücklicher Autorisierung aus. Nutze ansonsten autorisierte statische ARB-Prüfungen und dokumentiere die blockierte Generierung sichtbar.

Verwendet das Projekt kein ARB, führe ARB nicht als Nebenwirkung ein und folge der belegten Lokalisierungsquelle.

## Workflow

1. **Stack und Verträge feststellen:** Lokalisiere mit Gortex App-Einstieg, Featuregrenzen, Lifecycle-Owner, State, Navigation, Design Tokens, ARB-Quellen, generierte Ausgaben und Tests. Prüfe den aktuellen Checkout oder Worktree.
2. **Scope und Plattform festlegen:** Ordne jede Änderung einem Akzeptanzkriterium und Zielstack zu. Stoppe bei unbestätigtem Framework-, Architektur-, Designsystem- oder Lokalisierungswechsel.
3. **Referenz bedingt laden:** Lade ausschließlich die belegte Plattformreferenz und nur die dort relevanten Abschnitte.
4. **Impact prüfen:** Ermittle vor Mutation Abhängigkeiten, öffentliche Verträge, Plattformkanäle, Lifecycle-, Accessibility-, Layout- und Lokalisierungsfolgen sowie betroffene Tests.
5. **Kleinste konsistente Änderung umsetzen:** Nutze vorhandene Komponenten, State-, Transport-, Cache- und sichere Storage-Abstraktionen. Halte Secrets aus unsicherem Klartextspeicher heraus und bewahre Offline- und Fehlerverhalten.
6. **Post-edit prüfen:** Führe Gortex Change Detection aus, gleiche Pfade mit dem Scope ab und verifiziere, dass bei ARB keine generierte Datei geändert wurde.
7. **Verifizieren:** Führe nur autorisierte, gepinnte Checks aus. Belege relevante Lifecycle-, Accessibility-, adaptive UI- und Lokalisierungszustände. Builds, Compiles, Installationen und Paketierung bleiben ohne ausdrückliche Autorisierung gesperrt.

## Ergebnis

Liefere Status, Zusammenfassung, geänderte Pfade, Zielstack und geladene Referenz, angewandte Projekt-/Designkonventionen, Lifecycle-, Accessibility-, Responsive-/Adaptive- und ARB-Evidenz, Checkresultate und Einschränkungen.

- `completed`: Scope, Kriterien und Pflichtchecks sind aktuell belegt.
- `partial`: Eine nutzbare Änderung liegt vor, aber benannte Evidenz oder ein nicht blockierender Teil fehlt.
- `blocked`: Zielstack, Autorisierung, Projektentscheidung, Eingabe oder sichere Prüfmethode fehlt.
- `failed`: Umsetzung oder Prüfung schlug fehl; nenne beobachtete Teilwirkung und sicheren nächsten Schritt.

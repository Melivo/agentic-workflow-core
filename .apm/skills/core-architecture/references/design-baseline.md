# SWE-Basis und situative Auswahl

Diese Referenz gilt für die tatsächlich betroffenen Bereiche einer bestätigten Coding-Aufgabe. Ihr Laden aktiviert weder einen Architekturworkflow noch zusätzliche Schreibrechte. Die Basis stammt aus den ausdrücklich bereitgestellten Benutzergrundsätzen; Vertiefungen sind intern konsolidiert, ohne externe Skill-Abhängigkeit.

## S00 — Proportionale Grund- und Abschlussprüfung

**Auslöser:** Code erstellen, ändern oder verhaltensbewahrend refaktorieren; bei Review nur den freigegebenen Prüfbereich beurteilen.

**Inputs/Evidenz:** Ziel, Schreib- beziehungsweise Prüfscope, aktueller Diff einschließlich neuer Dateien, betroffene Module und Aufrufer, öffentliche Verträge, Projektkonventionen und relevante Tests. Nicht betroffene Bereiche werden nicht inventarisiert.

**Methode:**

- Gib jedem Modul einen klaren Zweck und einen möglichst kleinen öffentlichen Vertrag. Halte kohäsives Verhalten zusammen; trenne unabhängige Änderungsgründe. Sammle keine fachfremden Funktionen in allgemeinen Utils.
- Begründe jede neue Abstraktion mit einer konkreten Wissensgrenze oder einem aktuellen Nutzen; keine Schicht allein wegen eines Patterns.
- Halte Domänenlogik soweit sinnvoll unabhängig von UI, Persistenz und Netzwerk. Verberge interne Repräsentation, Schema- und Drittanbieterwissen, soweit es nicht bewusst öffentlicher Vertrag ist.
- Bevorzuge stabile APIs, begründete Abhängigkeitsrichtungen und unabhängige Testbarkeit. Vermeide unnötige und zyklische Abhängigkeiten. Prüfe vor neuen Abhängigkeiten vorhandene Alternativen und Boundary-/Testfolgen.
- Nutze DI, Adapter, Interfaces oder Events nur mit belegtem Nutzen für Kopplung, Austauschbarkeit oder Tests. Wähle die einfachste passende Lösung unter den aktuellen Constraints.

**Abschluss:** Prüfe an den betroffenen Modulen klare Verantwortung, Kohäsion, getrennte Änderungsgründe, verborgene Interna, begründete nichtzyklische Abhängigkeiten, stabile kleine Verträge und Testbarkeit ohne unnötige Beteiligung anderer Bereiche. Benenne nicht anwendbare Punkte. Ein negatives Urteil löst eine gezielte Nachprüfung aus, nicht automatisch eine Mutation.

**Ausnahmen/Stopgrenzen:** Fachliche Kopplung, öffentliche Datenverträge, notwendige Konfiguration und legitime Adapter sind nicht an sich Defekte. Ein kleines gezieltes Refactoring ist nur innerhalb eines dafür bestätigten Tasks und seiner Verhaltenserhaltungs-/Safety-Net-Grenzen zulässig. Entdeckte externe Arbeit wird als Folgearbeit geroutet; Review bleibt read-only. Neue Produktziele, materielle Vertrags-/Boundary-Änderungen oder fehlende Autorisierung stoppen die entsprechende Mutation.

**Ergebnis:** Kurzer Befund mit Stelle, geltendem Vertrag, Ursache, konkreter Wirkung, Test-/Verifikationsevidenz und gegebenenfalls nächstem erlaubten Schritt. Keine unbelegte Einsparungs- oder Qualitätsbehauptung.

## Direkte Auswahl nach Signal

Lade nur die passende Referenz und darin die ausgelöste Methode. Kein fester Durchlauf aller Methoden; eine triviale Änderung ohne Struktursignal endet nach S00.

| Belegtes Signal | Methode und direktes Ziel | Nicht daraus ableiten |
|---|---|---|
| Kleine Änderung verlangt unerwartet viele Anpassungen; notwendiges Wissen ist unklar | [M01 Komplexitätsdiagnose](boundaries-and-abstractions.md#m01--komplexitatsdiagnose) | Dateizahl allein beweist keinen Defekt |
| Format-/Protokollwissen verteilt; zwei Module ändern sich gekoppelt | [M02 Wissenseigentum und Grenzen](boundaries-and-abstractions.md#m02--wissenseigentum-und-grenzen) | Fachliche Kopplung ist nicht automatisch Leckage |
| Benachbarte Schichten wiederholen dasselbe Modell | [M03 Abstraktionsqualität](boundaries-and-abstractions.md#m03--abstraktionsqualitat) | Adapter nicht wegen Delegation ablehnen |
| Viele Schnittstellenentscheidungen bei wenig verborgenem Nutzen | [M04 Modultiefe](boundaries-and-abstractions.md#m04--modultiefe) | Länge oder Methodenzahl nicht als Schwellenwert |
| Aufrufer wiederholen Setup, kennen fremde Details oder tragen lokale Sonderfälle | [M05 Schnittstelle und Komplexitätsverlagerung](interface-and-errors.md#m05--schnittstelle-und-komplexitatsverlagerung) | Keine spekulative Generalisierung |
| Fehlerflächen wachsen; Catch-Blöcke ignorieren wichtige Folgen | [M06 Fehleroberfläche und Wiederherstellung](interface-and-errors.md#m06--fehleroberflache-und-wiederherstellung) | Kein stilles Maskieren bei Security-/Datenrisiko |
| Diff wirkt angeflickt, wiederholt Wissen oder erhöht Sonderfalllast | [M07 Designentwicklung](evolution-and-clarity.md#m07--designentwicklung) | Keine automatische Schuldenreparatur |
| Namen erzeugen falsche Erwartungen oder sind schwer präzisierbar | [M08 Benennung und Verständlichkeit](evolution-and-clarity.md#m08--benennung-und-verstandlichkeit) | Kein Stilfinding ohne Wirkung |
| Kommentare wiederholen Code, widersprechen Vertrag oder brauchen viele Qualifikationen | [M09 Vertragsdokumentation](evolution-and-clarity.md#m09--vertragsdokumentation) | Länge ist nur ein Signal |
| Materielle Entscheidung mit mehreren plausiblen Wegen | [M10 Alternativenvergleich](alternatives.md#m10--alternativenvergleich) | Keine Alternativenpflicht für triviale etablierte Lösung |

Bei unklarem Signal beginne mit M01 an einem konkreten Änderungsbeispiel, nicht mit einem Vollscan. Mehrere Warnzeichen derselben belegten Ursache ergeben einen Befund mit mehreren Evidenzstellen, keine mehrfachen Findings. Priorisiere tatsächliche Auswirkungen und Risiko vor Kategorien; Sicherheits-/Datenrisiken haben Vorrang vor ästhetischer Strukturkritik. Beende die Vertiefung, sobald Ursache und Wirkung bestätigt, eine legitime Ausnahme belegt oder die Evidenzlücke benannt ist.

Herkunft der konsolidierten Auswahl: [Provenienz](../PROVENANCE.md); Lizenz substantieller Clairvoyance-Adaptionen: [MIT-Hinweis](../THIRD_PARTY_NOTICES.md).

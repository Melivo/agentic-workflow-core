# SWE-Basis und situative Auswahl

Diese Referenz gilt für die tatsächlich betroffenen Bereiche explizit bestätigter, strukturrelevanter Arbeit an Code, Tools, Paketen, Einrichtung sowie Installations-, Update-, Entfernungs- und Automationsabläufen. Sie gilt nicht für beliebige Informations- oder Erklärungsfragen. Ihr Laden aktiviert weder einen Architekturworkflow noch zusätzliche Schreibrechte. Die Basis stammt aus den ausdrücklich bereitgestellten Benutzergrundsätzen; Vertiefungen sind intern konsolidiert, ohne externe Skill-Abhängigkeit.

## S00 — Proportionale Grund- und Abschlussprüfung

**Auslöser:** Explizit bestätigte, strukturrelevante Arbeit: Code erstellen, ändern oder verhaltensbewahrend refaktorieren; ebenso Tools, Pakete, Einrichtung, Installations-, Update- und Entfernungsabläufe sowie Automation, soweit sie Module, Verträge, Abhängigkeiten oder Nebenwirkungen ändern. Nicht anwendbar auf beliebige Informationsfragen. Bei Review nur den freigegebenen Prüfbereich beurteilen.

**Inputs/Evidenz:** Ziel, Schreib- beziehungsweise Prüfscope, aktueller Diff einschließlich neuer Dateien, betroffene Module und Aufrufer, öffentliche Verträge, Projektkonventionen und relevante Tests. Nicht betroffene Bereiche werden nicht inventarisiert.

**Verbindlicher Sollzustand:** Die fünf Prinzipien sind Ziele beim Gestalten, nicht nur Kriterien für nachträgliche Kritik:

- **Modularität:** Jedes Modul hat einen klaren Zweck und eine möglichst kleine öffentliche Schnittstelle.
- **Hohe Kohäsion:** Zusammengehöriges Verhalten liegt zusammen; ein Modul hat einen Änderungsgrund.
- **Trennung der Verantwortlichkeiten:** Fachregeln, Darstellung, Datenzugriff, Konfiguration, Validierung und Infrastruktur liegen in Modulen mit klarer Grenze, soweit eine vertretbare Projektgrenze das trägt. Fachregeln hängen nicht unnötig von UI-Frameworks, konkreten Datenbanken oder HTTP-Clients ab.
- **Abstraktion und Information Hiding:** Verbraucher kennen nur den öffentlichen Vertrag; interne Datenstrukturen, Schemata, Drittanbieter-Details und interner Zustand bleiben verborgen.
- **Geringe unnötige Kopplung:** Abhängigkeiten zeigen auf stabile Verträge; zyklische Abhängigkeiten werden vermieden; jede neue Abhängigkeit ist begründet.

**Austauschbarkeit:** Module sind so zu gestalten, dass eine vertragskonforme alternative Implementierung bei stabilem öffentlichem Vertrag ohne Anpassung unabhängiger Verbraucher eingesetzt werden kann. Ein Vertrag benennt Eingaben, Ergebnisse, erwartete Fehler und Nebenwirkungen. Keine künstliche Austauschbarkeit jeder Klasse: Interfaces, Adapter oder eine zweite Implementierung entstehen nur dort, wo ein konkreter Wechsel- oder Testnutzen besteht.

**Benannte Werte:** Bedeutsame Werte (etwa Zeitlimits, Grenzwerte, Formatkennungen, Pfade) werden als benannte Konstante oder als eng begrenzte Konfiguration am verantwortlichen Eigentümer geführt, nicht in einer globalen Sammelstelle. Nicht jeder Wert muss ausgelagert oder konfigurierbar sein; offensichtliche Werte wie 0 oder 1 bleiben im Code.

**Methode:**

- Halte kohäsives Verhalten zusammen; trenne unabhängige Änderungsgründe. Sammle keine fachfremden Funktionen in allgemeinen Utils.
- Begründe jede neue Abstraktion mit einer konkreten Wissensgrenze oder einem aktuellen Nutzen; keine Schicht allein wegen eines Patterns.
- Halte Domänenlogik soweit sinnvoll unabhängig von UI, Persistenz und Netzwerk. Verberge interne Repräsentation, Schema- und Drittanbieterwissen, soweit es nicht bewusst öffentlicher Vertrag ist.
- Bevorzuge stabile APIs, begründete Abhängigkeitsrichtungen und unabhängige Testbarkeit. Prüfe vor neuen Abhängigkeiten vorhandene Alternativen sowie Folgen für Grenzen und Tests.
- Nutze DI, Adapter, Interfaces oder Events nur mit belegtem Nutzen für Kopplung, Austauschbarkeit oder Tests. Wähle die einfachste passende Lösung unter den aktuellen Constraints.

**Nicht verlangt:** Keine Pflicht zu Interfaces, Klassen, MVC oder Schichten, keine Dateigrößenquote und keine Umbauten nur wegen eines Prinzips. Bestehende Projektarchitektur hat Vorrang, wenn sie ausdrücklich etwas anderes vorgibt. Lade die [Hintergrundreferenz](principles-background.md) nur bei Auslegungs- oder Erklärungsbedarf; die Regeln dieser Datei genügen für die Umsetzung.

**Abschluss:** Prüfe an den betroffenen Modulen klare Verantwortung, Kohäsion, getrennte Änderungsgründe, verborgene Interna, begründete nichtzyklische Abhängigkeiten, stabile kleine Verträge mit benannten Fehlern und Nebenwirkungen sowie Testbarkeit ohne unnötige Beteiligung anderer Bereiche. Benenne nicht anwendbare Punkte. Ein negatives Urteil löst eine gezielte Nachprüfung aus, nicht automatisch eine Mutation.

**Praktische Austauschfrage:** Kann eine vertragskonforme Alternative ohne Anpassung unabhängiger Verbraucher eingesetzt werden? Bei Nein nenne die Ursache (etwa fehlender stabiler Vertrag, bewusst öffentliche interne Struktur oder Plattformbindung) und halte eine begründete Ausnahme fest, solange die Abweichung besteht.

**Ausnahmen/Stopgrenzen:** Fachliche Kopplung, öffentliche Datenverträge, notwendige Konfiguration und legitime Adapter sind nicht an sich Defekte. Ein kleines gezieltes Refactoring ist nur innerhalb eines dafür bestätigten Tasks und seiner Verhaltenserhaltungs-/Safety-Net-Grenzen zulässig; ein Beispiel aus der Nutzerfassung erteilt keine Freigabe. Entdeckte externe Arbeit wird als Folgearbeit geroutet; Review bleibt read-only. Neue Produktziele, materielle Vertrags-/Boundary-Änderungen oder fehlende Autorisierung stoppen die entsprechende Mutation.

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

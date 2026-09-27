# Integrität und Datenstandards

Lade diese Referenz für neue oder geänderte Entitäten, Aggregate, Attribute, Schlüssel, Beziehungen, Constraints, Wertebereiche oder Lebenszyklusregeln.

## Integritätsklassen

Dokumentiere und erzwinge jede relevante Klasse am engsten autoritativen Ort:

- **Entity-Integrität:** stabile Identität, Primärschlüssel, Eindeutigkeit und zulässiger Lebenszyklus.
- **Domain-Integrität:** Typ, Format, Wertebereich, Einheit, Zeitzone, `NULL`-Semantik und erlaubte Werte.
- **Referenzielle Integrität:** gültige Beziehungen, Lösch-/Updateverhalten und Umgang mit verwaisten Datensätzen.
- **Business-Rule-Integrität:** fachliche Invarianten über Attribute, Zeilen oder Aggregate hinweg, einschließlich ihres Transaktionsbedarfs.

Bevorzuge deklarative Datenbankconstraints für universell geltende Invarianten. Anwendungsvalidierung verbessert Fehlermeldungen und schützt Grenzen, ist aber bei mehreren Schreibpfaden kein alleiniger Ersatz. Wenn eine Regel nicht als Constraint ausdrückbar ist, dokumentiere Owner, Durchsetzungsmechanismus, Race-Condition-Schutz und Prüfung.

## Modellqualität

- Normalisiere relationale Modelle standardmäßig bis mindestens 3NF. Jede Denormalisierung nennt gemessenen Zugriffsvorteil, Synchronisationsregel, Fehlerbild und Rebuildpfad.
- Definiere Aggregate in nichtrelationalen Modellen nach atomarem Schreibbedarf und Zugriffspfaden; unbeschränkte Dokumente oder Hot Keys sind sichtbar zu vermeiden.
- Wähle Schlüssel, Cardinality, Indexreihenfolge und Partitionierung aus tatsächlichen Zugriffspfaden und Kapazitätsannahmen.
- Vermeide polymorphe Fremdschlüssel, kommagetrennte Mehrfachwerte, EAV als unbegründeten Default, magische Sentinel-Werte und uneindeutige Soft-Delete-Semantik.
- Defaults dürfen fehlende fachliche Information nicht vortäuschen. `NULL`, leer, unbekannt, nicht anwendbar und gelöscht werden eindeutig unterschieden.

## Datenstandardtabelle

Für jedes neue oder geänderte Feld dokumentiere mindestens:

| Spalte | Inhalt |
|---|---|
| Name | kanonischer technischer und gegebenenfalls fachlicher Name |
| Definition | eindeutige Bedeutung und Owner |
| Typ/Format | physischer Typ, Einheit, Encoding, Präzision, Zeitzone |
| Erlaubte Werte | Bereich, Enum, Muster, `NULL`- und Defaultsemantik |
| Validierungsregel | Constraint, Referenz, Business-Regel und Fehlerverhalten |
| Lebenszyklus | Erstellung, Änderung, Aufbewahrung, Löschung oder Archivierung |

Pflege zusätzlich ein Glossar für mehrdeutige Fachbegriffe und eine Kapazitätsschätzung mit Startvolumen, Wachstum, Aufbewahrung, Zeilen-/Dokumentgröße, Indexfaktor und dominantem Engpass.

## Verifikation

Prüfe Constraints mit gültigen und ungültigen Fällen, Beziehungen einschließlich Löschverhalten, Business-Regeln unter Nebenläufigkeit sowie vorhandene Daten vor dem Verschärfen einer Regel. Belege, dass Schema, Migration, Anwendung und Dokumentation dieselbe Semantik verwenden. Eine erfolgreiche DDL-Ausführung ohne Daten- und Invariantenprüfung genügt nicht.

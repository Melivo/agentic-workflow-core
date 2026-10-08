# Grenzen, Abstraktionen und Modultiefe

Wähle nur die Methode zum beobachteten Signal. Analyse ist keine Umbaufreigabe: bestehende Verträge, bestätigter Scope und Verhaltenserhaltung bleiben bindend; externe Arbeit wird geroutet. Fehlende Evidenz ergibt eine benannte Lücke, kein Defekturteil.

<a id="m01--komplexitatsdiagnose"></a>
## M01 — Komplexitätsdiagnose

**Auslöser:** Eine konkrete Änderung ist unerwartet aufwendig, verteilt sich weit oder verlangt schwer auffindbares Wissen.

**Inputs/Evidenz:** Änderungsbeispiel, betroffene Aufrufer und Verträge, Abhängigkeiten, dokumentierte/implizite Invarianten; vorhandener Churn oder Wiederholungsfälle nur bei Relevanz.

**Methode:** Unterscheide Änderungsverstärkung (welche Stellen müssen für eine Entscheidung geändert werden?), kognitive Last (was muss ein Bearbeiter wissen?) und unbekannte Abhängigkeiten (welche notwendige Anpassung ist nicht erkennbar?). Trace das konkrete Beispiel zu Abhängigkeiten oder unklarem Wissen. Gewichte aktuellen Änderungsdruck und Fehlerfolgen statt nur Größe. Prüfe, ob Komplexität vermeidbar oder hinter einer stabilen Grenze kapselbar ist; leite daraus M02–M05 nur bei passendem Signal ab.

**Ausnahmen/Stopgrenzen:** Viele Dateien können durch echte fachliche Anforderungen oder generierte Projektionen nötig sein. Keine Formel als belastbare Messung ausgeben; keine Suche über das gesamte Repository bei einem lokalen Symptom. Bei fehlerhaftem beobachtbarem Verhalten gehört die Ursachenarbeit zu core-debug.

**Ergebnis/Abschluss:** Ein nachvollziehbarer Änderungsweg mit Symptom, Ursache, Auswirkung und enger Folgeprüfung; ohne Ursache nur Hypothese/Evidenzlücke.

<a id="m02--wissenseigentum-und-grenzen"></a>
## M02 — Wissenseigentum und Grenzen

**Auslöser:** Format, Protokoll oder interne Repräsentation ist mehrfach bekannt; ein Änderungsgrund zieht unerwartet mehrere Module mit; Teile sind nur gemeinsam verständlich.

**Inputs/Evidenz:** Konkrete Designentscheidung, Wissenseigentümer, Verbraucher, API-/Datenverträge, gemeinsame Änderungsbeispiele und Tests an der Grenze.

**Methode:** Benenne das unabhängig veränderliche Wissen und seinen autoritativen Eigentümer. Unterscheide sichtbare Vertragskopplung und versteckte gemeinsame Annahmen in Implementierungen. Grenzen um Wissen statt bloß um Lesen/Verarbeiten/Schreiben ziehen. Private Felder mit spiegelnden Zugriffsmethoden verbergen keine Repräsentationsentscheidung. Prüfe: zusammenführen, wenn Teile dasselbe interne Wissen besitzen und gemeinsam einfacher werden; trennen, wenn unabhängige Änderungsgründe hinter einer kleinen stabilen Schnittstelle liegen; eine dritte gemeinsame Fähigkeit extrahieren nur mit eigenständigem Zweck und insgesamt weniger Kopplung. Methoden sollen vollständige verständliche Operationen besitzen, nicht Fragmente mit unsichtbarer Reihenfolgenpflicht.

**Ausnahmen/Stopgrenzen:** Öffentliche DTOs, gemeinsam vereinbarte Protokolle, explizite Performance-/Konfigurationsverträge und echte Domäneninvarianten dürfen mehrere Verbraucher binden. Nicht jedes Co-Change ist Leckage. Notwendige Kopplung sichtbar machen kann besser sein als sie zu entfernen. Kein erzwungenes Merge, keine abstrakten SharedUtils, keine Vertragsänderung im lokalen Refactoring.

**Ergebnis/Abschluss:** Wissenskarte mit Eigentümer, belegtem Änderungsweg und begründeter Grenze; Status quo oder kleinste Verbesserung mit Vertrags-/Testfolgen und gerouteter externer Arbeit.

<a id="m03--abstraktionsqualitat"></a>
## M03 — Abstraktionsqualität

**Auslöser:** Benachbarte Schichten oder Wrapper scheinen dasselbe Konzept und dieselben Parameter erneut darzustellen.

**Inputs/Evidenz:** Beide Schnittstellen, reale Aufrufer, verborgenes Wissen, Seiteneffekte und Garantien des Adapters/Decorators.

**Methode:** Vergleiche die Denkmodelle der Schichten: welche Entscheidung kann der Aufrufer vergessen? Prüfe beide Fehlerarten: unnötige Details offengelegt und notwendige Garantien verschwiegen (etwa Dauerhaftigkeit). Delegation allein ist kein Urteil. Vergleiche bei fehlendem Nutzen Status quo, sinnvolle Umverteilung, Zusammenführung und direkte Nutzung; für Wrapper zusätzlich Integration in bestehenden Eigentümer, am speziellen Rand oder als eigenständige Fähigkeit prüfen.

**Ausnahmen/Stopgrenzen:** Adapter für Protokollwechsel, Policy, Security, Lifecycle, Austauschbarkeit oder stabile Drittanbietergrenzen können trotz ähnlicher Signaturen wertvoll sein. Decorators sind nicht pauschal falsch. Direktzugriff darf keine Sicherheits-/Kompatibilitätsgrenze umgehen.

**Ergebnis/Abschluss:** Unterschied der Modelle und Garantien oder konkret belegte Redundanz; Empfehlung mit Verlust-/Gewinnbilanz. Modultiefe ist separat M04, nicht Synonym für Abstraktionsqualität.

<a id="m04--modultiefe"></a>
## M04 — Modultiefe

**Auslöser:** Viele Aufruferentscheidungen, Weiterleitungsstufen oder kleine Komponenten bieten wenig verborgenes Verhalten.

**Inputs/Evidenz:** Formale API plus informeller Vertrag (Reihenfolge, Ressourcen, Nebenwirkungen, Fehler, Nebenläufigkeit), reale Aufrufsequenz und Implementierungsnutzen.

**Methode:** Stelle Wissen-/Setupkosten des Aufrufers dem verborgenem Nutzen gegenüber. Könnte er die Arbeit mit vergleichbarem Aufwand direkt erledigen, prüfe die eigenständige Boundary-Begründung. Untersuche redundante Weiterleitungen und durchgereichte Variablen. Defaults, typisierte Fähigkeiten oder eine kohärente Operation können Kosten senken. Ein fokussierter Context kann zusammengehörigen Zustand bündeln, darf aber kein globaler Datenkorb oder versteckte Abhängigkeit werden; Lebensdauer, Eigentum und möglichst Unveränderlichkeit festhalten.

**Ausnahmen/Stopgrenzen:** Kleine Module, Dispatcher und gleiche Signaturen verschiedener Implementierungen können sinnvoll sein. Keine Zeilen-/Klassen-/Parameterquote; tiefe Module legitimieren keine gemischten Verantwortlichkeiten. Keine Globals als pauschale Lösung für Durchreichen. Nicht jedes tiefe Modul schafft eine eigenständige Abstraktion (M03).

**Ergebnis/Abschluss:** Konkrete Interfacekosten und verborgener Nutzen; begründete Beibehaltung oder kleinste Vereinfachung, geprüft gegen Aufrufer- und Testvertrag.

Adaptiert aus Clairvoyance (MIT, Cody Bromley 2026): [Provenienz](../PROVENANCE.md), [Lizenz](../THIRD_PARTY_NOTICES.md).

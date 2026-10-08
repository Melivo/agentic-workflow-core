# Designentwicklung, Benennung und Vertragsdokumentation

Untersuche nur den betroffenen Diff beziehungsweise den bestätigten Prüfbereich und ausgelöste Methoden. Stil, Metrik oder Zeitdruck allein sind kein Defekt. Ein Befund braucht Stelle, Ursache und Wirkung. Keine zusätzliche Refactoringfreigabe; externe Schulden bleiben Folgearbeit, Review bleibt read-only.

<a id="m07--designentwicklung"></a>
## M07 — Designentwicklung

**Auslöser:** Eine Änderung hängt Sonderfälle an, dupliziert Regeln oder macht die bestehende Struktur erkennbar schwerer erweiterbar.

**Inputs/Evidenz:** Vorher-/Nachher-Vertrag und Diff, neue Anforderung, betroffene Aufrufer, vorhandene Struktur und Tests, Änderungsdruck und Constraints.

**Methode:** Frage, wie die betroffene Struktur mit Kenntnis dieser Anforderung aussehen würde, welche konkrete Abweichung der Diff erzeugt und welche kleinste passende Lösung die Abweichung vermeidet. Prüfe zusätzliche Flags, Abhängigkeiten, Parameter und Wiederholung auf gemeinsame Wissenseigentümerschaft. Dieselbe Syntax kann unabhängige Regeln ausdrücken: nicht automatisch extrahieren. Bei demselben Wissen vergleiche fokussierte Extraktion mit einmaliger Ausführung am passenden Eigentümer; die Extraktion muss Interfacekosten rechtfertigen. Prüfe mitgeänderte Kommentare gegen das tatsächliche Verhalten. Betrachte bei wiederholtem Shortcut-Muster den nächsten ähnlichen Änderungsfall, ohne spekulative Prognose als Messung auszugeben.

**Ausnahmen/Stopgrenzen:** Die kleinste Änderung kann die beste sein; eine Verbesserung über das bestätigte Ziel hinaus ist keine Pflicht. Zeitdruck, TODOs oder Workarounds beweisen keine Qualitätsverletzung. Keine feste Design-Investitionsquote, pauschale TDD-Kritik oder automatische Schuldenreparatur. Charakterisierung, Produktionsrefactoring, Bugfix und Feature bleiben getrennte Arbeitsarten.

**Ergebnis/Abschluss:** Belegtes Design-/Wissensdelta, Vertrags- und Testfolgen, Status quo oder eng begründete Richtung; Verbesserung außerhalb des Tasks als Folgearbeit mit Nutzen/Risiko statt Mutation.

<a id="m08--benennung-und-verstandlichkeit"></a>
## M08 — Benennung und Verständlichkeit

**Auslöser:** Ein Name erzeugt falsche Erwartungen, dieselbe Bezeichnung meint verschiedene Dinge oder eine Verantwortung lässt sich schwer präzise benennen.

**Inputs/Evidenz:** Deklaration, tatsächliche Verwendung, Scope-Distanz, lokale Konventionen und sichtbare/nicht sichtbare Seiteneffekte; Leserfeedback, falls vorhanden.

**Methode:** Prüfe den Namen ohne Implementierungsdetails, dann am tatsächlichen Kontext: benennt er Bedeutung, Einheiten und relevante Constraints korrekt? Weite Sichtbarkeit verlangt mehr Präzision, nicht automatisch mehr Wörter. Halte gleiches Konzept/gleicher Name und verschiedene Konzepte/unterscheidbare Namen zusammen. Vergleiche vorhergesagtes mit tatsächlichem Verhalten; indirekte Event-Flüsse, untypisierte Container oder überraschende Hintergrundarbeit brauchen explizite Verträge. Schweres Benennen ist Anlass, gemischte Verantwortung zu prüfen, nicht Beweis dafür. Reduziere benötigtes Wissen, nutze bekannte Konventionen und dokumentiere verbleibende nicht offensichtliche Bedeutung.

**Ausnahmen/Stopgrenzen:** Kurze lokale Namen und etablierte Domänenbegriffe sind legitim. Kein repositoryweiter Rename aus lokaler Kritik. Öffentliche Namen sind Verträge; Änderungen brauchen Kompatibilitätsprüfung und passenden Task.

**Ergebnis/Abschluss:** Konkrete Fehlinterpretation mit Use-Site und Wirkung; passender Name/Vertrag oder begründete Beibehaltung. Gemischte Verantwortung wird nachgeprüft, nicht automatisch aufgespalten.

<a id="m09--vertragsdokumentation"></a>
## M09 — Vertragsdokumentation

**Auslöser:** Kommentare wiederholen Syntax, widersprechen Verhalten, lassen notwendige Bedingungen offen oder müssen komplexe Ausnahmen erklären.

**Inputs/Evidenz:** Betroffene API/Implementierung, Dokumentation, Aufrufererwartungen, Einheiten, Grenzen, Ressourcenbesitz, Fehler und Seiteneffekte.

**Methode:** Unterscheide Interfacebeschreibung (Fähigkeit, Bedeutung, Bedingungen), Implementierungsbegründung (warum dieser Mechanismus), modulübergreifende Invarianten (ein kanonischer Ort mit Verweisen) und Datenfeldsemantik (Einheit, Bereich, Nullbarkeit, Eigentum, Beziehungen). Dokumentiere das nicht aus Name/Typ erkennbare Wissen. Interfaceprosa soll die Nutzung ohne Implementierungslektüre erlauben, keine austauschbaren Interna festschreiben. Prüfe lange qualifizierte Beschreibungen auf echte Vertragskomplexität. Bei autorisiertem neuen Design kann eine kurze Vertragsbeschreibung vor Implementierung die Grenze prüfen; dies ersetzt weder Tests noch TDD. Pflege betroffenes Wissen genau einmal nahe dem relevanten Code oder am belegten kanonischen Ort.

**Ausnahmen/Stopgrenzen:** Fachlich komplexe öffentliche Verträge dürfen umfangreich sein. Nicht jedes Feld benötigt einen Kommentar; keine Kommentarquote. Lesbarkeit ist kein Vorwand, unbekannte Invarianten zu löschen oder eine Designentscheidung als Schreibkorrektur auszuführen.

**Ergebnis/Abschluss:** Bestätigte Dokumentationslücke/-drift mit Vertragsbezug und kanonischer Zielstelle; Strukturverdacht bleibt separate Nachprüfung. Kein unbelegtes Nutzen-, Kosten- oder Tokenversprechen.

Adaptiert aus Clairvoyance (MIT, Cody Bromley 2026): [Provenienz](../PROVENANCE.md), [Lizenz](../THIRD_PARTY_NOTICES.md).

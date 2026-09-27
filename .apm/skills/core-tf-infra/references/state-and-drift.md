# State und Drift

Lade diese Referenz nur bei Backend-, State-, Locking-, Import- oder Driftwirkung. Der Einstiegsskill bleibt Eigentümer der Autorisierungsentscheidung.

## State-Grenzen

1. Identifiziere Root-Module, Backend, State-Eigentümer, Zielumgebung und Verbraucher, bevor du eine Änderung entwirfst.
2. Isoliere State mindestens nach Umgebung und Blast Radius. CLI-Workspaces allein sind keine Sicherheits- oder Berechtigungsgrenze.
3. Bevorzuge für Zusammenarbeit ein Remote Backend mit Verschlüsselung, Zugriffskontrolle, Versionierung beziehungsweise Recovery und vom Backend unterstütztem Locking. Dokumentiere ausdrücklich, wenn eine Fähigkeit technisch nicht verfügbar ist.
4. Behandle State, gespeicherte Pläne, Crashlogs und Outputs als sensible Artefakte. `sensitive = true` reduziert Anzeige, entfernt Werte aber nicht zuverlässig aus State oder Plan.
5. Halte Backend-Credentials außerhalb von HCL und Repository. Verwende getrennte, kurzlebige Identitäten für lesende Planung und schreibende Ausführung, soweit der Provider dies unterstützt.
6. Prüfe die Bootstrap-Abhängigkeit des State-Backends. Seine Erstellung, Migration und Wiederherstellung benötigen einen eigenen dokumentierten Pfad und dürfen nicht von einem bereits benötigten Backend abhängen.

Lokaler State ist nur für ausdrücklich begrenzte, nicht geteilte und nicht produktive Arbeit vertretbar. Er darf weder stillschweigend als Teamstandard übernommen noch mit echten Secrets versioniert werden.

## Locking und State-Mutationen

State-Operationen verändern die Zuordnung zwischen Konfiguration und realer Infrastruktur und sind keine gewöhnlichen Dateiedits. Import, Move, Remove, Replace-Markierung, Unlock und Backendmigration benötigen eine genaue Autorisierung für State, Umgebung und Operation.

Vor einer autorisierten State-Mutation:

- aktuellen Besitzer und Freshness des State belegen,
- Schreibaktivität und bestehende Locks prüfen,
- versionierte Sicherung oder getesteten Recoverypunkt benennen,
- Quell- und Zieladressen sowie erwartete reale Ressourcen erfassen,
- Parallelzugriffe stoppen, ohne fremde Prozesse gewaltsam zu beenden,
- Vorher-/Nachher-Inventar und Wiederherstellungsweg festlegen.

Ein Lock wird nie nur wegen seines Alters gebrochen. Force-Unlock verlangt Evidenz, dass kein legitimer Writer mehr aktiv ist, sowie eine separate ausdrückliche Autorisierung.

## Drift klassifizieren

Drift ist eine Abweichung zwischen Konfiguration, State und realer Ressource. Ein bereitgestellter Plan darf statisch analysiert werden; jede neue Live-Ermittlung über Provider oder Backend folgt den Autorisierungsgrenzen aus `SKILL.md`.

Ordne jede Abweichung genau einer Behandlung zu:

| Klasse | Behandlung |
|---|---|
| nicht autorisierte Fremdänderung | Ursache und Owner klären; nicht blind überschreiben |
| absichtlich außerhalb Terraform verwaltet | Eigentumsgrenze dokumentieren und Konfiguration klar trennen |
| gewünschte bestehende Ressource | kontrollierten Import mit stabiler Adresse und aktueller Autorisierung planen |
| veralteter State | Backend-, Lock- und Refreshursache untersuchen; keinen State manuell editieren |
| veraltete Konfiguration | kleinste HCL-Korrektur mit Impact- und Vertragsprüfung |
| Provider-/Defaultänderung | Version, Schema und Ersatzwirkung belegen; aktuelle offizielle Doku nur bei konkreter Lücke laden |

Verwende `ignore_changes` nur für ein belegtes externes Eigentum einzelner Attribute. Es ist kein Mittel, ungeklärte Drift, Securityabweichungen oder wiederkehrende manuelle Änderungen zu verbergen.

## Evidenz und Ergebnis

Berichte Backend und Isolation, Lockingmechanismus, Verschlüsselung und Recovery, State- und Planzugriff, Secret-Risiken, Driftklasse, gewählte Behandlung und verbleibenden Blast Radius. Wenn keine autorisierte Live-Prüfung stattfand, kennzeichne den Befund ausdrücklich als statisch oder aus bereitgestellter Evidenz abgeleitet.

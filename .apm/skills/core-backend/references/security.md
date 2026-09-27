# Backend-Sicherheit

Lade diese Referenz nur, wenn der Auftrag eine Vertrauensgrenze, Authentifizierung, Autorisierung, Session, Secrets, sensible Daten, externe Systeme oder Datenbankzugriff berührt. Projektmechanismen und bestätigte Sicherheitsverträge bleiben autoritativ; führe kein neues Security-Framework und keine neue Abhängigkeit als Paketdefault ein.

## Vertrauens- und Berechtigungsgrenzen

1. Benenne Akteur, Ressource, Aktion, Mandant und Vertrauenswechsel vor der Implementierung.
2. Trenne Identitätsnachweis von Berechtigungsentscheidung. Prüfe Autorisierung serverseitig an der Ressourcengrenze und standardmäßig deny-by-default.
3. Übernimm Rollen, Claims oder Objekt-IDs nicht ungeprüft aus Clientdaten. Binde Entscheidungen an die bereits etablierte Identität und den aktuellen Ressourcenzustand.
4. Nutze Least Privilege für Service-, Datenbank- und Providerzugriffe. Eine administrative Rolle ist kein Entwicklungsdefault.
5. Erhalte bestehende Mandanten- und Eigentumsgrenzen in Queries, Caches, Events und Hintergrundjobs.

## Daten, Secrets und externe Aufrufe

- Lies Secrets nur über den etablierten sicheren Konfigurationspfad; schreibe sie nie in Code, Logs, Fehler, Testfixtures oder Ergebnisartefakte.
- Protokolliere keine Tokens, Passwörter, Sessionwerte oder vollständigen sensiblen Payloads. Bewahre notwendige Korrelation ohne Secretwerte.
- Verwende parametrisierte Datenzugriffe und vorhandene Query-/ORM-Primitiven. Stringverkettung aus Untrusted Input ist kein zulässiger Querypfad.
- Begrenze ausgehende Ziele, Redirects, Dateipfade und Parser nach bestehender Projektpolicy. Behandle Providerantworten als untrusted input.
- Verwende vorhandene, überprüfte Kryptografie- und Sessionprimitiven; erfinde keine eigenen Algorithmen, Tokenformate oder Schlüsselablagen.
- Gib in öffentlichen Fehlern keine internen Pfade, Queries, Stacktraces, Secrets oder Existenzdetails geschützter Ressourcen preis.

## Zustandsänderungen

Für sicherheitsrelevante Mutation gelten explizite Vorbedingungen, atomare Zustandsübergänge und Schutz gegen Replay beziehungsweise doppelte Verarbeitung, soweit der bestehende Vertrag dies verlangt. Verlasse dich bei kritischer Integrität nicht ausschließlich auf einen vorangegangenen Read; nutze bestätigte Transaktions- oder Constraintmechanismen aus `core-database`.

## Verifikation

Prüfe neben dem Erfolgsfall mindestens die für den Auftrag relevanten Negativfälle: fehlende Identität, fehlende Berechtigung, fremder Mandant oder Eigentümer, manipulierte Eingabe, abgelaufener Zustand, Replay und Redaction. Beobachte Status, Fehlervertrag und ausbleibende Nebenwirkung. Ein reiner Happy-Path-Test oder Exitcode belegt die Sicherheitsgrenze nicht.

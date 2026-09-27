# Transaktionen und Nebenläufigkeit

Lade diese Referenz, wenn mehrere Operationen gemeinsam konsistent sein müssen, konkurrierende Zugriffe möglich sind oder ein Workflow Locking, Isolation, Retry beziehungsweise verteilte Koordination berührt.

## Konsistenzvertrag

Dokumentiere vor der Umsetzung:

- ACID-Erwartung für relationale Transaktionen oder BASE-/Konsistenzkompromiss für verteilte und nichtrelationale Flows,
- fachliche Invariante und atomare Transaktionsgrenze,
- beteiligte Tabellen, Aggregate oder Dienste,
- gewählte Isolation und konkret verhinderte Anomalien,
- Lockingstrategie, Lockreihenfolge und Timeout,
- Retry-, Idempotenz- und Konfliktverhalten,
- beobachtbares Commit-, Rollback- und Fehlersignal.

Wähle Isolation und Locks nach belegtem Konfliktrisiko und den vorhandenen Engine-/Projektkonventionen; verwende weder pauschal die stärkste noch die schwächste Stufe.

## Implementierungsregeln

- Halte Transaktionen so klein wie die fachliche Invariante erlaubt. Führe keine langsamen Netzwerkaufrufe oder Benutzerinteraktion innerhalb einer Datenbanktransaktion aus.
- Lies entscheidungsrelevanten Zustand und schreibe die abhängige Änderung atomar oder nutze einen bestätigten optimistischen Konfliktmechanismus.
- Lege für pessimistische Locks eine stabile Reihenfolge und begrenzte Wartezeit fest; Deadlocks werden erkannt, begrenzt wiederholt und sichtbar gemeldet.
- Wiederhole nur Fehler, die der Treiber oder Projektvertrag als transient klassifiziert. Ein Retry benötigt idempotente Wirkung oder einen eindeutigen Idempotency-Key.
- Verlasse dich nicht auf In-Memory-Locks für Integrität über Prozesse oder Instanzen hinweg.
- Bei serviceübergreifenden Flows dokumentiere Konsistenzfenster, Outbox/Inbox-, Saga- oder Kompensationsmechanismus und dessen Fehlerzustände. Behaupte keine globale ACID-Garantie ohne entsprechenden Vertrag.

## Verifikation

Prüfe Commit und Rollback sowie die materiellen Parallelfälle: konkurrierendes Update, Duplikat/Replays, Timeout, Deadlock oder Versionskonflikt. Belege, dass die Invariante erhalten bleibt und partielle Wirkungen entweder nicht sichtbar werden oder kontrolliert kompensiert werden. Nutze Engine-spezifische Syntax erst nach Prüfung der vorhandenen Version und Konvention.

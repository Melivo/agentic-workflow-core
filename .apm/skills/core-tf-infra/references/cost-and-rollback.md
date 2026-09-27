# Kosten und Rollback

Lade diese Referenz bei Ressourcenanlage, Größenänderung, Ersatz, Datenbewegung, laufenden Ausgaben, Kontinuitätsanforderungen oder möglichem Datenverlust.

## Kostenwirkung

Erstelle vor einer materiellen Infrastrukturänderung eine nachvollziehbare Delta-Sicht statt einer bloßen Gesamtschätzung:

| Dimension | Zu erfassende Wirkung |
|---|---|
| einmalig | Migration, Backfill, Snapshot, Restore, Datenkopie, Parallelbetrieb und Egress |
| laufend | Compute, Storage, Requests, Lizenzen, Logs, Monitoring, Backups und Supporttier |
| variabel | Traffic, Autoscaling, Queue-/Eventvolumen, Datenwachstum und regionsübergreifender Transfer |
| Ersatz | temporärer Doppelbetrieb, neue Adressen, Neuübertragung und vorzeitige Vertragskosten |
| Risiko | fehlende Tags/Budgets, unbegrenzte Skalierung, Quoten, Mindestlaufzeit und Kosten bei Fehlerwiederholung |

Nenne Annahmen, Preisregion, Einheit, Zeitraum und Unsicherheit. Vorhandene Budget-, Tagging- und Kostenstellenkonventionen haben Vorrang. Ein externes Kostentool oder Providerzugriff wird nur mit der dafür erforderlichen Netzwerk-, Credential- und gegebenenfalls Produktionsautorisierung ausgeführt; andernfalls bleibt die Schätzung statisch und als solche gekennzeichnet.

Kostenoptimierung darf Verfügbarkeit, Verschlüsselung, Backup, RPO/RTO oder Least Privilege nicht stillschweigend schwächen. Reservierungen, Commitments und lange Bindungen sind eigene finanzielle Entscheidungen und keine automatischen Defaults.

## Änderungs- und Recoveryklassen

Klassifiziere jede Ressource des erwarteten Deltas:

- **create:** neue Kosten, Quoten, Abhängigkeiten und spätere Löschbarkeit,
- **in-place update:** Unterbrechung, inkompatible Defaults und Recovery des vorherigen Werts,
- **replace:** Reihenfolge, Doppelbetrieb, Namens-/Adresskonflikte, Datenübernahme und Downtime,
- **delete:** Datenverlust, Retention, Abhängigkeiten und Wiederherstellbarkeit,
- **unknown:** Aktion bleibt blockiert, bis Providerverhalten und Planwirkung belegt sind.

Ein HCL-Revert ist nicht automatisch ein Rollback. Externe Daten, DNS, Zertifikate, Warteschlangen, Secrets, irreversible Provideroperationen und bereits konsumierte Outputs können eine reine Rückkehr zur alten Konfiguration verhindern.

## Rollback und Roll-forward

Definiere vor einer produktiven oder schwer reversiblen Änderung:

1. Eintrittskriterien für Abbruch und Recovery,
2. Owner und Entscheidungsweg,
3. letzten nachweislich wiederherstellbaren State- und Datenstand,
4. Sicherung, Aufbewahrung und getesteten Restorepfad,
5. Reihenfolge für Traffic, Compute, Daten, Identität und State,
6. maximal tolerierte Unterbrechung und Datenverlust als RTO/RPO,
7. Verifikation nach Rollback oder Roll-forward,
8. Aufräumarbeiten mit eigener Autorisierung für destruktive Schritte.

Bevorzuge Roll-forward, wenn ein Rückbau Daten oder State inkonsistent machen würde. Ersatzressourcen werden erst entfernt, nachdem Daten, Traffic, Monitoring und Recovery belegt sind. Backup-Existenz allein beweist keine Wiederherstellbarkeit; Restore und Abhängigkeiten müssen für den relevanten Pfad geprüft sein.

## Kontinuität und Drift nach der Änderung

Dokumentiere Single Points of Failure, Zonen-/Regionsabhängigkeiten, Quoten, externe Dienste, DNS/Zertifikate, State-Backend und Identitätsprovider. Lege fest, welche Signale Fehlfunktion, Kostenanomalie oder neue Drift anzeigen und wer reagiert.

Nach einer autorisierten Live-Änderung werden tatsächliche Wirkung, Kostenindikatoren, Health-Signale und verbleibende Drift gegen den freigegebenen Plan geprüft. Nicht autorisierte Cleanup-, Destroy- oder Kostenoptimierungsaktionen werden nicht aus einem erfolgreichen Apply abgeleitet.

## Ergebnis

Berichte Kostenbaseline und Delta mit Annahmen, Änderungs- und Recoveryklassen, RTO/RPO, Backup-/Restore-Evidenz, Rollback- und Roll-forward-Weg, Abbruchkriterien, Owner sowie verbleibende finanzielle und betriebliche Risiken. Wenn kein aktueller Live-Plan oder Kostenzugriff autorisiert war, nenne diese Evidenzgrenze ausdrücklich.

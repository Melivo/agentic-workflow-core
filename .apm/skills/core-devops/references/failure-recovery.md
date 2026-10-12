# Fehlerbehebung und sichere Recovery

Ziel ist die sichere Zustandsklärung, nicht automatisches Wiederholen. Nach fehlgeschlagenen oder möglicherweise partiell ausgeführten Aktionen zuerst den aktuellen Zustand beobachten.

## Erst sichern, dann diagnostizieren

1. Notiere konkrete Fehlermeldung, Befehl/Task, Arbeitsverzeichnis, Zeitpunkt, betroffene Pfade/Refs und letzten erfolgreichen Schritt. Secrets und private Werte redigieren.
2. Prüfe Worktree/Index, Konfliktmarker, generierte Artefakte, Prozesse/Ports und Providerlaufstatus passend zum Fehler. Prüfe, ob eine Mutation bereits teilweise wirksam wurde, bevor du erneut ausführst.
3. Lies Taskdefinition, Toolversion, Projektkonfiguration und relevante Logs; vergleiche gegen bekannten funktionierenden Stand. Keine unbeteiligten Verzeichnisse pauschal bereinigen.
4. Hypothesen einzeln prüfen und reversible, eng begrenzte Schritte bevorzugen. Reparatur, Wiederherstellung aus Backup und Reset sind unterschiedliche Wirkungen.

## Häufige Fälle

| Symptom | Sichere erste Prüfung | Recovery-Grenze |
|---|---|---|
| Task fehlt | verfügbare Tasks und zuständige Konfigurationsdatei lesen | keinen neuen Alias oder Runner erfinden |
| Runtime/Tool fehlt | deklarierte Version und Installationsquelle prüfen | Installation nur mit Freigabe, keine stille automatische Beschaffung |
| Task hängt | Prozess, Prompt, Netzwartezeit und Servermodus bestimmen | nicht blind mehrfach starten; kontrolliertes Beenden nur bei Autorisierung |
| Port belegt | Projektkonfiguration und Prozesszuordnung identifizieren | fremde Prozesse nicht beenden ohne Freigabe |
| Hook schlägt fehl | konkrete Hookausgabe, staged Diff und lokale Toolverfügbarkeit prüfen | nicht umgehen; nur Ursache oder Committext innerhalb Auftrag korrigieren |
| CI rot | betroffenen Job, Commit-SHA, Logs, Eingaben und Abhängigkeiten prüfen | fehlgeschlagener Check bleibt fehlgeschlagen; keine weichere Ersatzpipeline |
| Git-Konflikt | Ziel-/Quellref und beide Änderungsabsichten sichern | unbekannte Semantik eskalieren; kein automatisches ours/theirs |
| Push abgelehnt | Remotezustand und lokale Divergenz lesen | nicht auf Force wechseln; Integration neu beurteilen |
| Release/Paket teilweise | Tag, Commit, Asset und Providerstatus gezielt abgleichen | vor Retry Duplicate/Version-Kollision ausschließen |

Nach Recovery den kleinsten betroffenen Check erneut ausführen und die Wiederherstellung am aktuellen Zustand nachweisen. Wenn Datenverlust, Secret, unklare fremde Arbeit oder Shared-History-Risiko besteht, vor weiterer Mutation stoppen. Berichte enthalten Belege und offene Unsicherheit, nicht nur eine vermutete Ursache.

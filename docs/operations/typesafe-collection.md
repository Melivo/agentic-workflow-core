# TypeSafe-Collection: Aufnehmen, zustellen und wiederherstellen

Dieses Runbook beschreibt die optionale, explizit bediente Sammlung minimierter Planvergleichsereignisse. Der reguläre Planreview-Versuch gehört `core-plan`, nicht diesem Runbook; ein Ereignis ist kein Modellurteil oder Freigabe. Core besitzt Projektion, lokale SQLite-Sammlung, Outbox und CLI; automation-infra besitzt Pi-Erstinstallation, Unit und Allowlist. Ein erfolgreicher lokaler Aufruf beweist keinen Pi-Betrieb.

## Datenstandard und Eigentum

Die Wiregrenze ist die geschlossene Version collection/v1; das eingebettete Vergleichsereignis bleibt plan-comparison/v1. Das Datenmodell umfasst Event-ID und Hashbindung, freigegebene pseudonyme Projektkennung, Plan-/Kriterienidentität, Modell-/Core-/Fragenmetadaten, Wahrscheinlichkeiten und optionale Usage, Revision/Vorgänger/Selektion, fixes Ersturteil und getrennte Adjudikationslabels. Die kanonische Schema- und Glossardefinition in diesem Dokument ist die einmalige fachliche Erklärung; API-Details liegen im kanonischen Modul [.apm/skills/core-typesafe/scripts/typesafe_collection.py](../../.apm/skills/core-typesafe/scripts/typesafe_collection.py). Der Repositorypfad scripts/typesafe_collection.py bleibt als Kompatibilitätswrapper erhalten.

Referenzen auf Plan, Review, Evidenz und Reviewerrolle werden vor der Zustellung zu opaken `ref-<SHA256>`-Werten minimiert. Originaltexte, Planprosa, Kriterien, Reviewtexte, Chat, Payload und Rohfehlermeldungen gehören nicht in den Pi-Export. Hashreferenzen sind keine Inhaltsfilter und keine Geheimnisgarantie: Der verantwortliche Owner muss Inhalt und ausdrücklich freigegebene pseudonyme Projektkennung vor der Aufnahme prüfen. Aufnahme begründet keine Zustimmung zur weiteren Nutzung.

Unbekannte optionale Zahlenwerte bleiben unbekannt/null, nicht Null als gemessener Wert. API-/Transportfehler und unbekannte Ergebnisse bleiben von einem echten Modellurteil getrennt; Fehler werden nicht als Nullwahrscheinlichkeit oder fachlicher Fail umgedeutet. Import akzeptiert nur geschlossene, typisierte und konsistente Daten einschließlich Historienbezügen; doppelte JSON-Schlüssel, ungültige Hash-/ID-Bezüge und nicht endliche Zahlen werden abgewiesen.

Die portable [Bundlebedienung](../../.apm/skills/core-typesafe/SKILL.md#portable-sammlung-und-lokale-konfiguration) beschreibt lokale nichtgeheime Config, fest formatierte Core-Pseudonyme und explizite Policyaktivierung. Legacydefault bleibt synthetic-a/b. Hashes authentifizieren keine Projekte; UID-/Socket- und SSH-Bindungsgrenzen bleiben bestehen. Keine globale Config oder privater State wird durch Import oder diese Dokumentation eingerichtet.

## Owner-Ablauf

1. Nach verborgen gespeicherter Vorbewertung, fixiertem blindem Ersturteil und getrennter Adjudikation derselben Reviewer-Session prüft der Owner die erlaubte lokale Config. Ohne Freigabe/Config keine Pufferung oder Zustellung; Fehler lassen die Beobachtung offen und sperren keine Produktarbeit. Owner von core-plan erzeugt ein Vergleichsereignis über project_event(source_event, projects=allowlist). Nur die freigegebene Projektion wird weitergereicht.
2. Dauerhaft lokal aufnehmen: `python3 scripts/typesafe_collection.py enqueue --projects <projects.json> --outbox <outbox.sqlite> --create` für die initial freie Outbox. Spätere Aufrufe verwenden dieselben Pfade ohne `--create`. Wiredaten werden über stdin übergeben, nicht als Argumente. Das erfolgreiche Receipt bestätigt nur den lokalen Commit.
3. Zustellung ist ein eigener bewusster Schritt: `python3 scripts/typesafe_collection.py flush --projects <projects.json> --outbox <outbox.sqlite> --ssh-target <operator-alias>` oder lokal `python3 scripts/typesafe_collection.py flush --projects <projects.json> --outbox <outbox.sqlite> --socket <socket-path>`. Es gibt keinen Hintergrundversand oder automatischen Retry. Ein Flush verarbeitet höchstens 100 Einträge unter gemeinsam höchstens 15 Sekunden; bestätigte Einträge können schon entfernt sein, wenn ein späterer Eintrag fehlschlägt. Verbleibende Einträge bleiben für einen späteren expliziten Versuch.
4. Der Pi bestätigt Event-ID und gespeicherten Payloadhash erst nach Commit. Nur passende Acks entfernen genau den lokalen Outboxeintrag. Timeout, falsche Antwort, Abbruch oder Ausfall sind Transportstatus, nicht Modellurteil; Wiederholung desselben Events ist idempotent.

CLI-Receipt-Texte und Rückgabecodes beschreiben jeweils nur den lokalen Schritt. Ein Enqueue ohne Flush ist dauerhaft gepuffert, nicht zugestellt. Ein Flush-Erfolg meldet bestätigte Zustellversuche, keine neue globale Ereigniszahl oder Workflowfreigabe.

## Grenzen und Fehler

- Einzelnes Wireereignis höchstens 64 KiB, JSON-Tiefe höchstens 32, Empfangsfrist 5 s und begrenzte Antwort. CLI-Flush: maximal 100 Einträge und 15 s insgesamt.
- Lokale Outbox: höchstens 10.000 Einträge oder 64 MiB Payload. Vollstand lehnt vor Annahme ab; vorhandene Einträge werden nicht verdrängt.
- Outbox wird mit privater 0700-Elternablage betrieben. Erstinitialisierung darf --create; Restart und normale Nutzung nicht. Vorhandene unsichere/fremde Pfade oder Schemas werden nicht übernommen.
- Transport hat keine automatische Endlosschleife. Ein Netzwerk-/Pi-/Socketausfall lässt nicht bestätigte Daten lokal stehen. Dateisystem-, SQLite- oder Hardwarefehler können Dauerhaftigkeit verhindern und müssen als Persistenzfehler sichtbar bleiben.
- Fristen begrenzen die implementierten I/O-Pfade, garantieren aber keine Echtzeit gegen blockiertes Dateisystem oder nicht unterbrechbaren Kernel-I/O.

Die SSH-Variante nutzt einen bereits konfigurierten Operatoralias und die feste Remoteaktion des Infra-Runbooks. Sie öffnet keinen Listener, Port oder Tunnel und ändert weder SSH, sudoers, Tailnet noch Firewall. Vorhandene Adminrechte können naturgemäß administrieren; dies ist keine Isolation gegen Admin/root.

## Sicherung und isolierte Wiederherstellung

Nutze die SQLite-Backup-API über `python3 scripts/typesafe_collection.py snapshot --projects <projects.json> --database <db> --destination <freier-pfad>`; kopiere keine geöffnete SQLite-Datei. Wiederherstellung erfolgt mit `python3 scripts/typesafe_collection.py restore --projects <projects.json> --snapshot <snapshot> --destination <freier-pfad>` in einen eigenen freien privaten Drillpfad. Prüfe Integrität und kanonische Ereigniswerte/Hashes. Überschreibe niemals die Live-DB oder einen vorhandenen Pfad.

Der Snapshot dokumentiert seinen Aufnahmezeitpunkt. Ohne gesonderte Sicherungsfrequenz gibt es kein RPO-Versprechen; diese Schnittstelle belegt weder Borg/Offsite noch Datenträgerausfall, RTO oder allgemeinen Pi-Betrieb.

### Datierte synthetische Pi-Beobachtungen

Die einmalige T05-Abnahme dokumentierte am 2026-11-10T01:53:14.685543+00:00 insgesamt 16 synthetische Ereignisse. Der vollständige CK08-Nachweis einschließlich Quell-/Unitbindung steht im Original unter `.agentic-workflow/runs/run-G06-M04-v2-p01-r01/tasks/T05/attempt-01.yaml`; dessen kanonischer Ereignisbestand hatte SHA256 `898da84fd4ebe3594a80943c9d04ea3c29dcb701d99399f20030a2e324d65f21`.

Eine spätere einmalige Coordinator-Abnahme führte denselben gepinnten CK08-Aufruf am 2026-11-10T02:30:26.152689+00:00 aus: Baseline 16 erhalten, genau 8 neue synthetische Ereignisse aufgenommen, insgesamt 24; Unit enabled/active und ACK-loss-Replay, Ausfall/Reopen sowie UID-/Projekt-/Payload-Abweisungen bestätigt. Sicherung und isolierter Restore meldeten `integrity ok` und `complete_values_equal`; der kanonische Ereignisbestand hatte SHA256 `77940097d55e35289f9a0e44137acf796f6ae1050eb368708557180ad2fa232e`. Pi-Drill: `/var/lib/automation/state/typesafe-collection/drill-95cd750baf3a4f2d9bf7197dd4e08978`; lokale, danach leere Outbox: `/tmp/opencode/typesafe-collection-T05-1u4ethre/outbox.sqlite`. Receipt, Identität, Ressourcen-Inodes sowie Core-Quell- und Unit-Hash blieben gegenüber dem T05-Original unverändert.

Das sind zwei zeitgebundene synthetische Beobachtungen, keine fortlaufende Zustandsprüfung, allgemeine Verfügbarkeitszusage oder reguläre Pilotabnahme. Sie belegen keine Offsite-/Borg-Sicherung, automatische Sicherungsfrequenz, RPO/RTO, Datenträger-/Hardwareausfall, Pi-Reboot oder Modellgüte. Wiederholung des Hostchecks, Neuinstallation oder ein Servicezyklus sind aus diesen Dokumentationsbelegen nicht abgeleitet.

## Quellchecks

Aus Core-Repositorywurzel, mit vorhandener Toolchain und ohne Setup:

~~~sh
python3 -B -m unittest discover -s tests -p 'test_typesafe_collection*.py' -v
python3 -B -m unittest discover -s tests -p test_typesafe_comparison.py -v
~~~

Diese lokalen synthetischen Tests belegen Quellverhalten, keine Pi-Installation oder Livezustellung. Sie prüfen auch die portable Bundlequelle, ändern aber weder Workflowstatus noch eine Hostinstallation.

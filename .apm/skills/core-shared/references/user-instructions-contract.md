# Vertrag für Benutzeranweisungen

Dieser Vertrag gilt gemeinsam für `core-init-project` und `core-user2agent-instructions`. Er schützt manuelle Inhalte und verhindert konkurrierende Schreiber für `AGENTS.md`.

## Pfade und Richtung

- globale Quelle: `Path.home() / "AGENTS.md"`
- Projektziel: `Path.cwd() / "AGENTS.md"`
- zulässige Synchronisierungsrichtung: global → Projekt

Beide Pfade werden vor einer Vorschau absolut aufgelöst und angezeigt. Benutzer-Home oder Dateisystemroot dürfen nicht als Projektziel behandelt werden.

## Standardauswahl

Standardmäßig werden nur eindeutig manuelle Benutzeranweisungen zur Übernahme angeboten. Ausgeschlossen bleiben:

- generierte oder verwaltete Blöcke,
- globale Spezialkonfiguration eines Harnesses oder Providers,
- Secrets und Zugangsdaten,
- flüchtige Health-, Session- oder Workflowstatuswerte,
- Inhalte ohne eindeutige Herkunft oder Eigentümerschaft.

Der projektspezifische verwaltete Block enthält nur belegte Projektinvarianten, Preflight-Informationen und einen kompakten Routingindex. Ausführliche Fachmethodik bleibt in Skills und Referenzen.

## Vorschau und Bestätigung

1. Quelle und Projektziel read-only einlesen.
2. Manuelle Kandidaten und den exakten Zielabschnitt bestimmen.
3. Den vollständigen geplanten Diff mit beiden absoluten Pfaden anzeigen.
4. Eine separate ausdrückliche Bestätigung genau dieses Diffs abwarten.
5. Nur den bestätigten Zielabschnitt schreiben; Inhalte außerhalb davon bytegenau erhalten.
6. Marker, Zielbereich und unveränderte Außenbereiche erneut lesen und verifizieren.

Eine Bestätigung gilt nur für die gezeigte Fassung. Ändert sich Quelle oder Ziel vor dem Schreiben, wird die Vorschau verworfen und neu erzeugt. Schweigen oder eine frühere allgemeine Zustimmung reicht nicht.

## Marker und Idempotenz

Ein verwalteter Projektabschnitt verwendet stabile, eindeutig gepaarte Marker. Aktualisierungen ersetzen nur den Inhalt zwischen diesen Markern. Fehlen beide Marker vollständig, darf der Eigentümer des Zielblocks nach ausdrücklicher Bestätigung des exakten Diffs ein neues, eindeutig gepaartes Markersegment anlegen; dies autorisiert weder Scheduler-/Workflowänderungen noch Folgefreigaben. Fehlt nur ein Marker oder sind Marker doppelt, verschachtelt oder beschädigt, blockiert die Mutation; sie werden nicht heuristisch repariert. Prüfe Zielbereich und unveränderte Außenbereiche nach der Neuanlage erneut. Dieselbe bestätigte Eingabe muss ohne weitere Änderungen denselben Zielinhalt erzeugen.

`core-init-project` bleibt alleiniger Eigentümer seines Projektblocks. Inline verwendete Konfiguratoren oder Provider dürfen keinen konkurrierenden `AGENTS.md`-Schreibmodus aktivieren.

## Vollständige Dateiübernahme

Eine vollständige Kopie der globalen Datei ist eine gewarnte Ausnahme. Vorher werden Quelle, Ziel, gesamter Diff und der Verlust beziehungsweise die Überschreibung projektspezifischer Inhalte erklärt. Die Aktion benötigt eine ausdrückliche Bestätigung beider absoluter Pfade und des vollständigen Diffs.

## Priorität nach der Übernahme

Importierte globale Präferenzen bleiben unter aktuellen ausdrücklichen Benutzeranweisungen, bestätigten projektspezifischen Anweisungen, belegten Projektinvarianten und dem zuständigen Fachskill. Eine Synchronisierung kann keine höherrangige Regel, Autorisierung oder Projektgrenze abschwächen.

## Ergebnis

Der Abschluss berichtet Quelle, Ziel, übernommenen manuellen Abschnitt, erhaltene Außenbereiche und Verifikation. Es werden keine vollständigen vertraulichen Inhalte, Secrets oder Workflowstatuswerte protokolliert.

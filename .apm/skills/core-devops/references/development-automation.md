# Repoabhängige Entwicklungsautomation

Diese Referenz gilt für wiederholbare Projektaufgaben und ihre Verkabelung. „Aufgabe“ meint hier einen benannten Befehl samt Eingaben und Abhängigkeiten, nicht eine Workflow- oder Agentensteuerung.

## Bestand ermitteln

1. Finde Repositorywurzel und relevante Teilbereiche aus tatsächlichen Manifests, Arbeitsverzeichnis, Import-/Buildgrenzen und Projektanweisungen. Erfinde keine festen Verzeichnisse wie apps/web oder api.
2. Lies vorhandene Taskrunnerdateien (mise.toml, Makefile, package.json-Skripte, pyproject.toml, Justfile u. a.), Sprach-/Paketmanager-Manifeste, Versionpins, Lockfiles, Hookmanager, CI und Skripte. Entdecke Aufgaben mit dokumentierter CLI, etwa mise tasks ls, nur wenn mise bereits vorhanden/gewählt ist.
3. Notiere Aufgabe, Schreibwirkung, Voraussetzungen, Abhängigkeiten, betroffene Teilbereiche, Laufzeit und vorhandene lokale/CI-Nutzung. Prüfe Definitionen unbekannter Aufgaben vor Ausführung; Namen beweisen nicht, ob sie mutieren.
4. Skizziere Graph: unabhängige Prüfungen können parallel laufen, abhängige Schritte müssen auf erfolgreichem Vorgänger aufbauen. Serialisiere konkurrierende Formatter/Generatoren oder Aufgaben, die denselben Output ändern.

## Einrichten oder ausführen

- Nur prüfen: Bestehende Aufgaben benutzen, sofern Ausführung freigegeben ist. Keine Installation, Konfigurationsänderung oder Dependency-Aktualisierung ableiten.
- Einrichten: Nur im bestätigten Schreibscope. Eine Projektaufgabe muss reproduzierbare Eingabe, klare Abhängigkeiten, angemessene Ausgabe und Fehlerweitergabe haben. Nicht nebenbei Produktcode, Schema, Infrastruktur oder Deployment ändern.
- Werkzeugwahl: Für neue wiederholbare projektübergreifende Aufgaben mise bevorzugen, falls passend. Funktionierende vorhandene Werkzeuge und Teamgewohnheiten erhalten; kein Werkzeugwechsel allein der Einheitlichkeit wegen. APM ist keine Voraussetzung.
- Auslösen: Explizit sagen, welche Aufgabe ausgeführt wird und ob sie liest, Dateien schreibt, Code generiert, Dienste startet, Pakete baut oder Daten verändert. Einrichtung autorisiert keinen Run. Toolinstallation und Paket-/Deploymentwirkung bleiben eigene Freigaben.
- Generierung/Migration: Nur existierende Projektverträge, Schemaquellen und Generatoranweisungen nutzen; tatsächliche Ausgabepfade und Diff kontrollieren. Keine Datenbankmodellierung oder Migration entwerfen.

## Nachweis

Lokal und CI sollten dieselben Projektaufgaben verwenden, wenn das Projekt sie bereits definiert. Plattformworkflow darf Plattformsyntax enthalten, soll aber keine zweite abweichende Prüfimplementierung erzeugen. Prüfe Exitcode, relevante Ausgabe, Seiteneffekte und Artefakte. Dokumentiere Aufgabe, Voraussetzungen, Abhängigkeiten, Schreibwirkung und erwartete Nutzung knapp; bette keine Secrets in Taskdefinitionen ein.

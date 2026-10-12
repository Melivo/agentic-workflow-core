# Checks, Validierung und Hooks

Lade diese Referenz für lokale Prüfketten, Commit-Hooks und deren CI-Entsprechung.

## Prüfstrategie

- Beginne mit dem Projekt-Quickcheck oder einer vorhandenen Sammelaufgabe. Ergänze nur Prüfungen, die betroffene Verträge sinnvoll abdecken: Formatcheck, Lint, Typ-/Syntaxprüfung, relevante Tests, Security-/Dependency-Checks und gegebenenfalls Build.
- Trenne schreibende Werkzeuge (Formatter, Generator, Fixer) von nicht mutierenden Checks. Prüfe vor Formatterlauf den Worktree und begrenze ihn auf beauftragte Pfade, damit fremde Änderungen nicht überschrieben werden.
- Lies jeden Task-/Hookbefehl, ehe er ausgelöst wird. Erfasse Voraussetzungen, Datenzugriff, Netz, Dauer und Nebenwirkungen; baue keine Ersatzprüfung, die Fehler nur durch erfolgreiches Placeholder-Ergebnis verdeckt.
- Checks auf geänderten Dateien sind nützlich, ersetzen jedoch keinen vollständigen Check, wenn gemeinsame Konfiguration oder Abhängigkeiten betroffen sind.

## Hooks

Erhalte den schon verwendeten Hookmanager (zum Beispiel pre-commit, Husky, Lefthook oder Git-eigene Hooks), sofern kein genehmigter Grund zum Wechseln vorliegt. Ein Hook soll schnell, deterministisch und lokal verfügbar sein. Keine Downloads/Toolinstallation beim Commit als Überraschung; Tools vorher in einem ausdrücklich autorisierten Setup bereitstellen. Commit-Messageprüfung an den tatsächlich dafür vorgesehenen Hooktyp anschließen.

Bei Setup: bestehende Hooks und staged-only Regeln prüfen, kein paralleles zweites Hooksystem ohne Begründung einführen. Hook muss ausschließlich die beabsichtigten gestagten Pfade prüfen oder Dateien innerhalb des beauftragten Scopes verändern. Niemals unstaged Änderungen umformatieren, fremde Inhalte stagen oder Hookfehler durch --no-verify umgehen. Der Hooklauf selbst ist eine Aktion, die mit der gewünschten Gitoperation verbunden und dafür freigegeben sein muss.

## CI

CI sollte die gleichen überprüfbaren Projektaufgaben auf einem sauberen Checkout aufrufen, Versionen aus Repoquellen übernehmen und Fehler propagieren. Cache ist Optimierung, nicht Quelle der Wahrheit. Changed-file-Skip nur, wenn Abhängigkeitsgraph und gemeinsame Dateien zuverlässig berücksichtigt werden; Root-, Shared- oder unklarer Scope läuft durch den vollen relevanten Check. Ein grüner Status muss dem tatsächlichen Commit und den Pflichtjobs zugeordnet sein.

Nach Setup YAML-/Tasksyntax und Trigger, Jobabhängigkeiten, Secretsverwendung, Permissions, Cache-Schlüssel und Fehlerverhalten prüfen. Keine Secrets ausgeben oder in Logs, URLs, Taskargumente oder Artefakte schreiben. Keine Providerkonfiguration oder CI-Auslösung ohne passende Freigabe.

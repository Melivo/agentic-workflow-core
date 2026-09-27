---
name: core-scm
description: Führt klar benannte Git- und Releaseoperationen nach getrennten ausdrücklichen Autorisierungen aus. Verwenden für inspect, commit, branch, worktree, merge, rebase, push, tag oder release; nicht für Produktimplementierung, Deployment oder implizite Veröffentlichung.
---

# Core SCM

`core-scm` ist ein unterstützender Skill nach einer fachlich abgeschlossenen Änderung. Er ist kein alternativer Implementierungsworkflow, verändert keinen bestätigten Plan und startet keine Subagenten. Ohne passende ausdrückliche Autorisierung bleibt jede Operation bei `inspect` und damit read-only.

## Eingaben und verbindliche Verträge

Benötigt werden Repositorywurzel, gewünschte Operation, betroffene Pfade oder Refs, Ziel-Remote beziehungsweise Releaseziel sowie bekannte Checks und Einschränkungen. Lade:

- den [Workflowvertrag](../core-shared/references/workflow-contract.md) für Scope, Autorisierung und Blockade,
- den [Verifikationsvertrag](../core-shared/references/verification.md) für aktuelle Evidenz und verbotene implizite Wirkungen,
- das [Toolrouting](../core-shared/references/tool-routing.md) für Repositoryanalyse und sichtbare Fallbacks.

Prüfe den aktuellen Repository-, Branch-, Upstream-, Index- und Worktree-Zustand read-only, bevor eine autorisierte Mutation beginnt. Schütze fremde Änderungen, unversionierte Dateien und Secrets; Toolverfügbarkeit oder ein früherer erfolgreicher Review erweitert keine Autorisierung.

## Getrennte Autorisierungen

Erstelle vor jeder Mutation eine Operationsliste und ordne jede Wirkung genau einer aktuellen ausdrücklichen Benutzerautorisierung zu. Eine kombinierte Anweisung darf mehrere Wirkungen nur dann freigeben, wenn sie diese eindeutig benennt.

| Operation | Ohne eigene Autorisierung | Eng erlaubte Wirkung | Autorisiert niemals implizit |
|---|---|---|---|
| `inspect` | erlaubt, read-only | Status, Diffs, Historie, Refs, Upstream und Releaseautomation lesen | jede Mutation |
| `commit` | blockiert | überprüfte Pfade explizit stagen und lokalen Commit erzeugen | Push, Tag, Release |
| `branch` | blockiert | genau benannte Branchoperation | Commit, Merge, Rebase, Push |
| `worktree` | blockiert | genau benannten Worktree anlegen oder ändern | Entfernen, Bereinigen oder andere destruktive Wirkung |
| `merge` | blockiert | benannte Quellen in das benannte Ziel integrieren | Push, Tag, Release |
| `rebase` | blockiert | benannten Ref auf benannte Basis umschreiben | Force-Push oder fremde Refs ändern |
| `push` | blockiert | benannten Ref zum benannten Remote übertragen | Tags, Release, Force-Push |
| `tag` | blockiert | genau benannten Tag lokal erzeugen oder bearbeiten | Tag-Push oder Release |
| `release` | blockiert | Release für einen vorhandenen, benannten Tag erstellen | Tag-Erzeugung, Commit, Push, Deployment |

`commit`, `push`, `tag` und `release` benötigen **jeweils eine separate ausdrückliche Autorisierung** und werden niemals aus einer anderen Operation abgeleitet. Eine Releaseautorisierung gilt nicht als Tagautorisierung; eine Tagautorisierung gilt nicht als Pushautorisierung. Allgemeine Zustimmung, Schweigen, ein Paketdefault oder „fertig“ genügen nicht.

Force-Push, History-Rewrite außerhalb des benannten Rebase, Branch- oder Worktree-Löschung, Reset, Clean, Restore mit Datenverlust, Hook-Umgehung und andere destruktive Aktionen benötigen zusätzlich eine genau benannte Autorisierung. Gibt es Konflikte, ungeklärte fremde Änderungen, Secrets, unklare Ziel-Refs oder verletzte Schutzregeln, stoppe vor der Mutation mit `blocked`.

## Ablauf

### 1. Operation und Scope feststellen

1. Klassifiziere den Auftrag als `inspect | commit | branch | worktree | merge | rebase | push | tag | release`.
2. Zerlege kombinierte Aufträge in einzelne Wirkungen und halte pro Wirkung Autorisierung, Ziel und Ausschlüsse fest.
3. Frage nur nach einer materiell fehlenden Autorisierung oder Zielentscheidung; führe unabhängiges `inspect` weiter aus.
4. Leite weder Veröffentlichung noch Bereinigung aus dem Wunsch nach Abschluss ab.

### 2. Zustand und Risiken prüfen

1. Prüfe Status, Index, Diffs, Branch, Upstream, Divergenz, Konflikte und relevante Historie read-only.
2. Prüfe bei Commit jeden aufzunehmenden Pfad und stage nur explizite Pfade; verwende kein pauschales Staging.
3. Prüfe vor Push Ziel-Remote, Quell- und Ziel-Ref, Ahead/Behind und Branchschutz. Ein normaler Push darf nicht stillschweigend zu einem Force-Push werden.
4. Prüfe vor Tag oder Release Version, vorhandene Tags, Releaseautomation, Artefaktanforderungen und asynchrone Checks. Wähle bei fehlender Versionsentscheidung keine Version als Default.
5. Führe Builds, Compile, Bundle, Package, Installation, Deployment oder destruktive Vorbereitung nur aus, wenn sie separat autorisiert sind; sonst kennzeichne sie als `blocked`.

### 3. Genau die autorisierte Operation ausführen

Führe die kleinste Operation mit expliziten Pfaden, Refs und Zielen aus. Umgehe keine Hooks oder Schutzregeln. Verändere bei Konflikten nicht eigenmächtig die fachliche Lösung. Ein Fehlschlag erweitert weder Scope noch Autorisierung; sichere Wiederherstellung darf keine fremden Änderungen überschreiben.

### 4. Wirkung verifizieren

Lies Zustand, Diff, Refs und Remote- beziehungsweise Releaseergebnis erneut. Prüfe, dass nur autorisierte Pfade und Refs betroffen sind. Melde asynchrone Veröffentlichung als ausstehend, solange der Provider keinen terminalen Erfolg bestätigt. Ein lokaler Exitcode allein beweist keinen erfolgreichen Push, Tag oder Release.

## Ergebnisse

Berichte gewählte Operationen, zugeordnete Autorisierungen, betroffene Pfade und Refs, ausgeführte Checks, tatsächliche Wirkungen, Konflikte und Restrisiken.

- **completed:** Jede ausgeführte Wirkung war separat autorisiert und aktuell verifiziert.
- **partial:** Autorisierte Teilwirkungen sind belegt, weitere benannte Wirkungen fehlen oder sind ausstehend.
- **blocked:** Autorisierung, Ziel, Schutzregel, Check oder sichere Umgebung fehlt.
- **failed:** Eine autorisierte Operation schlug fehl; nenne Teilwirkung und sicheren nächsten Schritt.

Behaupte keinen Commit, Push, Tag oder Release, der nicht am aktuellen Repository- beziehungsweise Providerzustand beobachtet wurde.

---
name: core-scm
description: Führt klar benannte Git-, Veröffentlichungs- und Releaseoperationen nach getrennten ausdrücklichen Autorisierungen aus. Verwenden für inspect, commit, branch, worktree, merge, rebase, push, tag oder release sowie das sichere Erkennen und Verifizieren von Releaseautomation; nicht für Produktimplementierung, Deployment oder implizite Veröffentlichung.
---

# Core SCM

`core-scm` ist ein unterstützender Skill nach einer fachlich abgeschlossenen Änderung. Er ist kein alternativer Implementierungsworkflow, verändert keinen bestätigten Plan und startet keine Subagenten. Ohne passende ausdrückliche Autorisierung bleibt jede Operation bei `inspect` und damit read-only.

## Eingaben und verbindliche Verträge

Benötigt werden Repositorywurzel, gewünschte Operation, betroffene Pfade oder Refs, Ziel-Remote beziehungsweise Releaseziel sowie bekannte Checks und Einschränkungen. Für Tag oder Release benötigst du zusätzlich die ausdrücklich gewählte Version, das Tagmuster und gegebenenfalls die zu synchronisierenden Versionsdateien. Lade:

- den [Workflowvertrag](../core-shared/references/workflow-contract.md) für Scope, Autorisierung und Blockade,
- den [Verifikationsvertrag](../core-shared/references/verification.md) für aktuelle Evidenz und verbotene implizite Wirkungen,
- das [Toolrouting](../core-shared/references/tool-routing.md) für Repositoryanalyse und sichtbare Fallbacks.

Prüfe den aktuellen Repository-, Branch-, Upstream-, Index- und Worktree-Zustand read-only, bevor eine autorisierte Mutation beginnt. Schütze fremde Änderungen, unversionierte Dateien und Secrets. Toolverfügbarkeit oder ein früherer erfolgreicher Review erweitert keine Autorisierung.

## Getrennte Autorisierungen

Erstelle vor jeder Mutation eine Operationsliste und ordne jede Wirkung genau einer aktuellen ausdrücklichen Benutzerautorisierung zu. Eine kombinierte Anweisung darf mehrere Wirkungen nur dann freigeben, wenn sie diese eindeutig benennt. Kläre den Ausdruck „veröffentlichen“ zu `push`, `tag` und/oder `release`, sofern der Auftrag das Ziel nicht eindeutig benennt.

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

1. Ermittle mindestens Branch, Upstream, Ahead/Behind, unversionierte und gestagte Änderungen, Konfliktmarker und die relevante Historie. Bei Git CLI sind `git status --short --branch`, `git diff --stat`, `git diff --cached --stat` und `git log --oneline -10` die minimale Beobachtung.
2. Aktualisiere Tags und Remote-Refs nur, wenn Netzwerk und Berechtigung verfügbar sind, zum Beispiel mit `git fetch --tags --prune`; ein Fehlschlag bleibt als Evidenzlücke sichtbar.
3. Prüfe bei Commit jeden aufzunehmenden Pfad und stage nur explizite Pathspecs. Nimm alle nicht ignorierten Änderungen nur bei einer ausdrücklichen Anweisung dazu auf; stoppe bei Secrets, unerwarteten generierten Dateien oder Konflikten. Bilde logisch getrennte Änderungen getrennt ab und verwende ansonsten die vorhandene Commit-Konvention.
4. Prüfe vor Push Ziel-Remote, Quell- und Ziel-Ref, Ahead/Behind und Branchschutz. Ein normaler Push darf nicht stillschweigend zu einem Force-Push werden.
5. Prüfe vor Tag oder Release Version, vorhandene Tags, Releaseautomation, Artefaktanforderungen und asynchrone Checks. Wähle bei fehlender Versionsentscheidung keine Version als Default.
6. Führe Builds, Compile, Bundle, Package, Installation, Deployment oder destruktive Vorbereitung nur aus, wenn sie separat autorisiert sind; sonst kennzeichne sie als `blocked`.

### 3. Commit und Push ausführen

1. Führe vor einem Commit die kleinste praktische, aktuell autorisierte Prüfung aus. Bevorzuge den dokumentierten schnellen Projektcheck oder vorhandene Sammelgates wie `release-check`, `ci`, `check` oder `test`. Teure oder zugriffspflichtige Checks bleiben mit Grund offen.
2. Lies den gestagten Diff unmittelbar vor jedem Commit. Verwende weder `git add .` noch `git add -A`, umgehe keine Hooks und füge keine Agenten- oder Tool-`Co-Authored-By`-Trailer hinzu.
3. Prüfe nach dem Commit Status und die letzten Commits. Neue oder veränderte Dateien während der Verifikation werden erneut geprüft, niemals stillschweigend aufgenommen.
4. Push nur zum explizit autorisierten Remote und Ref. Bei Authentifizierungsfehler bleibt der lokale Commit erhalten; berichte den Fehler und stoppe. Verifiziere anschließend den synchronen Branchstatus und die noch nicht übertragenen Commits.

### 4. Releaseautomation und Tag behandeln

1. Suche vor einer Releaseentscheidung nach taggetriebener Automation in `.github/workflows`, `.gitea/workflows`, `.forgejo/workflows`, `.gitlab-ci.yml`, Release-Skripten, Paket-Skripten und Release-Dokumentation. Ermittle daraus Tagmuster und erforderliche Versionsdateien.
2. Wenn keine Releaseautomation existiert, erfinde weder Tag noch Release. Ein autorisierter Branch-Push kann dennoch abgeschlossen sein.
3. Wenn Version und Tag übereinstimmen müssen, ändere die notwendigen Versionsdateien, aktualisiere erforderliche Lockfiles, prüfe die Änderung, committe und pushe sie **vor** dem Tag. Jeder dieser Schritte benötigt seine eigene passende Autorisierung.
4. Erzeuge nur einen ausdrücklich autorisierten annotierten Tag im ermittelten Muster und pushe nur diesen Tag zum autorisierten Remote. Ein Tag ersetzt weder Branch-Push noch Provider-Release.

### 5. Wirkung verifizieren

1. Lies Status, Diff, Refs und Remote- beziehungsweise Releaseergebnis erneut. Prüfe, dass nur autorisierte Pfade und Refs betroffen sind.
2. Bestätige einen übertragenen Tag über den Remote, zum Beispiel mit `git ls-remote --tags <remote> <tag>`, oder über die Plattform-API.
3. Prüfe, soweit verfügbar, den ausgelösten Workflow oder Release-Status. Asynchrone Automation ist nur „ausgelöst“, bis der Provider den terminalen Erfolg bestätigt; behaupte ohne diesen Nachweis keine veröffentlichten Artefakte.

## Ergebnisse

Berichte gewählte Operationen, zugeordnete Autorisierungen, betroffene Pfade und Refs, ausgeführte Checks, erkannte Releaseautomation, tatsächliche Wirkungen, Konflikte und Restrisiken.

- **completed:** Jede ausgeführte Wirkung war separat autorisiert und aktuell verifiziert.
- **partial:** Autorisierte Teilwirkungen sind belegt, weitere benannte Wirkungen fehlen oder sind ausstehend.
- **blocked:** Autorisierung, Ziel, Schutzregel, Check oder sichere Umgebung fehlt.
- **failed:** Eine autorisierte Operation schlug fehl; nenne Teilwirkung und sicheren nächsten Schritt.

Behaupte keinen Commit, Push, Tag, Release oder veröffentlichtes Artefakt, das nicht am aktuellen Repository- beziehungsweise Providerzustand beobachtet wurde.

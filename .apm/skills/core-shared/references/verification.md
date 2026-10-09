# Verifikationsvertrag

Verifikation belegt beobachtbares Verhalten auf dem aktuellen Stand. Exitcode, Markdownbericht oder Agentenselbstauskunft allein beweisen keine Erfüllung.

## Pflichtcheckvertrag

Jedes Akzeptanzkriterium eines `plan/v1` wird von mindestens einem Check gedeckt. Ein ausführbarer Check nennt eindeutige ID, abgedeckte Kriterien, exaktes `command`-Array, projektrelatives `cwd` und die erwartete fachliche Beobachtung. Ausgeführt wird der gepinnte Check unverändert und seriell pro Run.

Aktuelle Evidenz umfasst:

- ausgeführtes Kommando und Arbeitsverzeichnis,
- Exitcode oder dokumentierten Blockierungsgrund,
- kurze relevante Ausgabe oder reproduzierbare Beobachtung,
- betroffene Kriterien und Artefaktpfade,
- Stand, auf dem die Prüfung lief,
- bekannte Einschränkungen.

Ein alternativer Befehl, ein anderes Arbeitsverzeichnis oder eine ältere Ausführung ersetzt keinen gepinnten Pflichtcheck.

## Autorisierungsgrenzen

Build, Compile, Bundle, Package, Installation, Commit, Push, Tag, Release, Deployment sowie produktive oder destruktive Infrastruktur- und Datenbankaktionen werden nur bei passender ausdrücklicher Autorisierung ausgeführt. Preview, Dry-run oder Scratch-Installation gelten weiterhin als Installation beziehungsweise paketbezogene Prüfung, wenn der bestätigte Plan sie so begrenzt.

Fehlt die Autorisierung, bleibt die Prüfung `blocked`; sie wird weder ausgelassen noch durch eine schwächere Prüfung als bestanden dargestellt. Paketdefaults erweitern keine Freigabe.

## Ergebniszuordnung

- `pass`: Der exakte Check lief auf aktuellem Stand erfolgreich und die erwartete fachliche Beobachtung liegt vor.
- `fail`: Der Check lief, aber Exitcode oder fachliche Beobachtung verfehlt die Erwartung.
- `blocked`: Der Check konnte wegen fehlender Autorisierung, Eingabe, Fähigkeit oder sicherer Umgebung nicht ausgeführt werden.

Ein Task ist `completed`, wenn alle Kriterien und Pflichtchecks aktuell belegt sind. Fehlende oder blockierte Pflichtcheckevidenz führt zu `partial` oder `blocked`; ein Ausführungsfehler führt zu `failed`, sofern kein engerer Blockierungsgrund gilt.

## Reihenfolge bei Änderungen

1. Vor einer Mutation Impact, Verträge und Scope prüfen. Bei Etappenarbeit die exakt bestätigten Ziel-, Index- und Definitionspfade sowie ihre Referenzen einbeziehen.
2. Die kleinste autorisierte Änderung ausführen.
3. Post-edit Change Detection durchführen und tatsächliche Pfade gegen `scope` prüfen.
4. Betroffene Guards, Tests und Contracts auf dem neuen Stand ausführen.
5. Nach jeder Korrektur alle betroffenen Checks und die Reviewprüfung wiederholen.
6. Evidenz nur wiederverwenden, wenn Eingaben, Abhängigkeiten und Repositorystand unverändert sind. Ein Task-Retry erzeugt einen neuen unveränderlichen Versuchspfad; Resume oder Review-Reparatur erzeugt dagegen keinen neuen Run und übernimmt keine ältere Taskevidenz ungeprüft. Bei Etappenabschluss deckt aktuelles Review-pass nur Plan/Run ab; `core-milestone` prüft zusätzlich die gepinnte Definition, bevor es deren Abschluss im Index verknüpft. Folgeetappen benötigen ausdrückliche Freigabe, Gesamtabschluss eigene Zielkriterien und Nachweise.

Tests, Hooks oder Validierungen dürfen nicht deaktiviert, übersprungen oder abgeschwächt werden, um einen Lauf grün erscheinen zu lassen.

## Unabhängiges Review

`core-review` startet in frischem Kontext, implementiert keine Fixes und liest den bestätigten Plan, aktuellen Gesamtdiff, das kompakte Handoff, aktuelle Task- und Checkevidenz sowie Einschränkungen. Es urteilt:

- `pass`, wenn Scope, Kriterien und relevante Risiken mit aktueller Evidenz erfüllt sind;
- `changes_requested`, wenn innerhalb des bestätigten Scopes behebbarer Änderungsbedarf besteht;
- `blocked`, wenn ein belastbares Urteil oder eine erforderliche Behebung durch eine materielle Lücke verhindert wird.

Findings verwenden `review/v1` und die Schweregrade `blocking | high | medium | low`. Eine materielle Änderung von Ziel, Scope, Architektur oder Akzeptanz geht zu `core-plan`; sie wird nicht als normale Reparatur eingeordnet. Nach höchstens zwei automatischen `execute ↔ review`-Korrekturrunden stoppt der Lauf mit sichtbaren verbleibenden Findings.

## Blockierte Paketfreigabeprüfungen

`apm compile --validate`, APM-Preview, `apm install --dry-run` und Scratch-Installationen gehören nur dann zu einem aktuell ausführbaren Pflichtcheck, wenn der bestätigte Plan und die Benutzerautorisierung dies erlauben. Andernfalls werden sie mit Grund als `blocked` dokumentiert und nicht ausgeführt.

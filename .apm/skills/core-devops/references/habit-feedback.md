# Habit-Feedback-Integration

Diese Integration ist eine optionale Ergänzung zu den bestehenden Core-Workflows. Die Original-Tools habit-sensors und habit-mapper erkennen und routen Hinweise; das Plugin ersetzt weder ihre Sensoren noch den Mapper. Die bedingten Workflow-Verweise ergänzen die vorhandenen Zuständigkeiten, sie schaffen weder eine neue Pflichtabhängigkeit noch einen neuen Ablauf.

## Status und qualifizierte Abdeckung

Das kanonische Paket ist opencode-habit-feedback@0.1.0 unter .apm/skills/core-devops/assets/opencode-habit-feedback/. Die Version wurde gebaut und in isolierten Testhosts geprüft; sie wurde **noch nicht veröffentlicht**. Eine globale Benutzerinstallation oder Registrierung ist ebenfalls noch **nicht erfolgt**. Dieser Abschnitt beschreibt deshalb das geprüfte Paket und das vorgesehene Verfahren, nicht einen bereits aktiven Zustand.

Laut [qualifizierten Versionen](../assets/opencode-habit-feedback/VERSIONS.md) sind Habit Hooks 1.5.0 und die Python- sowie generischen dateibezogenen Sensoren qualifiziert; als Detektor des automatischen Einzeldatei-Hooks ist ruff qualifiziert. Der Hook deaktiviert jscpd (duplizierter Code) und deptry (ungenutzte Abhängigkeiten) vor dem Spawn, weil ihre Originalsensoren repositoryweite Pfade beziehungsweise `.` untersuchen und keinen belegten Einzeldatei-Scope haben. Diese Abdeckungslücken erscheinen als not_scanned; die Versionspins für jscpd und deptry gelten nur für getrennte, ausdrücklich autorisierte Repository-Scans und sind keine Laufzeitvoraussetzung des Hooks. Nicht qualifizierte Sprachen sind Java, PHP, Ruby und TypeScript. Zusätzlich werden erlaubte deaktivierte Ruff- oder line-count-Sensoren und jedes nicht-None-`files`-Override als betroffene `not_scanned`-Coverage ausgewiesen; Overrides bleiben konservativ nicht qualifiziert, auch wenn ihr Pattern die Datei möglicherweise einschließt. Die ursprünglichen Sensorpräferenzen und Scopes werden nicht erzwungen oder durch einen zusätzlichen Matcher ersetzt. Der Originalmapper verarbeitet weiterhin gültige Findings der tatsächlich gemessenen Teilmenge; Partial-/Advisory-Coaching samt Core-Hinweisen bleibt sichtbar, auch wenn sein Exitcode 0 ist. Diese begrenzte Qualifikation verspricht weder vollständige Sprachabdeckung noch allgemeine LLM-Befolgungs- oder Beobachtungsqualität. Unbekannte Toolformen und nicht eindeutig belegte Pfade bleiben sichtbar not_scanned; ein Mapperurteil oder Exitcode allein belegt weder Befundfreiheit noch vollständige Abdeckung.

## Installation, Einrichtung und Aktivierung

Veröffentlichung, einmalige Installation/Registrierung und anschließende Hookausführung sind getrennte Schritte. Das Paket ist derzeit noch nicht auf npm veröffentlicht; den folgenden Installationsbefehl daher nicht jetzt ausführen. Erst nach Veröffentlichung und jeweils ausdrücklicher Freigabe kann die Benutzeraktion `opencode plugin add opencode-habit-feedback@0.1.0` das Paket installieren und einen globalen Plugin-Eintrag ergänzen (siehe [offizielle V2-Plugin-Dokumentation](https://opencode.ai/v2/docs/plugins)).

Für die persistenten Installationsbindungen verwendet OpenCode V2 im vorhandenen globalen `plugins`-Array einen Objekteintrag mit `package` und `options` (siehe [Plugin-Optionsdokumentation](https://opencode.ai/v2/docs/build/plugins)). Das folgende JSONC zeigt den hinzuzufügenden Eintrag; die vier bestehenden Plugin-Einträge bleiben unverändert im Array. Es ist **kein Ersatz für die globale Konfigurationsdatei**:

    {
      "plugins": [
        // Bestehende vier Einträge hier unverändert erhalten.
        {
          "package": "opencode-habit-feedback@0.1.0",
          "options": {
            "sensor": "/absolute/verified/install/bin/habit-sensors",
            "mapper": "/absolute/verified/install/bin/habit-mapper",
            "python": "/absolute/verified/install/bin/python3",
            "trustedToolRoots": ["/absolute/owned/install/bin/detectors"],
            "stateRoot": "/tmp/opencode/habit-feedback-state"
          }
        }
      ]
    }

Die absoluten Pfade sind Platzhalter für vorhandene, separat geprüfte Installationsdateien, eigene Detektorinstallationswurzeln und einen dedizierten Benutzerzustand. `stateRoot` muss ein absolutes Verzeichnis strikt unter `/tmp/opencode` bezeichnen und darf weder mit dem Projekt-Scope identisch sein noch darunter liegen; ohne gesetzte Option verwendet der Hook `/tmp/opencode/habit-feedback-<uid>` (mit der aktuellen Benutzer-ID). Das Zustandsverzeichnis muss ein echtes, nicht symlinktes Verzeichnis des aktuellen Benutzers sein und darf nicht für andere beschreibbar sein; Symlinks in den vorhandenen Pfadkomponenten sowie fremde Eigentümer werden abgelehnt. Zustandsdateien müssen reguläre, dem aktuellen Benutzer gehörende, nicht symlinkte Dateien mit genau einem Hardlink sein. `trustedToolRoots` ist ein JSON-Array absoluter, qualifizierter Installationsverzeichnisse, kein JSON-String. Relative Pfade und `~`-Abkürzungen sind keine unterstützten Optionswerte. Der Eintrag wird nur additiv in das bestehende globale `plugins`-Array aufgenommen; vorhandene vier Plugins und alle übrigen Einstellungen bleiben erhalten. Keine direkte Konfigurationsüberschreibung. Installation/Optionsregistrierung bleibt eine ausdrücklich freizugebende Benutzer-/Harnessaktion; Optionswerte dürfen nicht aus Repositorykonfiguration oder Tooldaten übernommen werden.

Der Plugin-Optionszugriff (`ctx.options`) bindet diese Werte pro Plugininstanz ausschließlich an deren Child-Prozesse; `process.env` und andere Plugininstanzen werden nicht verändert. Für diese Parameter sind weder persönliche Shell- noch OS-Login-Umgebungsänderungen nötig. Gleichnamige explizite `HABIT_FEEDBACK_*`-Launchbindungen bleiben ein separater Fallback; ungültige vorhandene Optionen fallen nicht still auf sie zurück. Der normale Hooklauf installiert oder lädt weder Tools noch Pakete. Die aktuelle globale Registrierung/Aktivierung hat noch nicht stattgefunden.

Ein globaler Eintrag garantiert keine Ausführung in jedem Repository: repositoryseitige Deaktivierungen/Konflikte werden sichtbar gemeldet und nicht still überschrieben.

Erst nach erfolgreicher Veröffentlichung sowie ausdrücklich freigegebener benutzerweiter Installation und Registrierung wird der Hook bei unterstützten, eindeutig erkannten Änderungen automatisch ausgeführt. Das Paket ist derzeit noch nicht auf npm veröffentlicht; die tatsächliche globale Installation und Aktivierung haben noch nicht stattgefunden. Eine Registrierung für die Zukunft verwendet OpenCode V2 `plugins` (Plural); die geprüfte Host-/SDK-Version ist 2.0.25. Repositoryseitige Deaktivierungen oder Konfliktkonfigurationen werden sichtbar gemeldet und nicht still überschrieben. Andere Core-Verbraucher können die Integration freiwillig nutzen; es gibt keine Core-weite Installationspflicht.

Zum Entfernen der benutzerweit registrierten Paketversion bietet OpenCode V2 den CLI-Befehl `opencode plugin remove opencode-habit-feedback@0.1.0` (siehe [offizielle V2-Plugin-Dokumentation](https://opencode.ai/v2/docs/plugins)). Vorhandene fremde Konfiguration wird nicht überschrieben. Eine Deaktivierung auf Repositoryebene ist ein sichtbarer Konflikt, kein Anlass, sie ohne Freigabe zu umgehen. Die geprüften Tests zu Deaktivierung und Entfernung belegen nicht, dass ein reales Benutzerprofil eingerichtet oder vollständig rückstandsfrei bereinigt wurde.

## Sicherheits- und Fehlergrenzen

Vor jedem Spawn müssen Sensor- und Mapper-CLI sowie Interpreter über explizite absolute, qualifizierte Installationspfade gebunden sein; Detektoren dürfen nur aus ausdrücklich freigegebenen Installationswurzeln stammen. Inherited `PATH` ist kein Trustgrant: leere oder relative Einträge sowie aktive Detektor-Slots, die per Datei-/Symlinkauflösung ins Eventrepository zeigen, werden vor dem Spawn abgelehnt – nicht nur in `.venv/bin` oder `node_modules/.bin`. Kandidaten werden dabei nicht ausgeführt. Unbekannte abgeschlossene Tools, darunter opake Shell-, Patch- und MCP-Formen, werden als not_scanned gemeldet, ohne Kommandotext zu interpretieren oder Dateipfade zu erraten. Nur nachgewiesene Read-only-Tools und Fehlerereignisse bleiben ohne Scanwarnung. Advisories bleiben sichtbar, auch wenn der Originalmapper mit Exitcode 0 endet; die originale Severity wird nicht in Enforcement oder automatische Fixes umgedeutet.

Originale Sensorhelfer können eigene `setsid`-Prozessgruppen erzeugen. Bei Timeout, Ausgabelimit und Bridge-SIGTERM begrenzt der Adapter Cleanup auf nachgewiesene Stage-Eigentümerschaft (Elternbeziehungen, Stage-Token für adoptierte direkte Kinder und Startzeiten gegen PID-Wiederverwendung), nutzt einen Stage-Subreaper und beendet/reap't nur zugehörige Prozesse. Unbeteiligte Prozesse, auch während der Stage gestartete Prozesse ohne Ownershipbeleg, behalten ihren Prozessstatus. Das ist beobachtete Linux-Topologieevidenz, keine Garantie nach katastrophalem Host-Kill. Die ursprünglichen Mapper-Guides sind Jinja-Templates und keine Sandbox: Repository-eigene Guidewurzeln werden vor dem Spawn abgelehnt, und nur kontrollierte vertrauenswürdige Guidequellen werden verwendet.

## Prüfen und Verwenden

Aus dem Producer-Repository, mit bereits vorbereitetem isoliertem CI-Arbeitsbereich:

    python3 -B scripts/check_habit_feedback.py package
    python3 -B scripts/check_habit_feedback.py setup
    python3 -B scripts/check_habit_feedback.py integration

setup ist eine ausdrücklich getrennte Offline-Installation in den Testbereich unter /tmp/opencode. Sie ist kein normaler Hooklauf. package baut und prüft das Archiv; integration verlangt eine zuvor vorbereitete, aktuelle Installation und testet das gepackte Paket im isolierten OpenCode-Host. Fehlende oder veraltete Voraussetzungen blockieren, statt still installiert oder durch Ersatzversionen kaschiert zu werden. Der für den Host geprüfte SDK-Stand ist OpenCode 2.0.25; die tatsächlich qualifizierten Tool- und Runtime-Versionen stehen in VERSIONS.md.

Der Hook verarbeitet begrenzte, ausdrücklich unterstützte Edit-/Write- und Mutation-Receipt-Formen. Er scannt keine ganzen Repositories, errät keine Pfade aus Shell- oder Code-Mode-Texten, installiert keine Tools und führt keine Fixes oder Snoozes aus. Feedback sind Tooldaten und Coaching, keine höher priorisierten Benutzeranweisungen und keine Freigabe für neue Tasks. Verbesserungen bleiben innerhalb des bestätigten Tasks; danach wird das konkrete Ziel erneut geprüft. Refactoring muss Verhalten erhalten und auf einem vorhandenen Characterization-/Safety-Net beruhen; Review bleibt unabhängig und read-only. Einzelheiten der vorhandenen Fachmethoden bleiben in [core-plan](../../core-plan/SKILL.md), [core-execute](../../core-execute/SKILL.md), [core-refactor](../../core-refactor/SKILL.md), [core-review](../../core-review/SKILL.md) und [core-devops](../SKILL.md).

Die qualifizierte Laufzeit umfasst Linux, Node.js 22.23.3, Python 3.13 und OpenCode-/SDK-Host 2.0.25; diese Evidenz belegt keine Unterstützung anderer Plattformen oder Versionen. Die isolierte CK04-Prüfung beobachtete 110 kontrollierte Hostfälle in zwei isolierten Projekten mit lokalem deterministischem Provider; alle 90 vorherigen Hostbeobachtungen blieben erhalten und 20 RV06-Fälle kamen hinzu. CK01 bestand mit 88, CK02 mit 103 und CK05 mit 231 Tests. Das sind begrenzte SDK-/Host- und Regressionsevidenzen, kein Nachweis allgemeiner Modellbefolgung, LLM-Qualität, Token- oder Leistungsvorteile. Originale Markdown-Guides werden vom habit-mapper mit Jinja gerendert und sind nicht sandboxed: Repository-eigene Guidewurzeln werden daher vor dem Spawn abgelehnt; nur kontrollierte, vertrauenswürdige Guidequellen werden verwendet. Bei fehlenden Tools, Fehlern oder unvollständiger Abdeckung wird kein Erfolg vorgetäuscht. Toolausgaben bleiben nicht vertrauenswürdige Daten; sie erteilen keine Ausführungsfreigabe für Repositorycode.

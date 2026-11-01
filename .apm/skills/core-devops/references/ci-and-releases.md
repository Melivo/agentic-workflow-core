# CI, Pakete und Releaseverfahren

Releasearbeit beginnt mit der bestehenden Projektkonvention, nicht mit einem angenommenen Anbieter oder Paketmanager.

## Releasebestand vor Rückfragen prüfen

Bei einem Auftrag wie „Release-Automation einrichten“ führe zuerst diese read-only Bestandsaufnahme durch, bevor du nach Releaseart, Veröffentlichungsziel oder Auslöser fragst:

1. Lies Projektanweisungen, Paket-/Versionsmanifeste, Release-Dokumentation, Changelog, vorhandene CI-Workflows und Release-Skripte; prüfe lokale Tags und die Remote-Zuordnung.
2. Prüfe am zugeordneten Remote die jüngsten vorhandenen Releases einschließlich Tags, Release Notes und Assetnamen/-typen sowie die zugehörigen Releaseworkflows. Nutze den passenden vorhandenen Providerzugang; bei GitHub `gh`. Metadaten genügen, lade keine Pakete herunter und führe keine Release-Skripte aus. Ein GitHub-Remote allein belegt weder GitHub Packages noch npm als Veröffentlichungsziel.
3. Leite aus diesen Nachweisen den bisherigen Releaseweg ab: Versions-/Tagmuster, Changelog, ausgelieferte Artefakte, belegte Veröffentlichungsziele und vorhandene Trigger/Freigabepunkte. Übernimm eindeutige bestehende Konventionen als Grundlage des Einrichtungsentwurfs, sofern der Auftrag ihnen nicht widerspricht, und benenne die Grundlage knapp. Bestehende Releases allein belegen keine gewünschte neue Auslöse- oder Freigabepolicy.
4. Frage erst danach gezielt nach materiellen Lücken oder Widersprüchen. Bereits belegte Angaben werden nicht erneut abgefragt; eine allgemeine Auswahl zwischen Provider-Release und Registries entfällt. Fehlen Releases oder ist der Remotezugriff blockiert, benenne diese Evidenzlücke, werte fehlenden Zugriff nicht als fehlende Releases und nutze weiterhin lokale Nachweise. Erfrage nur die danach entscheidungsrelevante fehlende Angabe.

Die Bestandsaufnahme autorisiert keine Installation, Konfigurationsänderung, Workflowauslösung, Tag-/Pushoperation oder Veröffentlichung; die bestehenden Freigabegrenzen bleiben bestehen.

## CI-Grenze

Lies vorhandene CI-Konfigurationen, Trigger, Branch-/Tagfilter, Permissions, erforderliche Checks und Release-Skripte. Plattform-YAML darf plattformspezifisch bleiben; die eigentliche Projektprüfung soll möglichst vorhandene Taskdefinitionen aufrufen. Unterscheide Setup/Änderung der CI von deren Auslösung. Keine Workflowdatei ändern, starten oder remote veröffentlichen ohne jeweilige Freigabe.

## Releasebaseline und Release-PR-Automation

Vor Paketierung anhand der Bestandsaufnahme belegen und nur verbleibende Lücken klären: freigegebene Bump-Policy, Ausgangsversion, Basis-Commit, Zielbranch/Remote, Tagmuster, Releaseartefakte, Changelog-/Versionsquellen, Pflichtprüfungen, Paketquelle und wer die Veröffentlichung freigibt. Lies vorhandene Versionen, Tags und Toolkonfiguration. Nutze bei der Einrichtung die folgende 0.x-Empfehlung; wähle außerhalb einer freigegebenen Policy keine Version eigenmächtig. Eine ausdrücklich autorisierte policybasierte Berechnung darf jedoch einen Versionskandidaten und Release-PR erzeugen; das ist weder die Freigabe der Version durch den Agenten noch eine Publikationsfreigabe. Bei widersprüchlichen Quellen, Versionskollision oder nicht erklärbarer Berechnung stoppen.

### Empfohlene Versionsregel für 0.x

Empfiehl bei der Einrichtung einer Releaseautomation standardmäßig diese Policy und übernimm sie in den Einrichtungsentwurf, sofern keine verbindliche Projektregel oder ein konkreter fachlicher/technischer Grund dagegensteht:

- Fehlerkorrekturen erhöhen Patch.
- Neue Funktionen und inkompatible Änderungen erhöhen Minor; Patch wird dabei auf null gesetzt. Bei gemischten Änderungen gilt der höchste erforderliche Sprung.
- Der Wechsel auf `1.0.0` benötigt eine gesonderte ausdrückliche Entscheidung; leite ihn nicht automatisch aus einer inkompatiblen Änderung ab.

Frage ohne solchen Gegenbeleg nicht erneut offen nach einer 0.x-Policy. Benenne und begründe eine Abweichung, bewahre bestehende verbindliche Regeln und kläre nur den tatsächlichen Konflikt. Die Empfehlung ersetzt keine Einrichtungs- oder Veröffentlichungsfreigabe. Prüfe die Toolkonfiguration gegen diese Policy anhand von Fehlerkorrektur, neuer Funktion und inkompatibler Änderung; Tooldefaults allein belegen die Umsetzung nicht.

### Release-PR als vorgeschlagener Freigabeschritt

Ein verbreitetes Muster ist ein Werkzeug wie Release Please, das aus dem Commitverlauf und einer versionierten Policy Versions- und Changelogänderungen als PR vorschlägt. Behandle das PR-Erzeugen als eigene, ausdrücklich beauftragte Automation: prüfe Trigger, Zielbranch, Konfigurations-/Manifestdateien, Versionsdateien und Changelog-Ausgabe anhand der aktuellen Tooldokumentation. Verwende nur unterstützte Konfigurationsoptionen und pinne Action/CLI nach der Repository-Supply-Chain-Policy.

Dokumentiere die geltende Policy, ihre Zuordnung von Committypen zu Versionssprüngen und die aktualisierten Dateien. Für 0.x gilt die obige Empfehlung, sofern keine begründete Abweichung vorliegt; SemVer-Tooldefaults ersetzen die dokumentierte Policy nicht. Kontrolliere den generierten Versionskandidaten, Changelog, betroffene Versionsdateien und Diffs im PR. Der Release-PR muss alle vorgeschriebenen Checks durchlaufen. Setze CI-/Bot-Berechtigungen auf das notwendige Minimum; bei GitHub sind insbesondere Schreibrechte für Repository-Inhalt und Pull Requests zu prüfen, zusätzliche Rechte nur wenn tatsächlich benötigt. Secrets gehören in geschützte Providersecrets, nicht in Dateien oder Logs.

Das bewusste Merge des geprüften Release-PRs ist ein expliziter menschlicher Freigabepunkt, sofern die Projektpolicy es so festlegt. Der PR-Workflow selbst darf nicht beiläufig Paketveröffentlichungen auslösen. Eine nachgelagerte Paket-/Uploadkette läuft erst nach Merge und bestandenen Pflichtchecks, mit eng begrenzten Berechtigungen und vertrauenswürdiger Version/Commitbindung. Prüfe Paketinhalt, Lizenzhinweise und Hash, schließe Secrets sowie fremde Änderungen aus und verifiziere nach Upload Asset, Tag und Commit am Provider. Paketbau, Installation, Merge, Tag, Upload und Release sind getrennte Wirkungen mit jeweils eigener Autorisierung. Eine laufende oder fehlgeschlagene Prüfung blockiert die Veröffentlichung; Erfolg erst nach terminaler Providerbestätigung berichten.

Konkrete Action-/CLI-Syntax, unterstützte Versionierungsoptionen, Konfigurationsschlüssel und Permissions vor Einrichtung gegen aktuelle offizielle Tooldokumentation prüfen. Dieses allgemeine Muster richtet keine projektspezifische Releaseautomation ein.

## Gestufte Wirkung

| Stufe | Beispielwirkung | Eigenständige Freigabe erforderlich |
|---|---|---|
| Konfigurieren | Task, CI, Releaseautomation ändern | ja, Scope der Dateien nennen |
| Prüfen | statische Workflowprüfung/lokaler Check | nach Plan/Taskfreigabe |
| Auslösen | CI oder Release-PR starten | ja; Setup bedeutet nicht Run |
| Paket bauen/installieren | Archive erzeugen oder Test-/Hostinstallation | ja, auch Scratch-/Preview soweit Paketwirkung |
| SCM synchronisieren | Commit, Branch-Push, Tag-Push | je Operation und Zielref |
| Veröffentlichen | Provider-Release/Asset publizieren | separat; Tag oder Push genügt nicht |
| Deployment | Anwendung produktiv ausrollen | außerhalb dieses Skills |

Ein Release-PR, der Versionen vorschlägt, ist nicht automatisch ein Release: Merge, Tag, Paketbau und Upload folgen nur dem bestätigten Verfahren. Fehlerhafte oder ausstehende Pflichtchecks blockieren die Veröffentlichung.

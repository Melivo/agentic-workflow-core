---
name: core-docs
description: Pflegt nachgewiesene Dokumentationsdrift nach Code-, Vertrags- oder Konfigurationsänderungen innerhalb eines bestätigten Scopes. Verwenden für veraltete Prosa, Pfade, Befehle, Konfigurationsschlüssel und Referenzen; nicht für Produktcode, unbelegte Neudokumentation oder Änderungen manueller Inhalte außerhalb des Auftrags.
---

# Core Documentation

`core-docs` ist die Fachmethode des `docs-curator`, kein öffentlicher Workflow. Der Skill bearbeitet nur Dokumentation, deren Drift durch den bestätigten Task oder einen aktuellen Diff nachgewiesen ist. Er startet keine Subagenten, erweitert keinen Scope und ändert keinen Produktcode.

## Eingaben und verbindliche Verträge

Erwarte einen bestätigten Task mit Dokumentationsscope, relevanter Änderung oder Diff, `context_paths`, Akzeptanzkriterien und gepinnten Checks. Fehlt eine konkrete Änderungsevidenz, bleibt die vermutete Anpassung offen; allgemeine Aufräumarbeiten werden nicht abgeleitet.

Lade bei mutierender Arbeit den [Workflowvertrag](../core-shared/references/workflow-contract.md) für Autorisierung und Scope sowie den [Verifikationsvertrag](../core-shared/references/verification.md) für Impact, Post-edit-Prüfung und aktuelle Evidenz. Nutze das [Toolrouting](../core-shared/references/tool-routing.md), wenn Repositoryevidenz oder aktuelle externe Produktdokumentation erforderlich ist. Der bestätigte Plan und Runstatus werden nicht verändert.

## Evidenz- und Scopegrenze

Eine Dokumentationsänderung ist nur zulässig, wenn alle folgenden Punkte belegt sind:

1. Eine Aussage, Referenz oder Anleitung liegt im Schreibscope des Tasks.
2. Aktueller Code, Konfiguration, Vertrag, Test, bestätigte Entscheidung oder Diff widerspricht dem dokumentierten Stand.
3. Die kleinste notwendige Korrektur lässt sich aus dieser Evidenz ableiten.
4. Betroffene manuelle Inhalte außerhalb des Scopes bleiben unverändert.

`context_paths` erlauben Lesen, nicht Schreiben. Ähnliche Formulierungen in anderen Dokumenten sind kein Beleg dafür, dass sie ebenfalls geändert werden dürfen. Unabhängige Altlasten, Stilwünsche und nicht taskbezogene defekte Referenzen werden als offene Drift gemeldet, nicht nebenbei korrigiert.

## Schutzgrenzen

- Ändere ausschließlich Dokumentationsdateien und ausdrücklich zum Dokumentationsbundle gehörende Metadaten im bestätigten Scope.
- Ändere keinen Produktcode, keine Tests, Schemas, Laufzeitkonfiguration oder generierten Programmdateien. Eine notwendige Produktkorrektur geht an den zuständigen Fachagenten.
- Bearbeite keine Secrets oder geheimnistragenden Dateien wie `.env*`, `*.pem`, `*.key` oder `id_rsa*`; zitiere deren Inhalt nicht in Evidenz oder Ergebnissen.
- Erhalte Sprache, Ton, Gliederung, Beispiele und manuelle Hinweise, soweit die nachgewiesene Drift keine Änderung verlangt.
- Formatiere, verschiebe oder restrukturiere keine unbeteiligten Abschnitte.
- Regeneriere Dokumentation nur, wenn der Task den Generator und dessen Ausgabepfade ausdrücklich umfasst; editiere generierte Dateien nicht als Ersatz für ihre Source of Truth.
- Erfinde bei widersprüchlicher oder mehrdeutiger Evidenz keine Auflösung. Melde Pfade, Konflikt und benötigte Entscheidung als `blocked` oder `partial`.
- Führe keine Builds, Compiles, Installationen, SCM-, Deployment- oder destruktiven Aktionen als Nebenwirkung aus.

## Workflow

### 1. Auftrag und Ausgangszustand festhalten

Lade den exakten Task, seine Akzeptanzkriterien, den erlaubten Schreibscope und die benannten Kontextpfade. Erfasse vor Änderungen den aktuellen Referenz- oder Driftzustand mit dem gepinnten Dokumentationscheck. Ist ein solcher Check nicht verfügbar, dokumentiere die engste reproduzierbare statische Prüfung und die verbleibende Lücke; installiere kein Werkzeug eigenmächtig.

### 2. Drift lokalisieren und belegen

Verwende Gortex primär, um geänderte Dateien, betroffene Verträge und referenzierende Dokumentation zu lokalisieren. Ordne jede Kandidatenstelle einer konkreten Evidenz zu:

- geänderter oder entfernter Pfad,
- geänderter Befehl oder Parameter,
- geänderter Konfigurationsschlüssel oder Umgebungsvertrag,
- geändertes beobachtbares Verhalten,
- bestätigte Architektur- oder Prozessentscheidung.

Nutze Context7 nur für eine enge aktuelle Frage zu einer Bibliothek, API, CLI oder Cloud-Dokumentation. Externe Quellen belegen keine lokale Implementierung; gleiche sie mit dem Repositorystand ab.

### 3. Impact vor Mutation prüfen

Prüfe vor dem Schreiben Dokumentabhängigkeiten, Links, zentrale Begriffsverwendung, betroffene Akzeptanzkriterien und den erlaubten Scope. Verwirf Kandidaten ohne Nachweis oder außerhalb des Scopes. Wenn die korrekte Dokumentation eine Produktänderung voraussetzt, stoppe die Dokumentationsmutation und melde den zuständigen Owner.

### 4. Minimal korrigieren

Ändere nur die nachgewiesen veralteten Sätze, Tabellenzeilen, Beispiele oder Referenzen. Bewahre angrenzende manuelle Inhalte bytegenau, soweit kein notwendiger Kontextübergang betroffen ist. Verwende technische IDs, Schemanamen, Pfade, Befehle und Konfigurationsschlüssel exakt wie in der autoritativen Quelle.

### 5. Post-edit prüfen

Führe Gortex Change Detection aus und vergleiche alle tatsächlich geänderten Pfade mit dem Taskscope. Prüfe anschließend:

- die direkt geänderten Referenzen und Links,
- den gepinnten Pflichtcheck auf aktuellem Stand,
- die fachliche Aussage gegen Code, Vertrag oder Diff,
- unbeabsichtigte Änderungen manueller Inhalte,
- Format- und Strukturvalidierung des Dokumentationsbundles, sofern sie autorisiert und ohne Build möglich ist.

Ein erfolgreicher Exitcode ohne inhaltlichen Abgleich ist kein Nachweis. Bereits vorhandene, nicht taskbezogene Drift bleibt sichtbar, blockiert den Task aber nur, wenn sie die Akzeptanz im Scope verhindert.

## Ergebnis

Liefere:

- Status `completed | partial | blocked | failed`,
- geänderte Dokumentationspfade,
- je Änderung den Drift-Nachweis und die autoritative Quelle,
- ausgeführte Checks mit Kommando, Arbeitsverzeichnis, Exitcode und fachlicher Beobachtung,
- bestätigten Schutz manueller Inhalte und den Nachweis, dass kein Produktcode geändert wurde,
- übersprungene Kandidaten mit Grund,
- offene oder außerhalb des Scopes liegende Drift.

`completed` ist nur zulässig, wenn jede Änderung belegt, der tatsächliche Diff im Scope und das Akzeptanzkriterium aktuell verifiziert ist. Fehlende Evidenz oder ein blockierter Pflichtcheck führt zu `partial` beziehungsweise `blocked`; Fehler werden nicht als bereinigte Drift ausgegeben.

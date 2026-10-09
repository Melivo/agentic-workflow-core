---
name: core-handoff
description: Erstellt aus ausdrücklich benannten Workflow-Artefakten einen kopierbaren Startprompt für eine neue Sitzung, auch mitten in einem Run. Verwenden für Sitzungswechsel und Milestone-Übergaben; nicht für Planung, Ausführung, Review oder eigene Fortschrittsverwaltung.
---

# Core Handoff

Nutze diesen Skill, wenn der Benutzer eine Sitzung wechseln möchte oder eine autorisierte Milestone-Übergabe ansteht. Er erzeugt einen Einstieg aus belegbaren Dateien, keine Zusammenfassung des Gesprächs. Er besitzt weder Plan-, Milestone- noch Runstatus und startet keine Agenten oder Workflows.

## Eingaben und Grenzen

Erforderlich sind Projektwurzel, Übergabezweck und exakte Pfade der maßgeblichen Artefakte: bestätigter Plan, bei laufender Arbeit Runzustand und dessen Handoff sowie relevante Taskresultate und Review. Für ein Vorhaben mit getrennten Formaten kommen Ziel-ID/-Pfad, Indexpfad, ausgewählte Definitions-ID/Version/-Pfad und erforderliche `decision_refs` hinzu; Plan/Run sind vor erster Planung nicht anwendbar. Prüfe Namen, IDs, Pfadbeziehungen, Auswahl und Freigabe gegen Originale. Ein ausdrücklich benannter Legacy-Einstieg bleibt `milestone/v1`. Frage nach fehlenden notwendigen Pfaden; suche nicht nach vermeintlich neuesten Dateien.

Lade den [Workflowvertrag](../core-shared/references/workflow-contract.md), den [Artefaktvertrag](../core-shared/references/artifact-contract.md) und die bestehende [Run-Handoffvorlage](../core-shared/assets/handoff.md). Für Repositoryzugriff lade bedarfsgerecht das [Toolrouting](../core-shared/references/tool-routing.md). Diese Verträge bestimmen Eigentum, Driftprüfung und Wiederaufnahme. Die Run-Handoffvorlage bleibt bei `core-execute`; dieser Skill überschreibt sie nicht.

## Workflow

### 1. Übergabepunkt prüfen

Lies die genannten Artefakte und den aktuellen Repositorystand. Prüfe IDs, Pfadbeziehungen, maßgeblichen Plan und belegten Resume-Punkt. Ein Handoff ist ein Wegweiser, keine Statusquelle; Status kommt aus den jeweils zuständigen Artefakten. Aus Chatbehauptungen oder Memories darf kein fehlender Laufzustand entstehen.

Bei laufenden Mutationen oder Dispatches ist noch keine verlässliche Übergabe möglich. Melde die offene Arbeit und lasse den zuständigen Ausführungsworkflow einen sicheren Haltepunkt herstellen. `core-execute` sichert seinen Runzustand und sein aktuelles Handoff; `core-milestone` aktualisiert gegebenenfalls den Etappenindex. Übernimm diese Schreibaufgaben nicht selbst. Nicht gespeicherte Entscheidungen verhindern einen vollständigen Startprompt; lasse sie durch ihren Eigentümer und erforderliche Bestätigung sichern.

Bei einem noch unbestätigten Planentwurf ohne Datei ist nur eine eingeschränkte Übergabe möglich: verweise auf vorhandene bestätigte Zielartefakte und benenne, dass Planung erneut nötig ist. Erfinde keinen bestätigten Plan und schreibe keinen parallelen Entwurf.

### 2. Einstieg und nächsten Schritt bestimmen

- **Mit Milestones:** Lade in der neuen Sitzung zuerst [`core-milestone`](../core-milestone/SKILL.md). Dieser zeigt Gesamtziel, Etappenübersicht, aktuelle ID und den passenden Goal-Prompt. Bei laufender Etappe route anhand der Artefakte zum bestehenden Plan/Run; nach Abschluss ist die nächste Etappe bis zur ausdrücklichen Freigabe nur ein Vorschlag.
- **Ohne Milestones, bestätigter Plan/Run:** Route zu `core-execute` für ausdrücklich autorisierte Ausführung oder Resume. Bei reviewbereitem Run ist der nächste Übergang `core-review`. Nach `pass` einer gepinnten Etappe folgt die zusätzliche Kriterienprüfung durch `core-milestone`; nur dieser Eigentümer aktualisiert den Index-Abschluss. Ein Run-pass allein beendet weder Etappe noch Gesamtziel. Veraltete Indexauswahl oder Versionsbindung stoppt Resume; route Auswahlklärung zu `core-milestone`, Planabweichung zu `core-plan`. Resume/Reparaturen behalten dieselbe Run-ID. Bei vorhandenem Review gelten Urteil und Reparaturgrenzen.
- **Planungsbedarf oder materielle Drift:** Route zu `core-plan` mit den exakten bestätigten Eingaben. Plane nicht selbst und verwende keinen veralteten Plan stillschweigend weiter.
- **Alles abgeschlossen:** Gib den belegten Abschluss aus. Erzeuge keinen Startprompt mit erfundener Folgearbeit.

### 3. Startprompt ausgeben

Fülle die [Startpromptvorlage](assets/start-prompt.md) ausschließlich aus den geprüften Eingaben. Entferne nicht anwendbare optionale Zeilen und ersetze alle Platzhalter. Nenne die Projektwurzel sowie bei Etappenarbeit Ziel-ID, Milestone-ID/Version, exakte Ziel-, Index-, Definitions-, Plan- und anwendbare Run-/Review-/Tasknachweispfade, relevante Constraints und Einschränkungen. Referenziere Originalnachweise statt Plan, Runstatus oder Gesprächshistorie zu kopieren. Veraltete Start-/Goal-Prompts sind keine Autorität: bei abgelöster Version, abgeschlossenem Milestone oder fehlender Freigabe darf der Prompt keine Arbeit reaktivieren; stoppe und verweise auf den zuständigen Eigentümer. Kein Folgedispatch und keine automatische Folgefreigabe.

Gib den Prompt im Chat als kopierbaren Textblock aus, davor eine kurze Erklärung des Wiedereinstiegs auf CS50-Einstiegsniveau. Mit Milestones fordert er ausdrücklich das Laden von `core-milestone`; ohne Milestones nennt er den zuständigen vorhandenen Core-Workflow. Die neue Sitzung prüft Artefakte und Drift erneut. Der Prompt erzeugt keine neue Freigabe und aktiviert keinen Goal-Modus.

Standardmäßig entsteht keine zusätzliche Datei. Nur bei ausdrücklich bestätigtem separatem Zielpfad darf eine Kopie des Startprompts geschrieben werden; niemals über Run-Handoff, Plan oder Milestone-Artefakt. Ein veralteter Prompt wird aus aktuellen Artefakten neu erzeugt, nicht mit Chatwissen fortgeschrieben.

## Ergebnis und Wiederaufnahme

- **completed:** überprüfte Artefaktreferenzen und eindeutiger kopierbarer Einstieg, ohne eigene Zustandsverwaltung.
- **partial:** sichere Referenzen liegen vor, aber ein nicht gesicherter Entwurf oder einzelne Nachweise fehlen; markiere die Einschränkung im Prompt.
- **blocked:** notwendiger Pfad, Autorisierung, sicherer Haltepunkt oder autoritativer Zustand fehlt beziehungsweise widerspricht sich. Nenne die fehlende Eingabe und ihren Eigentümer; erzeuge keinen ausführungsfähigen Prompt auf dieser Grundlage.
- **failed:** Prüfung oder erlaubtes Schreiben fehlgeschlagen; nenne Ursache und verbleibende Dateien.

Ändere keine Produktdateien, bestätigten Pläne, Milestone-Indizes, Runzustände oder Reviews. Keine Installation, SCM-, Harness-Konfiguration oder automatischen Sitzungsstarts.

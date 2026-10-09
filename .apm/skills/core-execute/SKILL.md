---
name: core-execute
description: Führt einen ausdrücklich benannten, bestätigten plan/v1 aus, koordiniert Fachagenten, integriert Ergebnisse serialisiert und steuert höchstens zwei Review-Reparaturrunden. Verwenden für Implementierung, Ausführung oder Resume eines bestätigten Plans; nicht für Planung, unabhängiges Review oder SCM.
---

# Core Execute

`core-execute` ist der einzige öffentliche Ausführungsworkflow. Er implementiert einen bestätigten Taskgraphen, besitzt jeden Fachagenten-Dispatch und verwaltet den aktuellen Run. Er plant nicht neu, bewertet seine Gesamtänderung nicht unabhängig und führt weder SCM- noch Deploymentoperationen als Abschluss aus.

## Aktivierung und Eingaben

Aktiviere diesen Skill nur, wenn der Benutzer einen **expliziten Pfad** zu genau einem bestätigten `plan/v1` nennt und dessen Ausführung oder Resume verlangt. Suche niemals nach dem vermeintlich neuesten Plan. Fehlt der Pfad oder ist `status: Confirmed` nicht validierbar, stoppe vor jeder Produktmutation und fordere das fehlende Eingabeartefakt beziehungsweise `core-plan` an.

Lade aus frischem Kontext:

- den exakt benannten Plan,
- aktuelle Projektanweisungen und den Repositorystand,
- bei Resume `.agentic-workflow/runs/<run-id>/state.yaml`, `handoff.md`, vorhandene `task-result/v1`-Dateien und `review.yaml`.

Der Plan bleibt unverändert. Laufstatus, Retryzähler, Evidenz und Findings gehören ausschließlich in die Run-Artefakte.

## Verbindliche Verträge

Lade vor dem Start:

- den [Workflowvertrag](../core-shared/references/workflow-contract.md) für Autorisierung, Scope, Abbruch und Wiederaufnahme,
- den [Artefaktvertrag](../core-shared/references/artifact-contract.md) für `plan/v1`, Runzustand, `task-result/v1`, Handoff und `review/v1`,
- das [Toolrouting](../core-shared/references/tool-routing.md) für Gortex und erlaubte Fallbacks,
- den [Verifikationsvertrag](../core-shared/references/verification.md) für aktuelle Evidenz und autorisierungsabhängige Checks,
- den [Workflowkatalog](../core-shared/assets/workflow-catalog.yaml) für bekannte Workflow-, Agenten- und Tool-IDs sowie das Limit der Reparaturrunden.

Verwende die [Handoffvorlage](../core-shared/assets/handoff.md), wenn `core-review` oder ein Resume frischen Kontext erhält.

## Kanonischer Ablauf

### 1. Plan und Drift validieren

1. Prüfe `schema: plan/v1`, `status: Confirmed` und genau einen eingebetteten Taskgraphen. Bei gepinnter Etappenarbeit lade Ziel, Index und exakte Definitionsversion erneut; verifiziere enthaltene IDs/Pfade, Indexauswahl/-freigabe, Planbindung und deren aktuelle Gültigkeit vor Start. Ein Versions-/Auswahlwechsel oder abgelöster Plan blockiert Start und Resume; route zu `core-milestone` für Auswahlklärung und zu `core-plan` für nötigen Ersatzplan. Setze weder automatisch fort noch überschreibe den laufenden Plan. Resume und Review-Reparaturen behalten dieselbe Run-ID; legacy `milestone/v1` wird nur über den ausdrücklich benannten Pfad gelesen.
2. Validiere für jeden Task einen registrierten Fachagenten, getrennte `context_paths` und `scope`, bekannte erforderliche MCPs, einen azyklischen Abhängigkeitsgraphen sowie die vollständige Abdeckung aller Akzeptanzkriterien durch eindeutige Checks.
3. Behandle einen leeren `scope` als read-only. Ein Check mit Build-, Compile-, Bundle-, Package- oder Installationswirkung ist ohne passende ausdrückliche Autorisierung blockiert.
4. Vergleiche Planannahmen, referenzierte Pfade, vorhandenen Diff und wiederverwendete Evidenz mit dem aktuellen Repositorystand. Drift macht betroffene Evidenz ungültig.
5. Stoppe bei Drift, die Ziel, Scope, Architektur oder Akzeptanz materiell verändert, und route zu `core-plan`. Bei kompatibler Drift aktualisiere nur Runzustand und neu zu erhebende Evidenz, niemals den Plan.

### 2. Run anlegen oder Resume durchführen

Lege `.agentic-workflow/runs/<run-id>/state.yaml` mit exaktem `plan_path`, aktuellem Laufzustand, integrierten und ausführbaren Task-IDs sowie der Zahl bereits verwendeter Review-Reparaturrunden an. Halte darin weder Planinhalt noch Taskevidenz, Findings oder Eventhistorie doppelt.

Bei Resume:

1. lade alle kanonischen Run-Artefakte und den Repositorystand neu,
2. prüfe Pfade, Drift, integrierte Abhängigkeiten und Freshness jeder Evidenz,
3. verwerfe veraltete Ergebnisse,
4. leite das Ready Set erneut ausschließlich aus bereits integrierten Abhängigkeiten ab.

Ein Chatverlauf oder Provider-Memory ersetzt kein Run-Artefakt.

### 3. Tasks schedulen und dispatchen

- Reihenfolge und Parallelität folgen nur `dependencies`, nicht Prioritäten oder Dateireihenfolge.
- Übergib jeden Task genau einem registrierten Fachagenten mit Auftrag, `context_paths`, `scope`, Akzeptanzkriterien, Checks und relevanten Constraints.
- Der Fachagent darf den Scope nicht erweitern und **keinen Subagenten** starten. Jeder weitere Dispatch bleibt allein bei `core-execute`.
- Read-only-Tasks dürfen ohne Ressourcenkollision parallel laufen.
- Schreibende Tasks dürfen nur mit disjunkten Scopes, gemeinsamer Ausgangsbasis und sicherer Isolation parallel laufen; höchstens zwei gleichzeitig. Serialisiere bei Unsicherheit.
- Erforderliche MCPs blockieren den Task, wenn keine vertraglich erlaubte Alternative existiert. Optionale Provider erweitern weder Scope noch Autorisierung.

### 4. Taskresultat prüfen

Verlange pro neuem Versuch die eigene, unveränderliche Datei `.agentic-workflow/runs/<run-id>/tasks/<task-id>/attempt-<nn>.yaml` mit `schema: task-result/v1`; `nn` ist mindestens zweistellig, fortlaufend und innerhalb dieses Runs/Tasks eindeutig. Ein Retry erhält die nächste Kennung und überschreibt oder deutet keinen früheren Versuch um. Bestehende `.agentic-workflow/runs/<run-id>/tasks/<task-id>.yaml` werden ausschließlich als Legacy-Ergebnis gelesen; sie werden weder neu beschrieben noch automatisch umbenannt oder migriert. Execute persistiert Rückgaben read-only Agenten in der jeweiligen neuen Taskresultatdatei; diese Agenten erhalten dadurch keine Schreibrechte an Produkt- oder Runartefakten. Ist der Taskagent ausdrücklich für Änderungen vorgesehen, darf er als eng begrenzte Ausnahme ausschließlich seine eigene Ergebnisdatei schreiben, nicht Plan, Runstatus, Handoff oder Review. Prüfe:

- Task-ID, Versuch und Status,
- `changed_paths` gegen die tatsächlichen Änderungen und den bestätigten `scope`,
- jede Akzeptanz-ID samt beobachtbarer Evidenz,
- jeden gepinnten Check mit unverändertem Kommando, `cwd`, Exitcode und fachlicher Beobachtung,
- Einschränkungen und Blockierungsgründe.

Ein Exitcode 0 oder eine Agentenbehauptung genügt nicht. Änderungen außerhalb des Scopes oder Mutationen durch read-only-Tasks werden nicht integriert. Fehlende aktuelle Pflichtcheckevidenz ergibt `partial` oder `blocked`, nicht `completed`.

### 5. Serialisiert integrieren und verifizieren

Integriere akzeptierte Taskergebnisse einzeln in den autoritativen Checkout. Führe keine internen Task-Commits ohne ausdrückliche Commitautorisierung aus. Prüfe nach jeder Integration den tatsächlichen Gesamtdiff und führe alle betroffenen Checks auf dem integrierten Stand erneut aus. Beginne die nächste abhängige Arbeit erst, wenn die Integration und ihre Evidenz belastbar sind.

### 6. An frisches Review übergeben

Ersetze `.agentic-workflow/runs/<run-id>/handoff.md` anhand der Shared-Vorlage. Referenziere den exakten Plan, Runzustand, aktuellen Repositorystand oder Diff, Taskresultate, Prüfevidenz und Einschränkungen. Starte `core-review` in frischem Kontext; übergib weder Implementierungsdiskussion noch Chatverlauf als Source of Truth.

### 7. Review-Findings reparieren

- Bei `pass` schließe den Run ab.
- Bei `changes_requested` ordne jedes innerhalb des bestätigten Scopes liegende Finding dem passenden Fachagenten zu, repariere es unter derselben `run_id`, integriere serialisiert und wiederhole betroffene Checks sowie das frische Review.
- Bei einer materiellen Änderung von Ziel, Scope, Architektur oder Akzeptanz route zu `core-plan` statt zu reparieren.
- Bei `blocked` dokumentiere den fehlenden Eingang, die Fähigkeit oder Autorisierung und stoppe die abhängige Arbeit.
- Erlaube insgesamt höchstens **zwei** automatische `execute ↔ review`-Reparaturrunden. Nach der zweiten Runde stoppt der Lauf mit den verbleibenden Findings; eine dritte automatische Runde ist verboten.

## Debugging innerhalb der Ausführung

Ein erwartbarer Implementierungsfehler bleibt beim zuständigen Domainagenten. Bei unklarer Ursache, Regression oder intermittierendem Fehler dispatcht ausschließlich `core-execute` den `debug-investigator` und weist die Fachmethode [`core-debug`](../core-debug/SKILL.md) zu. Debugging ist kein zusätzlicher Workflow und besitzt weder Scheduling noch Integration.

## Abbruch und Ergebnis

Beginne nach einem Benutzerabbruch keine neue Mutation oder keinen neuen Dispatch. Halte beobachtete Evidenz, verbleibende Nebenwirkungen und den aktuellen Resume-Punkt fest.

Ein erfolgreicher Run-Abschluss erfordert einen aktuellen `core-review`-Verdict `pass`, eingehaltenen Scope und aktuelle Pflichtcheckevidenz. Bei gepinnter Etappe folgt danach die zusätzliche Prüfung durch `core-milestone` gegen genau die gebundene Definitionsversion; nur `core-milestone` verknüpft den Etappenabschluss und Originalnachweise im Index. Run-pass ist weder Etappenabschluss noch Gesamtzielerfolg. `core-milestone` prüft Kriterien auch außerhalb des Taskgraphen; Gesamtzielerfolg erfordert separat alle Gesamtzielkriterien und Nachweise. Kein Execute-Dispatch plant oder genehmigt automatisch eine Folgeetappe. Liefere andernfalls ehrlich `partial`, `blocked` oder `failed` mit exakten Artefaktpfaden, Ursache und nächstem zulässigem Übergang.

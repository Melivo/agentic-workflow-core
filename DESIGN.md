# Agentic Workflow Core — finales Systemdesign

**Status:** Final und verbindlich
**Geltungsbereich:** öffentliches Microsoft-APM-Paket und dessen Workflow-Werkbank
**Kanonische Paketquelle:** `.apm/`
**Kernablauf:** `core-brainstorm? → core-plan → frischer Kontext → core-execute ↔ core-review`

## 1. Zweck und Autorität

Dieses Dokument konsolidiert die Entwürfe unter `reference/source-material/design-drafts/` zu einer einzigen Architektur. Es ist für die Paketimplementierung die Source of Truth. Frühere Entwürfe und Zwischenprotokolle bleiben als Herkunftsnachweis erhalten, sind bei Widersprüchen aber nachrangig.

In diesem Repository bezeichnet `DESIGN.md` das Systemdesign der Workflow-Werkbank. Die frühere Aussage, `DESIGN.md` sei ausschließlich für visuelles Design reserviert, gilt nur für Anwendungsprojekte mit einem visuellen Designsystem und wird für dieses Meta-Repository ausdrücklich nicht angewendet.

## 2. Ziele

Das Paket soll:

- wenige klar abgegrenzte Workflows bereitstellen, die ohne Parallelarchitektur ineinandergreifen,
- Planung, Ausführung und unabhängiges Review durch frische Kontexte trennen,
- Fachagenten auf kleine, überprüfbare Aufgaben begrenzen,
- Gortex als primäre Code-Intelligence verwenden und passende Gortex-Skills bedarfsgerecht einbinden,
- Context7, YouTube Transcript und Serena nach klaren Recherchegrenzen einsetzen,
- Honcho für nützliche semantische Erinnerung verwenden, ohne daraus eine zweite Source of Truth zu machen,
- aktuelle Projektartefakte statt Gesprächshistorien als Übergabe verwenden,
- aus OMA nur fachliche Substanz übernehmen, nicht dessen Orchestrierungs-, Event- oder Digest-Komplexität,
- als ein portables APM-Paket für OpenCode und Codex veröffentlichbar bleiben.

## 3. Nicht-Ziele

Nicht Teil des Kerns sind:

- konkurrierende Ausführungsworkflows wie `work`, `orchestrate`, `ultrawork`, `ralph` oder `exec-plan`,
- ein separater öffentlicher Debug-Workflow,
- ein separater `prime`-Workflow,
- vollständige Gesprächsjournale oder Toolprotokolle,
- Eventbus, Authority-Digests, Hashketten oder Revisionssessions als normale Workflow-Gates,
- automatische Commits, Pushes, Releases, Deployments, Builds oder destruktive Aktionen,
- unkontrollierte Agentenketten oder Subagenten, die selbst weitere Agenten starten,
- Gortex, Serena, Honcho oder ein MCP als Plan-, Task- oder Reviewdatenbank,
- statische Kopien schnell veraltender externer API-Dokumentation,
- universelle Framework-, Architektur- oder Toolvorgaben für jedes Zielprojekt.

## 4. Architekturprinzipien

1. **Ein Lebenszyklus, ein Eigentümer je Phase.** Jeder Workflow besitzt genau einen Abschnitt des Lebenszyklus.
2. **Artefakte statt Chatkontext.** Frische Kontexte lesen bestätigte Dateien und aktuelle Repositoryevidenz.
3. **Abhängigkeiten statt Prioritätsstufen.** Reihenfolge und Parallelität ergeben sich ausschließlich aus dem Taskgraphen.
4. **Ein Fachagent pro Task.** Koordination bleibt beim Workflow; Agenten erweitern weder Scope noch Agentenkette.
5. **Repositoryevidenz vor generischen Defaults.** Bestehender Code, Verträge und Projektinvarianten haben Vorrang.
6. **Research nur bei materieller Wissenslücke.** Recherche endet, sobald eine Entscheidung belastbar getroffen werden kann.
7. **Freshness vor Erinnerung.** Aktueller Code und bestätigte Artefakte schlagen semantisches Memory.
8. **Verifikation ist beobachtbar.** Exitcode, Behauptung oder Agentenselbstauskunft allein reichen nicht.
9. **Parallelität ist eine Optimierung.** Bei unklarer Isolation oder Abhängigkeit wird serialisiert.
10. **Lean bedeutet keine fehlenden Grenzen.** Kleine Verträge ersetzen große Orchestratoren.

## 5. Gesamtmodell

```text
Einmal pro Umgebung:
  APM-Paket installieren → core-init-mcps? → MCPs und Memory-Adapter prüfen

Einmal pro Repository:
  core-init-project → core-repo-audit?

Pro Änderung:
  core-brainstorm? → core-plan → frischer Kontext → core-execute → frischer Kontext → core-review
                                           ↑                           │
                                           └──── strukturierte Findings┘

Nach bestandenem Review:
  Abschluss → optionaler, ausdrücklich autorisierter core-scm-Schritt
```

### Öffentliche Kernworkflows

| ID | Verantwortung | Mutiert Produktcode? | Primärer Output |
|---|---|---:|---|
| `core-brainstorm` | Absicht, Scope und Lösungsrichtung klären | nein | kompakter Decision-Handoff |
| `core-plan` | Repositoryanalyse, Research, Entscheidungen und Taskgraph | nein | bestätigter `plan/v1` |
| `core-execute` | bestätigten Taskgraph ausführen und integrieren | ja | Run-Artefakte und Review-Handoff |
| `core-review` | unabhängige Prüfung und Urteil | nein | `review/v1` mit Findings oder `pass` |

### Unterstützende Skills

- `core-init-project`: Repository-Harness, Projektinvarianten und `AGENTS.md`-Preflight
- `core-init-mcps`: explizite Einrichtung und Health-Checks der Toolprovider
- `gortex-serena-configurator`: externe, inline verwendete Readiness- und Konfigurationsmethode für Gortex und den projektspezifischen Serena-Fallback
- `core-user2agent-instructions`: kontrollierte Pflege globaler und lokaler Benutzeranweisungen
- `core-repo-audit`: read-only Repositoryhygiene und Public-Readiness
- `core-scm`: Commit, Branch, Worktree, Merge, Push und Release nach expliziter Autorisierung
- Fachskills wie `core-architecture`, `core-backend`, `core-database`, `core-debug`, `core-docs`, `core-frontend`, `core-mobile`, `core-refactor`, `core-research` und `core-tf-infra`

Unterstützende Skills sind keine alternativen Lebenszyklen.

## 6. Kanonische Paketstruktur

```text
apm.yml
.apm/
├── agents/
│   ├── architecture-reviewer.agent.md
│   ├── backend-engineer.agent.md
│   ├── db-engineer.agent.md
│   ├── debug-investigator.agent.md
│   ├── docs-curator.agent.md
│   ├── frontend-engineer.agent.md
│   ├── mobile-engineer.agent.md
│   ├── pm-planner.agent.md
│   ├── qa-reviewer.agent.md
│   ├── refactor-engineer.agent.md
│   ├── research-explorer.agent.md
│   └── tf-infra-engineer.agent.md
└── skills/
    ├── core-shared/
    │   ├── SKILL.md
    │   ├── references/
    │   │   ├── workflow-contract.md
    │   │   ├── artifact-contract.md
    │   │   ├── tool-routing.md
    │   │   ├── verification.md
    │   │   └── user-instructions-contract.md
    │   └── assets/
    │       ├── workflow-catalog.yaml
    │       ├── handoff.md
    │       └── review-finding.yaml
    ├── core-brainstorm/
    ├── core-plan/
    ├── core-execute/
    ├── core-review/
    ├── core-init-project/
    ├── core-init-mcps/
    ├── core-user2agent-instructions/
    ├── core-repo-audit/
    ├── core-scm/
    ├── core-architecture/
    ├── core-backend/
    ├── core-database/
    ├── core-debug/
    ├── core-docs/
    ├── core-frontend/
    ├── core-mobile/
    ├── core-refactor/
    ├── core-research/
    └── core-tf-infra/
```

Jedes neu erstellte paketeigene Skillverzeichnis verwendet das Präfix `core-` und ist ein gültiges APM-Skillbundle mit `SKILL.md`; Verzeichnisname und Frontmatter-`name` sind identisch. `core-shared` ist ein intern referenziertes Bundle und kein fünfter Workflow. Seine `SKILL.md` ist ein kurzer Index; Verträge und Vorlagen liegen in `references/` beziehungsweise `assets/`.

APM projiziert `.apm/` in die Zielharnesses. Generierte `.agents/`, `.opencode/` oder `.codex/`-Kopien sind keine kanonischen Quellen und werden nicht manuell gepflegt.

Optionale Slash-Command-Adapter dürfen unter `.apm/prompts/` angeboten werden. Sie enthalten nur den Aufruf beziehungsweise die Übergabe an den kanonischen Skill und duplizieren keine Workflowlogik. Die Funktion des Pakets darf nicht von Command-Support eines einzelnen Harnesses abhängen.

### Externe APM-Skillabhängigkeit

Nur `gortex-serena-configurator` ist eine Laufzeitabhängigkeit der Workflow-Werkbank. Er wird als präzise virtuelle Unterverzeichnis-Abhängigkeit aus <https://github.com/Melivo/apm-package> bezogen, damit nicht die gesamte dortige Skillsammlung installiert wird und keine unnötigen Skillkollisionen entstehen:

```yaml
dependencies:
  apm:
    - Melivo/apm-package/skills/gortex-serena-configurator
```

`apm install` materialisiert diese Abhängigkeit und erzeugt beziehungsweise aktualisiert `apm.lock.yaml`. Der Lockfile wird versioniert und niemals manuell geändert. Vor Veröffentlichung wird eine verfügbare stabile Tag- oder Commit-Referenz bevorzugt; unabhängig davon hält der Lockfile den tatsächlich aufgelösten Commit und die Dateihashes fest.

### Sprache und Authoring-Gates

Alle paketeigenen Markdown-Dateien von Skills und Workflows werden auf Deutsch verfasst. Das betrifft insbesondere `SKILL.md`, zugehörige Markdown-Referenzen, Assets mit Instruktionstext und optionale Workflow-Promptadapter. Technische IDs, Frontmatter-Schlüssel, Dateipfade, Befehle, Schemanamen und Codebeispiele bleiben unverändert beziehungsweise in ihrer technisch erforderlichen Sprache. Dateien externer APM-Abhängigkeiten und generierte Zielprojektionen werden nicht übersetzt oder direkt bearbeitet.

`skill-creator` und `context-debloater` sind Authoring-Werkzeuge der Paketentwicklung, keine APM-Abhängigkeiten und keine Bestandteile eines Verbraucher-Workflows. Sie müssen in der Erstellungsumgebung verfügbar sein, werden aber weder durch dieses Paket installiert noch mit ihm ausgeliefert.

Für jeden neu erstellten oder materiell geänderten Skill beziehungsweise Workflow gilt verbindlich:

1. den lokal verfügbaren `skill-creator` laden und dessen Erstellungs- oder Revisionsablauf verwenden.
2. Skillbundle auf Routing, Ressourcen, Sicherheitsgrenzen und Struktur validieren.
3. Alle neu geschriebenen oder geänderten Markdown-Dateien dieses Skillbundles als explizite Einzelpfade mit `context-debloater` prüfen.
4. Debloat-Empfehlungen fachlich bewerten; akzeptierte Korrekturen am kanonischen Skill vornehmen und anschließend erneut validieren.
5. Beibehaltene Redundanz oder zurückgestellte Empfehlungen im Abschlussbericht knapp begründen.

`context-debloater` bleibt report-only und verändert die geprüften Dateien nicht selbst. Dieses Gate gilt auch für die vier Workflow-Skills, weil sie im APM-Paket als Skills ausgeliefert werden.

## 7. Minimaler Workflow-Katalog

`core-shared/assets/workflow-catalog.yaml` ist die maschinenlesbare Routingquelle, nicht der Ort für ausführliche Prozesslogik.

Er enthält nur:

- stabile Workflow-IDs,
- zulässige Vorgänger und Nachfolger,
- Ein- und Ausgabeschema,
- Mutationsklasse,
- Fresh-Context-Grenzen,
- maximale automatische Review-Reparaturrunden,
- bekannte Fachagenten- und Tool-IDs.

Die ausführliche Methode bleibt in den jeweiligen `SKILL.md`-Dateien. Dadurch verhindert der Katalog tote Referenzen, ohne eine zweite Workflowbeschreibung zu werden.

Verbindliche Übergänge:

```text
core-brainstorm → core-plan
core-plan → core-execute
core-execute → core-review
core-review.pass → completed
core-review.changes_requested → core-execute
core-review.material_scope_change → core-plan
```

Automatische `execute ↔ review`-Runden sind auf zwei begrenzt.

## 8. Shared Workflow Kernel

### `workflow-contract.md`

Definiert für alle Workflows:

- Autorisierungs- und Rückfragegrenzen,
- Umgang mit Abbruch, Blockade und Wiederaufnahme,
- Fresh-Context-Übergaben,
- Abschlussbedingungen,
- Vorrang expliziter und höherrangiger Anweisungen,
- Verbot stillschweigender Scope- oder Planänderungen.

### `artifact-contract.md`

Definiert Plan-, Run-, Handoff-, Taskresultat- und Findingformate sowie ihre Eigentümer.

### `tool-routing.md`

Definiert Capability-basierte Toolauswahl, Provider-Fallbacks und Grenzen für Gortex, Serena, Context7, YouTube Transcript, native Werkzeuge und Honcho.

### `verification.md`

Definiert Evidenz, Pflichtchecks, blockierte Prüfungen, Buildautorisierung, Reviewurteile und erneute Prüfung nach Korrekturen.

### `user-instructions-contract.md`

Definiert die sichere Übernahme manueller Benutzeranweisungen zwischen globaler und projektspezifischer `AGENTS.md`.

### Aufnahmeregel

Eine Regel gehört nur dann in `core-shared`, wenn sie von mindestens zwei Workflows oder Skills benötigt wird, domänenunabhängig ist und ihre Zentralisierung Widersprüche reduziert. Workflow-Schritte, Frameworkwissen und Fachmethodik bleiben beim jeweiligen Eigentümer.

## 9. Workflow: `core-brainstorm`

### Aktivierung

`core-brainstorm` ist optional. Es wird verwendet, wenn Ziel, Nutzerproblem, Scope oder Lösungsrichtung materiell unklar sind oder eine schwer reversible Entscheidung bevorsteht. Größe allein aktiviert kein Brainstorming.

### Ablauf

1. offenen Entscheidungsbedarf benennen,
2. Problem, Outcome, Scope, Nicht-Ziele und Constraints präzisieren,
3. nur materielle Lücken klären,
4. bei relevanten Entscheidungen mindestens zwei mechanistisch unterschiedliche Optionen vergleichen,
5. Entscheidung, Annahmen und verworfene Alternativen festhalten,
6. an `core-plan` übergeben.

### Tool- und Agentenbezug

- Gortex erkundet bei Brownfield-Entscheidungen den bestehenden Systemkontext.
- `architecture-reviewer` wird nur bei Architekturfolgen eingesetzt.
- `research-explorer` wird nur bei einer externen Wissenslücke read-only eingesetzt.
- Context7 und YouTube Transcript werden nicht vorsorglich geladen.
- Honcho darf bestätigte Nutzerpräferenzen beisteuern, aber keine Entscheidung ersetzen.

### Output

Standardoutput ist ein kompakter Decision-Handoff. Ein separates dauerhaftes Dokument entsteht nur, wenn Wissen über den einzelnen Plan hinaus Bestand haben muss. `core-plan` übernimmt die bestätigten Entscheidungen in den kanonischen Plan.

## 10. Workflow: `core-plan`

### Verantwortung

`core-plan` besitzt:

- Anforderungsframe,
- aktuelle Repositoryanalyse,
- bedingte externe Recherche,
- materielle Designentscheidungen,
- Taskgraph und Fachagentenzuweisung,
- Akzeptanzkriterien und Checks,
- statische Validierung und Nutzerbestätigung.

`core-plan` implementiert nicht und verwaltet keinen Laufzustand.

### Research-Hierarchie

1. Repositorycode, Tests und lokale Verträge über Gortex
2. aktuelle offizielle, möglichst versionsbezogene Dokumentation über Context7
3. lokale oder externe Projektinformation über Serena, wenn Gortex sie nicht bedienen kann oder Serena für die konkrete Informationssuche geeigneter konfiguriert ist
4. bekannte relevante Videos über YouTube Transcript
5. Standards und andere belastbare Primärquellen
6. Sekundärquellen nur ergänzend und gekennzeichnet

Research endet, sobald die materielle Planfrage beantwortet ist. Es gibt kein separates Pflichtdossier; Befund und Auswirkung werden knapp im Plan referenziert.

### Planformat

Der bestätigte Plan liegt unter:

```text
.agentic-workflow/plans/<plan-name>.md
```

Er ist ein Markdown-Dokument mit eingebettetem, validierbarem YAML-Taskgraphen:

```yaml
schema: plan/v1
status: Confirmed

tasks:
  - id: T01
    title: Kurzer, ergebnisorientierter Titel
    agent: backend-engineer
    task: Selbstständiger Auftrag für einen frischen Kontext
    context_paths: [src/example/, tests/example/]
    scope: [src/example/, tests/example/]
    dependencies: []
    required_mcps: [gortex]
    optional_mcps: [context7]
    acceptance:
      - id: AC01
        description: Beobachtbares Ergebnis
    checks:
      - id: CK01
        covers: [AC01]
        command: ["pytest", "tests/example/test_api.py"]
        cwd: "."
        pass: "exit code 0 und erwartete fachliche Beobachtung"
```

Regeln:

- genau ein registrierter Fachagent pro Task,
- `context_paths` sind Lesequellen, `scope` ist der erlaubte Änderungsscope,
- leeres `scope` bedeutet read-only,
- Abhängigkeiten sind der einzige Ordnungsmechanismus,
- jedes Akzeptanzkriterium wird durch mindestens einen Check gedeckt,
- Buildchecks werden nur aufgenommen und ausgeführt, wenn eine ausdrückliche Buildautorisierung vorliegt,
- materielle offene Unsicherheiten verhindern `Confirmed`.

### Übergabe

Der Plan enthält einen kurzen Handoff:

```text
Next workflow: execute
Input: exakter Pfad dieses bestätigten Plans
Constraints: relevante Planabschnitte
```

`core-execute` erhält einen frischen Kontext und sucht nicht selbst nach einem vermeintlich neuesten Plan.

## 11. Workflow: `core-execute`

### Verantwortung

`core-execute` ist der einzige öffentliche Implementierungs- und Ausführungsworkflow. Er besitzt Planvalidierung, Driftprüfung, Scheduling, Fachagenten-Dispatch, Isolation, Integration, Evidenz, Wiederaufnahme und die begrenzte Reparaturschleife.

Er plant nicht neu, urteilt nicht unabhängig über seine eigene Gesamtänderung und führt keine SCM- oder Deploymentoperation aus.

### Ablauf

1. bestätigten Plan und Projektpreflight laden,
2. Schema, Agenten, MCPs, Scopes, Abhängigkeiten und Checks validieren,
3. Repositorydrift prüfen,
4. Run anlegen oder fortsetzen,
5. Ready Set aus integrierten Abhängigkeiten ableiten,
6. Tasks an genau einen Fachagenten dispatchen,
7. Ergebnis und tatsächlichen Diff gegen Scope prüfen,
8. akzeptierte Ergebnisse serialisiert integrieren,
9. betroffene Checks auf dem integrierten Stand erneut ausführen,
10. Gesamtänderung mit frischem Kontext an `core-review` übergeben,
11. akzeptierte Findings innerhalb derselben `run_id` korrigieren,
12. nach bestandenem Review abschließen.

### Parallelität

- Read-only-Tasks dürfen parallel laufen, wenn keine externe Ressource kollidiert.
- Schreibende Tasks dürfen nur bei disjunkten Scopes, gemeinsamer Ausgangsbasis und sicherer Isolation parallel laufen.
- Standardmäßig werden höchstens zwei schreibende Tasks gleichzeitig ausgeführt.
- Integration in den autoritativen Checkout erfolgt immer serialisiert.
- Bei Unsicherheit wird serialisiert.
- Interne Task-Commits sind ohne ausdrückliche Commitautorisierung verboten.

### Debugging

Ein erwartbarer Implementierungsfehler bleibt beim zuständigen Domainagenten. Bei unklarer Ursache, Regression oder intermittierendem Fehler setzt `core-execute` den `debug-investigator` mit der Debug-Methode ein:

```text
reproduzieren → Hypothesen prüfen → Ursache bestimmen
→ minimal reparieren → Regressionsevidenz → execute fortsetzen
```

Debugging ist kein zusätzlicher Workflow.

### Taskresultat

```yaml
schema: task-result/v1
task_id: T01
attempt: 1
status: completed | partial | blocked | failed
changed_paths: []
acceptance:
  - id: AC01
    status: pass | fail | not_checked
    evidence: konkrete Beobachtung oder Artefaktpfad
checks:
  - id: CK01
    status: pass | fail | blocked
    command: ["pytest", "tests/example/test_api.py"]
    cwd: "."
    exit_code: 0
    evidence: kurze relevante Ausgabe
limitations: []
```

Exitcode 0 allein beweist keine fachliche Erfüllung. Pflichtchecks ohne aktuelle Evidenz führen zu `partial` oder `blocked`.

## 12. Workflow: `core-review`

### Verantwortung

`core-review` startet in einem frischen Kontext und besitzt das unabhängige Urteil. Es liest:

- bestätigten Plan,
- aktuellen Gesamtdiff,
- kompaktes Handoff,
- aktuelle Task- und Checkevidenz,
- bekannte Einschränkungen.

Es liest nicht die vollständige Implementierungsdiskussion und implementiert keine Korrekturen.

### Prüfreihenfolge

1. Ziel-, Scope- und Akzeptanzerfüllung
2. funktionale Korrektheit
3. Security- und Datenrisiken
4. Tests und Regressionen
5. Architektur, Modulgrenzen und Information Hiding
6. Performance, Accessibility und Dokumentation nach Relevanz
7. verbleibendes Risiko und Urteil

`qa-reviewer` führt die allgemeine Qualitätsanalyse aus. `architecture-reviewer` wird nur bei strukturellen Risiken hinzugenommen. Weitere Fachperspektiven werden bedarfsgerecht read-only eingesetzt; es gibt keine feste Reviewkaskade.

### Finding-Vertrag

```yaml
schema: review/v1
run_id: run-20260927-001
verdict: pass | changes_requested | blocked
findings:
  - id: RV01
    severity: blocking | high | medium | low
    task_id: T01
    owner: backend-engineer
    location: src/example.ts:42
    criterion: AC01
    evidence: reproduzierbare Beobachtung
    impact: konkrete Auswirkung
    expected_resolution: erforderliche Korrekturrichtung
    verification: erneute beobachtbare Prüfung
```

`task_id` wird verwendet, wenn ein Finding eindeutig einem Plantask zugeordnet werden kann. Ein innerhalb des bestätigten Scopes liegendes Querschnittsfinding darf stattdessen einen klaren `owner` und Bereich besitzen. Verändert ein Finding Ziel, Scope, Architektur oder Akzeptanzkriterien materiell, geht es zurück zu `core-plan`.

### Schleife

- `core-review` meldet Findings.
- `core-execute` ordnet sie dem passenden Fachagenten zu und integriert die Korrektur.
- Betroffene Checks und die Reviewprüfung werden auf dem aktuellen Stand wiederholt.
- Jede Reviewrunde startet aus aktuellen Artefakten, nicht aus dem alten Gespräch.
- Nach zwei automatischen Korrekturrunden stoppt der Lauf und informiert den Benutzer über verbleibende Findings.

## 13. Fachagentenmodell

Workflows besitzen den Lebenszyklus; Fachagenten besitzen Rollen. **Während der Ausführung eines Plans darf kein Fachagent eigene Subagenten starten; jeder weitere Dispatch bleibt ausschließlich bei `core-execute`.** Agenten erweitern keinen Scope.

| Agent | Primäre Verwendung | Grenze |
|---|---|---|
| `architecture-reviewer` | materielle Architekturentscheidung und strukturelles Review | keine Produktplanung, keine ungeplante Implementierung |
| `backend-engineer` | APIs, Authentifizierung, serverseitige Integration | keine unbestätigten Schemaentscheidungen |
| `db-engineer` | Datenmodell, Migration, Query und Index | keine produktive/destruktive Operation ohne Autorisierung |
| `debug-investigator` | unklare Ursachen, Regressionen, intermittierende Fehler | kein unabhängiges Refactoring |
| `docs-curator` | durch Änderungen verursachte Dokumentationsdrift | kein Produktcode |
| `frontend-engineer` | Web-UI und frontendseitige Integration | kein Frameworkwechsel ohne Entscheidung |
| `mobile-engineer` | Flutter, React Native und Swift | nur passende Plattformreferenz |
| `pm-planner` | bestätigungsfähiger Taskgraph | keine Implementierung |
| `qa-reviewer` | unabhängiges evidenzbasiertes Review | keine Fixes, keine Schleifensteuerung |
| `refactor-engineer` | verhaltensbewahrende Strukturänderung | keine Features oder Bugfixes |
| `research-explorer` | fokussierte read-only Evidenzsynthese | keine Repositorymutation |
| `tf-infra-engineer` | Terraform, IAM, Netzwerk und State | kein Apply oder Destroy ohne Autorisierung |

Fachmethodik liegt in Skills und bedingt geladenen Referenzen. Agentendefinitionen bleiben kurz und verweisen auf ihren Eigentümer-Skill. Die QA-Methode liegt im `core-review`-Skill; ein paralleler öffentlicher `qa`-Workflow oder zweiter QA-Lebenszyklus entfällt.

## 14. Tool- und MCP-Architektur

### Grundsatz

Workflows beschreiben benötigte Fähigkeiten, nicht vendorspezifische Aufrufzeremonie. `tool-routing.md` löst die Fähigkeit auf den verfügbaren Provider auf. Plan-Tasks nennen nur MCPs, deren Fehlen die konkrete Aufgabe wirklich blockiert.

### Gortex

Gortex ist die primäre Code-Intelligence für:

- taskbezogene Lokalisierung,
- Symbol-, Referenz- und Abhängigkeitsanalyse,
- Datenfluss- und Call-Chain-Analyse,
- Impact- und Vertragsprüfung vor Änderungen,
- sichere semantische Edits und Refactorings,
- post-edit Change Detection, Guards, Tests und Contracts,
- Diff-, PR-, Architektur- und Qualitätsanalyse.

Baseline für verändernde Codearbeit:

```text
explore/task → präziser Anchor → read/relations/trace
→ impact → edit/refactor → detect → guards/tests/contracts
```

Gortex-Views müssen zum aktuellen Checkout oder Worktree passen. Ein Fallback- oder inaktiver Ref-View bleibt read-only. Gortex speichert keinen Workflowzustand.

### Gortex-Skills

Gortex-Skills werden als bedingt geladene Arbeitsmethoden verwendet, nicht pauschal in jeden Kontext geladen:

| Situation | Bevorzugte Gortex-Skills |
|---|---|
| Repository kennenlernen | `gortex-onboarding`, `gortex-explore` |
| Architektur und Grenzen | `gortex-architecture-review`, `gortex-co-change` |
| Planung und Änderungsfolgen | `gortex-impact`, `gortex-dataflow-trace`, `gortex-cross-repo-usage` |
| sichere Mutation | `gortex-safe-edit`, `gortex-rename`, `gortex-refactor`, `gortex-extract-function` |
| Diagnose | `gortex-debug`, `gortex-incident-investigation` |
| Tests und Diagnostik | `gortex-add-test`, `gortex-fix-all` |
| unabhängiges Review | `gortex-pr-review`, `gortex-pr-review-agent`, `gortex-quality-audit` |

Der direkte Gortex-MCP-Vertrag bleibt die Baseline. Ein Gortex-Skill ist nur erforderlich, wenn sein höherwertiger Ablauf tatsächlich gebraucht wird. Die Skillnamen werden nicht in jeden Plantask kopiert.

### Context7

Context7 ist die bevorzugte Quelle für aktuelle, versionsbezogene Dokumentation zu Bibliotheken, Frameworks, SDKs, APIs, CLIs und Cloud-Diensten.

Vertrag:

1. Bibliothek-ID auflösen, sofern keine exakte ID vorliegt.
2. Version verwenden, wenn sie entscheidungsrelevant bekannt ist.
3. Pro Anfrage genau ein enges Dokumentationsthema abfragen.
4. Befund und Quelle in die konkrete Planentscheidung zurückführen.

Context7 wird nicht für allgemeine Programmierkonzepte, Business-Logic-Debugging, Repositoryreview oder Refactoring eingesetzt.

### YouTube Transcript

YouTube Transcript verarbeitet eine bekannte Video-URL. Es ist kein allgemeiner Videosuchdienst.

Einsatz:

- Video-Informationen und verfügbare Sprachen prüfen,
- bevorzugt ein zeitgestempeltes Transkript abrufen,
- nur entscheidungsrelevante Abschnitte auswerten,
- Sprecher, Datum, Quellenqualität und Zeitmarken sichtbar halten,
- Aussagen gegen offizielle Dokumentation oder Repositoryevidenz prüfen, wenn sie eine technische Entscheidung tragen.

Es wird nur verwendet, wenn eine relevante Quelle bekannt oder durch fokussierte Recherche begründet ausgewählt wurde.

### Serena

Serena ist der konfigurierte Fallback und ergänzende Provider für projektbezogene Recherche und Informationssuche:

- Datei-, Text- und symbolbezogene Suche im aktiven Projekt,
- Language-Server-basierte Definitionen und Referenzen,
- read-only Abfragen anderer ausdrücklich konfigurierter Projekte,
- Informationssuche, wenn Gortex die konkrete Operation nicht bedienen kann.

Serena ist kein allgemeiner Webresearch-Provider. Seine Memories und Onboardingnotizen werden von dieser Werkbank nicht als Workflowmemory verwendet, damit keine Konkurrenz zu Repositoryartefakten und Honcho entsteht. Serena wird nur für konkrete Projekte konfiguriert, niemals für das Benutzer-Home oder einen Dateisystemroot.

### Native Werkzeuge

Native Datei- und Suchwerkzeuge sind der letzte Fallback, wenn weder Gortex noch der ausdrücklich konfigurierte Serena-Pfad die Operation bedienen kann, sowie die normale Wahl außerhalb eines indexierten Projekts. Der Fallback wird im Ergebnis sichtbar gemacht.

## 15. Honcho-Memory

Honcho v3 dient als optionale semantische Erinnerung über Sitzungen, Werkzeuge und Modelle hinweg. Seine Workspace-, Peer-, Session- und Message-Primitiven eignen sich für langfristigen Kontext, nicht für transaktionalen Workflowzustand.

### Zulässige Nutzung

- stabile Benutzerpräferenzen,
- wiederkehrende, projektübergreifende Arbeitsweisen,
- explizit bestätigte langfristige Constraints,
- Hinweise auf frühere Entscheidungen, die anschließend gegen aktuelle Artefakte geprüft werden.

### Unzulässige Nutzung

- Planstatus, Taskstatus, Queue oder Retryzähler,
- Reviewurteil oder Findingstatus,
- Bestätigung oder Autorisierungsnachweis,
- Geheimnisse, Zugangsdaten oder unredigierte vertrauliche Inhalte,
- vollständige Gesprächsprotokolle,
- unbestätigte Annahmen als Fakten.

### Lesevertrag

Honcho wird nur mit einer auf Aufgabe und Projekt eingegrenzten Frage abgefragt. Ein Memorytreffer ist ein Hinweis. Vor Verwendung wird er gegen aktuelle Benutzeranweisungen, `AGENTS.md`, Plan, Code und andere Sources of Truth geprüft.

### Schreibvertrag

Geschrieben werden nur knappe, langlebige und bestätigte Informationen mit erkennbarer Herkunft. Projektfakten, die in Code oder Dokumentation gehören, werden dort gepflegt und nicht ausschließlich in Honcho abgelegt.

## 16. Informationsübertragung und Sources of Truth

```text
.agentic-workflow/
├── plans/
│   └── <plan-name>.md
└── runs/
    └── <run-id>/
        ├── state.yaml
        ├── handoff.md
        ├── tasks/
        │   └── <task-id>.yaml
        └── review.yaml
```

| Information | Source of Truth |
|---|---|
| Produktcode und Konfiguration | Repository und Git-Diff |
| Systemdesign dieses Pakets | `DESIGN.md` |
| Projektinvarianten | projektspezifische `AGENTS.md` und dokumentierte Verträge |
| Ziel, Scope und Taskgraph | bestätigter Plan unter `.agentic-workflow/plans/` |
| aktueller Ausführungszustand | `.agentic-workflow/runs/<run-id>/state.yaml` |
| Task- und Checkevidenz | `.agentic-workflow/runs/<run-id>/tasks/` |
| Kontextübergabe zu Review oder Resume | `.agentic-workflow/runs/<run-id>/handoff.md` |
| Reviewurteil und Findings | `.agentic-workflow/runs/<run-id>/review.yaml` |
| tatsächliche Änderungshistorie | Git |
| semantische Erinnerung | Honcho, nicht autoritativ |

Der Plan bleibt während der Ausführung unverändert. `state.yaml` enthält nur den aktuellen Resume-Zustand, keine Eventhistorie. `handoff.md` wird ersetzt statt endlos erweitert. Run-Artefakte sind normalerweise gitignoriert und nach Abschluss entbehrlich; bestätigte Pläne dürfen versioniert werden.

## 17. `core-init-project` und `AGENTS.md`

`core-init-project` ersetzt `prime` durch einen dauerhaften, kleinen Repository-Preflight:

1. Repository und Worktree prüfen.
2. Primäres Eingabeartefakt des aktuellen Workflows laden.
3. Nur relevante Dateien, Skills und Regeln lesen.
4. Git-Zustand vor Änderungen oder Review prüfen.
5. Gortex bedarfsgerecht verwenden.

Der verwaltete Projektabschnitt enthält nur belegte Fakten:

- Stack und Task Runner,
- tatsächliche Architektur- und Modulgrenzen,
- projektspezifische Sicherheits- und Freigabegrenzen,
- verbindliche Checks,
- kompakten Fachagenten- und Skill-Routingindex.

Ausführliche Domainhandbücher gehören in Fachskills, nicht in `AGENTS.md`. Dateiglobs sind nur Signale und werden mit Taskabsicht, Stack und Pfadkontext kombiniert.

### Code-Intelligence-Readiness mit `gortex-serena-configurator`

Nach Repository- und Stackinventur, aber vor dem Schreiben des verwalteten `AGENTS.md`-Blocks, lädt `core-init-project` den über APM installierten `gortex-serena-configurator` inline. Er wird nicht als Subagent dispatcht und erzeugt keinen eigenen Workflowzustand.

Der Integrationsablauf ist:

1. konkrete Repositorywurzel bestimmen und Benutzer-Home sowie Dateisystemroot ablehnen,
2. Gortex-Gesundheit und vorhandenes Tracking read-only prüfen,
3. Serena-Verfügbarkeit, projektspezifische Initialisierung, effektive Sprachen und autoritative MCP-Quelle read-only prüfen,
4. nur tatsächlich notwendige Aktionen gemeinsam zur Auswahl stellen,
5. ausschließlich bestätigte Serena-Einrichtung, Sprachabgleiche oder Gortex-Tracking-Aktionen ausführen,
6. Provider erneut auditieren und Bereitschaft getrennt für Gortex, Serena und native Fallbacks berichten.

Gortex-Tracking benötigt immer eine ausdrückliche Auswahl. Serena wird ausschließlich auf das konkrete Projekt begrenzt; Benutzer-Home, Dateisystemroot, Abhängigkeiten, Caches und generierte Bäume werden nicht als Serena-Projekt oder breiter Suchraum aktiviert.

Innerhalb von `core-init-project` bleibt `--apply-agents` beziehungsweise die entsprechende AGENTS-Schreiboption des Configurators deaktiviert. Der Configurator liefert nur seinen Readiness-Befund; `core-init-project` bleibt alleiniger Eigentümer des projektspezifischen verwalteten `AGENTS.md`-Blocks und schreibt dort die stabile Providerreihenfolge:

```text
Gortex, wenn gesund und Repository getrackt
→ projektspezifisches Serena als Recherche- und Code-Information-Fallback
→ native Werkzeuge als letzter Fallback
```

Flüchtige Health-Werte werden nicht in `AGENTS.md` persistiert. Ist Gortex nicht bereit, Serena aber verfügbar, darf der Init mit sichtbarer Degradierung abschließen. Sind beide nicht bereit, darf der Repository-Harness entstehen, aber Gortex-pflichtige spätere Tasks bleiben blockiert.

### Benutzeranweisungen

`core-init-project` und `core-user2agent-instructions` verwenden denselben Shared-Vertrag:

- globale Quelle: `Path.home() / "AGENTS.md"`
- Projektziel: `Path.cwd() / "AGENTS.md"`
- Synchronisierung nur global → Projekt,
- Standard: nur eindeutig manuelle Benutzeranweisungen zur Übernahme anbieten,
- generierte Blöcke und globale Spezialkonfiguration nicht kopieren,
- exakten Diff anzeigen und separat bestätigen lassen,
- Inhalte außerhalb des Zielabschnitts bytegenau erhalten,
- nach dem Schreiben Marker und Zielbereich verifizieren.

Eine vollständige Dateiübernahme ist eine gewarnte Ausnahme und verlangt die ausdrückliche Bestätigung beider absoluter Pfade.

### Priorität

1. System- und Entwickleranweisungen der Laufzeit
2. aktuelle ausdrückliche Benutzeranweisung
3. bestätigte projektspezifische Benutzeranweisungen
4. belegte Projektinvarianten und Verträge
5. zuständiger Fachskill und passende Referenz
6. importierte globale Präferenz
7. generischer Paketdefault

## 18. MCP-Einrichtung und APM

Aktuelle APM-Versionen können MCP-Abhängigkeiten in `apm.yml` deklarieren und pro Zielharness materialisieren. Das frühere pauschale Verbot, MCP-Konfiguration über das Paketmanifest zu verwalten, ist daher überholt.

Verbindliche Aufteilung:

- `apm.yml` darf portable, überprüfte MCP-Abhängigkeiten und Tool-Allowlisten deklarieren.
- `core-init-mcps` zeigt die konkrete Zielkonfiguration vorab, richtet umgebungsabhängige Provider kontrolliert ein und führt Health-Checks aus.
- Provider-spezifische Projektinitialisierung, etwa Gortex-Tracking oder Serena-Sprachen, bleibt ein expliziter Schritt und erfolgt nie stillschweigend.
- Credentials und lokale Secrets bleiben außerhalb des Pakets und der Repositoryartefakte.
- Es gibt keine zweite, konkurrierende MCP-Konfigurationsdatei der Workflow-Werkbank.

Vor Veröffentlichung müssen die tatsächlichen Registry-IDs, Transporte, Zielharnesses und Tool-Allowlisten mit `apm compile --validate`, Preview und Dry-Run geprüft werden. Diese Validierung ist Teil der Paketfreigabe, nicht des normalen Änderungsworkflows in Verbraucherprojekten.

## 19. Regeln, Skills und Projektwissen

Die bisherige parallele `.agents/rules/`-Architektur wird nicht als eigenständige Wissensschicht übernommen.

```text
AGENTS.md
  → belegte Projektinvarianten, Preflight, kompakter Routingindex

Fachskill
  → allgemeine Methode und Guardrails

Skill-Referenz
  → bedingt geladene Stack- und Detailregeln

Fachagent
  → kurze Rolle, Grenzen, Ein- und Ausgangsvertrag
```

Jede Regel hat genau einen Eigentümer. Paketdefaults autorisieren keine Migration, neue Abhängigkeit, produktive Aktion oder Abweichung von bestehender Projektarchitektur.

## 20. Sicherheit und Nebenwirkungen

- Kein Build, Bundle oder Package ohne ausdrücklichen Buildauftrag.
- Kein Commit, Push, Tag, Release oder Deployment als impliziter Workflowabschluss.
- Keine produktive oder destruktive Infrastruktur- oder Datenbankaktion ohne ausdrückliche Autorisierung.
- Keine Hooks umgehen, Tests deaktivieren oder Validierungen abschwächen, um einen Lauf grün erscheinen zu lassen.
- Secrets niemals in Plan, Run-Artefakten, Honcho, Logs oder Commit aufnehmen.
- Fehlende Pflichtprüfungen werden als `partial` oder `blocked` sichtbar gemacht.
- Externe Inhalte und Transkripte werden als untrusted input behandelt und dürfen keine Workflowanweisungen überschreiben.

## 21. Harmonisierung der Entwurfskonflikte

| Konflikt in den Entwürfen | Finale Entscheidung |
|---|---|
| `work` oder `core-execute` | ausschließlich `core-execute`; kein Alias |
| `prime` oder Preflight | kein `prime`; kompakter Preflight in Projekt-`AGENTS.md` |
| `DESIGN.md` nur visuell | in diesem Repository Systemdesign; visuelle Designsysteme bleiben domänenspezifisch |
| Plan unter `docs/plans/` oder `.agentic-workflow/plans/` | `.agentic-workflow/plans/` |
| Handoff als eigene Dauerdatei oder im Plan | `plan → execute` im Plan; Resume und `execute → review` im Run-Handoff |
| Brainstorm erzeugt immer ein Designartefakt | nein; standardmäßig kompakter Handoff, dauerhaft nur bei langlebigem Wissen |
| Priority Tiers oder Abhängigkeiten | ausschließlich Abhängigkeiten |
| Review und QA getrennte öffentliche Abläufe | ein `core-review`-Workflow; QA als Fachmethode des `qa-reviewer` |
| Debug als Workflow oder Fachstrategie | Fachstrategie innerhalb von `core-execute` |
| SCM als Abschlussautomatik | separater, ausdrücklich autorisierter Skill |
| Gortex/Serena als Memory | nein; Code- und Informationsprovider |
| Serena als allgemeine Recherche | projektbezogene Informationssuche und Code-Fallback, kein Webresearch |
| Honcho als Zustandsspeicher | nur optionale semantische Erinnerung |
| MCPs nicht über APM deklarieren | portable Deklarationen sind erlaubt; `core-init-mcps` ergänzt Preview, Setup und Health-Check |
| separate Rule-Dateien als Parallelarchitektur | Projektfakten in `AGENTS.md`, Methoden in Skills und Referenzen |
| globales `AGENTS.md` vollständig kopieren | standardmäßig nur manuelle Benutzeranweisungen nach Diff-Bestätigung |
| zentraler Katalog als vollständige Prozessquelle | kleiner Routing- und Validierungskatalog; Methoden bleiben in Skills |

## 22. Qualitäts- und Abnahmekriterien

Das Design gilt als umgesetzt, wenn:

1. nur `core-brainstorm`, `core-plan`, `core-execute` und `core-review` den Kernlebenszyklus bilden,
2. jeder Übergang ein eindeutiges Eingabe- und Ausgabeartefakt besitzt,
3. `core-execute` und `core-review` mit frischem Kontext aus Dateien arbeitsfähig sind,
4. der Plan genau eine Source of Truth bleibt und Runstatus nicht zurückgeschrieben wird,
5. jeder Task genau einem registrierten Fachagenten gehört,
6. Parallelität nur bei disjunkten Scopes und sicherer Isolation stattfindet,
7. Review-Findings reproduzierbar und maschinenlesbar an `core-execute` zurückgehen,
8. Gortex primär und seine Skills bedarfsgerecht geroutet werden,
9. Context7, YouTube Transcript und Serena ihre definierten Recherchegrenzen einhalten,
10. Honcho keinen autoritativen Workflowzustand enthält,
11. `core-init-project` manuelle `AGENTS.md`-Inhalte schützt und idempotent bleibt,
12. `.apm/` die einzige Paketquelle ist und alle generierten Projektionen reproduzierbar sind,
13. kein Paketdefault Builds, SCM, Deployment oder destruktive Aktionen implizit autorisiert,
14. APM-Validierung keine toten Workflow-, Agenten-, Skill- oder MCP-Referenzen findet,
15. `apm install` die virtuelle `gortex-serena-configurator`-Abhängigkeit aus `Melivo/apm-package` auflöst und der versionierte Lockfile ihren konkreten Commit und ihre Hashes festhält,
16. `core-init-project` den `gortex-serena-configurator` inline und ohne konkurrierenden `AGENTS.md`-Schreiber verwendet,
17. alle paket eigenen Markdown-Dateien von Skills und Workflows auf Deutsch verfasst sind,
18. jeder neu erstellte oder materiell geänderte Skill mit `skill-creator` erstellt beziehungsweise revidiert und anschließend mit `context-debloater` geprüft wurde.

## 23. Provenienz und aktuelle Referenzen

Konsolidierte interne Quellen:

- `reference/source-material/design-drafts/Brainstormvorhaben.md`
- `reference/source-material/design-drafts/Planvorhaben.md`
- `reference/source-material/design-drafts/Executevorhaben.md`
- `reference/source-material/design-drafts/Informationsuebertragung-vorhaben.md`
- `reference/source-material/design-drafts/Regelnvorhaben.md`
- `reference/source-material/design-drafts/toolskills-vorhaben.md`
- `reference/source-material/design-drafts/Uebernahmekandidaten-vorhaben.md`
- `reference/source-material/design-drafts/Shared-Workflow-Kernel-vorhaben.md`
- `reference/source-material/design-drafts/Projekt-Init-AGENTS-vorhaben.md`
- `reference/source-material/design-drafts/merkzettel-workflow.md`
- `reference/source-material/design-drafts/user2agent.md`
- die drei Zwischenprotokolle vom 27. September 2026

Aktuelle offizielle Produktquellen:

- Microsoft APM Producer-Dokumentation: <https://microsoft.github.io/apm/_llms-txt/producer-ramp.txt>
- Microsoft APM Dependency-Verwaltung: <https://microsoft.github.io/apm/consumer/manage-dependencies/>
- Abhängiges Skillpaket: <https://github.com/Melivo/apm-package>
- Context7 Agentregel und MCP-Ablauf: <https://github.com/upstash/context7/blob/master/rules/context7-mcp.md>
- Serena Tools: <https://oraios.github.io/serena/01-about/035_tools.html>
- Serena Project Workflow: <https://oraios.github.io/serena/02-usage/040_workflow.html>
- Honcho-v3-Übersicht: <https://honcho.dev/docs/v3/documentation/introduction/overview>

## 24. Schlussentscheidung

Die Workflow-Werkbank ist kein Orchestrator-Framework mit vielen Modi, sondern ein kleiner, dateibasierter Lebenszyklus:

```text
brainstorm klärt
plan entscheidet und zerlegt
execute setzt um und integriert
review urteilt unabhängig
```

Gortex liefert die primäre strukturelle Sicht auf den Code. Context7 liefert aktuelle offizielle Technologiedokumentation. YouTube Transcript erschließt gezielt bekannte Videoquellen. Serena ergänzt projektbezogene Recherche und dient als konfigurierter Code-Intelligence-Fallback. Fachagenten bearbeiten eng begrenzte Rollen. Honcho erinnert, entscheidet aber nicht.

Diese Trennung hält das System lean, clean, nachvollziehbar und nach einem Kontextwechsel reproduzierbar.

## Interne Designmethoden und capability-basiertes MCP-Routing

Die kanonische Fachbasis liegt in [core-architecture/references/design-baseline.md](.apm/skills/core-architecture/references/design-baseline.md), die Vertiefungen in den dort direkt ausgewählten paketinternen Referenzen. Die SWE-Grundsätze gelten für tatsächlich betroffene Coding-Bereiche und die Abschlussprüfung; Clairvoyance-Diagnosen werden ausschließlich durch belegte Struktur- oder Vertragssignale ausgelöst. Ein Referenzladen aktiviert keinen Architekturworkflow. Agentendefinitionen bleiben kurze Eigentümer-Skill-Verweise; core-shared enthält keine Designfachmethodik.

Boundary-/Abstraktionsdiagnose, Schnittstellen-/Fehlerprüfung, Designentwicklung/Vertragsklarheit und Alternativenvergleich teilen kanonische Methoden, keine kopierten Komplettworkflows. Warnzeichen werden erst mit Quelle, Ursache und Wirkung zum Finding. Legitime Adapter, öffentliche Datenverträge und notwendige fachliche Kopplung bleiben möglich. Fehlende Evidenz bleibt eine Lücke; neue Refactorings benötigen den bestätigten Task und sein Safety Net.

[Provenienz und vollständiges Quellenmapping](.apm/skills/core-architecture/PROVENANCE.md) sowie [MIT-Hinweise](.apm/skills/core-architecture/THIRD_PARTY_NOTICES.md) sichern die Clairvoyance-Adaptionen. Die Umsetzung erzeugt keine externen Skill-Laufzeitabhängigkeiten und übernimmt den privaten UNLICENSED-SWE-Skill nicht.

[Toolrouting](.apm/skills/core-shared/references/tool-routing.md) bestimmt benötigte Operationen aus dem Task und prüft relevante aktuelle Fähigkeiten über Laufzeitdeklarationen und gezielte Discovery. Weitere passende Provider dürfen innerhalb bestehender Prioritäts-, Projekt-, Freshness- und Autorisierungsgrenzen genutzt werden. Keine pauschale MCP-Inventarisierung, kein automatisches Provisionieren und kein blinder Retry möglicherweise ausgeführter Mutationen. Erlaubte Fallbacks und fehlende Pflichtfähigkeiten werden sichtbar berichtet.

Skill-Creator und Context-Debloater sind lokale Authoring-Werkzeuge, keine neuen Paketabhängigkeiten. Statische Struktur-/Routingprüfungen belegen kein beobachtetes Laufzeitverhalten und keine Token-, Kosten- oder Latenzersparnis.

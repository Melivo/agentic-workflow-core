# Agentic Workflow Core — finales Systemdesign

**Status:** Final und verbindlich
**Geltungsbereich:** öffentliches Microsoft-APM-Paket und dessen Workflow-Werkbank
**Kanonische Paketquelle:** `.apm/`
**Kernablauf:** `core-brainstorm? → core-plan → core-review (Planreview, Text) → Nutzerbestätigung → core-execute ↔ core-review (Umsetzungsreview)`

## 1. Zweck und Autorität

Dieses Dokument konsolidiert die Entwürfe unter `reference/source-material/design-drafts/` zu einer einzigen Architektur. Es ist für die Paketimplementierung die Source of Truth. Frühere Entwürfe und Zwischenprotokolle bleiben als Herkunftsnachweis erhalten, sind bei Widersprüchen aber nachrangig.

In diesem Repository bezeichnet `DESIGN.md` das Systemdesign der Workflow-Werkbank. Die frühere Aussage, `DESIGN.md` sei ausschließlich für visuelles Design reserviert, gilt nur für Anwendungsprojekte mit einem visuellen Designsystem und wird für dieses Meta-Repository ausdrücklich nicht angewendet.

## 2. Ziele

Das Paket soll:

- wenige klar abgegrenzte Workflows bereitstellen, die ohne Parallelarchitektur ineinandergreifen,
- Planung, Planreview vor Nutzerbestätigung und read-only Umsetzungsreview nach Execute durch frische Kontexte trennen,
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
10. **Lean bedeutet keine fehlenden Grenzen.** Kleine Verträge ersetzen große Orchestratoren. Geplant und umgesetzt wird nur die kleinste hinreichende Lösung für das ursprüngliche Ziel; der kumulative Scope zählt, nicht nur der direkte Vorgänger. Ein erlaubter Dateipfad ist keine Freigabe für beliebige zusätzliche Funktionen.

## 5. Gesamtmodell

```text
Einmal pro Umgebung:
  APM-Paket installieren → core-init-mcps? → vorhandene MCP-Provider read-only prüfen

Einmal pro Repository:
  core-init-project → core-repo-audit?

Pro Änderung:
  core-brainstorm? → core-plan → frischer Kontext → core-execute → frischer Kontext → core-review
                                           ↑                           │
                                           └──── strukturierte Findings┘

Nach bestandenem Review:
  Abschluss → optionaler, ausdrücklich autorisierter core-devops-Schritt (bei Codeänderungen Release erst jetzt)
```

### Öffentliche Kernworkflows

| ID | Verantwortung | Mutiert Produktcode? | Primärer Output |
| --- | --- | ---: | --- |
| `core-brainstorm` | Absicht, Scope und Lösungsrichtung klären | nein | kompakter Decision-Handoff |
| `core-plan` | Repositoryanalyse, Research, Entscheidungen, Taskgraph und eng begrenzter Planreview-Dispatch an `qa-reviewer`/`core-review` | nein | bestätigungsfähiger `plan/v1` |
| `core-execute` | bestätigten Taskgraph ausführen und integrieren | ja | Run-Artefakte und Review-Handoff |
| `core-review` | unabhängiges Planreview vor Bestätigung und read-only Umsetzungsreview nach Execute | nein | Texturteil im Planreview; `review/v1` im Umsetzungsreview |

### Unterstützende Skills

- `core-init-project`: Repository-Harness, Projektinvarianten und `AGENTS.md`-Preflight
- `core-init-mcps`: read-only Bereitschaftsprüfung bereits vorhandener Toolprovider; keine Installation oder Konfiguration
- `core-milestone`: Ziel, unveränderliche Etappendefinitionen und aktualisierbarer Auswahl-/Nachweisindex ausschließlich für ausdrücklich mehrstufige Vorhaben
- `core-handoff`: autorisierte Sitzungs- und Etappenübergabe anhand exakter Artefaktpfade, ohne Statusverwaltung
- `gortex-serena-configurator`: mitgelieferte, inline verwendete Readiness- und Konfigurationsmethode für Gortex und den projektspezifischen Serena-Fallback
- `core-user2agent-instructions`: kontrollierte Pflege globaler und lokaler Benutzeranweisungen
- `core-repo-audit`: read-only Repositoryhygiene und Public-Readiness
- `core-devops`: eigenständige, klar benannte Git-/Releaseaufträge nach ausdrücklicher Freigabe (ohne Implementierungsplan); geplante Automationseinrichtung dagegen über bestätigte Tasks mit `core-plan`/`core-execute`; Releases nach Codeänderungen erst nach bestandenem Review
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
    ├── core-handoff/
    ├── core-milestone/
    ├── core-repo-audit/
    ├── core-devops/
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

Die Paketquelle enthält aktuell 22 paketeigene `core-*`-Skillbundles einschließlich des internen `core-shared`; der mitgelieferte Begleitskill `gortex-serena-configurator` ergänzt diese 22 Bundles, ohne selbst ein Kernworkflow zu sein.

APM projiziert `.apm/` in die Zielharnesses. Generierte `.agents/`, `.opencode/` oder `.codex/`-Kopien sind keine kanonischen Quellen und werden nicht manuell gepflegt.

Optionale Slash-Command-Adapter dürfen unter `.apm/prompts/` angeboten werden. Sie enthalten nur den Aufruf beziehungsweise die Übergabe an den kanonischen Skill und duplizieren keine Workflowlogik. Die Funktion des Pakets darf nicht von Command-Support eines einzelnen Harnesses abhängen.

### Mitgelieferte Code-Intelligence-Methode

[`gortex-serena-configurator`](.apm/skills/gortex-serena-configurator/SKILL.md) liegt vollständig in der kanonischen Paketquelle. Die ursprüngliche Skill-ID, englischen Instruktionen und ausführbaren Quellen bleiben bei der Migration unverändert; Herkunft und die ausdrückliche MIT-Freigabe sind in seinem `PROVENANCE.md` dokumentiert. Die übrige private Sammlung wurde nicht übernommen oder neu lizenziert.

```yaml
dependencies:
  apm: []
```

Der Paketbau benötigt damit keine privaten Git-Clones oder Zugangsdaten. APM erzeugt den versionierten Lockfile; Archive und frische Installationen müssen alle Dateien des Begleitskills bytegenau gegen die kanonische Quelle prüfen. Seine unveränderten Sicherheitsprüfungen gehören über einen Test-Discovery-Adapter zur normalen CI.

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
core-plan → core-review (Planreview; Textantwort vor Bestätigung)
core-plan → core-execute (erst nach Nutzerbestätigung)
core-execute → core-review (Umsetzungsreview; review/v1)
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

`core-plan` implementiert nicht und verwaltet keinen Laufzustand. Ausschließlich für das Planreview vor Nutzerbestätigung darf es den `qa-reviewer` mit `core-review` in frischem Kontext beauftragen; dieser enge QA-Dispatch ist keine allgemeine Agentenkoordination.

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

- Plan und Tasks binden jede Arbeit an ein ursprüngliches Zielkriterium samt Notwendigkeit; Folge- und Ersatzpläne prüfen den kumulativen Scope gegen das Originalziel, nicht nur den direkten Vorgänger. Ein erlaubter Pfad ist keine Funktionsfreigabe.
- Bei Coding-Tasks wendet `core-plan` S00 bereits auf Lösungswahl und Taskgrenzen an, auch wenn kein Architektur-Trigger vorliegt.
- `context_paths` enthalten für Coding-Tasks die kanonische S00-Referenz und alle weiteren exakt benötigten Lesequellen; `scope` ist der erlaubte Änderungsscope.
- Akzeptanzkriterien und Checks decken anwendbare S00-relevante Ergebnisse konkret und überprüfbar ab, ohne ein neues Planfeld oder einen pauschalen Architektur-Vollscan.
- genau ein registrierter Fachagent pro Task,
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

### Verantwortung des Execute-Workflows

`core-execute` ist der einzige öffentliche Implementierungs- und Ausführungsworkflow. Er besitzt Planvalidierung, Driftprüfung, Scheduling, Fachagenten-Dispatch, Isolation, Integration, Evidenz, Wiederaufnahme und die begrenzte Reparaturschleife.

Er plant nicht neu, urteilt nicht unabhängig über seine eigene Gesamtänderung und führt keine SCM- oder Deploymentoperation aus.

### Ablauf des Execute-Workflows

1. bestätigten Plan und Projektpreflight laden,
2. Schema, Agenten, MCPs, Scopes, Abhängigkeiten und Checks validieren; bei Coding-Tasks S00 direkt auf die betroffenen Strukturen und Verträge anwenden,
3. Repositorydrift prüfen,
4. Run anlegen oder fortsetzen,
5. Ready Set aus integrierten Abhängigkeiten ableiten,
6. jeden Task an genau einen Fachagenten dispatchen; Coding-Tasks zusätzlich mit S00-Referenz und zuständigem Fachskill übergeben,
7. Ergebnis, S00-Befund in vorhandenen Ergebnisfeldern und tatsächlichen Diff gegen Scope prüfen; keine unabhängige Selbstreview,
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

Exitcode 0 allein beweist keine fachliche Erfüllung. Pflichtchecks ohne aktuelle Evidenz führen zu `partial` oder `blocked`. `core-execute` persistiert Rückgaben read-only eingesetzter Agenten in deren Taskresultat; diese Agenten erhalten dadurch keine Schreibrechte auf Produkt- oder andere Runartefakte. Ein ausdrücklich schreibender Task-Agent darf ausschließlich die eigene Ergebnisdatei als eng begrenzte Ausnahme ändern. Neue Taskversuche liegen in eindeutigen, unveränderlichen `tasks/<task-id>/attempt-<nn>.yaml`-Dateien; bestehende `tasks/<task-id>.yaml` werden nur lesend als Legacy-Ergebnis unterstützt und nicht migriert oder überschrieben.

## 12. Workflow: `core-review`

### Verantwortung und zwei Modi

`core-review` urteilt unabhängig und read-only in frischem Kontext. Es hat zwei getrennte Modi:

- **Planreview:** Nach vollständigem Entwurf und vor Nutzerbestätigung. Es prüft Entwurf und Originalauftrag und gibt `pass`, `changes_requested` oder `blocked` als kurze Textantwort mit konkreten Stellen aus. Es entsteht kein Run und kein `review/v1`; pass bedeutet nur bestätigungsfähig. Materielle Entwurfsänderungen werden erneut geprüft.
- **Umsetzungsreview:** Nach `core-execute` prüft es die integrierte Gesamtänderung anhand des bestätigten Plans, aktuellen Gesamtdiffs, kompakten Handoffs, Task-/Checkevidenz und Einschränkungen. Dieser Modus verwendet das bestehende `review/v1`.

In keinem Modus liest es die vollständige Implementierungsdiskussion oder implementiert Korrekturen. Im Umsetzungsreview empfiehlt es bei anhand von Originalziel, Kriterien, Nichtzielen und Diff belegtem Bloat ausdrücklich das Verwerfen beziehungsweise den kleinsten sicheren Rückbau statt zusätzlichen Ausbau. Unsichere Notwendigkeit wird als Evidenzlücke behandelt; notwendige Schutzmaßnahmen sowie fremde Änderungen bleiben erhalten. Die Empfehlung ist keine Mutationserlaubnis.

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

Workflows besitzen den Lebenszyklus; Fachagenten besitzen Rollen. **Während der Ausführung eines Plans darf kein Fachagent eigene Subagenten starten; jeder Dispatch bleibt ausschließlich bei `core-execute`.** Einzige Ausnahme außerhalb der Ausführung: `core-plan` darf ausschließlich für das Planreview `qa-reviewer`/`core-review` in frischem Kontext beauftragen. Agenten erweitern keinen Scope.

| Agent | Primäre Verwendung | Grenze |
| --- | --- | --- |
| `architecture-reviewer` | materielle Architekturentscheidung und strukturelles Review | keine Produktplanung, keine ungeplante Implementierung |
| `backend-engineer` | APIs, Authentifizierung, serverseitige Integration | keine unbestätigten Schemaentscheidungen |
| `db-engineer` | Datenmodell, Migration, Query und Index | keine produktive/destruktive Operation ohne Autorisierung |
| `debug-investigator` | unklare Ursachen, Regressionen, intermittierende Fehler | kein unabhängiges Refactoring |
| `docs-curator` | durch Änderungen belegte Dokumentationsdrift oder Dokumentationslücken entlang der DOX-Hierarchie | kein Produktcode |
| `frontend-engineer` | Web-UI und frontendseitige Integration | kein Frameworkwechsel ohne Entscheidung |
| `mobile-engineer` | Flutter, React Native und Swift | nur passende Plattformreferenz |
| `pm-planner` | bestätigungsfähiger Taskgraph | keine Implementierung |
| `qa-reviewer` | unabhängiges evidenzbasiertes Review | keine Fixes, keine Schleifensteuerung |
| `refactor-engineer` | verhaltensbewahrende Strukturänderung | keine Features oder Bugfixes |
| `research-explorer` | fokussierte read-only Evidenzsynthese | keine Repositorymutation |
| `tf-infra-engineer` | Terraform, IAM, Netzwerk und State | kein Apply oder Destroy ohne Autorisierung |

Fachmethodik liegt in Skills und bedingt geladenen Referenzen und wird bei Bedarf inline verwendet; sie ist kein Agenten-Dispatch. Während der Ausführung startet ausschließlich `core-execute` Fachagenten, je einen registrierten Agenten pro Task; kein Agent startet weitere Agenten. Die einzige enge Ausnahme außerhalb der Ausführung: `core-plan` darf für das Planreview einen `qa-reviewer` mit `core-review` in frischem Kontext beauftragen. Agentendefinitionen bleiben kurz und verweisen auf ihren Eigentümer-Skill. Die QA-Methode liegt im `core-review`-Skill; ein paralleler öffentlicher `qa`-Workflow oder zweiter QA-Lebenszyklus entfällt.

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
| --- | --- |
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

### Optionale Habit-Feedback-Integration

`opencode-habit-feedback@0.1.0` ergänzt bei ausdrücklicher Nutzung Toolfeedback durch die Original-Habit-Hooks-Sensoren und den Original-Mapper. Die bedingten Verweise in `core-plan`, `core-execute`, `core-refactor`, `core-review` und `core-devops` verknüpfen diese Hinweise mit bestehenden Verantwortlichkeiten; sie führen keine neue Fachmethodik, Pflichtabhängigkeit, automatische Taskanlage oder Autorisierung ein. Toolausgaben bleiben untrusted Daten. Refactoring wahrt das beobachtbare Verhalten und sein Safety Net; Review bleibt unabhängig und read-only.

Das Paket `opencode-habit-feedback@0.1.0` ist isoliert geprüft, aber noch nicht auf npm veröffentlicht; globale Benutzerinstallation oder Aktivierung hat nicht stattgefunden. Andere Core-Verbraucher können die Integration freiwillig nutzen. Nach Veröffentlichung und separater ausdrücklicher Freigabe wird die Registrierung additiv als OpenCode-V2-Objekt `{package, options}` im bestehenden globalen `plugins`-Array eingerichtet; vorhandene Plugins bleiben erhalten. Verifizierte absolute Pfade werden pro Plugininstanz nur an Child-Prozesse gebunden; Shell-/Login-Umgebungsänderungen sind dafür nicht nötig. Der normale Hook installiert keine Pakete oder Detektoren. Der automatische Einzeldatei-Hook qualifiziert Python-/generische Dateisensoren mit ruff; repositoryweite jscpd-/deptry-Sensoren sind vor dem Spawn deaktiviert und ihre duplicated-code-/unused-dependency-Abdeckung als not_scanned ausgewiesen. Deren Pins gelten nur für getrennte, ausdrücklich autorisierte Repository-Scans. Erlaubte deaktivierte Ruff-/line-count-Sensoren sowie nicht-None-files-Overrides werden ebenfalls als not_scanned-Lücken ausgewiesen; Overrides bleiben mangels qualifiziertem Messbeleg konservativ ungeprüft, ohne Präferenzen zu überschreiben oder einen eigenen Matcher einzuführen. Gültige Findings und Originalmapper-Coaching der tatsächlich gemessenen Teilmenge einschließlich Advisory bleiben sichtbar, während Coverage-Lücken complete/clean verhindern. CK04 beobachtete 110 isolierte Hostfälle, darunter alle 90 zuvor geprüften Fälle und 20 RV06-Fälle; daraus folgt keine Garantie allgemeiner LLM-Beobachtungsqualität. Eine globale Registrierung garantiert nicht die Aktivierung in jedem Repository; Deaktivierungen werden sichtbar gemeldet. Die qualifizierte Hostkombination ist Linux, Node.js 22, Python 3.13 und OpenCode-/SDK 2.0.25; daraus folgen keine Zusagen für andere Versionen, Sprachen, alle Dateien oder unbekannte Toolformen. Das genaue JSONC-Objekt, Fehler- und Vertrauensgrenzen sowie Prüfkommandos stehen in der [Habit-Feedback-Nutzungsreferenz](.apm/skills/core-devops/references/habit-feedback.md).

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
| --- | --- |
| Produktcode und Konfiguration | Repository und Git-Diff |
| Systemdesign dieses Pakets | `DESIGN.md` |
| Projektinvarianten | projektspezifische `AGENTS.md` und dokumentierte Verträge |
| Gesamtziel und gemeinsame bestätigte Entscheidungen | `.agentic-workflow/goals/<goal-id>/goal.md` (`goal/v1`), nur bei ausdrücklich mehrstufigem Vorhaben; Eigentümer: `core-milestone` |
| unveränderliche Etappendefinition und Version | `.agentic-workflow/goals/<goal-id>/milestones/<milestone-id>-v<version>.yaml` (`milestone-definition/v1`); Eigentümer: `core-milestone` |
| Versionsauswahl, aktuelle Etappe und Nachweisverweise | `.agentic-workflow/goals/<goal-id>/index.yaml` (`milestone-index/v1`); Eigentümer: `core-milestone` |
| Ziel, Scope und Taskgraph | bestätigter Plan unter `.agentic-workflow/plans/` (`plan/v1`); Eigentümer: `core-plan` |
| aktueller Ausführungszustand | `.agentic-workflow/runs/<run-id>/state.yaml`; Eigentümer: `core-execute` |
| Task- und Checkevidenz | neue Versuche: `.agentic-workflow/runs/<run-id>/tasks/<task-id>/attempt-<nn>.yaml`; Legacy-Leseform: `tasks/<task-id>.yaml`; `core-execute` persistiert read-only Agentenergebnisse |
| Kontextübergabe zu Review oder Resume | `.agentic-workflow/runs/<run-id>/handoff.md` |
| Reviewurteil und Findings | `.agentic-workflow/runs/<run-id>/review.yaml` |
| tatsächliche Änderungshistorie | Git |
| semantische Erinnerung | Honcho, nicht autoritativ |

Der Plan bleibt während der Ausführung unverändert. `state.yaml` enthält nur den aktuellen Resume-Zustand, keine Eventhistorie. `handoff.md` wird ersetzt statt endlos erweitert. Run-Artefakte sind normalerweise gitignoriert; bestätigte Pläne dürfen versioniert werden. Ziel, referenzierte Definitionsversionen, Index, Plan-, Run-, Review-, Taskversuchs- und Originalprüfnachweise bleiben erhalten, solange Ziele oder spätere Übergaben darauf angewiesen sind. Referenzabhängige Aufbewahrung ersetzt pauschale Löschung nach Runabschluss.

### Mehrstufige Ziele und Versionsübergaben

Einfache Vorhaben ohne Milestones benötigen keine Zielstruktur; ein bestätigter `plan/v1` genügt. Nur für ausdrücklich gewählte mehrstufige Vorhaben kommen drei getrennte Formate hinzu: `goal/v1` in `.agentic-workflow/goals/G01/goal.md`, unveränderliche `milestone-definition/v1`-Dateien unter `milestones/` und ein aktualisierbarer `milestone-index/v1` in `index.yaml`. `core-milestone` besitzt Ziel, Definitionen und Index. Bestätigte Definitionen bleiben unveränderlich. Das Ziel hält Gesamtziel, Nicht-Ziele, Leitplanken, bestätigte gemeinsame Entscheidungen und Gesamtzielkriterien fest; Definitionen halten Outcome, Scope, Kriterien und exakte versionierte Abhängigkeiten fest; der Index ist die Auswahl- und Nachweisquelle, kein Scheduler und keine Kopie von Task-/Runstatus.

Beispiel: `.agentic-workflow/goals/G01/milestones/M02-v1.yaml` bleibt nach Bestätigung unverändert. Eine inhaltliche Änderung erzeugt nach Prüfung eine neue `M02-v2.yaml`; ihre Auswahl im Index benötigt ausdrückliche Bestätigung. Ein bloß vorhandenes oder höher nummeriertes Artefakt ist nicht ausgewählt. Ein Plan wie `plan-G01-M02-v1-p01.md` pinnt Ziel, Index, ID, Version und Definitionspfad. Für v2 wird ein neuer Plan bestätigt, zum Beispiel `plan-G01-M02-v2-p01.md`; ein Ersatzplan derselben Version erhöht `p`, etwa auf `p02`. Ein eigenständiger neuer Ausführungslauf erhöht `r` (z. B. `run-G01-M02-v2-p01-r01/`); Resume und Review-Reparaturen behalten exakt dieselbe Run-ID. Taskversuche bleiben getrennte, unveränderliche Kennungen, zum Beispiel `tasks/T01/attempt-01.yaml`. Nummern, Dateinamen und Änderungsdatum ersetzen keine exakten Referenzen oder Freigaben.

Der Versionswechsel überträgt weder Planbindung noch historischen Erfolg: v1-Abschlussbelege verbleiben bei v1. Wiederverwendung für v2 setzt ausdrückliche Prüfung gegen die neuen Kriterien und Abhängigkeiten voraus; bis dahin ist v2 nicht abgeschlossen. Abhängige Etappen bleiben mit alten Versionsbezügen gebunden und für aktive Folgearbeit blockiert, bis passende Ersatzdefinitionen bestätigt sind. Eine neue Version gibt keine Folgeetappe frei. Ein laufender Run wird nicht automatisch umgebunden; nötigenfalls braucht es einen bestätigten Ersatzplan. Das frühere `milestone/v1` bleibt unter dem ausdrücklich benannten Pfad lesbar, wird aber weder automatisch migriert noch mit den getrennten Formaten vermischt. `core-handoff` überträgt exakte Ziel-, Index-, Definitions-, Plan- und einschlägige Runpfade; ein Startprompt oder Handoff ist keine Freigabe.

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

Nach Repository- und Stackinventur, aber vor dem Schreiben des verwalteten `AGENTS.md`-Blocks, lädt `core-init-project` den mitgelieferten `gortex-serena-configurator` inline. Er wird nicht als Subagent dispatcht und erzeugt keinen eigenen Workflowzustand.

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

## 18. MCP-Prüfung und APM

Aktuelle APM-Versionen können MCP-Abhängigkeiten in `apm.yml` deklarieren und pro Zielharness materialisieren. Das frühere pauschale Verbot, MCP-Konfiguration über das Paketmanifest zu verwalten, ist daher überholt.

Verbindliche Aufteilung:

- `apm.yml` kann portable, ausdrücklich geprüfte MCP-Abhängigkeiten und Tool-Allowlisten deklarieren; diese Deklaration ist keine Voraussetzung für die Providerbestandsprüfung.
- `core-init-mcps` prüft ausschließlich read-only bereits vorhandene Provider des benannten Harnesses und berichtet beobachtete Bereitschaft sowie Lücken. Es installiert, aktiviert oder konfiguriert nichts und ändert weder Harness- noch Paketdateien.
- Fehlende Provider oder Credentials werden gemeldet, nicht gesucht oder eingerichtet. Ein passender Installationsskill kann benannt werden, wird aber nicht automatisch ausgeführt.
- Provider-spezifische Projektinitialisierung, etwa Gortex-Tracking oder Serena-Sprachen, bleibt ein eigener, ausdrücklich autorisierter Schritt und erfolgt nie stillschweigend.
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
| --- | --- |
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
| MCP-Prüfung und APM-Deklaration vermischen | APM-Deklarationen sind separat; `core-init-mcps` prüft vorhandene Provider read-only und ändert keine Konfiguration |
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
15. `gortex-serena-configurator` vollständig aus `.apm/skills/` mitgeliefert, quellgebunden geprüft und ohne private Paketabhängigkeit installiert wird,
16. `core-init-project` den `gortex-serena-configurator` inline und ohne konkurrierenden `AGENTS.md`-Schreiber verwendet,
17. alle neu verfassten paketeigenen Markdown-Dateien von Skills und Workflows auf Deutsch verfasst sind; die quelltreue englische Konfigurator-Migration bleibt als dokumentierte Ausnahme erhalten,
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

Die kanonische Fachbasis liegt in [core-architecture/references/design-baseline.md](.apm/skills/core-architecture/references/design-baseline.md), die Vertiefungen in den dort direkt ausgewählten paketinternen Referenzen. `core-plan` wendet S00 bei Coding-Vorhaben bereits an Lösungswahl, Taskgrenzen, `context_paths` und überprüfbarer Akzeptanz-/Checkabdeckung an. `core-execute` prüft S00 direkt an den tatsächlich betroffenen Strukturen und Verträgen, übergibt Referenz und zuständigen Fachskill und verlangt den Nachweis in vorhandenen Ergebnisfeldern. Der zuständige Coding-Skill wendet die SWE-Grundsätze vor der ersten Codeänderung auf den betroffenen Bereich an und prüft ihn zum Abschluss; Clairvoyance-Diagnosen werden ausschließlich durch belegte Struktur- oder Vertragssignale ausgelöst. Ein Referenzladen aktiviert keinen Architekturworkflow. Agentendefinitionen bleiben kurze Eigentümer-Skill-Verweise; core-shared enthält keine Designfachmethodik.

Die fünf S00-Prinzipien sind ein verbindlicher Sollzustand für Code, Tools, Pakete, Einrichtung und Automation; Plan und Execute legen Komponenten, Verträge und Nachweise fest und kontrollieren sie in vorhandenen Ergebnisfeldern. Austauschbarkeit bedeutet, dass eine vertragskonforme Alternative bei stabilem Vertrag ohne Anpassung unabhängiger Verbraucher eingesetzt werden kann, und bedeutsame Werte liegen als benannte Konstante beim verantwortlichen Eigentümer. Es gilt keine Pflicht zu Interfaces, MVC oder Dateigrößenquoten; reine Informations- oder Bereitschaftsprüfungen bleiben read-only und lösen keinen Vollscan oder keine Installation aus. Die ausführliche [Hintergrundreferenz](.apm/skills/core-architecture/references/principles-background.md) dokumentiert Herkunft, Prinzipienbild und Nachweisgrenzen; dieses Dokument verweist darauf, anstatt die Methodik zu duplizieren. Die M02-Erweiterung (Habit Hooks) bleibt eine getrennte, bis zur Folgefreigabe inaktive Etappe und ist nicht Bestandteil dieser Designbasis.

Boundary-/Abstraktionsdiagnose, Schnittstellen-/Fehlerprüfung, Designentwicklung/Vertragsklarheit und Alternativenvergleich teilen kanonische Methoden, keine kopierten Komplettworkflows. Warnzeichen werden erst mit Quelle, Ursache und Wirkung zum Finding. Legitime Adapter, öffentliche Datenverträge und notwendige fachliche Kopplung bleiben möglich. Fehlende Evidenz bleibt eine Lücke; neue Refactorings benötigen den bestätigten Task und sein Safety Net.

[Provenienz und vollständiges Quellenmapping](.apm/skills/core-architecture/PROVENANCE.md) sowie [MIT-Hinweise](.apm/skills/core-architecture/THIRD_PARTY_NOTICES.md) sichern die Clairvoyance-Adaptionen. Die Umsetzung erzeugt keine externen Skill-Laufzeitabhängigkeiten und übernimmt den privaten UNLICENSED-SWE-Skill nicht.

[Toolrouting](.apm/skills/core-shared/references/tool-routing.md) bestimmt benötigte Operationen aus dem Task und prüft relevante aktuelle Fähigkeiten über Laufzeitdeklarationen und gezielte Discovery. Weitere passende Provider dürfen innerhalb bestehender Prioritäts-, Projekt-, Freshness- und Autorisierungsgrenzen genutzt werden. Keine pauschale MCP-Inventarisierung, kein automatisches Provisionieren und kein blinder Retry möglicherweise ausgeführter Mutationen. Erlaubte Fallbacks und fehlende Pflichtfähigkeiten werden sichtbar berichtet.

Skill-Creator und Context-Debloater sind lokale Authoring-Werkzeuge, keine neuen Paketabhängigkeiten. Statische Struktur-/Routingprüfungen belegen kein beobachtetes Laufzeitverhalten und keine Token-, Kosten- oder Latenzersparnis. Statische Prüfungen und kontrollierte Beispieltests sind auch kein Nachweis dafür, dass ein Sprachmodell die Regeln befolgt, und begründen keine allgemeine Leistungs- oder Qualitätsverbesserung.

## 25. Konkrete Repositoryautomation: mise, CI und Releases

`mise.toml` stellt `tools:setup`, `check`, `version:check`, `release:test`, `workflows:check`, `docs:check` und `acceptance` als gemeinsame lokale/CI-Einstiegspunkte bereit. Setup installiert die gepinnten Werkzeuge nur in einen isolierten Arbeitsbereich; die Prüfaufgaben installieren nicht automatisch. `acceptance` umfasst nach den Prüfungen den isolierten Producer-Paketbau und die Scratch-Installation des ZIPs als Verbraucher. Die bestätigte Toolchain ist auf Linux x64 geprüft; daraus folgt keine plattformübergreifende Laufzeitgarantie.

`.github/workflows/ci.yaml` führt die gemeinsamen Aufgaben bei Pull Requests und Pushes auf `main` mit lesendem `GITHUB_TOKEN` aus, ohne App-Schlüssel. `.github/workflows/release.yaml` ist davon getrennt: Zwei unabhängige Repositorygates (`RELEASE_PR_AUTOMATION_ENABLED` und `RELEASE_PUBLICATION_ENABLED`, jeweils nur exakt `true`) schalten Release-PR-Erzeugung und Veröffentlichung frei. Release Please erzeugt nur Release-PRs. Veröffentlichung verlangt einen von einem konfigurierten Maintainer gemergten Release-PR, passende Checks für exakte Commits und die Paketabnahme des exakten Merge-Commits; es gibt keinen Bot-Bypass und kein automatisches Merge. Eine gemeinsame GitHub App wird außerhalb des Repositories installiert und nur für das Repository freigeschaltet; `APP_CLIENT_ID`, `RELEASE_BOT_LOGIN`, `RELEASE_MAINTAINERS` und `RELEASE_REQUIRED_CHECKS` sind Repositoryvariablen, `APP_PRIVATE_KEY` ist ein Repositorysecret. Kurzlebige, repo-begrenzte App-Tokens werden erst für den jeweiligen privilegierten Abschnitt angefordert und dort widerrufen. Ein App-Schlüssel wird nicht automatisch rotiert.

Die Release-Concurrency-Gruppe verwendet `cancel-in-progress: false`, garantiert aber keine unbegrenzte Warteschlange: Ein neuer wartender Lauf kann einen älteren wartenden Lauf ersetzen. Falls ein Original-Release-Lauf für den korrekten Quell-SHA existiert, ist ein vollständiger Retry (`Re-run all jobs` oder `gh run rerun <run-id>`, ohne `--failed`) der vorgesehene Wiederholungspfad: Er verwendet denselben ursprünglichen `GITHUB_SHA`/`GITHUB_REF`, baut das Paket neu, prüft die Provider-/Paketgates erneut und mintet Tokens erneut. Der `release-pr`-Job prüft zusätzlich, ob dieser SHA noch der Tip von `main` ist; ein veralteter Tip wird übersprungen und braucht einen passenden aktuellen regulären CI-/Release-Lauf. GitHub begrenzt Wiederholungen auf 30 Tage und 50 Versuche und verwendet die Berechtigungen des ursprünglichen Auslösers. Das Workflowpaketartefakt läuft nach einem Tag ab; ein Retry baut neu statt es als Dauerbeleg wiederzuverwenden. Tags und Assets werden nicht überschrieben; nur identische, verifizierte Ergebnisse sind wiederholbar. Die konkrete GitHub-Laufzeit, App-Einrichtung, Repositoryregeln und Secrets bleiben externe, noch separat zu prüfende Voraussetzungen.

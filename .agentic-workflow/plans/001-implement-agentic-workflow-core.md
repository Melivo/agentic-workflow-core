# Agentic Workflow Core als APM-Paket implementieren

> Das finale `DESIGN.md` in ein schlankes, portable APM-Paket mit vier ineinandergreifenden Kernworkflows überführen.

**Status:** Confirmed
**Erstellt:** 2026-09-27
**Designgrundlage:** [`DESIGN.md`](../../DESIGN.md)
**Schema:** `plan/v1`

## Ziel

Ein installierbares APM-Paket bereitstellen, dessen Kernablauf `core-brainstorm? → core-plan → core-execute ↔ core-review` ohne konkurrierende Orchestratoren funktioniert. Es verwendet Gortex primär, Context7 und YouTube Transcript gezielt, Serena als projektbezogenen Informations- und Code-Fallback sowie Honcho ausschließlich als nicht autoritative semantische Erinnerung.

## Scope

- `apm.yml`, paketinterne Skills, Shared Kernel und bestehende Fachagenten vervollständigen.
- Die vier Kernworkflows, `init-project`, `init-mcps`, `user2agent-instructions`, `repo-audit` und `scm` als Skills implementieren.
- Fachskills für alle bereits vorhandenen Agenten anlegen.
- Plan-/Run-Artefakte, Workflowkatalog, deutsche Markdown-Konvention und die Authoring-Gates umsetzen.
- APM- und Paketvalidierung vorbereiten.

## Nicht-Ziele

- Produktcode, Deployment, Releases oder automatische SCM-Aktionen.
- Alternative Workflows oder Kompatibilitätsaliase (`work`, `orchestrate`, `ultrawork`, `ralph`, `exec-plan`, `prime`).
- Ein persistenter Orchestrator, Memory-Board, Eventbus oder Digest-Mechanismus.
- Eigene Subagenten-Dispatches durch Fachagenten.
- Builds, Bundles oder Packages ohne spätere ausdrückliche Buildautorisierung.

## Repositorybefund

- `DESIGN.md` ist die verbindliche Architekturquelle.
- `.apm/agents/` enthält bereits zwölf kanonische Fachagenten.
- `apm.yml`, das erste paketeigene Bundle `.apm/skills/core-shared/`, `.agentic-workflow/` und ein Root-`README.md` fehlen.
- `.gitignore` ignoriert derzeit `docs/plans/`, nicht aber den im Design festgelegten temporären Run-Pfad.
- Die Planung wird deshalb als versionierbares Artefakt unter `.agentic-workflow/plans/` angelegt; nur `.agentic-workflow/runs/` wird später ignoriert.

## Verbindliche Entscheidungen

| ID | Entscheidung |
|---|---|
| D01 | Nur `execute` implementiert und orchestriert Planaufgaben. |
| D02 | Jeder Fachagent bearbeitet genau einen zugewiesenen Task und startet niemals eigene Subagenten. |
| D03 | `.apm/` ist die einzige kanonische Paketquelle; generierte Harness-Projektionen werden nicht editiert. |
| D04 | `gortex-serena-configurator` wird als virtuelle APM-Unterverzeichnis-Abhängigkeit eingebunden. |
| D05 | `skill-creator` und `context-debloater` sind lokale Authoring-Gates, keine Paketabhängigkeiten. |
| D06 | Alle paketeigenen Skill- und Workflow-Markdown-Dateien sind deutsch; technische Schlüssel bleiben unverändert. |
| D07 | Bestätigte Pläne liegen unter `.agentic-workflow/plans/`, Runzustand ausschließlich unter `.agentic-workflow/runs/<run-id>/`. |
| D08 | Context7, YouTube Transcript, Serena und Honcho bleiben innerhalb der in `DESIGN.md` definierten Rollen. |
| D09 | Jedes neu erstellte paketeigene Skillbundle verwendet Verzeichnis und Frontmatter `core-<name>`; das Bundle liegt unter `.apm/skills/core-shared/` mit `name: core-shared`, externe Abhängigkeiten bleiben unverändert. |

## Ausführungsreihenfolge

```text
T01 → T02 → T03 ┬→ T09 ─┐
                ├→ T04 → T09 ┤
                ├→ T05 → T09 ┤
                ├→ T06 → T09 ┤
                ├→ T07 → T09 ┤
                ├→ T08 → T09 ┤
                ├→ T10 ──────┼→ T14 → T15
                ├→ T11 ──────┤
                ├→ T12 ──────┤
                ├→ T13 ──────┤
                └→ T17 ──────┘
```

## Aufgaben

```yaml
schema: plan/v1
status: Confirmed

tasks:
  - id: T01
    title: Paketmanifest und Artefaktgrenzen etablieren
    agent: docs-curator
    task: >
      Erstelle das APM-Manifest mit der einzigen virtuellen Abhängigkeit
      `Melivo/apm-package/skills/gortex-serena-configurator`. Ergänze die
      Repositorymetadaten und `.gitignore` so, dass bestätigte Pläne unter
      `.agentic-workflow/plans/` versionierbar bleiben und nur temporäre
      Run-Artefakte ignoriert werden. Ändere keine generierten Harness-Dateien.
    context_paths: [DESIGN.md, .gitignore, .apm/agents/]
    scope: [apm.yml, .gitignore, README.md]
    dependencies: []
    required_mcps: [gortex]
    optional_mcps: [context7]
    acceptance:
      - id: AC01
        description: apm.yml deklariert ausschließlich die definierte APM-Abhängigkeit.
      - id: AC02
        description: .agentic-workflow/runs/ ist ignoriert; .agentic-workflow/plans/ bleibt versionierbar.
      - id: AC03
        description: README beschreibt Installation, Paketgrenzen und ausdrückliche Autorisierungsgrenzen.
    checks:
      - id: CK01
        covers: [AC01, AC02, AC03]
        command: ["python3", "-c", "from pathlib import Path; import os; dependency='Melivo/apm-package/skills/gortex-serena-configurator'; files=[Path('apm.yml'),Path('.gitignore'),Path('README.md')]; assert all(p.is_file() for p in files),[str(p) for p in files if not p.is_file()]; manifest=files[0].read_text(); expected=['name: agentic-workflow-core','version: \"0.1.0\"','description: Leaner Workflow-Kern für planbasierte Multi-Agenten-Arbeit mit OpenCode und Codex.','author: Melivo','targets: [opencode, codex]','includes: auto','dependencies:','  apm:','    - '+dependency]; assert manifest.splitlines()==expected,manifest.splitlines(); active=[line.strip() for line in files[1].read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]; workflow_ignores=[line for line in active if not line.startswith('!') and line.startswith('.agentic-workflow')]; assert workflow_ignores==['.agentic-workflow/runs/'],workflow_ignores; readme=files[2].read_text(); required=['## Voraussetzungen','Microsoft Agent Package Manager (APM)','ein unterstütztes Zielharness (OpenCode oder Codex)','## Installation','apm install Melivo/agentic-workflow-core --target opencode,codex','## Namens- und Paketvertrag','Die kanonische Paketquelle liegt unter `.apm/`','generierte Projektionen','## Autorisierungsgrenzen','nur nach ausdrücklicher Freigabe']; missing=[token for token in required if token not in readme]; assert not missing,missing; probe=os.environ.get('AWC_CK01_WHITESPACE_PROBE'); checked=files+([Path(probe)] if probe else []); assert all(p.is_file() for p in checked),[str(p) for p in checked if not p.is_file()]; bad=[f'{p}:{number}' for p in checked for number,line in enumerate(p.read_text().splitlines(keepends=True),1) if line.rstrip(chr(13)+chr(10)).endswith((' ',chr(9)))]; assert not bad,bad"]
        cwd: "."
        pass: "Keine Whitespace-Fehler; Manifest, Ignore-Regel und README stimmen mit DESIGN.md überein."

  - id: T02
    title: Shared Workflow Kernel und Artefaktverträge anlegen
    agent: architecture-reviewer
    task: >
      Erstelle das `core-shared`-Skillbundle einschließlich kurzem SKILL.md,
      Workflow-, Artefakt-, Toolrouting-, Verifikations- und
      Benutzeranweisungsvertrag. Lege den minimalen Workflowkatalog sowie
      Handoff- und Findingvorlagen an. Halte alle Dateien deutsch und
      vermeide eine zweite Orchestrierungs- oder Statusquelle.
    context_paths: [DESIGN.md, .apm/agents/]
    scope: [.apm/skills/core-shared/]
    dependencies: [T01]
    required_mcps: [gortex]
    optional_mcps: []
    acceptance:
      - id: AC04
        description: Alle Shared-Verträge und Vorlagen aus DESIGN.md existieren einmalig.
      - id: AC05
        description: workflow-catalog.yaml enthält nur Routing- und Validierungsmetadaten.
      - id: AC06
        description: Handoff- und Findingformate unterstützen frische Kontexte und reproduzierbare Review-Findings.
    checks:
      - id: CK02
        covers: [AC04, AC05, AC06]
        command: ["python3", "/home/visimeos/.opencode/skills/skill-creator/scripts/quick_validate.py", ".apm/skills/core-shared"]
        cwd: "."
        pass: "Skillstruktur valide; alle Referenzen und Assets sind auflösbar."
      - id: CK03
        covers: [AC04, AC05, AC06]
        command: ["python3", "-c", "from pathlib import Path; import json,subprocess; root=Path('.apm/skills/core-shared'); files=[str(p) for p in root.rglob('*.md')]; subprocess.run(['python3','/home/visimeos/.opencode/skills/context-debloater/scripts/analyze_markdown.py'],input=json.dumps({'workspace':str(Path.cwd()),'targets':files}),text=True,check=True)"]
        cwd: "."
        pass: "Report-only Prüfung aller geänderten core-shared-Markdown-Dateien liegt vor."

  - id: T03
    title: Brainstorm- und Plan-Skills implementieren
    agent: pm-planner
    task: >
      Erstelle die deutschen Skills `brainstorm` und `plan`. Der Plan-Skill
      erzeugt genau einen bestätigten plan/v1-Plan unter
      .agentic-workflow/plans und trennt Kontextpfade, Schreibscopes,
      Abhängigkeiten, Akzeptanzkriterien und Checks. Er verwendet Gortex
      für Repositoryevidenz und aktiviert externe Recherche nur bei
      materieller Wissenslücke.
    context_paths: [DESIGN.md, .apm/skills/core-shared/, .apm/agents/pm-planner.agent.md]
    scope: [.apm/skills/core-brainstorm/, .apm/skills/core-plan/]
    dependencies: [T02]
    required_mcps: [gortex]
    optional_mcps: [context7, youtube-transcript]
    acceptance:
      - id: AC07
        description: brainstorm ist optional und übergibt nur bestätigte Entscheidungen an plan.
      - id: AC08
        description: plan erstellt einen plan/v1-Graphen ohne Priority Tiers oder parallele Planformate.
      - id: AC09
        description: Research-Hierarchie und Context7-/YouTube-Grenzen entsprechen DESIGN.md.
    checks:
      - id: CK04
        covers: [AC07, AC08, AC09]
        command: ["python3", "-c", "from pathlib import Path; import subprocess; roots=[Path('.apm/skills/core-brainstorm'),Path('.apm/skills/core-plan')]; [subprocess.run(['python3','/home/visimeos/.opencode/skills/skill-creator/scripts/quick_validate.py',str(r)],check=True) for r in roots]"]
        cwd: "."
        pass: "Beide Skillbundles sind strukturell valide."
      - id: CK05
        covers: [AC07, AC08, AC09]
        command: ["python3", "-c", "from pathlib import Path; import json,subprocess; roots=[Path('.apm/skills/core-brainstorm'),Path('.apm/skills/core-plan')]; files=[str(p) for r in roots for p in r.rglob('*.md')]; subprocess.run(['python3','/home/visimeos/.opencode/skills/context-debloater/scripts/analyze_markdown.py'],input=json.dumps({'workspace':str(Path.cwd()),'targets':files}),text=True,check=True)"]
        cwd: "."
        pass: "Report-only Debloat-Prüfung aller neu geschriebenen Markdown-Dateien liegt vor."

  - id: T04
    title: Execute- und Debug-Skills implementieren
    agent: debug-investigator
    task: >
      Erstelle `execute` und `debug`. execute validiert bestätigte Pläne,
      prüft Drift, dispatcht nur selbst, integriert serialisiert und nutzt
      Debugging bei unklarer Ursache als Fachstrategie. Implementiere die
      zwei Runden begrenzte execute-review-Reparaturschleife und verbiete
      Subagenten-Dispatch durch alle Fachagenten explizit.
    context_paths: [DESIGN.md, .apm/skills/core-shared/, .apm/agents/debug-investigator.agent.md]
    scope: [.apm/skills/core-execute/, .apm/skills/core-debug/]
    dependencies: [T02]
    required_mcps: [gortex]
    optional_mcps: []
    acceptance:
      - id: AC10
        description: execute ist der einzige Ausführungsworkflow und akzeptiert nur einen expliziten Confirmed-Planpfad.
      - id: AC11
        description: Taskresultat, Drift, Scopeprüfung, Resume und serialisierte Integration folgen den Shared-Verträgen.
      - id: AC12
        description: Debugging ist kein separater öffentlicher Workflow und Fachagenten können keine Subagenten starten.
    checks:
      - id: CK06
        covers: [AC10, AC11, AC12]
        command: ["python3", "-c", "from pathlib import Path; import subprocess; roots=[Path('.apm/skills/core-execute'),Path('.apm/skills/core-debug')]; [subprocess.run(['python3','/home/visimeos/.opencode/skills/skill-creator/scripts/quick_validate.py',str(r)],check=True) for r in roots]"]
        cwd: "."
        pass: "Beide Skillbundles sind strukturell valide."
      - id: CK07
        covers: [AC10, AC11, AC12]
        command: ["python3", "-c", "from pathlib import Path; import json,subprocess; roots=[Path('.apm/skills/core-execute'),Path('.apm/skills/core-debug')]; files=[str(p) for r in roots for p in r.rglob('*.md')]; subprocess.run(['python3','/home/visimeos/.opencode/skills/context-debloater/scripts/analyze_markdown.py'],input=json.dumps({'workspace':str(Path.cwd()),'targets':files}),text=True,check=True)"]
        cwd: "."
        pass: "Report-only Debloat-Prüfung aller neu geschriebenen Markdown-Dateien liegt vor."

  - id: T05
    title: Review- und QA-Methode implementieren
    agent: qa-reviewer
    task: >
      Erstelle den deutschen review-Skill mit frischem Reviewkontext,
      risikobasierter Prüfauswahl, review/v1-Findingvertrag und einem
      unabhängigen pass-, changes_requested- oder blocked-Urteil. Übernimm
      QA als interne Fachmethode, nicht als separaten Workflow.
    context_paths: [DESIGN.md, .apm/skills/core-shared/, .apm/agents/qa-reviewer.agent.md]
    scope: [.apm/skills/core-review/]
    dependencies: [T02]
    required_mcps: [gortex]
    optional_mcps: [context7]
    acceptance:
      - id: AC13
        description: review implementiert keine Fixes und erzeugt nur evidenzbasierte Findings.
      - id: AC14
        description: Findingformat, Schweregrade und materielle Rückgabe an plan entsprechen DESIGN.md.
      - id: AC15
        description: Fachprüfungen werden nach Relevanz statt als pauschaler Toolkatalog gewählt.
    checks:
      - id: CK08
        covers: [AC13, AC14, AC15]
        command: ["python3", "/home/visimeos/.opencode/skills/skill-creator/scripts/quick_validate.py", ".apm/skills/core-review"]
        cwd: "."
        pass: "Review-Skill ist strukturell valide."
      - id: CK09
        covers: [AC13, AC14, AC15]
        command: ["python3", "-c", "from pathlib import Path; import json,subprocess; root=Path('.apm/skills/core-review'); files=[str(p) for p in root.rglob('*.md')]; subprocess.run(['python3','/home/visimeos/.opencode/skills/context-debloater/scripts/analyze_markdown.py'],input=json.dumps({'workspace':str(Path.cwd()),'targets':files}),text=True,check=True)"]
        cwd: "."
        pass: "Report-only Debloat-Prüfung aller neu geschriebenen Markdown-Dateien liegt vor."

  - id: T06
    title: Projektinit und Benutzeranweisungsverwaltung implementieren
    agent: docs-curator
    task: >
      Erstelle `init-project` und `user2agent-instructions`. init-project
      erzeugt den kleinen Repository-Preflight und verwendet
      gortex-serena-configurator inline für Readiness, ohne dessen
      AGENTS-Schreibmodus zu aktivieren. Die Benutzeranweisungsverwaltung
      übernimmt nur nach exakter Vorschau und expliziter Bestätigung
      manuelle globale Einträge nach Projekt-AGENTS.md.
    context_paths: [DESIGN.md, .apm/skills/core-shared/, .apm/agents/docs-curator.agent.md]
    scope: [.apm/skills/core-init-project/, .apm/skills/core-user2agent-instructions/]
    dependencies: [T02]
    required_mcps: [gortex]
    optional_mcps: [serena]
    acceptance:
      - id: AC16
        description: init-project besitzt den Preflight, bewahrte manuelle Inhalte und einen idempotenten verwalteten Block.
      - id: AC17
        description: Gortex-Tracking ist optional und explizit; Serena bleibt projektbegrenzt.
      - id: AC18
        description: user2agent-instructions schützt generierte Blöcke und verlangt eine Diff-Bestätigung.
    checks:
      - id: CK10
        covers: [AC16, AC17, AC18]
        command: ["python3", "-c", "from pathlib import Path; import subprocess; roots=[Path('.apm/skills/core-init-project'),Path('.apm/skills/core-user2agent-instructions')]; [subprocess.run(['python3','/home/visimeos/.opencode/skills/skill-creator/scripts/quick_validate.py',str(r)],check=True) for r in roots]"]
        cwd: "."
        pass: "Beide Skillbundles sind strukturell valide."
      - id: CK11
        covers: [AC16, AC17, AC18]
        command: ["python3", "-c", "from pathlib import Path; import json,subprocess; roots=[Path('.apm/skills/core-init-project'),Path('.apm/skills/core-user2agent-instructions')]; files=[str(p) for r in roots for p in r.rglob('*.md')]; subprocess.run(['python3','/home/visimeos/.opencode/skills/context-debloater/scripts/analyze_markdown.py'],input=json.dumps({'workspace':str(Path.cwd()),'targets':files}),text=True,check=True)"]
        cwd: "."
        pass: "Report-only Debloat-Prüfung aller neu geschriebenen Markdown-Dateien liegt vor."

  - id: T07
    title: MCP-Initialisierung und Research-Skill implementieren
    agent: research-explorer
    task: >
      Erstelle `init-mcps` und `research`. init-mcps trennt portable
      Manifestdeklarationen von umgebungsabhängiger Einrichtung, Credentials
      und Health-Checks. research routet Repositoryfragen an Gortex, externe
      Dokumentation an Context7, bekannte Videos an YouTube Transcript und
      Serena nur für projektspezifische Informationssuche.
    context_paths: [DESIGN.md, .apm/skills/core-shared/, .apm/agents/research-explorer.agent.md]
    scope: [.apm/skills/core-init-mcps/, .apm/skills/core-research/]
    dependencies: [T02]
    required_mcps: [context7]
    optional_mcps: [gortex, youtube-transcript, serena]
    acceptance:
      - id: AC19
        description: init-mcps schreibt keine Secrets und konfiguriert Provider nicht stillschweigend.
      - id: AC20
        description: research dokumentiert Vertrauensniveau, Quellen und offene Evidenzlücken.
      - id: AC21
        description: Context7-, YouTube- und Serena-Grenzen entsprechen DESIGN.md.
    checks:
      - id: CK12
        covers: [AC19, AC20, AC21]
        command: ["python3", "-c", "from pathlib import Path; import subprocess; roots=[Path('.apm/skills/core-init-mcps'),Path('.apm/skills/core-research')]; [subprocess.run(['python3','/home/visimeos/.opencode/skills/skill-creator/scripts/quick_validate.py',str(r)],check=True) for r in roots]"]
        cwd: "."
        pass: "Beide Skillbundles sind strukturell valide."
      - id: CK13
        covers: [AC19, AC20, AC21]
        command: ["python3", "-c", "from pathlib import Path; import json,subprocess; roots=[Path('.apm/skills/core-init-mcps'),Path('.apm/skills/core-research')]; files=[str(p) for r in roots for p in r.rglob('*.md')]; subprocess.run(['python3','/home/visimeos/.opencode/skills/context-debloater/scripts/analyze_markdown.py'],input=json.dumps({'workspace':str(Path.cwd()),'targets':files}),text=True,check=True)"]
        cwd: "."
        pass: "Report-only Debloat-Prüfung aller neu geschriebenen Markdown-Dateien liegt vor."

  - id: T08
    title: SCM- und Repository-Audit-Skills implementieren
    agent: docs-curator
    task: >
      Erstelle `scm` und `repo-audit`. scm trennt inspect, commit, branch,
      worktree, merge, rebase, push und release mit ausdrücklichen
      Autorisierungsgrenzen. repo-audit ist standardmäßig read-only und
      liefert nur belegte Hygiene-, Public-Readiness- und
      .gitignore-Vorschläge.
    context_paths: [DESIGN.md, .apm/skills/core-shared/, .apm/agents/docs-curator.agent.md]
    scope: [.apm/skills/core-scm/, .apm/skills/core-repo-audit/]
    dependencies: [T02]
    required_mcps: [gortex]
    optional_mcps: []
    acceptance:
      - id: AC22
        description: scm autorisiert Commit, Push, Tag und Release getrennt.
      - id: AC23
        description: repo-audit verändert Dateien oder Index nie ohne neue ausdrückliche Autorisierung.
    checks:
      - id: CK14
        covers: [AC22, AC23]
        command: ["python3", "-c", "from pathlib import Path; import subprocess; roots=[Path('.apm/skills/core-scm'),Path('.apm/skills/core-repo-audit')]; [subprocess.run(['python3','/home/visimeos/.opencode/skills/skill-creator/scripts/quick_validate.py',str(r)],check=True) for r in roots]"]
        cwd: "."
        pass: "Beide Skillbundles sind strukturell valide."
      - id: CK15
        covers: [AC22, AC23]
        command: ["python3", "-c", "from pathlib import Path; import json,subprocess; roots=[Path('.apm/skills/core-scm'),Path('.apm/skills/core-repo-audit')]; files=[str(p) for r in roots for p in r.rglob('*.md')]; subprocess.run(['python3','/home/visimeos/.opencode/skills/context-debloater/scripts/analyze_markdown.py'],input=json.dumps({'workspace':str(Path.cwd()),'targets':files}),text=True,check=True)"]
        cwd: "."
        pass: "Report-only Debloat-Prüfung aller neu geschriebenen Markdown-Dateien liegt vor."

  - id: T09
    title: Agentenverträge mit den neuen Skills harmonisieren
    agent: architecture-reviewer
    task: >
      Aktualisiere die zwölf vorhandenen APM-Agentendefinitionen minimal auf
      die finalen deutschen Owner-Skills, Ein- und Ausgangsverträge,
      Scopegrenzen und das strikte Verbot eigener Subagenten. Kopiere keine
      Fachmethodik aus den Skills in Agenten hinein.
    context_paths: [DESIGN.md, .apm/agents/, .apm/skills/core-architecture/, .apm/skills/core-backend/, .apm/skills/core-brainstorm/, .apm/skills/core-database/, .apm/skills/core-debug/, .apm/skills/core-docs/, .apm/skills/core-execute/, .apm/skills/core-frontend/, .apm/skills/core-init-mcps/, .apm/skills/core-init-project/, .apm/skills/core-mobile/, .apm/skills/core-plan/, .apm/skills/core-refactor/, .apm/skills/core-repo-audit/, .apm/skills/core-research/, .apm/skills/core-review/, .apm/skills/core-scm/, .apm/skills/core-shared/, .apm/skills/core-tf-infra/, .apm/skills/core-user2agent-instructions/]
    scope: [.apm/agents/]
    dependencies: [T03, T04, T05, T06, T07, T08, T10, T11, T12, T13, T17]
    required_mcps: [gortex]
    optional_mcps: []
    acceptance:
      - id: AC24
        description: Jeder Agent referenziert einen vorhandenen Owner-Skill und bleibt unter 300 Zeilen.
      - id: AC25
        description: Jeder Agent verbietet Scopeausweitung und eigene Subagenten.
      - id: AC26
        description: Kein Agent dupliziert ausführliche Skillreferenzen oder besitzt Workflowzustand.
    checks:
      - id: CK16
        covers: [AC24, AC25, AC26]
        command: ["python3", "-c", "from pathlib import Path; import json,subprocess; files=[str(p) for p in sorted(Path('.apm/agents').glob('*.agent.md'))]; subprocess.run(['python3','/home/visimeos/.opencode/skills/context-debloater/scripts/analyze_markdown.py'],input=json.dumps({'workspace':str(Path.cwd()),'targets':files}),text=True,check=True)"]
        cwd: "."
        pass: "Report-only Prüfung aller geänderten Agenten-Markdown-Dateien liegt vor."

  - id: T10
    title: Architektur- und Refactoring-Skills implementieren
    agent: refactor-engineer
    task: >
      Erstelle die deutschen Skills `architecture` und `refactor` mit
      Methoden für materielle Boundary-Entscheidungen, Information Hiding,
      Verhaltenserhaltung, Characterization Tests und kleinen überprüfbaren
      Transformationen. Route Bugs und Implementierung an die zuständigen
      bestehenden Workflows und Agenten.
    context_paths: [DESIGN.md, .apm/skills/core-shared/, .apm/agents/architecture-reviewer.agent.md, .apm/agents/refactor-engineer.agent.md]
    scope: [.apm/skills/core-architecture/, .apm/skills/core-refactor/]
    dependencies: [T02]
    required_mcps: [gortex]
    optional_mcps: [context7]
    acceptance:
      - id: AC27
        description: architecture bewertet materialle Entscheidungen proportional und ohne Produktplanung zu duplizieren.
      - id: AC28
        description: refactor trennt Verhaltenserhaltung von Feature- und Bugfixarbeit.
    checks:
      - id: CK17
        covers: [AC27, AC28]
        command: ["python3", "-c", "from pathlib import Path; import subprocess; roots=[Path('.apm/skills/core-architecture'),Path('.apm/skills/core-refactor')]; [subprocess.run(['python3','/home/visimeos/.opencode/skills/skill-creator/scripts/quick_validate.py',str(r)],check=True) for r in roots]"]
        cwd: "."
        pass: "Beide Skillbundles sind strukturell valide."
      - id: CK18
        covers: [AC27, AC28]
        command: ["python3", "-c", "from pathlib import Path; import json,subprocess; roots=[Path('.apm/skills/core-architecture'),Path('.apm/skills/core-refactor')]; files=[str(p) for r in roots for p in r.rglob('*.md')]; subprocess.run(['python3','/home/visimeos/.opencode/skills/context-debloater/scripts/analyze_markdown.py'],input=json.dumps({'workspace':str(Path.cwd()),'targets':files}),text=True,check=True)"]
        cwd: "."
        pass: "Report-only Debloat-Prüfung aller neu geschriebenen Markdown-Dateien liegt vor."

  - id: T11
    title: Backend- und Datenbank-Skills implementieren
    agent: db-engineer
    task: >
      Erstelle die deutschen Skills `backend` und `database`. Kapsele
      allgemeine Sicherheits-, Validierungs-, Transaktions-, Migrations- und
      Integritätsregeln in bedingt geladene Referenzen. Vermeide starre
      Framework- oder Architekturdefaults.
    context_paths: [DESIGN.md, .apm/skills/core-shared/, .apm/agents/backend-engineer.agent.md, .apm/agents/db-engineer.agent.md]
    scope: [.apm/skills/core-backend/, .apm/skills/core-database/]
    dependencies: [T02]
    required_mcps: [gortex]
    optional_mcps: [context7]
    acceptance:
      - id: AC29
        description: backend und database respektieren bestehende Projektkonventionen vor Paketdefaults.
      - id: AC30
        description: Produktive oder destruktive Datenbankaktionen erfordern ausdrückliche Autorisierung.
    checks:
      - id: CK19
        covers: [AC29, AC30]
        command: ["python3", "-c", "from pathlib import Path; import subprocess; roots=[Path('.apm/skills/core-backend'),Path('.apm/skills/core-database')]; [subprocess.run(['python3','/home/visimeos/.opencode/skills/skill-creator/scripts/quick_validate.py',str(r)],check=True) for r in roots]"]
        cwd: "."
        pass: "Beide Skillbundles sind strukturell valide."
      - id: CK20
        covers: [AC29, AC30]
        command: ["python3", "-c", "from pathlib import Path; import json,subprocess; roots=[Path('.apm/skills/core-backend'),Path('.apm/skills/core-database')]; files=[str(p) for r in roots for p in r.rglob('*.md')]; subprocess.run(['python3','/home/visimeos/.opencode/skills/context-debloater/scripts/analyze_markdown.py'],input=json.dumps({'workspace':str(Path.cwd()),'targets':files}),text=True,check=True)"]
        cwd: "."
        pass: "Report-only Debloat-Prüfung aller neu geschriebenen Markdown-Dateien liegt vor."

  - id: T12
    title: Frontend- und Mobile-Skills implementieren
    agent: mobile-engineer
    task: >
      Erstelle die deutschen Skills `frontend` und `mobile` mit bedingten
      Frameworkreferenzen, Accessibility, Responsive-Verhalten,
      Plattform-Lifecycle und ARB-Source-of-Truth-Regeln. Vorhandene
      Designsysteme und Projektkonventionen haben stets Vorrang.
    context_paths: [DESIGN.md, .apm/skills/core-shared/, .apm/agents/frontend-engineer.agent.md, .apm/agents/mobile-engineer.agent.md]
    scope: [.apm/skills/core-frontend/, .apm/skills/core-mobile/]
    dependencies: [T02]
    required_mcps: [gortex]
    optional_mcps: [context7]
    acceptance:
      - id: AC31
        description: frontend behandelt vorhandenes DESIGN.md als projektspezifische Vorgabe.
      - id: AC32
        description: mobile lädt nur die passende Plattformreferenz und editiert bei ARB nur Quelldateien.
    checks:
      - id: CK21
        covers: [AC31, AC32]
        command: ["python3", "-c", "from pathlib import Path; import subprocess; roots=[Path('.apm/skills/core-frontend'),Path('.apm/skills/core-mobile')]; [subprocess.run(['python3','/home/visimeos/.opencode/skills/skill-creator/scripts/quick_validate.py',str(r)],check=True) for r in roots]"]
        cwd: "."
        pass: "Beide Skillbundles sind strukturell valide."
      - id: CK22
        covers: [AC31, AC32]
        command: ["python3", "-c", "from pathlib import Path; import json,subprocess; roots=[Path('.apm/skills/core-frontend'),Path('.apm/skills/core-mobile')]; files=[str(p) for r in roots for p in r.rglob('*.md')]; subprocess.run(['python3','/home/visimeos/.opencode/skills/context-debloater/scripts/analyze_markdown.py'],input=json.dumps({'workspace':str(Path.cwd()),'targets':files}),text=True,check=True)"]
        cwd: "."
        pass: "Report-only Debloat-Prüfung aller neu geschriebenen Markdown-Dateien liegt vor."

  - id: T13
    title: Terraform-Infrastruktur-Skill implementieren
    agent: tf-infra-engineer
    task: >
      Erstelle den deutschen Skill `tf-infra` und seine bedingten Referenzen.
      Infrastrukturarbeit muss State, Least Privilege, Drift, Kosten und
      Rollback berücksichtigen und apply oder destroy ohne ausdrückliche
      Autorisierung verbieten.
    context_paths: [DESIGN.md, .apm/skills/core-shared/, .apm/agents/tf-infra-engineer.agent.md]
    scope: [.apm/skills/core-tf-infra/]
    dependencies: [T02]
    required_mcps: [gortex]
    optional_mcps: [context7]
    acceptance:
      - id: AC33
        description: tf-infra verbietet apply und destroy ohne ausdrückliche Autorisierung.
    checks:
      - id: CK23
        covers: [AC33]
        command: ["python3", "/home/visimeos/.opencode/skills/skill-creator/scripts/quick_validate.py", ".apm/skills/core-tf-infra"]
        cwd: "."
        pass: "Der Skill ist strukturell valide."
      - id: CK24
        covers: [AC33]
        command: ["python3", "-c", "from pathlib import Path; import json,subprocess; root=Path('.apm/skills/core-tf-infra'); files=[str(p) for p in root.rglob('*.md')]; subprocess.run(['python3','/home/visimeos/.opencode/skills/context-debloater/scripts/analyze_markdown.py'],input=json.dumps({'workspace':str(Path.cwd()),'targets':files}),text=True,check=True)"]
        cwd: "."
        pass: "Report-only Debloat-Prüfung aller neu geschriebenen Markdown-Dateien liegt vor."

  - id: T17
    title: Dokumentations-Skill implementieren
    agent: docs-curator
    task: >
      Erstelle den deutschen Skill `docs` mit evidenzbasierter
      Dokumentationspflege. Er korrigiert nur durch einen Task oder Code-Diff
      nachweislich veraltete Dokumentation, erhält manuelle Inhalte außerhalb
      des Scopes und ändert keinen Produktcode.
    context_paths: [DESIGN.md, .apm/skills/core-shared/, .apm/agents/docs-curator.agent.md]
    scope: [.apm/skills/core-docs/]
    dependencies: [T02]
    required_mcps: [gortex]
    optional_mcps: []
    acceptance:
      - id: AC41
        description: docs aktualisiert nur nachgewiesen veraltete Dokumentation und keine Produktdateien.
    checks:
      - id: CK29
        covers: [AC41]
        command: ["python3", "/home/visimeos/.opencode/skills/skill-creator/scripts/quick_validate.py", ".apm/skills/core-docs"]
        cwd: "."
        pass: "Der Skill ist strukturell valide."
      - id: CK30
        covers: [AC41]
        command: ["python3", "-c", "from pathlib import Path; import json,subprocess; root=Path('.apm/skills/core-docs'); files=[str(p) for p in root.rglob('*.md')]; subprocess.run(['python3','/home/visimeos/.opencode/skills/context-debloater/scripts/analyze_markdown.py'],input=json.dumps({'workspace':str(Path.cwd()),'targets':files}),text=True,check=True)"]
        cwd: "."
        pass: "Report-only Debloat-Prüfung aller neu geschriebenen Markdown-Dateien liegt vor."

  - id: T14
    title: Paketdokumentation, Referenzen und deutsche Sprache prüfen
    agent: docs-curator
    task: >
      Konsolidiere README, Paketdokumentation und interne Skillverweise.
      Prüfe, dass alle paketeigenen Skill- und Workflow-Markdowndateien
      deutsch sind, technische Bezeichner unverändert bleiben und keine
      veralteten alternativen Workflows mehr als aktive Pfade erscheinen.
    context_paths: [DESIGN.md, README.md, .apm/]
    scope: [README.md]
    dependencies: [T03, T04, T05, T06, T07, T08, T10, T11, T12, T13, T17]
    required_mcps: [gortex]
    optional_mcps: []
    acceptance:
      - id: AC35
        description: Paketdokumentation verlinkt nur auf bestehende, kanonische Artefakte.
      - id: AC36
        description: Jede paketeigene Skill- und Workflow-Markdowndatei ist deutsch.
      - id: AC37
        description: Keine aktive Dokumentation empfiehlt work, orchestrate, ultrawork, ralph, exec-plan oder prime.
    checks:
      - id: CK25
        covers: [AC35, AC36, AC37]
        command: ["python3", "-c", "from pathlib import Path; import json,subprocess; roots=[Path('.apm/skills/core-architecture'),Path('.apm/skills/core-backend'),Path('.apm/skills/core-brainstorm'),Path('.apm/skills/core-database'),Path('.apm/skills/core-debug'),Path('.apm/skills/core-docs'),Path('.apm/skills/core-execute'),Path('.apm/skills/core-frontend'),Path('.apm/skills/core-init-mcps'),Path('.apm/skills/core-init-project'),Path('.apm/skills/core-mobile'),Path('.apm/skills/core-plan'),Path('.apm/skills/core-refactor'),Path('.apm/skills/core-repo-audit'),Path('.apm/skills/core-research'),Path('.apm/skills/core-review'),Path('.apm/skills/core-scm'),Path('.apm/skills/core-shared'),Path('.apm/skills/core-tf-infra'),Path('.apm/skills/core-user2agent-instructions')]; files=[str(Path('README.md'))]+[str(p) for r in roots for p in sorted(r.rglob('*.md'))]; subprocess.run(['python3','/home/visimeos/.opencode/skills/context-debloater/scripts/analyze_markdown.py'],input=json.dumps({'workspace':str(Path.cwd()),'targets':files}),text=True,check=True)"]
        cwd: "."
        pass: "Explizite Report-only Prüfung der Dokumentationsziele liegt vor."

  - id: T15
    title: Paket gegen Design und APM-Ausgabe verifizieren
    agent: qa-reviewer
    task: >
      Prüfe das integrierte Paket gegen DESIGN.md: Kanonizität von .apm,
      tote Referenzen, Shared-Verträge, Agenten-Skill-Zuordnungen, deutsche
      Markdown-Dateien, Subagentensperre und Artefaktpfade. Führe APM-
      Validierung, Preview und einen Scratch-Install nur aus, wenn eine
      ausdrückliche Build- beziehungsweise Installationsautorisierung
      vorliegt; ansonsten dokumentiere diese Lücke als blocked.
    context_paths: [DESIGN.md, apm.yml, README.md, .apm/, .gitignore]
    scope: []
    dependencies: [T01, T09, T14]
    required_mcps: [gortex]
    optional_mcps: [context7]
    acceptance:
      - id: AC38
        description: Alle Workflow-, Skill-, Agenten- und MCP-Verweise sind auflösbar und widerspruchsfrei.
      - id: AC39
        description: Das Paket erfüllt die Qualitäts- und Abnahmekriterien aus DESIGN.md oder dokumentiert jede nicht ausführbare Prüfung.
      - id: AC40
        description: APM-Compile, Preview und Scratch-Install sind nur nach expliziter Freigabe ausgeführt oder klar als blocked markiert.
    checks:
      - id: CK26
        covers: [AC38, AC39]
        procedure: >
          Mit Gortex die Paketstruktur, alle Workflow-, Skill-, Agenten- und
          MCP-Referenzen sowie die Abweichungen zu DESIGN.md prüfen.
        pass: "Keine unaufgelösten widersprüchlichen Verträge oder toten internen Referenzen."
      - id: CK27
        covers: [AC40]
        command: ["apm", "compile", "--validate"]
        cwd: "."
        pass: "Exit code 0; nur nach ausdrücklicher Buildautorisierung ausführen."
      - id: CK28
        covers: [AC40]
        command: ["apm", "install", "--dry-run", "--target", "opencode,codex"]
        cwd: "."
        pass: "Dry-run zeigt erwartete Projektionen ohne ungeplante Dateien; nur nach ausdrücklicher Installationsautorisierung ausführen."
```

## Risiken und Abbruchbedingungen

| Risiko | Reaktion |
|---|---|
| `gortex-serena-configurator` ist nicht per APM installierbar | Manifest nicht durch lokale Kopie ersetzen; Repositorypfad, Referenzformat und APM-Version prüfen. |
| Erzeugter Skill überschreitet Authoring-Gates | Kein Abschluss; Skill mit `skill-creator` überarbeiten und erneut mit `context-debloater` prüfen. |
| Gortex ist für eine erforderliche Operation nicht bereit | Task blockieren oder gemäß Toolrouting den erlaubten Serena-/Native-Fallback verwenden. |
| Research widerspricht DESIGN.md materiell | Nicht stillschweigend abweichen; Planentscheidung mit Nutzer klären. |
| APM-Validierung verlangt Compile/Install | Bis zur ausdrücklichen Build-/Installationsfreigabe als `blocked` ausweisen. |
| Fachagent versucht Subagenten zu starten | Versuch stoppen; Dispatch ausschließlich an execute zurückgeben. |

## Statische Planprüfung

- Alle Task-IDs, Akzeptanz-IDs und Check-IDs sind eindeutig.
- Der Abhängigkeitsgraph ist azyklisch.
- Jeder Task hat genau einen vorhandenen Agenten, getrennte Kontext- und Schreibpfade sowie mindestens einen Check.
- Parallele Tasks ab T03 besitzen disjunkte Schreibscopes.
- T15 besitzt bewusst einen leeren Schreibscope und ist read-only.
- T13 und T17 trennen Terraform- von Dokumentationswissen und besitzen disjunkte Schreibscopes.
- Jeder Skilltask enthält die verpflichtenden `skill-creator`- und `context-debloater`-Gates.
- Compile- und Installationschecks sind als künftige, autorisierungsgebundene Checks markiert.

## Übergabe

```text
Next workflow: core-execute
Input: .agentic-workflow/plans/001-implement-agentic-workflow-core.md
Voraussetzung: Status auf Confirmed setzen und alle späteren Build-/Installationschecks gesondert autorisieren.
```

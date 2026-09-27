# Fehleranalyse: Zu viele Planrevisionen

**Session ID:** ses_f20b96a20ffebVI4Wloacf6Bh7
**Created:** 9/26/2026, 9:52:20 PM
**Updated:** 9/27/2026, 1:07:22 AM

---

## Assistant

**Tool: bash**

---

## Assistant

Erledigt.

Die Sitzung `ses_f20b96a20ffebVI4Wloacf6Bh7` ist jetzt zugeordnet zu:

```text
/home/visimeos/Projects/agentic-workflow-core
```

Die Exportdatei liegt als Sicherung unter:

```text
/tmp/opencode/agentic-workflow-core-session.json
```

Bitte diese OpenCode-Instanz beenden und so neu öffnen:

```bash
opencode /home/visimeos/Projects/agentic-workflow-core \
  --session ses_f20b96a20ffebVI4Wloacf6Bh7
```

Es wurden keine Änderungen aus `automation-infra` in das neue Repository kopiert.

---

## User

ok klappt. dann weiter im brainstorm workflow.

## Gortex Session Orientation

✓ Gortex daemon ready (v0.64.4+2b5480bf, uptime 5h53m). 5 tracked repo(s), 64911 nodes, 207203 edges across 5 workspace(s).

**cwd `/home/visimeos/Projects/agentic-workflow-core` is tracked** as repo `` (workspace: `agentic-workflow-core`, 11566 nodes). Enforcement is active.

**Rule:** For an explicitly named file that the user asks you to read, review, or summarize, on the first direct file read caused by a new user request call `read(operation:"file", target:{file:"<path>"}, options:{new_user_task:true})`; do not start localization. Otherwise choose by requested output: when the requested output is files, symbols, or supporting evidence, call the mounted tool `mcp__gortex__explore` (never a bare `explore`) with `operation:"localize"`; it returns terminal evidence. Its localize task may be concise, but must faithfully preserve the issue title and every user-supplied technical identifier, path, literal, error, symptom, and stated hypothesis; never invent a causal hypothesis. A clearly framed problem section may be restored exactly at execution only for a clearly lossy model task, so evidence can reflect details beyond a concise tool argument. Use `mcp__gortex__explore` with `operation:"task"` only when work will actually continue beyond localization into diagnosis, relationship analysis, or implementation. After starting localization, obey `completion.required_action`. For `needs_recovery`, make one accepted, bounded Gortex MCP `search` or `read` call. If Gortex explicitly rejects an overbroad request and preserves the recovery allowance, correct it using only Gortex MCP `search` or `read`; the rejected request does not count as the accepted recovery. Do not call host Read, Grep, Glob, or Bash. At `answer_ready`, respond from `completion.final_response` and make no further tool calls. In that final response, each PRIMARY or SUPPORTING row is one aligned file/symbol tuple; preserve the PRIMARY file and symbol identities in the answer, while SUPPORTING rows are optional context. Any later Gortex navigation call for that same task is intentionally not executed and replays the same retained terminal payload; identical output is expected, not stale or canned output or an integration failure. Inspect indexed code with `search`, `read`, `relations`, or `trace`. Outside an active localization contract, use native read, search, or edit tools only when Gortex performance or integration is actually bad. Before mutation call `change(operation:"impact")`; for a signature change also call `change(operation:"verify")` with the proposed signature. Mutate with `edit` or `refactor`. After mutation call `change(operation:"detect")`; use the returned symbol IDs with `change` operations `tests`, `guards`, and `contract`. Call `capabilities` only when exact operation fields are unknown.
  - Native Gortex MCP is mandatory for this profile. If a referenced Gortex tool is missing from the callable MCP tools despite the server being configured, surface a Gortex MCP integration failure to the user and stop. Do not start a daemon or use any CLI/shell fallback.

### Worktree and branch routing

- The session/CWD selects the view. An implicit or session-discovered checkout (including a linked worktree) is an automatic overlay; do not explicitly `track` it. Only an explicit user request to track creates a dedicated logical graph.
- **Overall** means the selected overlay plus exactly one designated primary in its Git family, never a union of incompatible branches. Unique overlay/base matches keep normal relevance order; for a duplicate logical identity the overlay wins, and deletion/tombstone masks hide the base copy.
- Freshness `exact:false` means the requested view was not served. Every fallback is read-only. Use `require_exact:true` to refuse substitution, `require_fresh:true` to await filesystem state, and absolute RFC3339 `wait_deadline` to bound it.
- Select explicitly when CWD is not the target, for example `view:{kind:"worktree",checkout_id:"…"}` or `view:{kind:"git_ref",value:"refs/heads/release",graph_id:"…"}`. Inactive ref/commit views are immutable committed structural/source snapshots: no working-copy LSP, `search.text`, or edits. Approved coordinator-backed exact worktree edits are supported; fallback and ref/commit views are not.
- Explicitly untracking a non-primary dedicated worktree demotes it to automatic only when another ready primary survives. Before primary closure, family forget, or `set-primary`, preview the effects and obtain user confirmation.


---

## Assistant

**Tool: gortex_explore**

---

## Assistant

**Tool: gortex_search**

**Tool: gortex_search**

**Tool: gortex_search**

**Tool: gortex_search**

**Tool: gortex_search**

---

## Assistant

**Tool: gortex_search**

**Tool: gortex_search**

**Tool: gortex_search**

**Tool: gortex_search**

**Tool: gortex_search**

---

## Assistant

## Projektkontext – erster Überblick

Gortex hat im neuen Repository erfasst:

- **21 OMA-Fachskills** unter `oma-arbeitsmasse/skill/`
- **16 OMA-Workflows** unter `oma-arbeitsmasse/workflows/`
- **7 zusätzliche Evaluationskandidaten**:
  - `git-ship-release`
  - `maintain-repository`
  - `security-best-practices`
  - `security-threat-model`
  - `software-docs`
  - `swe-quality-check`
  - `typesafe-ai`
- Bereits erkennbare Duplikate zwischen Arbeitsmasse und `.agents/`, etwa bei:
  - `oma-dev-workflow`
  - `oma-observability`
  - `stack-set`
- `deepinit` erzeugt bereits Wissensbasis und Boundary-`AGENTS.md`; `stack-set` erzeugt stackspezifische Referenzen. Beide überschneiden sich teilweise mit dem Command-Template.
- `handoff.md` und `.agents/reference/` wurden im aktuellen Gortex-Index noch nicht gefunden. Sie sind möglicherweise nicht kopiert, untracked oder anders einsortiert. Das bleibt ein offener Inventarpunkt.

Zusätzlich aufgenommen:

- Serena-Memories gegen das Handoff-System vergleichen.
- Eine kanonische Historie für Umsetzung, Fehlschläge, Bugs und Findings definieren.
- Doppelpflege ausdrücklich vermeiden.

## Erste Klärungsfrage

Für wen und welche Laufzeit soll das Paket primär portabel sein?

- **A — Persönliches OpenCode-Paket:** für deine eigenen Repositories, Linux, OpenCode und Gortex fest vorausgesetzt.
- **B — Öffentliches OpenCode/APM-Paket:** für andere Nutzer installierbar; Gortex bleibt verpflichtende Abhängigkeit.
- **C — Clientübergreifend:** OpenCode, Codex, Claude Code und Gemini; gemeinsame `.agents`-Basis mit clientbezogenen Adaptern.
- **D — Anders:** eigene Zieldefinition.

Meine vorläufige Empfehlung wäre **C**, sofern der zusätzliche Adapteraufwand akzeptabel ist.

---

## User

zu reference habe ich ja den dateipfad angegeben. musst mit nativen tools und ist nicht in diesem repo. zu deinen fragen: kann öffentlich sein, aber muss mit: gortex, serena, honcho und context7 klappen. das sind also reqs. alle außer honcho haben mcp, diese kann man im apm.yml schreiben. default opencode und codex. auch überlegen: es ist gut wie oma es macht mit skills und workflows ordnern oder nur ein skills ordner besser.

---

## Assistant

**Tool: skill**

---

## Assistant

**Tool: glob**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

**Tool: gortex_search**

**Tool: gortex_search**

**Tool: gortex_search**

**Tool: gortex_search**

---

## User

---

## Assistant

## Objective
- Im neuen Repository `/home/visimeos/Projects/agentic-workflow-core` ein portables öffentliches APM-Paket mit schlanken deutschen Skills und Workflows entwerfen, das Stärken von OMA und `agentic-workflow-template` kombiniert, aber Plan-/Metadaten-Bloat vermeidet.
- Die pausierte `automation-infra`-Remediation bleibt technisch grün, aber formal noch nicht vollständig abgeschlossen.

## Important Details
- Zielplattformen: standardmäßig **OpenCode und Codex**.
- Pflichtintegrationen: **Gortex, Serena, Honcho und Context7**.
  - Gortex, Serena und Context7 besitzen MCP-Integrationen und sollen über `apm.yml` konfigurierbar sein.
  - Honcho besitzt keine entsprechende MCP-Integration; alternative Anbindung ist zu entwerfen.
- Gortex muss in allen Skills und Workflows berücksichtigt und grundsätzlich verwendet werden.
- Paket soll öffentlich nutzbar, repository- und pfadidempotent sein:
  - `.agents` in ein bestehendes Repository kopieren,
  - danach möglichst sofort verwendbar,
  - keine fest codierten Projektpfade.
- Repository als Microsoft-APM-Paket aufsetzen; `apm init` ist vorgesehen.
- Alle Skill- und Workflow-Markdowndateien müssen auf Deutsch geschrieben sein.
- Erhalten werden sollen:
  - Fachagenten,
  - nachvollziehbare Protokollierung umgesetzter Arbeiten,
  - Fehlschläge,
  - Bugs und Findings,
  - begrenzte Parallelisierung und unabhängige Reviews,
  - Sicherheits- und Produktionsgrenzen.
- Zu entscheiden:
  - Serena-Memories versus `.agents/reference/handoff.md`,
  - eine kanonische Quelle statt Doppelpflege,
  - getrennte `skills/`- und `workflows/`-Ordner wie OMA versus nur `skills/`,
  - Rolle von Honcho für langfristige Nutzer-/Agentenerinnerungen,
  - ob `user2agent` Bestandteil von Deep Init wird,
  - ob ein neues kombiniertes Deep-Init entsteht,
  - ob `_shared` und Stack-/Fachagent-YAML benötigt werden.
- Bei der späteren Erstellung sind `context-debloater` und `skill-creator` einzusetzen beziehungsweise deren Regeln zu berücksichtigen.
- Zu vermeiden:
  - mehrere konkurrierende Planquellen,
  - selbstreferenzielle Digests,
  - Reviews von Reviews,
  - unbeschränkte Planrevisionen,
  - Metadatenfehler als Produktfehler,
  - neue Task-IDs zur Umgehung von Retry-Grenzen.
- Historische Diagnose:
  - Ultrawork begrenzt VERIFY/REFINE, nicht jedoch den PLAN-Gate-Rücksprung.
  - Ultrawork enthält ausdrücklich einen Meta-Review des Completeness-Reviews.
  - Der aktuelle Orchestrate-Fall entstand dagegen überwiegend durch übernommene Sitzungskonventionen und zusätzliche, nicht vorgeschriebene Planreviews.
- Brainstorm-Workflow ist aktiv: derzeit Step 1, reine Analyse; noch keine Implementierung.
- Externe, ausdrücklich genannte Pfade dürfen mit nativen Dateitools gelesen werden, wenn sie nicht im Gortex-Workspace liegen.
- PC nicht herunterfahren.

## Work State
### Completed
- Neues Git-Repository angelegt:
  - `/home/visimeos/Projects/agentic-workflow-core`
  - Branch `main`
  - noch kein Commit.
- OpenCode-Sitzung `ses_f20b96a20ffebVI4Wloacf6Bh7` per Export/Import dem neuen Repository zugeordnet.
- Gortex erkennt den neuen Workspace `agentic-workflow-core`.
- Erste Inventarisierung:
  - 21 OMA-Skills unter `oma-arbeitsmasse/skill/`
  - 16 OMA-Workflows unter `oma-arbeitsmasse/workflows/`
  - 7 Kandidaten unter `evaluieren/`
- Evaluationskandidaten identifiziert:
  - `git-ship-release`
  - `maintain-repository`
  - `security-best-practices`
  - `security-threat-model`
  - `software-docs`
  - `swe-quality-check`
  - `typesafe-ai`
- Sieben externe Commands bereits gelesen:
  - `prime.md`
  - `create-prd.md`
  - `create-rules.md`
  - `plan-feature.md`
  - `execute.md`
  - `review.md`
  - `commit.md`
- Externe Reference-Struktur lokalisiert:
  - `handoff.md`
  - `PRD.md`
  - `architecture.md`
  - `architecture-rules.md`
  - `repositories.md`
  - `example-decision.md`
- Ablaufgrafik `.agents/agentic-workflow-framework.png` gelesen.
- Offizielle Recherche-Routen für APM, Honcho, Serena, Context7 und OMA geladen.
- `automation-infra` technisch umgesetzt:
  - Checker: SHA-256 `7defbc4950c80ec8c99dc7779d7aa461debcf60e7fbff5d111b2f3a881aa2f93`
  - Plan 018: SHA-256 `8801edd27ddc568331d343dd16e5de5d52800021e684ecbae5642cd6cd1b342f`
  - Checker-Test unverändert: SHA-256 `d950fe2746b1a54383019835ba12406cb03d182c4ee291130c483d1f477cfdb6`
  - fokussierte Tests: 33/33 bestanden.
- Evidence-Close-Run `65c280d9-9054-4214-ace6-a9a904f51a51`: completed, 10/10 Checks.
- Current Verification `d4f11023-6ce6-4d2d-b47a-f3693f38848c`:
  - 27/27 technische Checks Exit 0,
  - Coverage 90,86 %,
  - keine Produktmutation,
  - formale Closure scheiterte nur an `artifact-key binding mismatch`.
- Revision 14 der Remediation-Planung:
  - Planning-Run `4b1100d1-bd96-4c25-9c8f-dfe55af82f1b`
  - 11/11 Checks,
  - finaler Authority-Digest `3ec05e76d0ab44f54786e67b7346144f9c768ffe00eb813e9cadd34efdfb4906`.

### Active
- Vollständige Bestandsanalyse aller OMA-Skills, OMA-Workflows, Evaluationskandidaten, Commands und References.
- Für jedes Artefakt ist `übernehmen`, `anpassen`, `zusammenführen` oder `verwerfen` zu bestimmen.
- Zu untersuchen:
  - Deep Init versus `prime`/Reference-Struktur,
  - Integration von `user2agent`,
  - Serena versus Handoff versus Honcho,
  - `git-ship-release` versus OMA-SCM,
  - `maintain-repository` als Teil von Deep Init,
  - `_shared`-Ordner und gemeinsame Policies,
  - `stack-set` und Fachagent-YAML,
  - bestehende Ablaufgrafik versus neuer Flow,
  - Clairvoyance-Skills unter `https://github.com/codybrom/clairvoyance/tree/main/skills`,
  - APM-Paketstruktur und MCP-Konfiguration.
- Vorläufige Designrichtung, noch nicht beschlossen:
  - ein kanonischer Plan,
  - schlanker Standardablauf,
  - begrenzter Multi-Agent-Modus,
  - separater High-Assurance-Modus,
  - keine Planrevision nach Ausführungsbeginn,
  - maximal begrenzte Korrekturrunden.
- `automation-infra` bleibt pausiert; Revision 14 wurde noch nicht abschließend unabhängig geprüft oder ausgeführt.

### Blocked
- Keine Blockade für die aktuelle Brainstorm-Analyse.
- `automation-infra` besitzt weiterhin einen formalen Evidence-/Closure-Restpunkt, aber keinen bekannten Produkt- oder Testfehler.
- Noch offen ist, welche Logging-/Memory-Komponente die kanonische Wahrheit bildet.

## Next Move
1. Step 1 abschließen: sämtliche genannten lokalen und externen Dateien sowie Clairvoyance und die offiziellen APM-/MCP-Anforderungen systematisch bewerten; keine Dateien verändern.
2. Danach die nächste materielle Klärungsfrage einzeln stellen und anschließend 2–3 mechanistisch unterschiedliche Architekturansätze mit Prosa, Vergleichsmatrix und struktureller Empfehlung präsentieren.

## Relevant Files
- `/home/visimeos/Projects/agentic-workflow-core/`: neues Zielrepository.
- `/home/visimeos/Projects/agentic-workflow-core/oma-arbeitsmasse/skill/`: 21 zu evaluierende OMA-Skills.
- `/home/visimeos/Projects/agentic-workflow-core/oma-arbeitsmasse/workflows/`: 16 zu evaluierende OMA-Workflows.
- `/home/visimeos/Projects/agentic-workflow-core/evaluieren/`: zusätzliche Skill-Kandidaten.
- `/home/visimeos/Projects/agentic-workflow-core/evaluieren/git-ship-release/SKILL.md`: möglicher SCM-Ersatz.
- `/home/visimeos/Projects/agentic-workflow-core/evaluieren/maintain-repository/SKILL.md`: möglicher Deep-Init-Baustein.
- `/home/visimeos/Projects/agentic-workflow-template/.agents/commands/`: sieben schlanke Command-Vorlagen.
- `/home/visimeos/Projects/agentic-workflow-template/.agents/reference/handoff.md`: zu evaluierendes Handoff-System.
- `/home/visimeos/Projects/agentic-workflow-template/.agents/reference/docs/`: Architektur-, PRD-, Repository- und Decision-Vorlagen.
- `/home/visimeos/Projects/agentic-workflow-template/.agents/agentic-workflow-framework.png`: bestehendes Ablaufmodell.
- `/home/visimeos/.agents/skills/_shared/`: Referenz für mögliche gemeinsame Policies und Ressourcen.
- `/home/visimeos/.opencode/skills/software-docs/references/apm.md`: offizielle APM-Rechercheroute.
- `/home/visimeos/.opencode/skills/software-docs/references/honcho.md`: offizielle Honcho-Rechercheroute.
- `/home/visimeos/.opencode/skills/software-docs/references/serena.md`: offizielle Serena-Rechercheroute.
- `/home/visimeos/.opencode/skills/software-docs/references/context7.md`: offizielle Context7-Rechercheroute.
- `https://github.com/codybrom/clairvoyance/tree/main/skills`: externe Skill-Sammlung zur Bewertung.
- `/tmp/opencode/agentic-workflow-core-session.json`: Sicherung der übertragenen OpenCode-Sitzung.
- `/home/visimeos/Projects/automation-infra/.agents/results/plan-20260925-182034.json`: pausierter Revision-14-Plan.
- `/home/visimeos/Projects/automation-infra/.agents/results/remediation-handoff-current-verification-20260925-182034.md`: letzter Current-Verification-Handoff.

---

## User

---

## Assistant

**Tool: skill**

**Tool: gortex_read**

**Tool: todowrite**

---

## Assistant

**Tool: gortex_read**

---

## Assistant

**Tool: gortex_explore**

**Tool: gortex_ask**

**Tool: gortex_search**

**Tool: gortex_search**

**Tool: gortex_search**

---

## Assistant

**Tool: gortex_search**

---

## Assistant

**Tool: gortex_read**

---

## Assistant

**Tool: gortex_search**

**Tool: gortex_search**

**Tool: gortex_search**

**Tool: gortex_search**

---

## Assistant

**Tool: gortex_search**

**Tool: gortex_search**

**Tool: gortex_search**

---

## Assistant

**Tool: gortex_search**

**Tool: gortex_search**

**Tool: gortex_search**

---

## Assistant

**Tool: gortex_read**

---

## Assistant

**Tool: gortex_response**

---

## Assistant

**Tool: gortex_response**

---

## Assistant

**Tool: gortex_response**

---

## Assistant

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

---

## Assistant

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

---

## Assistant

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

---

## Assistant

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

---

## Assistant

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

**Tool: gortex_read**

---

## Assistant

**Tool: skill**

---

## Assistant

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

**Tool: read**

---

## Assistant

**Tool: webfetch**

**Tool: webfetch**

**Tool: webfetch**

**Tool: webfetch**

**Tool: webfetch**

**Tool: webfetch**

**Tool: webfetch**

**Tool: webfetch**

---

## Assistant

**Tool: webfetch**

**Tool: webfetch**

**Tool: webfetch**

**Tool: webfetch**

**Tool: webfetch**

**Tool: webfetch**

**Tool: gortex_read**

---

## Assistant

**Tool: task**

**Tool: skill**

**Tool: skill**

**Tool: gortex_read**

---

## Assistant

Ich habe weiter analysiert. Zwei wichtige Ergebnisse:

1. **APM kennt keinen eigenen Workflow-Primitivtyp.**  
   Portable Abläufe sollten daher als Skills unter `.apm/skills/` entstehen. Optionale Slash-Commands liegen unter `.apm/prompts/`, erreichen aber Codex nicht zuverlässig. Ein zusätzliches `workflows/`-Verzeichnis würde wieder Doppelpflege erzeugen.

2. **Honcho besitzt inzwischen eine offizielle MCP-Integration.**  
   Es gibt den gehosteten Server `https://mcp.honcho.dev`, lokale Varianten sowie offizielle OpenCode- und Codex-Integrationen. Die frühere Annahme „Honcho hat kein MCP“ ist damit überholt.

Vorläufige Quellenstruktur:

```text
.apm/
├── skills/          # portable Fachfähigkeiten und mehrstufige Abläufe
├── agents/          # explizit aufrufbare Fachagenten als *.agent.md
├── instructions/    # kurze, dauerhafte Regeln
└── prompts/         # optionale OpenCode-Kommandos; nicht kanonisch

apm.yml
AGENTS.md
docs/
```

Dabei gilt:

- `.apm/` ist die bearbeitete Paketquelle.
- `.agents/`, `.opencode/` und `.codex/` sind durch APM erzeugte Zielprojektionen, nicht parallele Quellen.
- `agents/openai.yaml` innerhalb eines Skills ist nur optionale OpenAI-UI-Metadaten. Es ersetzt **keinen** APM-Fachagenten; dafür ist `.apm/agents/<name>.agent.md` vorgesehen.
- Handoff-Dokumente bleiben kurz und taskbezogen.
- Serena-Memories dienen als projektbezogener, menschenlesbarer Navigationscache.
- Honcho sollte persönliche und sitzungsübergreifende Erinnerung übernehmen, aber nicht Architekturentscheidungen oder Pläne zur kanonischen Wahrheit machen.
- Die Clairvoyance-Auswertung empfiehlt ein reduziertes Set von etwa neun angepassten Skills statt aller 16; Router und Review-Orchestratoren würden sonst Routing-Bloat erzeugen.

**Eine Klärungsfrage:**  
Soll Honcho im Design als **optionale MCP-Abhängigkeit in `apm.yml`** vorgesehen werden – mit ausdrücklichem Opt-in wegen API-Key, Datenschutz und externer Speicherung? Das wäre meine Empfehlung. Alternativ können wir Honcho absichtlich nur über seine nativen OpenCode-/Codex-Plugins anbinden.

### Quellen
- [APM Producer Ramp](https://microsoft.github.io/apm/_llms-txt/producer-ramp.txt)
- [APM MCP Primitive](https://microsoft.github.io/apm/producer/author-primitives/mcp-as-primitive/)
- [Honcho MCP](https://honcho.dev/docs/v3/guides/integrations/mcp.md)
- [Honcho für OpenCode](https://honcho.dev/docs/v3/guides/integrations/opencode.md)
- [Honcho für Codex](https://honcho.dev/docs/v3/guides/integrations/codex.md)
- [Serena Memories & Onboarding](https://oraios.github.io/serena/02-usage/045_memories.html)

---

## User

was ich meinte: die 3 mcp die ich nannte, sollten in apm.yml für opencode und codex definiert werden. für honcho braucht es das nicht, weil da gibts ein opencode plugin. und ich selfhoste honcho. wenn leute sich das repo runterladen wollen, müssen sie ihren honcho mcp selbst konfigurieren, für mich brauche ich das nicht, darum bleibt es draußen. honcho ist übrigens bereits richtig konfiguriert bei mir.

---

## Assistant

Verstanden — ich korrigiere das Design:

- `apm.yml` deklariert **Gortex, Serena und Context7** als MCP-Abhängigkeiten für **OpenCode und Codex**.
- **Honcho bleibt vollständig außerhalb** des Pakets und der `apm.yml`.
  - Deine bestehende lokale Honcho-Konfiguration bleibt unberührt.
  - Andere Nutzer konfigurieren Honcho bei Bedarf selbst, etwa über das native OpenCode-Plugin oder ihre eigene MCP-Verbindung.
  - Die Paketdokumentation beschreibt Honcho höchstens als optionale, externe Ergänzung — ohne Setup-Anweisung oder Credential-Schema.

Nächste Designfrage: Soll die primäre Nutzung für andere sein:

1. `apm install <owner>/<repo>` in einem bestehenden Projekt,  
2. Repository klonen und darin `apm install` ausführen,  
3. beides, mit Variante 1 als empfohlener Standard?

---

## User

die idee ist: apm install als globale skills also --gloabl --target agent-skills oder so. weil: dann kann man immer mit workflows coden in jedem repo und jedes repo initialisieren.

---

## Assistant

**Tool: webfetch**

**Tool: webfetch**

**Tool: webfetch**

**Tool: webfetch**

---

## Assistant

**Tool: webfetch**

**Tool: webfetch**

**Tool: webfetch**

---

## Assistant

Verstanden. Das Ziel ist ein **global installierter Workflow-Werkzeugkasten**, der in jedem Repository verfügbar ist und dort per Deep Init die projektspezifische Struktur erzeugt.

Wichtige APM-Einschränkung:

- `--target agent-skills` installiert ausschließlich Skills nach `~/.agents/skills/`.
- Es installiert **keine Fachagenten und keine MCP-Konfiguration**.
- Für das vollständige OpenCode-/Codex-Paket wäre daher zunächst korrekt:

```bash
apm install -g <owner>/<repo> --target opencode,codex
```

Damit werden Skills und Fachagenten in die jeweiligen globalen Verzeichnisse installiert. Codex unterstützt dabei auch globale MCP-Konfiguration; OpenCode-MCP wird von APM derzeit nur projektbezogen geschrieben.

### Empfohlenes Zweistufenmodell

1. **Einmalig global installieren**
   - Workflows als Skills
   - Fachagenten
   - Deep Init
   - globale Codex-MCP-Konfiguration

2. **Deep Init in jedem Repository ausführen**
   - erzeugt die Wissens- und Dokumentationsstruktur,
   - erzeugt das lokale `apm.yml`,
   - deklariert dort Gortex, Serena und Context7,
   - konfiguriert die MCPs projektbezogen für OpenCode und Codex,
   - lässt Honcho vollständig unberührt.

Damit bleiben die Workflows überall verfügbar, während repositoryabhängige MCP- und Projektkonfigurationen erst beim Initialisieren entstehen.

**Eine Designfrage:** Soll Deep Init die lokalen MCP-Einträge automatisch installieren, oder nur das fertige `apm.yml` erzeugen und dem Nutzer anschließend den expliziten Befehl `apm install --only mcp` anzeigen? Meine Empfehlung ist die zweite, transparentere Variante.

### Quellen
- [APM `install` und globale Ziele](https://microsoft.github.io/apm/reference/cli/install/)
- [APM-Zielmatrix](https://microsoft.github.io/apm/reference/targets-matrix/)
- [APM-MCP-Installation](https://microsoft.github.io/apm/consumer/install-mcp-servers/)

---

## User

---

## Assistant

## Objective
- Im Repository `/home/visimeos/Projects/agentic-workflow-core` ein schlankes, öffentliches Microsoft-APM-Paket mit deutschen Skills und Workflow-Fähigkeiten entwickeln.
- Das Paket soll global installierbar sein, damit OpenCode und Codex in jedem Repository dieselben Workflows nutzen und neue Repositories initialisieren können.

## Important Details
- Primäre Zielplattformen: **OpenCode und Codex**.
- Vorgesehene Nutzung: globale Installation, sinngemäß `apm install <owner>/<repo> --global --target agent-skills`; exakte unterstützte Syntax und Target-Semantik sind noch offiziell zu verifizieren.
- `apm.yml` soll genau diese drei MCP-Integrationen für OpenCode und Codex definieren:
  - Gortex
  - Serena
  - Context7
- **Honcho bleibt vollständig außerhalb von `apm.yml` und Paket-Setup.**
  - Der Nutzer selfhostet Honcho.
  - Honcho ist lokal bereits korrekt konfiguriert.
  - Für OpenCode existiert ein Honcho-Plugin.
  - Andere Nutzer konfigurieren Honcho bei Bedarf selbst.
  - Keine Credentials oder Honcho-Konfigurationsschemata ins öffentliche Paket aufnehmen.
- Gortex muss in allen Skills und workflowartigen Abläufen berücksichtigt und grundsätzlich für Code-Erkundung verwendet werden.
- APM besitzt keinen eigenen Workflow-Primitivtyp:
  - portable Abläufe als Skills unter `.apm/skills/`
  - `.apm/prompts/` nur optional für Commands, nicht kanonisch
  - kein paralleler `workflows/`-Quellbaum
- Vorgesehene APM-Quellstruktur:
  - `.apm/skills/`
  - `.apm/agents/*.agent.md`
  - `.apm/instructions/`
  - optional `.apm/prompts/`
  - `apm.yml`
  - `AGENTS.md`
  - `docs/`
- `.apm/` ist die kanonische Paketquelle; erzeugte `.agents/`, `.opencode/` oder `.codex/`-Projektionen dürfen keine zweite Quelle bilden.
- `agents/openai.yaml` innerhalb einzelner Skills ist optionale OpenAI-Oberflächenmetadaten und kein Ersatz für `.apm/agents/<name>.agent.md`.
- Alle Skill- und workflowartigen Markdown-Dateien müssen auf Deutsch verfasst werden.
- Paket soll öffentlich, pfadunabhängig und idempotent sein; keine fest codierten Projektpfade oder privaten Inhalte.
- Gewünschte Eigenschaften:
  - Fachagenten
  - nachvollziehbare Protokolle zu Umsetzung, Fehlern, Bugs und Findings
  - begrenzte Parallelisierung
  - unabhängige Reviews
  - Sicherheits- und Produktionsgrenzen
  - Initialisierung beliebiger Repositories
- Zu vermeiden:
  - konkurrierende Planquellen
  - selbstreferenzielle Digests
  - Reviews von Reviews
  - unbeschränkte Planrevisionen
  - Metadatenfehler als Produktfehler
  - neue Task-IDs zur Umgehung von Retry-Grenzen
  - Routing- und Context-Bloat
- Vorläufige Memory-Trennung:
  - Serena-Memories: projektbezogener Navigationscache
  - Handoffs: kurz, taskbezogen und menschenlesbar
  - Honcho: externe persönliche/sitzungsübergreifende Erinnerung, nicht kanonische Projektwahrheit
- Noch zu entscheiden:
  - endgültige kanonische Logging-/Handoff-Struktur
  - Deep Init versus `prime`/Reference-Struktur
  - Integration von `user2agent`
  - `maintain-repository` als Initialisierungsbaustein
  - Umfang von `_shared`
  - Rolle von `stack-set` und Fachagent-Metadaten
- Bei der Erstellung sind `context-debloater` und `skill-creator` beziehungsweise deren Regeln anzuwenden.
- Brainstorm-/Designphase aktiv; noch keine Implementierung.
- PC nicht herunterfahren.
- Pausierter Nebenstrang `automation-infra` ist technisch grün, aber formal noch nicht vollständig geschlossen.

## Work State
### Completed
- Neues Git-Repository erstellt:
  - `/home/visimeos/Projects/agentic-workflow-core`
  - Branch `main`
  - noch kein Commit
- OpenCode-Sitzung `ses_f20b96a20ffebVI4Wloacf6Bh7` in das neue Repository übertragen.
- Gortex erkennt den Workspace `agentic-workflow-core`.
- Relevante Architektur- und Reference-Dokumente aus `agentic-workflow-template` gelesen.
- Inventar lokalisiert:
  - 21 OMA-Skills unter `oma-arbeitsmasse/skill/`
  - 16 OMA-Workflows unter `oma-arbeitsmasse/workflows/`
  - 7 zusätzliche Kandidaten unter `evaluieren/`
- OMA-Skill-Frontmatter und Kernausrichtung der 21 Skills geprüft.
- Alle 16 OMA-Workflows lokalisiert und die zentralen Abläufe gelesen, darunter:
  - `architecture.md`
  - `brainstorm.md`
  - `debug.md`
  - `deepinit.md`
  - `deepsec.md`
  - `design.md`
  - `docs.md`
  - `exec-plan.md`
  - `explain.md`
  - `pdf.md`
  - `plan.md`
  - `review.md`
  - `schedule.md`
  - `scm.md`
  - `stack-set.md`
  - `work.md`
- Evaluationskandidaten geprüft:
  - `git-ship-release`
  - `maintain-repository`
  - `security-best-practices`
  - `security-threat-model`
  - `software-docs`
  - `swe-quality-check`
  - `typesafe-ai`
  - zusätzlich `orchestrate.md`, `ralph.md`, `ultrawork.md`
- Sieben externe Command-Vorlagen gelesen:
  - `prime.md`
  - `create-prd.md`
  - `create-rules.md`
  - `plan-feature.md`
  - `execute.md`
  - `review.md`
  - `commit.md`
- Ablaufgrafik `.agents/agentic-workflow-framework.png` gelesen.
- Offizielle APM-, Honcho-, Serena-, Context7- und OMA-Rechercherouten geladen.
- Offizielle APM-Dokumentation zu Package Authoring, Installation, Targets und MCP-Installation untersucht.
- Korrigiert: Honcho besitzt offizielle MCP-, OpenCode- und Codex-Integrationen; für dieses Paket bleibt Honcho dennoch bewusst extern.
- Offizielle Context7-Integration für OpenCode und Codex geprüft.
- Clairvoyance-Recherche `ses_f203dfd26ffe9SXIQPqVNrS1Yi` abgeschlossen:
  - vollständiges Inventar von 16 Skills
  - Empfehlung für ein reduziertes, angepasstes Set von ungefähr neun Fähigkeiten
  - Router und Review-Orchestratoren als Bloat-Risiko erkannt
- `context-debloater`- und `skill-creator`-Regeln geladen.
- Designrichtung festgelegt:
  - `.apm/` als einzige Quelle
  - workflowartige Abläufe als Skills
  - globale Wiederverwendung in beliebigen Repositories
  - Honcho nicht paketieren
- `automation-infra`:
  - 33/33 fokussierte Tests bestanden
  - Evidence-Close-Run `65c280d9-9054-4214-ace6-a9a904f51a51`: completed, 10/10 Checks
  - Verification `d4f11023-6ce6-4d2d-b47a-f3693f38848c`: 27/27 technische Checks, Coverage 90,86 %
  - verbleibender formaler Fehler: `artifact-key binding mismatch`
  - Revision-14-Planning-Run `4b1100d1-bd96-4c25-9c8f-dfe55af82f1b`, 11/11 Checks
  - Authority-Digest `3ec05e76d0ab44f54786e67b7346144f9c768ffe00eb813e9cadd34efdfb4906`

### Active
- Exakte APM-CLI-Semantik für globale Installation und `--target agent-skills` verifizieren.
- Bewerten, ob und wie MCP-Abhängigkeiten bei einer globalen `agent-skills`-Installation nach OpenCode und Codex projiziert werden.
- Für jedes lokale Artefakt endgültig `übernehmen`, `anpassen`, `zusammenführen` oder `verwerfen` festlegen.
- Minimalen globalen Skill-Satz und Initialisierungsablauf entwerfen.
- 2–3 mechanistisch unterschiedliche Paketarchitekturen mit Vergleichsmatrix vorbereiten.
- Kanonische Grenzen zwischen Plan, Arbeitsprotokoll, Handoff und Serena-Memory festlegen.
- `automation-infra` bleibt pausiert; Revision 14 wurde noch nicht abschließend unabhängig geprüft oder ausgeführt.

### Blocked
- Kein technischer Blocker für die aktuelle Designanalyse.
- Noch ungeklärt ist, ob `agent-skills` der korrekte APM-Targetname und mit `--global` kombinierbar ist.
- `automation-infra` besitzt weiterhin einen formalen Evidence-/Closure-Restpunkt, aber keinen bekannten Produkt- oder Testfehler.

## Next Move
1. In der offiziellen APM-Dokumentation beziehungsweise Implementierung die genaue globale Installationssyntax, gültige Targetnamen und MCP-Projektion für OpenCode/Codex verifizieren.
2. Danach 2–3 Architekturvarianten für global installierte Workflow-Skills plus Repository-Initialisierung vorstellen und eine schlanke Variante empfehlen.

## Relevant Files
- `/home/visimeos/Projects/agentic-workflow-core/`: neues Zielrepository.
- `/home/visimeos/Projects/agentic-workflow-core/oma-arbeitsmasse/skill/`: 21 OMA-Skills als Ausgangsmaterial.
- `/home/visimeos/Projects/agentic-workflow-core/oma-arbeitsmasse/workflows/`: 16 OMA-Workflows zur Konsolidierung in Skills.
- `/home/visimeos/Projects/agentic-workflow-core/evaluieren/`: zusätzliche Skill- und Workflow-Kandidaten.
- `/home/visimeos/Projects/agentic-workflow-core/evaluieren/git-ship-release/SKILL.md`: möglicher Ersatz beziehungsweise Ausbau von OMA-SCM.
- `/home/visimeos/Projects/agentic-workflow-core/evaluieren/maintain-repository/SKILL.md`: möglicher Initialisierungs- und Repository-Audit-Baustein.
- `/home/visimeos/Projects/agentic-workflow-core/evaluieren/software-docs/SKILL.md`: offizielle Produktdokumentations-Routen.
- `/home/visimeos/Projects/agentic-workflow-template/.agents/commands/`: schlanke Command-Vorlagen.
- `/home/visimeos/Projects/agentic-workflow-template/.agents/reference/handoff.md`: Handoff-Vorlage.
- `/home/visimeos/Projects/agentic-workflow-template/.agents/reference/docs/`: Architektur-, PRD-, Repository- und Decision-Vorlagen.
- `/home/visimeos/Projects/agentic-workflow-template/.agents/agentic-workflow-framework.png`: bestehendes Ablaufmodell.
- `/home/visimeos/.agents/skills/_shared/`: Referenz für gemeinsame Policies und Ressourcen.
- `/home/visimeos/.opencode/skills/software-docs/references/apm.md`: offizielle APM-Rechercheroute.
- `/home/visimeos/.opencode/skills/software-docs/references/honcho.md`: offizielle Honcho-Rechercheroute.
- `/home/visimeos/.opencode/skills/software-docs/references/serena.md`: offizielle Serena-Rechercheroute.
- `/home/visimeos/.opencode/skills/software-docs/references/context7.md`: offizielle Context7-Rechercheroute.
- `https://microsoft.github.io/apm/reference/cli/install/`: APM-Installationsreferenz.
- `https://microsoft.github.io/apm/reference/cli/targets/`: APM-Targetreferenz.
- `https://microsoft.github.io/apm/reference/targets-matrix/`: unterstützte Target-Fähigkeiten.
- `https://microsoft.github.io/apm/consumer/install-mcp-servers/`: MCP-Installationsverhalten.
- `https://raw.githubusercontent.com/microsoft/apm/main/src/apm_cli/integration/targets.py`: Target-Profile und Auflösung.
- `https://github.com/codybrom/clairvoyance/tree/main/skills`: bewertete externe Skill-Sammlung.
- `/tmp/opencode/agentic-workflow-core-session.json`: Sicherung der übertragenen Sitzung.
- `/home/visimeos/Projects/automation-infra/.agents/results/plan-20260925-182034.json`: pausierter Revision-14-Plan.
- `/home/visimeos/Projects/automation-infra/.agents/results/remediation-handoff-current-verification-20260925-182034.md`: letzter Verification-Handoff.

---

## User

---

## Assistant

**Tool: skill**

**Tool: gortex_explore**

---

## Assistant

**Tool: gortex_search**

---

## Assistant

**Tool: gortex_read**

---

## Assistant

Ich setze mit dem Architekturvergleich fort. Die erneute Gortex-Lokalisierung lokaler Entwurfsartefakte blieb unbestätigt; die APM-Quellenroute ist jedoch in `evaluieren/software-docs/references/apm.md::doc:apm-md-microsoft-agent-package-manager-sources` bestätigt.

## Variante A – Universelles Skills-Paket *(taktisch)*

Globale Installation:

```bash
apm install -g <owner>/<repo> --target agent-skills
```

Alle Workflows und Fachrollen würden als Skills modelliert. Deep Init erzeugt anschließend die lokale Projektstruktur und MCP-Konfiguration.

**Vorteile:** maximal portabel und einfach.  
**Nachteile:** keine nativen OpenCode-/Codex-Agenten; MCPs werden nicht global mitinstalliert.

## Variante B – Native globale Werkzeuge plus Projektinitialisierung *(strukturell, empfohlen)*

Globale Installation:

```bash
apm install -g <owner>/<repo> --target opencode,codex
```

- Skills und Fachagenten stehen in jedem Repository bereit.
- Deep Init erzeugt pro Repository ein lokales `apm.yml`.
- Dieses enthält Gortex, Serena und Context7.
- Der Nutzer bestätigt anschließend explizit:

```bash
apm install --only mcp
```

Damit wird die APM-Beschränkung umgangen, dass OpenCode-MCP-Konfigurationen nur projektbezogen installiert werden.

**Vorteile:** native Fachagenten, globale Workflows, nachvollziehbare lokale MCP-Konfiguration.  
**Nachteile:** zwei Installationsstufen.

## Variante C – Globaler Bootstrap, vollständiges Paket lokal *(strukturell)*

Global wird nur Deep Init als `agent-skills`-Paket installiert. Deep Init installiert danach in jedem Repository das vollständige OpenCode-/Codex-Paket einschließlich MCPs.

**Vorteile:** jedes Repository ist vollständig reproduzierbar und unabhängig von globaler Konfiguration.  
**Nachteile:** wiederholte lokale Installation; Workflows stehen vor der Initialisierung nicht vollständig bereit.

| Kriterium | A | B | C |
|---|---:|---:|---:|
| Workflows sofort überall | Hoch | Hoch | Niedrig |
| Native Fachagenten | Nein | Ja | Ja |
| Reproduzierbare MCPs | Mittel | Hoch | Hoch |
| Einfache Bedienung | Hoch | Mittel | Mittel |
| Passt zum Zielbild | Mittel | **Sehr hoch** | Hoch |

**Empfehlung:** Variante B. Sie erfüllt „immer mit den Workflows arbeiten“ und hält repositoryabhängige MCP-Konfiguration transparent und reproduzierbar.

Soll ich **Variante B** als verbindliche Designbasis detailliert ausarbeiten?

---

## User

wichtig ist, dass die workflows richtig auf einander verweisen, auf die fachagenten und auf die mcp, sodass ein strukturierter arbeitsflow des users geschehen kann. Skills und Fachagenten sollen nicht in jedem Repository bereitstehen. Die müssen auch nicht im Open Code Ordner oder im Codexordner existieren. Es reicht, wenn die Skills im Agentsordner global sind, denn Open Code und Codex können die Skills dort erkennen hätten wir unnötige doppelte Dateien, die alle verwaltet werden müssen und wenn APM für Open Code die MCP nicht verwalten kann, dann soll APM das nicht machen. Diese MCP, die ich erwähnt habe, sollen global eingestellt werden und nicht Projektlokal, denn das sind MCP, die man immer verwenden kann. eigentlich sind es noch mehr: chrome-devtools, context7, forgejo-api-mcp, gortex, youtube-transcript, serena. für das erstaufsetzen dieser mcp können wir einen eigenen init workflow-mcps skill oder so erstellen. bei serena kann dafür der gortex-serena-configurator skill Miteinbezogen werden.

---

## Assistant

**Tool: todowrite**

**Tool: gortex_explore**

---

## Assistant

**Tool: gortex_search**

---

## Assistant

Verstanden. Damit ist die vorherige Empfehlung mit `--target opencode,codex` verworfen.

## Aktualisierte Zielarchitektur

### 1. Ein globaler Skill-Bestand

Installation ausschließlich nach:

```text
~/.agents/skills/
```

mit:

```bash
apm install -g <owner>/<repo> --target agent-skills
```

Keine Kopien in:

- `~/.config/opencode/skills`
- `~/.opencode/`
- `~/.codex/`
- einzelnen Repositories

OpenCode und Codex erkennen denselben globalen Skill-Bestand. Damit existiert nur eine zu wartende Fassung.

### 2. Workflows als orchestrierende Skills

Workflow-Skills wie `brainstorm`, `plan`, `work`, `debug` und `review` erhalten explizite, validierbare Abhängigkeiten:

```markdown
## Ablaufabhängigkeiten

- Vorheriger Workflow: `brainstorm`
- Nächster Workflow: `plan`
- Fachfähigkeiten: `architecture`, `backend`, `qa`
- Erforderliche MCPs: `gortex`
- Optionale MCPs: `context7`, `serena`
- Fallback: Bei nicht verfügbarem Gortex Serena verwenden
```

Ein zentraler Katalog ordnet zu:

- Workflow → Vorgänger und Nachfolger
- Workflow → Fachagenten/Fachfähigkeiten
- Workflow → erforderliche und optionale MCPs
- MCP → zulässige Aufgaben
- Fehlerfall → Fallback oder Abbruch

Ein Validator prüft bei der Paketentwicklung, ob alle genannten Skills, Übergänge und MCP-IDs tatsächlich existieren. So vermeiden wir tote Verweise und auseinanderlaufende Abläufe.

### 3. Globale MCP-Konfiguration außerhalb von APM

APM installiert und verwaltet keine MCP-Konfiguration.

Ein eigener globaler Skill, beispielsweise `init-mcps`, übernimmt einmalig:

1. OpenCode und Codex erkennen.
2. Bestehende globale Konfiguration lesen.
3. Bereits korrekt konfigurierte MCPs unangetastet lassen.
4. Änderungen als Vorschau zeigen.
5. Vor Schreiboperationen bestätigen lassen.
6. Sicherung der betroffenen Konfiguration anlegen.
7. Fehlende MCPs global konfigurieren.
8. Verfügbarkeit und Authentifizierung prüfen.
9. Einen Ergebnisbericht ohne Secrets erzeugen.

Initialer MCP-Katalog:

| MCP | Zweck |
|---|---|
| `gortex` | primäre Code-Intelligence, Navigation und sichere Änderungen |
| `serena` | projektbezogener Fallback für Code-Navigation |
| `context7` | aktuelle Bibliotheks- und Framework-Dokumentation |
| `chrome-devtools` | Browseranalyse, UI-Debugging und Web-Verifikation |
| `forgejo-api-mcp` | Forgejo-Repositories, Issues und Pull Requests |
| `youtube-transcript` | Video-Metadaten und Transkripte |

Für Gortex und Serena bindet `init-mcps` den vorhandenen `gortex-serena-configurator` ein. Dieser prüft Provider-Verfügbarkeit, Gortex-Tracking und die Serena-Fallback-Konfiguration. Die lokale Serena-Referenz bestätigt diese vorgesehene Nutzung in `evaluieren/software-docs/references/serena.md`.

Credentials werden niemals im Paket gespeichert. `init-mcps` darf nur auf bestehende sichere Credential-Quellen verweisen oder den Nutzer zur manuellen Einrichtung auffordern.

### 4. Strukturierter Benutzerfluss

```text
APM global installieren
        │
        ▼
init-mcps einmalig ausführen
        │
        ▼
init-project in einem neuen Repository
        │
        ▼
brainstorm → design → plan → work
                         │
                         ├─ Fachfähigkeit auswählen
                         ├─ passendes MCP prüfen
                         ├─ Facharbeit ausführen
                         └─ unabhängiges review
```

Jeder Workflow besitzt:

- eindeutige Eintrittsbedingungen,
- definierte Vorgänger und Nachfolger,
- explizite Fachfähigkeiten,
- MCP-Voraussetzungen und Fallbacks,
- Abbruch- und Wiederaufnahmeregeln,
- ein einheitliches Handoff-Format.

Vorhandene Ansatzpunkte sind unter anderem:

- `oma-arbeitsmasse/skill/oma-debug/SKILL.md::…Serena-MCP`
- `.agents/skills/oma-dev-workflow/resources/api-workflows.md`
- `.agents/workflows/architecture.md`
- `.agents/workflows/brainstorm.md`

## Noch notwendige Begriffsentscheidung

Da wir keine Dateien in `.opencode/agents` oder `.codex/agents` installieren, können die „Fachagenten“ entweder:

1. **Fach-Skills** sein, die vom aktuellen Agenten oder einem verfügbaren generischen Subagenten geladen werden, oder
2. separate Agentenprofile in `~/.agents/agents/` sein – allerdings ohne gesicherte portable Unterstützung durch beide Clients und den APM-Target `agent-skills`.

Meine Empfehlung ist **Variante 1**: Fachagenten werden als Fach-Skills mit klaren Übergabeverträgen modelliert. Workflows verweisen auf stabile Skill-Namen statt auf clientspezifische Agentendateien.

Soll ich diese Interpretation – **Fachagenten als global installierte Fach-Skills** – als verbindliche Grundlage verwenden?

---

## User

noch nicht. weiter besprechen. die fachagenten sind keine fachskills. du hast gesagt apm unterstützt agents?

---

## Assistant

**Tool: skill**

**Tool: gortex_read**

**Tool: context7_resolve-library-id**

---

## Assistant

**Tool: webfetch**

**Tool: webfetch**

**Tool: webfetch**

**Tool: webfetch**

---

## Assistant

Ja, **APM unterstützt echte Agenten als eigene Primitive**. Meine vorherige Formulierung war unpräzise: Der Target `agent-skills` unterstützt **nur Skills**, nicht Agenten.

## Was APM unterstützt

Kanonische Paketquelle:

```text
.apm/
├── skills/
│   └── <skill>/SKILL.md
└── agents/
    └── <fachagent>.agent.md
```

APM transformiert die Agenten beim Installieren in das Format des jeweiligen Clients:

| Target | Ziel für Agenten |
|---|---|
| Codex | `~/.codex/agents/<name>.toml` |
| OpenCode | `~/.config/opencode/agents/<name>.md` |
| `agent-skills` | Agenten werden übersprungen |

Der Grund sind unterschiedliche Agentenformate, Tool-Berechtigungen und Modellangaben. Es gibt derzeit **kein gemeinsames APM-Ziel wie `~/.agents/agents/`**, das OpenCode und Codex gleichermaßen als native Fachagenten lesen.

Skills können dagegen gemeinsam nach `~/.agents/skills/` installiert werden.

## Wichtig bezüglich der Duplikate

Bei nativen Agenten gäbe es zwar zwei erzeugte Dateien, aber nicht zwei manuell gepflegte Quellen:

```text
.apm/agents/backend.agent.md       ← einzige kanonische Quelle
              │
              ├─ APM → ~/.codex/agents/backend.toml
              └─ APM → ~/.config/opencode/agents/backend.md
```

APM erzeugt, aktualisiert und entfernt diese Projektionen anhand des Lockfiles. Inhaltlich verwalten würden wir nur `.apm/agents/backend.agent.md`.

Bei Skills ist deine Forderung eindeutig: nur eine globale Kopie unter `~/.agents/skills/`.

## Drei mögliche Modelle für die Fachagenten

### A. Native APM-Agenten

- Fachagenten liegen unter `.apm/agents/`.
- APM projiziert sie global nach OpenCode und Codex.
- Workflows delegieren über stabile Agentennamen wie `backend-engineer`.
- Beste native Tool-, Modell- und Berechtigungssteuerung.
- Erzeugt verwaltete Dateien in beiden Client-Verzeichnissen.

### B. Portable Agentenbeschreibungen

- Fachagenten bleiben echte getrennte Rollenbeschreibungen, aber nicht als APM-Agentenprimitive.
- Sie liegen beispielsweise als Ressourcen eines globalen Orchestrierungs-Skills:

```text
~/.agents/skills/workflow-core/
├── SKILL.md
└── agents/
    ├── backend-engineer.md
    ├── frontend-engineer.md
    └── qa-reviewer.md
```

- Workflow-Skills lesen die jeweilige Rollenbeschreibung und starten damit einen generischen Subagenten.
- Nur eine globale Kopie.
- Die Agenten sind keine Fach-Skills.
- Allerdings fehlen native Agentenprofile und verlässlich durchgesetzte Tool-/Modellrechte.

### C. Getrennte APM-Pakete

Ein Repository veröffentlicht logisch zwei Pakete:

1. **Workflow-/Skill-Paket**
   - Target: `agent-skills`
   - Installation nach `~/.agents/skills/`
   - keine Skill-Duplikate

2. **Fachagenten-Paket**
   - Targets: `opencode,codex`
   - enthält ausschließlich `.apm/agents/`
   - daher werden keine Skills in Client-Verzeichnisse dupliziert

Das kombiniert einen einzigen globalen Skill-Bestand mit echten nativen Fachagenten. Die Agentenprojektionen liegen zwar in beiden Client-Verzeichnissen, werden aber vollständig von APM aus einer kanonischen Quelle verwaltet.

**Meine aktuelle Empfehlung ist Modell C**, sofern die von APM verwalteten Agentenprojektionen akzeptabel sind. Es bietet zuverlässige Delegation, ohne Skills zu duplizieren.

Die entscheidende Frage lautet daher: Sind automatisch von APM verwaltete Agentendateien in `~/.codex/agents/` und `~/.config/opencode/agents/` akzeptabel, oder sollen auch Fachagenten zwingend nur einmal unter `~/.agents/` existieren?

### Quellen

- [APM Targets Matrix – Agents und `agent-skills`](https://microsoft.github.io/apm/reference/targets-matrix/)
- [APM Install – Targets und globale Installation](https://microsoft.github.io/apm/reference/cli/install/)
- [APM Target-Implementierung](https://github.com/microsoft/apm/blob/main/src/apm_cli/integration/targets.py)

---

## User

warum nicht A?

---

## Assistant

Doch — **A ist für die Fachagenten die richtige Wahl**.

Meine Empfehlung für C bezog sich nur auf die Paketierung, nicht auf ein anderes Agentenmodell:

- **Agentenmodell:** A – echte native APM-Agenten.
- **Paketierungsmodell:** getrennte Komponenten, damit Skills nicht dupliziert werden.

## Warum A allein zunächst problematisch erschien

Enthält ein einziges Paket sowohl Skills als auch Agenten und wird es so installiert:

```bash
apm install -g <paket> --target opencode,codex
```

verteilt APM beide unterstützten Primitive:

```text
Skills:
  Codex    → ~/.agents/skills/
  OpenCode → ~/.config/opencode/skills/   # unnötige zweite Kopie

Agenten:
  Codex    → ~/.codex/agents/
  OpenCode → ~/.config/opencode/agents/
```

Mit:

```bash
--target agent-skills
```

landen die Skills korrekt nur unter `~/.agents/skills/`, aber die Agenten werden vollständig übersprungen. APM bietet derzeit keinen Filter wie `--only agents`.

## Richtige Kombination

```text
Eine öffentliche Distribution
├── Workflow-Komponente
│   ├── enthält nur Skills
│   └── Target: agent-skills
│
└── Fachagenten-Komponente
    ├── enthält nur APM-Agenten
    └── Targets: opencode, codex
```

Damit ergibt sich:

```text
~/.agents/skills/                  ← genau ein globaler Skill-Bestand
~/.codex/agents/                   ← von APM erzeugte Codex-Agenten
~/.config/opencode/agents/         ← von APM erzeugte OpenCode-Agenten
```

Die Agenten besitzen weiterhin nur **eine kanonische Quelle**:

```text
.apm/agents/backend-engineer.agent.md
```

Die beiden nativen Fassungen werden ausschließlich von APM erzeugt und verwaltet.

C war also missverständlich benannt: Es ist keine Alternative zu A, sondern die **interne Paketstruktur, mit der wir A ohne duplizierte Skills umsetzen**.

Meine korrigierte Empfehlung lautet daher:

> **Native APM-Fachagenten verwenden. Skills und Agenten intern getrennt ausliefern, damit Skills nur einmal unter `~/.agents/skills/` liegen.**

---

## User

A ist gut und ein einziges Paket. es reicht wenn die target spezifisch sind. müssen nicht unter home/.agents sein. A beachtung, die Agents für Open Code sind nicht in Config, sondern in /home/visimeos/.opencode/agents/

---

## Assistant

**Tool: context7_resolve-library-id**

**Tool: read**

**Tool: read**

---

## Assistant

**Tool: context7_query-docs**

---

## Assistant

**Tool: bash**

---

## Assistant

Verstanden: **Modell A, ein einziges Paket, native zielsystemspezifische Projektionen.** Duplikate zwischen OpenCode und Codex sind damit akzeptabel, weil APM sie aus einer kanonischen Quelle verwaltet.

Vorgesehene Quelle:

```text
.apm/
├── skills/
└── agents/
```

Installation grundsätzlich über:

```bash
apm install -g <owner>/<repo> --target opencode,codex
```

Falls auch die Skills vollständig targetspezifisch statt unter `~/.agents/skills/` liegen sollen:

```bash
apm install -g <owner>/<repo> \
  --target opencode,codex \
  --legacy-skill-paths
```

## Wichtiger Punkt zum OpenCode-Pfad

Auf deinem System ist die Situation bestätigt:

```text
~/.opencode/agents/         12 Fachagenten
~/.config/opencode/agents/   3 weitere Agenten
```

Dein gewünschtes Ziel ist:

```text
/home/visimeos/.opencode/agents/
```

Die aktuelle APM-Implementierung verwendet bei `--global --target opencode` allerdings fest:

```text
~/.config/opencode/agents/
```

Das ist auch OpenCodes dokumentierter Standardpfad. `~/.opencode/agents/` entspricht einer alternativen beziehungsweise benutzerspezifischen OpenCode-Konfiguration. APM berücksichtigt diesen Pfad derzeit nicht automatisch.

Daher müssen wir im Design zwei Dinge trennen:

1. **APM-Paketmodell:** ein Paket mit echten Skills und Agenten – entschieden.
2. **OpenCode-Zielauflösung:** der Installationsablauf muss den tatsächlich verwendeten globalen OpenCode-Pfad erkennen, statt blind `~/.config/opencode` anzunehmen.

Meine Empfehlung für ein öffentliches Paket:

```text
1. Standardpfad oder aktive OpenCode-Konfiguration erkennen
2. vorhandene Agentenverzeichnisse prüfen
3. Nutzer den Zielpfad bestätigen lassen
4. OpenCode-Agenten in das bestätigte globale Verzeichnis projizieren
5. Codex weiterhin regulär über APM verwalten
```

Dabei darf `/home/visimeos` natürlich nicht fest codiert werden; verwendet würde beispielsweise `$HOME/.opencode/agents`.

Die nächste Entscheidung ist deshalb: Soll `$HOME/.opencode/agents` für alle Paketnutzer verbindlich sein, oder soll der Initialisierungsablauf den aktiven OpenCode-Agentenpfad erkennen und gegebenenfalls nachfragen? Ich empfehle die Erkennung.

### Quellen

- [OpenCode: Agent files](https://github.com/anomalyco/opencode/blob/dev/packages/web/src/content/docs/agents.mdx)
- [APM Targets Matrix](https://microsoft.github.io/apm/reference/targets-matrix/)
- [APM OpenCode target implementation](https://github.com/microsoft/apm/blob/main/src/apm_cli/integration/targets.py)

---

## User

standardpfad von apm ist ok für opencode.

---

## Assistant

**Tool: todowrite**

---

## Assistant

Festgehalten:

- **Ein einziges APM-Paket**
- echte APM-Skills und APM-Fachagenten
- globale Installation für `opencode,codex`
- APM-Standardpfade werden akzeptiert
- keine projektspezifische Installation
- MCP-Konfiguration nicht durch APM, sondern über `init-mcps`

Voraussichtliche Installation:

```bash
apm install -g <owner>/<repo> --target opencode,codex
```

## Nächster Designabschnitt: verlässliche Verknüpfung

Ich empfehle einen zentralen, maschinenlesbaren Workflow-Katalog als einzige Quelle für Übergänge und Abhängigkeiten:

```yaml
workflows:
  work:
    skill: work
    requires:
      workflows: [plan]
      mcps: [gortex]
    delegates:
      backend: backend-engineer
      frontend: frontend-engineer
      database: db-engineer
      infrastructure: tf-infra-engineer
    transitions:
      success: review
      defect: debug

agents:
  backend-engineer:
    required_mcps: [gortex]
    optional_mcps: [context7]
  qa-reviewer:
    required_mcps: [gortex]
    optional_mcps: [chrome-devtools]

mcps:
  gortex:
    purpose: code-intelligence
    fallback: serena
  context7:
    purpose: library-documentation
```

Der Katalog würde als Ressource eines Kern-Skills mitinstalliert, beispielsweise:

```text
.apm/skills/workflow-core/
├── SKILL.md
└── references/
    ├── workflow-map.yaml
    ├── handoff-contract.md
    └── mcp-policy.md
```

### Verbindliche Referenzen

Workflow-Skills verwenden ausschließlich stabile IDs:

```text
Skill:      plan
Fachagent:  pm-planner
MCP:        gortex
Übergang:   plan → work
```

Keine Referenz auf:

- Installationspfade
- OpenCode- oder Codex-Dateiformate
- konkrete Modellnamen
- private Benutzerkonfigurationen

APM übernimmt die Transformation der Fachagenten. Die Workflow-Logik bleibt clientunabhängig.

### Automatische Konsistenzprüfung

Ein Paketvalidator prüft vor Veröffentlichung:

1. Jeder referenzierte Workflow-Skill existiert.
2. Jeder Fachagent existiert unter `.apm/agents/`.
3. Jede MCP-ID ist im Katalog bekannt.
4. Jeder Übergang besitzt ein gültiges Ziel.
5. Erforderliche Übergaben entsprechen dem Handoff-Vertrag.
6. Kein Workflow endet unbeabsichtigt ohne Review oder Abschluss.
7. Reparaturschleifen sind begrenzt.
8. Gortex/Serena-Fallbacks sind widerspruchsfrei.

Zur Laufzeit prüft ein Workflow nur die für ihn relevanten Voraussetzungen. Fehlt beispielsweise `gortex`, verweist er gezielt auf `init-mcps`, statt unstrukturiert mit anderen Werkzeugen fortzufahren.

Soll dieser **zentrale Workflow-Katalog als Single Source of Truth** die verbindliche Grundlage für alle Workflow-, Fachagenten- und MCP-Verweise bilden?

---

## User

ok. ist damit das problem gelöst, das ich mit oma hatte? mit zu vielen revision sessions wegen irgendwelchen digests?

---

## Assistant

**Tool: gortex_explore**

---

## Assistant

**Tool: gortex_read**

---

## Assistant

**Noch nicht allein durch den Workflow-Katalog.** Dieser verhindert falsche Verweise zwischen Workflows, Fachagenten und MCPs. Das OMA-Problem mit den vielen Revision-Sessions entstand zusätzlich durch dessen Ausführungs- und Evidence-Protokoll.

Die bestehende OMA-Struktur besitzt einen eigenen Session-Index, erkennbar unter `.opencode/plugins/oma/state-marker.ts::sessionsDir`. Die konkrete Digest-Logik wurde bei der aktuellen Lokalisierung nicht vollständig gefunden; das bekannte `artifact-key binding mismatch` zeigt aber genau das Problem: Ein Metadatenfehler löste weitere Revisionen aus, obwohl Planung und technische Verifikation bereits erfolgreich waren.

## Zusätzliche Lösung: keine Digests als Workflow-Gate

Für das neue Paket sollten wir festlegen:

1. **Keine Authority-Digests für normale Arbeitsabläufe.**
2. **Keine Digest-Kette zwischen Plan, Umsetzung, Review und Abschluss.**
3. **Keine neue Session wegen eines Metadaten- oder Evidence-Fehlers.**
4. Ein Workflow behält während seiner gesamten Ausführung dieselbe `run_id`.
5. Eine Revision entsteht nur bei einer **inhaltlichen Änderung** von Ziel, Umfang, Architektur oder Akzeptanzkriterien.
6. Fehlende Logs, falsche Referenzen oder Formatfehler werden innerhalb desselben Laufs repariert.
7. Ein fehlgeschlagener Review führt zum bestehenden Arbeitsschritt zurück, nicht zu einer neuen Planungssession.
8. Automatische Reparaturschleifen werden begrenzt, beispielsweise auf zwei Versuche.
9. Danach wird der Nutzer gefragt, statt weitere Revisionen zu erzeugen.
10. Kryptografische Hashes bleiben optional für Releases, heruntergeladene Artefakte oder sicherheitskritische Nachweise – aber nicht für Workflow-Steuerung.

## Schlanker Laufzustand

Statt Digest-Graph und Revision-Sessions genügt ein kleiner Laufzustand:

```yaml
run_id: work-20260927-001
workflow: work
phase: review
attempt: 1
plan: docs/plans/example.md
implementation_status: complete
review_status: changes-requested
next: return-to-implementation
```

Der Zustand enthält keine selbstreferenziellen Hashes. Der Workflow-Katalog beschreibt die statischen Übergänge; der Laufzustand hält lediglich fest, wo sich die aktuelle Aufgabe befindet.

## Revisionsregel

```text
Inhaltliche Planänderung
  → Revision erhöhen

Fehlender Nachweis, Formatfehler, falscher Artifact-Key,
Digest-/Metadatenfehler oder fehlgeschlagener technischer Check
  → im selben Lauf korrigieren

Unklarer Scope oder widersprüchliche Nutzeranforderung
  → Nutzer fragen, keine automatische Revision
```

Damit wäre das konkrete OMA-Problem tatsächlich beseitigt: **Ein technischer oder formaler Nachweisfehler kann keine Kaskade neuer Revision-Sessions mehr auslösen.**

Soll diese digestfreie, auf einen stabilen Lauf begrenzte Ausführungsregel verbindlicher Bestandteil des Designs werden?

---

## User

schreib mal kurz ein Zwischen Protokoll in dieses Repository, damit diese Informationen bei der nächsten Kompaktion nicht verloren gehen.

---

## Assistant

**Tool: gortex_search**

**Tool: todowrite**

---

## Assistant

**Tool: gortex_change**

---

## Assistant

**Tool: gortex_edit**

---

## Assistant

**Tool: gortex_edit**

---

## Assistant

**Tool: gortex_edit**

---

## Assistant

**Tool: gortex_change**

**Tool: todowrite**

---

## Assistant

Zwischenprotokoll wurde gespeichert:

```text
docs/zwischenprotokoll-2026-09-27.md
```

Enthalten sind:

- bestätigte APM-/Agenten-/Skill-Architektur
- globale MCP-Liste und `init-mcps`
- Workflow-Katalog als Single Source of Truth
- Regeln gegen Digest-getriebene Revisionskaskaden
- offene Designentscheidungen

Die Datei wurde erstellt, committed und neu indiziert.

---

## User

/home/visimeos/Downloads/deep-research-report.md Was hältst du davon, wenn wir hiervon als Grundlage ausgehen? und das einem design.md machen wir dann ein prd?

---

## Assistant

**Tool: read**

**Tool: gortex_read**

**Tool: skill**

---

## Assistant

**Tool: read**

---

## Assistant

Als **Ideen- und Prüfkatalog** ist der Bericht nützlich, aber nicht als ungeprüfte fachliche Grundlage.

## Was wir übernehmen sollten

Sehr passend für unser Vorhaben sind:

- der Stresstest `Planner → DB → Backend → Test → Reviewer`
- deterministische Workflow-Übergänge
- klar begrenzte Fachagenten
- Failure-Mode-Matrix
- Wiederaufnahme nach Fehlern
- Beobachtbarkeit und verständliche Logs
- explizite MCP- und Tool-Berechtigungen
- begrenzte Parallelität
- Trennung von Ausführung und unabhängigem Review

Das bestätigt unseren Workflow-Katalog und die digestfreie Laufsteuerung.

## Schwächen des Berichts

Der Bericht enthält mehrere Warnzeichen:

- OpenCode/OMA wird als „OpenModelArchitecture“ und Microsoft-gestützt beschrieben; das passt nicht zu unserem OMA.
- Viele Aussagen verwenden „vermutlich“, „wahrscheinlich“ oder „scheint“, fließen aber trotzdem in numerische Scores ein.
- Es fehlen konkrete Quellenlinks pro Behauptung.
- Unterschiedliche Kategorien werden verglichen: Coding-Clients, Frameworks, Orchestratoren und komplette Plattformen.
- Einige bekannte Systeme werden als unbekannt geführt.
- Aussagen zu Recovery, Sandboxing und Laufzeit-Enforcement sind teilweise spekulativ oder widersprüchlich.
- Der Bericht bewertet vollständige Laufzeitplattformen. Unser APM-Paket kann nicht dieselben Garantien wie eine eigene Workflow-Engine oder Containerplattform erzwingen.

Daher:

> Den Kriterienkatalog verwenden, aber Scores und Produktbehauptungen nicht ungeprüft übernehmen.

## Empfohlene Dokumentreihenfolge

Ich würde **nicht zuerst DESIGN.md und daraus anschließend ein PRD erzeugen**. Besser ist:

```text
Research Report
      ↓
PRD – Was und warum?
      ↓
DESIGN.md – Wie wird es technisch gelöst?
      ↓
Implementierungsplan
```

### 1. Research-Basis

Der Bericht kommt kommentiert nach:

```text
docs/research/agent-harness-comparison.md
```

Dabei kennzeichnen wir:

- bestätigte Fakten
- unbestätigte Aussagen
- für unser Produkt relevante Prinzipien
- bewusst nicht übernommene Aussagen

### 2. PRD

Das PRD definiert:

- Zielgruppe
- Nutzerprobleme
- gewünschter Arbeitsfluss
- funktionale Anforderungen
- Qualitätsanforderungen
- Nicht-Ziele
- Erfolgskriterien
- Failure-Mode-Akzeptanzkriterien

### 3. `DESIGN.md`

Danach beschreibt `DESIGN.md`:

- APM-Paketstruktur
- Workflow-Katalog
- Skills und native Fachagenten
- OpenCode-/Codex-Projektionen
- `init-mcps`
- Laufzustand ohne Digest-Ketten
- Delegation, Review und Recovery
- Validierung und Tests

Unsere bisherigen Entscheidungen gehen dabei nicht verloren: Sie werden zunächst als verbindliche Anforderungen ins PRD und anschließend als technische Lösung ins Design übernommen.

**Empfehlung:** Bericht als Research-Eingabe sichern, dann zuerst das PRD und danach `DESIGN.md` erstellen. Soll ich mit der kommentierten Research-Basis und dem PRD-Entwurf beginnen?

---

## User

[Image 1] Siehe dieses Bild für weiteren Kontext.Es befindet sich auch im Repo, glaube ich.

---

## Assistant

**Tool: gortex_analyze**

---

## Assistant

**Tool: gortex_analyze**

---

## Assistant

**Tool: glob**

---

## Assistant

**Tool: gortex_search**

---

## Assistant

**Tool: read**

---

## Assistant

Das Bild ergänzt den Bericht sehr gut und bestätigt klar: **PRD zuerst, danach DESIGN.md**.

Die Bilddatei liegt nicht im aktuellen Repository, sondern hier:

```text
/home/visimeos/Projects/agentic-workflow-template/.agents/agentic-workflow-framework.png
```

## Was wir übernehmen sollten

### Grundablauf

```text
Research
   ↓
PRD
   ↓
Projektplanung
   ↓
Feature-/Taskplanung
   ↓
Implementierung
   ↓
Validierung
   ↓
Iteration
```

### Zentrale Prinzipien

- **PRD als fachliche Quelle:** Was wird gebaut und warum?
- **DESIGN.md als technische Quelle:** Wie wird es gebaut?
- **Zweistufige Planung:**
  - Projektplanung einmalig
  - Taskplanung pro Feature
- **Modulare Regeln:** Agenten erhalten nur relevanten Kontext.
- **Subagenten zur Kontextisolation:** Fachagenten liefern kompakte Ergebnisse zurück.
- **Plan → Implement → Validate:** klare Schleife mit unabhängigem Review.
- **Context Reset:** Ausführung beginnt mit frischem Kontext und einem dauerhaften Handoff.
- **Wiederkehrende Abläufe als Skills:** aber nur, wenn sie tatsächlich stabil und mehrfach nutzbar sind.
- **Git-Historie als Langzeitkontext:** ergänzend zu PRD und Design.
- **System Evolution:** wiederholt auftretende Fehler führen zu verbesserten Regeln oder Skills.

## Anpassung gegenüber dem Bild

Einige Regeln sollten wir präziser formulieren:

- „Context Reset“ bedeutet **neuer Ausführungskontext**, nicht neue Revision-Session.
- Der neue Kontext liest PRD, Design, Plan und Handoff; er übernimmt keine komplette alte Unterhaltung.
- Git ist historische Evidenz, aber nicht die alleinige Wahrheit.
- Nicht jeder Fehler erzeugt sofort eine neue Regel. Erst wiederkehrende oder systemische Fehler tun das.
- Die Iterationsschleife behält dieselbe `run_id`.
- Keine Digest-Ketten oder automatischen Revision-Sessions.
- Ein gescheiterter Test führt zurück zur Umsetzung, nicht zu einer neuen Planung, sofern sich der Scope nicht ändert.

## Empfohlene Dokumentstruktur

```text
PRD.md
DESIGN.md

docs/
├── research/
│   ├── agent-harness-comparison.md
│   └── agentic-workflow-framework.png
├── plans/
│   └── <feature>.md
└── zwischenprotokoll-2026-09-27.md
```

Dabei gilt:

| Dokument | Verantwortung |
|---|---|
| `PRD.md` | Zielgruppe, Probleme, Anforderungen, Nicht-Ziele, Erfolgskriterien |
| `DESIGN.md` | Paketarchitektur, Workflows, Agenten, MCPs, Laufzustand, Recovery |
| Feature-Plan | konkrete Änderung, Aufgaben, Tests und Abnahme |
| Handoff/Laufzustand | aktueller Fortschritt innerhalb derselben Ausführung |

Der Deep-Research-Bericht bleibt eine **Research-Eingabe**, nicht die Source of Truth. PRD und DESIGN übernehmen nur belastbare, für unser Paket relevante Schlussfolgerungen.

**Mein Vorschlag:** Als Nächstes erstellen wir zuerst `PRD.md`; nach dessen Freigabe leiten wir daraus `DESIGN.md` ab. Soll ich mit dem PRD-Entwurf beginnen?

---

## User

kein prd jetzt. Ich meinte diesen Arbeitsfloss als Blaupause für die Workflows, die wir bauen. ich will ja eine alternative zu oma bauen, die leaner und cleaner ist

---

## Assistant

**Tool: gortex_explore**

---

## Assistant

Verstanden — **kein PRD jetzt**. Das Bild soll die **Blaupause für unser Workflow-System** werden. Wir bauen damit eine schlankere, transparentere Alternative zu OMA.

Der Deep-Research-Bericht liefert ergänzend Prüfkriterien und Fehlerszenarien, aber das Bild definiert den eigentlichen Arbeitsfluss.

## Vorgeschlagener Kernablauf

```text
init-project? → prime → brainstorm? → plan
                                  │
                                  ▼
                         frischer Kontext
                                  │
                                  ▼
                              work
                                  │
                                  ▼
                       unabhängiges review
                         │              │
                      Fehler          bestanden
                         │              │
                         └──→ work      └──→ commit/Abschluss
                              gleicher Lauf
```

- `init-project` und `brainstorm` sind optional.
- `prime`, `plan`, `work` und `review` bilden den Kern.
- Eine Korrektur bleibt im selben Lauf.
- Ein Scope-Wechsel führt zurück zu `plan`, aber nicht zu einer neuen Revisionssession.

## Fünf öffentliche Kern-Workflows

### 1. `prime`

Baut zu Beginn ein schlankes mentales Modell auf:

- Repository-Anweisungen
- relevante Dokumentation
- Architektur
- Quellstruktur
- Git-Status und relevante Historie
- verfügbare MCPs
- keine Änderungen

Ergebnis ist eine kurze Kontextzusammenfassung, kein umfangreiches Sitzungsartefakt.

### 2. `brainstorm`

Optional für noch unklare Vorhaben:

- Anforderungen und Grenzen klären
- zwei oder drei Ansätze vergleichen
- Entscheidung bestätigen lassen
- Ergebnis als kurze Designentscheidung sichern

Kein Plan, keine Implementierung und keine automatisch erzeugten Revisionen.

### 3. `plan`

Erzeugt einen ausführbaren Feature- oder Taskplan:

- Ziel und Erfolgskriterien
- betroffene Komponenten
- benötigte Fachagenten
- relevante MCPs
- Aufgabenreihenfolge
- Tests und Validierung
- Risiken und Abbruchbedingungen

Bei Greenfield-Projekten kann `plan` auf ein vorhandenes PRD bestehen. Bei bestehenden Projekten verwendet es Code, Dokumentation und Nutzeranforderung.

### 4. `work`

Führt den Plan schrittweise aus:

- delegiert an passende native Fachagenten
- gibt jedem Agenten nur den notwendigen Kontext
- verwendet Gortex als primäre Code-Intelligence
- dokumentiert Ergebnisse direkt im Plan beziehungsweise Handoff
- führt vorgesehene Tests aus
- erzeugt keine neuen Planungs- oder Revision-Sessions

Nur der koordinierende Workflow darf Fachagenten starten. Fachagenten dürfen nicht unkontrolliert weitere Agentenketten erzeugen.

### 5. `review`

Läuft mit frischem Kontext und einem anderen Fachagenten:

- Plan und Akzeptanzkriterien lesen
- Diff und Tests überprüfen
- Sicherheits-, Qualitäts- und Dokumentationsaspekte prüfen
- bestanden oder konkrete Findings melden

Bei Findings:

```text
review → work → review
```

Die Schleife ist begrenzt, beispielsweise auf zwei automatische Korrekturrunden. Danach wird der Nutzer gefragt.

## Kleine Utility-Skills

Diese stehen neben dem Kernablauf, erweitern ihn aber nicht um neue Orchestrierungsebenen:

- `init-project` – Repository-Grundstruktur
- `init-mcps` – globale MCP-Einrichtung
- `commit` – explizit autorisierter Git-Commit
- `evolve` – wiederkehrende Prozessprobleme in Regeln oder Skills überführen

`evolve` reagiert nur auf wiederkehrende oder systemische Probleme. Nicht jeder einzelne Bug erzeugt sofort eine neue Regel.

## Fachagenten und MCPs

Der zentrale Workflow-Katalog ordnet Aufgaben direkt zu:

```yaml
task_routes:
  architecture:
    agent: architecture-reviewer
    mcps: [gortex, context7]

  backend:
    agent: backend-engineer
    mcps: [gortex, context7]

  frontend:
    agent: frontend-engineer
    mcps: [gortex, context7, chrome-devtools]

  database:
    agent: db-engineer
    mcps: [gortex]

  review:
    agent: qa-reviewer
    mcps: [gortex, chrome-devtools]
```

Weitere MCPs werden nur bei passender Aufgabe verwendet:

- `forgejo-api-mcp` für Forgejo
- `youtube-transcript` für Videos
- `serena` als konfigurierter Fallback zu Gortex

## Was wir von OMA nicht übernehmen

- Digest-Ketten
- Authority-Digests
- Revision-Sessions für formale Fehler
- State-Emitter und Checkpoint-Zeremonien
- konkurrierende Orchestratoren wie `work`, `orchestrate`, `ultrawork` und `ralph`
- verpflichtende Review-Kaskaden
- Workflow-Duplikate als Skill, Command und separate Workflow-Datei
- versteckte Plugin-/Hook-Abhängigkeiten für den normalen Ablauf
- vollständige Gesprächshistorien als Handoff
- unbegrenztes Subagent-Spawning

Stattdessen verwenden wir:

```text
wenige Workflows
+ native Fachagenten
+ explizite Übergänge
+ kleine Handovers
+ frische Kontexte
+ begrenzte Iteration
```

Damit ist das Bild nicht bloß Inspiration, sondern das **primäre Prozessmodell unserer leanen OMA-Alternative**.

Ist dieser Kern aus `prime → plan → work → review`, ergänzt um optionales `brainstorm` und wenige Utility-Skills, die gewünschte Richtung?

---

## User

Und sollten dann zum Beispiel nicht bei der Planung das Ganze in einzelne Aufgaben heruntergebrochen werden, welche dann den Fachagenten zugewiesen werden? Und ich hatte zuvor gefragt, ob der Skill Deep-init nicht gemerged werden sollte? plan-knowledge-governance, maintain-repository, deepinit und stack-set?

---

## Assistant

**Tool: gortex_explore**

**Tool: skill**

**Tool: skill**

---

## Assistant

**Tool: gortex_search**

---

## Assistant

**Tool: gortex_read**

---

## Assistant

Ja, genau. **`plan` muss die Arbeit in ausführbare Aufgaben zerlegen und jede Aufgabe einem Fachagenten zuweisen.** Meine vorherige Darstellung war zu grob.

## Aufgabe als zentrale Ausführungseinheit

Jede geplante Aufgabe sollte mindestens enthalten:

```yaml
id: T03
title: REST-Endpunkt implementieren
goal: Kundenprofil abrufbar machen
depends_on: [T01, T02]
agent: backend-engineer
scope:
  - src/customers/
required_mcps:
  - gortex
optional_mcps:
  - context7
inputs:
  - Architekturentscheidung ADR-003
acceptance:
  - Endpoint liefert 200 und 404 korrekt
  - Autorisierung wird geprüft
verification:
  - Unit-Tests
  - Integrationstest
status: pending
```

Der Plan ist damit nicht nur Text, sondern ein kleiner Task-Graph:

```text
T01 Datenmodell       → db-engineer
         │
         ▼
T02 Migration         → db-engineer
         │
         ├──────────────┐
         ▼              ▼
T03 Backend-API       T04 Frontend-Vorbereitung
→ backend-engineer   → frontend-engineer
         │              │
         └──────┬───────┘
                ▼
T05 Integrationstest → qa-reviewer
                │
                ▼
T06 Review           → unabhängiger qa-reviewer
```

### Regeln

- Eine Aufgabe hat genau einen verantwortlichen Fachagenten.
- Abhängigkeiten bestimmen die Reihenfolge.
- Nur wirklich unabhängige Aufgaben dürfen parallel laufen.
- Der koordinierende Workflow weist Agenten zu.
- Fachagenten dürfen nicht eigenmächtig weitere Agentenketten erzeugen.
- Jeder Fachagent erhält nur seine Aufgabe und den notwendigen Kontext.
- Der Reviewer darf nicht der Implementierer derselben Aufgabe sein.
- Statusänderungen stehen direkt im Plan; keine Digest- oder Revisionssession.

---

# Zusammenführung der Initialisierungs-Skills

Ja, diese Fähigkeiten gehören aus Nutzersicht weitgehend in **einen einzigen Workflow `init-project`**:

```text
deepinit
+ stack-set
+ plan-knowledge-governance
+ maintain-repository
→ init-project
```

Aber wir sollten nicht vier große Skill-Texte zu einem noch größeren Skill zusammenkopieren. Das würde wieder die OMA-Komplexität erzeugen.

Die richtige Lösung ist:

> **Ein öffentlicher Workflow, mehrere kleine interne Phasen.**

## Vorgeschlagener `init-project`-Ablauf

### Phase 1: Repository verstehen

Aus `deepinit`:

- Greenfield oder bestehendes Repository erkennen
- Projektstruktur und Architektur untersuchen
- vorhandene Dokumentation erfassen
- relevante Grenzen und Domänen bestimmen

### Phase 2: Stack erkennen

Aus `stack-set`:

- Sprachen, Frameworks und Buildsysteme erkennen
- Backend, Frontend, Mobile, Datenbank und Infrastruktur klassifizieren
- passende Fachagenten bestimmen
- relevante Validierungsbefehle erkennen

Der bisherige `stack-set` ist mit über 400 Zeilen und vielen generierten Templates zu umfangreich. Wir übernehmen nur:

- Erkennung
- Klassifikation
- Fachagenten-Routing
- nachweisbare Stack-Fakten

Keine ungefragte Generierung von Snippets und Technologievorlagen.

### Phase 3: Repository-Baseline prüfen

Aus `maintain-repository`:

- Git-Zustand
- verschachtelte Repositories
- Symlinks und Pfadprobleme
- Secrets und sensible Dateien
- Build-Artefakte
- Manifest-/Lockfile-Konsistenz
- vorhandene Qualitäts- und CI-Befehle

Diese Phase ist zunächst lesend. Findings werden gemeldet; Änderungen erfolgen nur nach Zustimmung.

### Phase 4: Wissensarchitektur bestimmen

Aus `plan-knowledge-governance`:

- authoritative Dokumente bestimmen
- veraltete oder konkurrierende Quellen erkennen
- Supersession-Regeln definieren
- Code-zu-Dokument-Verbindungen festlegen
- Aktualisierungsverantwortung definieren

Wichtig: Es wird kein separates Governance-Großprojekt erzeugt. Für normale Repositories reicht ein kleiner Abschnitt in der Dokumentationsstruktur.

### Phase 5: Lean Harness erzeugen

Aus `deepinit`:

```text
AGENTS.md          kurze Inhaltsübersicht
ARCHITECTURE.md    Domänen und Abhängigkeiten
docs/
├── plans/
├── decisions/
├── references/
└── handoff.md
```

Nur nachweisbar benötigte Dateien werden erzeugt. Keine leeren Dokumentbibliotheken auf Vorrat.

### Phase 6: Validieren

- alle Links existieren
- keine widersprüchlichen Quellen
- erkannter Stack stimmt mit Manifesten überein
- Workflow- und Fachagentenreferenzen sind gültig
- bestehende Nutzerinhalte wurden nicht überschrieben

## Was bleibt separat?

Ich würde nur `maintain-repository` in reduzierter Form zusätzlich als öffentlichen Utility-Skill `repo-audit` behalten, weil Repository-Wartung auch lange nach der Initialisierung benötigt wird.

```text
init-project
├── nutzt Stack-Erkennung intern
├── nutzt Knowledge-Governance intern
├── nutzt Repository-Audit intern
└── erzeugt den schlanken Repository-Harness

repo-audit
└── kann später unabhängig erneut ausgeführt werden
```

`stack-set` und `plan-knowledge-governance` wären danach keine separaten Nutzer-Workflows mehr. Ihre brauchbaren Teile werden interne Ressourcen von `init-project`.

## Ergebnis: schlankes öffentliches Workflow-Set

```text
Initialisierung:
  init-project
  init-mcps
  repo-audit

Arbeit:
  prime
  brainstorm
  plan
  work
  review
  commit

Verbesserung:
  evolve
```

Das ist deutlich cleaner als OMA: ein Einstiegspunkt pro Nutzerabsicht, ohne vier überlappende Initialisierungs-Workflows.

**Empfehlung:** `deepinit`, `stack-set` und die Bootstrap-Aspekte von `plan-knowledge-governance` vollständig in `init-project` integrieren; `maintain-repository` darin verwenden, aber zusätzlich als kleinen `repo-audit`-Utility erhalten.

Die automatische Gortex-Lokalisierung des vollständigen Overlaps blieb teilweise unbestätigt. Bestätigte Anker sind `oma-arbeitsmasse/workflows/deepinit.md`, `.codex/skills/stack-set/SKILL.md` und `evaluieren/maintain-repository/scripts/audit_repository.py::_finding`.

Soll dieses Modell – **ein öffentlicher `init-project` plus separat wiederverwendbares `repo-audit`** – verbindlich werden?

---


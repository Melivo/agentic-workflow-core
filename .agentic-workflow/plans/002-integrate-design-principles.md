# Situative Designmethoden und SWE-Grundsätze in Core integrieren

## Bestätigung und Ziel

Dieser Plan wurde am 2026-10-08 im Gespräch einschließlich des Zusatzes zum aktuellen MCP-Routing ausdrücklich bestätigt. Er autorisiert die hier beschriebenen Tasks erst im Rahmen eines separat gestarteten `core-execute`-Laufs; die Planerstellung selbst startet keine Implementierung.

Ziel: Die vom Benutzer bereitgestellten SWE-Grundsätze und passende Clairvoyance-Methoden intern in Core integrieren. Core benötigt dafür keine separat installierten Clairvoyance- oder SWE-Skills. Aktuell verfügbare, geeignete MCP-Fähigkeiten werden situativ genutzt, ohne Scope, Providerpriorität oder Autorisierung zu erweitern.

## Geltungsbereich und Nicht-Ziele

Kanonische Änderungen erfolgen ausschließlich an den unten benannten Paketquellen unter `.apm/` sowie an `README.md` und `DESIGN.md`. Generierte Projektionen unter `.agents/`, `.opencode/` und `.codex/` bleiben unverändert.

Ausgeschlossen sind Builds, Compiles, Bundles, Packaging, Installation, Änderungen globaler Benutzeranweisungen, Agenten- oder Modellkonfiguration, neue Paketabhängigkeiten, Commits, Pushes, Releases, Deployments und produktive oder destruktive Aktionen. Kostenpflichtige Live-Evaluationen benötigen eine separate Freigabe. Workflowsteuerung, Tasktrennung, Verhaltenserhaltung und Artefaktformate werden nicht geändert.

## Bestätigte Entscheidungen

- Die vom Benutzer bereitgestellten SWE-Grundsätze bilden die gemeinsame Basis für Coding-Aufgaben. Sie umfassen klare Verantwortlichkeiten, Kohäsion, unabhängig veränderliche Belange, kleine stabile Schnittstellen, Information Hiding, begründete Abhängigkeiten und unabhängige Testbarkeit.
- Clairvoyance liefert situative Vertiefungen, keinen obligatorischen Komplettscan. Methoden erhalten konkrete Auslöser, Ausschlüsse, Evidenzbedarf, Grenzen und Abschlussbedingungen.
- Fachmethoden bleiben außerhalb von `core-shared`. Gemeinsame Fachreferenzen werden unter `core-architecture/references/` kanonisch gehalten und direkt von Verbrauchern verlinkt; ihr Laden aktiviert nicht automatisch den Architekturworkflow.
- Subagenten behalten ihre kurzen Eigentümer-Skill-Verweise. Keine duplizierten Regeln oder zusätzliche Agentensteuerung.
- Autorisierung, Verhaltenserhaltung, Tasktrennung und Reviewformate bleiben unverändert. Entdeckte Strukturprobleme erlauben keine ungeplanten Refactorings; außerhalb des bestätigten Tasks werden sie als Folgearbeit geroutet.
- Die Abschlussprüfung betrachtet tatsächlich betroffene Bereiche. Nicht anwendbare Punkte werden benannt. Ein negativer Befund löst Nachprüfung aus, nicht automatisch einen Umbau.
- `skill-creator` und `context-debloater` sind lokale Authoring-Werkzeuge, keine neuen Paketabhängigkeiten. Der Debloater arbeitet ausschließlich report-only auf einer expliziten Markdown-Dateiliste.
- Clairvoyance-Übernahmen erhalten nachvollziehbare Herkunft und den MIT-Lizenzhinweis. Alle 16 Quellskills werden übernommen, konsolidiert oder begründet ausgeschlossen; nicht jeder Quellskill wird zu einer eigenen Referenzdatei.
- Inhalte des privaten, unlizenzieren `swe-quality-check` werden nicht übernommen. Als SWE-Basis dienen die ausdrücklich bereitgestellten Benutzergrundsätze. Der private Skill darf lediglich als Vergleichsquelle betrachtet werden.

## Fachliche Zerlegung

| Signal | Interne Methode | Hauptverbraucher |
|---|---|---|
| Änderungen verteilen sich unerwartet | Komplexitätsdiagnose, Wissenseigentum, versteckte Kopplung | Architektur, Refactoring, Audit |
| Schichten oder Wrapper wirken redundant | Abstraktionsqualität und Modultiefe | Architektur, Refactoring |
| Aufrufer brauchen viel Setup oder Sonderwissen | Schnittstellengeneralisierung, Defaults, Komplexitätsverlagerung | Implementierung, Architektur |
| Fehlerbehandlung wird unübersichtlich | Fehleroberfläche und sichere Wiederherstellung | Implementierung, Review |
| Änderungen wirken angeflickt | Designentwicklung, Sonderfälle und dupliziertes Wissen | Implementierung, Review |
| Namen oder Kommentare verschleiern Verträge | Benennung, Schnittstellendokumentation und Obviousness | Implementierung, Review |
| Eine materielle Entscheidung hat mehrere plausible Wege | Alternativenvergleich, gegebenenfalls Pre-Mortem | Architektur, Brainstorm |
| Mehrere Warnsignale treten zusammen auf | Ursachengruppierung statt mehrfacher Findings | Review, Audit |

`diagnose`, `design-review` und `red-flags` werden in interne Auswahlregeln zerlegt. Pauschale Komplettscans, feste Investitionsquoten, unbelegte Tokenersparnis und automatische Refactoringaufforderungen werden nicht übernommen. Warnsignale und Metriken sind keine Defekte ohne belegte Ursache und Auswirkung. Legitime Adapter, reale Domänenkopplung, erforderliche Konfiguration und bewusst öffentliche Verträge bleiben möglich.

## Zusatz: aktuell verfügbare MCP-Fähigkeiten

T02 ergänzt `core-shared/references/tool-routing.md` um situatives, capability-basiertes Routing:

1. Vor der Toolwahl benötigte Fähigkeit und relevante aktuell verfügbare Operation feststellen; vorhandene Laufzeitdeklarationen und gezielte Discovery nutzen.
2. Passende MCPs gezielt einsetzen, statt ausschließlich fest benannte Provider vorauszusetzen. Keine pauschale Inventarisierung oder Nutzung aller MCPs.
3. Weitere Provider nach belegter Fähigkeit, Projektbezug, Freshness und Nebenwirkungen einordnen, ohne aktuelle projektspezifische Providernamen dauerhaft in Core einzubauen.
4. Die bestehende Providerpriorität und konkrete Projektanweisungen bewahren. Verfügbarkeit erweitert weder Scope noch Schreibberechtigungen; kein automatisches Provisionieren, Aktivieren oder Autorisieren von Providern.
5. Ausfälle, erlaubte Fallbacks und verbleibende Evidenzlücken sichtbar dokumentieren. Ersatzfähigkeiten nicht mit identischer Qualität oder Schreibberechtigung gleichsetzen.
6. Pflicht- und optionale Provider bleiben getrennt; nur tatsächlich unersetzliche Fähigkeiten dürfen einen Task blockieren.

T03 prüft Fälle mit verfügbarem, fehlendem und ungeeignetem MCP sowie verbotenen Nebenwirkungen.

## Repositoryevidenz und Authoring-Quellen

- `README.md`: `.apm/` ist die kanonische Quelle; Skill-Creator und Debloater sind lokale Authoring-Werkzeuge, keine Paketabhängigkeiten.
- `.apm/skills/core-shared/SKILL.md`: Shared enthält Workflowverträge, keine Fachmethodik.
- `.apm/skills/core-shared/references/tool-routing.md`: bestehende Reihenfolge für Gortex, Context7, projektspezifisches Serena, YouTube Transcript, Honcho und native Fallbacks.
- `.apm/skills/core-refactor/SKILL.md`: Charakterisierung und Produktionsrefactoring bleiben getrennt; beobachtbares Verhalten und Safety Net sind verbindlich.
- `.apm/skills/core-review/SKILL.md`: risikobasierte unabhängige Prüfung, kein Fix, keine eigene Agentensteuerung.
- `.apm/agents/`: Fachagenten laden ihren Eigentümer-Skill und duplizieren keine Fachmethodik.
- `.apm/skills/core-shared/assets/workflow-catalog.yaml`: die im Taskgraphen genannten Agenten- und Tool-IDs sind registriert.
- Lokale Clairvoyance-Quelle: `/home/visimeos/.config/opencode/clairvoyance/skills/`; MIT-Lizenz: `/home/visimeos/.config/opencode/clairvoyance/LICENSE`, Copyright 2026 Cody Bromley. Diese Pfade sind Authoring-Eingaben, keine Paket-Laufzeitverweise. Bei Ausführung Revision oder Quellenhashes erfassen.
- Bereitgestellte SWE-Quelle: Benutzertext `pasted-context-1.txt` im Auftrag. Den tatsächlich bereitgestellten Inhalt als Quelle verwenden; keinen unbekannten lokalen Dateipfad erfinden. Die Grundsätze sind in den bestätigten Entscheidungen oben zusammengefasst.
- Vergleichsquelle: `/home/visimeos/.config/opencode/skills/swe-quality-check/PROVENANCE.md` erklärt den privaten Skill als UNLICENSED; keine Textübernahme ohne neue Lizenzentscheidung.

Externe Quellen werden nur für das Authoring gelesen. Fehlende lokale Quellen oder Authoring-Werkzeuge werden sichtbar gemeldet, nicht als Laufzeitabhängigkeiten eingebaut. Kein Provider- oder Analyseartefakt wird zur zweiten Plan-Source-of-Truth.

## Taskgraph


```yaml
schema: plan/v1
status: Confirmed

tasks:
  - id: T01
    title: Interne Designmethoden konsolidieren
    agent: architecture-reviewer
    task: >
      Mit skill-creator die bereitgestellten SWE-Grundsätze und die
      Clairvoyance-Methoden in kompakte, deutschsprachige Referenzen
      zerlegen. Jede Methode erhält Auslöser, Ausschlüsse, Evidenzbedarf,
      Grenzen und Abschlussbedingungen. Herkunft und MIT-Hinweis erhalten.
      Externe Quellen sind Authoring-Eingaben, keine Laufzeitabhängigkeiten.
    context_paths:
      - .apm/skills/core-architecture/
      - .apm/skills/core-refactor/SKILL.md
      - .apm/skills/core-review/SKILL.md
      - .apm/skills/core-shared/references/
      - DESIGN.md
    scope:
      - .apm/skills/core-architecture/references/
      - .apm/skills/core-architecture/PROVENANCE.md
      - .apm/skills/core-architecture/THIRD_PARTY_NOTICES.md
    dependencies: []
    required_mcps: [gortex]
    optional_mcps: []
    acceptance:
      - id: AC01
        description: >
          SWE-Basis und alle 16 Clairvoyance-Skills sind nachvollziehbar
          übernommen, konsolidiert oder begründet ausgeschlossen.
      - id: AC02
        description: >
          Referenzen sind standalone, situativ und mit unveränderten
          Autorisierungsgrenzen sowie korrekter Herkunft versehen.
    checks:
      - id: CK01
        covers: [AC01, AC02]
        command: [git, diff, --check]
        cwd: "."
        pass: >
          Exitcode 0; zusätzlich vollständiger manueller Abgleich
          Quelle → Methode → Auslöser → Ausschluss, mit belegten
          Lizenzhinweisen und ohne externe Laufzeitverweise.

  - id: T02
    title: Methoden und aktuelles MCP-Routing in die Core-Skills einbinden
    agent: docs-curator
    task: >
      Die Referenzen direkt in den betroffenen Skills verlinken.
      Die SWE-Basis für Coding-Aufgaben und die Abschlussprüfung
      verankern; Vertiefungen ausschließlich durch konkrete Signale
      aktivieren. Bestehende Überschneidungen konsolidieren.
      Toolrouting um situative Nutzung aktuell verfügbarer MCP-Fähigkeiten
      ergänzen; Providerpriorität, Projektgrenzen, Autorisierung und
      sichtbare Fallbacks erhalten. Keine pauschale Providerabfrage.
      README und DESIGN an die bestätigte Integration anpassen.
      Keine Agentendefinitionen verändern; Workflowsteuerung und
      Autorisierungsverträge unverändert lassen.
    context_paths:
      - .apm/skills/
      - .apm/agents/
      - README.md
      - DESIGN.md
    scope:
      - .apm/skills/core-architecture/SKILL.md
      - .apm/skills/core-backend/SKILL.md
      - .apm/skills/core-frontend/SKILL.md
      - .apm/skills/core-mobile/SKILL.md
      - .apm/skills/core-database/SKILL.md
      - .apm/skills/core-tf-infra/SKILL.md
      - .apm/skills/core-debug/SKILL.md
      - .apm/skills/core-refactor/SKILL.md
      - .apm/skills/core-review/SKILL.md
      - .apm/skills/core-repo-audit/SKILL.md
      - .apm/skills/core-brainstorm/SKILL.md
      - .apm/skills/core-shared/references/tool-routing.md
      - README.md
      - DESIGN.md
    dependencies: [T01]
    required_mcps: [gortex]
    optional_mcps: []
    acceptance:
      - id: AC03
        description: >
          Betroffene Skills laden die Basis und passende Vertiefungen
          über direkte paketinterne Verweise ohne Regelduplikation.
      - id: AC04
        description: >
          Scope, Tasktrennung, Verhaltenserhaltung, Agentensteuerung,
          Paketabhängigkeiten und Reviewformate bleiben erhalten.
      - id: AC07
        description: >
          Toolrouting und betroffene Skills berücksichtigen geeignete
          aktuell verfügbare MCP-Fähigkeiten situativ, wahren bestehende
          Providerpriorität und melden erlaubte Fallbacks und Evidenzlücken.
          Verfügbarkeit erzeugt keine neue Autorisierung.
    checks:
      - id: CK02
        covers: [AC03, AC04, AC07]
        command: [git, diff, --check]
        cwd: "."
        pass: >
          Exitcode 0; zusätzlich manueller Link-, Routing- und
          Vertragsabgleich des Gesamtdiffs. Jeder Verbraucher hat
          einen erreichbaren Verweis und konkrete Ladebedingungen.
          Die MCP-Auswahl folgt Bedarf, aktueller Capability und
          bestehenden Prioritäten, nicht einer pauschalen Toolliste.

  - id: T03
    title: Integration und MCP-Routing unabhängig prüfen
    agent: qa-reviewer
    task: >
      Den Gesamtdiff unabhängig prüfen. Context-debloater nur auf
      einer expliziten Markdown-Dateiliste report-only ausführen.
      Skill-Creator-Strukturvalidierung auf geänderte Bundles anwenden.
      Positive, einfache, benachbarte und riskante Aufgaben als
      Routingfälle prüfen. Zusätzlich verfügbare, fehlende und
      ungeeignete MCPs sowie verbotene Nebenwirkungen prüfen.
      Statische Befunde ausdrücklich von beobachtetem Agentenverhalten
      unterscheiden. Keine Korrekturen und keine kostenpflichtigen
      Live-Evaluationen.
    context_paths:
      - .apm/skills/
      - .apm/agents/
      - apm.yml
      - README.md
      - DESIGN.md
    scope: []
    dependencies: [T02]
    required_mcps: [gortex]
    optional_mcps: []
    acceptance:
      - id: AC05
        description: >
          Strukturvalidierung und Debloater-Prüfung sind dokumentiert;
          relevante Konflikte, Duplikate und Referenzfehler sind geklärt.
      - id: AC06
        description: >
          Routingfälle belegen passende Auswahlregeln; keine
          Komplettscanpflicht oder implizite Refactoringfreigabe entsteht.
          Nicht ausgeführte Verhaltensevaluation bleibt sichtbar.
      - id: AC08
        description: >
          MCP-Prüffälle zeigen passende Auswahl bei Verfügbarkeit,
          erlaubten Fallback oder ehrliche Blockade bei fehlender Fähigkeit,
          Ausschluss ungeeigneter Tools und Schutz vor nicht autorisierten
          Nebenwirkungen. Statische Prüfung wird nicht als Live-Evidenz
          bezeichnet.
    checks:
      - id: CK03
        covers: [AC05, AC06, AC08]
        command: [git, diff, --check]
        cwd: "."
        pass: >
          Exitcode 0; zusätzlich unabhängige Prüfevidenz aus
          Skill-Creator, beiden Debloater-Skripten und Routingfällen
          einschließlich der MCP-Fälle. Fehlende Verhaltensevidenz
          wird nicht als Erfolg ausgegeben.
```

## Verifikation und Evidenzgrenzen

Die gepinnten Git-Prüfungen belegen ausschließlich Diffhygiene, nicht fachliche Erfüllung. Zusätzlich sind die jeweils unter `pass` genannten manuellen und Authoring-Prüfungen erforderlich. Eine Exitcode-0-Ausgabe ohne diesen Abgleich ist kein bestandenes Akzeptanzkriterium. Unversionierte neue Referenzen werden ausdrücklich in die Inhalts- und Linkprüfung einbezogen.

Die lokalen Authoring-Skripte werden bei Ausführung am tatsächlich vorhandenen Skillstand aufgelöst: `skill-creator/scripts/quick_validate.py` je geändertem Bundle sowie `context-debloater/scripts/analyze_markdown.py` und `context-debloater/scripts/consolidate_duplicates.py` mit derselben expliziten Workspace-/Target-Liste. Ihre Rubriken, Hashes, Invarianten und ausgeschlossenen Referenzen werden berücksichtigt. Skripte werden nicht als Core-Laufzeitabhängigkeit eingebaut. Fehlt ein erforderliches Werkzeug, bleibt die entsprechende Pflichtprüfung sichtbar blockiert.

Statische Routingfälle umfassen mindestens:

- triviale Änderung ohne strukturellen Anlass: keine unnötige Clairvoyance-Vertiefung;
- konkrete Boundary-/Wissensleckage: passende Diagnose mit Aufrufer- und Vertragsbezug;
- legitimer Adapter oder echte Domänenkopplung: kein automatisches Smell-Finding;
- entdeckt notwendiges Refactoring außerhalb des Tasks: Folgearbeit statt Mutation;
- Fehlerbehandlung mit Datenverlust-/Security-Risiko: kein stilles Maskieren;
- passender verfügbarer MCP: engste geeignete Operation unter geltender Priorität;
- fehlende oder ungeeignete MCP-Fähigkeit: erlaubter Fallback oder belegte Blockade;
- verfügbare mutierende Remoteoperation ohne Freigabe: nicht ausführen;
- neu verfügbarer geeigneter Provider: capability-basiert einordnen ohne fest verdrahteten Providernamen.

Für eine echte Verhaltensevaluation sind Task-only-Baseline, bisherige Skills und neue Skills unter gleichen Bedingungen zu vergleichen. Unabhängige Evaluatoren erhalten rohe Aufgaben und notwendige Constraints, keine erwarteten Antworten oder Autorenurteile. Dieser Plan erlaubt statische Prüfungen und vorhandene Aufzeichnungen, aber keine kostenpflichtigen Live-Evaluationen. Fehlende Laufzeitmessungen, Kosten-, Latenz- oder Tokendaten bleiben als fehlend ausgewiesen.

## Risiken und Übergabe

Hauptgefahren sind Überladung kleiner Aufgaben, verdeckte externe Abhängigkeiten, duplizierte Regeln, scope-erweiternde Refactoringanweisungen, unzulässige Textübernahme und MCP-Verfügbarkeit als vermeintliche Freigabe. Die Auslöser, Quellenprüfung, direkten paketinternen Verweise, getrennten Taskscopes und negativen Prüffälle adressieren diese Risiken.

Die Taskfolge ist `T01 → T02 → T03`; es gibt keine parallelen Schreibscopes. T03 ersetzt nicht das abschließende `core-review` des Ausführungsworkflows. Status, Findings und Checkresultate werden ausschließlich in den Run-Artefakten geführt; dieser bestätigte Plan bleibt unverändert.

Nächster Workflow: core-execute
Eingabe: .agentic-workflow/plans/002-integrate-design-principles.md
Rahmenbedingungen: bestätigte Entscheidungen, MCP-Zusatz, Nicht-Ziele, Taskscopes und Verifikationsgrenzen dieses Plans.

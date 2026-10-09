---
name: core-brainstorm
description: "Klärt optional ein materiell unklares Vorhaben, vergleicht unterschiedliche Lösungsrichtungen und übergibt ausschließlich bestätigte Designentscheidungen an core-plan oder die ausdrücklich gewählte Etappenplanung mit core-milestone."
---

# Core Brainstorm

Nutze diesen optionalen Workflow, wenn Ziel, Nutzerproblem, Geltungsbereich oder Lösungsrichtung materiell unklar ist oder eine schwer reversible Entscheidung bevorsteht. Die Größe eines Vorhabens allein aktiviert ihn nicht.

`core-brainstorm` plant und implementiert nicht. Ist das Vorhaben bereits ausreichend bestimmt, überspringe Brainstorming: Übergib den unveränderten Auftrag direkt an `core-plan` oder bei ausdrücklich gewählter Etappenplanung an [`core-milestone`](../core-milestone/SKILL.md). Für die Ausführung eines bestätigten `plan/v1` ist ausschließlich `core-execute` zuständig; unabhängige Prüfung gehört zu `core-review`.

## Situative Designmethoden

Nutze [S00 – SWE-Basis und Auswahl](../core-architecture/references/design-baseline.md) für tatsächlich betroffene Struktur- und Vertragsfragen im bestätigten Prüfumfang. Detailmethoden werden nur bei konkretem Signal geladen, nicht als Vollscan. Bei einer materiellen Wissenslücke kann Brainstorm `core-research` inline einsetzen; eine Architekturentscheidung nutzt bei konkreter Boundary-/Vertragswirkung `core-architecture`. Verhaltensbewahrendes Struktur-/Safety-Net-Signal kann `core-refactor` inline begrenzen: Characterization und Refactoring bleiben getrennte, voneinander abhängige Tasks. Diese Fachmethoden erteilen keinen Implementierungsdispatch. Die Referenzen aktivieren keinen Architekturworkflow und erlauben keine ungeplanten Refactorings.

Nutze bei unklaren Strukturproblemen [M01–M04](../core-architecture/references/boundaries-and-abstractions.md) zur Eingrenzung. Bei einer materiellen technischen Richtungsentscheidung mit plausiblen Alternativen nutze [M10](../core-architecture/references/alternatives.md), einschließlich des begrenzten Pre-Mortems bei Bedarf. Keine Implementierung, eigene Agentensteuerung oder zusätzlichen Pflichtartefakte ableiten.

Wenn Tools benötigt werden, prüfe relevante aktuell verfügbare MCP-Fähigkeiten gemäß [Toolrouting](../core-shared/references/tool-routing.md); Verfügbarkeit erweitert weder Scope noch Autorisierung.

## Eingaben und Ergebnis

Erforderlich sind der aktuelle Auftrag, ausdrückliche Rahmenbedingungen und die für die offene Entscheidung relevante Repositoryevidenz. Ein vorhandener Plan-, Run- oder Reviewstatus ist keine Brainstorm-Source-of-Truth.

Das Ergebnis ist ein kompaktes Design in Form einer Entscheidungsübergabe: bestätigte Lösungsrichtung, Grenzen, Leitplanken und Begründungen, kein Detailplan. Empfänger ist standardmäßig `core-plan`, bei ausdrücklich gewählter Etappenplanung `core-milestone`. Sie enthält ausschließlich bestätigte Entscheidungen und belegte Rahmenbedingungen. Ein dauerhaftes separates Dokument entsteht nur, wenn die Information über den einzelnen Plan hinaus Bestand haben muss und der Benutzer diesen zusätzlichen Schreibbereich autorisiert.

## Verbindliche Verträge

- Lade für Autorisierung, Abbruch und Abschluss den [Workflowvertrag](../core-shared/references/workflow-contract.md).
- Lade bei Repositoryanalyse oder externer Evidenz das [Toolrouting](../core-shared/references/tool-routing.md).
- Nutze den [Workflowkatalog](../core-shared/assets/workflow-catalog.yaml) nur zur Prüfung der Übergänge `core-brainstorm → core-plan` beziehungsweise optional `core-brainstorm → core-milestone`.

## Workflow

1. **Aktivierung prüfen.** Benenne die konkrete materielle Unklarheit. Wenn keine besteht, stoppe das Brainstorming und route ohne erneute Grundsatzklärung zum autorisierten Empfänger.
2. **Entscheidungsrahmen bilden.** Präzisiere Nutzerproblem, gewünschtes Ergebnis, Geltungsbereich, Nicht-Ziele und Rahmenbedingungen. Stelle nur Fragen, deren Antwort Ergebnis, Sicherheit, Geltungsbereich oder schwer reversible Folgen verändert.
3. **Aktuellen Systemkontext belegen.** Untersuche Brownfield-Fragen zuerst mit Gortex im aktuellen Checkout oder Worktree. Repositorycode, Tests und lokale Verträge schlagen generische Defaults und Erinnerung.
4. **Evidenzlücken gezielt schließen.** Nutze externe Recherche nur, wenn die Entscheidung ohne sie materiell unsicher bleibt. Context7 dient aktueller offizieller Technologie- und API-Dokumentation. YouTube Transcript wird nur für eine bekannte relevante Video-URL verwendet. Serena ist ausschließlich projektspezifische Informationssuche oder Code-Fallback, kein Webresearch. Jeder Fallback und jede Evidenzlücke bleibt sichtbar.
5. **Alternativen vergleichen.** Vergleiche bei einer relevanten Entscheidung mindestens zwei mechanistisch unterschiedliche Optionen anhand von Nutzen, Risiken, Reversibilität, Projektpassung und erforderlicher Verifikation. Scheinvarianten zählen nicht.
6. **Entscheidung bestätigen.** Halte Annahmen nicht als Fakten fest. Bitte um Bestätigung, wenn die Auswahl nicht bereits ausdrücklich autorisiert oder durch eine belegte Projektinvariante festgelegt ist.
7. **Übergabe erzeugen.** Übergib nur bestätigte Inhalte in der unten definierten Form. Materielle offene Punkte verhindern die Übergabe und führen zu `blocked` statt zu einer erfundenen Entscheidung.

Architekturperspektive ist nur bei materiellen Architekturfolgen erforderlich. Fokussierte externe Recherche bleibt read-only. Honcho darf einen Hinweis auf bestätigte Präferenzen liefern, ersetzt aber weder Benutzerbestätigung noch aktuelle Repositoryevidenz.

## Entscheidungsübergabe

```text
Nächster Workflow: <core-plan oder ausdrücklich gewähltes core-milestone>
Problem: <bestätigtes Nutzerproblem>
Ergebnis: <bestätigtes beobachtbares Ergebnis>
Geltungsbereich: <bestätigte Grenzen>
Nicht-Ziele: <bestätigte Ausschlüsse>
Rahmenbedingungen: <bestätigte oder lokal belegte Vorgaben>
Entscheidungen:
- <Entscheidung und knappe Begründung>
Verworfene Alternativen:
- <Alternative und bestätigter Ablehnungsgrund>
Evidenz:
- <Repositorypfad oder belastbare Quelle und entscheidungsrelevanter Befund>
```

Füge keine offenen Annahmen, Taskzerlegung, Prioritätsstufen, Runstatuswerte oder unbestätigten Researchbefunde ein. Ohne Etappenplanung übernimmt `core-plan` die bestätigten Entscheidungen in genau einen kanonischen `plan/v1`. Bei ausdrücklich gewählter Etappenplanung übergibt Brainstorm die bestätigten gemeinsamen Entscheidungen an `core-milestone`; dieser Eigentümer hält sie einmalig in `.agentic-workflow/goals/<goal-id>/goal.md` (`goal/v1`) fest und verknüpft bestätigte Designquellen als `decision_refs`. Dazu gehören Ziel-ID und exakter Zielpfad; Definitionen und Auswahl/Nachweise bleiben getrennt in [Definitionsformat](../core-milestone/references/milestone-format.md) und [Indexformat](../core-milestone/references/milestone-index-format.md). Jede freigegebene Etappe erhält ihren eigenen Plan. Ein separates Design-Dokument ist nicht erforderlich, sofern keine ausdrücklich referenzierte Quelle langlebig gebraucht wird. Vor einem Sitzungswechsel müssen die Entscheidungen am autorisierten Artefaktpfad schriftlich vorliegen; eine Chatübergabe genügt nicht.

## Abschluss und Fehlerfälle

- **completed:** Die Entscheidungsübergabe enthält nur bestätigte Entscheidungen und benennt `core-plan` oder das ausdrücklich gewählte `core-milestone` als nächsten Workflow.
- **partial:** Nutzbare Optionen oder Evidenz liegen vor, aber die Entscheidung ist noch nicht bestätigt; es erfolgt keine bestätigte Übergabe.
- **blocked:** Eine materielle Eingabe, sichere Evidenzquelle oder erforderliche Autorisierung fehlt.
- **failed:** Die Analyse konnte nicht belastbar durchgeführt werden; nenne Ursache und verbleibende Nebenwirkungen.

Starte keine Implementierung, ändere keinen Produktcode und erzeuge keinen parallelen Plan oder Workflowstatus.

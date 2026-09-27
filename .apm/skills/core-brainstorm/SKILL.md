---
name: core-brainstorm
description: "Klärt optional ein materiell unklares Vorhaben, vergleicht unterschiedliche Lösungsrichtungen und übergibt ausschließlich bestätigte Entscheidungen an core-plan."
---

# Core Brainstorm

Nutze diesen optionalen Workflow, wenn Ziel, Nutzerproblem, Geltungsbereich oder Lösungsrichtung materiell unklar ist oder eine schwer reversible Entscheidung bevorsteht. Die Größe eines Vorhabens allein aktiviert ihn nicht.

`core-brainstorm` plant und implementiert nicht. Ist das Vorhaben bereits ausreichend bestimmt, übergib den unveränderten Auftrag direkt an `core-plan`. Für die Ausführung eines bestätigten `plan/v1` ist ausschließlich `core-execute` zuständig; unabhängige Prüfung gehört zu `core-review`.

## Eingaben und Ergebnis

Erforderlich sind der aktuelle Auftrag, ausdrückliche Rahmenbedingungen und die für die offene Entscheidung relevante Repositoryevidenz. Ein vorhandener Plan-, Run- oder Reviewstatus ist keine Brainstorm-Source-of-Truth.

Das Ergebnis ist eine kompakte Entscheidungsübergabe an `core-plan`. Sie enthält ausschließlich bestätigte Entscheidungen und belegte Rahmenbedingungen. Ein dauerhaftes separates Dokument entsteht nur, wenn die Information über den einzelnen Plan hinaus Bestand haben muss und der Benutzer diesen zusätzlichen Schreibbereich autorisiert.

## Verbindliche Verträge

- Lade für Autorisierung, Abbruch und Abschluss den [Workflowvertrag](../core-shared/references/workflow-contract.md).
- Lade bei Repositoryanalyse oder externer Evidenz das [Toolrouting](../core-shared/references/tool-routing.md).
- Nutze den [Workflowkatalog](../core-shared/assets/workflow-catalog.yaml) nur zur Prüfung des Übergangs `core-brainstorm → core-plan`.

## Workflow

1. **Aktivierung prüfen.** Benenne die konkrete materielle Unklarheit. Wenn keine besteht, stoppe das Brainstorming und route direkt zu `core-plan`.
2. **Entscheidungsrahmen bilden.** Präzisiere Nutzerproblem, gewünschtes Ergebnis, Geltungsbereich, Nicht-Ziele und Rahmenbedingungen. Stelle nur Fragen, deren Antwort Ergebnis, Sicherheit, Geltungsbereich oder schwer reversible Folgen verändert.
3. **Aktuellen Systemkontext belegen.** Untersuche Brownfield-Fragen zuerst mit Gortex im aktuellen Checkout oder Worktree. Repositorycode, Tests und lokale Verträge schlagen generische Defaults und Erinnerung.
4. **Evidenzlücken gezielt schließen.** Nutze externe Recherche nur, wenn die Entscheidung ohne sie materiell unsicher bleibt. Context7 dient aktueller offizieller Technologie- und API-Dokumentation. YouTube Transcript wird nur für eine bekannte relevante Video-URL verwendet. Serena ist ausschließlich projektspezifische Informationssuche oder Code-Fallback, kein Webresearch. Jeder Fallback und jede Evidenzlücke bleibt sichtbar.
5. **Alternativen vergleichen.** Vergleiche bei einer relevanten Entscheidung mindestens zwei mechanistisch unterschiedliche Optionen anhand von Nutzen, Risiken, Reversibilität, Projektpassung und erforderlicher Verifikation. Scheinvarianten zählen nicht.
6. **Entscheidung bestätigen.** Halte Annahmen nicht als Fakten fest. Bitte um Bestätigung, wenn die Auswahl nicht bereits ausdrücklich autorisiert oder durch eine belegte Projektinvariante festgelegt ist.
7. **Übergabe erzeugen.** Übergib nur bestätigte Inhalte in der unten definierten Form. Materielle offene Punkte verhindern die Übergabe und führen zu `blocked` statt zu einer erfundenen Entscheidung.

Architekturperspektive ist nur bei materiellen Architekturfolgen erforderlich. Fokussierte externe Recherche bleibt read-only. Honcho darf einen Hinweis auf bestätigte Präferenzen liefern, ersetzt aber weder Benutzerbestätigung noch aktuelle Repositoryevidenz.

## Entscheidungsübergabe

```text
Nächster Workflow: core-plan
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

Füge keine offenen Annahmen, Taskzerlegung, Prioritätsstufen, Runstatuswerte oder unbestätigten Researchbefunde ein. `core-plan` übernimmt die bestätigten Entscheidungen in genau einen kanonischen `plan/v1`.

## Abschluss und Fehlerfälle

- **completed:** Die Entscheidungsübergabe enthält nur bestätigte Entscheidungen und benennt `core-plan` als nächsten Workflow.
- **partial:** Nutzbare Optionen oder Evidenz liegen vor, aber die Entscheidung ist noch nicht bestätigt; es erfolgt keine bestätigte Übergabe.
- **blocked:** Eine materielle Eingabe, sichere Evidenzquelle oder erforderliche Autorisierung fehlt.
- **failed:** Die Analyse konnte nicht belastbar durchgeführt werden; nenne Ursache und verbleibende Nebenwirkungen.

Starte keine Implementierung, ändere keinen Produktcode und erzeuge keinen parallelen Plan oder Workflowstatus.

---
name: core-user2agent-instructions
description: Übernimmt eindeutig manuelle Benutzeranweisungen kontrolliert von der globalen in die projektspezifische AGENTS.md. Verwenden für Vorschau, selektive Synchronisierung oder ausdrücklich bestätigte vollständige Übernahme; nicht für generierte Blöcke, Providerkonfiguration oder Synchronisierung vom Projekt ins Benutzer-Home.
---

# Core User2Agent Instructions

Synchronisiere Benutzeranweisungen ausschließlich **global → Projekt**. Schütze manuelle Projektinhalte, generierte Bereiche und fremde verwaltete Blöcke. Dieser Skill konfiguriert keine Provider, verändert keinen Workflowzustand und startet keine Subagenten.

## Verbindlicher Vertrag und Pfade

Lade den [Vertrag für Benutzeranweisungen](../core-shared/references/user-instructions-contract.md), bevor Quelle oder Ziel ausgewertet werden. Verwende genau:

```text
globale Quelle: Path.home() / "AGENTS.md"
Projektziel:     Path.cwd() / "AGENTS.md"
```

Löse beide Pfade absolut auf und zeige sie in jeder Vorschau. Lehne Benutzer-Home, Dateisystemroot und ein breites Elternverzeichnis als Projektziel ab. Eine umgekehrte oder bidirektionale Synchronisierung ist nicht zulässig.

## Eigentum und Standardauswahl

Standardmäßig werden nur eindeutig manuelle Benutzeranweisungen als Kandidaten angeboten. Schließe aus:

- generierte oder anderweitig verwaltete Blöcke einschließlich `CORE-INIT-PROJECT`, OMA-, Harness- und Providerbereiche,
- globale Spezialkonfiguration eines Harnesses oder Providers,
- Secrets, Zugangsdaten und vertrauliche Werte,
- flüchtige Health-, Session- oder Workflowstatuswerte,
- Inhalte mit unklarer Herkunft oder Eigentümerschaft.

Verwende für selektiv übernommene Anweisungen genau ein eigenes Markerpaar im Projektziel:

```text
<!-- CORE-USER-INSTRUCTIONS:START -->
<!-- CORE-USER-INSTRUCTIONS:END -->
```

`core-user2agent-instructions` besitzt nur diesen Zielbereich. Es darf den von `core-init-project` verwalteten Block, andere generierte Blöcke oder Inhalte außerhalb seines Zielbereichs weder neu formatieren noch ersetzen.

## Workflow: Selektive Synchronisierung

1. Lies globale Quelle und Projektziel read-only.
2. Erfasse den Zielinhalt außerhalb des eigenen Markerpaares bytegenau.
3. Blockiere bei fehlender eindeutiger Herkunft sowie bei doppelten, verschachtelten, ungepaarten oder beschädigten eigenen Markern; repariere Marker nicht heuristisch.
4. Bestimme die manuellen Kandidaten und zeige für jeden, warum er eingeschlossen oder ausgeschlossen wird.
5. Erzeuge den **vollständigen exakten Diff** für das Projektziel und zeige beide absoluten Pfade.
6. Fordere eine separate ausdrückliche **Bestätigung genau dieses Diffs** an. Schweigen, eine frühere allgemeine Zustimmung, eine Bestätigung nur der Absicht oder eine Auswahl ohne finalen Diff autorisiert keinen Schreibzugriff.
7. Lies Quelle und Ziel unmittelbar vor der Mutation erneut. Bei jeder Abweichung ist die Bestätigung verbraucht: Verwirf die Vorschau, erzeuge einen neuen exakten Diff und fordere eine neue Bestätigung an.
8. Schreibe ausschließlich den bestätigten Zielbereich. Wenn das Markerpaar fehlt, füge genau einen vollständigen Block hinzu; andernfalls ersetze nur den Inhalt dazwischen.
9. Lies das Ergebnis erneut und verifiziere Marker, bestätigten Zielinhalt sowie bytegenau unveränderte Außenbereiche.
10. Prüfe die Idempotenz read-only: Dieselbe Quelle und Auswahl müssen gegen das Ergebnis einen leeren Diff erzeugen.

Eine Bestätigung ist an Inhalt und beide Pfade der Vorschau gebunden. Sie darf nicht auf weitere Kandidaten, spätere Änderungen oder einen anderen Zielpfad übertragen werden.

## Gewarnte vollständige Dateiübernahme

Eine vollständige Kopie der globalen `AGENTS.md` ist keine Standardaktion. Biete sie nur auf ausdrücklichen Wunsch an und erkläre vorher den möglichen Verlust beziehungsweise die Überschreibung projektspezifischer Inhalte.

Vor einer vollständigen Übernahme:

1. prüfe und zeige beide absoluten Pfade,
2. zeige den vollständigen exakten Datei-Diff einschließlich aller entfernten Projektbereiche,
3. benenne betroffene manuelle, generierte und verwaltete Blöcke,
4. fordere eine ausdrückliche Bestätigung beider Pfade und genau dieses vollständigen Diffs an,
5. verwirf die Bestätigung bei jeder zwischenzeitlichen Quellen- oder Zieländerung.

Ohne diese enge Bestätigung bleibt die Aktion blockiert. Auch eine vollständige Übernahme darf Secrets nicht in Bericht oder Protokoll ausgeben. Stelle bei einem Fehler den vorherigen Zustand nur wieder her, wenn dadurch keine zwischenzeitliche fremde Änderung verloren geht.

## Priorität und Ergebnis

Übernommene globale Präferenzen bleiben unter aktuellen ausdrücklichen Benutzeranweisungen, bestätigten projektspezifischen Anweisungen, belegten Projektinvarianten und dem zuständigen Fachskill. Die Synchronisierung schwächt keine höherrangige Regel, Autorisierung oder Projektgrenze ab.

Berichte abschließend:

- Status `completed`, `partial`, `blocked` oder `failed`,
- globale Quelle und Projektziel,
- den übernommenen manuellen Abschnitt ohne vertrauliche Vollinhalte,
- erhaltene Außenbereiche und geschützte generierte Blöcke,
- Bestätigungs- und Verifikationsergebnis,
- verbleibende Mehrdeutigkeiten oder sichere nächste Schritte.

`completed` erfordert den bestätigten Zielinhalt, gültige Marker, unveränderte Außenbereiche und einen leeren Idempotenz-Diff. Fehlende exakte Diff-Bestätigung, beschädigte Marker, Pfaddrift oder unklare Eigentümerschaft ergibt `blocked`, nicht eine heuristische Mutation.

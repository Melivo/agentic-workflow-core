# TypeSafe-Evaluationsordner

## Purpose

Diesen lokalen, gitignorierten Ordner nur für eine ausdrücklich beauftragte Plan-Evaluation und mit Artefaktschreibrecht verwenden. Die portable, versionierte Regel ist die kanonische Vorlage unter `.apm/skills/core-typesafe/assets/evaluation-directory-AGENTS.md`.

## Ownership

Der normale Evaluationsablauf gehört `core-plan`; diese Datei regelt nur den lokalen Ergebnisbereich. Ergebnisse sind getrennte `plan-comparison/v1`-Daten, kein Plan-, Review-, Task- oder Workflowstatus.

## Local Contracts

- Vor dem fixierten unabhängigen Erstreview darf der externe Reviewer diesen Ordner, TypeSafe-Ergebnisse und Modellhinweise nicht lesen; der Owner darf sie diesem Reviewer nicht offenlegen. Der Reviewer erhält Originalplan, Kriterien und nötige Quellen mit einer expliziten Leseregel gegen diesen Ordner und fremde Sessions.
- Nach der unveränderten Erstantwort sichert der Owner deren Originalbytes und Hash referenzierbar. Erst danach erhält derselbe Reviewer in derselben Session Modellresultate und Originale zur getrennten Adjudikation; das Ersturteil bleibt unverändert. Vorabzugriff oder begründeter Kontaminationsverdacht lässt den Vergleich offen beziehungsweise ausgeschlossen.
- Bewahre Originale und alle Ereignisrevisionen unverändert auf. Schreibe nur an freie Pfade und prüfe Dateikonflikte mit vorhandenen bewachten Werkzeugen. IDs und Referenzen minimieren; keine Rohtexte, Secrets oder vollständigen Chats exportieren.
- Diese organisatorische Leseregel erzwingt keine technische Zugriffssperre und beweist keine Isolation oder Modellgüte. Fehlende Originale oder sichere Sessionfortsetzung bleiben offen.

## Work Guidance

Die Vorlage bei Änderungen an der kanonischen Version neu kopieren; fremde vorhandene lokale Dateien nicht überschreiben. In anderen Projekten die lokale Kopie nur bei ausdrücklich beauftragter Evaluation und entsprechendem Artefaktschreibrecht anlegen.

## Verification

Manuell prüfen, dass lokale Kopie und versionierte Vorlage bytegleich sind. Dauerhafte Tests verwenden synthetische temporäre Projektfixtures, nie diese echte gitignorierte Datei.

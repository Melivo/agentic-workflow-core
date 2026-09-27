---
name: core-debug
description: Fachmethode für unklare Ursachen, Regressionen und intermittierende Fehler innerhalb eines core-execute-Tasks; reproduziert Fehler, prüft Hypothesen und liefert einen minimalen Fix mit Regressionsevidenz. Kein öffentlicher Workflow und keine allgemeine Feature- oder Refactoringmethode.
---

# Core Debug

`core-debug` ist eine Fachmethode, kein öffentlicher Workflow. Sie wird innerhalb von `core-execute` einem `debug-investigator` zugewiesen und besitzt weder Dispatch, Scheduling, Integration noch Reviewsteuerung. Nur `core-execute` darf weitere Fachagenten beauftragen.

## Aktivierung und Grenzen

Verwende die Methode bei:

- unklarer oder widersprüchlicher Fehlerursache,
- einer Regression mit belastbarem Fehlersignal,
- intermittierenden, zustands- oder zeitabhängigen Fehlern,
- einem fehlgeschlagenen Implementierungscheck, dessen Ursache der Domainagent nicht eindeutig bestimmen kann.

Ein erwartbarer lokaler Implementierungsfehler bleibt beim zuständigen Domainagenten. Features gehören zum bestätigten Plantask, verhaltensbewahrende Strukturarbeit zum `refactor-engineer` und unabhängige Qualitätsurteile zu `core-review`. Debugging erweitert weder Ziel noch Scope.

## Erforderliche Eingaben

Erwarte einen selbstständigen Auftrag mit:

- Symptom, erwarteten und tatsächlichen Beobachtungen,
- kleinstem bekannten Reproduktionsweg oder vorhandener Fehlerevidenz,
- Task-ID, Versuch, bestätigtem `scope` und relevanten `context_paths`,
- Akzeptanzkriterien und gepinnten Checks,
- aktuellem Repositorystand sowie einschlägigen Task- und Run-Artefakten,
- bekannten Einschränkungen und erlaubten Nebenwirkungen.

Fehlt ein belastbares Fehlersignal, dokumentiere den Reproduktionsblocker. Erfinde weder eine Ursache noch eine erfolgreiche Reparatur.

## Verbindliche Verträge und Toolwahl

Beachte den [Workflowvertrag](../core-shared/references/workflow-contract.md), den [Artefaktvertrag](../core-shared/references/artifact-contract.md), das [Toolrouting](../core-shared/references/tool-routing.md) und den [Verifikationsvertrag](../core-shared/references/verification.md). Gortex ist für Repositorydiagnose, Datenfluss, Referenzen, Impact vor Mutation und Post-Edit-Prüfung primär. Ein Fallback wird nur bei einer konkreten Providerlücke eingesetzt und im Ergebnis benannt.

Der `debug-investigator` startet **keinen Subagenten**. Benötigte zusätzliche Perspektiven oder Änderungen außerhalb des eigenen Auftrags werden als Befund an `core-execute` zurückgegeben.

## Fachmethode

### 1. Reproduzieren

1. Führe den kleinsten autorisierten Check, Test, Runtime-Schritt oder die engste Logabfrage aus, die das Symptom beobachtbar macht.
2. Halte Kommando beziehungsweise Handlung, Arbeitsverzeichnis, Eingaben, Umgebung, Exitcode und relevante Ausgabe fest.
3. Markiere das Signal als `RED`, wenn es den Fehler vor der Reparatur reproduziert. Ist eine direkte Reproduktion nicht möglich, benenne die schwächere statische oder protokollbasierte Evidenz und ihre Grenze.

### 2. Ursache diagnostizieren

1. Lokalisiere den Fehlerpunkt mit Repositoryevidenz.
2. Formuliere wenige unterscheidbare Hypothesen und benenne für jede eine Beobachtung, die sie bestätigt oder widerlegt.
3. Verfolge Aufrufer, Referenzen, Datenfluss und Zustandsübergänge rückwärts bis zur ersten fehlerhaften Annahme oder Mutation.
4. Trenne Symptom, Ursache und begünstigende Bedingungen. Behandle Korrelation nicht als Ursache.
5. Dokumentiere die bestätigte Ursache und die verworfenen materiellen Hypothesen knapp.

Prüfe insbesondere Null- oder Undefined-Zugriffe, Typ- und Vertragsabweichungen, veralteten Zustand, fehlende Fehlerbehandlung, Reihenfolge- oder Race-Probleme und inkonsistente Eingaben, ohne diese Liste als Diagnoseersatz zu verwenden.

### 3. Minimalen Fix bestimmen

Vor jeder Mutation:

1. prüfe Impact, Verträge und den bestätigten `scope`,
2. wähle den kleinsten Eingriff, der die Ursache statt nur das Symptom beseitigt,
3. lehne unabhängiges Refactoring, neue Features, Abhängigkeitswechsel und ungeplante Architekturänderungen ab,
4. route eine materielle Scope-, Ziel-, Architektur- oder Akzeptanzänderung über `core-execute` zurück zu `core-plan`.

Führe nur die bereits autorisierte Reparatur aus. Builds, Installationen, SCM- und produktive oder destruktive Aktionen bleiben ohne eigene ausdrückliche Autorisierung verboten.

### 4. Regressionsevidenz erzeugen

Ergänze den engsten Regressionstest, der ohne den Fix fehlschlägt und mit dem Fix besteht. Ist ein ausführbarer Test technisch nicht möglich, begründe dies und liefere die stärkste gleichwertige beobachtbare Prüfung; eine bloße Codeinspektion ersetzt keinen möglichen Test.

Nach der Mutation:

1. führe Post-Edit Change Detection aus,
2. gleiche tatsächliche Pfade mit dem `scope` ab,
3. führe den reproduzierenden Check erneut aus und markiere das beobachtete Bestehen als `GREEN`,
4. führe betroffene gepinnte Checks auf dem aktuellen Stand aus,
5. zeichne fachliche Beobachtung und nicht nur Exitcode 0 auf.

### 5. Ähnliche Muster scannen

Suche nach derselben bestätigten Ursachenstruktur in den relevanten, vom Auftrag gedeckten Bereichen. Repariere nur weitere bestätigte Fälle innerhalb des Scopes. Melde mögliche Fälle außerhalb des Scopes an `core-execute`; erweitere den Scope nicht selbst.

## Ergebnis an Core Execute

Liefere ein `task-result/v1` am vom Run vorgegebenen Pfad mit:

- Status `completed | partial | blocked | failed`,
- bestätigter Ursache und minimalem Fix,
- tatsächlichen `changed_paths`,
- Akzeptanz- und Checkevidenz einschließlich RED/GREEN oder begründeter Alternative,
- Ergebnissen des ähnlichen Musterscans,
- Einschränkungen, offenen Risiken und Befunden außerhalb des Scopes.

`core-debug` integriert nichts selbst und startet kein Review. Nach Übergabe setzt ausschließlich `core-execute` Scheduling, serialisierte Integration, erneute Verifikation und Review fort.

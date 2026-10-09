---
name: core-init-project
description: Initialisiert oder aktualisiert den kleinen Repository-Preflight, prüft Code-Intelligence-Readiness und pflegt einen idempotenten Projektblock in AGENTS.md. Verwenden für die einmalige oder erneute projektspezifische Einrichtung; nicht für MCP-Installation, globale Benutzeranweisungen oder allgemeine Repositoryaudits.
---

# Core Init Project

Richte den Repository-Harness für genau ein konkretes Projekt ein. Bewahre manuelle Inhalte, bestehende generierte Bereiche und fremde verwaltete Blöcke. `core-init-project` besitzt ausschließlich seinen eigenen Projektblock in `AGENTS.md`; es installiert keine Provider, startet keine Subagenten und erzeugt keinen Workflowzustand.

## Eingaben und Verträge

Benötigt werden die konkrete Repositorywurzel, der aktuelle Repository- und Worktree-Zustand sowie das primäre Eingabeartefakt des aufrufenden Workflows. Bei ausdrücklich gewählter Etappenplanung kann dies der exakt benannte Zielindex (`.agentic-workflow/goals/<goal-id>/index.yaml`) sein; lies ihn nur als Kontext. Das begründet weder eine Zielanlage noch Definitions- oder Versionsauswahl oder eine Etappenfreigabe. Löse die Projektwurzel absolut auf und lehne Benutzer-Home, Dateisystemroot und breite Elternverzeichnisse ab.

Lade vor einer Mutation:

- den [Vertrag für Benutzeranweisungen](../core-shared/references/user-instructions-contract.md) für Pfade, Marker, Vorschau, Bestätigung und Erhaltung außerhalb des Zielbereichs;
- das [Toolrouting](../core-shared/references/tool-routing.md) für Providerreihenfolge, Projektgrenzen und sichtbare Fallbacks;
- den externen, über APM bereitgestellten Skill `gortex-serena-configurator` für die Code-Intelligence-Readiness.

`gortex-serena-configurator` bleibt eine unveränderte externe Abhängigkeit. Verwende ihn **inline** als Methode im aktuellen Lauf: nicht kopieren, nicht umbenennen, nicht als Subagent dispatchen und keinen separaten Status anlegen.

## Workflow

### 1. Repository-Preflight

1. Prüfe Repositorywurzel, Worktree und aktuellen Git-Zustand read-only.
2. Lade das ausdrücklich benannte primäre Eingabeartefakt des aktuellen Workflows.
3. Lies nur dafür relevante Dateien, Skills, Regeln und lokale Verträge.
4. Ermittle aus Repositoryevidenz Stack, Task Runner, Architektur- und Modulgrenzen, projektspezifische Sicherheits- und Freigabegrenzen sowie verbindliche Checks.
5. Verwende Gortex bedarfsgerecht; Toolverfügbarkeit erweitert weder Lese- noch Schreibscope.

Dateiglobs sind nur Signale. Kombiniere sie mit Taskabsicht, Stack und Pfadkontext. Persistiere keine Vermutung und keine flüchtigen Health-, Session- oder Workflowstatuswerte.

### 2. Provider-Readiness inline prüfen

Führe den Preflight von `gortex-serena-configurator` mit der konkreten Repositorywurzel read-only aus; halte `--apply-agents` und jede entsprechende `AGENTS.md`-Schreiboption deaktiviert. Provideraktionen benötigen eine konkret gezeigte Auswahl und passende ausdrückliche Autorisierung. Serena darf ausschließlich für dieses konkrete Projekt initialisiert werden; aktiviere oder konfiguriere niemals globales Serena. Der Configurator liefert den Readiness-Befund; der Schreibbesitz für den unten definierten Projektblock bleibt bei `core-init-project`.

1. Prüfe Gortex-Gesundheit und vorhandenes Tracking read-only.
2. Prüfe Serena-Verfügbarkeit, projektspezifische Initialisierung, effektive Sprachen und autoritative MCP-Quelle read-only.
3. Stelle nur tatsächlich notwendige Aktionen gemeinsam zur Auswahl.
4. Führe ausschließlich ausdrücklich ausgewählte Aktionen aus.
5. Auditiere danach Gortex, Serena und native Fallbacks erneut und berichte ihre Bereitschaft getrennt.

`Repository in Gortex tracken` ist immer **optional** und benötigt eine ausdrückliche Auswahl; fehlendes Tracking autorisiert keine automatische Registrierung. Entferne oder ändere vorhandenes Tracking niemals implizit.

Serena bleibt auf dieses konkrete Projekt begrenzt. Aktiviere weder Benutzer-Home noch Dateisystemroot oder ein breites Elternverzeichnis und schließe Abhängigkeiten, Caches, generierte Bäume, Binärdateien und Vendor-Verzeichnisse vom breiten Suchraum aus. Projektbezogene Serena-Einrichtung und Sprachabgleich benötigen jeweils die dafür gezeigte Auswahl. Gortex bleibt der primäre Code-Intelligence-Provider.

### 3. Kleinen verwalteten Projektblock entwerfen

Der Zielpfad ist die projektspezifische `Path.cwd() / "AGENTS.md"`. Verwende genau ein stabiles Markerpaar:

```text
<!-- CORE-INIT-PROJECT:START -->
<!-- CORE-INIT-PROJECT:END -->
```

Der Block enthält belegte Projektfakten und kompaktes Core-Routing:

- Stack und Task Runner,
- tatsächliche Architektur- und Modulgrenzen,
- projektspezifische Sicherheits- und Freigabegrenzen,
- verbindliche Checks,
- einen kompakten Fachagenten- und Skill-Routingindex,
- die stabile Providerreihenfolge `Gortex → projektspezifisches Serena → native Werkzeuge`.

Lade ausschließlich beim Entwurf dieses Blocks die [Core-Routingvorlage](assets/core-routing.md). Übernimm ihren kompakten Abschnitt neben den Projektfakten in das eigene Markerpaar; der Skill-Routingindex wird dadurch konkretisiert, nicht zusätzlich dupliziert. Prüfe die genannten Skills im Zielharness: Fehlende Skills werden als Einschränkung benannt, nicht installiert oder als verfügbar behauptet. Erhalte beim Kürzen oder Anpassen die fünf Entscheidungsgrenzen der Vorlage; ergänze keine sitzungsabhängigen IDs, Statuswerte, pauschalen Etappenpflichten oder Startfreigaben. Die Vorlage ist Ausgabeinhalt, kein Auftrag, jetzt einen Core-Workflow zu starten.

Prüfe den Entwurf vor der Diff-Vorschau auf passenden Einstieg, Fortführung bereits autorisierter Arbeit einschließlich Review, bedingten Etappenabschluss, bedarfsabhängige Fachmethoden und sicheren Wiedereinstieg. Bei Widerspruch zu manuellen Anweisungen oder fehlender Voraussetzung kläre die konkrete Lücke statt fremde Bereiche anzupassen oder Freigaben zu erfinden. Ausführliche Fachmethodik bleibt in den zuständigen Skills. Globale Benutzeranweisungen gehören `core-user2agent-instructions`; fremde generierte oder verwaltete Blöcke bleiben unverändert.

### 4. Exakten Diff bestätigen und idempotent schreiben

1. Lies das Projektziel und erfasse den Inhalt außerhalb des eigenen Markerpaares bytegenau.
2. Blockiere bei doppelten, verschachtelten, ungepaarten oder beschädigten eigenen Markern; repariere sie nicht heuristisch.
3. Erzeuge den vollständigen geplanten Diff und zeige den absoluten Zielpfad.
4. Warte auf eine separate ausdrückliche Bestätigung genau dieses Diffs. Schweigen, eine frühere allgemeine Zustimmung oder eine veränderte Vorschau genügen nicht.
5. Verwirf die Vorschau, wenn sich Ziel oder Evidenz vor dem Schreiben ändern.
6. Ersetze bei bestätigter Aktualisierung ausschließlich den Inhalt zwischen einem gültigen Markerpaar; fehlen beide Marker vollständig, füge genau einen vollständigen Block hinzu.
7. Lies die Datei erneut und verifiziere Marker, Zielbereich und bytegenau unveränderte Außenbereiche.
8. Führe denselben Entwurf gedanklich beziehungsweise read-only erneut gegen das Ergebnis aus: Es darf kein weiterer Diff entstehen. Nur dann ist die Aktualisierung idempotent.

Überschreibe niemals die gesamte `AGENTS.md`. Bei einem Schreib- oder Verifikationsfehler stoppe, berichte die beobachtete Teilwirkung und stelle den vor der Mutation erfassten Zustand nur dann wieder her, wenn dies ohne Verlust zwischenzeitlicher fremder Änderungen sicher möglich ist.

## Ergebnisse und Zustände

- **completed:** Preflight ist belegt, ausgewählte Provideraktionen sind geprüft, der bestätigte Projektblock ist verifiziert und ein zweiter Lauf wäre diff-frei.
- **partial:** Der Harness oder Block ist gültig, aber eine optionale Providerfähigkeit fehlt; nenne die sichtbare Degradierung.
- **blocked:** Projektgrenze, Eingabeartefakt, exakte Diff-Bestätigung, sichere Markerlage oder erforderliche Providerfähigkeit fehlt.
- **failed:** Eine ausgewählte Aktion oder verifizierte Mutation schlug fehl; nenne Pfad, Teilwirkung und sicheren nächsten Schritt.

Ist Gortex nicht bereit, Serena aber projektspezifisch verfügbar, darf der Init mit sichtbarer Degradierung abschließen. Sind beide nicht bereit, darf der Repository-Harness entstehen; spätere Gortex-pflichtige Tasks bleiben jedoch blockiert.

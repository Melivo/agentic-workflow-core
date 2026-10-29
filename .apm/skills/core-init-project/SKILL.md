---
name: core-init-project
description: Initialisiert oder aktualisiert den Repository-Preflight oder gleicht ausdrücklich ausgewählte verwaltete Projektanweisungen in AGENTS.md gegen ihre Vorlagen ab. Verwenden für projektspezifische Einrichtung und selektiven Core-/Serena-Gortex-Abgleich; nicht für MCP-Installation, globale Benutzeranweisungen oder allgemeine Repositoryaudits.
---

# Core Init Project

Bei ausdrücklich angefordertem Anweisungsabgleich führe ausschließlich Abschnitt 6 aus; überspringe normales Init, Provideraudit, Laufzeiteinrichtung und `.gitignore`-Pflege. Andernfalls richte den Repository-Harness für genau ein konkretes Projekt ein. Bewahre manuelle Inhalte, bestehende generierte Bereiche und fremde verwaltete Blöcke. `core-init-project` pflegt seinen eigenen Projektblock in `AGENTS.md` und den unten begrenzten lokalen Artefaktschutz in `.gitignore`; es installiert keine Provider, startet keine Subagenten und erzeugt keinen Workflowzustand.

## Eingaben und Verträge

Benötigt werden die konkrete Repositorywurzel, der aktuelle Repository- und Worktree-Zustand sowie das primäre Eingabeartefakt des aufrufenden Workflows. Bei ausdrücklich gewählter Etappenplanung kann dies der exakt benannte Zielindex (`.agentic-workflow/goals/<goal-id>/index.yaml`) sein; lies ihn nur als Kontext. Das begründet weder eine Zielanlage noch Definitions- oder Versionsauswahl oder eine Etappenfreigabe. Löse die Projektwurzel absolut auf und lehne Benutzer-Home, Dateisystemroot und breite Elternverzeichnisse ab.

Lade vor einer Mutation:

- den [Vertrag für Benutzeranweisungen](../core-shared/references/user-instructions-contract.md) für Pfade, Marker, Vorschau, Bestätigung und Erhaltung außerhalb des Zielbereichs;
- das [Toolrouting](../core-shared/references/tool-routing.md) für Providerreihenfolge, Projektgrenzen und sichtbare Fallbacks;
- den mitgelieferten Skill [`gortex-serena-configurator`](../gortex-serena-configurator/SKILL.md) für die Code-Intelligence-Readiness.

`gortex-serena-configurator` ist eine quelltreu migrierte Konfigurationsmethode der kanonischen Paketquelle. Verwende ihn **inline** als Methode im aktuellen Lauf: nicht kopieren, nicht umbenennen, nicht als Subagent dispatchen und keinen separaten Status anlegen.

## Workflow

### 1. Repository-Preflight

1. Prüfe Repositorywurzel, Worktree und aktuellen Git-Zustand read-only.
2. Lade das ausdrücklich benannte primäre Eingabeartefakt des aktuellen Workflows.
3. Lies nur dafür relevante Dateien, Skills, Regeln und lokale Verträge.
4. Ermittle aus Repositoryevidenz Stack, Task Runner, Architektur- und Modulgrenzen, projektspezifische Sicherheits- und Freigabegrenzen sowie verbindliche Checks.
5. Verwende Gortex bedarfsgerecht; Toolverfügbarkeit erweitert weder Lese- noch Schreibscope.

Dateiglobs sind nur Signale. Kombiniere sie mit Taskabsicht, Stack und Pfadkontext. Persistiere keine Vermutung und keine flüchtigen Health-, Session- oder Workflowstatuswerte.

### 2. Provider-Readiness inline prüfen

Prüfe vor dem ersten Skriptaufruf die Konfigurator-Laufzeit; führe erst danach den Preflight von `gortex-serena-configurator` mit der konkreten Repositorywurzel read-only aus. Halte `--apply-agents` und jede entsprechende `AGENTS.md`-Schreiboption deaktiviert. Provideraktionen benötigen eine konkret gezeigte Auswahl und passende ausdrückliche Autorisierung. Serena darf ausschließlich für dieses konkrete Projekt initialisiert werden; aktiviere oder konfiguriere niemals globales Serena. Der Configurator liefert den Readiness-Befund; der Schreibbesitz für den unten definierten Projektblock bleibt bei `core-init-project`.

#### Konfigurator-Laufzeit vorbereiten

1. Lies die [Laufzeitanforderungen](../gortex-serena-configurator/REQUIREMENTS.md) und die [Dependencydeklaration](../gortex-serena-configurator/scripts/requirements.txt). Sie bleiben die einzige Quelle für Python-Mindestversion und Paketversionsbereiche. PyYAML ersetzt `ruamel.yaml` nicht.
2. Wähle einen vorhandenen geeigneten Python-Interpreter und ermittle dessen absoluten Pfad. Prüfe mit genau diesem Interpreter read-only Python-Version, Paketversion und tatsächlichen Import:

   ```text
   "<python>" -B -c "import sys; from importlib.metadata import version; from ruamel.yaml import YAML, YAMLError; print(sys.executable); print(sys.version); print(version('ruamel.yaml'))"
   ```

   Vergleiche die beobachteten Versionen mit den Anforderungen; ein erfolgreicher Import allein genügt nicht. Verwechsle die Umgebung des Serena-CLI/MCP-Prozesses nicht mit der Laufzeit des Audit-Skripts.
3. Fehlt Python, das Paket oder eine passende Version, biete die notwendige Laufzeiteinrichtung als eigene Auswahl an. Zeige vor der Freigabe Interpreter, absoluten Umgebungspfad, Requirementsdatei, konkrete Befehle, Netzwerk-/Dateiwirkungen und Entfernungspfad. Bevorzuge eine vorhandene geeignete isolierte Werkzeugumgebung; andernfalls schlage eine separate virtuelle Umgebung vor. Erzeuge sie erst nach ausdrücklicher Freigabe. Installiere Pakete ausschließlich über den bestätigten Interpreter mit `"<python>" -m pip install -r "<absoluter-konfiguratorpfad>/scripts/requirements.txt"`. Keine globale oder Systeminstallation, kein `sudo`, kein `--break-system-packages` und keine Änderung der Anwendungsabhängigkeiten. Die Auswahl einer Serena-Provideraktion allein ist keine Installationsfreigabe.
4. Wiederhole nach einer freigegebenen Einrichtung dieselbe Versions- und Importprüfung. Verwende den verifizierten absoluten Interpreterpfad für alle Audit- und ausgewählten Apply-Aufrufe; kein Rückfall auf ein unqualifiziertes `python`. Bei erneutem Init prüfe erneut und überspringe die Einrichtung, wenn alles passt. Fehlt die Freigabe oder scheitert die Einrichtung, führe das Audit-Skript nicht aus und melde die konkrete Laufzeitlücke; ein nicht gestartetes Audit ist kein erfolgreicher Readiness-Nachweis.

#### Provideraudit durchführen

1. Prüfe Gortex-Gesundheit und vorhandenes Tracking read-only.
2. Prüfe Serena-Verfügbarkeit, projektspezifische Initialisierung, effektive Sprachen und autoritative MCP-Quelle read-only.
3. Stelle nur tatsächlich notwendige Aktionen gemeinsam zur Auswahl.
4. Führe ausschließlich ausdrücklich ausgewählte Aktionen aus.
5. Auditiere danach Gortex, Serena und native Fallbacks erneut und berichte ihre Bereitschaft getrennt.

`Repository in Gortex tracken` ist immer **optional** und benötigt eine ausdrückliche Auswahl; fehlendes Tracking autorisiert keine automatische Registrierung. Entferne oder ändere vorhandenes Tracking niemals implizit.

Serena bleibt auf dieses konkrete Projekt begrenzt. Aktiviere weder Benutzer-Home noch Dateisystemroot oder ein breites Elternverzeichnis und schließe Abhängigkeiten, Caches, generierte Bäume, Binärdateien und Vendor-Verzeichnisse vom breiten Suchraum aus. Projektbezogene Serena-Einrichtung und Sprachabgleich benötigen jeweils die dafür gezeigte Auswahl. Gortex bleibt der primäre Code-Intelligence-Provider. Der Readiness-Preflight löst keinen Vollscan und keine Installation aus. Die [S00-Basis](../core-architecture/references/design-baseline.md) gilt für geänderte Einrichtungsbestandteile wie den Projektblock oder eine ausdrücklich ausgewählte Provideraktion; dabei sind Abhängigkeiten, Konfiguration und Entfernungspfad zu benennen.

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

Prüfe den Entwurf vor der Diff-Vorschau auf passenden Einstieg, Fortführung bereits autorisierter Arbeit einschließlich Review, bedingten Etappenabschluss mit verpflichtendem `core-handoff` und anschließendem Halt vor der Folgeetappe, bedarfsabhängige Fachmethoden und sicheren Wiedereinstieg. Die Handoff-Pflicht nach verifiziertem Milestone-Abschluss darf beim Anpassen der Vorlage nicht zu einem bloßen Angebot abgeschwächt werden; am Gesamtzielende bleibt der belegte Abschluss ohne erfundene Folgearbeit erhalten. Bei Widerspruch zu manuellen Anweisungen oder fehlender Voraussetzung kläre die konkrete Lücke statt fremde Bereiche anzupassen oder Freigaben zu erfinden. Ausführliche Fachmethodik bleibt in den zuständigen Skills. Globale Benutzeranweisungen gehören `core-user2agent-instructions`; fremde generierte oder verwaltete Blöcke bleiben unverändert.

### 4. Lokale Artefakte vor Veröffentlichung schützen

Prüfe bei Erstinitialisierung und erneutem Init die `.gitignore` an der konkreten Repositorywurzel. Stelle für lokale Pläne, persönliche Überlegungen, Run-Artefakte, Logs und Serena-Zustand diese Verzeichnisausschlüsse sicher:

```gitignore
/.agentic-workflow/
/.serena/
```

Ergänze nur fehlenden wirksamen Schutz; gleichwertige bestehende Regeln benötigen keinen zusätzlichen Eintrag. Erhalte bestehende Inhalte und Zeilenenden; lege eine fehlende `.gitignore` erst nach bestätigter Vorschau an. Füge keine pauschale Dotfile-Regel hinzu und nimm weder `.agents/` noch `.apm/` in den Ausschluss auf. Ändere vorhandene Regeln für diese oder andere Pfade nicht. Bei widersprüchlichen Negationsregeln kläre den Konflikt, statt sie still zu überschreiben. Erzeuge die ausgeschlossenen Verzeichnisse nicht allein für diese Prüfung.

Prüfe read-only mit `git ls-files -- .agentic-workflow .serena`, ob dort bereits Dateien getrackt werden. Melde nur betroffene Pfade, nicht persönliche Inhalte: `.gitignore` entfernt weder getrackte Dateien noch frühere Commits. Entferne nichts aus Index, Arbeitsbaum oder Historie und führe keinen Commit oder Push aus. Bereinigung braucht einen gesonderten Auftrag; Dateien außerhalb dieser beiden Verzeichnisse sind durch diese Regel nicht geschützt.

Zeige den `.gitignore`-Diff mit absolutem Zielpfad zusammen mit der Projektblock-Vorschau und hole vor dem Schreiben die ausdrückliche Bestätigung ein. Verwirf ihn bei zwischenzeitlichen Änderungen. Verifiziere danach mit `git check-ignore --no-index --stdin` anhand hypothetischer Dateipfade in beiden Verzeichnissen den wirksamen Ausschluss, ohne Dateien anzulegen. Prüfe bestehende Negationsregeln auch für konkrete Unterpfade. Ein zweiter Entwurf darf keinen weiteren Diff erzeugen. Melde fehlenden Schutz oder getrackte Artefakte als offene Datenschutzlücke, nicht als erfolgreich geschützten Zustand.

### 5. Exakten Diff bestätigen und idempotent schreiben

1. Lies das Projektziel und erfasse den Inhalt außerhalb des eigenen Markerpaares bytegenau.
2. Blockiere bei doppelten, verschachtelten, ungepaarten oder beschädigten eigenen Markern; repariere sie nicht heuristisch.
3. Erzeuge den vollständigen geplanten Diff und zeige den absoluten Zielpfad.
4. Warte auf eine separate ausdrückliche Bestätigung genau dieses Diffs. Schweigen, eine frühere allgemeine Zustimmung oder eine veränderte Vorschau genügen nicht.
5. Verwirf die Vorschau, wenn sich Ziel oder Evidenz vor dem Schreiben ändern.
6. Ersetze bei bestätigter Aktualisierung ausschließlich den Inhalt zwischen einem gültigen Markerpaar; fehlen beide Marker vollständig, füge genau einen vollständigen Block hinzu.
7. Lies die Datei erneut und verifiziere Marker, Zielbereich und bytegenau unveränderte Außenbereiche.
8. Führe denselben Entwurf gedanklich beziehungsweise read-only erneut gegen das Ergebnis aus: Es darf kein weiterer Diff entstehen. Nur dann ist die Aktualisierung idempotent.

Überschreibe niemals die gesamte `AGENTS.md`. Bei einem Schreib- oder Verifikationsfehler stoppe, berichte die beobachtete Teilwirkung und stelle den vor der Mutation erfassten Zustand nur dann wieder her, wenn dies ohne Verlust zwischenzeitlicher fremder Änderungen sicher möglich ist.

### 6. Selektiver Abgleich bestehender Blöcke

Für den erneuten Abgleich einer bestehenden `AGENTS.md` gegen die zuständigen Vorlagen nutze den deterministischen [Helper](scripts/reconcile_blocks.py) dieses Bundles statt eines nebenwirkenden Konfigurator-Apply. Er erzeugt getrennte Diffs für die verwalteten Markerpaare `CORE-INIT-PROJECT` und `SERENA-GORTEX-PROJECT`, schreibt ausschließlich die bestätigte Auswahl und verändert keine Provider, Tracking-Zustände, MCP-Konfiguration, `.gitignore` oder andere Dateien. Eine neue Abhängigkeit entsteht nicht; der Helper benötigt nur die Python-Standardbibliothek.

Vorlagen bleiben bei ihrem Eigentümer und werden nicht dupliziert:

- `CORE-INIT-PROJECT`: der nach Abschnitt 3 entworfene Block einschließlich der [Core-Routingvorlage](assets/core-routing.md). Erhalte sämtliche belegten Projektfakten aus dem bestehenden Block unverändert und ersetze nur eindeutig zuordenbares Routing. Ist die Fakt-/Anweisungsgrenze unklar, blockiere den konkreten Vorschlag; keine heuristische Löschung oder semantische Klassifikation. Der Aufrufer schreibt diesen vollständig geprüften Block als temporäre Vorlagendatei. Der Helper prüft Marker und Schreibgrenzen, nicht die fachliche Wahrheit der gelieferten Vorlage.
- `SERENA-GORTEX-PROJECT`: Eigentum des Mitgelieferten Konfigurators. Extrahiere die Vorlage read-only aus der Konstante `PROJECT_PLAYBOOK` in `../gortex-serena-configurator/scripts/serena_safety.py` über `extract-template` und schreibe sie in eine temporäre Vorlagendatei; übernimm sie nicht in dieses Bundle. Enthält der bestehende Projektblock zusätzliche belegte Projektfakten, erhalte diese im geprüften Entwurf; bei unklarer Abgrenzung blockiere den Vorschlag ebenso wie beim Core-Block.

Ablauf:

1. Erzeuge mit `preview` den vollständigen read-only Bericht: je gültigem Block Status `current`, `drift` oder `missing` plus getrennter Unified Diff und ein Bestätigungstoken. Defekte Marker beenden bereits die Vorschau mit einem Fehler statt eines anwendbaren Tokens.
2. Biete genau die vier Auswahlen an: nur Core, nur Serena/Gortex, beide oder keiner. Fehlende Blöcke werden mit Anlage-Diff vorgeschlagen; unmarkierte Außeninhalte werden nicht migriert.
3. Zeige den absoluten Zielpfad, beide absoluten Vorlagenpfade, alle Diffs der Auswahl und das Token; verlange eine separate ausdrückliche Bestätigung genau dieser Fassung.
4. Schreibe mit `apply`, `--select` und dem Bestätigungstoken. Ein falsches Token, ein verändertes Ziel oder eine veränderte Auswahl bricht den Schreibversuch ab; beschädigte, doppelte, verschachtelte oder ungepaarte Marker blockieren jede Anwendung.
5. Verifiziere nach dem Schreiben Markerlage und bytegleiche Außenbereiche; führe `preview` erneut aus: der zweite Lauf muss diff-frei (`current`) sein.

Der Helper bearbeitet ausschließlich Dateien namens `AGENTS.md`, lehnt Symlinks sowie Benutzer-Home und Dateisystemroot als Ziel ab und erhält Zeilenenden. Das normale Init-Verhalten der Abschnitte 1 bis 5 bleibt unverändert; der Abgleich ist eine zusätzliche, getrennt bestätigte Aktion.

Beispiel (Helperpfad und alle Eingaben absolut setzen; `core-block.md` ist der geprüfte Entwurf einschließlich erhaltener Projektfakten):

```sh
python -B "$helper" extract-template --source "$configurator/scripts/serena_safety.py" --name PROJECT_PLAYBOOK > "$tmp/serena-block.md"
python -B "$helper" preview --target "$project/AGENTS.md" --block "CORE-INIT-PROJECT=$tmp/core-block.md" --block "SERENA-GORTEX-PROJECT=$tmp/serena-block.md" --select "CORE-INIT-PROJECT,SERENA-GORTEX-PROJECT"
# Erst nach separater Bestätigung der gezeigten Fassung:
python -B "$helper" apply --target "$project/AGENTS.md" --block "CORE-INIT-PROJECT=$tmp/core-block.md" --block "SERENA-GORTEX-PROJECT=$tmp/serena-block.md" --select "CORE-INIT-PROJECT,SERENA-GORTEX-PROJECT" --confirm "$confirmed_token"
```

Für nur einen Block ist `--select` dessen Markername; für keinen `none`. Das Token ist ein Drift-Nachweis, keine Benutzerfreigabe: kopiere es nicht ohne separate Bestätigung nach `apply`. Nach bestätigtem Schreiben prüfe den vollständigen Zielinhalt; bei Fehlern keine blinde Wiederherstellung über zwischenzeitliche Fremdänderungen.

Im reinen Abgleich bedeutet **completed**: bestätigte Auswahl geschrieben (oder keiner gewählt), Außenbereiche und Fakten erhalten, Zweitlauf für ausgewählte Blöcke diff-frei. **blocked**: unklare Faktenabgrenzung, ungültige Marker oder fehlende Bestätigung; **failed**: Schreib-/Verifikationsfehler mit benannter Teilwirkung. Providerbereitschaft und Artefaktschutz werden dabei nicht bewertet. Die folgenden Zustände gelten nur für normales Init.

## Ergebnisse und Zustände

- **completed:** Konfigurator-Laufzeit und Preflight sind belegt, ausgewählte Provideraktionen sind geprüft, der bestätigte Projektblock und der Artefaktschutz sind verifiziert, keine Artefakte in den beiden Verzeichnissen sind getrackt und ein zweiter Lauf wäre diff-frei.
- **partial:** Der Harness oder Block ist gültig, aber die Konfigurator-Laufzeit oder eine optionale Providerfähigkeit fehlt oder bereits getrackte Artefakte lassen eine Datenschutzlücke offen; nenne die konkrete Einschränkung.
- **blocked:** Projektgrenze, Eingabeartefakt, exakte Diff-Bestätigung, sichere Markerlage oder erforderliche Providerfähigkeit fehlt oder der wirksame Artefaktschutz bleibt ungeklärt.
- **failed:** Eine ausgewählte Aktion oder verifizierte Mutation schlug fehl; nenne Pfad, Teilwirkung und sicheren nächsten Schritt.

Ist Gortex nicht bereit, Serena aber projektspezifisch verfügbar, darf der Init mit sichtbarer Degradierung abschließen. Sind beide nicht bereit, darf der Repository-Harness entstehen; spätere Gortex-pflichtige Tasks bleiben jedoch blockiert.

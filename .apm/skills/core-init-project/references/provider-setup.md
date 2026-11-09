# Provider-Setup und Python-Laufzeit

Diese interne Referenz gehört zu `core-init-project` und ist kein eigenständiger
Skill. Lade sie für Provider-Readiness, Interpreterauflösung oder ausdrücklich
ausgewählte Provideraktionen. Der reine `AGENTS.md`-Blockabgleich lädt sie nicht.

## Providerreihenfolge

1. Verwende Gortex, wenn dessen MCP gesund ist und das Repository bereits
   erfasst ist.
2. Verwende projektbezogenes Serena, wenn Gortex die Operation nicht bedienen
   kann.
3. Im bekannten Projekt verwende native Datei- und Suchwerkzeuge nur, wenn beide
   Provider die Operation nicht bedienen können; eine unbekannte Datei ist keine
   Ausnahme. Vor Projektzuordnung ist ausschließlich eng begrenzte native
   Pfad-/Namenssuche zur Projektermittlung zulässig, keine Inhalts-/Symbolsuche.
   Die Home-Ausnahme bleibt erhalten: bei CWD `Path.home()` native Datei-, Such-
   und Laufzeitwerkzeuge statt Gortex oder Serena.
4. Begrenze Serena auf das konkrete Projekt; Benutzer-Home, Dateisystemroot und
   breite Elternverzeichnisse sind keine Projektroots.
5. Kehre zu Gortex zurück, sobald es verfügbar ist. Wiederhole eine Abfrage
   nicht allein zum Providervergleich.

Gortex bleibt primärer Code-Intelligence-Provider. Ein vorbereiteter
Serena-Fallback ändert diese Primärauswahl nicht.

## Aufruf und Auswahl

1. Löse die konkrete Repositorywurzel auf und prüfe Gortex-Gesundheit und
   vorhandenes Tracking read-only.
2. Auditiere Serena-CLI, Projektinitialisierung, effektive Sprachen und die
   autoritative projektbezogene MCP-Quelle read-only.
3. Stelle nur erforderliche Aktionen gemeinsam zur Auswahl: Serena prüfen oder
   einrichten, Serena-Sprachen abgleichen, projektbezogene Anweisungen prüfen,
   Repository in Gortex tracken. Bereits eindeutig ausgewählte Aktionen werden
   nicht erneut abgefragt.
4. Jede Auswahl autorisiert nur ihre konkret gezeigte Mutation. Nicht ausgewählte
   Prüfungen bleiben read-only.

Readiness bleibt rein lesend. Serena-Initialisierung, Sprachabgleich und
MCP-Konfiguration benötigen jeweils ausdrückliche Autorisierung für das konkrete
Projekt; normales Init oder ein fehlender Fallback erteilen diese nicht.

`core-init-project` bleibt Eigentümer seines Projektblocks und aktiviert keinen
konkurrierenden `--apply-agents`-Schreibmodus. Globale Benutzeranweisungen
gehören `core-user2agent-instructions`; diese Integration erweitert weder deren
noch die globale Schreibberechtigung des Init-Skills. Die bisherigen selektiven
Helper-CLI-Optionen bleiben für ihren bestehenden, gesondert autorisierten
Eigentümerkontext erhalten.

## Verbindliche Providergrenzen

- Erhalte gleichwertige vollständige Anleitung, ersetze verwaltete Blöcke in
  place und ergänze nur fehlende Abschnitte. Einen historischen globalen
  `SERENA-PLAYBOOK`-Block migriert nur der zuständige Anweisungsowner.
- Halte Home-Sicherheitsregeln im globalen Block und Projektanbieterfolge sowie
  Serena-Readiness im Projektblock getrennt.
- Verwende im Benutzer-Home native Datei-, Such- und Laufzeitwerkzeuge; die
  lokale Serena-CLI dient dort nur Konfiguration, Projektverwaltung, Memories
  und Wiederherstellung.
- Halte die effektive globale Serena-Metadatenkonfiguration bei
  `language_servers: []` oder altem `languages: []`; die gewinnende Datei ist
  `<home>/.serena/.serena/project.local.yml`, wenn sie einen Sprachschlüssel
  definiert, sonst `project.yml`. Die globale `serena_config.yml` erhält keine
  Sprachliste; `language_backend: LSP` bleibt gültig.
- Globales Serena-MCP bleibt deprovisioniert. Nur eine bestätigte autoritative
  Projektquelle erhält den projektbezogenen Serena-MCP-Eintrag.
- Wähle die dominante Quellsprache und behalte eine Nebensprache nur ab fünf
  Dateien oder 10 % erkannter Quelltextdateien. Konfigurierte Backendvarianten
  bleiben erhalten, solange ihre Basissprache ausgewählt ist.
- Ändere Gortex-Tracking nur nach ausdrücklicher Auswahl; entferne oder
  verändere vorhandenes Tracking niemals implizit.

## Python Runtime

Löse die Laufzeit vor dem ersten `serena_safety.py`-Aufruf auf.
[REQUIREMENTS.md](../REQUIREMENTS.md) und
[scripts/requirements.txt](../scripts/requirements.txt) besitzen das
Python-Minimum und den Paketbereich; PyYAML ersetzt `ruamel.yaml` nicht.

1. Prüfe diese Kandidaten in Reihenfolge und stoppe beim ersten erfolgreichen
   Nachweis. Fehlender Interpreter, `ImportError` oder eine Version außerhalb
   der Anforderungen führt zum nächsten Kandidaten:
   1. Aktueller Interpreter: `python3` oder `python` auf `PATH`
      (`py -3` unter Windows).
   2. Projektumgebung: `<project>/.venv` oder der vom Taskrunner deklarierte
      Interpreter, über `mise which python` ermittelt.
   3. Eine vom Nutzer oder Projekt konkret für diesen Zweck benannte
      Toolumgebung.
   4. Der Interpreter des aufgelösten `serena`-Launchers.

   Diese vier Quellen sind die gesamte begrenzte Suche; Home, Caches und andere
   Umgebungen werden nicht durchsucht.
2. Prüfe jeden direkten Kandidaten read-only. Ein erfolgreicher Import allein
   genügt nicht; Python- und Paketversion müssen zu den Anforderungen passen:

   ```text
   "<candidate>" -B -c "import sys; from importlib.metadata import version; from ruamel.yaml import YAML, YAMLError; print(sys.executable); print(sys.version); print(version('ruamel.yaml'))"
   ```

3. Prüfe einen von mise gelieferten Kandidaten im tatsächlichen Runner, nicht
   nur über einen nackten Host-Prozess. Deaktiviere automatische Installation
   ausschließlich für diesen Prozess und verwende den absoluten Kandidatenpfad:

   ```text
   MISE_AUTO_INSTALL=0 MISE_EXEC_AUTO_INSTALL=0 mise which python
   MISE_AUTO_INSTALL=0 MISE_EXEC_AUTO_INSTALL=0 mise exec -- "<absolute-candidate>" -B -c "<probe>"
   ```

   `mise exec` führt den Befehl in seiner Child-Umgebung aus. Die beiden
   Variablen verhindern fehlende Toolinstallationen bei diesen Read-only-Probes;
   bestehende mise-Einstellungen oder Umgebungsvariablen werden nicht verändert.
   Gepinnte Projekt- oder Prüfbefehle werden nicht still ersetzt.

   Benötigt der nachgewiesene Runner eine bereits vorhandene virtuelle
   Umgebung, darf `VIRTUAL_ENV=<existing-env>` zusammen mit einem
   prozesslokalen `PATH=<existing-env>/bin:$PATH` nur nach einem erfolgreichen
   Probe derselben absoluten Interpreteridentität und Abhängigkeit verwendet
   werden. Keine persistente Aktivierung, keine Hostpfade als portable Vorgabe
   und keine Änderung an Projekt-, mise-, Python- oder App-Konfiguration.
4. Verwende das ausgegebene absolute `sys.executable` als `<python>`. War die
   Runnerprobe erforderlich, führe jeden Audit-, Apply- und Re-Audit-Aufruf mit
   derselben prozesslokalen `mise exec`-Form aus; sonst direkt mit
   `"<python>"`. `PYTHONPATH` bleibt unverändert.
5. Wenn kein Kandidaten nachweisbar passt, ist nur eine isolierte Neueinrichtung
   möglich:
   - Eine konkrete Freigabe, die genau diese Laufzeiteinrichtung benannt, deckt
     sie ohne erneute Routinefrage. Eine Serena-Provideraktion allein ist keine
     Setupfreigabe.
   - Ohne diese Freigabe frage einmal gemeinsam mit der Aufrufauswahl und zeige
     Basisinterpreter, absoluten Umgebungspfad, Requirementsdatei, Befehle,
     Netzwerk-/Dateiwirkungen und Entfernungspfad.
   - Führe nur diese Befehle mit einem ausreichend neuen Basisinterpreter und
     einer neuen dedizierten Umgebung aus; wiederhole danach die Probe:

     ```text
     "<base-python>" -m venv "<absolute-env>"
     "<env-python>" -m pip install -r "<absolute-skill>/scripts/requirements.txt"
     ```

   - Installiere ausschließlich dort: kein System-, Global- oder `--user`-pip,
     `sudo`, `--break-system-packages`, keine App-Abhängigkeitsänderung und
     keine Änderung an Projekt- oder Serena-Umgebung.
6. Bei abgelehnter oder fehlgeschlagener Einrichtung bleibt das Audit ungestartet;
   melde die konkrete Lücke als blocked. Ein ungestartetes Audit ist kein
   Readiness-Nachweis.

## Workflow

1. Lies [configuration-precedence.md](configuration-precedence.md), löse
   `<python>` über [Python Runtime](#python-runtime) und führe vom Bundle-Root
   `"<python>" scripts/serena_safety.py --cwd <project> --home <home>` als
   read-only Baseline aus; bei Runnerbedarf mit derselben nachgewiesenen
   `mise exec`-Form.
2. Bilde ausdrücklich ausgewählte Aktionen auf `--apply-agents`,
   `--apply-serena` und `--apply-languages` ab. `--apply` bleibt der
   bestehende explizite Shortcut für alle verwalteten Aktionen im jeweils
   autorisierten Eigentümerkontext.
3. Verwende für ausgewähltes Gortex-Tracking die konfigurierte MCP-Operation und
   verifiziere den bereiten Zustand; kein CLI-Fallback bei nativem MCP-Profil.
4. Initialisiere bei ausgewählter Serena-Einrichtung nur das konkrete Projekt,
   verifiziere die autoritative Projekt-MCP-Quelle und behalte Gortex primär.
5. Schreibe ausgewählte Sprachen in die gewinnende `project.local.yml` oder
   `project.yml`.
6. Ändere nur eine bestätigte MCP-SSOT und regeneriere Projektionen.
7. Wiederhole das Audit. Starte Serena nach Konfigurations-/Sprachänderungen neu
   und prüfe die effektive Client-MCP-Liste, sofern verfügbar.
8. Berichte Gortex, Serena, native Fallbacks, globale Anleitung und Sprachen
   getrennt.

## Rangfolge und Eigentum

- `serena start-mcp-server --tool-timeout 10` überschreibt globales
  `tool_timeout: 10.0`.
- Schreibe `tool_timeout` nicht in Projekt-YAML.
- `project.local.yml` mit `language_servers`, altem `languages` oder
  `language` gewinnt gegenüber `project.yml`. Erhalte die vorhandene
  Schlüsselform.
- Widersprüchliche Schlüssel erzeugen `conflicting-language-keys` und
  blockieren Apply. `language_servers: []` ist für Projekte ohne Quellcode
  gültig.
- OpenCode-`timeout` verwendet Millisekunden (`10000`), Serena-CLI Sekunden
  (`10`). Schreibe nur in die bestätigte autoritative Projektquelle.
- Setze unter Windows `PYTHONIOENCODING=utf-8` und `PYTHONUTF8=1` in der
  aktiven lokalen MCP-Quelle und regeneriere Projektionen.

## Schutz und Recovery

- Keine breiten Serena-Scans über Home, Repository, Dependencies, generierte
  Ausgaben, Binärdateien, Caches oder Vendor-Bäume und keine parallelen breiten
  Serena-Aufrufe.
- Überschreibe niemals eine ganze `AGENTS.md`; bearbeite keine generierten
  Projektionen, Laufzeitkopien oder Symlinks bei vorhandener Upstream-Quelle.
- Bearbeite keine MCPM-Registry manuell; verwende nach ausdrücklicher
  Autorisierung die Owner-CLI.
- Sichere jede verwaltete Datei und rolle ausgewählte Schreibzugriffe zurück,
  wenn Initialisierung, Parsing oder Schreiben fehlschlägt.
- Wiederhole einen Serena-Timeout einmal mit engerer Anfrage. Nach einem zweiten
  Timeout verwende die lokale CLI aus dem konkreten Workspace. Stoppe nur einen
  bestätigt veralteten `serena ... start-mcp-server`-Prozess, starte die
  Client-Sitzung neu und wiederhole die Anfrage.

## Ressourcen

- `references/configuration-precedence.md`: Provider-, Timeout-, Client-,
  Sprach- und Eigentumsregeln.
- `scripts/serena_safety.py`: Audit und selektiv autorisierte Writes.
- `scripts/test_serena_safety.py`: Original-Regressionstests samt Vorlagengrenzen.

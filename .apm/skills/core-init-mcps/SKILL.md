---
name: core-init-mcps
description: Richtet die MCP-Toolprovider der Werkbank einmal pro Umgebung kontrolliert ein; leitet die Zielkonfiguration aus der Paketdeklaration ab, zeigt sie vorab, materialisiert nur einzeln bestätigte Einträge im Zielharness und führt Health-Checks für Gortex, Context7, YouTube Transcript, Serena und Honcho aus. Verwenden nach der APM-Paketinstallation, bei Providerwechsel oder bei umgebungsspezifischen Providerstörungen; nicht für projektbezogene Gortex- oder Serena-Konfiguration (core-init-project), Paketfreigabevalidierung oder laufende Recherche.
---

# Core Init MCPs

`core-init-mcps` besitzt die umgebungsabhängige Provider-Einrichtung der Werkbank: Vorschau der Zielkonfiguration, einzeln bestätigte Materialisierung und Health-Checks. Es führt keinen Änderungsworkflow aus, schreibt keinen `AGENTS.md`-Block und startet keine Subagenten.

## Eigentumsgrenzen

| Schicht | Eigentümer | Inhalt |
|---|---|---|
| portable Deklaration | `apm.yml` und versionierter `apm.lock.yaml` der Paketquelle | MCP-Abhängigkeiten, Registry-IDs, Transporte, Tool-Allowlisten |
| umgebungsabhängige Einrichtung | `core-init-mcps` | Vorschau, bestätigte Materialisierung, Health-Checks, Bereitschaftsbericht |
| Credentials | Benutzer allein | Tokens, API-Keys und andere Secrets im sicheren Speicher des Zielharnesses |
| projektspezifische Providerinitialisierung | `core-init-project` mit `gortex-serena-configurator` | Gortex-Tracking, Serena-Sprachen, Providerreihenfolge im Projektblock |

`core-init-mcps` ändert weder Paketdeklaration noch Lockfile und erzeugt keine zweite, konkurrierende MCP-Konfigurationsdatei der Werkbank. Die Paketfreigabevalidierung mit `apm compile --validate`, Preview und Dry-Run gehört zur Paketfreigabe, nicht zu diesem Skill.

## Verbindliche Verträge

Lade vor der Ausführung das [Toolrouting](../core-shared/references/tool-routing.md). Die dortigen Providergrenzen gelten unverändert auch für die Einrichtung: Gortex bleibt primäre Code-Intelligence, Serena bleibt auf ausdrücklich konfigurierte Projekte begrenzt, Context7 und YouTube Transcript bleiben auf ihre dokumentierten Einsatzzwecke beschränkt, und Honcho bleibt eine optionale, nicht autoritative Erinnerung.

## Workflow

### 1. Deklarierte Zielkonfiguration ermitteln

1. Lies `apm.yml` und `apm.lock.yaml` der installierten Paketquelle read-only.
2. Leite je Provider Registry-ID, aufgelöste Version oder Commit, Transport, Zielharnesses und Tool-Allowlisten ab.
3. Behandle lokal vorhandene, nicht deklarierte Provider als Umgebungszustand: melden, weder entfernen noch stillschweigend umkonfigurieren.

### 2. Ist-Zustand der Zielharnesses erfassen

1. Ermittle die konkreten Zielharnesses und ihre autoritativen MCP-Konfigurationspfade.
2. Erfasse read-only, welche deklarierten Provider bereits materialisiert sind und welche Abweichungen zum Lockfile bestehen.
3. Weise Konfigurationsdateien außerhalb der APM-Projektion nur als Fund aus; schreibe sie nicht.

### 3. Zielkonfiguration vorab anzeigen

Zeige je Provider und Zielharness:

- deklarierte Registry-ID und die im Lockfile festgehaltene Auflösung,
- Transport und geplante Einträge,
- geplante Tool-Allowlisten,
- den exakten erwarteten Diff der Harness-Konfiguration.

Ohne belastbare Deklaration oder bei Widerspruch zwischen Deklaration und Lockfile stoppe mit `blocked`; rate keine Einträge und nenne die Lücke.

### 4. Explizite Bestätigung einholen

1. Lass jede Materialisierung oder Änderung einzeln und ausdrücklich bestätigen.
2. Schweigen, Zeitablauf, frühere allgemeine Zustimmung oder eine veränderte Vorschau genügen nicht.
3. Verwirf die Vorschau, wenn sich Deklaration, Lockfile oder Harness-Zustand vor der Bestätigung ändern.

### 5. Bestätigte Einträge materialisieren

1. Materialisiere ausschließlich bestätigte, deklarierte Einträge über den vorgesehenen APM-Mechanismus des Zielharnesses; verbindlich ist der Lockfile-Stand, es wird nichts neu aufgelöst.
2. Schreibe keine Harness-Konfigurationsdatei direkt, umgehe keine Projektion und lege keine eigene Konfigurationsdatei an.
3. Lasse unbestätigte und fremde Einträge unverändert; entferne nichts.
4. Prüfe nach der Materialisierung den Ist-Zustand gegen die Vorschau; Abweichungen werden gemeldet, nicht geglättet.
5. Ein erneuter Lauf ohne neue Bestätigung erzeugt keinen Diff.

### 6. Credentials und Secrets

- Trage keine Tokens, API-Keys, Passwörter oder anderen Secrets in Konfiguration, Berichte oder Logs ein und fordere sie nicht an.
- Fehlende Credentials werden je Provider als Bereitschaftslücke gemeldet, nicht durch schwächere oder unsichere Authentifizierung umgangen.
- Erscheint ein Secret-Wert versehentlich in einer Ausgabe, redigiere ihn und weise auf die sichere Ablage im Zielharness hin.

### 7. Health-Checks ausführen

Führe je materialisiertem Provider die kleinste unschädliche, read-only Prüfung aus:

| Provider | Kleinste Prüfung | Grenze |
|---|---|---|
| Gortex | MCP-Verbindung und operative Bereitschaft | `repo_not_tracked` ist kein Fehler dieses Skills; Tracking gehört zu `core-init-project` |
| Context7 | Auflösen einer bekannten Bibliotheks-ID | keine Recherche über ein enges Thema hinaus |
| YouTube Transcript | Verfügbarkeit der Transkriptwerkzeuge | höchstens eine bekannte URL als Prüfeingabe; keine Videosuche |
| Serena | MCP-Verfügbarkeit | Projektinitialisierung und Sprachabgleich gehören zu `core-init-project` |
| Honcho | Verbindung des Memory-Adapters | optionaler Provider; fehlt er, bleibt das eine sichtbare Einschränkung |

Ein nicht ausführbarer Check wird für diesen Provider als nicht bereit gemeldet, nicht durch Annahmen oder schwächere Ersatzprüfungen ersetzt.

### 8. Bereitschaft berichten

Berichte je Provider getrennt: deklariert, bestätigt, materialisiert, bereit, sichtbare Degradierung und Credential-Lücke. Persistiere keine flüchtigen Health-Werte in `AGENTS.md` oder anderen Repositorydateien.

## Ergebnisse und Zustände

- **completed:** alle deklarierten Provider sind bestätigt materialisiert, und ihre Health-Checks bestehen mit beobachtbarer Evidenz.
- **partial:** optionale Provider wie Honcho fehlen, oder einzelne Health-Checks sind nicht ausführbar; die Degradierung ist sichtbar.
- **blocked:** erforderliche Bestätigung, belastbare Deklaration, Zielharness oder Credentials fehlen; nie durch stillschweigende Konfiguration umgangen.
- **failed:** eine bestätigte Materialisierung schlug fehl; nenne Pfad, beobachtete Teilwirkung und sicheren nächsten Schritt.

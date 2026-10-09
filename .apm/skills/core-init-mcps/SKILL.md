---
name: core-init-mcps
description: Prüft read-only die bereits vorhandenen MCP-Provider eines Harnesses und berichtet Bereitschaftslücken; installiert oder konfiguriert nichts und sucht keine Secrets. Verwenden für eine Bestandsprüfung; für Installation unter Linux den passenden Skill mcp-install-linux oder unter Windows mcp-install-windows benennen, ohne ihn automatisch auszuführen.
---

# Core Init MCPs

`core-init-mcps` führt ausschließlich eine read-only Bestands- und Bereitschaftsprüfung der bereits im Zielharness vorhandenen Provider aus. Es installiert, aktiviert oder konfiguriert keine Provider, ändert weder Harness-Dateien noch Paketdateien und führt keinen Änderungsworkflow aus.

## Eigentumsgrenzen

| Schicht | Eigentümer | Inhalt |
|---|---|---|
| vorhandene Harness-Provider | `core-init-mcps` | read-only Erkennung und Bereitschaftsbericht |
| Credentials | Benutzer allein | sichere Ablage; der Skill sucht, liest oder erfragt keine Secrets |
| projektspezifische Providerinitialisierung | `core-init-project` mit `gortex-serena-configurator` | ausschließlich konkret autorisierte Projektaktionen; kein globales Serena |

Eine `apm.yml`-Deklaration oder ein Paket-Lockfile ist weder Voraussetzung noch Quelle für diese Bestandsprüfung. Dieser Skill ändert keine Paket-, Harness- oder Providerkonfiguration. Paketfreigabevalidierung und Installation sind separate, ausdrücklich autorisierte Aufgaben.

## Verbindliche Verträge

Lade vor der Ausführung das [Toolrouting](../core-shared/references/tool-routing.md). Die dortigen Providergrenzen gelten unverändert auch für die Prüfung: Gortex bleibt primäre Code-Intelligence, Serena bleibt auf ausdrücklich konfigurierte Projekte begrenzt, Context7 und YouTube Transcript bleiben auf ihre dokumentierten Einsatzzwecke beschränkt, und Honcho bleibt eine optionale, nicht autoritative Erinnerung.

## Workflow

1. Prüfe read-only, welche Provider im ausdrücklich bezeichneten Harness bereits vorhanden und erreichbar sind. Nutze nur die für den Provider passende, kleinste unschädliche Bereitschaftsprüfung. Eine Deklaration oder ein Lockfile wird nicht vorausgesetzt.
2. Lies oder inspiziere keine Secret-Werte, Schlüsselbunde oder Credential-Speicher. Fehlende Provider, Berechtigungen oder Credentials werden als nicht verfügbar gemeldet; es wird nichts gesucht, angefordert, eingerichtet oder geändert.
3. Wenn Einrichtung gewünscht ist, benenne lediglich den plattformgerechten Installationsskill (`mcp-install-linux`/`mcp-install-windows`). Starte keinen Installer und ändere keine Provider-, Harness-, Paket- oder Projektkonfiguration.
4. Berichte je vorhandenem Provider die beobachtete Verfügbarkeit, die tatsächlich ausgeführte Prüfung und Grenzen. Persistiere keine flüchtigen Health-Werte.

## Ergebnisse und Zustände

- **completed:** die read-only Prüfung der bezeichneten vorhandenen Provider ist mit beobachtbarer Evidenz abgeschlossen.
- **partial:** einzelne Prüfungen sind nicht ausführbar oder Provider/Credentials fehlen; die Lücken sind sichtbar.
- **blocked:** ein eindeutiger Zielharness oder erforderlicher Zugriff für die Prüfung fehlt. Keine Lücke wird durch Konfiguration oder Installation umgangen.
- **failed:** eine read-only Prüfung schlug fehl; nenne die beobachtete Einschränkung, ohne eine Änderung vorzunehmen.

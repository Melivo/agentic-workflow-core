---
name: core-typesafe
description: Stellt eine kleine Python-API bereit, die einzelne Skill-Relevanz-, Anforderungsabdeckungs- und Behauptungsstützungsfragen über TypeSafe als beratende Wahrscheinlichkeiten auswertet. Verwenden, wenn der reguläre Core-Planreview-Versuch oder ein ausdrücklich beauftragter Core-Aufruf eines der Profile skill_relevance, requirement_coverage oder claim_support benötigt; nicht für Freigaben, Dispatch, Reviewurteile, Workflowstatus oder eigene Fragenentwürfe.
---

# Core TypeSafe

Das Modul [scripts/typesafe_eval.py](scripts/typesafe_eval.py) verbirgt Fragenprofile, Antwortprüfung und HTTP. Fachlicher Vertrag und Nutzungsgrenzen stehen im [TypeSafe-Vertrag](../core-shared/references/typesafe-contract.md). Ergebnisse sind Hinweise: Entscheidungen bleiben bei Menschen und deterministischem Code.

## Bildbeispiele

Bei ausdrücklich freigegebener Arbeit mit den synthetischen PNG-Lernfällen die [Bedienungsreferenz](references/images.md) laden; für Befunde und Grenzen zusätzlich [Bild-Evaluation](references/images-evaluation.md). Diese optionale Probe erweitert weder die Textprofile noch Planvergleichsdaten.

## Reine Planvergleichsdaten

Das optionale Modul [scripts/plan_comparison.py](scripts/plan_comparison.py) bindet unveränderte Planbytes und Kriterien und erzeugt detached `plan-comparison/v1`-Ereignisdaten. Seine öffentliche API umfasst `bind_plan`, `model_event`, `fix_review`, `comparison_event`, `append_event` sowie `ComparisonError`. Es führt weder IO noch Modellaufrufe oder Workflowänderungen aus; der Owner bewahrt Originale, vollständige Ereignishistorie und freie Zielpfade. Es beweist keine Blindheit, authentifiziert keine Datensätze und entscheidet keine Wahrscheinlichkeiten. Bei jedem Core-Planreview versucht der Owner regulär eine minimierte Vorbewertung ohne Projektpilot-Auswahl; fehlende Datenfreigabe, Fähigkeit oder technische Fehler lassen die Beobachtung offen, normales Review und Produktarbeit gehen weiter. Der normale Ablauf gehört `core-plan`; die organisatorische Leseregel steht in der [Evaluationsordner-Vorlage](assets/evaluation-directory-AGENTS.md).

## Portable Sammlung und lokale Konfiguration

[scripts/typesafe_collection.py](scripts/typesafe_collection.py) ist die einzige Implementierung von Projektion, Collection, Outbox und explizitem Transport. Das Repositoryskript gleichen Namens ist nur ein Kompatibilitätswrapper. Die bestehenden Datenformate und APIs bleiben erhalten; Import oder Enqueue startet keinen Versand. Nur ein passendes Commit-ACK entfernt einen Outboxeintrag. Fehler bleiben offen, unbestätigte Einträge erhalten.

Für die tatsächlich benötigte lokale Transportkonfiguration steht [scripts/typesafe_owner.py](scripts/typesafe_owner.py) bereit: Lege das Bundleverzeichnis `scripts/` auf den Importpfad und verwende `load_config(path)` für `(policy, sender)`. Es liest eine begrenzte nichtgeheime JSON-Datei, erzeugt aber weder Ablagen noch Modell-, SSH- oder Scheduleraufrufe. Der Defaultpfad ist `~/.config/agentic-workflow-core/typesafe.json`; privater Betriebszustand gehört nach `~/.local/state/agentic-workflow-core/typesafe/` (eigene 0700-Ablage, Dateien 0600). Einrichtung braucht eine gesonderte Hostfreigabe.

Die geschlossene Config enthält `projects: {projects: ["synthetic-a", "synthetic-b"], core_project_ids: true}` und `transport: {ssh_target, binding: {hostname, user, port}, remote_script}`. Werte stammen aus freigegebener lokaler Konfiguration; keine fest eingebauten Hostnamen oder privaten Pfade. Der Sender prüft die effektive SSH-Bindung vor dem Ereignisversand; Abweichung verweigert ihn. `remote_script` ist ein absoluter sicherer Pythonpfad, kein freies Shellkommando; Dienst-UID und Remoteaktion bleiben beschränkt.

`project_id(identity)` erzeugt lokal deterministisch `core-` plus 64 kleine SHA256-Hexzeichen aus einer stabilen lokalen Projektidentität. Der Owner wählt dieselbe Identität über Sitzungen hinweg; weder Identität noch Pfad/Namen werden exportiert. Hashing ist keine Authentifizierung und schützt nicht gegen Erraten. `load_projects` und `project_policy` behalten die strikte synthetische Allowlist als Legacydefault; nur das explizite boolesche `core_project_ids: true` erlaubt zusätzlich exakt dieses Core-ID-Format, keine Wildcard. Die bestehende UID-/Socketgrenze bleibt nötig.

`month_end_due(aware_datetime)` prüft vor Daten-/Berichtswirkung den letzten Kalendertag um 22:00 Europe/Berlin. Es ist nur eine Kalenderprüfung, kein Scheduler und kein Duplikatschutz; tatsächliche Zeitpläne, einmalige Ausführung und Receipts bleiben beim vorhandenen Schedulerowner.

## Vor einem Aufruf klären

- Der Auftrag erlaubt den Versand genau dieser Textausschnitte, die Requestzahl und die Kosten. Es gibt keinen automatischen Secret- oder Datenschutzfilter; der Aufrufer verantwortet jede Passage.
- Der Aufrufer nennt Modellkennung und Core-Version ausdrücklich.
- Für den bevorzugten optionalen MCP-Weg braucht Core keinen lokalen Schlüssel; die Authentifizierung bleibt beim bereits eingerichteten MCP. Nur der HTTPS-Fallback benötigt `TYPESAFE_API_KEY` in der geerbten Umgebung. Fehlt er, melde `key_missing` als Blocker und wechsle nicht zu einem anderen Weg.

## Direkter HTTPS-Fallback

Geprüft mit Linux x64 und Python 3.13.14; andere Versionen/Plattformen nicht qualifiziert. Keine Installation erforderlich: Lege `scripts/` auf den Importpfad.

```python
import typesafe_eval as ts

result = ts.evaluate(
    'claim_support',
    {'claim': '...', 'ref': 'docs/a.md#L3', 'passage': '...'},
    model='jev-latest', core_version='0.14.1', transport=ts.https_transport)
```

Ohne Transport prüft `ts.build_request(profile, inputs, model=...)` die Eingabe und baut die Anfrage netzfrei. Tests übergeben als `transport` eine Funktion `payload -> dict`; sie meldet Fehler per `ts.TransportError(code, http_status)`.

## Optionaler Harness-MCP-Weg

Wenn der Harness die Fähigkeit für `typesafe-mcp-arbitype.evaluate` aktuell entdeckt und den ausdrücklich freigegebenen Request ausführen darf, bevorzugt diesen bereits eingerichteten optionalen MCP vor HTTPS. Rufe zuerst `search` für den exakten Namespace `typesafe-mcp-arbitype` und die Operation `evaluate` auf, prüfe das zurückgegebene aktuelle Schema und leite nur `state`, `questions` und `model` aus `prepared.payload` weiter. Übergib die strukturierte Rohantwort unverändert an `ts.finalize_response(prepared, response, core_version=..., duration_seconds=...)`; der Owner misst die Dauer lokal und ordnet die Antwort dem tatsächlichen Aufruf zu. `typesafe_eval` selbst hat weder MCP-Client noch CodeMode-Zugriff und ruft kein Tool auf.

Der Owner behält Originalinputs, Profil, Modellkennung, Fragenversion und -Fingerprint, Referenzen, Core-Version sowie den tatsächlich übergebenen Payload lokal unverändert. Bei einem Prozesswechsel ruft der Abschlussprozess `build_request` mit diesen Originalinputs frisch auf und vergleicht den neu gebauten Payload exakt strukturell und wertmäßig sowie Profil, Modell, Fragenversion, Fingerprint, Referenzen und Core-Version mit der ursprünglichen Vorbereitung und dem tatsächlichen Versand. Bei Drift bleibt der Abschluss offen. Übergib `finalize_response` ausschließlich das unveränderte echte `PreparedRequest`-Objekt dieses frischen Builds; deserialisierte oder manuell konstruierte Objekte und reparierte Rohantworten sind ausgeschlossen. Das Modul validiert Wertgleichheit, nicht Objektidentität über Prozesse. Der Owner verantwortet die Zuordnung von Aufruf und Rohantwort; der Abgleich beweist weder kryptographische Herkunft noch tatsächliche MCP-/Modellantwort. Das Bundle liefert keine Bridge oder residente Laufzeit; falls der Harness Payload und Rohantwort nicht übergeben kann, bleibt diese Fähigkeit offen statt als vorhanden ausgegeben zu werden.

Fehlende Request-/Datenfreigabe oder kein sendbarer `prepared.outcome` bedeutet kein Versand. HTTPS darf nur bewusst gewählt werden, wenn der MCP bzw. sein Endpoint bereits vor einem möglichen Bewertungsversand nachweislich nicht verfügbar ist und die HTTP-Voraussetzungen erfüllt sind. Nach Toolaufruf, möglichem Versand, Timeout, Auth-, API- oder Antwortfehler gibt es keinen automatischen Retry und keinen HTTP-Zweitversand. Ein expliziter MCP-Toolaufruf ist keine Garantie für genau eine interne Provideranfrage; unbekannte Retry-/Kostenangaben bleiben unbekannt.

| Profil | Felder von `inputs` | Fragen |
| --- | --- | --- |
| `skill_relevance` | `goal`, `task`, `candidates: [{ref, responsibility}]` | Noul `fit`, Choice `central_responsibility` |
| `requirement_coverage` | `criterion`, `task`, `evidence: [{ref, text}]` | Noul `covers` |
| `claim_support` | `claim`, `ref`, `passage` | Noul `supports`, Choice `relation`, Noul `matching_passage` |

## Ergebnis lesen

`EvaluationResult` (`to_dict()` für Daten) enthält `outcome`, `reason`, `uncertainty`, `answers`, `references`, `error`, `http_status`, `request_sent`, `requested_model`, `response_model`, `question_version`, `question_fingerprint`, `core_version`, `duration_seconds` und `usage`.

| `outcome` / `reason` | Bedeutung | Nächster Schritt |
| --- | --- | --- |
| `no_fit` / `no_candidates` | Keine Kandidaten, nichts gesendet | Kein Modellurteil; der Aufrufer entscheidet über die Kandidatenliste. |
| `unresolved` / `missing_evidence`, `missing_passage` | Originaltext fehlt (`None`), nichts gesendet | Quelle beschaffen; nicht als „nein“ werten. |
| `unresolved` / `no_confirmed_evaluation_rule` | Modell hat geantwortet; es gibt noch keine bestätigte Auswertungsregel | Rohe Wahrscheinlichkeiten als Hinweis nutzen; Schwellen nicht selbst erfinden. |
| `error` | Technischer Fehler, keine Modellantwort | Nach `error`-Code behandeln; nie als negatives Urteil werten. |

`request_sent=False` bedeutet nachweislich nichts gesendet, insbesondere bei `key_missing` und `key_invalid`. `True` bedeutet Versand möglich oder erfolgt, nicht bestätigte Zustellung; auch bei Timeout oder Netzfehler kann bereits gesendet worden sein.

Der reale Adapter begrenzt DNS, TCP/TLS, Statuszeile, Header und Body gemeinsam auf `TIMEOUT_SECONDS` (Standard: 30 Sekunden). Er nutzt einen privaten kurzlebigen Python-Prozess, beendet ihn bei Fristablauf und wartet auf dessen Ende; es bleibt kein sendender Hintergrundthread. Prozessstart und Aufräumen können geringe Betriebssystemlatenz hinzufügen. Requestdaten gehen nur durch die Eingabepipe, nicht durch Prozessargumente; Antworten sind auf `MAX_RESPONSE_BYTES` begrenzt (1 MiB).

`uncertainty` ist `unassessed` bei einer Modellantwort und sonst `no_model_answer`. Fehlende Token-Zähler bleiben `None`, sie bedeuten weder null Tokens noch einen Kostennachweis.

| `error` | Ursache und Behebung |
| --- | --- |
| `input_invalid` | Felder oder Typen verletzen den Profilvertrag; Aufruf korrigieren. |
| `transport_missing` | Kein Transport übergeben; bewusst einen wählen oder nur `build_request` nutzen. |
| `key_missing`, `key_invalid` | Schlüssel fehlt oder hat kein Headerformat; als Blocker melden. |
| `auth_failed` | HTTP 401/403; Schlüsselberechtigung durch den Nutzer prüfen lassen. |
| `http_error` | Sonstiger Status in `http_status`, auch abgelehnte Weiterleitungen; es gibt keinen automatischen Retry. |
| `timeout`, `network_error` | Keine verwertbare Antwort; ein erneuter Versuch braucht einen neuen Entschluss des Aufrufers. |
| `response_too_large`, `response_invalid` | Antwort über dem Limit oder vertragswidrig; sie wird weder repariert noch normalisiert. |
| `transport_failed` | Ein übergebener Transport warf eine unklassifizierte Ausnahme. |

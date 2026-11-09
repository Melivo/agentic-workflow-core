# TypeSafe-Bewertungs- und Integrationsvertrag

Diese bedingte Referenz gilt nur für ausdrücklich passende Design-, Integrations- oder Evaluationsaufträge. Sie aktiviert keine aktuelle Pflichtphase oder Laufzeit. Planstatus, Reviewurteil, Freigabe und Workflowstatus bleiben bei deterministischem Core-Code und ihren bestehenden Artefakten.

## Eignung aller Core-Skills

Semantische Bewertung kann nur variable Sprache unterstützen; sie ersetzt keine fachliche Verantwortung. Nichtnutzung ist ein valides Ergebnis.

| Skill | Sinnvolle Teilaufgabe oder begründete Nichtnutzung; unveränderte Verantwortung |
|---|---|
| core-architecture | Optional: semantischer Fit eines Vorschlags zu vorgegebenen Boundary-Fragen; Architekturentscheidung und Trade-offs bleiben beim Owner. |
| core-backend | Kein routinemäßiger Fit: API-Korrektheit und Autorisierung folgen überprüfbaren Verträgen und menschlicher Prüfung. |
| core-brainstorm | Optional: Gruppierung sprachlicher Nutzerabsichten; Richtungsentscheidung bleibt beim Nutzer. |
| core-database | Kein Fit für Schema, Integrität oder Migrationen; Datenmodellierung bleibt beim Fachskill. |
| core-debug | Optional: Zuordnung eines Fehlerberichts zu vorgegebenen Hypothesen; Reproduktion und Kausalnachweis bleiben beim Debugger. |
| core-devops | Kein Fit für Git-/Release-/CI-Fakten und Operationsfreigaben; diese sind deterministisch bzw. nutzergebunden. |
| core-docs | Optional: prüfen, ob eine Passage eine einzelne Behauptung semantisch stützt; Quellenverantwortung und Scope bleiben beim Curator. |
| core-execute | Optional: Claim-zu-Checkevidenz-Abgleich für einzelne Akzeptanzbehauptungen; Ausführung, Status und Autorisierung bleiben unersetzbar und nie modellentscheidbar. |
| core-frontend | Optional: Zuordnung sprachlicher UI-Anforderungen zu Kriterien; Implementierungs- und Accessibility-Verantwortung bleibt. |
| core-handoff | Optional: einzelne Promptbehauptung gegen Originalauftrag/Handoffquelle abgleichen; Zielauswahl und Freigabe bleiben unersetzbar. |
| core-init-mcps | Kein Fit: Providerbereitschaft ist Bestandsprüfung; Installation bleibt explizit freigabepflichtig. |
| core-init-project | Optional: semantischer Abgleich ausgewählter Dokumentationsanforderungen; kein Fit für Providerbereitschaft oder Einrichtungsfreigabe, und ein semantischer Hinweis beweist weder Fähigkeit noch Zustimmung; Setup-/Sync-Grenzen bleiben. |
| core-milestone | Optional: ein Etappenkriterium gegen konkrete Abschlussnachweise prüfen; Etappenauswahl, Abschlussentscheidung und Indexpflege bleiben beim Owner. |
| core-mobile | Optional: Zuordnung textlicher Plattformanforderungen; Lifecycle- und Accessibility-Prüfung bleibt. |
| core-plan | Potenzieller Hauptnutzen: Hinweise zu Skill-Fit, Kriterienabdeckung und Claim-Evidenz; Plan-/Scopeentscheidung bleibt beim Planer und Nutzer. |
| core-refactor | Kein routinemäßiger Fit: Verhaltensbewahrung muss durch Tests/Charakterisierung belegt werden. |
| core-repo-audit | Optional: semantische Gruppierung bereits belegter Findings; Fakten und Auditurteil bleiben begründet. |
| core-research | Optional: Relevanz oder Zitatstützung einer einzelnen Passage bewerten; Rechercheauswahl und Primärquellenprüfung bleiben beim Researcher. |
| core-review | Potenzieller Vergleichshinweis erst nach blind fixiertem Urteil; unabhängiges Review bleibt read-only. |
| core-shared | Kein Fit: Index ohne eigene fachliche Bewertung oder Workflowrolle. |
| core-tf-infra | Kein Fit für Infrastrukturfreigaben oder Terraform-Zustands-/Apply-Entscheidungen. |
| core-user2agent-instructions | Kein Fit: manuelle Weisungen und Autorität bleiben beim Nutzer. |

## Fragenprofile

Jev unterstützt atomare Noul-Aussagen (Wahrheitswahrscheinlichkeit) und Choice-Auswahl. Fragen sehen einander nicht; benötigte Fakten gehören in den jeweiligen State. Eine Choice wird mit einer Noul-Fitfrage gepaart, damit No-fit ausdrückbar bleibt. Wahrscheinlichkeiten sind keine Wahrheit oder Konfidenzgarantie.

| Profil | State und atomare Frage | Ergebnis und offene Fälle |
|---|---|---|
| skill_relevance | Plan-Ziel, einzelner Task und angebotene Skillverantwortungen. Choice: Welche angebotene Verantwortung ist zentral? Noul: Ist eine davon tatsächlich nötig? | Wahrscheinlichkeiten je Option plus Fit-Wahrscheinlichkeit. No-fit bei fehlendem Fit; Grenzbereich oder diffuse Verteilung = unsicher, nie automatischer Dispatch. |
| requirement_coverage | Ein Kriterium, Tasktext und konkrete Referenzstellen. Noul: Deckt diese Task das Kriterium ausdrücklich ab? Optionale Choice zu einer einzigen Lückenart separat. | Wahrscheinlichkeit plus Eingabereferenzen; fehlende Evidenz oder Grenzbereich bleibt unresolved. Keine Ja/Nein-Erzwingung. |
| claim_support | Einzelbehauptung, Originalquelle und bezeichnete Passage. Noul: Stützt diese Passage die Behauptung direkt? Choice: direkt gestützt / widerspricht / thematisch aber nicht belegend / keine passende Passage; separat Noul, ob überhaupt passende Passage existiert. | Wahrscheinlichkeiten je Relation und Fit; Modell erzeugt keine Belegreferenz. Fehlende Quelle oder Unsicherheit bleibt unresolved. |

Fragen sind neutral, konkret und einzeln; keine Sammelfrage „ist alles gut?“. IDs, Pfade, Hashes, Auswahl, Zählen, Zeit und Berechnung bleiben Code. Role, Autorisierung, Nutzerzustimmung, Versand, Statuswechsel und nächste Schritte entscheiden ausschließlich Menschen oder deterministischer Workflowcode. API-Fehler sind Fehler, niemals negative Antwort. Keine API-Requests in M01; Kosten, Datenfreigabe und Requestzahl bedürfen späterer separater Freigabe.

## Gemeinsame technische Daten- und Versionsgrenze

Ein späterer Evaluationsdatensatz ist getrennt von plan/v1, review/v1, task-result/v1 und Workflowstatus; er erweitert keines dieser Formate. Minimalfelder: pseudonyme Projektkennung, Planhash, Kriterien-ID, Core-/Modell-/Fragenversion, TypeSafe-Ergebnis mit Wahrscheinlichkeiten und eigenständiger Unsicherheitsklassifikation, API-Fehlerstatus, unabhängige Erstprüfungsreferenz/-hash sowie getrenntes Adjudikationslabel mit Evidenzreferenz, verantwortlicher Prüferrolle und Zeitstempel. TypeSafe-Unsicherheit, API-Fehler, Adjudikationslabel und Selektionsstatus sind verschiedene Typen/Zustände und dürfen nicht ineinander umgedeutet werden. Die Bewertung des Vergleichs, Kennzahlen und Studiendesign gehören ausschließlich in die [core-review-Evaluationsmethode](../../core-review/references/typesafe-evaluation.md).

Planhash wird über exakt dieselben unveränderten Planbytes gebildet, die beiden Prüfpfaden zugrunde liegen; Kodierung und Hashverfahren müssen im späteren Transportvertrag fixiert sein. Eine Event-ID identifiziert ein unveränderliches Ereignis anhand versionierter Identitätsfelder (mindestens Projektkennung, Planhash, Kriteriums-ID, Eventtyp und Revision); identische ID bei anderer Nutzlast ist Konflikt, nicht Update. Korrekturen sind append-only Revisionen mit Vorgänger-ID und explizitem supersedes-Verweis; alte Ereignisse und Originalreferenzen bleiben erhalten. Fehlende oder unzugängliche Originalquellen bleiben unresolved.

Späterer Transport liegt bei core-plan. TypeSafe-Auswertung, Transport und Speicherung sind getrennte Komponenten. Minimierung: keine Rohchats, Secrets, privaten Dokumente oder unnötigen Namen; nur erforderliche, ausdrücklich freigegebene Passagen und prüfbare Referenzen. Eine spätere Sammlung kann lokale SQLite auf Pi hinter geschütztem Receiver, idempotente Event-IDs und Offline-Queue nutzen; dies wird in M01 nicht angelegt, implementiert oder aktiviert. Ausfall ist weder Erfolg noch Qualitätsmangel.

## Quellen und Grenzen

Offizielle aktuelle Quellen: [primitives](https://docs.typesafe.ai/primitives.md), [advanced questions](https://docs.typesafe.ai/primitives/advanced.md), [models](https://docs.typesafe.ai/models.md), [model jaggedness](https://docs.typesafe.ai/model-jaggedness.md), [System One concepts](https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md). Jev liefert typed Wahrscheinlichkeiten; Unsicherheit ist nicht Adjudikation und eine Wahrscheinlichkeit keine Wahrheit. Modellverhalten ist versionsabhängig und jagged; Deployment-, Netzwerk- und Datenschutzpolitik bleiben separate Entscheidung. Keine empirische Core-Wirksamkeit ist belegt.

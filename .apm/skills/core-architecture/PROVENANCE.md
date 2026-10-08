# Herkunft der internen Designmethoden

## Quellen und Übernahmegrenze

- **SWE-Basis S00:** ausdrücklich bereitgestellte Benutzergrundsätze im bestätigten Plan `002-integrate-design-principles` und T01-Auftrag vom 2026-10-08. Eigene deutschsprachige Formulierung dieser Grundsätze; kein erfundener Dateipfad zur ursprünglichen Texteingabe.
- **Clairvoyance:** Cody Bromley, <https://clairvoyance.fyi>, lokale Authoring-Kopie `clairvoyance/skills/`, gelesen am 2026-10-08. Git-Revision `1854d2029728fcea02f9216e147e9a545cd665f4`; zusätzlich unten SHA-256 der tatsächlich verwendeten Dateien. Die Hashes identifizieren die gelesenen Bytes unabhängig von der Revision. Lizenz MIT, Copyright (c) 2026 Cody Bromley; vollständiger Hinweis in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- Gelesen und adaptiert wurden die 16 `SKILL.md` und der Pre-Mortem-Fallback. Andere optionale Quellreferenzen wurden nicht übernommen. Keine vollständige Kopie der Skill-Sammlung, keine fremden Agenten-/Runtime-Metadaten, keine externen Laufzeitpfade oder Installationsanforderungen.
- **Nicht übernommen:** privater `swe-quality-check` (UNLICENSED). Weder sein Text noch seine eigene Methodik bilden eine Quelle dieser Referenzen.
- **Authoring:** lokaler skill-creator für progressive Disclosure, Struktur und statische Validierung; kein zusätzlicher Paketbestandteil oder Laufzeitdependency. Statische Auswahlprüfung ist keine beobachtete Verhaltensevaluation.

Substantielle Clairvoyance-Methoden sind übersetzt, konsolidiert und an die bestätigten Grenzen angepasst. Das MIT-Copyright und der Erlaubnis-/Haftungstext werden mit diesen Adaptionen ausgeliefert; bloßes Umformulieren ersetzt diesen Lizenzhinweis nicht. Die Methoden aktivieren keine Workflows.

## Vollständiges Quellen → Methode → Auslöser → Ausschluss-Mapping

Ziele: [S00/Auswahl](references/design-baseline.md), [M01–M04](references/boundaries-and-abstractions.md), [M05–M06](references/interface-and-errors.md), [M07–M09](references/evolution-and-clarity.md), [M10](references/alternatives.md). Die IDs sind die kanonischen Methoden, keine neuen Skills. Jeder Methodeneintrag definiert Inputs/Evidenz, Methode, Ausnahmen/Stopgrenzen und Ergebnis/Abschluss.

| Quellskill | Disposition / kanonische Methode | Konkreter Auslöser | Absichtlicher Ausschluss / Anpassung |
|---|---|---|---|
| abstraction-quality | konsolidiert M03 | benachbarte Schichten wiederholen Modell | keine pauschale Decorator-/Adapter-Abwertung; notwendige Garantien nicht verstecken |
| code-evolution | konsolidiert M07, Dokumentationspflege M09 | Diff fügt Sonderfälle/dupliziertes Wissen hinzu | kein „Schulden jetzt reparieren“ außerhalb Task; gleiche Syntax nicht automatisch gemeinsame Regel |
| comments-docs | konsolidiert M09 | redundante, veraltete oder unvollständige Vertragsprosa | keine Pflichtkommentare je Feld, Kostenquote oder starre Comments-first-/Anti-TDD-Regel |
| complexity-recognition | konsolidiert M01 | überraschender Änderungsaufwand oder verborgenes notwendiges Wissen | keine Formel als Messbeweis, kein Hotspot-/Repositoryvollscan |
| deep-modules | konsolidiert M04 | Interfacekosten bei wenig verborgenem Nutzen | keine Längen-/Anzahlgrenzen, Globals oder pauschale Delegationsverbote |
| design-it-twice | adaptiert M10 | materielle Entscheidung mit plausiblen Alternativen | keine Agentensteuerung/Isolation; keine Quote oder Pflicht bei trivialen Entscheidungen |
| design-review | zerlegt in S00-Auswahl + M01–M09 | mehrere konkrete Struktur-/Vertragssignale | kein eigener Reviewworkflow, feste Phasenfolge oder abschließender Vollscan |
| diagnose | zerlegt in direkte S00-Auswahl; unklar → M01 | vages Symptom mit engem Änderungsbeispiel | keine externen Skill-Aufrufe, kein red-flags-Vollscan als Fallback |
| error-design | adaptiert M06 | viele Fehlerformen oder ignorierende Handler | keine universelle Reihenfolge, stilles Maskieren oder pauschales Crash-Rezept; Security/Datenintegrität begrenzen |
| general-vs-special | konsolidiert M05 | Aufrufer-Sonderwissen in allgemeinem Mechanismus | ein Verbraucher nicht automatisch falsch; öffentliche Datenverträge legitim; keine spekulative Generalisierung |
| information-hiding | konsolidiert M02 | verteilte interne Repräsentations-/Protokollannahmen | notwendige offene Verträge/fachliche Kopplung nicht als Leckage werten |
| module-boundaries | konsolidiert M02 | gekoppelte Änderungsgründe oder nur gemeinsam verständliche Teile | keine automatische Merge-/Split-Regel; dritte Abstraktion nur mit konkretem Nutzen |
| naming-obviousness | konsolidiert M08 | Name erzeugt falsches Modell oder verschleiert Verantwortung | kein Stilfinding/automatisches Split oder breiter Rename; lokale Namen zulässig |
| pull-complexity-down | konsolidiert M05; Tiefe M04 | wiederholtes Setup/unnötige Konfigurationslast | Konfiguration nicht pauschal Defekt; keine fremde Policy nach unten drücken |
| red-flags | zerlegt in S00-Auswahl und M01–M10 | konkretes Warnzeichen im betroffenen Bereich | kein obligatorischer 17-Punkte-Scan, Schwellenwerte oder Defekt aus Warnzeichen; gemeinsame Ursachen gruppieren |
| strategic-mindset | eingeschränkt M07; Alternativen M10 | belegtes wiederholtes Shortcut-/Änderungsmuster | 10–20%-Quote, TDD-Abwertung, Zero-Tolerance-Umbau und unbelegte Kosten-/Token-/Payoff-Prognosen ausgeschlossen |

### Erhalt der 17 red-flags-Signale ohne Scanpflicht

| Quellsignal | Kanonisches Ziel / Präzisierung |
|---|---|
| Shallow Module | M04: Kosten versus Nutzen, legitime kleine Module zulässig |
| Pass-Through Method | M03/M04: fehlender Boundary-Nutzen, nicht Delegation allein |
| Conjoined Methods | M02: versteckte gemeinsame Operation |
| Temporal Decomposition | M02: geteiltes Wissen statt zeitliche Reihenfolge prüfen |
| Information Leakage | M02: interne Annahme versus öffentlicher Vertrag |
| Overexposure | M05: unnötige Aufruferentscheidung versus notwendige Konfiguration |
| Repetition | M07: gemeinsames Wissen versus unabhängig gleiche Syntax |
| Special-General Mixture | M05/M07: Policy-Eigentümer prüfen |
| Comment Repeats Code | M09: fehlende Zusatzinformation |
| Implementation Documentation Contaminates Interface | M09/M03: austauschbare Interna versus erforderliche Garantie |
| Vague Name | M08: belegte Fehlinterpretation, nicht Stil |
| Hard to Pick Name | M08: Anlass zur Verantwortungsnachprüfung |
| Hard to Describe | M09: Vertragskomplexität prüfen, nicht Prosalänge bestrafen |
| Non-obvious Code | M08/M01: falsche Erwartung/verborgenes Wissen belegen |
| No Alternatives Considered | M10: nur bei materieller Entscheidung |
| Tactical Momentum | M07: Design-/Wissensdelta, keine Personenbewertung/Quote |
| Catch-and-Ignore | M06: sichere Recovery oder relevante Fehlerwirkung |

## Quellenfingerprints (SHA-256)

Pfade sind relativ zur Authoring-Quelle Clairvoyance, keine Laufzeitlinks.

| Datei | SHA-256 |
|---|---|
| skills/abstraction-quality/SKILL.md | `1220cea554717b86c11e0f4e90230d583ca9c5a6862533dc33b5a15d66a9a35e` |
| skills/code-evolution/SKILL.md | `9b62ae63519429ac53b37efe657d201c690ac4bb8875edd0158cf6372fd83011` |
| skills/comments-docs/SKILL.md | `3d21da1ce2aa05f283a4d689131fa03429b6ae1dd2544b1756ec1d1d0b4b0327` |
| skills/complexity-recognition/SKILL.md | `5d510d0f8ed32866bd860f8d4157cc7cd9b71171733f13541a58e74abd385980` |
| skills/deep-modules/SKILL.md | `de5ce281fa2cab26963dd072a64033a3a6f257ccede14a69688b8e6151e2710f` |
| skills/design-it-twice/SKILL.md | `6faca0433224200527e0ca2d718044acb031f01e72c9733a2b446189df626b1b` |
| skills/design-review/SKILL.md | `51ab3179fd45932f50f0c17f4d35f481c704148248ab99c9ee93d0087d79587d` |
| skills/diagnose/SKILL.md | `dc6770be3049533ef288589d6e9d3801e4d118ba569afe8cbf0212254b12332c` |
| skills/error-design/SKILL.md | `d3cd98be2b24bc5ce65c59a52354a6fe90bb5123804689039df5d394171cb830` |
| skills/general-vs-special/SKILL.md | `e4f67b141609bec197ad848cf9ebf3dcc44135e9b5efc12ed7c7b51f0a4ebcc9` |
| skills/information-hiding/SKILL.md | `bf32b262cda2254c6c0f8c8a9461ae628d8a64df8868d66872542d35f44357ce` |
| skills/module-boundaries/SKILL.md | `4f75da9380b408909d84ee0ae739cb3d2878a1a56d0324c86076c8fa2a6057bc` |
| skills/naming-obviousness/SKILL.md | `e6fccdf97b310f7ffeaa94242f4a5ecc6455d2b3f8a7ddbc685142e7a5b57518` |
| skills/pull-complexity-down/SKILL.md | `05aa31703795b092e50542d9669ff06c66ab8566841da17a25df9345df1290cb` |
| skills/red-flags/SKILL.md | `170e607b76098bf6abf04152df5a21e29b4f239ac200426a307c1717e100f508` |
| skills/strategic-mindset/SKILL.md | `8e522ef1287f081ead222804e376a606eca93bb90ed48a65a4be8332d25e1be6` |
| skills/design-it-twice/references/pre-mortem-fallback.md | `09bb79b1cf2844f66cf750afc0820b3bf642482f079069cf50aac1e0bfd4ac3c` |
| LICENSE | `84da69c63b21f3b3ff663bfe46f250b08cd4e2ba34dbda1764d8e93ab69c1e3c` |

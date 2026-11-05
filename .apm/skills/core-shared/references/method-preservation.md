# Erhaltungswege für übernommene Methoden

## Zweck und Geltung

Dieser Index ist ein bedingt geladener Referenzindex. Er zeigt, wo eine übernommene Methode fachlich bereits im Core-Verfahren steht, welche Teile bewusst nicht übernommen wurden und welche Rechtegrenze gilt. Er ist keine Fachmethodensammlung, kein Auswahlcontroller und keine Autorität über Workflow, Scope, Freigaben oder Artefakte. Die Methodik steht jeweils im verlinkten Core-Verfahren.

Lade diese Datei nur, wenn ein bestätigter Auftrag eine übernommene Methode einordnet, ändert, entfernt oder als Autoren- beziehungsweise Evaluationshilfe nutzt.

## Geltungsregeln

- Die Methodik gehört dem verlinkten `core-*`-Verfahren. Dieser Index wiederholt keine Schritte daraus.
- Fremde Steuerung wird nicht übernommen: eigene Controller, Dispatcher, Modell- oder Anbieterpflichten, Statushaltung, automatische Commits, Branches, PRs, Installationen oder Freigaben.
- Unbekannte oder nicht geklärte Rechte erlauben weder Kopie, Übersetzung, Paraphrase noch Ersatzimplementierung. Eine Core-Formulierung entsteht nur aus vorhandener Core-Deckung.
- Erhaltene Originale bleiben unverändert an ihrem Herkunftsort. Ihre Ressourcen (Vorlagen, Helfer, Begleitdateien) werden nicht in Core übernommen.
- Originalflags zur manuellen Aufrufbeschränkung werden respektiert. Core ruft übernommene Originale nicht implizit auf.
- Dieser Index entfernt, komponiert oder verschiebt nichts. Ressourcenänderung, Entfernung und Zusammenlegung brauchen eine eigene ausdrückliche Freigabe.
- Die portable Fassung von `skill-creator` ersetzt nicht die Claude-synchronisierte Fassung mit eigenem Evaluationswerkzeug.

## Core-Verfahren nach Komponente

Die Zuordnung belegt nur die genannte fachliche Abdeckung durch Textstellen. Sie belegt kein Modellverhalten.

| Komponente | Core-Verfahren | Erhalten beim Original, bewusst nicht übernommen |
| --- | --- | --- |
| architect | [Proportionale Methode](../../core-architecture/SKILL.md#proportionale-methode); [M10 Alternativenvergleich](../../core-architecture/references/alternatives.md#m10--alternativenvergleich) | Usage-first, Wissensgrenzen und Alternativen; Modellzwang, Dispatch und automatische Umsetzung nicht übernommen |
| codebase-design | [Situative Designmethoden](../../core-architecture/SKILL.md#situative-designmethoden); [M01 bis M04 Grenzen und Abstraktionen](../../core-architecture/references/boundaries-and-abstractions.md); [M10](../../core-architecture/references/alternatives.md#m10--alternativenvergleich) | Vertiefungs- und Alternativenvorlagen bleiben beim Original |
| improve-codebase-architecture | [Workflow Repositoryanalyse und Entscheidung](../../core-architecture/SKILL.md#workflow-repositoryanalyse-und-entscheidung); [Routing entdeckter Arbeit](../../core-architecture/SKILL.md#routing-entdeckter-arbeit) | Berichtsvorlage bleibt beim Original; CDN-Pflichtberichte und Testlöschung nicht übernommen |
| diagnosing-bugs | [Reproduzieren](../../core-debug/SKILL.md#1-reproduzieren); [Ursache diagnostizieren](../../core-debug/SKILL.md#2-ursache-diagnostizieren); [Regressionsevidenz](../../core-debug/SKILL.md#4-regressionsevidenz-erzeugen) | Schleifenhelfer bleibt beim Original |
| figure-it-out | [Ursache diagnostizieren](../../core-debug/SKILL.md#2-ursache-diagnostizieren); [Pflichtcheckvertrag](verification.md#pflichtcheckvertrag) | Unklares Ergebnis gilt als inconclusive, nicht als Pass; keine parallele Steuerung oder Commitkontrolle |
| tdd | [Regressionsevidenz](../../core-debug/SKILL.md#4-regressionsevidenz-erzeugen); [Unverhandelbare Trennung](../../core-refactor/SKILL.md#unverhandelbare-trennung) | Characterization Tests bleiben getrennt von Bugfix-Tests |
| interrogate | [Findings formulieren](../../core-review/SKILL.md#4-findings-formulieren); [Reproduzieren](../../core-debug/SKILL.md#1-reproduzieren) | Reprokommando und Nullbefund-Ergebnis; kein Laufzeit-Repro als Pflicht |
| code-review | [Planreview-Modus](../../core-review/SKILL.md#planreview-modus); [Risiken ableiten](../../core-review/SKILL.md#2-risiken-aus-der-anderung-ableiten); [Evidenz erheben](../../core-review/SKILL.md#3-automatisierte-und-manuelle-evidenz-erheben) | Standards-/Anforderungslinse; kein eigener Controller und kein kopierter Smell-Katalog |
| chief-of-staff | [Runzustand](artifact-contract.md#runzustand); [Serialisiert integrieren](../../core-execute/SKILL.md#5-serialisiert-integrieren-und-verifizieren) | Datierte Quellenbelege; keine Wiki-Statushoheit und keine ungefragten Umfeldmutationen |
| implement-spec | [Plan und Drift validieren](../../core-execute/SKILL.md#1-plan-und-drift-validieren); [Tasks schedulen](../../core-execute/SKILL.md#3-tasks-schedulen-und-dispatchen) | Eigener Dispatch, Branch, Reset, Merge, PR und Ticketablauf nicht übernommen |
| arena | [Tasks schedulen](../../core-execute/SKILL.md#3-tasks-schedulen-und-dispatchen); [Taskresultat prüfen](../../core-execute/SKILL.md#4-taskresultat-prufen) | Kriterien und isolierte Briefs nur innerhalb Execute; eigener Dispatcher, Modellfamilienpflicht und Statushoheit nicht übernommen |
| swarm | [Statisch validieren](../../core-plan/SKILL.md#5-statisch-validieren-und-bestatigen); [Tasks schedulen](../../core-execute/SKILL.md#3-tasks-schedulen-und-dispatchen) | Nur Abdeckungshinweis innerhalb Execute; keine parallele Orchestrierung |
| wayfinder | [Entscheidungsübergabe](../../core-brainstorm/SKILL.md#entscheidungsubergabe); [Auftrag rahmen](../../core-plan/SKILL.md#1-auftrag-rahmen) | Trennung von Entscheidungsfrage und Umsetzungsschnitt; keine eigene Statushoheit |
| grilling | [Brainstorm-Workflow](../../core-brainstorm/SKILL.md#workflow) (Entscheidungsrahmen und Bestätigung) | Nur Abhängigkeiten und Nutzerentscheidungen gegenüber belegbaren Fakten; keine Ausführung des Originalworkflows |
| to-spec | [Auftrag rahmen](../../core-plan/SKILL.md#1-auftrag-rahmen) | Problem, Testgrenzen, Entscheidungen und Nichtziele; Trackerpublikation nicht übernommen |
| to-tickets | [Taskgraph zerlegen](../../core-plan/SKILL.md#4-einen-taskgraphen-zerlegen) | Vertikale prüfbare Schnitte und echte Blockierkanten; der Core-Plan bleibt einzige Graphautorität |
| how | [Erforderliche Eingaben und begrenzter Ablauf](../../core-research/SKILL.md#erforderliche-eingaben-und-begrenzter-ablauf); [Dokumentationspflicht](../../core-research/SKILL.md#dokumentationspflicht) | Erklärvorlagen bleiben beim Original; nur Quellenarbeit, keine Fremdsteuerung |
| why | [Evidenzklassen und Quellenhierarchie](../../core-research/SKILL.md#evidenzklassen-und-quellenhierarchie) | Historische Playbooks bleiben beim Original; Belegklassen und Widerspruchsprüfung über Core |
| research | [Evidenzklassen und Quellenhierarchie](../../core-research/SKILL.md#evidenzklassen-und-quellenhierarchie); [Verhaltensfälle](../../core-research/SKILL.md#verhaltensfalle-recherchieren-oder-stoppen) | Begrenzte Read-only-Recherche; kein Backgrounddispatch und kein Autorschreiben |
| deep-research | [Evidenzklassen und Quellenhierarchie](../../core-research/SKILL.md#evidenzklassen-und-quellenhierarchie); [Dokumentationspflicht](../../core-research/SKILL.md#dokumentationspflicht) | Mehrquellen-Synthese; kein Subagent-Controller, Dispatch allein durch Execute |
| recall | [Ergebnis und Wiederaufnahme](../../core-handoff/SKILL.md#ergebnis-und-wiederaufnahme); [Abbruch, Blockade und Wiederaufnahme](workflow-contract.md#abbruch-blockade-und-wiederaufnahme) | Zeit- und Workspacegrenze; Originalartefakte bleiben Resumequelle, kein erneutes Mining |
| blast-radius | [Entscheidende Sicherheitsannahmen](workflow-contract.md#zielbindung-und-funktionaler-scope) | Teilweise: Sicherheitsannahme, indirekte Folgen und Evidenzstärke sind im Core-Vertrag. Die Versionierungsfrage ist dort nicht eigens genannt und bleibt beim Original |
| show-me-your-work | [Taskresultat prüfen](../../core-execute/SKILL.md#4-taskresultat-prufen); [Pflichtcheckvertrag](verification.md#pflichtcheckvertrag) | Entscheidung, Grund, Beleg und Ergebnis in vorhandenen Core-Artefakten; Vorlage und Helfer bleiben beim Original |

## Bedingt nutzbare Autoren- und Pflegemethoden

Diese Methoden sind nur bei ausdrücklichem Autoren- oder Pflegeauftrag einzusetzen. Sie erzeugen weder eine eigene Evaluationspipeline noch Dispatch oder Statusablage.

| Komponente | Berührungspunkt in Core | Grenze |
| --- | --- | --- |
| automate-me | [Autorisierung und Rückfragen](workflow-contract.md#autorisierung-und-ruckfragen) | Wiederholte Präferenzsignale über ein Zeitfenster, keine Dauerregel aus einer Einzelaussage, Referenz statt Kopie. Mining-Subagenten, Modellkette und Pflicht-Worktree/PR nicht übernommen |
| reflect | [Autorisierung und Rückfragen](workflow-contract.md#autorisierung-und-ruckfragen) | Belegte dauerhafte Lernpunkte mit Vorschlag, Verwerfung oder mechanischer Maßnahme; kein Selbstdispatch |
| correct | [Ähnliche Muster scannen](../../core-debug/SKILL.md#5-ahnliche-muster-scannen) | Wiederholte belegte Fehlerklassen und Gegenprobe; kein fremder Controller |
| maintain-verification-skill | [Pflichtcheckvertrag](verification.md#pflichtcheckvertrag) | Indexpflege nur im Skillordner, nie Produktcode; ehrliches clean oder blocked |
| principle-build-the-lever | [Kleinste Aktion wählen](../../core-devops/SKILL.md) (Workflow Schritt 4) | Wiederholbare deterministische Werkzeuge nur, wenn das Profil sie trägt; Lever als Vorschlag, keine Diffpflicht |
| principle-sequence-verifiable-units | [Taskgraph zerlegen](../../core-plan/SKILL.md#4-einen-taskgraphen-zerlegen); [Kleine Transformationen](../../core-refactor/SKILL.md#4-kleine-transformationen-ausfuhren) | Verifizierbare Einheiten, before/after-Bracket, failing-test-first; der Delivery-Rahmen bleibt Auftragssache |
| skill-creator (Claude-synchronisierte Fassung) | [Bedarfsabhängige Messvergleiche](verification.md#bedarfsabhangige-messvergleiche) | Treatment-/Baseline-Vergleich, verblindeter Vergleich, Assertion-Kritik nur als Autorenhilfe; Original vollständig erhalten, nicht durch die portable Fassung ersetzt |

## Original ohne Core-Fachmethode

Diese Fähigkeiten bleiben beim Original. Core übernimmt keine Produktlogik, Installation oder Modellbefund-Automatik.

- prototype: Logik- und UI-Fragen trennen, isolierte Zustandsdemo und echte Varianten. Produktübernahme und Installation brauchen eine getrennte Freigabe.
- statechart: TLA+-Modellprüfung mit Gegenbeispielpfaden und Replay. Ein Modellbefund ist kein Codebug; Werkzeug und Testkorpus bleiben beim Original.

## Referenzen ohne Core-Import

Diese Komponenten werden nicht in Core übernommen. Originale bleiben unverändert; eine spätere Referenzbereinigung ist eine eigene Entscheidung.

- design: Routing zum vorhandenen banner-design-Original, ohne Pflichtskill und ohne allgemeines Core-Designmandat.
- banner-design: Einstieg und Produktionsanleitung bleiben eigenständig; nur die bereits vorhandene Ressourcenreferenz wird nicht verdoppelt.
- writing-shape: Einstieg zum bestehenden writing-beats-Modus; keine Textverschmelzung, kein Beat-Ersatz.
- writing-beats: vollständiger Beatmodus bleibt eigenständig; keine Textverschmelzung und keine Entfernung.

## Bewusste Nichtübernahmen

Diese Einträge sind nicht Teil von Core. Das Löschen oder Entfernen der Originale ist keine Folge dieses Indexes.

- grill-me: Der Alias-Einstieg wird nicht übernommen. Die Methodik steht über grilling beziehungsweise core-brainstorm; grilling bleibt Original.
- implement: Eigene Commit- und Autofreigabelogik wird nicht übernommen. Spezifikationsausführung und Verifikation liegen bei [core-execute](../../core-execute/SKILL.md).
- principle-never-block-on-the-human: Das Gegenprinzip zur Rückfrage wird nicht übernommen. Die Freigabegrenze gilt unverändert nach [Autorisierung und Rückfragen](workflow-contract.md#autorisierung-und-ruckfragen).

## Rechte- und Herkunftsgrenzen

- Kandidatenprüfung ohne gefundenen eigenständigen Lizenztext: nur bestehende Core-Deckung, keine Quelltextübernahme.
- Unbekannte Rechte oder unbekannter Owner: kein Importrecht; keine Kopie, Paraphrase, Ersatzimplementierung oder behauptete Eigenautorschaft.
- MIT-Angabe im Frontmatter (design, banner-design): Original nur referenzieren; bei jeder späteren Kopie gelten Lizenz und Attribution.
- Apache-2.0-Lizenzdatei der Claude-synchronisierten skill-creator-Fassung: Lizenz und vorhandene Hinweise bleiben beim Original.

Exakte Quellpfade und Prüfsummen werden nicht in ausgelieferten Core-Quellen geführt.

## Grenzen

- Die Zuordnung zeigt Textstellen und Abdeckung, nicht Modellverhalten oder Laufzeitauflösung.
- Globale Installationen, Hardlinks und Fremdnutzung externer Kopien sind nicht Teil dieses Indexes.

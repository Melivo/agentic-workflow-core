# TypeSafe-Planbewertung: unabhängige Evaluation

Nur für ausdrücklich beauftragtes Design, Integration oder Evaluation von TypeSafe-Planhinweisen laden. Dies ist kein aktiver Review-Workflow, Runner oder Statusspeicher. Der [gemeinsame TypeSafe-Vertrag](../../core-shared/references/typesafe-contract.md) besitzt Eignung, Fragenprofile und den technischen Daten-/Versionsvertrag. Diese Referenz besitzt ausschließlich den Bewertungsablauf, Metriken, Studiendesign, konservative Zielwerte und Offline-Fälle.

## Blindes Review und Adjudikation

1. core-plan bindet Modellbewertung und unabhängige Prüfung an denselben unveränderten Planhash und dieselben vorab festgelegten Kriterien. Ein TypeSafe-Ergebnis ist kein Planurteil.
2. Reviewer sieht die Planfassung ohne Modellresultat, fixiert Ersturteil, Scope, Begründung und Quellenreferenzen unveränderlich.
3. Erst danach sieht derselbe Reviewer das Modellresultat und gleicht es mit Originalplan und Evidenz ab. Seine spätere Adjudikation bleibt ein separates Ereignis und überschreibt das Ersturteil nicht.
4. Adjudikationslabel ist je Kriterium genau eines von: material_defect, no_material_defect, unresolved. Unresolved ist keine negative oder positive Wahrheit. Reviewer-Ersturteil (defect_found / no_defect_found) bleibt davon getrennt; TypeSafe-Ergebnis (alert / unflagged / no_fit / uncertain / api_error / selection_excluded) ist ein drittes, unabhängiges Feld. Insbesondere werden uncertain und api_error nie als unflagged gewertet.
5. „TypeSafe-Miss“ bezeichnet jedes adjudizierte material_defect-Kriterium, das TypeSafe als unflagged bewertet hat, unabhängig davon, wer den Defekt zuerst entdeckt hat. „Reviewer-Miss“ bezeichnet separat jedes material_defect-Kriterium, das der unabhängige Reviewer in seinem fixierten Ersturteil nicht gefunden hat. Fehler des Modells und Fehler des Reviewers sind nicht austauschbar.
6. Abweichende oder unbelegte Bewertungen bleiben offen; keine Mehrheitsentscheidung. Bei materieller offener Entscheidung Nutzerentscheidung einholen. Promptbehauptung von Blindheit beweist keine Isolation; ohne technische Evidenz zu Eingabe-/Berechtigungstrennung und Reihenfolge ist die unabhängige Vergleichsaussage nicht nachgewiesen.

## Metriken und Nenner

Für jede Quote vorab Population, Ein- und Ausschlussregeln, Zähler und Nenner festschreiben. Eine Kriterienbeobachtung ist nur auswertbar, wenn TypeSafe-Ausgabe und unabhängige Adjudikation für das vorab definierte Kriterium vorliegen.

- **TypeSafe-Kriterien-Miss-Rate**: Anzahl aller adjudizierten material_defect-Kriterien mit TypeSafe-Status unflagged / Anzahl aller adjudizierten Kriterien mit TypeSafe-Status unflagged. Zähler unabhängig vom Reviewer-Ersturteil bestimmen.
- **Reviewer-Miss-Rate**: Anzahl aller adjudizierten material_defect-Kriterien mit Reviewer-Ersturteil no_defect_found / Anzahl aller adjudizierten material_defect-Kriterien mit entscheidbarem Reviewer-Ersturteil. Separat berichten; sie bewertet Reviewerleistung, nicht Modellmisses.
- **Defect recall**: als alert markierte adjudizierte material_defect-Kriterien / alle adjudizierten material_defect-Kriterien mit entscheidbarem TypeSafe-Ergebnis (alert oder unflagged). Unsicherheiten und API-Fehler separat halten.
- **False-alert rate**: alert markierte no_material_defect-Kriterien / alle adjudizierten no_material_defect-Kriterien mit TypeSafe-Status alert oder unflagged.
- **False-alert-Planrate**: unabhängig adjudizierte eligible Plancluster mit mindestens einem alert auf no_material_defect / alle vollständig adjudizierten eligible Plancluster mit TypeSafe-Status alert oder unflagged für den gesamten vorab festgelegten Kriteriumsumfang. Nur diese Clusterquote nutzt dieselbe Cluster-/Konfidenzmethodik wie die primäre Plan-Miss-Rate.
- **Zusatzbefunde**: belegte zusätzliche materielle Findings pro Plan und deren Präzision mit explizitem Nenner; niemals bloße Anzahl als Gütequote ausgeben.

Bei Nullnenner ist eine Quote nicht bestimmbar, nicht null. Unresolved, APIerror, Unsicherheit und Selektion werden nie in einen gemeinsamen Status gemischt. Coverage-Quoten erhalten eigene Nenner: API-Fehler / alle für TypeSafe vorgesehenen Kriterien; no_fit / alle vorab eligible Kriterien; uncertain / alle erfolgreich beantworteten Kriterien; unresolved / alle zur Adjudikation eingereichten Kriterien; Selektionsausschlüsse / alle vorab eligible Kriterien. Zusätzlich absoluter Zähler, Nenner und Grund berichten. Fehlende/geblockte Daten bleiben sichtbar, statt den Evaluationsnenner still zu verkleinern.

### Vier Kombinationsfälle und Handrechnung

Für ein adjudiziertes material_defect-Kriterium gibt es vier Kombinationen:

| TypeSafe | Reviewer-Ersturteil | Zählung |
| --- | --- | --- |
| alert | defect_found | kein TypeSafe-Miss, kein Reviewer-Miss |
| alert | no_defect_found | kein TypeSafe-Miss, Reviewer-Miss |
| unflagged | defect_found | TypeSafe-Miss, kein Reviewer-Miss |
| unflagged | no_defect_found | TypeSafe-Miss und Reviewer-Miss |

Gegenbeispiel: 100 adjudizierte unflagged Kriterien, darin zehn materielle Defekte, die der Reviewer alle findet. TypeSafe-Misses = 10/100; Reviewer-Misses = 0/10 materielle Defekte (und 0/100 unflagged Kriterien, falls diese ergänzende Reviewerquote ausdrücklich gezeigt wird). Der erste Nenner bewertet den Modellmiss, der zweite die Reviewerfehler unter Defekten. Er darf nicht als 0/100 Modellmiss interpretiert werden. Offline-Rechnung muss genau diese Werte reproduzieren. Für alle vier Zellen ebenso gilt: nicht vorhandene Zellen sind null Ereignisse nur bei positivem Nenner; Nullnenner bedeutet nicht bestimmbar.

## Studiendesign und Entscheidungsziele

Entwicklungs- und Held-out-Evaluation nach unabhängiger Planfamilie oder Projekt trennen, nie nach Kriterienzeile desselben Plans. Wiederholte Pläne eines Projekts/Planfamilie bilden einen Cluster. Kriterienmetriken sind beschreibend und korreliert; 300 Kriterien aus wenigen Plänen sind keine 300 unabhängigen Belege.

Primäre Inferenz erfolgt auf unabhängiger Planfamilie/Projekt: Ein eligible Plancluster ist „TypeSafe-unauffällig“ nur wenn Bewertung und Adjudikation vollständig vorliegen, alle eligible Kriterien Status alert oder unflagged haben und keines als alert markiert ist. no_fit, uncertain, api_error, selection_excluded oder unresolved machen den Cluster für die primäre Inferenz unvollständig; ihre Coverage wird separat berichtet. Primäres Ereignis: mindestens ein adjudiziertes materielles Defektkriterium in diesem unauffälligen Plancluster, unabhängig vom Reviewer-Ersturteil. Primäre Miss-Wahrscheinlichkeit = solche Ereignisse / alle unabhängig adjudizierten TypeSafe-unauffälligen Plancluster. Plancluster mit unresolved Kriterien, API-Fehlern, fehlender Prüfung oder Selektionsausschluss werden nicht still als fehlerfrei behandelt; ihre Deckungsquoten erscheinen separat. Kriterienebenen-Miss-Rate bleibt deskriptiv.

Vor Datensicht Mindestumfang und Fehlergrenzen fixieren. Konservatives internes Designziel: mindestens 150 voneinander unabhängige held-out Planfamilien/Projekte mit vollständiger eligible Prüfung und Adjudikation, außerdem mindestens 300 Kriterienbeobachtungen insgesamt als deskriptive Datenbasis. Mehrere Pläne aus demselben Projekt/Familiencluster erhöhen nicht die Zahl unabhängiger Einheiten. Wenn 150 unabhängige Cluster nicht belegbar sind, keine inferenzielle Zielerreichung behaupten.

Für die primäre Ereignisquote je nachweislich unabhängigem Cluster wird ein einseitiges exaktes 95%-Clopper-Pearson-Intervall berichtet. Interne Bewertungsziele sind obere Konfidenzgrenze höchstens 2% für primäre TypeSafe-Miss-Wahrscheinlichkeit und höchstens 10% für die separat definierte False-Alert-Planrate. Ein Ziel ist nur erreicht, wenn die vorab bestimmte Population und der Nenner vollständig vorliegen und die Obergrenze eingehalten wird; bei kleinen Stichproben oder zu breitem Intervall lautet das Ergebnis unzureichende Evidenz. Kriterienebenenwerte erhalten keine unabhängige Binomial-Sicherheitsbehauptung. Strata nach Risiko, Planart und Version werden ausgewiesen; Untergruppen ohne eigene ausreichende unabhängige Cluster bleiben deskriptiv. Versionsdrift, Selektionsbias oder Unabhängigkeitszweifel verhindern Zielerreichung.

Diese konservativen Werte sind interne Bewertungsmaßstäbe, niemals automatische Freigabe-, Dispatch-, Schwellenanpassungs- oder Reviewverkürzungsregeln. Sie belegen keine empirische Wirksamkeit und genehmigen kein Geldbudget.

## Berichte und Offline-Fallbeschreibungen

Monatliche Berichte sind später read-only. Dreimonatsauswertung zählt ab dokumentiertem Pilotstart nach später freigegebener Releaseinstallation und braucht zugleich ausreichende Fallzahlen, vollständige Coverage und Datenqualität; Kalenderzeit allein genügt nicht. Kein automatisches OpenChamber-Tuning oder Statuswechsel.

Offline-Fälle, ohne API-Requests:

- Positiv: Kriterium verlangt Tastaturnavigation und Task nennt Fokusführung sowie Testnachweis; ein konkreter belegter Hinweis ist prüfbar.
- Negativ: allgemeiner Begriff „Sicherheit“ ohne konkretes Berechtigungs-/Authentifizierungskriterium; thematische Nähe ist kein Claim-Beleg.
- No-fit: exakter Pfad-/Versionsabgleich; deterministischer Code genügt.
- Unresolved: Originalquelle des Kriteriums ist nicht erreichbar; kein definitives Label.
- Independence: Reviewer fixiert Urteil ohne Modellresultat; eine Textanweisung allein beweist technische Isolation nicht.

## Offizielle Dokumentation

Verwendete aktuelle offizielle Quellen: [primitives](https://docs.typesafe.ai/primitives.md), [advanced questions](https://docs.typesafe.ai/primitives/advanced.md), [models](https://docs.typesafe.ai/models.md), [model jaggedness](https://docs.typesafe.ai/model-jaggedness.md), [System One concepts/how to build](https://docs.typesafe.ai/concepts/how-to-build-with-system-one.md), [skill suggestion cookbook](https://docs.typesafe.ai/cookbooks/skill_suggestion.md). Keine fremde Prosa oder Code übernommen. Jaggedness und Modellresultate sind versionsabhängig; diese Quellen ersetzen keine lokale, unabhängige Evaluation.

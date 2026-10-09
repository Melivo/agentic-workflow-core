# Goal-Prompt

Ersetze vor Ausgabe alle Platzhalter anhand geprüfter Artefakte. Nenne Ziel-ID und exakte `goal.md`, `index.yaml`, Definitionspfad samt Milestone-ID/Version, bestätigten Planpfad sowie vorhandene Run-, Review- und Tasknachweispfade. IDs, Inhalte und Namen müssen übereinstimmen. Gib den Text kopierbar aus. Der Prompt ist ein wiederholt injizierbarer Zielhinweis, kein Sitzungsstart, Statusspeicher oder zusätzliche Autorisierung. Er aktiviert keinen Plan; Ausführung beginnt erst nach Planbestätigung und ausdrücklicher Execute-Autorisierung.

```text
Arbeite ausschließlich an der ausdrücklich freigegebenen Etappe <Milestone-ID> Version <Version> für Ziel <Goal-ID>.
Zieldatei: <exakter goal.md-Pfad>
Index: <exakter index.yaml-Pfad>
Definitionsdatei: <exakter Definitionspfad>
Bestätigter Plan: <exakter Planpfad für diese ID-Version>
Run und Nachweise: <exakte state.yaml-, review.yaml- und relevante task-result/v1-Pfade; „noch nicht vorhanden“ nur vor Runstart>

Prüfe Auswahl und aktuelle Freigabe im Index, IDs/Pfade/Inhalte sowie Planbindung neu. Halte gemeinsame bestätigte Entscheidungen im Ziel und die Scopegrenze/Kriterien der gepinnten Definition ein. Abschlusskriterien: <Kriterien-IDs und Kurztexte>.

Gib vor der Arbeit eine kurze Orientierung mit Ziel-ID, Etappen-ID/Version, exakten Referenzen, gewünschtem Ergebnis, bestätigtem Plan und nächstem zulässigen Schritt. Leite den Zustand nur aus Ziel, Index, Definition, Plan, Run, Review und Originalnachweisen ab. Resume und Review-Reparatur behalten dieselbe Run-ID.

Bei fehlendem Designbeleg, Drift, Versions-/ID-/Pfadwiderspruch, nicht ausgewählter oder veralteter Definition/Plan, fehlendem Pflichtnachweis oder bereits abgeschlossenem Milestone: stoppe ohne Fortsetzung oder Neudispatch und nenne den zuständigen Eigentümer (`core-milestone` zur Auswahl/Abschlussprüfung, `core-plan` für Ersatzplanung). Ein Run-pass ist kein Milestone-Abschluss. Nur core-milestone kann nach zusätzlicher Kriterienprüfung den Abschluss im Index verknüpfen. Veraltete Prompts reaktivieren keine Version. Folgeetappen benötigen ausdrückliche Freigabe; Gesamtabschluss erfordert zusätzlich die goal_acceptance-Nachweise.

Ist die Etappe abgeschlossen, starte nichts Weiteres. Übergib nur nach autorisiertem Handoff mit exakten Ziel-, Index-, Definitions-, Plan-, Run-, Review- und Evidenzpfaden. Ist das Gesamtziel belegt abgeschlossen, gib den Gesamtabschluss mit Originalnachweisen aus. Keine automatische Folgefreigabe, kein Folgedispatch, keine automatische Freigabe. Eine Wiederholung dieses Prompts hebt Abschluss, Blocker oder Freigabegrenzen nicht auf.
```

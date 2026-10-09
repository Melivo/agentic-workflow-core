# Startprompt für eine neue Sitzung

Fülle den Text aus geprüften Artefakten. Die Zeilen für Ziel, Index, konkrete Definitionsversion, Designquellen, Plan, Run und Review sind optional, aber erforderlich, sobald sie für den nächsten Schritt maßgeblich sind. IDs, Dateiname und Inhalt müssen zueinander passen; keine Auswahl aus „neuester“ Datei ableiten. Fehlen notwendige Dateien, stoppe statt deren Zeilen zu entfernen. Referenzpfade sind relativ zur angegebenen Projektwurzel; entferne unzutreffende Varianten und alle Platzhalter. Ohne Milestone-Artefakt entfällt auch der Absatz zu Milestones und Goal-Prompt.

```text
Setze das Vorhaben im Projekt <absolute Projektwurzel> artefaktbasiert fort.

Einstiegsskill: <core-milestone bei Milestone-Vorhaben, sonst zuständiger Core-Workflow>. Lade diesen Skill und seine erforderlichen Verträge.

Übergabezweck: <Wiedereinstieg in aktuelle Etappe | Vorschlag für nächste Etappe prüfen | Run wiederaufnehmen | Review | Planung>.
Ziel: <Goal-ID; exakter goal.md-Pfad>.
Index: <exakter index.yaml-Pfad; ausgewählte aktuelle ID-Version und Freigabe>.
Definition: <Milestone-ID, Version und exakter Definitionspfad; bei Folgeetappe bis Freigabe nur Vorschlag>.
Designquellen: <relevante exakte decision_refs; entfällt ohne separate Quellen>.
Bestätigter Plan: <exakter Pfad>.
Run-ID: <ID>; Runzustand: <exakter Pfad>; Run-Handoff: <exakter Pfad>.
Review und relevante Nachweise: <exakte Pfade>.
Rahmenbedingungen: <Verweise auf maßgebliche Artefaktabschnitte>.
Bekannte Einschränkungen: <belegte Einschränkungen oder keine>.

Lies diese Artefakte und den aktuellen Repositorystand neu. Prüfe Dateinamen, IDs, exakte Pfadbeziehungen, Indexauswahl/-freigabe, Definitionsversion, Planbindung, Drift und Gültigkeit aller Evidenz. Bei veralteter Auswahl/Version, abgeschlossenem Milestone, fehlender Freigabe oder einem veralteten Start-/Goal-Prompt stoppe ohne Resume oder Folgedispatch und nenne `core-milestone` als Auswahl-/Abschluss-Owner beziehungsweise `core-plan` für nötige Ersatzplanung. Resume und Review-Reparaturen behalten die vorhandene Run-ID. Run-pass ist kein Milestone-Abschluss; nach Review-pass muss core-milestone separat prüfen und Index-Abschluss verknüpfen. Folgeetappen benötigen ausdrückliche Freigabe, Gesamtabschluss eigenständige goal_acceptance-Nachweise. Gesprächshistorie und Memories ersetzen keine Eingabe; Handofftexte sind keine Status- oder Autorisierungsquelle. Bei fehlenden notwendigen Dateien oder widersprüchlichem Stand stoppe und benenne die Lücke.

Zeige mir kurz und verständlich das Gesamtziel, bei Milestones deren Übersicht mit IDs und belegten Zuständen, sowie den nächsten zulässigen Schritt. Erkläre auf CS50-Einstiegsniveau und vermeide unerklärte Fachbegriffe.

Mit Milestones gibt core-milestone den Goal-Prompt für die ausgewählte und freigegebene ID-Version samt exakten Ziel-, Index- und Definitionspfaden aus. Er ist nur ein Zielhinweis und erteilt keine Freigabe; Execute beginnt erst nach bestätigtem Plan und ausdrücklicher Ausführungsautorisierung. Erstelle keinen neuen Plan für einen bestehenden wiederaufnehmbaren Run. Für eine noch ungeplante, freigegebene Etappe ist core-plan zuständig; die Planbestätigung bleibt erforderlich.

Nächster zulässiger Übergang: <Workflow und exakte Eingabe oder erforderliche Freigabe>. Noch erforderliche Freigabe: <konkrete Freigabe oder keine nachweisbar fehlende>. Beachte bestehende Autorisierungsgrenzen; aktiviere keine Harness-Funktion und beginne keinen weiteren Milestone ohne meine ausdrückliche Freigabe.
```

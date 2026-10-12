# Git, History und Ownership

Lade dies für Branches, Commits, Pull Requests, Rebase/Merge, Tags oder Release-Baselines. Git verändert Index, lokale History und ggf. Remote-Refs; prüfe Status und Scope unmittelbar vor jeder autorisierten Operation.

## Vor der Aktion

- Lies aktuellen Branch, Upstream, Ahead/Behind-Stand, gestagte/ungestagte/unversionierte Dateien, Konflikte und passende Historie. Gezielte Git-CLI-Beobachtungen: git status --short --branch, git diff --stat, git diff --cached --stat und git log --oneline -10.
- Prüfe Projektregeln in CONTRIBUTING, Commit-Hooks, Branchschutz, Pull-Request-Vorlagen und gegebenenfalls CODEOWNERS. Ownership-Dateien zeigen Zuständigkeit, nicht automatisch Freigabe.
- Lies relevante Diffs; suche in vorgeschlagenen Pfaden nach versehentlich enthaltenen Secrets, ohne Werte auszugeben. Bewahre fremde Änderungen und unversionierte Dateien.
- Zerlege jede gewünschte Wirkung: Commit, Branch, Merge, Rebase, Push, Tag und Release sind getrennte Autorisierungen. „Fertig“ oder „veröffentlichen“ ist ohne eindeutiges Ziel keine zusätzliche Freigabe.

## Commit und PR

Verwende vorhandene Commitkonventionen. Conventional Commits sind geeignet, wenn das Repository sie verlangt oder verwendet: übliche Struktur type(scope): summary; Typen, Scope, Sprache, Ticketbezug und Breaking-Change-Form folgen den lokalen Regeln. Teile Änderungen nach logisch unabhängigem Zweck, nicht allein nach Dateizahl. Lies den vollständig gestagten Diff, stage ausschließlich benannte Pfade und umgehe keine Hooks. Commit-only endet strikt mit dem lokalen Commit. Push oder PR erfolgen ausschließlich bei aktueller ausdrücklicher Freigabe für genau diese Wirkung und ihr Ziel; Projektkonventionen bestimmen das Verfahren, nicht die Freigabe.

Vor PR: vergleiche Basis und Head, prüfe betroffene Tests, Konflikte, Ownership und erforderliche Checks. PR-Beschreibung benennt Zweck, relevante Risiken, Prüfungen und bekannte Einschränkungen. Ein grüner Teilcheck ersetzt keine erforderliche CI.

## History und Remote

- Branch-/Worktree-/Merge-/Rebase-Ziel und ausgeschlossene Refs vorab konkret benennen.
- Bei nicht-fast-forward Push: Remotezustand lesen und Divergenz lokal integrieren; nicht mit Force wiederholen.
- Rebase, Amend, Reset, Clean, Restore mit Datenverlust, Force-Push, Branch-/Taglöschung und Hook-Umgehung sind besonders destruktiv und benötigen gesonderte genaue Freigabe. Geteilte/publizierte History nicht still umschreiben.
- Bei Konflikten beide fachlichen Absichten erhalten, Konfliktstellen und betroffene Dateien nachvollziehen und betroffene Checks nach Lösung erneut ausführen. Konfliktmarker oder unklare Semantik bedeuten Stopp, nicht automatisches ours/theirs.
- Push verifiziert den ausdrücklich benannten Remote und Ref sowie verbleibende lokale Abweichungen. Tagerstellung, Tag-Push und Provider-Release nicht zusammenfassen.

## Baselines und Ergebnis

Für Release-Baselines Version, Basis-Commit, Zielbranch, Tagmuster und vorhandene Releaseautomation aus Projektquellen ableiten. Tags/Releaseartefakte nicht aus dem Branch allein vermuten. Nach jeder Mutation Status, Diffs, Commit-ID, lokale/Remote-Refs und ggf. Providerstatus frisch prüfen. Berichte nur beobachtete Wirkungen; fehlende Remote-/CI-Zugriffe als Evidenzlücke nennen.

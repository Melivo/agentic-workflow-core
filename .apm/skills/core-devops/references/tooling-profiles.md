# Toolprofile nach Repositorysignal

Wähle Prüfwerkzeuge anhand vorhandener Sprache, Frameworks, Manifeste und Konfiguration. Dies sind Such- und Auswahlfragen, keine Aufforderung neue Abhängigkeiten zu installieren.

| Profil | Zu untersuchen | Regeln für Auswahl |
|---|---|---|
| Python | pyproject.toml, ruff.toml, tox.ini, pytest.ini, Lockfile und Projektaufgaben | vorliegende Formatter/Linter/Typprüfer und Versionpins übernehmen; Test-Runner nicht durch Linter ersetzen |
| JavaScript/TypeScript | package.json, Lockfile, tsconfig, ESLint/Biome-Konfiguration und Workspace | Paketmanager und Skripte des Repos nutzen; Formatierung, Lint, Typprüfung und Tests als getrennte Resultate ausweisen |
| Swift | Package.swift, Xcode-Projekt, SwiftLint-/Formatregeln und vorhandene Schemes | bestehende Build-/Test- und Plattformvoraussetzungen beachten; keine neue iOS-Plattformannahme |
| Dart/Flutter | pubspec.yaml, analysis_options.yaml, lockfile und CI | bestehende Analyze-, Format- und Testbefehle nutzen; Geräte-/Simulatoranforderungen separat markieren |
| Container/Workflowdateien | Dockerfile, Compose, CI-YAML, Shellskripte und Repo-Guides | passende Syntax-/Lintwerkzeuge nur nach bestehender Konvention; keine produktiven Image-Pushes aus einem Check ableiten |
| Weitere Sprachen | jeweilige Manifest-, Toolchain- und CI-Definition | vom Repo bestimmte Werkzeuge zuerst; falls kein Prüfer besteht, Lücke als Entscheidung/Setupbedarf benennen statt still eine Abhängigkeit einzuführen |

Beurteile Prüfer nach Zweck: Formatcheck soll nichts schreiben; Formatter verändert Dateien. Linter, Compiler/Typprüfer und Tests decken verschiedene Fehlerklassen ab. Wähle bei geänderten Dateien den engsten verlässlichen Scope, aber beachte gemeinsame Konfiguration und Imports: einzelne Dateien können kein vollständiger Typcheck sein.

Versionen müssen aus Manifest, Lockfile oder überprüfter aktueller offizieller Dokumentation stammen. Verwende keine erfundenen Mindestversionen oder CLI-Flags. Für versionsempfindliche CLI-/API-Aussagen zuerst die aktuelle offizielle Dokumentation ermitteln; wenn sie nicht verfügbar ist, keine präzise Syntax behaupten. Dokumentiere fehlende Runtime/Abhängigkeit als Voraussetzung und installiere sie nicht ohne Freigabe.

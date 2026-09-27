# Flutter

Lade diese Referenz nur für einen belegten Flutter-/Dart-Task. Projektarchitektur, `DESIGN.md`, State- und Navigationskonventionen bleiben vorrangig.

- Bewahre die vorhandene Schichtung und State-Lösung. Verwende Riverpod oder Bloc nur, wenn das Projekt sie bereits nutzt oder ihre Einführung bestätigt ist; nutze kein komplexes ad-hoc `setState` als zweite Zustandsarchitektur.
- Behandle `initState`, Abhängigkeitsänderungen, App-Lifecycle, Routenwechsel und `dispose` als unterschiedliche Grenzen. Entsorge Controller, FocusNodes, Animationen, Subscriptions, Timer und Observer beim zuständigen Owner.
- Prüfe `mounted` beziehungsweise Owner-Gültigkeit nach asynchronen Grenzen und verhindere veraltete Resultate. Cleanup darf keine neue asynchrone Arbeit starten.
- Nutze `MediaQuery`, Layout Constraints, Safe Areas und vorhandene adaptive Primitiven statt fester Geräteabmessungen. Prüfe Text Scaling, Semantics, Fokus, große Touchziele und reduzierte Bewegung.
- Ändere bei Flutter-Gen-Lokalisierung nur die ARB-Quelldatei. Generierte Dart-Lokalisierung bleibt unverändert; Generierung benötigt die im Auftrag erlaubte Ausführung.
- Verwende bestehende Transport-, Repository-, Cache- und Secure-Storage-Abstraktionen. Plain Preferences sind kein Secret Store.

Führe Widget-, Semantics- und Integrationschecks nur aus, wenn sie gepinnt und autorisiert sind. Ein Flutter-Build ist kein impliziter Testschritt.

# Angular

Lade diese Referenz nur, wenn Angular und seine Version im Repository belegt sind. Bestehende Architektur, `DESIGN.md`, Komponentenbibliothek und Projektkonventionen bleiben vorrangig.

- Bewahre die vorhandene Standalone-/NgModule-, Routing-, Formular-, State- und Stylingstrategie; migriere sie nicht als Nebenwirkung.
- Halte Templates deklarativ, typsicher und zugänglich. Verwende vorhandene Komponenten und Tokens statt paralleler UI-Primitiven.
- Wähle Signals, Observables und lokale Felder entsprechend der im Projekt etablierten Zustandsgrenze. Erzeuge keine doppelte Source of Truth.
- Beende manuelle Subscriptions und externe Ressourcen mit dem projektüblichen Lifecyclemechanismus. Templates und frameworkverwaltete Bindungen sollen Cleanup übernehmen, wo dies belegt ist.
- Bewahre Change-Detection- und SSR/Hydration-Annahmen der verwendeten Version; optimiere erst nach beobachtbarer Evidenz.
- Prüfe Navigation, Fokusführung, Formularfehler, asynchrone Zustände und responsive Templates in den vom Task betroffenen Flows.

Bei einer konkreten versionsabhängigen Angular- oder RxJS-Frage konsultiere Context7 gemäß `core-shared`-Toolrouting. Diese Referenz autorisiert weder eine Migration noch eine neue Abhängigkeit.

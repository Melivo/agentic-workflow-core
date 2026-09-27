# React und Next.js

Lade diese Referenz nur, wenn der Repositorykontext React belegt. Wende Next.js-spezifische Regeln nur an, wenn Next.js und dessen Version im Projekt belegt sind. Repositorykonventionen und `DESIGN.md` bleiben vorrangig.

## React

- Halte Komponenten auf Darstellung und Interaktion fokussiert; platziere Serverzustand, Formularzustand und lokalen UI-Zustand in den bereits etablierten Projektgrenzen.
- Leite Werte während des Renderns ab, statt synchronisierbare Kopien als Zustand zu führen. Verwende Effects nur für Synchronisation mit externen Systemen.
- Bereinige Subscriptions, Listener, Observer, Timer und abbrechbare Requests im Effect-Cleanup. Berücksichtige doppelte Entwicklungsaufrufe und stale Closures.
- Bewahre stabile Komponentenverträge. Ergänze Memoisierung nur bei gemessenem Renderproblem, nicht als Default.
- Verwende die vorhandene Form-, Query-, State- und Testlösung; führe keine zweite Bibliothek für dieselbe Verantwortung ein.

## Next.js, falls belegt

- Respektiere App-/Pages-Router, Server-/Client-Component-Grenzen, Caching und Datenladepfad der verwendeten Projektversion.
- Füge eine Client-Grenze nur für Browser-APIs, Interaktivität oder clientseitigen Zustand ein und halte sie möglichst klein.
- Verhindere Hydration-Abweichungen durch deterministisches initiales Markup und versioniere keine Annahme über volatile Next.js-Defaults in den Skill.
- Prüfe Navigation, Loading-, Error- und Not-found-Grenzen sowie Metadaten nur, soweit der Task sie berührt.

Bei einer konkreten versionsabhängigen React- oder Next.js-Frage konsultiere Context7 gemäß `core-shared`-Toolrouting. Übernimm keine API allein aus dieser allgemeinen Referenz.

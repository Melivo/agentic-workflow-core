# React Native

Lade diese Referenz nur für einen belegten React-Native-Task. Projektarchitektur, `DESIGN.md`, Navigation, New-/Old-Architecture-Entscheidung und bestehende Bibliotheken bleiben vorrangig.

- Bewahre die vorhandene State- und Server-State-Lösung. Zustand, Cache und Request-Lifecycle dürfen keine konkurrierenden Sources of Truth bilden; führe Zustand oder TanStack Query nicht ohne bestätigte Projektentscheidung ein.
- Bereinige Effects, AppState- und Navigation-Listener, Timer, Subscriptions sowie abbrechbare Requests. Berücksichtige Focus/Blur, Background/Foreground, Screen-Unmount und mögliche veraltete Closures getrennt.
- Kapsle native Module und Plattformunterschiede hinter bestehenden Projektgrenzen. Ändere Pod-, Gradle-, Berechtigungs- oder Native-Konfiguration nur, wenn sie im Taskscope liegt.
- Verwende Flexbox, Safe-Area-, Keyboard- und Window-Dimension-Primitiven statt fester Gerätewerte. Prüfe Dynamic Type beziehungsweise Font Scaling, Accessibility Labels/State, Fokus, Touchziele, reduzierte Bewegung und beide Plattformkonventionen.
- Bei ARB-basierter plattformübergreifender Lokalisierung editiere ausschließlich die ARB-Quelldateien. Ändere keine daraus generierten TypeScript-, Android- oder iOS-Ressourcen.
- Verwende bestehende Transport-, Offline-, Cache- und sichere Storage-Abstraktionen. MMKV oder AsyncStorage sind kein Secret Store ohne belegte sichere Schutzschicht.

Führe Komponenten- und Integrationschecks nur gepinnt und autorisiert aus. Metro-, Gradle- oder Xcode-Builds sind ohne ausdrückliche Buildautorisierung ausgeschlossen.

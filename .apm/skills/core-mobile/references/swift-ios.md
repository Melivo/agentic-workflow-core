# Swift iOS

Lade diese Referenz nur für einen belegten nativen Swift-/SwiftUI-Task. Vorhandene App-/Core-/Features-/Shared-Grenzen, `DESIGN.md`, Deployment Target und iOS-Konventionen bleiben vorrangig.

- Isoliere UI-Zustand auf dem `MainActor` und verwende das im Projekt etablierte Observation-Modell. Führe `@Observable`, Combine oder eine zweite State-Architektur nicht ohne bestätigte Entscheidung ein.
- Binde strukturierte Arbeit an den engsten Owner. SwiftUI-`.task` wird mit der View-Lebensdauer abgebrochen; zusätzlich gestartete Tasks, Observer, Delegates und native Handles benötigen einen expliziten zuständigen Lifecycle.
- Reagiere auf Scene Phase, Navigation und Background/Foreground nur dort, wo der Featurevertrag es verlangt. Verlasse dich für aktives Task-Cleanup nicht auf `deinit`.
- Verwende Dynamic Type, Accessibility Labels/Values/Traits, Fokus, VoiceOver-Reihenfolge, reduzierte Bewegung, ausreichende Touchziele, Safe Areas und adaptive Größenklassen gemäß iOS HIG und bestehendem Designsystem.
- Bei ARB-basierter gemeinsamer Lokalisierung ändere ausschließlich die ARB-Quelldateien. Generierte Swift-Symbole, String Catalogs oder Ressourcen werden nicht direkt editiert.
- Verwende vorhandene API-Client-, Repository-, Cache- und Keychain-Abstraktionen. Secrets gehören nicht in `UserDefaults` oder Klartextdateien.

Führe Unit-, View- und XCUITest-Prüfungen nur aus, wenn sie gepinnt und autorisiert sind. Xcode-Build, Codegenerierung und Paketauflösung benötigen eine ausdrückliche Freigabe.

# Migrationen

Lade diese Referenz für Schema-, Daten-, Index-, Partitionierungs-, Backfill-, Re-Embedding- oder Reindexänderungen. Erzeuge Migrationen mit dem bestehenden Projekttool; ein Paketdefault führt kein neues Tool ein und eine erzeugte Datei autorisiert keine Ausführung.

## Plan und Reihenfolge

1. Bestimme Ausgangsschema, Zielinvariante, betroffene Zugriffspfade, Datenvolumen, Kompatibilitätsfenster und Betriebsgrenzen.
2. Bevorzuge für Live-Systeme Expand-Contract:
   - additive, rückwärtskompatible Erweiterung,
   - kontrolliertes Dual-Write oder kompatible Übergangslogik,
   - begrenzter, wiederaufnehmbarer Backfill,
   - verifizierter Read-Switch,
   - verzögerter Contract-Schritt nach Soak Window.
3. Trenne destruktive Schritte von der expandierenden Migration und behandle sie als eigene, ausdrücklich autorisierte Operation.
4. Halte genau einen Migrations-Head. Bei Forks erzeuge vor der Übergabe eine projektkonforme Merge-Revision, statt einen Zweig stillschweigend zu verwerfen oder umzuschreiben.

## Reversibilität und Betrieb

- Migrationen sind standardmäßig reversibel. Wenn ein Down-Pfad Datenverlust oder falsche Semantik erzeugen würde, dokumentiere stattdessen einen sicheren Roll-forward- und Restore-Pfad mit Begründung.
- Definiere Vorbedingungen, Nachbedingungen, Abbruchkriterien, Backup-/Restorebezug und Wiederaufnahme nach Teilfehlern.
- Plane DDL auf heißen Tabellen lock-aware mit Timeout, kurzer Sperrdauer und geprüftem Engineverhalten. Unbegrenztes Warten oder erzwungene Sperren sind kein Default.
- Batches begrenzen Zeilen, Laufzeit und Transaktionsgröße; Fortschritt ist idempotent und beobachtbar. Vermeide eine Volltabellenmutation in einer einzigen langen Transaktion.
- Prüfe Fremdschlüssel, Defaults, `NULL`-Übergänge, Trigger, Replikation, CDC, Cache, Suchindex und alte Anwendungsversionen nach Relevanz.
- Versioniere bei Embeddings Modell, Dimension, Chunking und Vorverarbeitung; plane parallelen Index, Qualitätsprüfung, Umschaltung und Rückweg.

## Ausführungsgrenze

Vor jeder Ausführung gelten die Autorisierungsregeln aus `core-database/SKILL.md`. Nenne exakte Umgebung, Ziel, Migrationsbereich, erwartete Locks, Backupstatus, Abbruchkriterium und Rollback-/Roll-forward-Pfad. Preview oder Dry-run gegen Produktion bleibt eine produktive Aktion. Bei Drift zwischen geprüftem und aktuellem Schema wird nicht ausgeführt.

## Verifikation

Validiere Migration und Rückweg mit der vorhandenen nichtproduktiven Teststrategie, sofern autorisiert. Prüfe Schema- und Dateninvarianten, Kompatibilität alter und neuer Anwendungsversionen, Batch-Wiederaufnahme, Laufzeit-/Lockannahmen und den einzelnen Head. Nach Ausführung belegen Vorher-/Nachher-Zustand und fachliche Stichprobe die Wirkung; Exitcode allein genügt nicht.

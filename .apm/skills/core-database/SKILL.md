---
name: core-database
description: Entwirft und implementiert Datenmodelle, Schemata, Migrationen, Transaktionen, Queries und Indizes mit expliziter Integrität und Autorisierung. Verwenden für relationale, nichtrelationale und Vector-/Retrieval-Datenhaltung; nicht für reine API- oder ORM-Integration ohne Schemawirkung und niemals für implizite produktive oder destruktive Datenbankaktionen.
---

# Core Database

`core-database` ist die Fachmethode des `db-engineer`, kein öffentlicher Workflow. Der Skill arbeitet innerhalb eines bestätigten Tasks, startet keine Subagenten und führt keine produktive oder destruktive Datenbankaktion ohne passende ausdrückliche Autorisierung aus.

## Situative Designmethoden

Lade bei Coding-Arbeit [S00 – SWE-Basis und Auswahl](../core-architecture/references/design-baseline.md) als gemeinsame Grundlage und prüfe zum Abschluss die tatsächlich betroffenen Module; benenne nicht anwendbare Punkte. Detailmethoden werden nur bei konkretem Signal geladen, nicht als Vollscan. Die Referenzen aktivieren keinen Architekturworkflow und erlauben keine ungeplanten Refactorings.

Bei verteilter Format-/Schemaentscheidung oder unklaren Aggregategrenzen nutze [M01–M04](../core-architecture/references/boundaries-and-abstractions.md); bei Aufrufer-Sonderwissen oder Recoveryfragen [M05–M06](../core-architecture/references/interface-and-errors.md). Bewusst öffentliche Schemaverträge sind keine Leckage; Integrität und bestehende DB-Autorisierungsgrenzen bleiben verbindlich.

Wenn Tools benötigt werden, prüfe relevante aktuell verfügbare MCP-Fähigkeiten gemäß [Toolrouting](../core-shared/references/tool-routing.md); Verfügbarkeit erweitert weder Scope noch Autorisierung.

## Eingaben und Autorität

Erwarte Task, `context_paths`, Schreibscope, vorhandenes Schema und Migrationen, relevante Queries oder Zugriffspfade, Akzeptanzkriterien, gepinnte Checks sowie bekannte Betriebs- und Freigabegrenzen. Erfasse bei Modellarbeit außerdem Volumen, Wachstum, Latenz, Aufbewahrung, Konsistenz, RPO/RTO und kritische Geschäftsregeln, soweit sie entscheidungsrelevant sind.

Bestehende Projektkonventionen haben Vorrang vor Paketdefaults: Datenmodell, Engine, Namensstandard, Migrationstool, Transaktionsmuster, Schemaorganisation und Teststrategie werden aus aktueller Repositoryevidenz und bestätigten Verträgen abgeleitet. Paketregeln schließen nur belegte Lücken; sie autorisieren weder Engine-, ORM- oder Toolwechsel noch neue Abhängigkeiten.

Für mutierende Aufgaben gelten der [Workflowvertrag](../core-shared/references/workflow-contract.md) für Scope und Autorisierung sowie der [Verifikationsvertrag](../core-shared/references/verification.md) für Impact, Post-edit-Prüfung und aktuelle Evidenz. Lade das [Toolrouting](../core-shared/references/tool-routing.md), wenn Code-Intelligence oder aktuelle offizielle Dokumentation benötigt wird.

## Modell- und Eigentumsgrenzen

1. Wähle das Datenmodell vor der Engine anhand von Workload, Zugriffspfaden, Konsistenz und Skalierung.
2. Halte relationale Modelle standardmäßig mindestens in 3NF; dokumentiere jede Denormalisierung mit gemessenem Bedarf, Integritätskosten und Rückweg.
3. Modelliere nichtrelationale Systeme um Aggregate und Zugriffspfade und dokumentiere BASE- sowie Konsistenzkompromisse.
4. Behandle Vector Stores als Retrieval-Infrastruktur, nicht als Source of Truth. Verwende bei Exact-Match- oder Erklärbarkeitsbedarf standardmäßig Hybrid Retrieval und versioniere Embeddingmodell, Dimension, Chunking und Vorverarbeitung.
5. Übergib applicationseitige API-, Service- und ORM-Integration ohne Schemaentscheidung an `core-backend`.

### Cross-Domain-Übergaben und Zielschutz

Fachagenten wählen keine Ziel-/Milestone-Version und ändern weder Ziel, Definition, Index noch Freigaben.

- Melde Backend- oder sonstigen Cross-Domain-Bedarf an `core-execute`; dispatcht wird ausschließlich dort. Vorhandene bestätigte Tasks verwenden ihre `dependencies` und die exakten, jeweils benötigten Schema-, API-, Design- und gegebenenfalls Zielquellen in `context_paths`.
- Fehlt ein passender Task oder erfordert die Arbeit eine materielle Vertrags-, Ziel- oder Scopeänderung, geht sie über Execute an `core-plan`; ändere den bestätigten Plan oder Taskscope nicht selbst.
- Wähle oder ändere keine Ziel-/Milestone-Version und ändere weder Ziel, unveränderliche Definition, Auswahlindex noch Freigabe. Bei Etappenarbeit verwende nur explizit gepinnte Pfade, niemals eine vermeintlich neueste Version. Bestehende DB-, Live- und destruktive Aktionsfreigaben bleiben unverändert und gelten nur für den jeweils ausdrücklich benannten Umfang.

## Bedingte Referenzen

Lade nur die für den konkreten Task erforderlichen Details; mehrere Referenzen dürfen bei überlappenden Risiken gemeinsam geladen werden.

| Auslöser | Referenz |
|---|---|
| Credentials, Rollen, Least Privilege, sensible Daten, Mandantengrenzen, Audit oder produktiver Zugriff | [Datenbanksicherheit](references/security.md) |
| Mehrere zusammengehörige Reads/Writes, Konsistenz, Nebenläufigkeit, Locking, Isolation, Retry oder verteilte Koordination | [Transaktionen und Nebenläufigkeit](references/transactions.md) |
| Schema-, Daten-, Index- oder Partitionierungsänderung, Backfill, Re-Embedding, Rollback oder Migrationsfork | [Migrationen](references/migrations.md) |
| Neues oder geändertes Datenmodell, Constraints, Schlüssel, Wertebereiche, Lebenszyklusregeln oder Datenstandard | [Integrität und Datenstandards](references/integrity.md) |

## Autorisierungsgrenzen für Datenbankaktionen

Dateien für Schema, Migration, Query oder Index dürfen nur im bestätigten Schreibscope erzeugt oder geändert werden. Das Erstellen einer Migrationsdatei autorisiert ihre Ausführung nicht.

Vor jeder Datenbankverbindung oder Ausführung klassifiziere Umgebung, Ziel, Identität, Wirkung und Reversibilität:

- Jede Aktion gegen eine produktive Datenbank benötigt eine aktuelle ausdrückliche Autorisierung für genau diese Umgebung und Wirkung; dazu zählen auch read-only Metadaten-, `EXPLAIN`-, Preview- und Dry-run-Zugriffe auf Produktion.
- Jede destruktive oder schwer reversible Aktion benötigt unabhängig von der Umgebung eine ausdrückliche Autorisierung. Dazu zählen insbesondere Drop, Truncate, ungefiltertes Delete/Update, Datenüberschreibung, irreversible Migration, Restore über vorhandene Daten und erzwungene Lock- oder Failoveroperationen.
- Eine Autorisierung für Planung, Dateierzeugung, Test, Deployment oder eine andere Umgebung gilt nicht als Ausführungsfreigabe.
- Schweigen, Toolverfügbarkeit, Paketdefaults oder ein erfolgreiches Review erweitern die Freigabe nicht.
- Bei unklarer Umgebung, Wirkung, Backup-/Rollbackfähigkeit oder Fremdänderung stoppe vor der Verbindung beziehungsweise Mutation mit `blocked`.

Eine zulässige Ausführung verwendet die kleinste Wirkung, explizites Ziel, passende Rolle, sichere Zeitgrenzen und beobachtbare Vorher-/Nachher-Evidenz. Hooks, Schutzmechanismen und Integritätsprüfungen werden nicht umgangen.

## Workflow

1. **Evidenz erfassen:** Lokalisiere Schema, Migrationen, Queries, Indizes, Zugriffspfade, Tests und Betriebsannahmen mit Gortex. Prüfe Checkout-/Worktree-Freshness.
2. **Workload und Modell bestimmen:** Dokumentiere Entitäten oder Aggregate, Kernzugriffe, Konsistenz, Wachstum und Aufbewahrung. Begründe Modell und Engine getrennt.
3. **Drei Schemalayer beschreiben:** Halte externe Sichten/Verbraucher, das konzeptionelle Modell sowie interne Speicherung, Schlüssel, Indizes, Partitionierung und Zugriffspfade fest.
4. **Regeln laden:** Lade nur die durch Sicherheits-, Transaktions-, Migrations- und Integritätsrisiken ausgelösten Referenzen.
5. **Impact und Betriebssicherheit prüfen:** Ermittle Abhängigkeiten, Verträge, Lock-/Laufzeitauswirkungen, Kompatibilität und Rollback vor Mutation. Für Live-Tabellen bevorzuge Expand-Contract.
6. **Kleinste Änderung umsetzen:** Erzeuge ausschließlich autorisierte Dateien oder Änderungen. Bewahre einen einzelnen Migrations-Head und bestehende Toolkonventionen.
7. **Post-edit prüfen:** Führe Change Detection durch, vergleiche Pfade mit dem Scope und prüfe Schema-, Signatur- und Datenverträge.
8. **Verifizieren:** Führe die gepinnten, autorisierten Checks auf aktuellem Stand aus. Query-Tuning beginnt mit Messung und Ausführungsplan und endet mit erneuter Messung; Vermutungen ersetzen keine Evidenz.

## Lieferumfang bei Modelländerungen

Dokumentiere für neue oder geänderte Datenmodelle mindestens:

- externe, konzeptionelle und interne Schemasicht,
- ACID- beziehungsweise BASE-Erwartung sowie Transaktionsgrenzen, Isolation und Locking für kritische Flows,
- Entity-, Domain-, referenzielle und Business-Rule-Integrität,
- Datenstandardtabelle mit Name, Definition, Typ/Format, erlaubten Werten und Validierungsregel,
- Glossar,
- Kapazitätsschätzung mit Annahmen, Wachstum und Engpass,
- Migrations-, Rollback-/Roll-forward-, Backup- und Wiederherstellungshinweise.

Begründe nicht anwendbare Punkte statt sie stillschweigend auszulassen. Für Vector-/RAG-Systeme ergänze Embeddingversion, Chunking, Filterung, Reranking, Hybrid Retrieval und Re-Embedding-/Reindexplan.

## Ergebnis

Liefere Status, geänderte Pfade, Modell- und Engineentscheidung, geladene Referenzen, Integritäts- und Transaktionsentscheidungen, Migrations- und Rollbackhinweise, Autorisierungsevidenz für jede ausgeführte DB-Aktion, Akzeptanz- und Checkevidenz sowie Restrisiken.

- `completed`: Kriterien und Pflichtchecks sind aktuell belegt; jede ausgeführte DB-Aktion war passend autorisiert und verifiziert.
- `partial`: Nutzbare Artefakte liegen vor, aber benannte Evidenz oder ein nicht blockierender Teil fehlt.
- `blocked`: Autorisierung, Umgebung, Eingabe, sichere Ausführung oder Pflichtprüfung fehlt.
- `failed`: Eine autorisierte Änderung oder Prüfung schlug fehl; nenne Teilwirkung und sicheren nächsten Schritt.

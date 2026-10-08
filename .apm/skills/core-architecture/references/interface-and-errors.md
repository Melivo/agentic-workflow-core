# Schnittstellenlast und sichere Fehleroberflächen

Nur bei belegtem Signal laden. Die Methoden liefern Diagnose und Vorschläge, keine zusätzliche Schreibfreigabe. Scope, öffentliche Verträge und Tasktrennung gelten unverändert; Review bleibt read-only. Verhaltensänderungen sind keine verdeckten Refactorings.

<a id="m05--schnittstelle-und-komplexitatsverlagerung"></a>
## M05 — Schnittstelle und Komplexitätsverlagerung

**Auslöser:** Aufrufer wiederholen Setup, konfigurieren unverstandene Interna, behandeln interne Sonderfälle oder eine allgemeine Fähigkeit trägt Wissen eines bestimmten Verbrauchers.

**Inputs/Evidenz:** Aktuelle Anwendungsfälle, reale Aufrufstellen, Parameter/Defaults, Fehler und Reihenfolgenpflichten, Eigentümer der jeweiligen Policy und Testnähte.

**Methode:**

1. Benenne die kleinste Schnittstelle, die heutige Bedürfnisse deckt; keine zukünftigen Fähigkeiten erfinden. Trenne allgemeinen Mechanismus und spezielle fachliche Policy am passenden Eigentümer.
2. Prüfe für Konfiguration: brauchen Verbraucher tatsächlich unterschiedliche Werte, kann der Eigentümer sie sicher bestimmen, und rechtfertigt die Wirkung die Interfacekosten? Sichere Defaults oder ableitbare Werte können entlasten; notwendige Konfiguration bleibt ausdrücklich. Automatik ist nur besser, wenn sie vorhersehbar und überprüfbar ist.
3. Ziehe Komplexität nur zum Implementierer, wenn sie zu seiner Fähigkeit gehört, die übrige Anwendung vereinfacht und den öffentlichen Vertrag vereinfacht. UI-/Domänenpolicy nicht in Persistenz oder Netzwerk drücken, um Aufrufzeilen zu sparen.
4. Prüfe Zugriffsmethoden auf Repräsentationsleckage; bevorzuge Fähigkeiten vor internen Feldoperationen, soweit der öffentliche Datenvertrag das erlaubt. Bewerte Durchreichen/Context nach tatsächlichen Wissenskosten, nicht bloßer Parameterzahl.

**Ausnahmen/Stopgrenzen:** Ein einzelner Verbraucher macht eine API nicht falsch. Bewusst öffentliche Daten, fachlich notwendige Varianten und Deployment-/Securitykonfiguration sind legitim. Defaults dürfen keine Autorisierungsentscheidung, Geld-/Ressourcenwirkung oder wichtige Fehlerfolge verschweigen. Keine spekulative Generalisierung, keine neuartige Abhängigkeit oder Vertragsänderung ohne bestätigte Entscheidung.

**Ergebnis/Abschluss:** Tabelle der belastenden Entscheidungen mit Eigentümer, Verbraucherbedarf, sicherem Default oder begründeter Exposition; Empfehlung mit belegter Entlastung und Vertrags-/Testfolgen.

<a id="m06--fehleroberflache-und-wiederherstellung"></a>
## M06 — Fehleroberfläche und Wiederherstellung

**Auslöser:** Viele Fehlerformen, wiederholte Catch-Blöcke, leere/Default-liefernde Handler oder unklare Verantwortung für Wiederherstellung.

**Inputs/Evidenz:** Fehlerbedingungen an betroffener Boundary, Rückgaben/Ausnahmen, Seiteneffekte, Integritäts-/Securityfolgen, Wiederholbarkeit, Cleanup und tatsächliche Entscheidungsmöglichkeiten des Verbrauchers.

**Methode:** Betrachte jede Fehlerform als Teil des Vertrages. Prüfe pro Fall, ohne universelle Rangordnung:

- **Vertrag vereinfachen:** Kann ein idempotentes „Zustand sicherstellen“ den Sonderfall legitim entfernen? Nur wenn Verbraucher die Information nicht benötigen; bestehendes Fehlerverhalten nicht still ändern.
- **Intern vollständig wiederherstellen:** Nur bei belegter sicherer Recovery, ohne relevanten Informationsverlust und als expliziter Vertrag. Begrenzte Retries müssen Nebenwirkungen, Idempotenz und Ressourcen berücksichtigen.
- **Aggregieren:** Gemeinsame Behandlung an geeigneter Boundary kann Fehlerflächen reduzieren; notwendige Ursachen, Retrybarkeit und Diagnostics bleiben erhalten, Secrets nicht loggen. Ein Request-Handler darf isolieren, aufräumen und einen klaren Fehler liefern statt überall identische Catch-Blöcke.
- **Propagieren oder kontrolliert stoppen:** Wenn der Verbraucher entscheiden muss, Fehler mit ausreichender Bedeutung weitergeben. Fehlt sichere Recovery, an der kleinsten sicheren Boundary kontrolliert abbrechen und Zustand schützen; keine pauschale Prozess-Crash-Regel. Kosten und Verfügbarkeit der Wiederherstellung explizit vergleichen.

**Ausnahmen/Stopgrenzen:** Sicherheitsverletzung, unbestätigte Persistenz, verlorene Nachrichten, Datenverlust und nur teilweise ausgeführte Operationen niemals als Erfolg/harmlosen Default maskieren. Logging allein ist keine Wiederherstellung; Log-and-rethrow kann an einer Observability-Boundary dennoch gerechtfertigt sein. Ein Dienst, dessen Wert von Recovery abhängt, darf Fehler nicht einfach durch Crash „vereinfachen“. Fehlender Integritätsnachweis stoppt eine vorgeschlagene Maskierung.

**Ergebnis/Abschluss:** Fehler→Owner→Verbraucherentscheidung→Recovery-/Abbruchgarantie mit relevanten Fehlerpfadtests. Bei fehlender Sicherheit benannte Lücke und zuständiger Debug-/Domain-/Security-Folgeauftrag, kein unsicherer Vereinfachungsfix.

Adaptiert aus Clairvoyance (MIT, Cody Bromley 2026): [Provenienz](../PROVENANCE.md), [Lizenz](../THIRD_PARTY_NOTICES.md).

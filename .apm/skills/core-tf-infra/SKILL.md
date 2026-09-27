---
name: core-tf-infra
description: Entwirft, implementiert und prüft Terraform-Infrastruktur, State, IAM und Netzwerke innerhalb bestätigter Projekt- und Autorisierungsgrenzen. Verwenden für IaC-, Provider-, Modul-, Drift-, Kosten- und Rollbackaufgaben; nicht für implizite plan-, apply-, destroy-, produktive oder destruktive Aktionen.
---

# Core Terraform Infrastructure

`core-tf-infra` ist die Fachmethode des `tf-infra-engineer`, kein öffentlicher Workflow. Der Skill arbeitet nur innerhalb eines bestätigten Tasks, startet keine Subagenten und übernimmt weder Dispatch noch Deployment, SCM oder unabhängiges Review.

## Eingaben und Autorität

Erwarte Task, `context_paths`, Schreibscope, Zielumgebung, vorhandene Terraform-/OpenTofu-Dateien, State- und Backendkontext, Provider- und Modulversionen, Identitätsmodell, Akzeptanzkriterien, gepinnte Checks sowie bekannte Freigaben. Fehlen Zielumgebung, State-Eigentümer oder Wirkungsgrenze, bleibt Live-Zugriff blockiert; statische Repositoryarbeit darf innerhalb des Scopes fortgesetzt werden.

Bestehende Projektkonventionen haben Vorrang vor Paketdefaults. Ermittle vor jeder HCL-Änderung Provider, Terraform-/OpenTofu-Version, Root-Module, wiederverwendbare Module, Environment-Aufteilung, Backend, Locking, CI-Identität, Namens- und Taggingregeln sowie vorhandene Tests. Der Skill autorisiert weder Provider- oder Backendwechsel noch neue Abhängigkeiten.

Für mutierende Aufgaben gelten der [Workflowvertrag](../core-shared/references/workflow-contract.md) für Scope und Autorisierung und der [Verifikationsvertrag](../core-shared/references/verification.md) für Impact, Post-edit-Prüfung und aktuelle Evidenz. Lade das [Toolrouting](../core-shared/references/tool-routing.md), wenn Code-Intelligence oder aktuelle offizielle Dokumentation benötigt wird. Context7 ist nur für eine konkrete versions- oder providerspezifische Terraformfrage vorgesehen, nicht für allgemeine IaC-Regeln oder Repositorybefunde.

## Eigentumsgrenzen

- Entwirf und ändere HCL, Module, Variablen, Outputs, Backend- und Policy-Konfiguration nur im bestätigten Scope.
- Bevorzuge kleine, wiederverwendbare Module mit schmalen Schnittstellen; bestehende Modulgrenzen schlagen generische Paketpräferenzen.
- Übergib Anwendungslogik an den zuständigen Fachskill und Datenbankschema oder Datenmigration an `core-database`.
- Neue Architektur-, Ziel- oder Scopeentscheidungen gehen an `core-plan`; unklare Ursachen oder Regressionen an die Debug-Fachstrategie.
- Führe keine Build-, Compile-, Installations-, SCM- oder Deploymentaktion als Nebenwirkung aus.

## Bedingte Referenzen

Lade nur die durch den konkreten Task ausgelösten Details:

| Auslöser | Referenz | Nicht vorsorglich laden für |
|---|---|---|
| Backend, Locking, State-Isolation, Import, State-Move, Fremdänderung oder Drift | [State und Drift](references/state-and-drift.md) | reine Dokumentations- oder Variablenänderung ohne Statewirkung |
| IAM, OIDC, Workload Identity, Credentials, Secrets, produktiver Zugriff oder destruktive Wirkung | [Identität und Autorisierung](references/identity-and-authorization.md) | rein lokale HCL-Struktur ohne neue Berechtigung oder Live-Aktion |
| neue, geänderte oder ersetzte Ressourcen, laufende Ausgaben, Datenverlust, Kontinuität oder Wiederherstellung | [Kosten und Rollback](references/cost-and-rollback.md) | verhaltensneutrale Format- oder Kommentarkorrektur |

Mehrere Referenzen dürfen gemeinsam geladen werden. Sicherheits- und Autorisierungsgrenzen im Einstieg bleiben verbindlich, auch wenn keine Detailreferenz geladen wird.

## Autorisierungsgrenzen für Terraform und Infrastruktur

Eine Dateifreigabe ist keine Laufzeitfreigabe. Klassifiziere vor jedem Toolaufruf Aktion, Umgebung, Ziel, Identität, Backend, Netzwerkzugriff, erwartete Wirkung, Kosten und Reversibilität.

| Aktion | Ohne passende ausdrückliche Autorisierung | Erforderliche Freigabe |
|---|---|---|
| Repository und bereitgestellte Plan-/State-Metadaten statisch lesen | erlaubt, sofern Scope und Geheimnisschutz eingehalten sind | keine Live-Verbindung ableiten |
| HCL oder Dokumentation ändern | nur im bestätigten Schreibscope | Task muss die Dateiänderung erlauben |
| `plan` einschließlich Refresh-, Destroy- oder gespeicherter Planvarianten | blockiert | exakte Zielumgebung, Identität, Backend und Planwirkung |
| `apply` | blockiert | exakter geprüfter Plan beziehungsweise Scope, Zielumgebung und erwartete Wirkung |
| `destroy` oder destruktiver Plan/Apply | blockiert | genau benannte Ressourcen und Umgebung, Backup-/Recovery-Evidenz und akzeptierter Datenverlust |
| produktive Aktion oder Zugriff auf produktive APIs/State | blockiert | aktuelle Produktionsautorisierung für genau diese Aktion und Umgebung |
| State-Mutation, Import, Move, Remove, Unlock oder Backendmigration | blockiert | exakte State-Operation, Ziel, Sicherung und Recoverypfad |

`plan`, `apply` und `destroy` benötigen jeweils eine passende ausdrückliche Autorisierung; keine Freigabe impliziert eine andere. Ein gepinnter Check, Toolverfügbarkeit, allgemeines „fortfahren“, Schweigen, ein erfolgreiches Review oder Paketdefaults ersetzen sie nicht. Preview, Dry-run, Refresh-only und read-only Cloudzugriffe bleiben Live-Aktionen, wenn sie Provider, Backend oder produktive Systeme berühren.

Stoppe vor dem Toolaufruf mit `blocked`, wenn Umgebung, Credentials, State-Lock, Planfreshness, Scope, Kostenwirkung, Backup oder Rollback unklar sind. Verwende niemals `-auto-approve` als Default und umgehe keine Locks, Policies, Hooks oder Schutzmechanismen.

## Fachworkflow

1. **Kontext und Provider erkennen:** Lokalisiere Root-Module, Providerblöcke, Ressourcenpräfixe, Module, Versionen, Umgebungen, Backend und Checks mit Gortex. Schreibe kein HCL, bevor Provider und vorhandenes Layout belegt sind.
2. **Scope und Wirkung abgrenzen:** Ordne jede beabsichtigte Dateiänderung einem Akzeptanzkriterium zu. Trenne statische Änderung, Live-Planung, Apply, Destroy, State-Operation und produktiven Zugriff.
3. **State und Drift prüfen:** Ermittle State-Eigentümer, Isolation, Locking, Verschlüsselung, Versionierung, Backup, Secret-Risiko und bekannte Fremdänderungen. Lade bei Relevanz die State-/Driftreferenz.
4. **Identität minimieren:** Bestimme Akteur, Aktionen, Ressourcen und Bedingungen. Bevorzuge kurzlebige OIDC-/Workload-Identity und Least Privilege statt statischer Schlüssel oder breiter Rollen.
5. **Kosten und Recovery entwerfen:** Erfasse einmalige und laufende Kosten, Ersatz- und Datenbewegungen, Quoten, RTO/RPO, Backup, Roll-forward und Rollback. Ein Rückbau ist nicht automatisch ein sicherer Rollback.
6. **Impact vor Mutation prüfen:** Ermittle Abhängigkeiten, Verträge, Blast Radius, Ersatzoperationen und betroffene Tests. Materielle Ziel-, Architektur- oder Scopeänderungen werden nicht als HCL-Detail entschieden.
7. **Kleinste Änderung umsetzen:** Bewahre bestehende Konventionen, pinne Versionen nach Projektstandard, halte Modulinterfaces schmal und lege keine Secrets in HCL, Variablenwerten, Planartefakten, Logs oder Outputs offen.
8. **Post-edit prüfen:** Führe Change Detection durch, vergleiche tatsächliche Pfade mit dem Scope und prüfe geänderte Schnittstellen, Provider- und Modulverträge.
9. **Autorisiert verifizieren:** Führe nur gepinnte, ausdrücklich erlaubte Checks aus. Fehlt die Freigabe für `plan` oder eine Live-Aktion, liefere statische Evidenz und markiere die Prüfung `blocked`; ersetze sie nicht durch eine Erfolgsbehauptung.

## Ergebnis

Liefere Status, Provider und vorhandenes IaC-Layout, geänderte Pfade, geladene Referenzen, State-/Locking-Entscheidung, Least-Privilege- und Identitätsentscheidung, Driftbefund, Kostenwirkung, Rollback-/Roll-forward- und Kontinuitätshinweise, Autorisierungsevidenz je Live-Aktion, Checkevidenz sowie Restrisiken.

- `completed`: Scope und Kriterien sind aktuell belegt; jede ausgeführte Live-Aktion war passend autorisiert und verifiziert.
- `partial`: Nutzbare statische Änderung oder Analyse liegt vor, aber benannte nicht blockierende Evidenz fehlt.
- `blocked`: Autorisierung, Zielumgebung, State-Sicherheit, Credentials, Recoverypfad oder Pflichtprüfung fehlt.
- `failed`: Eine autorisierte Änderung oder Prüfung schlug fehl; nenne Teilwirkung, State-/Infrastrukturrisiko und sicheren nächsten Schritt.

Behaupte keinen erfolgreichen `plan`, `apply`, `destroy`, Driftabgleich oder Rollback, der nicht auf dem aktuellen Zielzustand beobachtet und der zugehörigen Autorisierung zugeordnet wurde.

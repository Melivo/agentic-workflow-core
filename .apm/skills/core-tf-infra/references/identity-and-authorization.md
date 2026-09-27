# Identität und Autorisierung

Lade diese Referenz bei IAM, CI/CD-Identitäten, Credentials, Secrets, produktivem Zugriff oder destruktiver Wirkung. Sie konkretisiert Least Privilege; sie erteilt keine Freigabe.

## Least-Privilege-Methode

Definiere Berechtigungen aus dem konkreten Datenfluss und der geplanten Wirkung:

1. **Akteur:** menschlicher Leser, CI-Planer, CI-Anwender, Laufzeitdienst oder Break-glass-Rolle.
2. **Aktion:** erforderliche Read-, Create-, Update-, Delete-, Pass-/Impersonate- und State-Rechte getrennt erfassen.
3. **Ressource:** Konto, Projekt, Subscription, Compartment, Region und konkrete Ressourcen oder Pfade begrenzen.
4. **Bedingung:** Umgebung, Branch/Repository, Audience, Subject, Tags, Zeitfenster, Netzwerk oder Genehmigungsstufe einschränken.
5. **Lebensdauer:** kurzlebige Föderation und automatische Rotation gegenüber statischen Zugangsdaten bevorzugen.
6. **Beobachtbarkeit:** Auditlogs, eindeutige Principals und Alarmierung für privilegierte oder destruktive Nutzung vorsehen.

Trenne Plan-/Leserechte von Apply-/Schreibrechten und Produktionsrollen von Nichtproduktion. Wildcards sind kein Default. Wenn ein Provider eine engere Ressourcengrenze technisch nicht unterstützt, dokumentiere den belegten Grund, den minimalen Action-Satz, kompensierende Bedingungen und den geplanten Reviewzeitpunkt.

## OIDC und Credentials

Bevorzuge OIDC, Workload Identity, Managed Identity oder ein gleichwertiges kurzlebiges Föderationsmodell. Binde Trust Policies mindestens an erwarteten Issuer, Audience und Subject beziehungsweise workload-spezifische Claims. Ein Repository- oder Organisationswildcard darf keine produktive Schreibrolle erhalten, wenn eine engere Bindung möglich ist.

- Lege Schlüssel, Tokens, Passwörter und Backend-Credentials nie in HCL, `.tfvars`, Plan-/Run-Artefakten, Logs oder Outputs ab.
- Secret-Manager-Datenquellen verhindern nicht automatisch, dass Werte in State oder Plan persistieren. Minimiere Secretmaterial in Terraform und behandle State weiterhin als sensibel.
- Markiere sensible Outputs, aber beschreibe diese Markierung nicht als Verschlüsselungs- oder Zugriffsschutz.
- Rotiere oder widerrufe exponierte Credentials über den zuständigen sicheren Prozess; ersetze sie nicht nur im Repository.

## Freigabe je Wirkung

Ordne jede Live-Aktion einer aktuellen ausdrücklichen Autorisierung zu. Die Freigabe nennt mindestens Aktion, Umgebung, Ziel, Identität und Wirkungsgrenze; für destruktive oder produktive Aktionen zusätzlich erwartete Änderungen, Kosten-/Datenwirkung und Recoverypunkt.

- `plan` autorisiert weder `apply` noch State-Mutationen.
- `apply` autorisiert weder `destroy` noch ungeprüfte Ersatz- oder Zusatzressourcen außerhalb des freigegebenen Plans.
- `destroy` wird auf genau benannte Ressourcen und eine konkrete Umgebung begrenzt.
- Nichtproduktionsfreigabe gilt nicht für Produktion.
- Read-only IAM oder Cloudzugriff auf Produktion bleibt produktiver Zugriff und benötigt passende Autorisierung.
- Eine neue Planversion, Drift oder geänderte Provider-/Modulabhängigkeit kann die bisherige Apply-Freigabe ungültig machen.

Bei Break-glass-Nutzung dokumentiere Owner, Grund, Ablaufzeit, Logging, Review und Rücknahme der erhöhten Rechte. Dauerhafte Ausweitung ist kein zulässiger Recovery-Shortcut.

## Prüffragen

Vor einer IAM- oder Live-Aktion müssen folgende Fragen belegt sein:

- Welcher Principal handelt und wodurch wird er authentifiziert?
- Welche konkreten Aktionen und Ressourcen sind erforderlich?
- Welche Rechte sind nur für Planung, welche für Mutation nötig?
- Welche Claims oder Bedingungen begrenzen Missbrauch?
- Wo können Secrets in Plan oder State gelangen?
- Wie werden Rechte widerrufen, rotiert und auditiert?
- Welche aktuelle Benutzerautorisierung deckt genau diese Wirkung?

Fehlt eine Antwort, bleibt die Aktion `blocked`. Für konkrete Provider-Syntax oder versionsabhängige IAM-Fähigkeiten lade gemäß Toolrouting aktuelle offizielle Dokumentation über Context7; übertrage keine generischen Beispiele ungeprüft in HCL.

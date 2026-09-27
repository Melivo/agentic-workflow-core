# Datenbanksicherheit

Lade diese Referenz nur, wenn Rollen, Credentials, Mandantengrenzen, sensible Daten, Audit, Verschlüsselung oder ein Zugriff auf eine laufende Datenbank betroffen sind. Die Autorisierungsgrenzen für produktive und destruktive Aktionen stehen in `core-database/SKILL.md` und gelten unverändert.

## Zugriff und Rollen

- Verwende die vorhandene Identitäts- und Rollenarchitektur mit Least Privilege. Trenne Laufzeit-, Read-only-, Migrations-, Backup- und Administrationsrechte, soweit das Projekt diese Verantwortungen unterscheidet.
- Vergib keine breiten Eigentümer- oder Superuserrechte als Paketdefault. Jede neue Berechtigung nennt benötigte Operationen, Objekte, Umgebung und Widerrufspfad.
- Halte Mandanten- und Zeilenisolation in allen Zugriffspfaden konsistent. Eine Anwendungsklausel allein ersetzt keine bestätigte Datenbankpolicy, wenn alternative Pfade bestehen.
- Nutze parametrisierte Queries und etablierte Treiber-/ORM-Primitiven; Untrusted Input wird nie als SQL-, Query-, Operator-, Pfad- oder Identifierfragment übernommen.

## Credentials und Schutzbedarf

- Beziehe Credentials aus der etablierten Secretablage. Speichere sie weder in Migrationen, Fixtures, URLs, Logs noch Ergebnisartefakten.
- Dokumentiere Klassifikation, Aufbewahrung, Löschung, Maskierung und zulässige Replikation sensibler Daten, wenn der Task diese Daten berührt.
- Verwende die projektseitig festgelegten Transport- und At-rest-Schutzmechanismen. Erfinde keine Kryptografie und ändere Schlüssel- oder Verschlüsselungsarchitektur nicht als Nebenwirkung.
- Produktionskopien dürfen nicht ungeprüft in Entwicklung oder Tests übernommen werden; nutze bestehende Maskierungs- oder Synthetikverfahren.

## Audit und Betrieb

Protokolliere sicherheitsrelevante administrative und datenverändernde Vorgänge gemäß Projektpolicy mit Akteur, Ziel, Zeitpunkt und Ergebnis, jedoch ohne Secret- oder unnötige Inhaltsdaten. Prüfe, dass Backup, Restore, Replikate, Exporte und Observability denselben Schutzbedarf einhalten. Fehlende Auditierbarkeit oder unklare Datenherkunft ist ein sichtbares Risiko, kein stillschweigend akzeptierter Default.

## Verifikation

Belege wirksame Minimalrechte, verweigerte unzulässige Zugriffe, Mandantenisolation, Secretfreiheit der Artefakte und Redaction. Nutze keine produktiven Konten oder Daten für die Prüfung ohne passende ausdrückliche Autorisierung.

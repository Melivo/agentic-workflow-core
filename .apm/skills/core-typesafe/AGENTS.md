# Core TypeSafe

## Purpose

Portable, beratende TypeSafe-Bewertung für die drei Profile aus dem
[TypeSafe-Vertrag](../core-shared/references/typesafe-contract.md) bereitstellen.

## Ownership

Dieses Bundle besitzt Fragenwortlaut, Antwortprüfung, HTTP-Adapter, den isolierten
synthetischen Bildprototyp und den reinen Planvergleichs-Helper. Es stellt außerdem `finalize_response` als netzfreien
Abschluss einer rohen Harnessantwort bereit; ein MCP-Client oder eine Verbindung
zu CodeMode-Tools gehört nicht zum Pythonmodul. Die einzige Collection-/Outbox-/Transportimplementierung liegt in `scripts/typesafe_collection.py`; `scripts/typesafe_owner.py` besitzt nur sichere lokale Configlektüre und die reine Monatsendeprüfung. Das gleichnamige Repositoryskript ist ein Kompatibilitätswrapper. Der fachliche Datenvertrag bleibt
bei `core-shared`, die Bewertungsmethode bei `core-review`; der normale Planablauf
bei `core-plan`: regulärer minimierter Vorbewertungsversuch bei jedem Core-Planreview, blindes fixes Ersturteil und getrennte Adjudikation derselben Session. Fehlende Datenfreigabe/Fähigkeit oder Fehler lassen nur die Beobachtung offen. Import startet keinen Aufruf; der Owner braucht vor jedem Versand passende Freigaben.

## Local Contracts

- Öffentliche API von `scripts/typesafe_eval.py`: `PROFILES`, `build_request`,
  `evaluate`, `finalize_response`, `https_transport`, `PreparedRequest`,
  `EvaluationResult`, `EvaluationError`, `InputValidationError`, `TransportError`.
- Nur Python-Standardbibliothek; läuft aus einer Bundlekopie ohne Installation.
- Import und `build_request` sind netzfrei. Gesendet wird nur über einen vom
  Aufrufer übergebenen Transport und höchstens einmal je `evaluate`.
- `https_transport` hat eine feste Zieladresse, prüft TLS und begrenzt die gesamte
  Netzwerkzeit einschließlich DNS, Verbindung, Status, Header und Body. Ein privater
  Einmalprozess besitzt das HTTP-IO; bei Fristablauf wird er beendet und eingesammelt.
  Die Pipeantwort ist größenbegrenzt, Schlüssel und Payload stehen nie in argv.
  Er folgt keinen Weiterleitungen und wiederholt nichts. Er liest
  ausschließlich `TYPESAFE_API_KEY` aus der geerbten Umgebung; Proxy-Einstellungen
  der Umgebung gelten wie bei `urllib` üblich.
- `request_sent=False` bezeichnet nachweisliche Nichtsendung, insbesondere
  `key_missing`/`key_invalid`; `True` bedeutet Versand möglich oder erfolgt,
  keine Zustellgarantie. Netzwerk- und Timeoutfehler bleiben ungewiss.
- Bewertungs- und reine Planvergleichsmodule: Keine Datei-, Log- oder Statusschreibzugriffe. Collection/Outbox schreiben nur explizit in sichere eigene Ressourcen; der Ownerhelper liest nur Config. Fehler tragen feste Texte und Codes,
  keine Payloads, Antwortkörper, Ausnahmetexte oder Schlüssel.
- Geänderter Fragenwortlaut erhöht `QUESTION_VERSION`.
- Aktionsschwellen fehlen bewusst: Modellantworten bleiben `unresolved`, bis eine
  profilbezogene Auswertungsregel separat bestätigt ist.

## Work Guidance

Offizielle TypeSafe-Dokumentation vor Vertragsänderungen frisch lesen. Echte
API-Aufrufe brauchen eine ausdrückliche Freigabe für Daten, Requestzahl und Kosten.

## Verification

`tests/test_typesafe_eval.py` prüft das Bundle offline mit synthetischen Antworten.
Das belegt weder Modellgüte noch Authentifizierung oder Live-Kompatibilität.

## Child DOX Index

- [Lernbeispiele](examples/AGENTS.md) — isolierte synthetische Bildfixtures und
  experimentelle Beispiele; getrennt von Textprofilen und Sammlung.
- [Bildbedienung](references/images.md) und [Bild-Evaluation](references/images-evaluation.md) —
  begrenzte Bedienung, gebundene Versuchsbefunde und Nichtnutzung.
- [Evaluationsordner-Vorlage](assets/evaluation-directory-AGENTS.md) — minimale
  Leseregel und Originalschutz für ausdrücklich beauftragte Evaluationsartefakte;
  die Projektkopie wird nur bei vorhandenem Artefaktschreibrecht angelegt.

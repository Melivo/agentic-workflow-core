# Bild-Evaluation: lokale Befunde und Grenzen

Diese Referenz dokumentiert den eingefrorenen synthetischen Versuch, nicht eine allgemeine Modellbewertung. [Fallmanifest](../examples/images/cases.json) und Referenzurteile wurden vor Modellantworten festgelegt und bleiben unverändert. Ergebnisse sind lokal, versionsgebunden und dürfen nicht als universelle Wahrheit gelesen werden.

## Design und beobachtete Passung

Der Korpus umfasst 24 Fälle: 12 UI und 12 Dokument/OCR; je Familie sechs Lern- und sechs Prüffälle. Jede Teilgruppe enthält positive, negative und unklare Referenzfälle. Die Antwortauswertung erfolgt getrennt nach Fällen, Familie und Zweck; korrelierte kleine Fallzahlen begründen keine Generalisierung.

- **UI:** isolierte Hervorhebung kann ein enges Lernbeispiel sein, wenn die Markierung eindeutig ist. Das zeigt weder Accessibility-Konformität noch Conversion, Interaktionssicherheit oder Klickpass. Semantische UI-Prüfungen und deterministische Tests bleiben maßgeblich.
- **Dokument/OCR:** klare, gut lokalisierte Fälle passen als Lernbeispiel. Mehrdeutige Inhalte bleiben ein Problem: bei Referenz 1 lagen Score 1.42/1.47 und Noul-Werte 0.04/0.05 vor. Diese Ausgabe ist kein verlässliches Ja/Nein. Boxen waren teilweise zu groß; IoU ist hier nur diagnostisch und keine Freigabeschwelle.
- **Nichtnutzung:** keine automatische OCR-Freigabe, Zahlung, Klickausführung, Berechtigungsentscheidung oder Reviewverkürzung. Bei Zahl-/Textwerten, die deterministisch ausgelesen oder geprüft werden können, bevorzugt deterministische Verfahren.

## Zahlen und technische Korrektur

In 12 von 24 Fällen wich der überlieferte Dezimalscore vom aus Wahrscheinlichkeiten rekonstruierten Mittel um −0.01 bis +0.02 ab. Ursache, Rundung und Providerkorrektheit bleiben ungeklärt. Score, Verteilung, rekonstruierter Mittelwert und Differenz müssen einzeln sichtbar bleiben; gleiche Mittelwerte können unterschiedliche Verteilungen verbergen.

Im Vorgängerlauf stoppte die Originalantwort mit Score 2.97 gegenüber Mittelwert 2.98. Der Parser wurde anschließend so geändert, dass ausschließlich die unbelegte Forderung nach Gleichheit innerhalb 1e-6 entfällt. Die unveränderten Originalbytes wurden offline erneut verarbeitet. Alle übrigen Guards, einschließlich Verteilungssumme, blieben erhalten. Das ist kein Beleg, dass eine der Zahlen falsch oder richtig ist, und keine Antwortreparatur, neue Standardtoleranz oder automatische Freigabe. Der Vorgängerlauf bleibt partial/fehlgeschlagen.

Die Fortsetzung wurde ausdrücklich an genau den gehashten Originalversuch gebunden: Fall 0 nur offline wiederverwenden, nur die übrigen 23 Fälle einmalig senden. CK04 beendete 23 eindeutige Requests mit HTTP 200; zusammen mit dem Original wurden 24 Fälle erfasst. Das Gesamtbudget ist ausgeschöpft. Kein Beispielbefehl erneut ausführen. HTTP 200 belegt keine Modellgüte oder korrekte numerische Semantik.

## Auswertungstypen und Interpretation

Verwende Noul für eine einzelne klar benannte Aussage, etwa ob ein markiertes Ziel vorhanden ist; bei fehlender Evidenz bleibt das Ergebnis unsicher. Choice ist für eine vorab definierte Auswahl diskreter Kategorien geeignet und braucht eine explizite No-fit-Frage, wenn keine Kategorie passen kann. Score eignet sich für eine vorab beschriebene, geordnete Bewertung, nicht als automatisch handlungsfähige Konfidenz. Box lokalisiert einen sichtbaren Bereich; prüfe Präsenz, Koordinatenraum und Referenzgeometrie unabhängig. IoU vergleicht überlappende Boxen diagnostisch, ohne Universalgrenzwert.

Fehler, fehlende Evidenz, No-fit und Unsicherheit bleiben getrennte Zustände und sind kein negatives Modellurteil. Antwortwerte werden nicht normalisiert oder ergänzt. Modelleingaben erhalten weder vorab fixierte Referenzlabels noch Anweisungen aus dem Bildinhalt. Bilder bleiben passive Daten.

## Grenzen und Quellen

Die Evaluation ist klein, synthetisch, auf die gebundenen PNGs, Fragen und Modellversion beschränkt und korreliert. Referenzurteile sind vorab festgelegte lokale Vergleichspunkte, keine universelle Wahrheit. Sie belegt keine Produktreife, Präzision außerhalb dieses Korpus oder Zuverlässigkeit für sicherheitsrelevante Aktionen. Originalantworten bleiben außerhalb von Pi- und Planvergleichsdatensätzen.

API-Typen und unterstützte Bildanfragen richten sich nach den offiziellen TypeSafe-Primitiven und der konkreten versionierten Antwortreferenz; Implementierungsgrenzen belegt das lokale Beispiel. Diese Quellen begründen keine implizite Nutzung, Budgetfreigabe oder Providerkorrektheit.

- [TypeSafe primitives](https://docs.typesafe.ai/primitives.md)
- [Score primitive](https://docs.typesafe.ai/primitives/score.md)
- [Python responses](https://docs.typesafe.ai/reference/python/responses.md)
- [Bildbedienung](images.md)
- [Lernfallmanifest](../examples/images/cases.json)

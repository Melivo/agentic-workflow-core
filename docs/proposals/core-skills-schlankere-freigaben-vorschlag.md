# Vorschlag: Zielorientierte Freigaben für die Core-Skills

Stand: 2. November 2026. Diskussionsvorschlag, noch nicht implementiert.
Es werden weder Skills noch globale Anweisungen durch dieses Dokument geändert.

## Ziel

Ein bestätigtes Ziel oder ein freigegebener Meilenstein soll innerhalb seines
vereinbarten Wirkungs- und Risikorahmens eigenständig erreicht werden. Der Nutzer
entscheidet über Ziele, wesentliche Risiken und echte Alternativen, nicht über
jeden notwendigen Entwicklungs-, Prüf- oder Reparaturschritt.

**Leitregel:** Ein bereits freigegebener Zweck und Wirkungsrahmen wird nicht für
jeden darunterliegenden Schritt erneut zur Entscheidung gestellt.

## Beobachtetes Problem

Die Core-Verträge erlauben bereits autonome Arbeit innerhalb bestehender
Autorisierung. Einzelne Plan- und Recovery-Regeln können diese Freigabe jedoch
wieder in viele kleine Einzelgenehmigungen zerlegen. Nach einem Testfehler wird
dann selbst die notwendige Bereinigung zum neuen Freigabeprozess.

Weitere Reibung entsteht, wenn agentenseitig gewählte Abläufe zu vermeintlichen
Produktanforderungen werden: zusätzliche persönliche Testzyklen, wiederholte
Bereitschaftsabfragen oder enge Zeitfenster, die menschliche Rückmeldungen mit
automatischen Sicherheitsaktionen konkurrieren lassen.

Ein fehlgeschlagener Test muss als fehlgeschlagen erhalten bleiben. Daraus folgt
aber nicht automatisch ein Verbot bereits autorisierter Diagnose und Recovery.

## 1. Autorisierung einmal am Wirkungsrahmen festmachen

`core-plan` benennt knapp die tatsächlichen Grenzen, soweit sie nicht schon aus
dem Auftrag eindeutig hervorgehen:

- Ziel und Akzeptanzkriterien;
- betroffene Umgebung und Kunden-/Datenbindung;
- erlaubte notwendige Änderungen und externe Wirkungen;
- Kostenrahmen und ausgeschlossene irreversible Aktionen;
- Test-, Bereinigungs- und Recovery-Wirkungen einschließlich zulässiger Neustarts;
- Schritte, die wirklich nur der Nutzer persönlich ausführen kann.

Dafür genügen wenige Sätze im bestehenden Plan. Keine neue Freigabedatei,
Autorisierungsdatenbank oder zusätzliche Pflichtmatrix einführen.

Beispiel: Die ausdrückliche Freigabe eines Staging-Abozyklus mit Stripe-Testdaten
kann Diagnose, erforderliche Fehlerbehebung, Testbestellung, Testkündigung,
Bereinigung des eigenen Testabos und kontrollierte Wiederaufnahme der betroffenen
Stage-Dienste einschließen. Sie schließt nicht automatisch Stripe Live,
Produktionsänderungen, fremde Kunden oder Datenlöschung ein.

## 2. Rückfragen nur bei einem echten Entscheidungspunkt

Eine erneute Freigabe ist erforderlich, wenn mindestens einer dieser Fälle gilt:

- Eine notwendige Wirkung liegt außerhalb des bestätigten Rahmens oder ist darin
  materiell unklar.
- Ein neues Produktziel, geändertes Nutzerverhalten oder ein wesentlicher
  Zielkonflikt verlangt eine Entscheidung des Nutzers.
- Es entstehen neue erhebliche Kosten, Produktionswirkungen, ein erhöhtes
  irreversibles Datenrisiko oder eine neue Vertrauensgrenze.
- Eine sichere Fortsetzung ist ohne eine tatsächlich nutzereigene Aktion nicht
  möglich, etwa Google-Zustimmung, Anmeldung oder vorgeschriebene persönliche
  Abnahme.

Keine erneute Freigabe allein wegen eines Fehlversuchs, eines notwendigen kleinen
Fixes, eines Neustarts innerhalb freigegebener Recovery oder eines weiteren
erforderlichen Regressionstests. Planbestätigung und aktuelle Nutzeranweisungen
sind gemeinsam auszuwerten; eine alte restriktivere Planformulierung darf eine
spätere ausdrückliche Freigabe nicht ignorieren.

## 3. Testfehler, Sicherheit und Fortsetzung trennen

Nach einem Fehler führt `core-execute` innerhalb seiner Autorisierung aus:

1. Unsichere weitere Wirkungen stoppen und den tatsächlichen Zustand prüfen.
2. Fehlversuch und relevante Evidenz unverändert erhalten.
3. Ursache mit vorhandenen Werkzeugen eingrenzen.
4. Notwendige Bereinigung und kleinste geeignete Reparatur durchführen.
5. Invarianten und sichere Wiederaufnahmebedingungen prüfen.
6. Betroffene Tests wiederholen und bis zur Akzeptanzprüfung fortsetzen.

Ein Sicherheitsstopp bleibt wirksam, bis die sichere Fortsetzung belegt ist.
Das ist kein blinder automatischer Neustart. Ist Recovery bereits freigegeben,
braucht ihre kontrollierte Ausführung aber keine zusätzliche Zustimmung.
Unbekannte Datenintegrität oder ein nicht beherrschbarer Fehler bleiben echte
Haltegründe. Wiederholungen ohne neue Erkenntnis lösen eine Ursachen- und
Vereinfachungsprüfung aus, keine endlose Testschleife.

## 4. Testbedienung nicht unnötig auf den Nutzer verlagern

- Wenn der Nutzer Tests an den Agenten delegiert, übernimmt dieser alle dafür
  zulässigen Bedienhandlungen. Eine zusätzliche persönliche Wiederholung ist nur
  nötig, wenn sie aus einer bestätigten Anforderung folgt.
- Synthetische Sandbox-Zahlungen sind von echten Zahlungen zu unterscheiden.
  Persönlicher OAuth-Consent ist kein Grund, auch alle nachfolgenden Testschritte
  dem Nutzer zuzuweisen.
- Bei unvermeidbaren persönlichen Aktionen einen vorbereiteten, kurzen
  Übergabepunkt verwenden statt vieler Bereitschafts- und Bestätigungsdialoge.
- Sicherheitszeitbudgets aus dem tatsächlichen Risiko ableiten. Sie dürfen nicht
  hauptsächlich die Antwortgeschwindigkeit des Nutzers testen. Eine notwendige
  Schutzgrenze wird nicht einfach verlängert oder abgeschaltet; stattdessen den
  Testablauf innerhalb des freigegebenen Rahmens vereinfachen.

## 5. Neuplanung proportional einsetzen

Ein lokaler Fehler oder eine operative Anpassung bleibt Ausführung, solange Ziel,
beobachtbares Verhalten und freigegebener Wirkungsrahmen unverändert bleiben.

Für eine tragende Architekturänderung oder eine materielle Scopeänderung bleibt
Neuplanung erforderlich. Ob dafür eine neue Nutzerfreigabe nötig ist, richtet
sich nach der tatsächlichen Entscheidung und den neuen Wirkungen, nicht allein
danach, dass ein neues Planartefakt entsteht. Unbekannte wesentliche Änderungen
werden nicht pauschal aus einer Zielsetzung autorisiert.

Agentenseitig eingeführte, nicht notwendige Prozessanforderungen zuerst auf
Vereinfachung prüfen. Bestätigte Nutzeranforderungen und Schutzgrenzen dabei
nicht stillschweigend streichen. Eine Dokumentaktualisierung allein erzeugt
weder neue Berechtigungen noch einen Produktnachweis.

## 6. Kleinste Änderung an den bestehenden Skills

Die gemeinsame Regel gehört zentral in
`core-shared/references/workflow-contract.md`, insbesondere in Autorisierung,
Scope, Ersatzplanung und Wiederaufnahme. Die anderen Skills verweisen darauf,
statt dieselbe Logik jeweils neu und möglicherweise strenger zu formulieren.

- `core-plan`: notwendige Test-/Recovery-Wirkungen vorab berücksichtigen;
  keine unbegründeten Genehmigungspunkte oder zusätzlichen Zielkriterien erfinden.
- `core-execute`: innerhalb des Rahmens bis zur fachlichen Verifikation handeln;
  nach einem Fehler nicht allein wegen des Fehlerstatus neue Freigaben verlangen.
- `core-review`: überflüssige Freigabeschleifen und nicht zielgebundene
  Prozessanforderungen ebenso prüfen wie fehlende Sicherheitsgrenzen.
- `core-debug`: einen minimalen Fix mit vorhandenen Regressionstests liefern;
  keine neue Diagnoseinfrastruktur als Standardreaktion.
- `core-milestone` und `core-handoff`: Originalkriterien und tatsächliche
  Autorisierung weitergeben; keine zusätzlichen Start- oder Bestätigungsformeln
  verlangen, wenn der laufende Auftrag die Fortsetzung eindeutig umfasst.

Keine neuen Schemas, Skills, Freigabe-Tools oder parallelen Statusquellen nötig.
Die vorhandenen Artefakte bleiben Nachweise, nicht Selbstzweck oder zusätzliche
Genehmigungsinstanz.

## Vorgeschlagener zentraler Regeltext

> Arbeite ein bestätigtes Ziel innerhalb seines ausdrücklich freigegebenen
> Wirkungs- und Risikorahmens eigenständig bis zur Verifikation ab. Diese
> Autorisierung umfasst auch notwendige Diagnose, lokale Fehlerbehebung,
> vereinbarte Tests sowie freigegebene Bereinigung und kontrollierte Recovery.
> Frage erneut nur nach einer materiell offenen Entscheidung, einer Wirkung
> außerhalb dieses Rahmens oder einer unvermeidbaren persönlichen Aktion.
> Ein Fehlversuch, ein neues internes Artefakt oder eine agentenseitig gewählte
> Prozessregel begründet allein keine neue Freigabepflicht. Erhalte Fehlerevidenz,
> prüfe sichere Fortsetzungsbedingungen und vereinfache unnötige Mechanik.
> Höherrangige Vorgaben und ausdrückliche Ausschlüsse bleiben verbindlich.

## Verhaltensprüfung vor einer tatsächlichen Skill-Änderung

Die Überarbeitung sollte an getrennten Vergleichsfällen geprüft werden:

- Freigegebener Stage-Test scheitert: Diagnose, eigene Testdaten bereinigen,
  kontrolliert fortsetzen, ohne neue Freigabeschleife.
- Dafür wäre erstmals ein Produktionseingriff nötig: konkret nachfragen.
- Kleiner Fix innerhalb bestehender Verträge: implementieren und prüfen,
  nicht neu planen.
- Änderung verlangt ein anderes Datenmodell oder neue erhebliche Kosten:
  Entscheidungsbedarf benennen und vor neuen Wirkungen klären.
- Nutzer delegiert Sandbox-Tests: Agent testet; nur echter persönlicher Consent
  wird übergeben.
- Sicherheitsstopp bei unklarer Integrität: sicher halten und Ursache prüfen;
  keinen ungeprüften Wiederanlauf aus einer allgemeinen Zielsetzung ableiten.
- Nutzer bricht ab: keine neue Arbeit beginnen.

Erfolg bedeutet weniger unnötige Rückfragen bei gleicher Zielerfüllung und
gleichen relevanten Schutzgrenzen. Das muss am beobachteten Agentenverhalten
belegt werden, nicht nur an kürzeren Skill-Dateien oder einer geänderten Prosa.

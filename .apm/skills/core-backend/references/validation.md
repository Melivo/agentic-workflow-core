# Backend-Validierung

Lade diese Referenz nur für neue oder geänderte Request-, Event-, Config-, Datei-, Provider- oder Serialisierungsgrenzen. Nutze das bestehende Schema-, Parser- und Fehlerkonzept des Projekts; Paketdefaults wählen keine Bibliothek und ändern keinen öffentlichen Vertrag.

## Grenzmodell

1. Bestimme Quelle, Vertrauensniveau und kanonische interne Repräsentation.
2. Validiere an der ersten zuständigen Grenze und übergib danach einen typisierten beziehungsweise eindeutig geprüften Wert.
3. Unterscheide:
   - syntaktische Validierung von Form, Typ, Format und Größe,
   - Domainvalidierung von Wertebereichen und Beziehungen,
   - Business-Regeln, die aktuellen autoritativen Zustand benötigen.
4. Erzwinge Business- und Persistenzintegrität zusätzlich dort, wo Race Conditions oder alternative Schreibpfade die Anwendungsvalidierung umgehen können.

## Regeln

- Leite Pflichtfelder, optionale Felder, Defaults, unbekannte Felder, Normalisierung und Fehlercodes aus dem bestehenden Vertrag ab.
- Normalisiere erst nach erfolgreicher struktureller Prüfung. Eine Normalisierung darf ungültige oder mehrdeutige Eingaben nicht stillschweigend gültig machen.
- Begrenze Größe, Tiefe, Anzahl, Zahlbereiche und Laufzeitkosten dort, wo Eingaben Ressourcenverbrauch steuern.
- Behandle IDs, Enums, Zeitwerte, Geldwerte, Locale, Encoding und Zeitzone explizit; rate keine Einheit oder Zeitzone.
- Verwende für partielle Updates eine eindeutige Semantik für „fehlt“, `null`, löschen und unverändert.
- Prüfe Provider- und Datenbankausgaben, wenn sie eine externe Vertrauensgrenze überschreiten oder ein öffentlicher Responsevertrag davon abhängt.
- Bewahre die projektspezifische Fehlerhülle. Fehler bleiben für den Aufrufer handlungsfähig, ohne sensible interne Details offenzulegen.

## Verifikation

Decke repräsentativ gültige Werte, Grenzwerte, fehlende und zusätzliche Felder, falsche Typen, ungültige Formate, Größenlimits und relevante Business-Regeln ab. Prüfe bei Zustandsänderungen, dass abgelehnte Eingaben keine partielle Nebenwirkung hinterlassen. Property- oder Fuzz-Tests sind nur dann erforderlich, wenn das Projekt sie nutzt oder der Parser-/Formatrisiko sie materiell rechtfertigt.

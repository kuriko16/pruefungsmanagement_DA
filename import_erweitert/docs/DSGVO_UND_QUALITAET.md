# DSGVO-Konzept und Datenqualität: Prüfungsdaten

> Entwurf für die Diplomarbeit. **Keine Rechtsberatung.** Konkrete Aufbewahrungsfristen und die Rechtsgrundlage legt die Schule fest (Direktion, Datenschutzbeauftragte:r). Wo hier eine Frist steht, ist sie als **offen** markiert und nicht geraten.

## 1. Welche Daten

| Kategorie | Beispiele | Herkunft | Schutzbedarf |
|---|---|---|---|
| Stammdaten Schüler:innen | Personen-ID, Name, Klasse | Sokrates | mittel |
| Anmeldedaten | Wahlfach, Schwerpunkt, DA-Titel, Betreuung | Anmelde-Excel | mittel |
| Prüfungsdaten | Noten, Prüfer:in, Beisitzer:in | Import und manuelle Eingabe | **hoch** (Leistungsbeurteilung) |
| Stammdaten Lehrpersonen | Personen-ID, Kürzel, Name | Schulverwaltung | niedrig bis mittel |
| Importprotokoll | Name oder ID plus Fehlertext | Import | mittel, enthält Personenbezug |

Es gibt **keine** besonderen Kategorien nach Art. 9 DSGVO. Religion als Wahlfach ist ein Grenzfall: Die Wahl kann Rückschlüsse auf ein Bekenntnis zulassen. Deshalb sollten nur Berechtigte diese Spalte sehen.

## 2. Grundsätze (Art. 5 DSGVO) und wie das System sie umsetzt

| Grundsatz | Umsetzung |
|---|---|
| Zweckbindung | Daten nur für die Organisation von Reife- und Diplomprüfung. Kein Export für andere Zwecke ohne Freigabe. |
| Datenminimierung | Der eduFLOW-Export enthält E-Mail, Geschlecht, Geburtsdatum und Formular-Zeitstempel. Diese Felder werden **nicht** übernommen (getestet). Unbekannte Spalten werden verworfen (R04). |
| Richtigkeit | 14 + 7 Prüfregeln, Abgleich über die Personen-ID, Fehlerprotokoll, Schutz manueller Korrekturen (Quellenspalte) |
| Speicherbegrenzung | Löschkonzept, siehe Abschnitt 4 |
| Integrität und Vertraulichkeit | Rollenrechte, Verschlüsselung, Protokollierung, siehe Abschnitt 3 |
| Rechenschaftspflicht | Eintrag im Verarbeitungsverzeichnis, Importprotokolle, Änderungsprotokoll |

**Rechtsgrundlage (Annahme, von der Schule zu bestätigen):** Art. 6 Abs. 1 lit. e DSGVO (öffentliche Aufgabe) in Verbindung mit dem Schulrecht. Eine Einwilligung ist nicht nötig und auch nicht passend, weil die Prüfung verpflichtend ist.

## 3. Speicherung und Verarbeitung

- **Speicherort:** nur auf Schul-Infrastruktur oder im Schul-Tenant (EU). Keine echten Daten auf privaten Rechnern, in Git-Repos oder in KI-Chats. Entwickelt und getestet wird nur mit `testdaten/`.
- **Rollen (Annahme):**

| Rolle | Darf |
|---|---|
| Administration / Sekretariat | Import starten, Protokoll lesen |
| Prüfungsvorsitz, Abteilungsvorstand | alles lesen, Prüfer/Beisitzer zuteilen |
| Prüfer:in | Noten der eigenen Prüfungen eintragen |
| Betreuer:in | eigene Diplomarbeitsteams lesen |
| Schüler:in | eigene Daten lesen (Auskunftsrecht) |

- **Technisch:** TLS für die Übertragung, verschlüsselte Datenbank oder verschlüsseltes Laufwerk, Backups ebenfalls verschlüsselt.
- **Änderungsprotokoll:** Jede manuelle Änderung an Note, Prüfer oder Beisitzer wird mit Zeit und Benutzer:in protokolliert. Heute gibt es nur `geaendert_am`; die Spalte für den Benutzer fehlt noch und ist ein offener Punkt für Sirins Modell.
- **Importprotokoll:** enthält Namen. Es wird wie die Prüfungsdaten behandelt und nach X Tagen gelöscht (offen, Vorschlag: nach Abschluss des Prüfungstermins).
- **Auftragsverarbeitung:** Läuft das System bei einem externen Anbieter, braucht es einen AV-Vertrag nach Art. 28.

## 4. Löschkonzept

| Daten | Löschen wann | Wie |
|---|---|---|
| Anmelde-Excel (Rohdatei) | nach erfolgreichem Import und Kontrolle | Datei aus Teams entfernen, Löschung dokumentieren |
| Importprotokolle | nach Abschluss des Haupttermins **plus** Nachtermin | automatischer Job |
| Anmeldedaten (Wahlfach usw.) | nach Ablauf der Einspruchsfrist | Job, danach nur noch Prüfungsergebnis |
| Noten und Prüfungsprotokolle | **gesetzliche Aufbewahrungsfrist, offen**, bei der Direktion erfragen | Archiv, nur lesend |
| Testdaten | keine Frist, erfunden | – |

Technisch: Ein Löschjob läuft regelmäßig, löscht nach Stichtag und schreibt einen Bericht, *was* gelöscht wurde (Anzahl, kein Inhalt). Backups laufen mit derselben Frist aus.

**Betroffenenrechte:** Auskunft (Art. 15) als Export der eigenen Daten. Berichtigung (Art. 16) über die manuelle Pflege, die vor Re-Importen geschützt ist. Löschung (Art. 17) gilt nur eingeschränkt, solange die gesetzliche Aufbewahrung läuft.

## 5. Datenqualitätsmetriken

Umgesetzt in `backend/qualitaet.py`. Jede Kennzahl ist ein Anteil von 0 bis 1.

| Dimension | Kennzahl | Formel | Zielwert (Vorschlag) |
|---|---|---|---|
| Vollständigkeit | Anmeldequote | Anmeldungen / Schüler:innen laut Sokrates | 1,0 vor Anmeldeschluss |
| Vollständigkeit | Pflichtfelder Anmeldung | gefüllte Pflichtfelder / (Anmeldungen × 6) | 1,0 |
| Vollständigkeit | Prüfungen komplett | Prüfungen mit Note, Prüfer und Beisitzer / alle Prüfungen | 1,0 vor Zeugnisdruck |
| Konsistenz | Prüfer ≠ Beisitzer | Prüfungen mit verschiedenen Personen / alle | 1,0 |
| Konsistenz | Betreuung gültig | DAs mit Betreuer:in in Stammdaten / alle DAs | 1,0 |
| Konsistenz | Noten nur für Angemeldete | Personen mit Noten **und** Anmeldung / Personen mit Noten | 1,0 |
| Aktualität | Alter letzter Import | heute − `MAX(importiert_am)` in Tagen | ≤ 7 Tage während der Anmeldephase |

Zusätzlich aus dem Protokoll: **Fehlerquote je Import** = Personen mit FEHLER / alle Personen in der Datei. Steigt sie, ist meist die Vorlage geändert worden.

**Beispiel mit den Dummy-Daten** (getestet): Die Anmeldequote ist niedrig, weil nur 9 von 24 Personen in Sokrates eine fehlerfreie Anmeldung haben. Die Pflichtfelder liegen bei 1,0. „Noten nur für Angemeldete“ liegt unter 1,0, weil die Notendatei auch Personen ohne gültige Anmeldung enthält. Genau das soll die Kennzahl sichtbar machen.

## 6. Offene Punkte

1. Aufbewahrungsfristen für Noten und Protokolle bei der Direktion klären.
2. Im aufbereiteten Langformat (5AHWIM) die Personen-ID-Spalte behalten. Der eduFLOW-Export hat sie, das Langformat derzeit nicht.
3. Benutzer-Spalte für das Änderungsprotokoll in Sirins Modell.
4. Wer darf die Spalte Wahlfach (Religion) sehen?

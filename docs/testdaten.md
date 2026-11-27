# Testdaten für Import und Oberfläche

Alle Namen, Personen-IDs, E-Mail-Adressen und Geburtsdaten sind **erfunden**. Die Schulkennzahl `900000` ist ebenfalls erfunden. Die Excel-Dateien sind **nicht** im Repository (`.xlsx` steht in `.gitignore`), das Skript erzeugt sie bei jedem Aufruf neu.

## Erzeugen und prüfen

```bash
python tools/demodaten.py --testfaelle
python backend/import_anmeldungen.py --jahr 2026/27 --db data/test.db --report data/fehlerbericht.md data/dummy/Dummy_Anmeldung_5AHWIM.xlsx data/dummy/Dummy_Anmeldung_5BHWII.xlsx data/dummy/Dummy_Anmeldung_5CHWIL.xlsx
python -m pytest tests -q
```

- `--testfaelle` schreibt `data/dummy/Dummy_Anmeldung_<Klasse>.xlsx` für 5AHWIM, 5BHWII und 5CHWIL. Der Zufalls-Seed ist fest (2026), damit alle dieselben Daten bekommen.
- `tests/test_testfaelle.py` prüft automatisch, dass jede Regel R01–R13 genau bei ihrer Personen-ID anschlägt und keine ungeplanten Meldungen entstehen.
- Ohne `--testfaelle` erzeugt das Skript wie bisher die Demodaten in `data/demo/` (mit `--db` auch gleich in die Datenbank).
- Vorhandene Testdateien und `data/test.db` werden dabei überschrieben. Löschen Sie `data/test.db` vor einem neuen Lauf, wenn Sie einen frischen Stand wollen.

## Testfälle: welche Personen-ID testet welche Regel

Jeder Fall ändert genau eine Zeile einer sonst fehlerfreien Klasse (R02: zwei Zeilen). „Zeile“ ist die Excel-Zeile im Blatt „Teilnehmer und Ergebnisse“.

| Regel | Schwere | Klasse | Zeile | Personen-ID | Testfall |
| --- | --- | --- | --- | --- | --- |
| R01 | Fehler | 5AHWIM | 3 | (leer) | Personen-ID fehlt |
| R02 | Fehler | 5AHWIM | 5 und 6 | 90000020000004 | Personen-ID doppelt |
| R03 | Warnung | 5AHWIM | 8 | 91000020000007 | ID beginnt mit 910000 statt Schulkennzahl 900000 |
| R04 | Warnung | 5AHWIM | 9 | 90000020000008 | Status „In Bearbeitung“ statt „Abgeschlossen“ |
| R05 | Fehler | 5AHWIM | 10 | 90000020000009 | Verbindliche Anmeldung „nein“ |
| R06 | Warnung | 5BHWII | 3 | 90000020000013 | Kenntnisnahme nächster Termin leer |
| R07 | Warnung | 5BHWII | 4 | 90000020000014 | Tippfehler in der Domain: `studnet.tgm.ac.at` |
| R08 | Hinweis | 5BHWII | 6 | 90000020000016 | Leerzeichen am Rand bei Nachname und Vorname |
| R09 | Fehler | 5BHWII | 8 | 90000020000018 | Klausurart passt nicht zur Zahl der Fächer |
| R10 | Warnung | 5CHWIL | 3 | 90000020000025 | Klasse „5CHWI“ passt nicht zum Dateinamen 5CHWIL |
| R11 | Warnung | 5CHWIL | 5 | 90000020000027 | Geburtsdatum im Blatt „Ergebnisse-Optionsfelder“ um einen Tag verschoben |
| R12 | Warnung | 5CHWIL | 7 | 90000020000029 | Betreuer\*in als „Nachname Vorname“, der Rest der Gruppe als „Vorname Nachname“. Gemeldet wird die ganze Gruppe mit diesem Titel. |
| R13 | Warnung | 5CHWIL | 9 | 90000020000031 | Titel der Diplomarbeit fehlt |

Ergebnis: 36 Zeilen gelesen, 31 importiert. Nicht importiert werden die Fälle R01, R02 (beide Zeilen), R05 und R09.
Die aktuelle Liste gibt `python tools/demodaten.py --testfaelle` auch selbst aus. Ändert sich der Generator, die Tabelle hier nachziehen.

## Format (wie der eduFLOW-Export)

- Eine Datei pro Klasse, die Klasse steht im Dateinamen.
- Blatt **„Teilnehmer und Ergebnisse“**, Kopfzeile in genau dieser Reihenfolge:
  `Nachname, Vorname, Klasse, Empfänger*in E-Mail, Personen-ID, Personentyp, Geschlecht, Geburtsdatum, Schulkennzahl, Status, Gesehen am, Ausgefüllt am, Klausurart, Ausbildungsschwerpunkt, Titel der Diplomarbeit:, Diplomarbeitsbetreuer*in:, PS_AM, PS_FT, PS_D_oder_E1, PS_Deutsch, PS_Englisch, PM_D, PM_E, PM_SPF, PM_WF_BI, PM_WF_LOG, PM_WF_MB, Kenntnisnahme nächster Termin, Verbindliche Anmeldung`
  **Achtung:** mit Sternchen, also `Empfänger*in E-Mail` und `Diplomarbeitsbetreuer*in:`. Ohne Sternchen findet der Import die Spalten nicht. In Markdown verschwinden die Sternchen leicht.
- Blatt **„Ergebnisse-Optionsfelder“** mit Nachname, Vorname, Personen-ID, Geburtsdatum (für R11).
- Personen-ID: 14 Ziffern, beginnt mit der Schulkennzahl `900000`. Personentyp `S`, Status `Abgeschlossen`, E-Mail `…@student.tgm.ac.at`.
- **3 schriftlich + 3 mündlich:** PS_AM, PS_FT, PS_D_oder_E1 (Deutsch oder Englisch). Mündlich PM_SPF, die andere Sprache in PM_D bzw. PM_E und das Wahlfach.
- **4 schriftlich + 2 mündlich:** PS_AM, PS_FT, PS_Deutsch, PS_Englisch. Mündlich PM_SPF und das Wahlfach.
- Wahlfach im Feld des Schwerpunkts, mit den Werten aus den echten Vorlagen:

| Klasse | Schwerpunkt | Feld | Wahlfächer |
| --- | --- | --- | --- |
| 5AHWIM | Maschinenbau | PM_WF_MB | Religion, Ethik, Naturwissenschaften, Geografie, Geschichte und Politische Bildung, Werkstoff- und Fertigungstechnik |
| 5BHWII | Betriebsinformatik | PM_WF_BI | Religion, Ethik, Naturwissenschaften, Geografie, Geschichte und Politische Bildung, Softwareentwicklung und Projektmanagement / Netzwerke und Embedded Software |
| 5CHWIL | Logistik | PM_WF_LOG | Religion, Ethik, Naturwissenschaften, Geografie, Geschichte und Politische Bildung, Logistik |

PM_SPF ist in allen Klassen „Betriebstechnik/Unternehmensführung und Wirtschaftsrecht“. Ethik ist in allen drei Klassen wählbar.

## Diplomarbeiten (JP-05) und Noten (JP-06): Formatvorschlag

Dummy-Daten für Diplomarbeiten oder Noten gibt es im Repository **noch nicht**, und auch kein festgelegtes Format. Damit Mikail den Import-Button vorbereiten kann, hier ein **Vorschlag**, abgestimmt auf `backend/schema.sql`. Bitte im Team bestätigen, bevor jemand darauf baut.

**JP-05 Diplomarbeiten:** Datei `Diplomarbeiten_<Klasse>.xlsx`, Blatt „Diplomarbeiten“, eine Zeile pro Kandidat\*in.

| Spalte | Pflicht | Ziel im Schema |
| --- | --- | --- |
| Personen-ID | ja (Schlüssel) | `anmeldung.personen_id` |
| Klasse | ja | Kontrolle gegen `klasse.name` |
| Titel der Diplomarbeit | ja | `diplomarbeit.titel` |
| Betreuer\*in | ja | `diplomarbeit.betreuer_text`, Abgleich mit `lehrperson` → `betreuer_id` nur wenn leer |
| Teamnummer | nein | gleiche Nummer = gleiche Diplomarbeit |

**JP-06 Noten:** Datei `Noten_<Klasse>.xlsx`, Blatt „Noten“, eine Zeile pro Kandidat\*in und Prüfung.

| Spalte | Pflicht | Ziel im Schema |
| --- | --- | --- |
| Personen-ID | ja (Schlüssel, zusammen mit Feld) | über `anmeldung` |
| Feld | ja | `pruefungsfach.feld`, z. B. `PS_AM`, `PM_WF_MB` |
| Jahresnote | nein | `pruefungsfach.note_jn` |
| Prüfungsnote | nein | `pruefungsfach.note_mp` |
| Gesamtnote | nein | `pruefungsfach.note_gn` |

Noten nur 1–5. Laut Schema werden die Noten manuell gepflegt. Ein Notenimport darf deshalb nur **leere** Felder füllen und nichts überschreiben, was in der Oberfläche eingetragen wurde.

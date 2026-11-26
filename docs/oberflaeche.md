# Weboberfläche (MVP) – Teil Mikail Simsek

Lokale Weboberfläche auf Basis des gemeinsamen SQLite-Schemas (`backend/schema.sql`) und des
bestehenden Imports (`backend/import_anmeldungen.py`). Läuft nur lokal, keine Cloud.

## Starten

**Am einfachsten (Windows/Mac):** Doppelklick auf `START_Windows.bat` bzw. `START_Mac.command`
(oder im Terminal `python start.py`). Beim ersten Mal wird eine eigene Python-Umgebung angelegt
und Flask/openpyxl installiert (braucht einmal Internet), dann werden Demodaten geladen und der
Browser öffnet http://localhost:8080. Voraussetzung: Python 3.10+ von python.org.

Demodaten neu erzeugen: `Demo_zuruecksetzen_Windows.bat` bzw. `python start.py --reset`.

**Mit Docker:** `docker compose up --build` → http://localhost:8080 (lädt beim ersten Start Demodaten).

**Händisch:** `pip install -r requirements.txt`, `python tools/demodaten.py --db`, `python webapp/app.py`.

Tests: `python -m pytest tests -q`

## Seiten

| Seite | Was man dort macht | User Story |
| --- | --- | --- |
| Dashboard | Stand pro Klasse: fehlende Prüfer:innen, Beisitz, Prüfungstage, Noten, Fortschritt, Notenverteilung, letzte Importe | MS-09 |
| Kandidat:innen | Liste mit Suche (Name, Personen-ID) und Filter nach Klasse, Fach, Lehrperson, „nur offene“ | MS-08 |
| Kandidat (Detail) | Stammdaten bearbeiten, DA-Betreuung aus Stammdaten wählen, pro Fach Prüfer:in, Beisitz, Prüfungstag, JN/MP/GN eintragen, Anmeldung löschen; Import-Meldungen zur Person werden angezeigt | MS-02, MS-03, MS-04, MS-06 |
| Zuweisung | Pro Klasse und Fach Prüfer:in, Beisitz und Prüfungstag für alle auf einmal setzen | MS-02, MS-03 |
| Lehrpersonen | Stammdaten anlegen, deaktivieren, löschen (nur ohne Zuweisungen) | SB-04 |
| Import | eduFLOW-Anmeldungen hochladen, Prüfprotokoll R01–R13 wird angezeigt | MS-07, JP-01, JP-07 |
| Export Excel | „Übersicht Reife- und Diplomprüfung“ im Aufbau der Vorlage, ein Blatt pro Klasse | MS-07, UE-05 |

## Änderungen an gemeinsamen Dateien

- `backend/import_anmeldungen.py`: Ein erneuter Import löscht die Prüfungsfächer nicht mehr,
  sondern gleicht sie ab. Prüfer:innen, Tage und Noten aus der Oberfläche bleiben dadurch erhalten
  (war im README als bekannte Lücke vermerkt). Die Importlogik pro Datei steckt jetzt in
  `importiere_datei()`, damit Kommandozeile und Oberfläche denselben Code verwenden.
  Die Klasse wird jetzt auch aus den Original-Dateinamen („… HWI 5BHWII.xlsx“) erkannt.
- Schema: Die Oberfläche ergänzt `pruefungsfach.pruefungstag` und `pruefungsfach.note_jn`
  automatisch (siehe `webapp/db.py`). Vorschlag an Sirin: fix in `schema.sql` übernehmen.

## Datenschutz

`tools/demodaten.py` erzeugt Dateien im eduFLOW-Format mit erfundenen Namen, Schulkennzahl 900000.
Echte Anmeldedateien, die Datenbank und Excel-Dateien sind per `.gitignore` ausgeschlossen.
Hochgeladene Dateien werden nur kurz zwischengespeichert und gleich wieder gelöscht.

## Offen / nächste Schritte

- Themengebiete pro Fach pflegen (MS-05)
- Notenberechnung (JN/MP → GN) sobald die Formel mit Herrn Angerer erhoben ist (SB-06)
- Druck-Button an Yilmaz' PDF-Erstellung anbinden (MS-07/YY-05), Export ggf. auf seinen Code umstellen
- Button für Klentis Zeitplan, sobald der Algorithmus steht (KZ-02); die Prüfungstage aus der Oberfläche sind dafür die Eingabe
- PWA (installierbar), Benutzerrollen (MS-10), Kopfdaten pro Klasse (Vorsitz, Jahrgangsvorstand)

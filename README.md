# Prüfungsmanagementsystem – Projektgerüst (Startpunkt)

Dieses Gerüst ist ein Vorschlag zum Weiterbauen, keine fertige Lösung. Es soll uns schnell
einen gemeinsamen Ausgangspunkt geben: ein Datenbankschema (Entwurf für Sirin) und einen
Import-Prototyp (Startpunkt für Julian), der die eduFLOW-Anmeldedateien einliest.

## Ordner

| Ordner / Datei | Inhalt |
| --- | --- |
| `backend/schema.sql` | Datenmodell v0 in SQLite (Kandidat, Anmeldung, Prüfungsfach, Diplomarbeit, Lehrperson, Klasse, Prüfungsjahr, Importprotokoll) |
| `backend/import_anmeldungen.py` | Liest die Anmelde-Excel, prüft sie (Regeln R01 bis R13), schreibt in die Datenbank und erstellt ein Fehlerprotokoll |
| `data/input/` | Hier die Excel-Dateien ablegen. **Nicht ins Repository einchecken** (personenbezogene Daten) |
| `docs/` | Platz für Analyse, ER-Diagramm, User Stories. Enthält `user_stories.csv` (48 Anforderungen) und `github-setup.md` (Anleitung für Repository und Project) |
| `webapp/` | Weboberfläche (Flask): Dashboard, Kandidat:innen, Zuweisung, Noten, Import, Export. Anleitung: `docs/oberflaeche.md` |
| `tools/demodaten.py` | Erzeugt erfundene Anmeldedateien im eduFLOW-Format für Demo und Tests. Mit `--testfaelle` mindestens ein Testfall je Prüfregel R01–R13, Liste in `docs/testdaten.md` |
| `tools/create_github_issues.py` | Legt Labels, Meilensteine und Issues aus `docs/user_stories.csv` in GitHub an (zuerst Probelauf) |

## Ausprobieren

Voraussetzung: Python 3.10 oder neuer und `pip install openpyxl`.

```bash
cd backend
python import_anmeldungen.py --jahr 2025/26 --db ../data/pruefung.db \
    --report ../data/fehlerbericht.md ../data/input/*.xlsx
```

Das Skript kann mehrfach laufen: Kandidaten, Anmeldungen und Fächer werden aktualisiert statt doppelt angelegt.

## Prüfregeln

| Regel | Schwere | Prüfung |
| --- | --- | --- |
| R01 | Fehler | Personen-ID fehlt |
| R02 | Fehler | Personen-ID kommt mehrfach vor |
| R03 | Warnung | ID nicht 14 Ziffern oder beginnt nicht mit der Schulkennzahl |
| R04 | Warnung | Status ist nicht „Abgeschlossen" |
| R05 | Fehler | Anmeldung nicht verbindlich bestätigt |
| R06 | Warnung | Kenntnisnahme des nächsten Termins fehlt |
| R07 | Warnung | E-Mail-Domain weicht von `student.tgm.ac.at` ab |
| R08 | Hinweis | Leerzeichen am Rand eines Werts |
| R09 | Fehler | Zahl der Prüfungsfächer passt nicht zur gewählten Klausurart |
| R10 | Warnung | Klasse in der Datei passt nicht zum Dateinamen |
| R11 | Warnung | Geburtsdatum unterscheidet sich zwischen den beiden Blättern |
| R12 | Warnung | Gleicher Titel, Betreuer*in in unterschiedlicher Schreibweise |
| R13 | Warnung | Titel der Diplomarbeit fehlt |

Datensätze mit Schwere „Fehler" werden nicht importiert, alle anderen schon.

Testdaten mit einem Fall je Regel: `python tools/demodaten.py --testfaelle`, siehe `docs/testdaten.md`. `tests/test_testfaelle.py` prüft automatisch, dass jede Regel anschlägt.

## Bekannte Lücken

- Prüfer, Beisitzer, Prüfungstage und Noten werden über die Weboberfläche gepflegt und bleiben bei erneutem Import erhalten.
- Betreuer*innen werden nur als Text gespeichert, noch nicht mit den Lehrpersonen-Stammdaten verknüpft.
- Der Import der Diplomarbeitsdaten aus den separaten Excel-Dateien und der Noten fehlt noch.
- Weboberfläche (MVP) und Docker-Start: siehe `docs/oberflaeche.md`.
- Das Prüfungsjahr wird per Parameter angegeben, die Beispieldateien stammen aus dem Anmeldezeitraum November 2025.

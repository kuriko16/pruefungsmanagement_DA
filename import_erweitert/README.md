# import_erweitert: Erweiterung des Imports (Julian)

> **Stand: parallel zum Prototyp, noch nicht integriert.** Entstanden, bevor das Repository lokal vorlag.
> Der Team-Prototyp `backend/import_anmeldungen.py` und das Schema `backend/schema.sql` bleiben unverändert.
> Nächster Schritt: die Erweiterungen unten in den Prototyp übernehmen und ins Schema von Sirin schreiben.

**Was hier neu ist gegenüber dem Prototyp:**
- Abgleich der Betreuer:innen mit den Lehrpersonen-Stammdaten (Vorname Nachname / Nachname Vorname / mit Komma / mit Titel), mehrdeutige Namen werden abgelehnt statt geraten
- Abgleich mit Sokrates über die Personen-ID, inklusive Prüfung, ob Name und Klasse zur ID passen
- Fachregeln je Klasse aus den echten Vorlagen: Schwerpunkt, Wahlfach-Feld, erlaubte Wahlfächer, Sprachkombination 3+3 / 4+2 (`backend/fachkonfig.py`)
- Import von Noten mit eigenen Prüfregeln, manuell gepflegte Note/Prüfer/Beisitzer bleiben beim Re-Import erhalten
- Liest den eduFLOW-Export **und** das Langformat (Feld/Wert)
- Datenminimierung: E-Mail, Geschlecht, Geburtsdatum werden nicht übernommen
- Datenqualitätsmetriken, DSGVO-Konzept, 29 Tests mit erfundenen Daten, Vorführskripte

**Aufgefallen im Prototyp:** In `main()` steht `len(rows)`, `rows` ist dort aber nicht definiert. Der Aufruf über die Kommandozeile bricht deshalb nach der ersten Datei mit einem NameError ab. Die Weboberfläche ist nicht betroffen, weil sie `importiere_datei()` direkt aufruft.

---

# Diplomarbeit: Importsystem Anmeldungen und Zeugnisdaten

Teil von Julian (Import). Das Datenmodell gehört Sirin. `backend/ziel_db.py` enthält nur ein **angenommenes** Schema zum Testen.
Abteilung Wirtschaftsingenieure: 5AHWIM (Maschinenbau), 5BHWII (Betriebsinformatik), 5CHWIL (Logistik).

| Ordner/Datei | Inhalt |
|---|---|
| `backend/import_anmeldungen.py` | Import (eduFLOW-Export und Langformat), 14 Anmelde-Regeln + 7 Noten-Regeln, Fehlerprotokoll, CLI |
| `backend/fachkonfig.py` | Klassen, Fächer, Wertelisten aus den echten Teams-Vorlagen |
| `backend/normalisierung.py` | Namen und Klassen vergleichbar machen |
| `backend/ziel_db.py` | alles SQL, Schutz manueller Werte |
| `backend/qualitaet.py` | Kennzahlen Vollständigkeit, Konsistenz, Aktualität |
| `tests/test_import.py` | automatische Tests mit erfundenen Daten |
| `testdaten/` | 3 Klassendateien im eduFLOW-Aufbau, eine Datei im Langformat, Stammdaten, Noten, `FEHLERFAELLE.md`, `STRUKTUR.md` |
| `demo.py` / `eingabe.py` / `zeige_ergebnis.py` | Vorführung, Live-Eingabe, Ergebnis als Excel |
| `docs/` | Erklärung, DSGVO-Konzept, Drehbuch, Befehlsliste |

## Benutzen (im Ordner `import_erweitert`)

```bash
python demo.py
```

```bash
python -m unittest discover -s tests -t . -v
```

```bash
python -m backend.import_anmeldungen --db ergebnisse/pruefung.sqlite --lehrpersonen testdaten/lehrpersonen_dummy.csv --sokrates testdaten/sokrates_export_dummy.csv --anmeldung testdaten/anmeldung_5AHWIM.xlsx testdaten/anmeldung_5BHWII.xlsx testdaten/anmeldung_5CHWIL.xlsx --noten testdaten/noten_dummy.csv --protokoll ergebnisse/protokoll.csv
```

Testdaten neu erzeugen: `python testdaten/erzeuge_dummy.py`. Voraussetzung: Python 3.10+ und `openpyxl`. Keine echten Schülerdaten in diesen Ordner legen.

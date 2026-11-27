# So funktioniert der Import, Block für Block

Datei: `backend/import_anmeldungen.py`. Die Hilfsdateien:
- `fachkonfig.py`: Klassen, Fächer, Wertelisten
- `normalisierung.py`: Namen vergleichbar machen
- `ziel_db.py`: alles SQL
- `qualitaet.py`: Kennzahlen

## 1. Der Weg einer Zeile

```
3 Klassendateien (eduFLOW-Export      Lehrpersonen.csv    Sokrates.csv
oder Langformat)                             │                  │
      │                                      └────────┬─────────┘
      ▼                                               ▼
lies_anmeldung()  ── R01, R04, R08 ──▶  Person-Objekte   lade_stammdaten()
      │
      ▼
pruefe_person()   ── R02, R03, R05–R07, R09–R12, R14 ──▶ Protokoll
pruefe_teams()    ── R13 (auch über Klassen hinweg)
      │  nur Personen ohne FEHLER
      ▼
speichere_diplomarbeit() + speichere_anmeldung()

noten.csv ── importiere_noten() ── N01–N06 ──▶ importiere_pruefungswerte()  (N07: manuelle Werte bleiben)
```

## 2. Die Blöcke im Einzelnen

**`fachkonfig.py`.** Hier stehen die Fachregeln als Daten, übernommen aus den echten Teams-Vorlagen:
- die drei Klassen mit Schwerpunkt, eigenem Wahlfach-Feld (`PM_WF_MB`, `PM_WF_BI`, `PM_WF_LOG`) und erlaubten Wahlfächern
- die beiden Prüfungsvarianten (3 schriftlich + 3 mündlich oder 4 + 2)
- die Prüfungsteile

Kommt ein Wahlfach dazu, wird nur diese Datei geändert.

**`Meldung` und `Protokoll`.** Jede Auffälligkeit wird eine Zeile mit Regel, Stufe, Datei, Excel-Zeile, Person und Text. Stufen:
- `FEHLER`: Die Person wird nicht importiert.
- `WARNUNG`: Die Person wird importiert, aber jemand sollte hinschauen.
- `INFO`: nur ein Hinweis.

**`Person`.** Eine Anmeldung, wie sie aus der Datei kommt: Name, Klasse, Personen-ID, Formular-Status und die Antworten als Wörterbuch `werte`.

**`lies_anmeldung()`.** Öffnet das Blatt „Teilnehmer und Ergebnisse“ und erkennt das Format an den Überschriften:
- **eduFLOW-Export (breit):** eine Zeile pro Person, jede Antwort hat eine eigene Spalte. So kommt die Datei aus dem Formular.
- **Langformat:** Spalten `Feld` und `Wert`, eine Zeile pro Person und Feld. So ist die 5AHWIM-Datei in Teams aufbereitet.

Spalten werden **über ihre Überschrift** gesucht, nicht über ihre Position. Unbekannte Spalten ergeben eine Warnung (R04). E-Mail, Geschlecht und Geburtsdatum werden absichtlich nicht gelesen. `finally: wb.close()` gibt die Datei unter Windows wieder frei.

**`pruefe_person()`.** Prüft eine Person mit allen Einzelregeln, siehe Tabelle unten. Dabei werden `klasse`, `sokrates_id` und `betreuer_id` gesetzt.

**`pruefe_teams()`.** Alle fehlerfreien Personen mit gleichem Diplomarbeitstitel bilden ein Team. Das Team braucht dieselbe Betreuung und darf höchstens 4 Personen haben.

**`importiere_anmeldungen()`.** Liest eine **oder mehrere** Klassendateien und prüft alle gemeinsam. So fällt auch auf, wenn dieselbe Person in zwei Dateien angemeldet ist.

**`anmeldedaten()`.** Übersetzt die Formularfelder in die Zielspalten. Ein Beispiel: Aus `PM_WF_MB`, `PM_WF_BI` oder `PM_WF_LOG` wird immer die eine Spalte `wahlfach`.

**`finde_lehrperson()`.** Der Name wird in Wörter ohne Titel zerlegt. Er passt, wenn er `Nachname + Vorname` oder `Vorname + Nachname` ergibt. Mit Komma gilt nur `Nachname, Vorname`. Bei mehreren Treffern wird **nicht geraten** (R12).

**`importiere_noten()`.** Jede CSV-Zeile durchläuft N01–N06. Nur fehlerfreie Zeilen gehen an `db.importiere_pruefungswerte()`.

**`importiere_alles()`.** Läuft als eine Transaktion. Stürzt etwas ab, wird mit `rollback()` nichts halb geschrieben.

## 3. Die 14 Prüfregeln für Anmeldungen

| Regel | Prüft | Stufe |
|---|---|---|
| R01 | Blatt und Pflichtspalten vorhanden, Format erkennbar | FEHLER, ganze Datei |
| R02 | Nachname und Vorname nicht leer | FEHLER |
| R03 | Klasse ist 5AHWIM, 5BHWII oder 5CHWIL; „5 b hwii“ wird korrigiert | WARNUNG wenn korrigierbar, sonst FEHLER |
| R04 | Spalte oder Feld bekannt | WARNUNG, wird ignoriert |
| R05 | Pflichtfelder gefüllt, **abhängig von Klasse und Prüfungsvariante** | FEHLER |
| R06 | Wert erlaubt: Klausurart, Schwerpunkt passt zur Klasse, Wahlfach aus der Liste der Klasse, kein Wahlfach-Feld einer anderen Klasse | FEHLER |
| R07 | Verbindliche Anmeldung = „ja“ und Formular-Status = „Abgeschlossen“ | FEHLER |
| R08 | Person nicht doppelt (in einer Datei oder in mehreren) | FEHLER |
| R09 | Person in Sokrates gefunden, über die Personen-ID oder über Name + Klasse | FEHLER |
| R10 | Personen-ID passt zu Name und Klasse in Sokrates bzw. Treffer eindeutig | FEHLER |
| R11 | Betreuer:in in Stammdaten gefunden | FEHLER |
| R12 | Betreuer:in eindeutig | FEHLER |
| R13 | Team: gleiche Betreuung, höchstens 4 Personen | FEHLER |
| R14 | Sprachen passen zur Variante: bei 3+3 mündlich die andere Sprache, bei 4+2 Deutsch und Englisch schriftlich | FEHLER |

Regeln für die Noten:
- N01 Personen-ID bekannt
- N02 Prüfungsteil bekannt (PS_AM, PS_D, PS_E, PS_FT, PM_DA, PM_SPF, PM_D, PM_E, PM_WF)
- N03 Note ganzzahlig 1–5
- N04 Kürzel bekannt
- N05 Prüfer:in ≠ Beisitzer:in
- N06 kein Duplikat
- N07 (INFO) manueller Wert geschützt

## 4. Schutz manueller Daten

Jedes schützbare Feld (`note`, `pruefer_id`, `beisitzer_id`) hat eine Spalte `quelle_…` mit dem Wert `import` oder `manuell`.
- Die Oberfläche schreibt über `manuell_setzen()`. Dabei wird die Quelle auf `manuell` gesetzt.
- Der Import überschreibt nur Werte mit der Quelle `import` oder leere Werte. Weicht ein geschützter Wert ab, steht im Protokoll die Meldung N07.
- Ein zweiter Import mit denselben Dateien ändert nichts. Das nennt man idempotent, und es ist getestet.

**Warum das so gebaut ist:** Würde der Import „nur leere Felder füllen“, blieben Tippfehler aus dem ersten Import für immer stehen. Mit der Quellenspalte darf der Import seine eigenen Fehler korrigieren, aber nie die Arbeit eines Menschen überschreiben.

## 5. Abgleich mit Sokrates

Der eduFLOW-Export enthält die **Personen-ID**. Damit wird direkt in Sokrates gesucht. Zusätzlich wird geprüft, ob Name und Klasse dazu passen, normalisiert („Oeztuerk“ = „Öztürk“). Passt die ID zu einer anderen Person, greift R10. Das fängt Tipp- und Kopierfehler ab.
Fehlt die ID, etwa im Langformat ohne ID-Spalte, läuft der Abgleich über Name + Klasse. Bei Namensgleichheit in einer Klasse greift R10.

## 6. Anpassen an Sirins Datenmodell

Nur `backend/ziel_db.py` ändern: das Schema löschen und die SQL-Befehle in den Methoden auf ihre Tabellen umstellen. Die Methodennamen bleiben gleich, dann laufen Import und Tests unverändert weiter.

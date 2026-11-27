# Vorführung: Drehbuch (ca. 10 Minuten)

## Vorher (5 Minuten, vor der Stunde)

1. Ordner `import_erweitert` im Explorer öffnen, in die Adresszeile `powershell` tippen, Enter.
2. Probelauf: `python demo.py --ohne-pause`. Bricht nichts ab, ist alles bereit.
3. `python zeige_ergebnis.py` ausführen (Excel muss dabei geschlossen sein).
4. Terminal-Schrift größer machen (Strg + Mausrad), damit man es am Beamer lesen kann.

## Ablauf

| # | Du tust | Du sagst (Kernaussage) |
|---|---|---|
| 0 | `testdaten/anmeldung_5BHWII.xlsx` kurz zeigen | „Das ist genau der Aufbau unseres eduFLOW-Exports, mit den echten Fächern aus den drei Klassen. Nur die Personen sind erfunden.“ |
| 1 | `python demo.py`, Enter | „Zuerst lade ich die Stammdaten: Lehrpersonen und den Sokrates-Export mit Personen-IDs.“ |
| 2 | Enter | „Alle drei Klassen auf einmal, jede Anmeldung mit 14 Regeln geprüft. Rot heißt nicht importiert, Gelb heißt importiert mit Hinweis.“ Zeig auf **Öztürk Deniz**: „Hier rät das System nicht, es lehnt ab.“ Zeig auf **Moser**: „Die Personen-ID gehört jemand anderem, das wird erkannt.“ |
| 3 | Enter | „Betreuer stehen in verschiedenen Schreibweisen drin, alle werden richtig zugeordnet. Ahorn und Birkner sind ein Team, obwohl die Betreuerin einmal anders geschrieben ist.“ |
| 4 | Enter | „Auch Noten werden geprüft: Note 6, Text statt Zahl, unbekannte ID, Prüfer gleich Beisitzer, unbekanntes Fach.“ |
| 5 | Enter | **Wichtigster Punkt:** „Eine Lehrerin korrigiert eine Note von Hand. Danach wird neu importiert, und die Korrektur bleibt.“ |
| 6 | Enter | „Kennzahlen zur Datenqualität. Die Anmeldequote ist niedrig, weil ich absichtlich viele Fehler eingebaut habe.“ |
| 7 | `start ergebnisse\ergebnis_dummy.xlsx` | „Das Protokoll gibt es auch als Excel, fürs Sekretariat.“ |
| 8 | `python -m unittest discover -s tests -t . -v` | „Automatische Tests prüfen das bei jeder Änderung.“ |

## Fehler live eintippen

`python eingabe.py`, dann `a` für eine Anmeldung oder `n` für eine Note.
Zu jeder Frage steht ein gültiger Vorschlag in Klammern. **Enter** übernimmt ihn, eine eigene Eingabe ersetzt ihn, `-` lässt das Feld leer. Geprüft wird erst, wenn alle Fragen beantwortet sind.

Einmal alles mit Enter → **OK**. Danach **ein** Feld falsch eingeben:

| Eingabe | Ergebnis |
|---|---|
| Klasse `5 a hwim` | WARNUNG R03, korrigiert |
| Klasse `5DHWIL` | FEHLER R03, Klasse gibt es nicht |
| Klasse `5BHWII` (bei Birkner) | FEHLER R10, Birkner ist laut Sokrates in 5AHWIM |
| Vorname `Hans` | FEHLER R10, ID gehört Jonas Birkner |
| Personen-ID `99990000000555` | FEHLER R09, nicht in Sokrates |
| Klausuren `4` | OK, Variante 4 schriftlich + 2 mündlich |
| Sprache mündlich = schriftlich (z. B. beide `Englisch`) | FEHLER R14 |
| Schwerpunkt `Logistik` (in 5AHWIM) | FEHLER R06 |
| Betreuer `Lukas Martin` | FEHLER R12, mehrdeutig |
| Betreuer `Aigner, Theresa` oder `Prof. Theresa Aigner` | OK, wird erkannt |
| Wahlfach `Kochen` | FEHLER R06 |
| Verbindliche Anmeldung `-` | FEHLER R05 |
| Status `In Bearbeitung` | FEHLER R07 |
| Note `6` oder `gut` | FEHLER N03 |
| Prüfungsteil `Turnen` | FEHLER N02 |
| Prüfer und Beisitzer beide `AIG` | FEHLER N05 |

`h` zeigt alle gültigen Namen, IDs, Wahlfächer je Klasse und Kürzel. `q` beendet. Gespeichert wird nichts.

## Live-Test mit Excel

1. `python demo.py --live` legt `ergebnisse/demo_live_5BHWII.xlsx` an.
2. Die Datei in Excel öffnen und einen Fehler einbauen lassen, z. B. ein Wahlfach auf „Kochen“ setzen.
3. **Speichern und Excel schließen.**
4. `python demo.py --live` noch einmal starten. Der neue Fehler steht in Schritt 2 bei 5BHWII.

## Fragen, die kommen können

- **„Woher kommen die Regeln?“** Aus den echten Vorlagen in Teams: Spaltenzuordnung, Optionenwahl und Export-Übersicht. Der Abgleich mit der Anforderungserhebung steht noch aus.
- **„Warum werden Geschlecht und Geburtsdatum nicht übernommen?“** Datenminimierung nach DSGVO. Für die Prüfung braucht man sie nicht.
- **„Und Sirins Datenbank?“** Alles SQL steht in `backend/ziel_db.py`. Wenn ihr Modell fertig ist, wird nur diese Datei angepasst.
- **„Hast du das allein programmiert?“** Ehrlich sagen: mit KI-Unterstützung. Meine Arbeit war Analyse, Abgrenzung, Testfälle, Prüfen und die Entscheidungen.

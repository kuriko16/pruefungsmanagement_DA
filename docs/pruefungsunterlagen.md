# Prüfungsunterlagen – Yilmaz Yükseloglu

## Start und Vorführung

Im Projektordner (dort liegt start.py):

```bash
python start.py
```

Danach http://localhost:9094 öffnen und oben **Prüfungsunterlagen** anklicken.
Prüfungsjahr 2026/27 oder 2025/26 auswählen. Für den Zeitplan eine einzelne Klasse wählen.

- **RDP-Übersicht → Excel herunterladen:** füllt die echte Übersichtsvorlage mit vorhandenen Daten.
- **Zeitplan → Excel-Vorlage herunterladen:** öffnet die bereinigte zweite Schulvorlage zum Ausfüllen.
- **Prüfungszettel / Kommissionsübersicht → PDF öffnen / drucken:** erzeugt PDFs aus denselben Datenbankdaten.
- Drucken erfolgt im PDF-Fenster über das Druckersymbol oder Strg+P.
- PDF-Kopien der beiden Excel-Vorlagen benötigen lokal installiertes LibreOffice. Es wird automatisch erkannt; alternativ PM_SOFFICE auf die ausführbare soffice-Datei setzen. Die beiden anderen PDF-Buttons benötigen nur ReportLab.

start.py aktualisiert die Pakete automatisch, wenn requirements.txt geändert wurde.
Wer die bestehende Python-Umgebung direkt verwendet, kann zuerst `python -m pip install -r requirements.txt` ausführen.
Keine Datenbank zurücksetzen: `--reset` wird für dieses Update nicht gebraucht.

## Aufbau

| Datei | Aufgabe |
| --- | --- |
| backend/dokumente/daten_lesen.py | Liest vorhandene Daten pro Prüfungsjahr und Klasse. Kein Import, keine Datenänderung. |
| backend/dokumente/vorlagen.py | Wählt die Vorlagenversion für ein Prüfungsjahr aus. |
| backend/dokumente/excel_erstellen.py | Füllt die RDP-Vorlage und liefert die Zeitplan-Leervorlage. |
| backend/dokumente/pdf_export.py | Erzeugt PDF-Unterlagen und konvertiert Excel lokal mit LibreOffice. |
| webapp/dokumente_routen.py | Verbindet die Buttons mit der Dokumenterstellung. |
| webapp/templates/dokumente.html | Seite mit Klassen-/Versionsauswahl und Download-Buttons. |
| vorlagen/2026_27/v1/ | Versionierte, bereinigte Kopien der beiden bereitgestellten Schulvorlagen. |

Die Dateien für 2025/26 liegen entsprechend unter vorlagen/2025_26/v1/.
Die ursprünglichen Dateien mit eingetragenen Namen werden nicht mitgeliefert.
Die gespeicherten Vorlagen bleiben beim Export unverändert; jedes Ergebnis entsteht im Arbeitsspeicher.

## Was bereits funktioniert

- RDP-Matrix: eine Zeile pro Person, schriftliche und mündliche Fächer, DA-Gruppen, manuell zugewiesene Betreuung.
- Zusätzliche Wahlfächer erhalten eigene Spalten; vorhandene Fachspalten bleiben erhalten.
- Ein Detailblatt zeigt Person, Fach, Prüfer, Beisitz und vorhandene Noten eindeutig, auch bei mehreren Prüfern für dasselbe Fach.
- Personen werden über IDs unterschieden, auch bei gleichen Namen.
- MP, GN und Betreuung werden übernommen, nicht berechnet oder aus Rohwerten geraten.
- Downloads berücksichtigen nur das ausgewählte Prüfungsjahr und die gewählte Klasse.
- Bestehender Link /export/uebersicht führt ebenfalls zur neuen Vorlagenausgabe.

## Grenzen des aktuellen Datenmodells

Im vorläufigen Schema fehlen Beginnzeiten, Dauer, Raum, Aufsichten und eine Terminzuordnung für die NT-Blätter.
Der Zeitplan bleibt daher ein Leerformular mit eurer ursprünglichen Blattstruktur, Spalten, Druckbereichen und Zeitformeln.
Die Zeitformeln rechnen erst weiter, sobald ein Beginn und eine Dauer eingetragen wurden.
Klenti liefert später die geplanten Werte; Yilmaz übernimmt nur deren Ausgabe.

Die RDP-Ausgabe befüllt die drei Hauptblätter, nicht die NT-Blätter. Letztere bleiben in der Vorlagendatei erhalten.
Vorsitz und Jahrgangsvorstand sind in den Ausgaben noch manuell zu ergänzen.
Eine Zulassung und ein Kompensationsbedarf werden nicht aus Anmeldungen oder MP=5 abgeleitet.
Die Zählformel berücksichtigt X und XV; XV wird ohne bestätigte Datenquelle nicht automatisch gesetzt.

Die beiden allgemeinen PDF-Formulare sind als Entwurf gekennzeichnet, weil dafür noch keine freigegebenen Vorlagen vorliegen.
Word-Serienbriefe werden ergänzt, sobald die Word-Vorlagen vorhanden sind.
Wenn sich Sirins Datenmodell ändert, muss hauptsächlich lade_dokumentdaten() angepasst werden.

## Neue Vorlagenversion

Bestehende v1-Dateien nicht überschreiben. Für ein neues Jahr den bereinigten v1-Ordner in einen neuen Jahresordner kopieren und version.json anpassen.
Für ein neues Layout einen v2-Ordner anlegen. Die Weboberfläche bietet vorhandene Versionen zur Auswahl an.
Alternativ können die beiden ursprünglichen Schuldateien mit tools/vorlagen_vorbereiten.py bereinigt werden:

```bash
python tools/vorlagen_vorbereiten.py --uebersicht "Pfad/zur/Uebersicht.xlsx" --zeitplan "Pfad/zum/Zeitplan.xlsx" --jahr 2027/28 --version 1
```

Dieses Hilfsskript ist auf die zwei bereitgestellten Layouts zugeschnitten. Bei anderen Layouts muss die Auswahl der erhaltenen Beschriftungen geprüft werden.

## Prüfung

```bash
python -m pytest tests -q
```

Die Tests verwenden ausschließlich erfundene Daten. Sie prüfen unter anderem Jahresgrenzen, doppelte Namen, manuelle Betreuung, zusätzliche Fächer, lange Klassenlisten und Excel-Formelsicherheit.

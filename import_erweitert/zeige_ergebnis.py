"""Führt den Import mit den Dummy-Daten aus und schreibt alles in eine Excel-Datei.

Aufruf (im Ordner import_erweitert):  python zeige_ergebnis.py
Ergebnis: ergebnisse/ergebnis_dummy.xlsx
Blätter: Protokoll, Anmeldungen, Diplomarbeiten, Pruefungen, Kennzahlen
"""
from __future__ import annotations

from dataclasses import astuple
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from backend.import_anmeldungen import importiere_alles
from backend.qualitaet import metriken
from backend.ziel_db import ZielDB
from testdaten.erzeuge_dummy import stelle_sicher

HIER = Path(__file__).resolve().parent
TD = HIER / "testdaten"
ZIEL = HIER / "ergebnisse" / "ergebnis_dummy.xlsx"

FARBE = {"FEHLER": "F8CBAD", "WARNUNG": "FFE699", "INFO": "BDD7EE"}


def blatt(wb, titel, kopf, zeilen, breiten=None):
    ws = wb.create_sheet(titel)
    ws.append(kopf)
    for c in ws[1]:
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="C6E0B4")
    for z in zeilen:
        ws.append(list(z))
    for i, b in enumerate(breiten or [], start=1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = b
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    return ws


def main() -> None:
    stelle_sicher()  # Dummy-Excel erzeugen, falls nicht vorhanden
    db = ZielDB()
    klassen = [TD / f"anmeldung_{k}.xlsx" for k in ("5AHWIM", "5BHWII", "5CHWIL")]
    prot = importiere_alles(db, TD / "lehrpersonen_dummy.csv", TD / "sokrates_export_dummy.csv",
                            klassen, TD / "noten_dummy.csv")
    q = lambda sql: db.conn.execute(sql).fetchall()  # noqa: E731

    wb = Workbook()
    wb.remove(wb.active)
    ws = blatt(wb, "Protokoll", ["Regel", "Stufe", "Datei", "Zeile", "Person", "Text"],
               (astuple(m) for m in prot.meldungen), [7, 10, 24, 7, 20, 70])
    for row in ws.iter_rows(min_row=2):
        row[1].fill = PatternFill("solid", fgColor=FARBE[row[1].value])

    blatt(wb, "Anmeldungen", ["Personen-ID", "Nachname", "Vorname", "Klasse", "Schwerpunkt", "Klausurart",
                              "Diplomarbeit", "Betreuer:in", "Sprache schriftl.", "Sprache mündl.",
                              "Wahlfach", "importiert am"],
          q("""SELECT a.personen_id, s.nachname, s.vorname, s.klasse, a.schwerpunkt, a.klausurart, d.titel,
                      l.vorname || ' ' || l.nachname, a.sprache_schriftlich, a.sprache_muendlich,
                      a.wahlfach, a.importiert_am
               FROM anmeldung a JOIN schueler s USING(personen_id)
               LEFT JOIN diplomarbeit d USING(da_id) LEFT JOIN lehrperson l ON l.personen_id = d.betreuer_id
               ORDER BY s.klasse, s.nachname"""), [16, 12, 10, 9, 18, 30, 40, 18, 18, 14, 40, 22])

    blatt(wb, "Diplomarbeiten", ["Titel", "Betreuer:in", "Team"],
          q("""SELECT d.titel, l.vorname || ' ' || l.nachname, GROUP_CONCAT(s.nachname, ', ')
               FROM diplomarbeit d LEFT JOIN lehrperson l ON l.personen_id = d.betreuer_id
               LEFT JOIN anmeldung a ON a.da_id = d.da_id LEFT JOIN schueler s ON s.personen_id = a.personen_id
               GROUP BY d.da_id ORDER BY d.titel"""), [45, 20, 30])

    blatt(wb, "Pruefungen", ["Personen-ID", "Nachname", "Prüfungsteil", "Note", "Prüfer:in", "Beisitzer:in",
                             "Quelle Note", "Quelle Prüfer", "Quelle Beisitzer"],
          q("""SELECT p.personen_id, s.nachname, p.pruefungsteil, p.note, lp.kuerzel, lb.kuerzel,
                      p.quelle_note, p.quelle_pruefer, p.quelle_beisitzer
               FROM pruefung p JOIN schueler s USING(personen_id)
               LEFT JOIN lehrperson lp ON lp.personen_id = p.pruefer_id
               LEFT JOIN lehrperson lb ON lb.personen_id = p.beisitzer_id
               ORDER BY p.personen_id, p.pruefungsteil"""), [12, 14, 14, 6, 10, 12, 12, 12, 14])

    m = metriken(db)
    blatt(wb, "Kennzahlen", ["Dimension", "Kennzahl", "Wert"],
          ((dim, k, v) for dim, werte in m.items() for k, v in werte.items()), [18, 30, 28])

    ZIEL.parent.mkdir(exist_ok=True)
    wb.save(ZIEL)
    print(f"Geschrieben: {ZIEL}")


if __name__ == "__main__":
    main()

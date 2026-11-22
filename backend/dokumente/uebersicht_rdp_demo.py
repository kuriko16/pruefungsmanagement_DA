"""Erster Excel-Prototyp: eine Zeile je Prüfung, nur erfundene Beispieldaten."""

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill


def erstelle_uebersicht(pruefungsjahr, pruefungen):
    """Schreibt die übergebenen Prüfungen in eine neue Excel-Datei."""
    arbeitsmappe = Workbook()
    blatt = arbeitsmappe.active
    blatt.title = "RDP-Übersicht"

    blatt["A1"] = f"Übersicht Reife- und Diplomprüfung – {pruefungsjahr}"
    blatt["A1"].font = Font(size=14, bold=True)
    blatt["A2"] = "Demo mit erfundenen Daten. Gelb: Betreuung manuell eintragen."

    # Diese Spalten sind ein erster Entwurf, noch keine bestätigte Vorlage.
    spalten = [
        "Personen-ID", "Kandidat:in", "Klasse", "Prüfungsfach",
        "Prüfungsart", "Prüfer:in", "Beisitzer:in", "Betreuung (manuell)",
    ]
    for nummer, titel in enumerate(spalten, start=1):
        zelle = blatt.cell(row=4, column=nummer, value=titel)
        zelle.font = Font(bold=True, color="FFFFFF")
        zelle.fill = PatternFill(fill_type="solid", fgColor="24476B")
        zelle.alignment = Alignment(wrap_text=True, vertical="center")
    blatt.row_dimensions[4].height = 32

    for pruefung in pruefungen:
        # Die letzte Spalte bleibt für die manuelle Betreuungseingabe leer.
        blatt.append(list(pruefung) + [None])
        blatt.cell(row=blatt.max_row, column=8).fill = PatternFill(
            fill_type="solid", fgColor="FFF2CC"
        )

    # Lesbare Spaltenbreiten und Filter für die Übersicht.
    breiten = {"A": 18, "B": 24, "C": 12, "D": 22,
               "E": 18, "F": 22, "G": 22, "H": 26}
    for spalte, breite in breiten.items():
        blatt.column_dimensions[spalte].width = breite
    blatt.freeze_panes = "A5"
    blatt.auto_filter.ref = f"A4:H{blatt.max_row}"

    # Der Pfad funktioniert unabhängig davon, wo das Terminal geöffnet wurde.
    projektordner = Path(__file__).resolve().parents[2]
    ausgabeordner = projektordner / "data" / "ausgabe" / pruefungsjahr.replace("/", "_")
    ausgabeordner.mkdir(parents=True, exist_ok=True)

    # Jede Ausführung erhält eine neue Datei: manuelle Einträge bleiben erhalten.
    zeitstempel = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dateipfad = ausgabeordner / f"uebersicht_rdp_demo_{zeitstempel}.xlsx"
    arbeitsmappe.save(dateipfad)
    return dateipfad


if __name__ == "__main__":
    # Alle Namen, IDs, Klassen und Zuweisungen sind frei erfunden.
    # Reihenfolge: ID, Name, Klasse, Fach, Art, Prüfer:in, Beisitzer:in.
    beispielpruefungen = [
        ("DEMO-001", "Mira Beispiel", "5XTEST", "Mathematik",
         "schriftlich", "Alex Test", "Robin Muster"),
        ("DEMO-001", "Mira Beispiel", "5XTEST", "Deutsch",
         "mündlich", "Robin Muster", "Alex Test"),
    ]

    datei = erstelle_uebersicht("2026/27", beispielpruefungen)
    print(f"Excel-Datei erstellt: {datei}")
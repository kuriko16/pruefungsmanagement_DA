"""Bereitet Kopien der beiden Schulvorlagen ohne personenbezogene Inhalte vor.

Es werden ausschließlich Layouts übernommen, keine Anmeldungen importiert.
Aufruf siehe docs/pruefungsunterlagen.md. Bestehende Versionen werden nie überschrieben.
"""

import argparse
import json
import sys
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.packaging.core import DocumentProperties
from openpyxl.packaging.custom import CustomPropertyList
from openpyxl.worksheet.header_footer import HeaderFooter

PROJEKT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJEKT / "backend"))
from dokumente.vorlagen import jahresordner  # noqa: E402


def bereinigen(mappe, erlaubte_werte):
    """Nur ausdrücklich ausgewählte Beschriftungen bleiben in der Kopie."""
    mappe.properties = DocumentProperties(creator="Prüfungsmanagement TGM", lastModifiedBy="")
    mappe.custom_doc_props = CustomPropertyList()
    mappe.defined_names.clear()
    mappe._external_links = []
    for blatt in mappe:
        blatt.defined_names.clear()
        blatt._images.clear()
        blatt._charts.clear()
        blatt.HeaderFooter = HeaderFooter()
        blatt.conditional_formatting._cf_rules.clear()
        blatt.data_validations.dataValidation.clear()
        for zelle in list(blatt._cells.values()):
            if isinstance(zelle, MergedCell):
                continue
            zelle.comment = None
            zelle.hyperlink = None
            zelle.value = erlaubte_werte.get((blatt.title, zelle.coordinate))
        # Die Originaldatei hat Formatierungen bis Zeile 65.000. Sie enthalten
        # keine benötigten Tabellenzeilen und würden jeden Export verlangsamen.
        for schluessel in list(blatt._cells):
            if schluessel[0] > 45:
                del blatt._cells[schluessel]
        for zeile in list(blatt.row_dimensions):
            if zeile > 45:
                del blatt.row_dimensions[zeile]


def uebersicht_vorbereiten(pfad):
    mappe = load_workbook(pfad, keep_links=False)
    erlaubt = {}
    for blatt in mappe:
        for zeile in blatt.iter_rows(min_row=7, max_row=9, min_col=5, max_col=20):
            for zelle in zeile:
                if zelle.value is not None:
                    erlaubt[blatt.title, zelle.coordinate] = zelle.value
    bereinigen(mappe, erlaubt)
    for blatt in mappe:
        for bereich in list(blatt.merged_cells.ranges):
            if bereich.min_row >= 11:
                blatt.unmerge_cells(str(bereich))
        for adresse, text in {
            "A1": "Vorsitzende/r:", "A2": "Jahrgangsvorstand:",
            "A3": "Termin mündliche RDP:",
            "A5": "Übersicht der Anmeldungen – Zulassung und Kompensation sind gesondert zu prüfen.",
            "A7": "{{klasse}} {{jahr}}", "A10": "Gruppe", "B10": "Betreuer",
            "C10": "Nachname", "D10": "Vorname", "I10": "Betreuung",
            "U10": "Anzahl", "V10": "Diplomarbeitstitel",
        }.items():
            blatt[adresse] = text
        for zeile in range(11, 31):
            blatt[f"U{zeile}"] = f'=COUNTIF(E{zeile}:P{zeile},"X")+COUNTIF(J{zeile}:P{zeile},"XV")'
        blatt.freeze_panes = "E11"
        blatt.print_title_rows = "1:10"
    return mappe


def zeitplan_vorbereiten(pfad):
    mappe = load_workbook(pfad, keep_links=False)
    erlaubt = {}
    for blatt in mappe:
        kopf = 2 if blatt.title.startswith("Aufsicht") else (4 if "Präsentation" in blatt.title else 5)
        for zelle in blatt[kopf]:
            if zelle.value is not None:
                erlaubt[blatt.title, zelle.coordinate] = zelle.value
    bereinigen(mappe, erlaubt)
    for blatt in mappe:
        aufsicht = blatt.title.startswith("Aufsicht")
        kopf = 2 if aufsicht else (4 if "Präsentation" in blatt.title else 5)
        for bereich in list(blatt.merged_cells.ranges):
            if bereich.min_row > kopf:
                blatt.unmerge_cells(str(bereich))
        if aufsicht:
            tag = "1" if blatt.title.endswith("Mo") else "2"
            blatt.title = f"Aufsicht_Vorbereitung_Tag{tag}"
            blatt["A1"] = "Aufsicht Vorbereitung – Datum: __________"
            blatt.print_area = "A1:D7"
        else:
            art = "Diplomarbeitspräsentation" if kopf == 4 else "Mündliche RDP"
            blatt["A1"] = f"{{{{klasse}}}} – {art} – {{{{jahr}}}}"
            blatt["A2"], blatt["A3"] = "Vorsitzende/r:", "Jahrgangsvorstand:"
            if kopf == 5:
                blatt["A4"] = "Datum / Raum / Beginn: ______________________________"
            # Erst nach manueller Eingabe von Beginn und Dauer weiterrechnen.
            for zeile in range(kopf + 2, 21):
                vor = zeile - 1
                blatt[f"D{zeile}"] = f'=IF(OR(D{vor}="",E{vor}=""),"",D{vor}+TIME(0,E{vor},0))'
                blatt[f"D{zeile}"].number_format = "hh:mm"
    return mappe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uebersicht", type=Path, required=True)
    parser.add_argument("--zeitplan", type=Path, required=True)
    parser.add_argument("--jahr", required=True)
    parser.add_argument("--version", type=int, required=True)
    args = parser.parse_args()
    if args.version < 1:
        parser.error("Die Version muss mindestens 1 sein.")
    ziel = PROJEKT / "vorlagen" / jahresordner(args.jahr) / f"v{args.version}"
    if ziel.exists():
        parser.error("Diese Version existiert bereits. Bitte eine neue Versionsnummer verwenden.")
    uebersicht = uebersicht_vorbereiten(args.uebersicht)
    zeitplan = zeitplan_vorbereiten(args.zeitplan)
    ziel.mkdir(parents=True)
    uebersicht.save(ziel / "uebersicht_rdp.xlsx")
    zeitplan.save(ziel / "zeitplan_muendlich.xlsx")
    meta = {"pruefungsjahr": args.jahr, "version": f"v{args.version}",
            "basis": "Schulvorlagen 2025/26; personenbezogene Inhalte entfernt",
            "zeitplan_status": "Leerformular; keine automatische Terminplanung"}
    (ziel / "version.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Vorlagen gespeichert: {ziel.relative_to(PROJEKT)}")


if __name__ == "__main__":
    main()

"""Füllt die bereinigten Schulvorlagen mit bereits vorhandenen Daten."""

from collections import defaultdict
from copy import copy
from datetime import date

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill
from openpyxl.utils import get_column_letter

from .vorlagen import DokumentFehler, vorlagenpfad

SCHRIFTLICH = {"Angewandte Mathematik": 5, "Deutsch": 6, "Englisch": 7, "Fachtheorie": 8}
MUENDLICH = {"Deutsch": 11, "Englisch": 12, "Geografie, Geschichte und Politische Bildung": 13,
             "Naturwissenschaften": 14, "Religion": 15}
VERTIEFUNG = {"5AHWIM": "Werkstoff- und Fertigungstechnik",
              "5BHWII": "Softwareentwicklung und Projektmanagement / Netzwerke und Embedded Software",
              "5CHWIL": "Logistik"}


def text_eintragen(zelle, wert):
    """Daten bleiben Text: Auch ein Titel mit führendem '=' wird keine Excel-Formel."""
    zelle.value = "" if wert is None else str(wert)
    zelle.data_type = "s"


def datum(wert):
    if not wert:
        return ""
    try:
        return date.fromisoformat(wert).strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return str(wert)


def kopiere_zelle(quelle, ziel):
    ziel._style = copy(quelle._style)
    ziel.alignment = copy(quelle.alignment)


def erstelle_uebersicht(daten, version="v1"):
    mappe = load_workbook(vorlagenpfad(daten["jahr"], "uebersicht", version))
    namen = {klasse["name"] for klasse in daten["klassen"]}
    unbekannt = namen - set(mappe.sheetnames)
    if unbekannt:
        raise DokumentFehler("In dieser Vorlage fehlen Klassenblätter: " + ", ".join(sorted(unbekannt)))
    for blatt in list(mappe):
        if blatt.title not in namen:
            mappe.remove(blatt)
    for klasse in daten["klassen"]:
        befuelle_klasse(mappe[klasse["name"]], klasse, daten["jahr"])
    pruefungsdetails(mappe, daten)
    mappe.calculation.fullCalcOnLoad = True
    return mappe


def befuelle_klasse(blatt, klasse, jahr):
    pruefungen = [p for k in klasse["kandidaten"] for p in k["pruefungen"]]
    muendlich = {**MUENDLICH, VERTIEFUNG[klasse["name"]]: 16}
    # Zusätzliche Wahlfächer bekommen eigene Spalten vor der Kompensation.
    extra = sorted({p["fach"] for p in pruefungen
                    if p["art"] == "muendlich" and p["feld"] != "PM_SPF" and p["fach"] not in muendlich})
    anzahl = len(extra)
    if anzahl:
        # openpyxl verschiebt verbundene Bereiche nicht automatisch mit.
        bereiche = [copy(r) for r in blatt.merged_cells.ranges if r.min_col >= 17]
        for r in bereiche:
            blatt.unmerge_cells(str(r))
        blatt.insert_cols(17, anzahl)
        for r in bereiche:
            r.shift(col_shift=anzahl)
            blatt.merge_cells(str(r))
        for bereich in ("I7:P7", "M8:P8"):
            blatt.unmerge_cells(bereich)
        blatt.merge_cells(start_row=7, start_column=9, end_row=7, end_column=16 + anzahl)
        blatt.merge_cells(start_row=8, start_column=13, end_row=8, end_column=16 + anzahl)
        # Breiten der rechts liegenden Spalten bleiben wie in der Originalvorlage.
        for spalte in range(24, 16, -1):
            blatt.column_dimensions[get_column_letter(spalte + anzahl)].width = blatt.column_dimensions[get_column_letter(spalte)].width
        for spalte, fach in enumerate(extra, 17):
            muendlich[fach] = spalte
            blatt.column_dimensions[get_column_letter(spalte)].width = blatt.column_dimensions["P"].width
            for zeile in range(9, 12):
                kopiere_zelle(blatt.cell(zeile, 16), blatt.cell(zeile, spalte))
            text_eintragen(blatt.cell(9, spalte), fach)

    letzte_pruefung = 16 + anzahl
    letzte_druckspalte = 20 + anzahl
    zaehler, titelspalte = 21 + anzahl, 22 + anzahl
    for zeile in range(11, 46):
        for spalte in range(1, 25 + anzahl):
            blatt.cell(zeile, spalte).value = None
    text_eintragen(blatt["A7"], f"{klasse['name']} {jahr}")
    tage = sorted({p["pruefungstag"] for p in pruefungen if p["art"] == "muendlich" and p["pruefungstag"]})
    text_eintragen(blatt["E3"], ", ".join(datum(t) for t in tage))
    text_eintragen(blatt.cell(10, zaehler), "Anzahl")
    text_eintragen(blatt.cell(10, titelspalte), "Diplomarbeitstitel")
    schwerpunkt = {p["fach"] for p in pruefungen if p["feld"] == "PM_SPF"}
    if len(schwerpunkt) > 1:
        raise DokumentFehler(f"{klasse['name']}: Mehrere Schwerpunktfächer benötigen eine angepasste Vorlage.")
    if schwerpunkt:
        text_eintragen(blatt["J9"], next(iter(schwerpunkt)))

    def fachspalte(pruefung):
        if pruefung["art"] == "schriftlich":
            if pruefung["fach"] not in SCHRIFTLICH:
                raise DokumentFehler(f"Für das schriftliche Fach '{pruefung['fach']}' fehlt eine Vorlagenspalte.")
            return SCHRIFTLICH[pruefung["fach"]]
        return 10 if pruefung["feld"] == "PM_SPF" else muendlich[pruefung["fach"]]

    lehrende = defaultdict(set)
    for p in pruefungen:
        if p["pruefer_nachname"]:
            lehrende[fachspalte(p)].add(p["pruefer_nachname"])
    for spalte in range(5, letzte_pruefung + 1):
        if spalte != 9:
            text_eintragen(blatt.cell(10, spalte), " / ".join(sorted(lehrende[spalte])))
            blatt.cell(10, spalte).alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    # Kompensation wird nicht aus MP oder GN hergeleitet. Die Entscheidung fehlt im Modell.
    for spalte in range(letzte_pruefung + 1, letzte_druckspalte + 1):
        blatt.cell(10, spalte).value = None

    gruppen = {}
    for kandidat in klasse["kandidaten"]:
        # Ohne Diplomarbeit jede Person einzeln lassen, keine erfundene gemeinsame Gruppe.
        schluessel = ("da", kandidat["da_id"]) if kandidat["da_id"] else ("person", kandidat["anmeldung_id"])
        gruppen.setdefault(schluessel, []).append(kandidat)
    zeile, gruppe = 11, 0
    for mitglieder in gruppen.values():
        anfang = zeile
        if mitglieder[0]["da_id"]:
            gruppe += 1
        for k in mitglieder:
            for spalte in range(1, titelspalte + 1):
                kopiere_zelle(blatt.cell(11, spalte), blatt.cell(zeile, spalte))
            blatt.row_dimensions[zeile].height = max(blatt.row_dimensions[11].height or 22, 22)
            text_eintragen(blatt.cell(zeile, 3), k["nachname"])
            text_eintragen(blatt.cell(zeile, 4), k["vorname"])
            if k["da_id"]:
                blatt.cell(zeile, 9, "X")
            for pruefung in k["pruefungen"]:
                blatt.cell(zeile, fachspalte(pruefung), "X")
            ende = get_column_letter(letzte_pruefung)
            blatt.cell(zeile, zaehler, f'=COUNTIF(E{zeile}:{ende}{zeile},"X")+COUNTIF(J{zeile}:{ende}{zeile},"XV")')
            zeile += 1
        for spalte, wert in ((1, str(gruppe) if mitglieder[0]["da_id"] else ""),
                             (2, mitglieder[0]["betreuer"]), (titelspalte, mitglieder[0]["da_titel"])):
            text_eintragen(blatt.cell(anfang, spalte), wert)
            blatt.cell(anfang, spalte).alignment = Alignment(vertical="center", wrap_text=True)
            if zeile - anfang > 1:
                blatt.merge_cells(start_row=anfang, start_column=spalte, end_row=zeile - 1, end_column=spalte)
    # Zusätzliche Hinweise ersetzen keine Zulassungsentscheidung.
    for r in range(zeile, zeile + 3):
        for c in range(1, letzte_druckspalte + 1):
            blatt.cell(r, c).border = Border()
            blatt.cell(r, c).fill = PatternFill()
    blatt.merge_cells(start_row=zeile + 1, start_column=1, end_row=zeile + 1, end_column=letzte_druckspalte)
    blatt.cell(zeile + 1, 1, "Zuordnung je Person/Fach/Lehrperson: Blatt Prüfungsdetails. Kompensation bleibt offen.")
    blatt.cell(zeile + 1, 1).font = Font(name="Calibri", size=9)
    blatt.print_area = f"A1:{get_column_letter(letzte_druckspalte)}{zeile + 2}"
    blatt.print_title_rows = "1:10"
    blatt.page_setup.orientation = "landscape"
    blatt.page_setup.fitToWidth, blatt.page_setup.fitToHeight = 1, 0
    blatt.sheet_properties.pageSetUpPr.fitToPage = True


def pruefungsdetails(mappe, daten):
    """Eindeutige Zuordnung auch dann, wenn ein Fach mehrere Prüfer:innen hat."""
    blatt = mappe.create_sheet("Prüfungsdetails")
    kopf = ["Prüfungsjahr", "Klasse", "Personen-ID", "Nachname", "Vorname", "Art", "Fach",
            "Prüfer:in", "Beisitz", "Prüfungstag", "JN", "MP", "GN", "Diplomarbeit", "Betreuung"]
    blatt.append(kopf)
    for p in daten["pruefungen"]:
        werte = [daten["jahr"], p["klasse"], p["personen_id"], p["nachname"], p["vorname"],
                 "mündlich" if p["art"] == "muendlich" else p["art"], p["fach"], p["pruefer"],
                 p["beisitz"], datum(p["pruefungstag"]), p["note_jn"], p["note_mp"], p["note_gn"],
                 p["da_titel"], p["betreuer"]]
        zeile = blatt.max_row + 1
        for spalte, wert in enumerate(werte, 1):
            zelle = blatt.cell(zeile, spalte)
            if spalte in (11, 12, 13):
                zelle.value = wert
            else:
                text_eintragen(zelle, wert)
            zelle.alignment = Alignment(vertical="top", wrap_text=True)
        blatt.row_dimensions[zeile].height = 48
    for zelle in blatt[1]:
        zelle.font = Font(bold=True)
        zelle.fill = PatternFill("solid", fgColor="DDE6F0")
    for spalte in range(1, 16):
        blatt.column_dimensions[get_column_letter(spalte)].width = 22 if spalte not in (7, 14) else 48
    blatt.freeze_panes, blatt.auto_filter.ref = "A2", blatt.dimensions
    blatt.print_title_rows = "1:1"
    blatt.print_area = blatt.dimensions
    blatt.page_setup.orientation = "landscape"
    blatt.page_setup.fitToWidth, blatt.page_setup.fitToHeight = 1, 0
    blatt.sheet_properties.pageSetUpPr.fitToPage = True


def erstelle_zeitplanvorlage(jahr, klasse, version="v1"):
    """Liefert die Schulvorlage. Zeiten werden hier weder geplant noch erfunden."""
    mappe = load_workbook(vorlagenpfad(jahr, "zeitplan", version))
    for blatt in mappe:
        blatt.page_setup.orientation = "landscape"
        blatt.page_setup.fitToWidth, blatt.page_setup.fitToHeight = 1, 1
        blatt.sheet_properties.pageSetUpPr.fitToPage = True
        blatt.row_breaks.brk.clear()
        blatt.col_breaks.brk.clear()
        if blatt.title.startswith("5AHWIM"):
            blatt.title = blatt.title.replace("5AHWIM", klasse, 1)
        for zelle in list(blatt._cells.values()):
            if zelle.data_type == "s" and isinstance(zelle.value, str):
                zelle.value = zelle.value.replace("{{jahr}}", jahr).replace("{{klasse}}", klasse)
    return mappe

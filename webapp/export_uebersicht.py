"""Export der "Übersicht Reife- und Diplomprüfung" als Excel, angelehnt an die Vorlage
Übersicht_Reife_und_Diplomprüfung_5XHWIX_25_26.xlsx (ein Blatt pro Klasse).

Aufbau eines Blatts wie in der Vorlage:
  Zeile 1-3   Vorsitz, Jahrgangsvorstand (händisch), Termin mündliche RDP (aus den Prüfungstagen)
  Zeile 7-9   Spaltengruppen: schriftlich | mündlich (DA, Schwerpunktfach, Sprache, Wahlfach) | Kompensation
  Zeile 10    Prüfer:innen je Fach (Nachnamen aus den Zuweisungen)
  ab Zeile 11 je Kandidat:in ein "X" pro gewählter Prüfung, gruppiert nach Diplomarbeit

Hinweis: Yilmaz baut die Dokumenterstellung (YY-01). Dieser Export ist der Button in der
Oberfläche und kann später auf seinen Code umgestellt werden.
"""
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# Kurzbezeichnungen wie in der Vorlage ("AM\nAngewandte Mathematik")
KUERZEL = {
    "Angewandte Mathematik": "AM", "Deutsch": "D", "Englisch": "E", "Fachtheorie": "FT",
    "Religion": "R", "Ethik": "ETH", "Naturwissenschaften": "NW2",
    "Geografie, Geschichte und Politische Bildung": "GGP",
}
REIHENFOLGE_SCHRIFTLICH = ["Angewandte Mathematik", "Deutsch", "Englisch", "Fachtheorie"]

DUENN = Side(style="thin", color="999999")
RAHMEN = Border(left=DUENN, right=DUENN, top=DUENN, bottom=DUENN)
KOPF = PatternFill("solid", fgColor="DDE6F0")
FETT = Font(bold=True)
MITTE = Alignment(horizontal="center", vertical="center", wrap_text=True)


def beschriftung(fach):
    k = KUERZEL.get(fach)
    return f"{k}\n{fach}" if k else fach


def erstelle_uebersicht(con, jahr):
    mappe = Workbook()
    mappe.remove(mappe.active)
    klassen = con.execute("""SELECT k.id, k.name FROM klasse k JOIN pruefungsjahr j ON j.id = k.pruefungsjahr_id
                             WHERE j.bezeichnung = ? ORDER BY k.name""", (jahr,)).fetchall()
    for klasse in klassen:
        blatt_fuer_klasse(mappe, con, klasse, jahr)
    if not klassen:
        mappe.create_sheet("leer")["A1"] = "Für dieses Prüfungsjahr sind noch keine Daten importiert."
    return mappe


def blatt_fuer_klasse(mappe, con, klasse, jahr):
    ws = mappe.create_sheet(klasse["name"])
    # Alle Prüfungen der Klasse inkl. Kandidat, Diplomarbeit und Prüfer-Nachname in einer Abfrage
    zeilen = con.execute("""
        SELECT a.id AS anm, kd.nachname, kd.vorname, pf.art, pf.feld, pf.fach, pf.note_mp, pf.pruefungstag,
               p.nachname AS pruefer, d.titel AS da_titel,
               COALESCE(b.nachname || ' ' || b.vorname, d.betreuer_text) AS betreuer
        FROM anmeldung a
        JOIN kandidat kd ON kd.personen_id = a.personen_id
        LEFT JOIN pruefungsfach pf ON pf.anmeldung_id = a.id
        LEFT JOIN lehrperson p ON p.id = pf.pruefer_id
        LEFT JOIN anmeldung_diplomarbeit ad ON ad.anmeldung_id = a.id
        LEFT JOIN diplomarbeit d ON d.id = ad.diplomarbeit_id
        LEFT JOIN lehrperson b ON b.id = d.betreuer_id
        WHERE a.klasse_id = ?
        ORDER BY d.titel IS NULL, d.titel, kd.nachname, kd.vorname""", (klasse["id"],)).fetchall()

    # 1) Spalten bestimmen: welche Fächer kommen in dieser Klasse vor?
    schriftl = sorted({z["fach"] for z in zeilen if z["art"] == "schriftlich"},
                      key=lambda f: (REIHENFOLGE_SCHRIFTLICH.index(f) if f in REIHENFOLGE_SCHRIFTLICH else 99, f))
    spf = sorted({z["fach"] for z in zeilen if z["feld"] == "PM_SPF"})
    sprache = [f for f in ("Deutsch", "Englisch")
               if any(z["fach"] == f and z["feld"] in ("PM_D", "PM_E") for z in zeilen)]
    wahl = sorted({z["fach"] for z in zeilen if (z["feld"] or "").startswith("PM_WF")})

    # Jede Spalte: (Gruppe, Fach, Prüfungsart, Feld-Filter)
    spalten = [("schriftlich", f, "schriftlich", None) for f in schriftl]
    spalten += [("Diplomarbeit", "Präsentation \nund Diskussion", "da", None)]
    spalten += [("Schwerpunktfach", f, "muendlich", "PM_SPF") for f in spf]
    spalten += [("Sprache", f, "muendlich", "sprache") for f in sprache]
    spalten += [("Wahlfach\n(V….vorgezogene sRDP)", f, "muendlich", "PM_WF") for f in wahl]
    erste = 5  # Spalte E, wie in der Vorlage
    n_pruef = len(spalten)
    sp_anzahl = erste + n_pruef + len(schriftl)  # nach den Kompensationsspalten
    sp_titel = sp_anzahl + 1

    # 2) Kopfbereich
    tage = sorted({z["pruefungstag"] for z in zeilen if z["art"] == "muendlich" and z["pruefungstag"]})
    termin = (f"{_datum(tage[0])} – {_datum(tage[-1])}" if len(tage) > 1 else _datum(tage[0])) if tage else ""
    for zeile, (text, wert) in enumerate([("Vorsitzende/r:", ""), ("Jahrgangsvorstand:", ""),
                                          ("Termin mündliche RDP:", termin)], start=1):
        ws.cell(zeile, 1, text).font = FETT
        ws.cell(zeile, 5, wert)
    ws.cell(5, 1, "Die unten angeführten Kandidatinnen und Kandidaten sind zur mündlichen "
                  "Reife- und Diplomprüfung zugelassen.")
    ws.cell(7, 1, f"{klasse['name']} {jahr}").font = Font(bold=True, size=13)

    # Zeile 7: Hauptgruppen, Zeile 8: Untergruppen beim mündlichen Teil
    _gruppe(ws, 7, erste, erste + len(schriftl) - 1, "Prüfungen schriftlich")
    _gruppe(ws, 7, erste + len(schriftl), erste + n_pruef - 1, "Prüfungen mündlich")
    _gruppe(ws, 7, erste + n_pruef, sp_anzahl - 1, "Kompensationsprüfung\nmöglich bzw. erforderlich in")
    start = erste + len(schriftl)
    for name in ("Diplomarbeit", "Schwerpunktfach", "Sprache", "Wahlfach\n(V….vorgezogene sRDP)"):
        breite = sum(1 for s in spalten if s[0] == name)
        if breite:
            _gruppe(ws, 8, start, start + breite - 1, name.replace("Diplomarbeit", "Diplom-\narbeit"))
            start += breite

    # Zeile 9 (Fach) und Zeile 10 (Prüfer:innen dieses Fachs)
    for i, (_, fach, art, filt) in enumerate(spalten):
        c = erste + i
        _kopf(ws, 9, c, beschriftung(fach) if art != "da" else fach)
        if art == "da":
            _kopf(ws, 10, c, "Betreuer:in")
        else:
            namen = sorted({z["pruefer"] for z in zeilen if z["fach"] == fach and z["art"] == art and z["pruefer"]})
            _kopf(ws, 10, c, "\n".join(namen))
    for i, fach in enumerate(schriftl):
        _kopf(ws, 9, erste + n_pruef + i, beschriftung(fach))
        _kopf(ws, 10, erste + n_pruef + i, f"={get_column_letter(erste + i)}10")
    for c, text in ((1, "Gruppe"), (2, "Betreuer:in"), (3, "Nachname"), (4, "Vorname"),
                    (sp_anzahl, "Anzahl"), (sp_titel, "Diplomarbeitstitel")):
        _kopf(ws, 10, c, text)

    # 3) Kandidat:innen, gruppiert nach Diplomarbeit
    kandidaten = {}
    for z in zeilen:
        k = kandidaten.setdefault(z["anm"], {"z": z, "pruef": []})
        if z["fach"]:
            k["pruef"].append(z)
    zeile = 11
    gruppen = {}
    for k in kandidaten.values():
        gruppen.setdefault(k["z"]["da_titel"], []).append(k)
    for nr, (titel, mitglieder) in enumerate(gruppen.items(), start=1):
        anfang = zeile
        for k in mitglieder:
            ws.cell(zeile, 3, k["z"]["nachname"])
            ws.cell(zeile, 4, k["z"]["vorname"])
            for i, (_, fach, art, filt) in enumerate(spalten):
                if art == "da":
                    treffer = titel is not None
                else:
                    treffer = any(p["fach"] == fach and p["art"] == art and _passt(p["feld"], filt) for p in k["pruef"])
                if treffer:
                    ws.cell(zeile, erste + i, "X")
            # Kompensationsprüfung: wenn die schriftliche Note ein Nicht genügend (5) ist
            for i, fach in enumerate(schriftl):
                if any(p["fach"] == fach and p["art"] == "schriftlich" and p["note_mp"] == 5 for p in k["pruef"]):
                    ws.cell(zeile, erste + n_pruef + i, "X")
            von, bis = get_column_letter(erste), get_column_letter(erste + n_pruef - 1)
            ws.cell(zeile, sp_anzahl, f'=COUNTIF({von}{zeile}:{bis}{zeile},"X")')
            for c in range(1, sp_titel + 1):
                ws.cell(zeile, c).border = RAHMEN
                if c >= erste:
                    ws.cell(zeile, c).alignment = MITTE
            zeile += 1
        # Gruppe, Betreuer und Titel über alle Mitglieder zusammenfassen (wie in der Vorlage)
        ws.cell(anfang, 1, f"{klasse['name'][1]}{nr}" if titel else "–")
        ws.cell(anfang, 2, mitglieder[0]["z"]["betreuer"] if titel else "")
        ws.cell(anfang, sp_titel, titel or "(keine Diplomarbeit eingetragen)")
        for c in (1, 2, sp_titel):
            if zeile - 1 > anfang:
                ws.merge_cells(start_row=anfang, start_column=c, end_row=zeile - 1, end_column=c)
            ws.cell(anfang, c).alignment = Alignment(vertical="center", wrap_text=True)

    # 4) Spaltenbreiten und Fixierung
    for c, breite in {1: 8, 2: 18, 3: 18, 4: 14}.items():
        ws.column_dimensions[get_column_letter(c)].width = breite
    for c in range(erste, sp_anzahl + 1):
        ws.column_dimensions[get_column_letter(c)].width = 11
    ws.column_dimensions[get_column_letter(sp_titel)].width = 50
    ws.row_dimensions[9].height = 75
    ws.row_dimensions[10].height = 45
    ws.freeze_panes = "E11"
    ws.page_setup.orientation = "landscape"


def _passt(feld, filt):
    if filt is None:
        return True
    if filt == "sprache":
        return feld in ("PM_D", "PM_E")
    return (feld or "").startswith(filt)


def _datum(iso):
    j, m, t = iso.split("-")
    return f"{t}.{m}.{j}"


def _kopf(ws, zeile, spalte, text):
    zelle = ws.cell(zeile, spalte, text)
    zelle.font, zelle.fill, zelle.alignment, zelle.border = FETT, KOPF, MITTE, RAHMEN


def _gruppe(ws, zeile, von, bis, text):
    if bis < von:
        return
    _kopf(ws, zeile, von, text)
    if bis > von:
        ws.merge_cells(start_row=zeile, start_column=von, end_row=zeile, end_column=bis)

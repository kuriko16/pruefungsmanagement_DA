"""Lokale PDF-Ausgabe aus vorhandenen Daten und den echten Excel-Druckbereichen."""

import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import pdf_erstellen  # Registriert die eingebetteten Vera-Schriften.
from .excel_erstellen import datum
from .vorlagen import DokumentFehler


def libreoffice_pfad():
    """LibreOffice ist nur für PDF-Kopien der Excel-Vorlagen erforderlich."""
    kandidaten = [os.environ.get("PM_SOFFICE"), shutil.which("soffice"), shutil.which("libreoffice"),
                  "/Applications/LibreOffice.app/Contents/MacOS/soffice",
                  r"C:\Program Files\LibreOffice\program\soffice.exe",
                  r"C:\Program Files (x86)\LibreOffice\program\soffice.exe"]
    return next((str(p) for p in kandidaten if p and Path(p).is_file()), None)


def excel_als_pdf(mappe, nur_uebersicht=False):
    programm = libreoffice_pfad()
    if not programm:
        raise DokumentFehler("Für PDF-Kopien der Excel-Vorlagen bitte LibreOffice lokal installieren. "
                             "Prüfungszettel und Kommissions-PDF funktionieren auch ohne LibreOffice.")
    if nur_uebersicht and "Prüfungsdetails" in mappe.sheetnames:
        mappe.remove(mappe["Prüfungsdetails"])
    # Eigener Ordner und eigenes LibreOffice-Profil je Download, auch bei parallelen Aufrufen.
    with tempfile.TemporaryDirectory(prefix="rdp_pdf_") as ordner:
        basis = Path(ordner)
        quelle = basis / "dokument.xlsx"
        mappe.save(quelle)
        try:
            ergebnis = subprocess.run(
                [programm, f"-env:UserInstallation={(basis / 'profil').as_uri()}", "--headless",
                 "--convert-to", "pdf:calc_pdf_Export", "--outdir", str(basis), str(quelle)],
                capture_output=True, timeout=60, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as fehler:
            raise DokumentFehler("Die lokale PDF-Konvertierung konnte nicht abgeschlossen werden.") from fehler
        pdf = basis / "dokument.pdf"
        if ergebnis.returncode or not pdf.is_file():
            raise DokumentFehler("LibreOffice konnte diese Excel-Datei nicht als PDF ausgeben.")
        return pdf.read_bytes()


def dokument_pdf(daten, art):
    """Prüfungszettel pro Prüfung oder eine Kommissionsübersicht pro Klasse."""
    if art not in ("pruefungszettel", "kommission") or not daten["pruefungen"]:
        raise DokumentFehler("Für diese Auswahl sind keine passenden Prüfungsdaten vorhanden.")
    puffer = io.BytesIO()
    quer = art == "kommission"
    doc = SimpleDocTemplate(puffer, pagesize=landscape(A4) if quer else A4,
                           leftMargin=16*mm, rightMargin=16*mm, topMargin=16*mm, bottomMargin=17*mm,
                           title="Kommissionsübersicht" if quer else "Prüfungszettel")
    stile = getSampleStyleSheet()
    for stil in stile.byName.values():
        stil.fontName = "Vera"
    stile["Title"].fontName, stile["Title"].alignment = "VeraFett", 0
    stile["Normal"].fontSize, stile["Normal"].leading = 9, 12

    def text(wert, fett=False):
        s = escape("" if wert is None else str(wert)).replace("\n", "<br/>")
        return Paragraph(f"<b>{s}</b>" if fett else s, stile["Normal"])

    def tabelle(zeilen, breiten, kopf=False):
        t = Table([[text(w, (kopf and i == 0) or (not kopf and j == 0)) for j, w in enumerate(z)]
                   for i, z in enumerate(zeilen)], colWidths=[b*mm for b in breiten], repeatRows=int(kopf))
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (-1, 0) if kopf else (0, -1), colors.HexColor("#EEF3F8")),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#D5DDE6")),
            ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        return t

    def kopf(titel, klasse):
        return [Paragraph(titel, stile["Title"]), text(f"Prüfungsjahr {daten['jahr']} | Klasse {klasse}"),
                Spacer(1, 3*mm), text("Entwurf – die endgültige Formularvorlage fehlt noch."), Spacer(1, 6*mm)]

    inhalt = []
    if art == "pruefungszettel":
        for nummer, p in enumerate(daten["pruefungen"]):
            if nummer:
                inhalt.append(PageBreak())
            inhalt += kopf("Prüfungszettel", p["klasse"])
            noten = " / ".join("–" if p[n] is None else f"{p[n]:g}" for n in ("note_jn", "note_mp", "note_gn"))
            inhalt.append(tabelle([
                ["Kandidat:in", f"{p['vorname']} {p['nachname']}"], ["Personen-ID", p["personen_id"]],
                ["Prüfungsfach", p["fach"]], ["Art", "mündlich" if p["art"] == "muendlich" else p["art"]],
                ["Prüfungstag", datum(p["pruefungstag"]) or "noch offen"], ["Beginn / Raum", "noch offen"],
                ["Prüfer:in", p["pruefer"] or "noch offen"],
                ["Beisitz", p["beisitz"] or ("noch offen" if p["art"] == "muendlich" else "–")],
                ["JN / MP / GN", noten], ["Diplomarbeit", p["da_titel"]],
                ["Betreuung der Diplomarbeit", p["betreuer"] or "noch offen"],
            ], [49, 129]))
            inhalt += [Spacer(1, 10*mm), text("Bemerkungen: ____________________________________________________"),
                       Spacer(1, 10*mm), text("Unterschrift: _____________________________________________________")]
    else:
        for nummer, klasse in enumerate(daten["klassen"]):
            if nummer:
                inhalt.append(PageBreak())
            inhalt += kopf("Kommissionsübersicht", klasse["name"])
            inhalt += [text("Vorsitz / Jahrgangsvorstand: __________________________________________"), Spacer(1, 5*mm)]
            zeilen = [["Kandidat:in", "Fach / Art", "Tag", "Prüfer:in", "Beisitz"]]
            for k in klasse["kandidaten"]:
                for p in k["pruefungen"]:
                    art_text = "mündlich" if p["art"] == "muendlich" else p["art"]
                    zeilen.append([f"{k['nachname']} {k['vorname']}\nID: {k['personen_id']}",
                                   f"{p['fach']}\n{art_text}", datum(p["pruefungstag"]) or "offen",
                                   p["pruefer"] or "offen", p["beisitz"] or ("offen" if p["art"] == "muendlich" else "–")])
            inhalt.append(tabelle(zeilen, [51, 83, 28, 51, 52], kopf=True))

    def fusszeile(canvas, dokument):
        canvas.setFont("Vera", 8)
        canvas.drawString(16*mm, 9*mm, f"Prüfungsjahr {daten['jahr']} · Entwurf · Seite {dokument.page}")

    doc.build(inhalt, onFirstPage=fusszeile, onLaterPages=fusszeile)
    return puffer.getvalue()

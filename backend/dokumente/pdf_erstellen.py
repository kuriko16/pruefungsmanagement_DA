"""Technischer PDF-Prototyp; das endgültige Layout wird noch abgestimmt."""

from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


# Die mitgelieferte Schrift wird eingebettet, damit das PDF gleich aussieht.
schriftordner = Path(reportlab.__file__).resolve().parent / "fonts"
pdfmetrics.registerFont(TTFont("Vera", str(schriftordner / "Vera.ttf")))
pdfmetrics.registerFont(TTFont("VeraFett", str(schriftordner / "VeraBd.ttf")))
pdfmetrics.registerFontFamily("Vera", normal="Vera", bold="VeraFett")


def erstelle_pdf(titel, pruefungsjahr, angaben, dateiname):
    """Erzeugt ein PDF aus Feldnamen und Werten, ohne Daten zu verändern."""
    projektordner = Path(__file__).resolve().parents[2]
    ausgabeordner = (
        projektordner / "data" / "ausgabe"
        / pruefungsjahr.replace("/", "_") / "pdf"
    )
    ausgabeordner.mkdir(parents=True, exist_ok=True)

    # Jede Ausführung erzeugt eine neue Datei.
    zeitstempel = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dateipfad = ausgabeordner / f"{dateiname}_{zeitstempel}.pdf"

    dokument = SimpleDocTemplate(
        str(dateipfad), pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
    )
    stile = getSampleStyleSheet()
    stile["Normal"].fontName = "Vera"
    stile["Normal"].leading = 14
    stile["Title"].fontName = "VeraFett"
    stile["Title"].alignment = 0  # Titel linksbündig anzeigen.

    # escape sorgt dafür, dass z. B. & und < als normaler Text erscheinen.
    inhalt = [
        Paragraph(escape(titel), stile["Title"]),
        Paragraph(f"Prüfungsjahr: {escape(pruefungsjahr)}", stile["Normal"]),
        Spacer(1, 4 * mm),
        Paragraph("Entwurf - Layout und Pflichtfelder noch abzustimmen.", stile["Normal"]),
        Spacer(1, 8 * mm),
    ]

    # Paragraph bricht längere Texte innerhalb der Tabellenzellen um.
    zeilen = []
    for feld, wert in angaben.items():
        text = "" if wert is None else str(wert)
        zeilen.append([
            Paragraph(f"<b>{escape(feld)}</b>", stile["Normal"]),
            Paragraph(escape(text), stile["Normal"]),
        ])

    tabelle = Table(zeilen, colWidths=[55 * mm, 115 * mm])
    tabelle.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EDF2F7")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
    ]))
    inhalt.append(tabelle)
    dokument.build(inhalt)
    return dateipfad


if __name__ == "__main__":
    # Alle Personen und Zuordnungen sind frei erfunden.
    jahr = "2026/27"
    pruefung = {
        "Personen-ID": "DEMO-001",
        "Kandidat:in": "Mira Beispiel",
        "Klasse": "5XTEST",
        "Prüfungsfach": "Mathematik",
        "Prüfungsart": "mündlich",
        "Prüfer:in": "Alex Test",
        "Beisitzer:in": "Robin Muster",
    }
    zettel = erstelle_pdf("Prüfungszettel", jahr, pruefung, "pruefungszettel_demo")

    # Diese Feldauswahl dient nur dem Test, nicht als vollständige Kommission.
    kommission = {
        "Prüfungsfach": pruefung["Prüfungsfach"],
        "Prüfer:in": pruefung["Prüfer:in"],
        "Beisitzer:in": pruefung["Beisitzer:in"],
        "Termin": "Noch nicht festgelegt",
        "Raum": "Noch nicht festgelegt",
    }
    unterlagen = erstelle_pdf(
        "Kommissionsunterlagen", jahr, kommission, "kommissionsunterlagen_demo"
    )

    print(f"Prüfungszettel erstellt: {zettel}")
    print(f"Kommissionsunterlagen erstellt: {unterlagen}")
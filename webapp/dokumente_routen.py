"""Yilmaz' Dokument-Buttons. Die vorhandene Oberfläche bindet diesen Blueprint ein."""

import io
import sqlite3
from contextlib import closing

from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for

import db
from dokumente.daten_lesen import lade_dokumentdaten
from dokumente.excel_erstellen import erstelle_uebersicht, erstelle_zeitplanvorlage
from dokumente.pdf_export import dokument_pdf, excel_als_pdf, libreoffice_pfad
from dokumente.vorlagen import DokumentFehler, jahresordner, versionen

dokumente = Blueprint("dokumente", __name__)


def jahr_lesen(con):
    jahre = [r[0] for r in con.execute("SELECT bezeichnung FROM pruefungsjahr ORDER BY bezeichnung DESC")]
    gewaehlt = request.cookies.get("jahr")
    return gewaehlt if gewaehlt in jahre else (jahre[0] if jahre else None)


@dokumente.get("/dokumente")
def seite():
    with closing(db.verbinden()) as con:
        jahr = jahr_lesen(con)
        klassen = con.execute("""SELECT k.id, k.name FROM klasse k JOIN pruefungsjahr j ON j.id=k.pruefungsjahr_id
                                WHERE j.bezeichnung=? ORDER BY k.name""", (jahr,)).fetchall()
    try:
        vorhanden = versionen(jahr)
    except DokumentFehler:
        vorhanden = []
    return render_template("dokumente.html", klassen=klassen, versionen=vorhanden,
                           libreoffice=bool(libreoffice_pfad()))


@dokumente.get("/dokumente/download")
def download():
    if request.args.get("ausgabe"):
        art, _, format = request.args["ausgabe"].partition(".")
        return ausgabe(art, format)
    return ausgabe(request.args.get("art", "uebersicht"), request.args.get("format", "xlsx"))


def ausgabe(art, format):
    """Ausgabe direkt im Speicher, ohne die Datenbank oder Vorlagen zu verändern."""
    try:
        if art not in ("uebersicht", "zeitplan", "pruefungszettel", "kommission") or format not in ("xlsx", "pdf"):
            raise DokumentFehler("Diese Ausgabe wird nicht unterstützt.")
        version = request.args.get("version", "v1")
        klasse_text = request.args.get("klasse", "")
        if klasse_text and (not klasse_text.isdecimal() or int(klasse_text) < 1):
            raise DokumentFehler("Bitte eine gültige Klasse auswählen.")
        klasse_id = int(klasse_text) if klasse_text else None
        with closing(db.verbinden()) as con:
            jahr = jahr_lesen(con)
            jahrpfad = jahresordner(jahr)
            daten = lade_dokumentdaten(con, jahr, klasse_id)
        klasse = daten["klassen"][0]["name"] if len(daten["klassen"]) == 1 else "alle_Klassen"
        if art in ("pruefungszettel", "kommission"):
            if format != "pdf":
                raise DokumentFehler("Dieses Dokument gibt es als PDF.")
            inhalt = dokument_pdf(daten, art)
        else:
            if art == "zeitplan":
                if len(daten["klassen"]) != 1:
                    raise DokumentFehler("Bitte für die Zeitplanvorlage genau eine Klasse auswählen.")
                mappe = erstelle_zeitplanvorlage(jahr, klasse, version)
            else:
                mappe = erstelle_uebersicht(daten, version)
            if format == "pdf":
                inhalt = excel_als_pdf(mappe, nur_uebersicht=art == "uebersicht")
            else:
                puffer = io.BytesIO()
                mappe.save(puffer)
                inhalt = puffer.getvalue()
        # Dateinamen aus der Datenbank bekommen keine Pfad- oder Steuerzeichen.
        sicher = "".join(c if c.isalnum() or c in "_-" else "_" for c in klasse)
        dateiname = f"{art}_{sicher}_{jahrpfad}.{format}"
        antwort = send_file(io.BytesIO(inhalt), download_name=dateiname,
                            as_attachment=format != "pdf",
                            mimetype="application/pdf" if format == "pdf" else
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        antwort.headers["Cache-Control"] = "no-store"
        return antwort
    except DokumentFehler as fehler:
        flash(str(fehler), "fehler")
    except sqlite3.Error:
        flash("Die Datenbank passt noch nicht zur Dokumentenschnittstelle. Bitte das Datenmodell abstimmen.", "fehler")
    return redirect(url_for("dokumente.seite"))

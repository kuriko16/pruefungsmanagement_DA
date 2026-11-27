"""Weboberfläche (MVP) für das Prüfungsmanagementsystem – Teil Mikail Simsek.

Start am einfachsten: start.py (bzw. START_Windows.bat / START_Mac.command) -> http://localhost:9094
Start mit Docker:    docker compose up                                      -> http://localhost:9094

Aufbau: Flask liefert HTML-Seiten aus (Templates in webapp/templates). Jede Funktion mit
@app.route(...) ist eine Seite bzw. ein Formular-Ziel. Die Daten liegen in SQLite
(Schema: backend/schema.sql), der Import nutzt direkt backend/import_anmeldungen.py.

Umgesetzte User Stories: MS-01 (lokale Weboberfläche), MS-02 (Prüfer/Beisitz zuweisen),
MS-03 (Prüfungstage), MS-04 (Noten, MP/GN manuell), MS-06 (bearbeiten/löschen),
MS-07 (Import/Export per Button), MS-08 (Suche/Filter), MS-09 (Dashboard).
"""
import collections
import io
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, send_file, url_for

import db
from export_uebersicht import erstelle_uebersicht

# Den bestehenden Import aus backend/ einbinden (gleicher Code wie auf der Kommandozeile)
sys.path.insert(0, str(db.PROJEKT / "backend"))
import import_anmeldungen  # noqa: E402
from dokumente_routen import dokumente, ausgabe  # noqa: E402

app = Flask(__name__)
app.secret_key = "nur-lokal"  # nötig für flash()-Meldungen; das System läuft nur lokal
app.register_blueprint(dokumente)

NOTEN = [1, 2, 3, 4, 5]


# ---------------------------------------------------------------- Hilfsfunktionen

def aktuelles_jahr(con):
    """Das gewählte Prüfungsjahr (Cookie) oder das neueste vorhandene."""
    jahre = [z["bezeichnung"] for z in con.execute("SELECT bezeichnung FROM pruefungsjahr ORDER BY bezeichnung DESC")]
    gewaehlt = request.cookies.get("jahr")
    if gewaehlt in jahre:
        return gewaehlt, jahre
    return (jahre[0] if jahre else None), jahre


def lehrpersonen(con, nur_aktive=True):
    sql = "SELECT * FROM lehrperson" + (" WHERE aktiv=1" if nur_aktive else "") + " ORDER BY nachname, vorname"
    return con.execute(sql).fetchall()


def zahl_oder_none(wert):
    """Formularwerte sind immer Text. Leeres Feld -> None (NULL in der DB)."""
    wert = (wert or "").strip().replace(",", ".")
    return float(wert) if wert else None


def id_oder_none(wert):
    return int(wert) if wert else None


@app.context_processor
def global_fuer_templates():
    """Diese Werte stehen in jedem Template zur Verfügung (z. B. für die Jahr-Auswahl im Menü)."""
    con = db.verbinden()
    jahr, jahre = aktuelles_jahr(con)
    con.close()
    return {"jahr": jahr, "jahre": jahre, "noten": NOTEN}


@app.post("/jahr")
def jahr_waehlen():
    antwort = redirect(request.referrer or url_for("dashboard"))
    antwort.set_cookie("jahr", request.form["jahr"], max_age=60 * 60 * 24 * 365)
    return antwort


# ---------------------------------------------------------------- Dashboard (MS-09)

@app.get("/")
def dashboard():
    con = db.verbinden()
    jahr, _ = aktuelles_jahr(con)
    # Pro Klasse zählen: Kandidat:innen, Prüfungen und was davon noch fehlt.
    # Beisitz gibt es nur bei mündlichen Prüfungen, daher wird dort nur mündlich gezählt.
    klassen = con.execute("""
        SELECT k.id, k.name, k.schwerpunkt,
               COUNT(DISTINCT a.id)                                           AS kandidaten,
               COUNT(pf.id)                                                   AS pruefungen,
               SUM(pf.art = 'muendlich')                                      AS muendlich,
               SUM(pf.pruefer_id IS NULL)                                     AS ohne_pruefer,
               SUM(pf.art = 'muendlich' AND pf.beisitz_id IS NULL)            AS ohne_beisitz,
               SUM(pf.pruefungstag IS NULL)                                   AS ohne_tag,
               SUM(pf.note_mp IS NULL)                                        AS ohne_note
        FROM klasse k
        JOIN pruefungsjahr j ON j.id = k.pruefungsjahr_id
        LEFT JOIN anmeldung a ON a.klasse_id = k.id
        LEFT JOIN pruefungsfach pf ON pf.anmeldung_id = a.id
        WHERE j.bezeichnung = ?
        GROUP BY k.id ORDER BY k.name""", (jahr,)).fetchall()

    # Fortschritt in Prozent: wie viele der nötigen Einträge sind schon erledigt?
    stand = []
    for k in klassen:
        noetig = 3 * (k["pruefungen"] or 0) + (k["muendlich"] or 0)  # Prüfer + Tag + Note (+ Beisitz mündl.)
        offen = (k["ohne_pruefer"] or 0) + (k["ohne_beisitz"] or 0) + (k["ohne_tag"] or 0) + (k["ohne_note"] or 0)
        prozent = round(100 * (noetig - offen) / noetig) if noetig else 0
        stand.append({**dict(k), "prozent": prozent})

    # Notenverteilung (nur eingetragene Prüfungsnoten) als kleine Auswertung
    verteilung = dict(con.execute("""
        SELECT CAST(pf.note_mp AS INTEGER), COUNT(*) FROM pruefungsfach pf
        JOIN anmeldung a ON a.id = pf.anmeldung_id JOIN klasse k ON k.id = a.klasse_id
        JOIN pruefungsjahr j ON j.id = k.pruefungsjahr_id
        WHERE j.bezeichnung = ? AND pf.note_mp IS NOT NULL GROUP BY 1""", (jahr,)).fetchall())

    importe = con.execute("""
        SELECT l.*, SUM(m.schwere='FEHLER') AS fehler, SUM(m.schwere='WARNUNG') AS warnungen
        FROM import_lauf l LEFT JOIN import_meldung m ON m.import_lauf_id = l.id
        GROUP BY l.id ORDER BY l.id DESC LIMIT 5""").fetchall()
    con.close()
    gesamt = {s: sum((k[s] or 0) for k in klassen)
              for s in ("kandidaten", "pruefungen", "ohne_pruefer", "ohne_beisitz", "ohne_tag", "ohne_note")}
    return render_template("dashboard.html", klassen=stand, gesamt=gesamt, importe=importe,
                           verteilung=[(n, verteilung.get(n, 0)) for n in NOTEN])


# ---------------------------------------------------------------- Kandidatenliste mit Suche/Filter (MS-08)

@app.get("/kandidaten")
def kandidaten():
    con = db.verbinden()
    jahr, _ = aktuelles_jahr(con)
    q = request.args.get("q", "").strip()
    klasse = request.args.get("klasse", "")
    fach = request.args.get("fach", "")
    lehrer = request.args.get("lehrer", "")
    nur_offen = request.args.get("offen") == "1"

    # Die WHERE-Bedingungen werden je nach gesetztem Filter zusammengebaut.
    # Werte kommen immer als ?-Parameter in die Abfrage (Schutz vor SQL-Injection).
    bedingungen, parameter = ["j.bezeichnung = ?"], [jahr]
    if q:
        bedingungen.append("(kd.nachname LIKE ? OR kd.vorname LIKE ? OR kd.personen_id LIKE ?)")
        parameter += [f"%{q}%"] * 3
    if klasse:
        bedingungen.append("k.id = ?")
        parameter.append(klasse)
    if fach:
        bedingungen.append("EXISTS (SELECT 1 FROM pruefungsfach x WHERE x.anmeldung_id = a.id AND x.fach = ?)")
        parameter.append(fach)
    if lehrer:
        bedingungen.append("EXISTS (SELECT 1 FROM pruefungsfach x WHERE x.anmeldung_id = a.id "
                           "AND (x.pruefer_id = ? OR x.beisitz_id = ?))")
        parameter += [lehrer, lehrer]

    zeilen = con.execute(f"""
        SELECT a.id, kd.personen_id, kd.nachname, kd.vorname, k.name AS klasse,
               a.anzahl_schriftlich, a.anzahl_muendlich, d.titel AS da_titel,
               (SELECT COUNT(*) FROM pruefungsfach x WHERE x.anmeldung_id = a.id
                  AND (x.pruefer_id IS NULL OR x.pruefungstag IS NULL
                       OR (x.art='muendlich' AND x.beisitz_id IS NULL))) AS offen_zuweisung,
               (SELECT COUNT(*) FROM pruefungsfach x WHERE x.anmeldung_id = a.id AND x.note_mp IS NULL) AS offen_noten
        FROM anmeldung a
        JOIN kandidat kd ON kd.personen_id = a.personen_id
        JOIN klasse k ON k.id = a.klasse_id
        JOIN pruefungsjahr j ON j.id = k.pruefungsjahr_id
        LEFT JOIN anmeldung_diplomarbeit ad ON ad.anmeldung_id = a.id
        LEFT JOIN diplomarbeit d ON d.id = ad.diplomarbeit_id
        WHERE {' AND '.join(bedingungen)}
        ORDER BY k.name, kd.nachname, kd.vorname""", parameter).fetchall()
    if nur_offen:
        zeilen = [z for z in zeilen if z["offen_zuweisung"] or z["offen_noten"]]

    klassen = con.execute("""SELECT k.id, k.name FROM klasse k JOIN pruefungsjahr j ON j.id=k.pruefungsjahr_id
                             WHERE j.bezeichnung=? ORDER BY k.name""", (jahr,)).fetchall()
    faecher = [z[0] for z in con.execute("SELECT DISTINCT fach FROM pruefungsfach ORDER BY fach")]
    lehr = lehrpersonen(con, nur_aktive=False)
    con.close()
    return render_template("kandidaten.html", zeilen=zeilen, klassen=klassen, faecher=faecher,
                           lehrpersonen=lehr, filter=request.args)


# ---------------------------------------------------------------- Detail- und Bearbeitungsansicht (MS-02/03/04/06)

def lade_anmeldung(con, anmeldung_id):
    return con.execute("""
        SELECT a.*, kd.nachname, kd.vorname, kd.geburtsdatum, kd.email, kd.geschlecht,
               k.name AS klasse, k.schwerpunkt, d.id AS da_id, d.titel AS da_titel,
               d.betreuer_id, d.betreuer_text
        FROM anmeldung a
        JOIN kandidat kd ON kd.personen_id = a.personen_id
        JOIN klasse k ON k.id = a.klasse_id
        LEFT JOIN anmeldung_diplomarbeit ad ON ad.anmeldung_id = a.id
        LEFT JOIN diplomarbeit d ON d.id = ad.diplomarbeit_id
        WHERE a.id = ?""", (anmeldung_id,)).fetchone()


@app.get("/anmeldung/<int:anmeldung_id>")
def kandidat_detail(anmeldung_id):
    con = db.verbinden()
    anm = lade_anmeldung(con, anmeldung_id)
    if anm is None:
        con.close()
        flash("Diese Anmeldung gibt es nicht (mehr).", "fehler")
        return redirect(url_for("kandidaten"))
    faecher = con.execute("""SELECT * FROM pruefungsfach WHERE anmeldung_id = ?
                             ORDER BY art DESC, feld""", (anmeldung_id,)).fetchall()
    # Meldungen aus dem Import zu dieser Person (Fehlerprotokoll, JP-07)
    meldungen = con.execute("""SELECT DISTINCT schwere, regel, text FROM import_meldung
                               WHERE personen_id = ? ORDER BY schwere""", (anm["personen_id"],)).fetchall()
    lehr = lehrpersonen(con)
    con.close()
    return render_template("kandidat.html", a=anm, faecher=faecher, lehrpersonen=lehr, meldungen=meldungen)


@app.post("/anmeldung/<int:anmeldung_id>")
def kandidat_speichern(anmeldung_id):
    """Speichert Stammdaten, DA-Betreuung und alle Prüfungsfächer in einem Schritt."""
    f = request.form
    con = db.verbinden()
    anm = lade_anmeldung(con, anmeldung_id)
    con.execute("UPDATE kandidat SET nachname=?, vorname=?, email=?, geburtsdatum=? WHERE personen_id=?",
                (f["nachname"].strip(), f["vorname"].strip(), f.get("email", "").strip() or None,
                 f.get("geburtsdatum") or None, anm["personen_id"]))
    if anm["da_id"]:
        con.execute("UPDATE diplomarbeit SET betreuer_id=? WHERE id=?", (id_oder_none(f.get("betreuer_id")), anm["da_id"]))

    # Die Felder je Fach heißen z. B. "pruefer_12" (12 = id des Prüfungsfachs)
    for (fid,) in con.execute("SELECT id FROM pruefungsfach WHERE anmeldung_id=?", (anmeldung_id,)).fetchall():
        werte = {}
        for feld in ("note_jn", "note_mp", "note_gn"):
            werte[feld] = zahl_oder_none(f.get(f"{feld}_{fid}"))
            if werte[feld] is not None and not 1 <= werte[feld] <= 5:
                flash(f"Note {werte[feld]:g} ist ungültig (erlaubt 1 bis 5) und wurde nicht gespeichert.", "fehler")
                werte[feld] = None
        con.execute("""UPDATE pruefungsfach SET pruefer_id=?, beisitz_id=?, pruefungstag=?,
                       note_jn=?, note_mp=?, note_gn=? WHERE id=?""",
                    (id_oder_none(f.get(f"pruefer_{fid}")), id_oder_none(f.get(f"beisitz_{fid}")),
                     f.get(f"tag_{fid}") or None, werte["note_jn"], werte["note_mp"], werte["note_gn"], fid))
    con.commit()
    con.close()
    flash("Gespeichert.", "ok")
    return redirect(url_for("kandidat_detail", anmeldung_id=anmeldung_id))


@app.post("/anmeldung/<int:anmeldung_id>/loeschen")
def kandidat_loeschen(anmeldung_id):
    """Löscht die Anmeldung samt Prüfungsfächern. Den Kandidaten nur, wenn er sonst nirgends angemeldet ist."""
    con = db.verbinden()
    anm = lade_anmeldung(con, anmeldung_id)
    if anm:
        con.execute("DELETE FROM anmeldung WHERE id=?", (anmeldung_id,))  # ON DELETE CASCADE löscht die Fächer
        if not con.execute("SELECT 1 FROM anmeldung WHERE personen_id=?", (anm["personen_id"],)).fetchone():
            con.execute("DELETE FROM kandidat WHERE personen_id=?", (anm["personen_id"],))
        con.commit()
        flash(f"Anmeldung von {anm['vorname']} {anm['nachname']} wurde gelöscht.", "ok")
    con.close()
    return redirect(url_for("kandidaten"))


# ---------------------------------------------------------------- Sammel-Zuweisung pro Klasse und Fach (MS-02/03)

@app.route("/zuweisung", methods=["GET", "POST"])
def zuweisung():
    """Herr Angerer weist meist eine:n Prüfer:in pro Fach und Klasse zu (siehe Zeile 10 der Übersicht).
    Hier geht das für alle Kandidat:innen einer Klasse auf einmal."""
    con = db.verbinden()
    jahr, _ = aktuelles_jahr(con)
    klassen = con.execute("""SELECT k.id, k.name FROM klasse k JOIN pruefungsjahr j ON j.id=k.pruefungsjahr_id
                             WHERE j.bezeichnung=? ORDER BY k.name""", (jahr,)).fetchall()
    klasse_id = request.values.get("klasse", type=int) or (klassen[0]["id"] if klassen else None)

    if request.method == "POST":
        ueberschreiben = request.form.get("ueberschreiben") == "1"
        geaendert = 0
        # Jede Tabellenzeile schickt gruppe/pruefer/beisitz/tag; zip() legt sie zeilenweise zusammen.
        zeilen = zip(request.form.getlist("gruppe"), request.form.getlist("pruefer"),
                     request.form.getlist("beisitz"), request.form.getlist("tag"))
        for schluessel, pruefer, beisitz, tag in zeilen:
            art, fach = schluessel.split("|", 1)  # Schlüssel = "art|fach"
            for spalte, wert in (("pruefer_id", id_oder_none(pruefer)),
                                 ("beisitz_id", id_oder_none(beisitz)),
                                 ("pruefungstag", tag or None)):
                if wert is None:
                    continue  # leeres Feld = nichts ändern
                bedingung = "" if ueberschreiben else f" AND {spalte} IS NULL"
                cur = con.execute(f"""UPDATE pruefungsfach SET {spalte} = ?
                                      WHERE art = ? AND fach = ?{bedingung}
                                      AND anmeldung_id IN (SELECT id FROM anmeldung WHERE klasse_id = ?)""",
                                  (wert, art, fach, klasse_id))
                geaendert += cur.rowcount
        con.commit()
        flash(f"{geaendert} Einträge aktualisiert.", "ok")
        con.close()
        return redirect(url_for("zuweisung", klasse=klasse_id))

    # Für jede Kombination Art + Fach zeigen wir an, was aktuell eingetragen ist.
    gruppen = con.execute("""
        SELECT pf.art, pf.fach, COUNT(*) AS anzahl,
               COUNT(DISTINCT pf.pruefer_id) AS n_pruefer, MIN(pf.pruefer_id) AS pruefer_id,
               COUNT(DISTINCT pf.beisitz_id) AS n_beisitz, MIN(pf.beisitz_id) AS beisitz_id,
               COUNT(DISTINCT pf.pruefungstag) AS n_tag, MIN(pf.pruefungstag) AS tag,
               SUM(pf.pruefer_id IS NULL) AS ohne_pruefer,
               SUM(pf.beisitz_id IS NULL) AS ohne_beisitz,
               SUM(pf.pruefungstag IS NULL) AS ohne_tag
        FROM pruefungsfach pf JOIN anmeldung a ON a.id = pf.anmeldung_id
        WHERE a.klasse_id = ? GROUP BY pf.art, pf.fach
        ORDER BY pf.art DESC, pf.fach""", (klasse_id,)).fetchall()
    lehr = lehrpersonen(con)
    namen = {l["id"]: f"{l['nachname']} {l['vorname']}" for l in lehrpersonen(con, nur_aktive=False)}
    con.close()
    return render_template("zuweisung.html", klassen=klassen, klasse_id=klasse_id, gruppen=gruppen,
                           lehrpersonen=lehr, namen=namen)


# ---------------------------------------------------------------- Lehrpersonen-Stammdaten (SB-04, für MS-02)

@app.route("/lehrpersonen", methods=["GET", "POST"])
def lehrpersonen_seite():
    con = db.verbinden()
    if request.method == "POST":
        aktion = request.form.get("aktion")
        if aktion == "neu":
            try:
                con.execute("INSERT INTO lehrperson(nachname, vorname, kuerzel) VALUES (?,?,?)",
                            (request.form["nachname"].strip(), request.form["vorname"].strip(),
                             request.form.get("kuerzel", "").strip().upper() or None))
                flash("Lehrperson angelegt.", "ok")
            except Exception:
                flash("Diese Lehrperson gibt es schon.", "fehler")
        elif aktion == "umschalten":
            con.execute("UPDATE lehrperson SET aktiv = 1 - aktiv WHERE id=?", (request.form["id"],))
        elif aktion == "loeschen":
            lid = request.form["id"]
            benutzt = con.execute("""SELECT COUNT(*) FROM pruefungsfach WHERE pruefer_id=? OR beisitz_id=?""",
                                  (lid, lid)).fetchone()[0]
            if benutzt:
                flash(f"Kann nicht gelöscht werden: noch {benutzt} Zuweisungen. Stattdessen deaktivieren.", "fehler")
            else:
                con.execute("UPDATE diplomarbeit SET betreuer_id=NULL WHERE betreuer_id=?", (lid,))
                con.execute("DELETE FROM lehrperson WHERE id=?", (lid,))
                flash("Lehrperson gelöscht.", "ok")
        con.commit()
        con.close()
        return redirect(url_for("lehrpersonen_seite"))

    liste = con.execute("""
        SELECT l.*, (SELECT COUNT(*) FROM pruefungsfach WHERE pruefer_id = l.id) AS als_pruefer,
                    (SELECT COUNT(*) FROM pruefungsfach WHERE beisitz_id = l.id) AS als_beisitz
        FROM lehrperson l ORDER BY l.aktiv DESC, l.nachname, l.vorname""").fetchall()
    con.close()
    return render_template("lehrpersonen.html", liste=liste)


# ---------------------------------------------------------------- Import per Button (MS-07, ruft JP-01 auf)

@app.route("/import", methods=["GET", "POST"])
def import_seite():
    ergebnisse = []
    vorschlag = f"{date.today().year}/{str(date.today().year + 1)[2:]}"
    if request.method == "POST":
        jahr = request.form["jahr"].strip()
        con = db.verbinden()
        for datei in request.files.getlist("dateien"):
            if not datei.filename.lower().endswith(".xlsx"):
                continue
            # Die Datei wird nur kurz zwischengespeichert und danach gleich wieder gelöscht.
            with tempfile.TemporaryDirectory() as tmp:
                pfad = Path(tmp) / "upload.xlsx"
                datei.save(pfad)
                try:
                    gelesen, importiert, meldungen = import_anmeldungen.importiere_datei(
                        con, pfad, jahr, anzeigename=datei.filename)
                    zaehler = collections.Counter(m.schwere for m in meldungen)
                    # Wichtigstes zuerst: Fehler, dann Warnungen, dann Hinweise, jeweils nach Regel
                    reihenfolge = {"FEHLER": 0, "WARNUNG": 1, "HINWEIS": 2}
                    meldungen = sorted(meldungen, key=lambda m: (reihenfolge[m.schwere], m.regel))
                    ergebnisse.append({"datei": datei.filename, "gelesen": gelesen, "importiert": importiert,
                                       "zaehler": zaehler, "meldungen": meldungen})
                except Exception as fehler:  # z. B. falsches Blatt oder kaputte Datei
                    ergebnisse.append({"datei": datei.filename, "abbruch": str(fehler)})
        con.close()
        antwort = app.make_response(render_template("import.html", ergebnisse=ergebnisse, vorschlag=jahr))
        antwort.set_cookie("jahr", jahr)  # nach dem Import gleich dieses Jahr anzeigen
        return antwort
    return render_template("import.html", ergebnisse=ergebnisse, vorschlag=vorschlag)


# ---------------------------------------------------------------- Export Übersicht als Excel (MS-07)

@app.get("/export/uebersicht")
def export_uebersicht():
    return ausgabe("uebersicht", "xlsx")


db.initialisieren()

if __name__ == "__main__":
    # Port 9094 statt 5000, weil macOS den Port 5000 für AirPlay belegt.
    # host 0.0.0.0, damit es auch im Docker-Container erreichbar ist.
    app.run(host=os.environ.get("PM_HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 9094)), debug=False)

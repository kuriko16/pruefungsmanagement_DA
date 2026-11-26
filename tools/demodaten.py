#!/usr/bin/env python3
"""Demodaten-Generator: erfundene Kandidat:innen im eduFLOW-Format.

Die echten Anmeldedateien enthalten personenbezogene Daten und dürfen weder ins Repo
noch in Screenshots. Dieses Skript erzeugt Dateien mit GLEICHEM Aufbau (Blätter, Spalten,
Feldnamen PS_/PM_), aber erfundenen Namen. Damit lässt sich der komplette Ablauf
(Import -> Zuweisen -> Noten -> Export) vorführen.

Absichtlich eingebaute Auffälligkeiten, damit die Prüfregeln etwas finden:
  - 1 Anmeldung nicht verbindlich (R05 -> wird nicht importiert)
  - 1 Tippfehler in der E-Mail-Domain (R07)
  - 1 Betreuer:in in vertauschter Schreibweise (R12)

Aufruf:
  python tools/demodaten.py                 -> nur Excel-Dateien in data/demo/ erzeugen
  python tools/demodaten.py --db            -> zusätzlich importieren, Lehrpersonen anlegen
                                               und einen Teil der Zuweisungen/Noten vorbefüllen
"""
import argparse
import random
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook

PROJEKT = Path(__file__).resolve().parents[1]
AUSGABE = PROJEKT / "data" / "demo"
SCHULKENNZAHL = "900000"          # erfunden, keine echte Schulkennzahl
JAHR = "2026/27"

VORNAMEN = ["Lena", "Paul", "Sophie", "Elias", "Mia", "Jonas", "Hannah", "David", "Lea", "Felix", "Emma",
            "Lukas", "Anna", "Tobias", "Sara", "Noah", "Laura", "Simon", "Nina", "Florian", "Julia", "Ben",
            "Valentina", "Matteo", "Aylin", "Luca", "Elif", "Moritz", "Clara", "Can"]
NACHNAMEN = ["Brunner", "Lechner", "Wallner", "Berger", "Steiner", "Moser", "Hofer", "Leitner", "Pichler",
             "Fuchs", "Gruber", "Eder", "Schwarz", "Wimmer", "Auer", "Bauer", "Kaiser", "Lang", "Winkler",
             "Haas", "Koller", "Mayr", "Aigner", "Reiter", "Sommer", "Vogel", "Jäger", "Kraus", "Frank", "Weiß"]
LEHRPERSONEN = [("Aschauer", "Martin", "ASC"), ("Bichler", "Karin", "BIC"), ("Danninger", "Robert", "DAN"),
                ("Ebner", "Ulrike", "EBN"), ("Fasching", "Thomas", "FAS"), ("Gassner", "Petra", "GAS"),
                ("Holzer", "Andreas", "HOL"), ("Illek", "Sabine", "ILL"), ("Jandl", "Michael", "JAN"),
                ("Kern", "Barbara", "KER"), ("Lutz", "Stefan", "LUT"), ("Mader", "Eva", "MAD"),
                ("Nowak", "Georg", "NOW"), ("Oberhauser", "Ines", "OBE")]

# Klassen wie in den echten Vorlagen, Schwerpunkt bestimmt das Wahlfach-Feld
KLASSEN = {
    "5AHWIM": ("Maschinenbau", "PM_WF_MB", "Maschinen- und Anlagentechnik"),
    "5BHWII": ("Betriebsinformatik", "PM_WF_BI", "Softwareentwicklung und Projektmanagement / Netzwerke und Embedded Software"),
    "5CHWIL": ("Logistik", "PM_WF_LOG", "Logistik und Supply Chain Management"),
}
WAHLFAECHER = ["Religion", "Ethik", "Geografie, Geschichte und Politische Bildung", "Naturwissenschaften"]
SPF = "Betriebstechnik/Unternehmensführung und Wirtschaftsrecht"
DA_THEMEN = ["Digitale Lagerverwaltung für einen Fahrradhändler", "Energiemonitoring in der Schulwerkstatt",
             "Webshop-Optimierung für ein Familienunternehmen", "Automatisierte Dienstplanung im Pflegeheim",
             "Ersatzteillogistik in der Instandhaltung", "Barrierefreie Website für einen Sportverein",
             "Kostenrechnung für eine Kleinserienfertigung", "Ticketsystem für den IT-Support"]

KOPF = ["Nachname", "Vorname", "Klasse", "Empfänger*in E-Mail", "Personen-ID", "Personentyp", "Geschlecht",
        "Geburtsdatum", "Schulkennzahl", "Status", "Gesehen am", "Ausgefüllt am", "Klausurart",
        "Ausbildungsschwerpunkt", "Titel der Diplomarbeit:", "Diplomarbeitsbetreuer*in:", "PS_AM", "PS_FT",
        "PS_D_oder_E1", "PS_Deutsch", "PS_Englisch", "PM_D", "PM_E", "PM_SPF", "PM_WF_BI", "PM_WF_LOG",
        "PM_WF_MB", "Kenntnisnahme nächster Termin", "Verbindliche Anmeldung"]


def erzeuge_klasse(klasse, rnd, nummern):
    schwerpunkt, wf_feld, wf_fach = KLASSEN[klasse]
    zeilen = []
    themen = rnd.sample(DA_THEMEN, 3)
    betreuer = rnd.sample(LEHRPERSONEN, 3)
    for i in range(rnd.randint(10, 13)):
        vn, nn = rnd.choice(VORNAMEN), rnd.choice(NACHNAMEN)
        pid = SCHULKENNZAHL + f"{next(nummern):08d}"
        geb = date(2007, 1, 1) + timedelta(days=rnd.randint(0, 600))
        gruppe = i % 3
        b = betreuer[gruppe]
        z = dict.fromkeys(KOPF)
        z.update({
            "Nachname": nn, "Vorname": vn, "Klasse": klasse, "Personen-ID": pid, "Personentyp": "Schüler*in",
            "Empfänger*in E-Mail": f"{vn[0].lower()}{nn.lower()}@student.tgm.ac.at".replace("ä", "ae").replace("ß", "ss"),
            "Geschlecht": rnd.choice(["männlich", "weiblich"]), "Geburtsdatum": geb.strftime("%d.%m.%Y"),
            "Schulkennzahl": SCHULKENNZAHL, "Status": "Abgeschlossen", "Ausgefüllt am": "12.11.2026",
            "Ausbildungsschwerpunkt": schwerpunkt, "Titel der Diplomarbeit:": themen[gruppe],
            "Diplomarbeitsbetreuer*in:": f"{b[1]} {b[0]}",
            "PS_AM": "Angewandte Mathematik", "PS_FT": "Fachtheorie", "PM_SPF": SPF,
            wf_feld: rnd.choice(WAHLFAECHER + [wf_fach] * 3),
            "Kenntnisnahme nächster Termin": "ja", "Verbindliche Anmeldung": "ja",
        })
        if rnd.random() < 0.8:   # 3 schriftlich + 3 mündlich: eine Sprache schriftlich, die andere mündlich
            sprache = rnd.choice(["Deutsch", "Englisch"])
            z["Klausurart"] = "3 schriftliche Klausuren und 3 mündliche Prüfungen"
            z["PS_D_oder_E1"] = sprache
            z["PM_E" if sprache == "Deutsch" else "PM_D"] = "Englisch" if sprache == "Deutsch" else "Deutsch"
        else:                    # 4 schriftlich + 2 mündlich
            z["Klausurart"] = "4 schriftliche Klausuren und 2 mündliche Prüfungen"
            z["PS_Deutsch"], z["PS_Englisch"] = "Deutsch", "Englisch"
        zeilen.append(z)

    # Absichtliche Auffälligkeiten (siehe Kopfkommentar)
    if klasse == "5AHWIM":
        zeilen[2]["Verbindliche Anmeldung"] = "nein"
    if klasse == "5BHWII":
        zeilen[4]["Empfänger*in E-Mail"] = zeilen[4]["Empfänger*in E-Mail"].replace("tgm.ac.at", "tgm.ac.ta")
        zeilen[3]["Diplomarbeitsbetreuer*in:"] = f"{betreuer[0][0]} {betreuer[0][1]}"  # Nachname Vorname
    return zeilen


def schreibe_xlsx(klasse, zeilen):
    """Gleicher Aufbau wie der eduFLOW-Export: zwei Blätter, Kopfzeile = Feldnamen."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Teilnehmer und Ergebnisse"
    ws.append(KOPF)
    for z in zeilen:
        ws.append([z[k] for k in KOPF])
    ws2 = wb.create_sheet("Ergebnisse-Optionsfelder")
    ws2.append(["Nachname", "Vorname", "Personen-ID", "Geburtsdatum"])
    for z in zeilen:
        ws2.append([z["Nachname"], z["Vorname"], z["Personen-ID"], z["Geburtsdatum"]])
    AUSGABE.mkdir(parents=True, exist_ok=True)
    pfad = AUSGABE / f"DEMO_Anmeldung_{klasse}.xlsx"
    wb.save(pfad)
    return pfad


def befuelle_db(dateien):
    """Importiert die Demodateien über den echten Import und trägt einen Teil der manuellen Daten ein."""
    sys.path.insert(0, str(PROJEKT / "webapp"))
    sys.path.insert(0, str(PROJEKT / "backend"))
    import db
    import import_anmeldungen
    db.initialisieren()
    con = sqlite3.connect(db.DB_PFAD)
    con.execute("PRAGMA foreign_keys = ON")
    con.executemany("INSERT OR IGNORE INTO lehrperson(nachname, vorname, kuerzel) VALUES (?,?,?)", LEHRPERSONEN)
    for d in dateien:
        g, i, m = import_anmeldungen.importiere_datei(con, d, JAHR)
        print(f"{d.name}: {i}/{g} importiert, {len(m)} Meldungen")

    # Vorbefüllung, damit das Dashboard unterschiedliche Stände zeigt:
    # 5AHWIM fast fertig, 5BHWII halb, 5CHWIL noch leer
    rnd = random.Random(7)
    lehrer = [r[0] for r in con.execute("SELECT id FROM lehrperson")]
    for klasse, anteil in (("5AHWIM", 0.95), ("5BHWII", 0.5)):
        faecher = con.execute("""SELECT DISTINCT pf.art, pf.fach FROM pruefungsfach pf
                                 JOIN anmeldung a ON a.id = pf.anmeldung_id JOIN klasse k ON k.id = a.klasse_id
                                 WHERE k.name = ?""", (klasse,)).fetchall()
        for n, (art, fach) in enumerate(faecher):
            if rnd.random() > anteil:
                continue
            p, b = rnd.sample(lehrer, 2)
            tag = ("2027-05-0" + str(5 + n % 3)) if art == "schriftlich" else ("2027-06-1" + str(n % 2))
            con.execute("""UPDATE pruefungsfach SET pruefer_id=?, beisitz_id=CASE WHEN art='muendlich' THEN ? END,
                           pruefungstag=? WHERE art=? AND fach=? AND anmeldung_id IN
                           (SELECT a.id FROM anmeldung a JOIN klasse k ON k.id=a.klasse_id WHERE k.name=?)""",
                        (p, b, tag, art, fach, klasse))
        # Noten nur für schriftliche Prüfungen (die sind im Schuljahr zuerst dran)
        for (fid,) in con.execute("""SELECT pf.id FROM pruefungsfach pf JOIN anmeldung a ON a.id=pf.anmeldung_id
                                     JOIN klasse k ON k.id=a.klasse_id WHERE k.name=? AND pf.art='schriftlich'""",
                                  (klasse,)).fetchall():
            if rnd.random() < anteil:
                con.execute("UPDATE pruefungsfach SET note_jn=?, note_mp=? WHERE id=?",
                            (rnd.choice([1, 2, 2, 3, 3, 4]), rnd.choice([1, 2, 2, 3, 3, 4, 4, 5]), fid))
    con.commit()
    con.close()
    print(f"Datenbank: {db.DB_PFAD}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", action="store_true", help="Demodaten auch in die Datenbank laden")
    ap.add_argument("--seed", type=int, default=2026, help="Zufallswert (gleicher Wert = gleiche Daten)")
    args = ap.parse_args()
    rnd = random.Random(args.seed)
    nummern = iter(range(10000001, 10099999))
    dateien = [schreibe_xlsx(k, erzeuge_klasse(k, rnd, nummern)) for k in KLASSEN]
    for d in dateien:
        print(f"erzeugt: {d.relative_to(PROJEKT)}")
    if args.db:
        befuelle_db(dateien)


if __name__ == "__main__":
    main()

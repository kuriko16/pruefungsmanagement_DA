#!/usr/bin/env python3
"""Import-Prototyp: eduFLOW-Anmeldungen zur Reife- und Diplompruefung -> SQLite.

Liest das Blatt "Teilnehmer und Ergebnisse" der Anmeldedateien, prueft die Daten,
schreibt sie ins Schema aus schema.sql und erzeugt ein Fehlerprotokoll.

Regeln:
  FEHLER   -> Datensatz wird NICHT importiert
  WARNUNG  -> Datensatz wird importiert, Auffaelligkeit steht im Protokoll
  HINWEIS  -> nur Information (z. B. Leerzeichen am Rand)

Im Protokoll stehen nur Personen-IDs, keine Namen (Datenschutz).

Aufruf:
  python import_anmeldungen.py --jahr 2025/26 --db ../data/pruefung.db \
      --report ../data/fehlerbericht.md  datei1.xlsx datei2.xlsx ...
"""
import argparse
import collections
import datetime as dt
import re
import sqlite3
import warnings
from dataclasses import dataclass
from pathlib import Path

import openpyxl

warnings.filterwarnings("ignore", message="Cannot parse header or footer")

SHEET = "Teilnehmer und Ergebnisse"
CHECK_SHEET = "Ergebnisse-Optionsfelder"
EXPECTED_MAIL_DOMAIN = "student.tgm.ac.at"
KLAUSURART_RE = re.compile(r"(\d)\s+schriftliche.*?(\d)\s+m(?:ü|ue)ndliche", re.I)


@dataclass
class Meldung:
    schwere: str
    regel: str
    personen_id: str | None
    text: str


def clean(value):
    """Text bereinigen: Leerzeichen am Rand und doppelte Leerzeichen entfernen."""
    if value is None:
        return None
    if isinstance(value, str):
        value = re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()
        return value or None
    return value


def to_iso_date(value):
    if isinstance(value, (dt.datetime, dt.date)):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, str):
        for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
            try:
                return dt.datetime.strptime(value.strip(), fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass
    return None


def read_sheet(wb, name):
    """Blatt als Liste von Dicts lesen (Kopfzeile = Spaltennamen, leere Spalten ignorieren)."""
    ws = wb[name]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    out = []
    for r in rows[1:]:
        rec = {h: v for h, v in zip(header, r) if h}
        if rec.get("Nachname") or rec.get("Personen-ID"):
            out.append(rec)
    return out


def name_key(text):
    """Vergleichsschluessel fuer Personennamen, unabhaengig von der Reihenfolge."""
    return tuple(sorted(clean(text).lower().split())) if clean(text) else ()


def validate(rows, klasse, check_rows):
    meldungen = []
    pid_counts = collections.Counter(clean(r.get("Personen-ID")) for r in rows)
    check_by_id = {clean(r.get("Personen-ID")): r for r in check_rows}

    for r in rows:
        pid = clean(r.get("Personen-ID"))

        def add(schwere, regel, text):
            meldungen.append(Meldung(schwere, regel, pid, text))

        if not pid:
            add("FEHLER", "R01", "Personen-ID fehlt")
            continue
        if pid_counts[pid] > 1:
            add("FEHLER", "R02", "Personen-ID kommt mehrfach vor")
        kennzahl = clean(r.get("Schulkennzahl"))
        if not (pid.isdigit() and len(pid) == 14 and kennzahl and pid.startswith(str(kennzahl))):
            add("WARNUNG", "R03", "Personen-ID hat nicht das erwartete Format (14 Ziffern, beginnt mit Schulkennzahl)")
        if clean(r.get("Status")) != "Abgeschlossen":
            add("WARNUNG", "R04", f"Status ist '{clean(r.get('Status'))}', erwartet 'Abgeschlossen'")
        if clean(r.get("Verbindliche Anmeldung")) != "ja":
            add("FEHLER", "R05", "Anmeldung ist nicht verbindlich bestaetigt")
        if clean(r.get("Kenntnisnahme nächster Termin")) != "ja":
            add("WARNUNG", "R06", "Kenntnisnahme des naechsten Termins fehlt")
        mail = clean(r.get("Empfänger*in E-Mail")) or ""
        if mail.split("@")[-1].lower() != EXPECTED_MAIL_DOMAIN:
            add("WARNUNG", "R07", f"E-Mail-Domain '{mail.split('@')[-1]}' weicht von {EXPECTED_MAIL_DOMAIN} ab (Tippfehler?)")
        raw_ws = [k for k, v in r.items() if isinstance(v, str) and v != v.strip()]
        if raw_ws:
            add("HINWEIS", "R08", f"Leerzeichen am Rand in: {', '.join(raw_ws)}")

        art = clean(r.get("Klausurart")) or ""
        m = KLAUSURART_RE.search(art)
        n_ps = sum(1 for k, v in r.items() if k.startswith("PS_") and clean(v))
        n_pm = sum(1 for k, v in r.items() if k.startswith("PM_") and clean(v))
        if not m:
            add("FEHLER", "R09", f"Klausurart nicht lesbar: '{art}'")
        elif (int(m.group(1)), int(m.group(2))) != (n_ps, n_pm):
            add("FEHLER", "R09", f"Klausurart '{art}' passt nicht zu den Faechern ({n_ps} schriftlich, {n_pm} muendlich)")

        if clean(r.get("Klasse")) != klasse:
            add("WARNUNG", "R10", f"Klasse '{clean(r.get('Klasse'))}' passt nicht zum Dateinamen ({klasse})")

        chk = check_by_id.get(pid)
        if chk is None:
            add("WARNUNG", "R11", f"Personen-ID fehlt im Blatt '{CHECK_SHEET}'")
        else:
            a, b = to_iso_date(r.get("Geburtsdatum")), to_iso_date(chk.get("Geburtsdatum"))
            if a != b:
                add("WARNUNG", "R11", "Geburtsdatum unterscheidet sich zwischen den Blaettern")

        if not clean(r.get("Titel der Diplomarbeit:")):
            add("WARNUNG", "R13", "Titel der Diplomarbeit fehlt")

    # Gleicher Titel, aber Betreuer in verschiedenen Schreibweisen
    by_title = collections.defaultdict(list)
    for r in rows:
        by_title[clean(r.get("Titel der Diplomarbeit:")) or ""].append(r)
    for titel, group in by_title.items():
        schreibweisen = {clean(g.get("Diplomarbeitsbetreuer*in:")) for g in group}
        if len(schreibweisen) > 1 and len({name_key(s) for s in schreibweisen}) == 1:
            for g in group:
                meldungen.append(Meldung(
                    "WARNUNG", "R12", clean(g.get("Personen-ID")),
                    "Betreuer*in bei gleichem Titel in unterschiedlicher Schreibweise "
                    "(Vorname Nachname / Nachname Vorname)"))
    return meldungen


def import_rows(con, rows, meldungen, klasse, jahr):
    fehler_ids = {m.personen_id for m in meldungen if m.schwere == "FEHLER"}
    cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO pruefungsjahr(bezeichnung) VALUES (?)", (jahr,))
    jahr_id = cur.execute("SELECT id FROM pruefungsjahr WHERE bezeichnung=?", (jahr,)).fetchone()[0]
    schwerpunkt = next((clean(r.get("Ausbildungsschwerpunkt")) for r in rows if r.get("Ausbildungsschwerpunkt")), None)
    cur.execute("INSERT OR IGNORE INTO klasse(name, schwerpunkt, pruefungsjahr_id) VALUES (?,?,?)",
                (klasse, schwerpunkt, jahr_id))
    klasse_id = cur.execute("SELECT id FROM klasse WHERE name=? AND pruefungsjahr_id=?", (klasse, jahr_id)).fetchone()[0]

    imported = 0
    for r in rows:
        pid = clean(r.get("Personen-ID"))
        if not pid or pid in fehler_ids:
            continue
        cur.execute(
            """INSERT INTO kandidat(personen_id, nachname, vorname, geburtsdatum, geschlecht, email, schulkennzahl)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(personen_id) DO UPDATE SET nachname=excluded.nachname, vorname=excluded.vorname,
                 geburtsdatum=excluded.geburtsdatum, geschlecht=excluded.geschlecht, email=excluded.email""",
            (pid, clean(r.get("Nachname")), clean(r.get("Vorname")), to_iso_date(r.get("Geburtsdatum")),
             clean(r.get("Geschlecht")), clean(r.get("Empfänger*in E-Mail")), clean(r.get("Schulkennzahl"))))
        art = clean(r.get("Klausurart"))
        m = KLAUSURART_RE.search(art or "")
        cur.execute(
            """INSERT INTO anmeldung(personen_id, klasse_id, status, ausgefuellt_am, klausurart,
                                     anzahl_schriftlich, anzahl_muendlich, kenntnisnahme, verbindlich)
               VALUES (?,?,?,?,?,?,?,?,?)
               ON CONFLICT(personen_id, klasse_id) DO UPDATE SET status=excluded.status,
                 ausgefuellt_am=excluded.ausgefuellt_am, klausurart=excluded.klausurart,
                 anzahl_schriftlich=excluded.anzahl_schriftlich, anzahl_muendlich=excluded.anzahl_muendlich,
                 kenntnisnahme=excluded.kenntnisnahme, verbindlich=excluded.verbindlich""",
            (pid, klasse_id, clean(r.get("Status")), clean(r.get("Ausgefüllt am")), art,
             int(m.group(1)) if m else None, int(m.group(2)) if m else None,
             clean(r.get("Kenntnisnahme nächster Termin")), clean(r.get("Verbindliche Anmeldung"))))
        anm_id = cur.execute("SELECT id FROM anmeldung WHERE personen_id=? AND klasse_id=?", (pid, klasse_id)).fetchone()[0]

        # Faecher neu schreiben (idempotent). Manuell gepflegte Spalten (Pruefer, Noten) gehen dabei
        # verloren, daher in der echten Version nur fehlende Faecher ergaenzen.
        cur.execute("DELETE FROM pruefungsfach WHERE anmeldung_id=?", (anm_id,))
        for feld, wert in r.items():
            if feld and (feld.startswith("PS_") or feld.startswith("PM_")) and clean(wert):
                cur.execute("INSERT INTO pruefungsfach(anmeldung_id, art, feld, fach) VALUES (?,?,?,?)",
                            (anm_id, "schriftlich" if feld.startswith("PS_") else "muendlich", feld, clean(wert)))

        titel = clean(r.get("Titel der Diplomarbeit:"))
        if titel:
            cur.execute("INSERT OR IGNORE INTO diplomarbeit(titel, betreuer_text, pruefungsjahr_id) VALUES (?,?,?)",
                        (titel, clean(r.get("Diplomarbeitsbetreuer*in:")), jahr_id))
            da_id = cur.execute("SELECT id FROM diplomarbeit WHERE titel=? AND pruefungsjahr_id=?", (titel, jahr_id)).fetchone()[0]
            cur.execute("INSERT OR REPLACE INTO anmeldung_diplomarbeit(anmeldung_id, diplomarbeit_id) VALUES (?,?)",
                        (anm_id, da_id))
        imported += 1
    return imported


def write_report(path, results):
    lines = ["# Fehlerprotokoll Import Anmeldungen", "",
             f"Erstellt am {dt.datetime.now():%d.%m.%Y %H:%M}. Es werden nur Personen-IDs genannt, keine Namen.", ""]
    for datei, gelesen, importiert, meldungen in results:
        lines += [f"## {datei}", "", f"Zeilen gelesen: {gelesen}, importiert: {importiert}", ""]
        if not meldungen:
            lines += ["Keine Auffaelligkeiten.", ""]
            continue
        summary = collections.Counter((m.schwere, m.regel) for m in meldungen)
        lines += ["| Schwere | Regel | Anzahl |", "| --- | --- | --- |"]
        lines += [f"| {s} | {r} | {n} |" for (s, r), n in sorted(summary.items())]
        lines += ["", "| Schwere | Regel | Personen-ID | Meldung |", "| --- | --- | --- | --- |"]
        lines += [f"| {m.schwere} | {m.regel} | {m.personen_id or '-'} | {m.text} |" for m in meldungen]
        lines.append("")
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dateien", nargs="+", help="eduFLOW-Anmeldedateien (.xlsx)")
    ap.add_argument("--jahr", required=True, help="Pruefungsjahr, z. B. 2025/26")
    ap.add_argument("--db", default="pruefung.db")
    ap.add_argument("--report", default="fehlerbericht.md")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    con.executescript((Path(__file__).parent / "schema.sql").read_text(encoding="utf-8"))
    results = []
    for datei in args.dateien:
        klasse = Path(datei).stem.split("_")[-1]
        wb = openpyxl.load_workbook(datei, data_only=True)
        rows = read_sheet(wb, SHEET)
        check_rows = read_sheet(wb, CHECK_SHEET) if CHECK_SHEET in wb.sheetnames else []
        meldungen = validate(rows, klasse, check_rows)
        importiert = import_rows(con, rows, meldungen, klasse, args.jahr)
        con.execute("INSERT INTO import_lauf(datei, zeitpunkt, zeilen_gelesen, zeilen_importiert) VALUES (?,?,?,?)",
                    (Path(datei).name, dt.datetime.now().isoformat(timespec="seconds"), len(rows), importiert))
        lauf_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
        con.executemany("INSERT INTO import_meldung(import_lauf_id, schwere, regel, personen_id, text) VALUES (?,?,?,?,?)",
                        [(lauf_id, m.schwere, m.regel, m.personen_id, m.text) for m in meldungen])
        con.commit()
        results.append((Path(datei).name, len(rows), importiert, meldungen))
        zaehler = collections.Counter(m.schwere for m in meldungen)
        print(f"{Path(datei).name}: {len(rows)} gelesen, {importiert} importiert, "
              f"{zaehler['FEHLER']} Fehler, {zaehler['WARNUNG']} Warnungen, {zaehler['HINWEIS']} Hinweise")
    write_report(args.report, results)
    print(f"Fehlerprotokoll: {args.report}")


if __name__ == "__main__":
    main()

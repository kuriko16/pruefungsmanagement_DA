"""Vorführung des Importsystems im Terminal, Schritt für Schritt.

Aufruf (im Ordner import_erweitert):
  python demo.py                       Vorführung mit Pausen (Enter drücken)
  python demo.py --ohne-pause          alles auf einmal
  python demo.py --live                statt 5BHWII die Live-Kopie ergebnisse/demo_live_5BHWII.xlsx
                                       importieren (vorher in Excel etwas kaputt machen und speichern)
Alle Daten sind erfunden.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from collections import defaultdict
from pathlib import Path

from backend.import_anmeldungen import FEHLER, INFO, WARNUNG, importiere_alles
from backend.qualitaet import metriken
from backend.ziel_db import ZielDB
from testdaten.erzeuge_dummy import stelle_sicher

HIER = Path(__file__).resolve().parent
TD = HIER / "testdaten"
LP, SOK, NOT = TD / "lehrpersonen_dummy.csv", TD / "sokrates_export_dummy.csv", TD / "noten_dummy.csv"
KLASSEN = {k: TD / f"anmeldung_{k}.xlsx" for k in ("5AHWIM", "5BHWII", "5CHWIL")}
LIVE = HIER / "ergebnisse" / "demo_live_5BHWII.xlsx"

os.system("")  # schaltet unter Windows die Farben im Terminal ein
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Namen wie „Dvořák“ sicher ausgeben
ROT, GELB, GRUEN, BLAU, FETT, AUS = "\033[91m", "\033[93m", "\033[92m", "\033[96m", "\033[1m", "\033[0m"
FARBE = {FEHLER: ROT, WARNUNG: GELB, INFO: BLAU}
PAUSE = True


def titel(nr: int, text: str) -> None:
    if PAUSE:
        input(f"\n{FETT}[Enter] weiter zu Schritt {nr}{AUS} ")
    print(f"\n{FETT}{'=' * 78}\n Schritt {nr}: {text}\n{'=' * 78}{AUS}")


def zeige_anmeldungen(db: ZielDB, prot) -> None:
    meldungen = defaultdict(list)
    for m in prot.meldungen:
        if m.regel.startswith("R") and m.person != "-":
            meldungen[m.person].append(m)
    importiert = {f"{r['nachname']} {r['vorname']} ({r['klasse']})" for r in db.conn.execute(
        "SELECT s.nachname, s.vorname, s.klasse FROM anmeldung JOIN schueler s USING(personen_id)")}
    personen = sorted(set(meldungen) | importiert, key=lambda p: (p.rsplit("(", 1)[-1], p))
    for m in prot.meldungen:
        if m.person == "-":
            print(f" {FARBE[m.stufe]}{m.stufe}{AUS} {m.datei}: {m.regel}: {m.text}")
    klasse_vorher = None
    abgelehnt = 0
    for p in personen:
        klasse = p.rsplit("(", 1)[-1].rstrip(")")
        if klasse != klasse_vorher:
            print(f"\n {FETT}{klasse}{AUS}")
            klasse_vorher = klasse
        name = p.rsplit(" (", 1)[0]
        fehler = [m for m in meldungen[p] if m.stufe == FEHLER]
        warn = [m for m in meldungen[p] if m.stufe == WARNUNG]
        if fehler:
            abgelehnt += 1
            mehr = f" (+{len(fehler) - 1})" if len(fehler) > 1 else ""
            print(f"   {name:<20}{ROT}{'ABGELEHNT':<13}{AUS}{fehler[0].regel}: {fehler[0].text[:80]}{mehr}")
        elif warn:
            print(f"   {name:<20}{GELB}{'OK, Hinweis':<13}{AUS}{warn[0].regel}: {warn[0].text}")
        else:
            print(f"   {name:<20}{GRUEN}{'IMPORTIERT':<13}{AUS}")
    print(f"\n {GRUEN}{len(importiert)} importiert{AUS}, {ROT}{abgelehnt} abgelehnt{AUS}")


def main() -> None:
    stelle_sicher()  # Dummy-Excel erzeugen, falls nicht vorhanden
    global PAUSE
    ap = argparse.ArgumentParser()
    ap.add_argument("--ohne-pause", action="store_true")
    ap.add_argument("--live", action="store_true", help="Live-Kopie von 5BHWII importieren")
    a = ap.parse_args()
    PAUSE = not a.ohne_pause and sys.stdin.isatty()

    dateien = dict(KLASSEN)
    if a.live:
        if not LIVE.exists():
            LIVE.parent.mkdir(exist_ok=True)
            shutil.copy(KLASSEN["5BHWII"], LIVE)
            print(f"Live-Kopie angelegt: {LIVE}\nIn Excel öffnen, etwas ändern, speichern, schließen, nochmal starten.")
            return
        dateien["5BHWII"] = LIVE

    print(f"{FETT}Importsystem Anmeldungen & Zeugnisdaten, Vorführung mit erfundenen Daten{AUS}")
    print(" Anmeldungen: " + ", ".join(p.name for p in dateien.values()))
    print(f" Stammdaten:  {LP.name}, {SOK.name}\n Noten:       {NOT.name}")

    # 1 ---------------------------------------------------------------------
    titel(1, "Stammdaten laden (Lehrpersonen, Sokrates)")
    db = ZielDB()
    importiere_alles(db, LP, SOK)
    print(f" {len(db.lehrpersonen())} Lehrpersonen, {len(db.schueler())} Schüler:innen mit Personen-ID geladen")
    print(" Klassen: 5AHWIM (Maschinenbau), 5BHWII (Betriebsinformatik), 5CHWIL (Logistik)")

    # 2 ---------------------------------------------------------------------
    titel(2, "Anmeldungen der 3 Klassen importieren und prüfen (14 Regeln)")
    prot = importiere_alles(db, LP, SOK, list(dateien.values()))
    zeige_anmeldungen(db, prot)
    print("\n Nicht übernommen (Datenminimierung): E-Mail, Geschlecht, Geburtsdatum, Formular-Zeitstempel")

    # 3 ---------------------------------------------------------------------
    titel(3, "Betreuer:innen-Abgleich: verschiedene Schreibweisen")
    for r in db.conn.execute("""SELECT d.titel, l.vorname || ' ' || l.nachname AS lp, l.personen_id,
                                       COUNT(a.personen_id) AS n
                                FROM diplomarbeit d JOIN lehrperson l ON l.personen_id = d.betreuer_id
                                JOIN anmeldung a ON a.da_id = d.da_id GROUP BY d.da_id ORDER BY d.titel"""):
        print(f" {r['titel']:<45} {r['n']} Pers. -> {GRUEN}{r['lp']} ({r['personen_id']}){AUS}")
    print("\n In den Dateien stehen z. B. „Aigner Theresa“, „Brunner, Klaus“, „Prof. DI Ruth Engel“, „frank bernhard“.")
    print(f" Mehrdeutig („Lukas Martin“ passt auf zwei Lehrpersonen) -> {ROT}abgelehnt statt geraten{AUS}.")

    # 4 ---------------------------------------------------------------------
    titel(4, "Noten importieren und prüfen")
    prot_n = importiere_alles(db, LP, SOK, noten=NOT)
    for m in prot_n.meldungen:
        print(f" {FARBE[m.stufe]}{m.stufe:<8}{AUS} Zeile {m.zeile:<3} {m.person:<15} {m.regel}: {m.text}")
    anz = db.conn.execute("SELECT COUNT(*) FROM pruefung").fetchone()[0]
    print(f"\n {GRUEN}{anz} gültige Noten gespeichert{AUS}, {ROT}{len(prot_n.meldungen)} Zeilen abgelehnt{AUS}")

    # 5 ---------------------------------------------------------------------
    titel(5, "Schutz manueller Daten beim erneuten Import")
    pid, teil = "99990000000201", "PS_AM"
    alt = db.pruefung(pid, teil)
    neue_note = 5 if alt["note"] != 5 else 4
    print(f" Ilić Nina, {teil}. Vorher (aus Import):  Note {alt['note']}, Quelle '{alt['quelle_note']}'")
    db.manuell_setzen(pid, teil, "note", neue_note)
    db.commit()
    print(f" Lehrperson korrigiert von Hand auf Note {neue_note} -> Quelle 'manuell'")
    print(" Jetzt wird die Notendatei ein zweites Mal importiert ...")
    prot_r = importiere_alles(db, LP, SOK, noten=NOT)
    neu = db.pruefung(pid, teil)
    farbe = GRUEN if neu["note"] == neue_note else ROT
    print(f" Nachher:                            {farbe}Note {neu['note']}, Quelle '{neu['quelle_note']}'{AUS}")
    for m in prot_r.meldungen:
        if m.regel == "N07":
            print(f" {BLAU}INFO{AUS} {m.text}")
    print(f" -> {GRUEN}Die händische Korrektur bleibt erhalten.{AUS}")

    # 6 ---------------------------------------------------------------------
    titel(6, "Datenqualität")
    for dim, werte in metriken(db).items():
        print(f" {FETT}{dim}{AUS}")
        for k, v in werte.items():
            print(f"   {k:<30} {v}")

    print(f"\n{FETT}Fertig.{AUS} Alle Details: python zeige_ergebnis.py -> ergebnisse/ergebnis_dummy.xlsx")


if __name__ == "__main__":
    main()

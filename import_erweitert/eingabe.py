"""Eine Anmeldung oder Note von Hand eintippen und sofort prüfen lassen.

Aufruf (im Ordner import_erweitert):  python eingabe.py
Bei jeder Frage steht ein gültiger Vorschlag in [Klammern]. Enter übernimmt ihn,
eigene Eingabe ersetzt ihn, '-' lässt das Feld leer. So kann man gezielt EINEN
Fehler einbauen. Es wird nichts gespeichert (Datenbank nur im Arbeitsspeicher).
"""
from __future__ import annotations

import csv
import os
import sys
import tempfile
from pathlib import Path

from backend import fachkonfig as fk
from backend.import_anmeldungen import (
    FEHLER, INFO, WARNUNG, Person, Protokoll, importiere_alles, importiere_noten, pruefe_person,
)
from backend.normalisierung import norm_klasse
from backend.ziel_db import ZielDB
from testdaten.erzeuge_dummy import stelle_sicher

HIER = Path(__file__).resolve().parent
TD = HIER / "testdaten"

os.system("")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROT, GELB, GRUEN, BLAU, FETT, GRAU, AUS = ("\033[91m", "\033[93m", "\033[92m", "\033[96m",
                                           "\033[1m", "\033[90m", "\033[0m")
FARBE = {FEHLER: ROT, WARNUNG: GELB, INFO: BLAU}

VORSCHLAG_NOTE = [
    ("Personen-ID", "personen_id", "99990000000102"),
    ("Prüfungsteil (" + ", ".join(fk.PRUEFUNGSTEILE) + ")", "pruefungsteil", "PS_AM"),
    ("Note (1-5)", "note", "2"),
    ("Prüfer:in (Kürzel)", "pruefer_kuerzel", "AIG"),
    ("Beisitzer:in (Kürzel)", "beisitzer_kuerzel", "BRU"),
]


def frage(text: str, vorschlag: str) -> str:
    antwort = input(f"  {text} {GRAU}[{vorschlag}]{AUS}: ")
    if antwort.strip() == "-":  # "-" = Feld absichtlich leer lassen
        return ""
    return antwort if antwort.strip() else vorschlag


def ergebnis(prot: Protokoll, ok_text: str) -> None:
    print()
    if not prot.meldungen:
        print(f"  {GRUEN}{FETT}OK{AUS}{GRUEN}: {ok_text}{AUS}")
        return
    gezeigt = set()
    for m in prot.meldungen:  # gleiche Meldung nur einmal zeigen
        if (m.stufe, m.regel, m.text) in gezeigt:
            continue
        gezeigt.add((m.stufe, m.regel, m.text))
        print(f"  {FARBE[m.stufe]}{FETT}{m.stufe}{AUS} {m.regel}: {m.text}")
    if not any(m.stufe == FEHLER for m in prot.meldungen):
        print(f"  {GRUEN}-> trotzdem {ok_text}{AUS}")
    else:
        print(f"  {ROT}-> wird NICHT importiert{AUS}")


def pruefe_anmeldung(db: ZielDB) -> None:
    print(f"\n{FETT}Neue Anmeldung{AUS} {GRAU}(Enter = Vorschlag, '-' = Feld leer lassen){AUS}")
    nachname = frage("Nachname", "Birkner")
    vorname = frage("Vorname", "Jonas")
    klasse = frage("Klasse (5AHWIM, 5BHWII, 5CHWIL)", "5AHWIM")
    pid = frage("Personen-ID", "99990000000102")
    kl = fk.KLASSEN.get(norm_klasse(klasse), fk.KLASSEN["5AHWIM"])
    variante = frage("Klausuren: 3 = 3 schriftl.+3 mündl., 4 = 4 schriftl.+2 mündl.", "3")
    w = {
        "Klausurart": {"3": fk.KLAUSUR_3_3, "4": fk.KLAUSUR_4_2}.get(variante, variante),
        "Ausbildungsschwerpunkt": frage("Ausbildungsschwerpunkt", kl["schwerpunkt"]),
        "Titel der Diplomarbeit:": frage("Titel der Diplomarbeit", "Smarte Stundenplanung"),
        "Diplomarbeitsbetreuer*in:": frage("Betreuer:in", "Theresa Aigner"),
        "PS_AM": "Angewandte Mathematik", "PS_FT": "Fachtheorie", "PM_SPF": fk.PM_SPF,
    }
    if variante == "4":
        w["PS_Deutsch"], w["PS_Englisch"] = "Deutsch", "Englisch"
    else:
        schriftlich = frage("Sprache schriftlich (Deutsch/Englisch)", "Englisch")
        andere = "Deutsch" if schriftlich == "Englisch" else "Englisch"
        muendlich = frage("Sprache mündlich", andere)
        w["PS_D_oder_E1"] = schriftlich
        w["PM_D" if muendlich == "Deutsch" else "PM_E"] = muendlich
    w[kl["wahlfach_feld"]] = frage(f"Wahlfach ({kl['wahlfach_feld']})", sorted(kl["wahlfaecher"])[0])
    w["Verbindliche Anmeldung"] = frage("Verbindliche Anmeldung (ja/leer)", "ja")
    w["Kenntnisnahme nächster Termin"] = "ja"
    status = frage("Formular-Status", "Abgeschlossen")

    p = Person("Eingabe", 2, nachname, vorname, klasse, pid, status, w)
    prot = Protokoll()
    pruefe_person(p, db.lehrpersonen(), db.schueler(), prot)
    ergebnis(prot, "würde importiert")


def pruefe_note(db: ZielDB) -> None:
    print(f"\n{FETT}Neue Note{AUS} {GRAU}(Enter = Vorschlag){AUS}")
    werte = {feld: frage(text, vorschlag) for text, feld, vorschlag in VORSCHLAG_NOTE}
    with tempfile.TemporaryDirectory() as tmp:
        pfad = Path(tmp) / "eingabe.csv"
        with open(pfad, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=list(werte), delimiter=";")
            w.writeheader()
            w.writerow(werte)
        prot = Protokoll()
        importiere_noten(pfad, db, prot)
        db.rollback()  # nichts dauerhaft speichern
    ergebnis(prot, "würde gespeichert")


def hilfe(db: ZielDB) -> None:
    print(f"\n{FETT}Gültige Daten zum Ausprobieren{AUS}")
    for k in fk.KLASSEN:
        print(f"  {FETT}{k}{AUS} ({fk.KLASSEN[k]['schwerpunkt']}): " + ", ".join(
            f"{s['nachname']} {s['vorname']} ({s['personen_id'][-3:]})" for s in db.schueler() if s["klasse"] == k))
        print(f"    Wahlfächer: {', '.join(sorted(fk.KLASSEN[k]['wahlfaecher']))}")
    print("  Personen-ID = 9999000000 + die drei Ziffern in Klammern, z. B. 99990000000201")
    print("  Lehrpersonen: " + ", ".join(
        f"{l['vorname']} {l['nachname']} ({l['kuerzel']})" for l in db.lehrpersonen()))
    print(f"\n{FETT}Ideen für Fehler{AUS}: Klasse '5DHWIL' · Klasse '5BHWII' bei Birkner · Vorname 'Hans' · "
          "Personen-ID '99990000000555' · Betreuer 'Lukas Martin' · Wahlfach 'Kochen' · "
          "Sprache mündlich = schriftlich · Status 'In Bearbeitung' · Note '6' · Prüfer = Beisitzer")


def main() -> None:
    stelle_sicher()  # Dummy-Excel erzeugen, falls nicht vorhanden
    db = ZielDB()
    importiere_alles(db, TD / "lehrpersonen_dummy.csv", TD / "sokrates_export_dummy.csv")
    print(f"{FETT}Prüfung einzelner Eingaben{AUS} (erfundene Daten, nichts wird gespeichert)")
    print(f"{GRAU}Hinweis: Geprüft wird erst, wenn alle Fragen beantwortet sind.{AUS}")
    while True:
        wahl = input(f"\n{FETT}[a]{AUS} Anmeldung  {FETT}[n]{AUS} Note  {FETT}[h]{AUS} Hilfe  "
                     f"{FETT}[q]{AUS} Ende: ").strip().lower()
        if wahl == "a":
            pruefe_anmeldung(db)
        elif wahl == "n":
            pruefe_note(db)
        elif wahl == "h":
            hilfe(db)
        elif wahl == "q":  # nur q beendet, ein versehentliches Enter nicht
            break


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print()

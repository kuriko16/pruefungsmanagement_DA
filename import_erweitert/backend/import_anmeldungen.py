"""Import der Anmeldungen zur Reife- und Diplomprüfung, der Diplomarbeiten und der Noten.

Ablauf (siehe docs/ERKLAERUNG.md):
  1. Stammdaten laden: Lehrpersonen (CSV) und Sokrates-Export (CSV)
  2. Anmelde-Excel lesen. Zwei Formate werden erkannt:
       - eduFLOW-Export (breit): eine Zeile pro Person, mit Personen-ID
       - Langformat: eine Zeile pro Person und Feld (Spalten Feld/Wert)
  3. 14 Prüfregeln (R01-R14) anwenden, alles ins Fehlerprotokoll
  4. Nur fehlerfreie Personen schreiben (Warnungen sind erlaubt)
  5. Noten importieren (N01-N06), manuell gepflegte Werte bleiben unangetastet (N07)

Grundsatz: Bei einem FEHLER wird die Person nicht importiert. Es wird nie geraten.

Aufruf:
  python -m backend.import_anmeldungen --db pruefung.sqlite \
      --lehrpersonen testdaten/lehrpersonen_dummy.csv \
      --sokrates testdaten/sokrates_export_dummy.csv \
      --anmeldung testdaten/anmeldung_5AHWIM.xlsx testdaten/anmeldung_5BHWII.xlsx \
      --noten testdaten/noten_dummy.csv --protokoll protokoll.csv
"""
from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path

from openpyxl import load_workbook

from . import fachkonfig as fk
from .normalisierung import KLASSEN_MUSTER, name_tokens, norm_klasse, norm_text
from .ziel_db import ZielDB

BLATT = "Teilnehmer und Ergebnisse"
NAME_SPALTEN = ["Nachname", "Vorname", "Klasse"]
MAX_TEAMGROESSE = 4  # Annahme, mit Schule klären
FEHLER, WARNUNG, INFO = "FEHLER", "WARNUNG", "INFO"
TITEL, BETREUER = "Titel der Diplomarbeit:", "Diplomarbeitsbetreuer*in:"


# --- Fehlerprotokoll ---------------------------------------------------------
@dataclass
class Meldung:
    regel: str
    stufe: str
    datei: str
    zeile: int | str
    person: str
    text: str


class Protokoll:
    def __init__(self) -> None:
        self.meldungen: list[Meldung] = []

    def melde(self, regel, stufe, datei, zeile, person, text) -> None:
        self.meldungen.append(Meldung(regel, stufe, datei, zeile, person, text))

    def hat_fehler(self, person: str) -> bool:
        return any(m.person == person and m.stufe == FEHLER for m in self.meldungen)

    def regeln(self, stufe: str | None = None) -> set[str]:
        return {m.regel for m in self.meldungen if stufe is None or m.stufe == stufe}

    def speichere(self, pfad: str | Path) -> None:
        with open(pfad, "w", newline="", encoding="utf-8-sig") as fh:
            w = csv.DictWriter(fh, fieldnames=list(Meldung.__dataclass_fields__), delimiter=";")
            w.writeheader()
            w.writerows(asdict(m) for m in self.meldungen)


@dataclass
class Person:
    """Eine Anmeldung, wie sie aus der Datei kommt (noch ungeprüft)."""
    datei: str
    zeile: int
    nachname: str = ""
    vorname: str = ""
    klasse_roh: str = ""
    personen_id: str = ""
    status: str | None = None          # nur im eduFLOW-Export vorhanden
    werte: dict = field(default_factory=dict)
    # werden bei der Prüfung gesetzt
    klasse: str = ""
    sokrates_id: str = ""
    betreuer_id: str = ""

    @property
    def anzeige(self) -> str:
        name = f"{self.nachname} {self.vorname}".strip() or f"Zeile {self.zeile}"
        return f"{name} ({norm_klasse(self.klasse_roh) or '?'})"


# --- Einlesen ----------------------------------------------------------------
def lies_csv(pfad: str | Path) -> list[dict]:
    with open(pfad, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def lade_stammdaten(db: ZielDB, lehrpersonen_csv, sokrates_csv) -> None:
    for r in lies_csv(lehrpersonen_csv):
        db.speichere_lehrperson(r["personen_id"], r["kuerzel"], r["vorname"], r["nachname"])
    for r in lies_csv(sokrates_csv):
        db.speichere_schueler(r["personen_id"], r["nachname"], r["vorname"], norm_klasse(r["klasse"]))


def _text(v) -> str:
    return "" if v is None else str(v).strip()


def _bekannte_spalte(name: str) -> bool:
    return (name in fk.ANTWORTFELDER or name in fk.STAMMSPALTEN or name in fk.NICHT_UEBERNOMMEN
            or name in NAME_SPALTEN or re.fullmatch(r"Erw\. Daten ?\d+", name) is not None or name == "")


def lies_anmeldung(pfad: str | Path, prot: Protokoll) -> list[Person]:
    """Liest eine Anmeldedatei. R01 (Aufbau), R04 (unbekannte Spalten/Felder), R08 (Duplikate)."""
    datei = Path(pfad).name
    wb = load_workbook(pfad, read_only=True, data_only=True)
    try:  # read_only hält die Datei offen -> immer schließen (sonst unter Windows gesperrt)
        if BLATT not in wb.sheetnames:
            prot.melde("R01", FEHLER, datei, "-", "-", f"Blatt '{BLATT}' fehlt")
            return []
        zeilen = list(wb[BLATT].iter_rows(values_only=True))
    finally:
        wb.close()
    if not zeilen:
        prot.melde("R01", FEHLER, datei, 1, "-", "Blatt ist leer")
        return []
    kopf = [_text(c) for c in zeilen[0]]
    fehlend = [s for s in NAME_SPALTEN if s not in kopf]
    if fehlend:
        prot.melde("R01", FEHLER, datei, 1, "-", f"Spalten fehlen: {', '.join(fehlend)}")
        return []
    if "Feld" in kopf and "Wert" in kopf:
        return _lies_langformat(kopf, zeilen[1:], datei, prot)
    return _lies_eduflow(kopf, zeilen[1:], datei, prot)


def _lies_eduflow(kopf, zeilen, datei, prot) -> list[Person]:
    """eduFLOW-Export: eine Zeile pro Person, Antworten in eigenen Spalten."""
    if not any(f in kopf for f in fk.ANTWORTFELDER):
        prot.melde("R01", FEHLER, datei, 1, "-", "Weder Feld/Wert-Spalten noch eduFLOW-Antwortspalten gefunden")
        return []
    for name in kopf:
        if not _bekannte_spalte(name):
            prot.melde("R04", WARNUNG, datei, 1, "-", f"Unbekannte Spalte '{name}' wird ignoriert")
    idx = {name: i for i, name in enumerate(kopf) if name}
    personen = []
    for nr, z in enumerate(zeilen, start=2):
        if all(c in (None, "") for c in z):
            continue
        hole = lambda s: _text(z[idx[s]]) if s in idx and idx[s] < len(z) else ""  # noqa: E731
        p = Person(datei, nr, hole("Nachname"), hole("Vorname"), hole("Klasse"), hole("Personen-ID"),
                   hole("Status") if "Status" in idx else None)
        p.werte = {f: hole(f) for f in fk.ANTWORTFELDER if f in idx}
        personen.append(p)
    return _pruefe_duplikate(personen, prot)


def _lies_langformat(kopf, zeilen, datei, prot) -> list[Person]:
    """Langformat: eine Zeile pro Person und Feld."""
    idx = {name: i for i, name in enumerate(kopf) if name}
    personen: dict[tuple, Person] = {}
    for nr, z in enumerate(zeilen, start=2):
        if all(c in (None, "") for c in z):
            continue
        hole = lambda s: _text(z[idx[s]]) if s in idx and idx[s] < len(z) else ""  # noqa: E731
        key = (norm_text(hole("Nachname")), norm_text(hole("Vorname")), norm_klasse(hole("Klasse")))
        p = personen.setdefault(key, Person(datei, nr, hole("Nachname"), hole("Vorname"), hole("Klasse"),
                                            hole("Personen-ID")))
        feld, wert = hole("Feld"), hole("Wert")
        if feld not in fk.ANTWORTFELDER:
            prot.melde("R04", WARNUNG, datei, nr, p.anzeige, f"Unbekanntes Feld '{feld}' ignoriert")
        elif feld in p.werte:
            gleich = p.werte[feld] == wert
            prot.melde("R08", WARNUNG if gleich else FEHLER, datei, nr, p.anzeige,
                       f"Feld '{feld}' mehrfach" + ("" if gleich else " mit unterschiedlichen Werten"))
        else:
            p.werte[feld] = wert
    return list(personen.values())


def _pruefe_duplikate(personen: list[Person], prot) -> list[Person]:
    """R08 im eduFLOW-Format: gleiche Personen-ID oder gleicher Name+Klasse doppelt."""
    gesehen: dict[tuple, Person] = {}
    for p in personen:
        for key in ({("id", p.personen_id)} if p.personen_id else set()) | {
                ("name", norm_text(p.nachname), norm_text(p.vorname), norm_klasse(p.klasse_roh))}:
            if key in gesehen:
                prot.melde("R08", FEHLER, p.datei, p.zeile, p.anzeige,
                           f"Person doppelt (auch in Zeile {gesehen[key].zeile})")
                prot.melde("R08", FEHLER, p.datei, gesehen[key].zeile, gesehen[key].anzeige,
                           f"Person doppelt (auch in Zeile {p.zeile})")
                break
            gesehen[key] = p
    return personen


# --- Abgleich ----------------------------------------------------------------
def finde_lehrperson(roh: str, lehrpersonen) -> list:
    """Alle Lehrpersonen, auf die der Freitext passt.

    Erlaubt sind "Vorname Nachname" und "Nachname Vorname". Mit Komma
    ("Nachname, Vorname") ist die Reihenfolge eindeutig.
    """
    woerter, hat_komma = name_tokens(roh)
    treffer = []
    for lp in lehrpersonen:
        v, n = name_tokens(lp["vorname"])[0], name_tokens(lp["nachname"])[0]
        if woerter == n + v or (not hat_komma and woerter == v + n):
            treffer.append(lp)
    return treffer


def _gleich(a: str, b: str) -> bool:
    return norm_text(a) == norm_text(b)


# --- Prüfung -----------------------------------------------------------------
def pruefe_person(p: Person, db_lehrpersonen, db_schueler, prot: Protokoll) -> None:
    """Regeln R02, R03, R05, R06, R07, R09-R12, R14 für eine Person."""
    a, w = p.anzeige, p.werte
    melde = lambda regel, text, stufe=FEHLER: prot.melde(regel, stufe, p.datei, p.zeile, a, text)  # noqa: E731

    # R02 Name vollständig
    if not p.nachname or not p.vorname:
        melde("R02", "Nachname oder Vorname leer")

    # R03 Klasse gültig und bekannt
    p.klasse = norm_klasse(p.klasse_roh)
    if not KLASSEN_MUSTER.match(p.klasse) or p.klasse not in fk.KLASSEN:
        melde("R03", f"Klasse '{p.klasse_roh}' ungültig oder nicht in der Abteilung "
                     f"({', '.join(fk.KLASSEN)})")
    elif p.klasse != p.klasse_roh:
        melde("R03", f"Klasse '{p.klasse_roh}' zu '{p.klasse}' korrigiert", WARNUNG)
    kl = fk.KLASSEN.get(p.klasse)

    # R05 Pflichtfelder (abhängig von Klasse und Klausurart)
    leer = [f for f in fk.pflichtfelder(p.klasse, w.get("Klausurart", "")) if not w.get(f)]
    if leer:
        melde("R05", f"Pflichtfeld leer/fehlt: {', '.join(leer)}")

    # R06 erlaubte Werte
    def erlaubt(feld, werte):
        if w.get(feld) and w[feld] not in werte:
            melde("R06", f"'{w[feld]}' ist für {feld} nicht erlaubt")
    erlaubt("Klausurart", fk.KLAUSURARTEN)
    erlaubt("PS_AM", {"Angewandte Mathematik"})
    erlaubt("PS_FT", {"Fachtheorie"})
    erlaubt("PS_D_oder_E1", {"Deutsch", "Englisch"})
    erlaubt("PM_SPF", {fk.PM_SPF})
    if kl:
        erlaubt("Ausbildungsschwerpunkt", {kl["schwerpunkt"]})
        erlaubt(kl["wahlfach_feld"], kl["wahlfaecher"])
        for fremd in fk.WAHLFACH_FELDER - {kl["wahlfach_feld"]}:
            if w.get(fremd):
                melde("R06", f"{fremd} gehört nicht zur Klasse {p.klasse} (dort {kl['wahlfach_feld']})")

    # R07 verbindlich angemeldet und Formular abgeschlossen
    if w.get("Verbindliche Anmeldung") and norm_text(w["Verbindliche Anmeldung"]) != "ja":
        melde("R07", "Verbindliche Anmeldung nicht bestätigt")
    if p.status is not None and p.status != "Abgeschlossen":
        melde("R07", f"Formular-Status '{p.status or 'leer'}' statt 'Abgeschlossen'")

    # R09/R10 Sokrates: über Personen-ID, sonst über Name + Klasse
    if p.personen_id:
        treffer = [s for s in db_schueler if s["personen_id"] == p.personen_id]
        if not treffer:
            melde("R09", f"Personen-ID {p.personen_id} nicht im Sokrates-Export")
        else:
            s = treffer[0]
            abw = [f"{feld} '{ist}' ≠ Sokrates '{soll}'" for feld, ist, soll in (
                ("Nachname", p.nachname, s["nachname"]), ("Vorname", p.vorname, s["vorname"]),
                ("Klasse", p.klasse, s["klasse"])) if not _gleich(ist, soll)]
            if abw:
                melde("R10", "Personen-ID passt nicht zu den Daten: " + "; ".join(abw))
            else:
                p.sokrates_id = s["personen_id"]
    else:
        treffer = [s for s in db_schueler if _gleich(s["nachname"], p.nachname)
                   and _gleich(s["vorname"], p.vorname) and s["klasse"] == p.klasse]
        if not treffer:
            melde("R09", "Nicht im Sokrates-Export gefunden (Name + Klasse)")
        elif len(treffer) > 1:
            melde("R10", "Mehrere Sokrates-Treffer: " + ", ".join(t["personen_id"] for t in treffer))
        else:
            p.sokrates_id = treffer[0]["personen_id"]

    # R11/R12 Betreuer:in
    roh = w.get(BETREUER, "")
    if roh:
        lp = finde_lehrperson(roh, db_lehrpersonen)
        if not lp:
            melde("R11", f"Betreuer:in '{roh}' nicht in Stammdaten")
        elif len(lp) > 1:
            melde("R12", f"Betreuer:in '{roh}' mehrdeutig: "
                  + ", ".join(f"{l['vorname']} {l['nachname']} ({l['personen_id']})" for l in lp))
        else:
            p.betreuer_id = lp[0]["personen_id"]

    # R14 Sprachkombination passt zur Klausurart
    art = w.get("Klausurart")
    if art == fk.KLAUSUR_3_3 and w.get("PS_D_oder_E1") in ("Deutsch", "Englisch"):
        schriftlich = w["PS_D_oder_E1"]
        muendlich_feld, muendlich_wert = ("PM_E", "Englisch") if schriftlich == "Deutsch" else ("PM_D", "Deutsch")
        falsch_feld = "PM_D" if muendlich_feld == "PM_E" else "PM_E"
        if w.get(muendlich_feld) != muendlich_wert:
            melde("R14", f"Schriftlich {schriftlich} -> mündlich muss {muendlich_feld} = {muendlich_wert} sein")
        if w.get(falsch_feld):
            melde("R14", f"{falsch_feld} darf nicht gefüllt sein, wenn schriftlich {schriftlich} gewählt ist")
        if w.get("PS_Deutsch") or w.get("PS_Englisch"):
            melde("R14", "PS_Deutsch/PS_Englisch gehören zur Variante 4 schriftlich + 2 mündlich")
    elif art == fk.KLAUSUR_4_2:
        if w.get("PS_Deutsch", "Deutsch") != "Deutsch" or w.get("PS_Englisch", "Englisch") != "Englisch":
            melde("R14", "Bei 4 schriftlichen Klausuren: PS_Deutsch = Deutsch und PS_Englisch = Englisch")
        for f in ("PS_D_oder_E1", "PM_D", "PM_E"):
            if w.get(f):
                melde("R14", f"{f} gehört zur Variante 3 schriftlich + 3 mündlich")


def pruefe_teams(personen: list[Person], prot: Protokoll) -> None:
    """R13: Personen mit gleichem DA-Titel bilden ein Team mit gleicher Betreuung."""
    teams: dict[str, list[Person]] = defaultdict(list)
    for p in personen:
        if not prot.hat_fehler(p.anzeige) and p.werte.get(TITEL):
            teams[norm_text(p.werte[TITEL])].append(p)
    for mitglieder in teams.values():
        betreuer = {m.betreuer_id for m in mitglieder}
        if len(betreuer) > 1 or len(mitglieder) > MAX_TEAMGROESSE:
            grund = ("unterschiedliche Betreuer:innen" if len(betreuer) > 1
                     else f"mehr als {MAX_TEAMGROESSE} Personen")
            for m in mitglieder:
                prot.melde("R13", FEHLER, m.datei, m.zeile, m.anzeige, f"Diplomarbeitsteam inkonsistent: {grund}")


def anmeldedaten(p: Person) -> dict:
    """Übersetzt die Formularfelder in die Zielspalten."""
    w = p.werte
    if w.get("Klausurart") == fk.KLAUSUR_4_2:
        schriftlich, muendlich = "Deutsch und Englisch", None
    else:
        schriftlich = w.get("PS_D_oder_E1")
        muendlich = w.get("PM_D") or w.get("PM_E")
    return {
        "klausurart": w.get("Klausurart"),
        "schwerpunkt": w.get("Ausbildungsschwerpunkt"),
        "sprache_schriftlich": schriftlich,
        "sprache_muendlich": muendlich,
        "pm_spf": w.get("PM_SPF"),
        "wahlfach": w.get(fk.KLASSEN[p.klasse]["wahlfach_feld"]),
        "kenntnisnahme": int(norm_text(w.get("Kenntnisnahme nächster Termin")) == "ja"),
    }


def importiere_anmeldungen(pfade, db: ZielDB, prot: Protokoll) -> int:
    """Liest eine oder mehrere Klassendateien, prüft alle gemeinsam (Teams über Klassen hinweg)."""
    if isinstance(pfade, (str, Path)):
        pfade = [pfade]
    personen = [p for pfad in pfade for p in lies_anmeldung(pfad, prot)]
    lehrpersonen, schueler = db.lehrpersonen(), db.schueler()
    for p in personen:
        pruefe_person(p, lehrpersonen, schueler, prot)
    # dieselbe Person in zwei Dateien
    ids = defaultdict(list)
    for p in personen:
        if p.sokrates_id:
            ids[p.sokrates_id].append(p)
    for gruppe in ids.values():
        if len({x.datei for x in gruppe}) > 1:
            for x in gruppe:
                prot.melde("R08", FEHLER, x.datei, x.zeile, x.anzeige, "Person in mehreren Dateien angemeldet")
    pruefe_teams(personen, prot)
    gut = [p for p in personen if not prot.hat_fehler(p.anzeige)]
    for p in gut:
        da_id = db.speichere_diplomarbeit(p.werte[TITEL], p.betreuer_id)
        db.speichere_anmeldung(p.sokrates_id, da_id, anmeldedaten(p))
    return len(gut)


# --- Noten -------------------------------------------------------------------
def importiere_noten(pfad, db: ZielDB, prot: Protokoll) -> int:
    datei = Path(pfad).name
    schueler_ids = {s["personen_id"] for s in db.schueler()}
    kuerzel = {lp["kuerzel"]: lp["personen_id"] for lp in db.lehrpersonen()}
    gesehen: set[tuple] = set()
    gute = []
    for nr, r in enumerate(lies_csv(pfad), start=2):
        pid, teil = r["personen_id"].strip(), r["pruefungsteil"].strip()
        anzahl_vorher = len(prot.meldungen)

        def f(regel, text):
            prot.melde(regel, FEHLER, datei, nr, pid, text)

        if pid not in schueler_ids:
            f("N01", "Personen-ID unbekannt")
        if teil not in fk.PRUEFUNGSTEILE:
            f("N02", f"Prüfungsteil '{teil}' unbekannt")
        try:
            note = int(r["note"])
            if not 1 <= note <= 5:
                raise ValueError
        except ValueError:
            note = None
            f("N03", f"Note '{r['note']}' ist keine ganze Zahl von 1 bis 5")
        for rolle in ("pruefer_kuerzel", "beisitzer_kuerzel"):
            if r[rolle].strip() not in kuerzel:
                f("N04", f"{rolle} '{r[rolle]}' unbekannt")
        if r["pruefer_kuerzel"].strip() == r["beisitzer_kuerzel"].strip():
            f("N05", "Prüfer:in und Beisitzer:in sind dieselbe Person")
        if (pid, teil) in gesehen:
            f("N06", "Note für diesen Prüfungsteil doppelt in der Datei")
        gesehen.add((pid, teil))
        if len(prot.meldungen) == anzahl_vorher:
            gute.append((nr, pid, teil, {"note": note,
                                         "pruefer_id": kuerzel[r["pruefer_kuerzel"].strip()],
                                         "beisitzer_id": kuerzel[r["beisitzer_kuerzel"].strip()]}))
    for nr, pid, teil, werte in gute:
        for feld in db.importiere_pruefungswerte(pid, teil, werte):
            prot.melde("N07", INFO, datei, nr, pid,
                       f"{teil}: '{feld}' wurde manuell gepflegt und nicht überschrieben")
    return len(gute)


# --- Gesamtlauf --------------------------------------------------------------
def importiere_alles(db: ZielDB, lehrpersonen, sokrates, anmeldung=None, noten=None) -> Protokoll:
    """Eine Transaktion: Entweder alles Gültige wird geschrieben oder bei Absturz nichts."""
    prot = Protokoll()
    try:
        lade_stammdaten(db, lehrpersonen, sokrates)
        if anmeldung:
            importiere_anmeldungen(anmeldung, db, prot)
        if noten:
            importiere_noten(noten, db, prot)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return prot


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", required=True)
    ap.add_argument("--lehrpersonen", required=True)
    ap.add_argument("--sokrates", required=True)
    ap.add_argument("--anmeldung", nargs="*", help="eine oder mehrere Klassendateien")
    ap.add_argument("--noten")
    ap.add_argument("--protokoll", default="importprotokoll.csv")
    a = ap.parse_args(argv)
    db = ZielDB(a.db)
    try:
        prot = importiere_alles(db, a.lehrpersonen, a.sokrates, a.anmeldung, a.noten)
    finally:
        db.close()
    prot.speichere(a.protokoll)
    zaehler = defaultdict(int)
    for m in prot.meldungen:
        zaehler[m.stufe] += 1
    print(f"Fertig. Fehler: {zaehler[FEHLER]}, Warnungen: {zaehler[WARNUNG]}, Infos: {zaehler[INFO]} -> {a.protokoll}")


if __name__ == "__main__":
    main()

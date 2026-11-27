"""Tests mit erfundenen Daten aus testdaten/ (siehe FEHLERFAELLE.md).

Start:  python -m unittest discover -s tests -t . -v   (im Ordner import_erweitert)
"""
from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from openpyxl import Workbook

from backend import fachkonfig as fk
from backend.import_anmeldungen import FEHLER, INFO, WARNUNG, finde_lehrperson, importiere_alles, main
from backend.normalisierung import norm_klasse, norm_text
from backend.qualitaet import metriken
from backend.ziel_db import ZielDB
from testdaten import erzeuge_dummy

TD = Path(__file__).resolve().parent.parent / "testdaten"
LP, SOK, NOT = TD / "lehrpersonen_dummy.csv", TD / "sokrates_export_dummy.csv", TD / "noten_dummy.csv"
KLASSEN = [TD / f"anmeldung_{k}.xlsx" for k in ("5AHWIM", "5BHWII", "5CHWIL")]
LANG = TD / "anmeldung_5AHWIM_langformat.xlsx"


_TMP = None


def setUpModule():
    """Testdaten frisch in einen Temp-Ordner schreiben.

    So stören in Excel geöffnete Dateien in testdaten/ die Tests nicht."""
    global _TMP, TD, LP, SOK, NOT, KLASSEN, LANG
    _TMP = tempfile.TemporaryDirectory()
    TD = Path(_TMP.name)
    erzeuge_dummy.main(TD)
    LP, SOK, NOT = TD / "lehrpersonen_dummy.csv", TD / "sokrates_export_dummy.csv", TD / "noten_dummy.csv"
    KLASSEN = [TD / f"anmeldung_{k}.xlsx" for k in ("5AHWIM", "5BHWII", "5CHWIL")]
    LANG = TD / "anmeldung_5AHWIM_langformat.xlsx"


def tearDownModule():
    erzeuge_dummy.OUT = Path(erzeuge_dummy.__file__).resolve().parent
    _TMP.cleanup()


def pid(n: int) -> str:
    return f"9999{n:010d}"


def meldungen(prot, regel, person=None, stufe=None):
    return [m for m in prot.meldungen if m.regel == regel and (person is None or person in str(m.person))
            and (stufe is None or m.stufe == stufe)]


def angemeldet(db) -> set[str]:
    return {r[0] for r in db.conn.execute("SELECT personen_id FROM anmeldung")}


class Normalisierung(unittest.TestCase):
    def test_umlaute_und_akzente(self):
        self.assertEqual(norm_text("Öztürk"), norm_text("Oeztuerk"))
        self.assertEqual(norm_text("Dvořák"), "dvorak")

    def test_klasse(self):
        self.assertEqual(norm_klasse("5 b hwii"), "5BHWII")


class Fachkonfiguration(unittest.TestCase):
    def test_drei_klassen_mit_schwerpunkt(self):
        self.assertEqual({k: v["schwerpunkt"] for k, v in fk.KLASSEN.items()},
                         {"5AHWIM": "Maschinenbau", "5BHWII": "Betriebsinformatik", "5CHWIL": "Logistik"})

    def test_pflichtfelder_je_variante(self):
        self.assertIn("PS_D_oder_E1", fk.pflichtfelder("5AHWIM", fk.KLAUSUR_3_3))
        vier = fk.pflichtfelder("5CHWIL", fk.KLAUSUR_4_2)
        self.assertIn("PS_Deutsch", vier)
        self.assertIn("PM_WF_LOG", vier)
        self.assertNotIn("PS_D_oder_E1", vier)


class Betreuerabgleich(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        db = ZielDB()
        importiere_alles(db, LP, SOK)
        cls.lp = db.lehrpersonen()

    def ids(self, roh):
        return [l["personen_id"] for l in finde_lehrperson(roh, self.lp)]

    def test_gueltige_schreibweisen(self):
        for roh, p in [("Theresa Aigner", "LP-1001"), ("Aigner Theresa", "LP-1001"),
                       ("Brunner, Klaus", "LP-1002"), ("Prof. DI Ruth Engel", "LP-1005"),
                       ("frank bernhard", "LP-1006"), ("  Theresa   Aigner ", "LP-1001"),
                       ("Dr. Aigner Theresa, MSc", "LP-1001")]:
            with self.subTest(roh=roh):
                self.assertEqual(self.ids(roh), [p])

    def test_komma_ist_eindeutig(self):
        self.assertEqual(self.ids("Klaus, Brunner"), [])
        self.assertEqual(self.ids("Lukas, Martin"), ["LP-1007"])

    def test_mehrdeutig_und_unbekannt(self):
        self.assertEqual(sorted(self.ids("Lukas Martin")), ["LP-1007", "LP-1008"])
        self.assertEqual(self.ids("Herbert Unbekannt"), [])
        self.assertEqual(self.ids("Aigner"), [])  # nur Nachname reicht nicht


class DreiKlassenImport(unittest.TestCase):
    """Kompletter Lauf über die drei Klassendateien (eduFLOW-Format)."""

    @classmethod
    def setUpClass(cls):
        cls.db = ZielDB()
        cls.prot = importiere_alles(cls.db, LP, SOK, KLASSEN, NOT)
        cls.ok = angemeldet(cls.db)

    def fehler(self, regel, person):
        return meldungen(self.prot, regel, person, FEHLER)

    def test_genau_die_gueltigen_importiert(self):
        self.assertEqual(self.ok, {pid(n) for n in (101, 102, 107, 108, 201, 202, 203, 301, 302)})

    def test_fehlerfaelle(self):
        faelle = [("E01", "R11", "Cerny"), ("E02", "R06", "Dvořák"), ("E02", "R05", "Dvořák"),
                  ("E03", "R07", "Ertl"), ("E04", "R14", "Feichtinger"), ("E05", "R09", "Lindner"),
                  ("E06", "R10", "Moser"), ("E07", "R06", "Nagl"), ("E08", "R12", "Öztürk Deniz"),
                  ("E09", "R08", "Prinz"), ("E10", "R02", "Reiter"), ("E11", "R05", "Schuster"),
                  ("E12", "R03", "Toth"), ("E13", "R06", "Uhl"), ("E14", "R05", "Vogl"),
                  ("E15", "R13", "Wagner"), ("E15", "R13", "Yilmaz")]
        for kennung, regel, person in faelle:
            with self.subTest(kennung=kennung, regel=regel):
                self.assertTrue(self.fehler(regel, person))

    def test_unbekannte_spalte_nur_warnung(self):
        self.assertTrue(meldungen(self.prot, "R04", stufe=WARNUNG))

    def test_klasse_wird_korrigiert(self):
        self.assertTrue(meldungen(self.prot, "R03", "Kern", WARNUNG))
        self.assertIn(pid(203), self.ok)

    def test_sokrates_ueber_personen_id_trotz_umlaut(self):
        # Datei: "Oeztuerk Aylin", Sokrates: "Öztürk Aylin", gleiche Personen-ID
        self.assertIn(pid(302), self.ok)

    def test_variante_4_plus_2(self):
        r = self.db.conn.execute("SELECT * FROM anmeldung WHERE personen_id=?", (pid(107),)).fetchone()
        self.assertEqual(r["klausurart"], fk.KLAUSUR_4_2)
        self.assertEqual(r["sprache_schriftlich"], "Deutsch und Englisch")
        self.assertIsNone(r["sprache_muendlich"])

    def test_variante_3_plus_3_sprachen(self):
        r = self.db.conn.execute("SELECT * FROM anmeldung WHERE personen_id=?", (pid(102),)).fetchone()
        self.assertEqual((r["sprache_schriftlich"], r["sprache_muendlich"]), ("Englisch", "Deutsch"))

    def test_wahlfach_je_klasse(self):
        for p, klasse in [(pid(101), "5AHWIM"), (pid(201), "5BHWII"), (pid(302), "5CHWIL")]:
            wf = self.db.conn.execute("SELECT wahlfach FROM anmeldung WHERE personen_id=?", (p,)).fetchone()[0]
            self.assertIn(wf, fk.KLASSEN[klasse]["wahlfaecher"])

    def test_team_mit_zwei_schreibweisen_des_betreuers(self):
        r = self.db.conn.execute(
            "SELECT COUNT(*), MIN(d.betreuer_id) FROM anmeldung a JOIN diplomarbeit d USING(da_id) "
            "WHERE d.titel='Wartungsplanung für eine Spritzgussanlage'").fetchone()
        self.assertEqual(tuple(r), (2, "LP-1001"))

    def test_keine_sensiblen_zusatzdaten_gespeichert(self):
        spalten = {r[1] for t in ("schueler", "anmeldung") for r in self.db.conn.execute(f"PRAGMA table_info({t})")}
        self.assertFalse(spalten & {"geschlecht", "geburtsdatum", "email"})

    def test_noten(self):
        for regel, p in [("N03", pid(301)), ("N01", pid(999)), ("N04", pid(208)), ("N05", pid(208)),
                         ("N06", pid(101)), ("N02", pid(102))]:
            with self.subTest(regel=regel):
                self.assertTrue(self.fehler(regel, p))
        self.assertEqual(len(self.fehler("N03", pid(301))), 2)
        self.assertEqual(self.db.conn.execute("SELECT COUNT(*) FROM pruefung").fetchone()[0], 70)


class Formate(unittest.TestCase):
    def test_langformat_gleich_wie_eduflow(self):
        db = ZielDB()
        prot = importiere_alles(db, LP, SOK, LANG)
        self.assertEqual(prot.meldungen, [])
        self.assertEqual(angemeldet(db), {pid(n) for n in (101, 102, 107, 108)})

    def test_dieselbe_person_in_zwei_dateien(self):
        db = ZielDB()
        prot = importiere_alles(db, LP, SOK, [KLASSEN[0], LANG])
        self.assertTrue(meldungen(prot, "R08", "Ahorn", FEHLER))
        self.assertNotIn(pid(101), angemeldet(db))


class SchutzManuellerDaten(unittest.TestCase):
    def test_reimport_ueberschreibt_manuelle_werte_nicht(self):
        db = ZielDB()
        importiere_alles(db, LP, SOK, KLASSEN, NOT)
        p, teil = pid(201), "PS_AM"
        alt = db.pruefung(p, teil)
        db.manuell_setzen(p, teil, "note", 5 if alt["note"] != 5 else 4)
        db.manuell_setzen(p, teil, "beisitzer_id", "LP-1010")
        db.commit()
        hand = db.pruefung(p, teil)
        prot = importiere_alles(db, LP, SOK, KLASSEN, NOT)
        neu = db.pruefung(p, teil)
        self.assertEqual(neu["note"], hand["note"])
        self.assertEqual(neu["beisitzer_id"], "LP-1010")
        self.assertEqual(neu["pruefer_id"], alt["pruefer_id"])
        self.assertEqual(neu["quelle_pruefer"], "import")
        info = meldungen(prot, "N07", p)
        self.assertEqual(({m.stufe for m in info}, len(info)), ({INFO}, 2))

    def test_reimport_ist_idempotent(self):
        db = ZielDB()
        importiere_alles(db, LP, SOK, KLASSEN, NOT)
        vorher = [tuple(r)[:-1] for r in db.conn.execute("SELECT * FROM pruefung ORDER BY 1,2")]
        anz = db.conn.execute("SELECT COUNT(*) FROM diplomarbeit").fetchone()[0]
        importiere_alles(db, LP, SOK, KLASSEN, NOT)
        nachher = [tuple(r)[:-1] for r in db.conn.execute("SELECT * FROM pruefung ORDER BY 1,2")]
        self.assertEqual(vorher, nachher)
        self.assertEqual(db.conn.execute("SELECT COUNT(*) FROM diplomarbeit").fetchone()[0], anz)

    def test_manuell_nur_fuer_erlaubte_felder(self):
        db = ZielDB()
        importiere_alles(db, LP, SOK)
        with self.assertRaises(ValueError):
            db.manuell_setzen(pid(201), "PS_AM", "personen_id", "X")


class KaputteDateien(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def mappe(self, name, kopf, zeilen, blatt="Teilnehmer und Ergebnisse"):
        wb = Workbook()
        ws = wb.active
        ws.title = blatt
        ws.append(kopf)
        for z in zeilen:
            ws.append(z)
        pfad = self.dir / name
        wb.save(pfad)
        return pfad

    def test_r01_spalte_fehlt(self):
        pfad = self.mappe("k.xlsx", ["Nachname", "Vorname", "Feld", "Wert"], [["Ahorn", "Lena", "PS_AM", "x"]])
        db = ZielDB()
        prot = importiere_alles(db, LP, SOK, pfad)
        self.assertEqual([m.regel for m in prot.meldungen], ["R01"])
        self.assertEqual(angemeldet(db), set())

    def test_r01_blatt_fehlt(self):
        pfad = self.mappe("l.xlsx", ["x"], [], blatt="Irgendwas")
        self.assertIn("R01", importiere_alles(ZielDB(), LP, SOK, pfad).regeln(FEHLER))

    def test_r14_vier_klausuren_mit_muendlicher_sprache(self):
        kopf = ["Nachname", "Vorname", "Klasse", "Personen-ID", "Status", *fk.ANTWORTFELDER]
        werte = {"Klausurart": fk.KLAUSUR_4_2, "Ausbildungsschwerpunkt": "Maschinenbau",
                 "Titel der Diplomarbeit:": "Test", "Diplomarbeitsbetreuer*in:": "Theresa Aigner",
                 "PS_AM": "Angewandte Mathematik", "PS_FT": "Fachtheorie", "PS_Deutsch": "Deutsch",
                 "PS_Englisch": "Englisch", "PM_D": "Deutsch", "PM_SPF": fk.PM_SPF,
                 "PM_WF_MB": "Religion", "Verbindliche Anmeldung": "ja"}
        z = ["Gaal", "Anna", "5AHWIM", pid(107), "Abgeschlossen", *[werte.get(f, "") for f in fk.ANTWORTFELDER]]
        prot = importiere_alles(ZielDB(), LP, SOK, self.mappe("v.xlsx", kopf, [z]))
        self.assertEqual([m.regel for m in prot.meldungen], ["R14"])

    def test_protokoll_csv_und_cli(self):
        ziel = self.dir / "prot.csv"
        main(["--db", str(self.dir / "t.sqlite"), "--lehrpersonen", str(LP), "--sokrates", str(SOK),
              "--anmeldung", *map(str, KLASSEN), "--noten", str(NOT), "--protokoll", str(ziel)])
        with open(ziel, encoding="utf-8-sig") as fh:
            zeilen = list(csv.DictReader(fh, delimiter=";"))
        self.assertTrue(zeilen)
        self.assertEqual(set(zeilen[0]), {"regel", "stufe", "datei", "zeile", "person", "text"})


class Qualitaet(unittest.TestCase):
    def test_metriken(self):
        db = ZielDB()
        importiere_alles(db, LP, SOK, KLASSEN, NOT)
        m = metriken(db, jetzt=datetime.now(timezone.utc) + timedelta(days=3))
        schueler = db.conn.execute("SELECT COUNT(*) FROM schueler").fetchone()[0]
        self.assertEqual(m["vollstaendigkeit"]["anmeldequote"], round(9 / schueler, 3))
        self.assertEqual(m["vollstaendigkeit"]["pflichtfelder_anmeldung"], 1.0)
        self.assertEqual(m["konsistenz"]["betreuer_in_stammdaten"], 1.0)
        self.assertLess(m["konsistenz"]["noten_nur_fuer_angemeldete"], 1.0)  # Prinz hat Noten ohne Anmeldung
        self.assertEqual(m["aktualitaet"]["alter_tage"], 3)

    def test_leere_db(self):
        self.assertIsNone(metriken(ZielDB())["vollstaendigkeit"]["anmeldequote"])


if __name__ == "__main__":
    unittest.main()

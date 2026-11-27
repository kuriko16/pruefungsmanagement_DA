"""Prüft die Dummy-Testfälle aus tools/demodaten.py gegen den Import.

Jede Prüfregel R01-R13 muss genau bei der Personen-ID anschlagen, für die der Testfall
gebaut ist, und darf keine ungeplanten Meldungen auslösen.

Ausführen:  python -m pytest tests -q
"""
import collections
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

PROJEKT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJEKT / "tools"), str(PROJEKT / "backend")]
import demodaten  # noqa: E402
import import_anmeldungen  # noqa: E402

ALLE_REGELN = {f"R{n:02d}" for n in range(1, 14)}


@pytest.fixture(scope="module")
def ergebnis():
    tmp = Path(tempfile.mkdtemp())
    dateien, faelle = demodaten.erzeuge_testdaten(ordner=tmp)
    con = sqlite3.connect(tmp / "test.db")
    con.executescript((PROJEKT / "backend" / "schema.sql").read_text(encoding="utf-8"))
    meldungen = []
    for d in dateien:
        _, _, m = import_anmeldungen.importiere_datei(con, d, "2026/27")
        meldungen += m
    kandidaten = {r[0] for r in con.execute("SELECT personen_id FROM kandidat")}
    con.close()
    return faelle, meldungen, kandidaten


def test_jede_regel_hat_einen_testfall(ergebnis):
    faelle, _, _ = ergebnis
    assert {regel for _, _, _, regel, _ in faelle} == ALLE_REGELN


def test_jede_regel_meldet_genau_ihre_personen_id(ergebnis):
    faelle, meldungen, _ = ergebnis
    gemeldet = collections.defaultdict(set)
    for m in meldungen:
        gemeldet[m.regel].add(m.personen_id)
    for klasse, zeile, pid, regel, text in faelle:
        if regel == "R12":   # R12 meldet die ganze Gruppe mit demselben Titel
            assert pid in gemeldet[regel], (regel, text)
        else:
            assert gemeldet[regel] == {pid}, (regel, text, gemeldet[regel])


def test_keine_ungeplanten_regeln(ergebnis):
    faelle, meldungen, _ = ergebnis
    assert {m.regel for m in meldungen} == {regel for _, _, _, regel, _ in faelle}


def test_fehler_werden_nicht_importiert_warnungen_schon(ergebnis):
    faelle, meldungen, kandidaten = ergebnis
    fehler = {m.personen_id for m in meldungen if m.schwere == "FEHLER"}
    warnungen = {m.personen_id for m in meldungen if m.schwere in ("WARNUNG", "HINWEIS")} - fehler
    assert not (fehler - {None}) & kandidaten
    assert warnungen <= kandidaten


def test_personen_ids_und_pflichtformat(ergebnis):
    tmp = Path(tempfile.mkdtemp())
    dateien, _ = demodaten.erzeuge_testdaten(ordner=tmp)
    import openpyxl
    for d in dateien:
        wb = openpyxl.load_workbook(d)
        assert wb.sheetnames[:2] == ["Teilnehmer und Ergebnisse", "Ergebnisse-Optionsfelder"]
        kopf = [c.value for c in wb["Teilnehmer und Ergebnisse"][1]]
        assert kopf == demodaten.KOPF
        assert d.name.startswith("Dummy_Anmeldung_5") and d.name.endswith(".xlsx")


def test_gleicher_seed_gleiche_daten():
    a = Path(tempfile.mkdtemp())
    b = Path(tempfile.mkdtemp())
    _, fa = demodaten.erzeuge_testdaten(seed=2026, ordner=a)
    _, fb = demodaten.erzeuge_testdaten(seed=2026, ordner=b)
    assert fa == fb

"""Prüft Vorlagen und Datentrennung ausschließlich mit erfundenen Angaben."""
import io
import sqlite3
import sys
from pathlib import Path

import openpyxl
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from dokumente.daten_lesen import lade_dokumentdaten
from dokumente.excel_erstellen import erstelle_uebersicht, erstelle_zeitplanvorlage
from dokumente.pdf_export import dokument_pdf
from dokumente.vorlagen import DokumentFehler, vorlagenpfad


@pytest.fixture
def con():
    db = sqlite3.connect(":memory:")
    db.executescript((ROOT / "backend/schema.sql").read_text())
    db.executescript("""
        INSERT INTO pruefungsjahr VALUES (1,'2026/27'),(2,'2025/26');
        INSERT INTO klasse VALUES (1,'5AHWIM','Maschinenbau',1),(2,'5AHWIM','Maschinenbau',2);
        INSERT INTO kandidat(personen_id,nachname,vorname) VALUES ('DEMO-1','Beispiel','Mira'),('DEMO-2','Beispiel','Mira');
        INSERT INTO anmeldung(id,personen_id,klasse_id) VALUES (1,'DEMO-1',1),(2,'DEMO-2',1),(3,'DEMO-1',2);
        INSERT INTO lehrperson VALUES (1,'Muster','Alex','AM',1);
        INSERT INTO diplomarbeit VALUES (1,'=KEINE_FORMEL',NULL,'NICHT_MANUELL',1);
        INSERT INTO anmeldung_diplomarbeit VALUES (1,1),(2,1);
        INSERT INTO pruefungsfach(id,anmeldung_id,art,feld,fach,pruefer_id,note_mp,note_gn)
            VALUES (1,1,'muendlich','PM_WF_MB','Ethik',1,2,3),
                   (2,2,'schriftlich','PS_AM','Angewandte Mathematik',1,5,NULL),
                   (3,3,'muendlich','PM_E','Englisch',NULL,NULL,NULL);
    """)
    yield db
    db.close()


def test_jahr_ids_und_manuelle_betreuung(con):
    vorher = con.total_changes
    daten = lade_dokumentdaten(con, "2026/27")
    assert len(daten["klassen"][0]["kandidaten"]) == 2  # gleicher Name, unterschiedliche Personen-ID
    assert {p["pruefung_id"] for p in daten["pruefungen"]} == {1, 2}
    assert all(p["betreuer"] is None for p in daten["pruefungen"])
    assert con.total_changes == vorher
    con.execute("UPDATE diplomarbeit SET betreuer_id=1")
    assert lade_dokumentdaten(con, "2026/27")["pruefungen"][0]["betreuer"] == "Muster Alex"
    with pytest.raises(DokumentFehler):
        lade_dokumentdaten(con, "2026/27", klasse_id=2)


def test_echte_vorlage_und_zusaetzliches_fach(con):
    pfad = vorlagenpfad("2026/27", "uebersicht")
    vorher = pfad.read_bytes()
    mappe = erstelle_uebersicht(lade_dokumentdaten(con, "2026/27"))
    ws = mappe["5AHWIM"]
    assert ws["E7"].value == "Prüfungen schriftlich"
    assert ws["Q9"].value == "Ethik" and ws["Q11"].value == "X"
    assert ws["W11"].value == "=KEINE_FORMEL" and ws["W11"].data_type == "s"
    assert ws["B11"].value == ""  # eduFLOW-Rohwert wird nicht als Betreuung ausgegeben
    assert all(ws.cell(12, c).value is None for c in range(18, 22))  # MP=5 ist keine Kompensationsentscheidung
    assert ws["V11"].value == '=COUNTIF(E11:Q11,"X")+COUNTIF(J11:Q11,"XV")'
    assert pfad.read_bytes() == vorher
    puffer = io.BytesIO()
    mappe.save(puffer)
    assert openpyxl.load_workbook(io.BytesIO(puffer.getvalue()))["5AHWIM"]["W11"].data_type == "s"


def test_mehr_kandidaten_als_in_der_originalvorlage(con):
    for n in range(10, 55):
        con.execute("INSERT INTO kandidat(personen_id,nachname,vorname) VALUES (?,?,?)", (f"DEMO-{n}", "Test", str(n)))
        con.execute("INSERT INTO anmeldung(personen_id,klasse_id) VALUES (?,1)", (f"DEMO-{n}",))
    ws = erstelle_uebersicht(lade_dokumentdaten(con, "2026/27"))["5AHWIM"]
    assert sum(ws.cell(r, 3).value is not None for r in range(11, 58)) == 47
    assert "$T$" not in str(ws.print_area)  # Zusätzliche Ethikspalte wird ebenfalls gedruckt.


def test_zeitplan_ohne_erfundene_termine():
    wb = erstelle_zeitplanvorlage("2026/27", "5BHWII")
    assert len(wb.sheetnames) == 7
    ws = wb["5BHWII_1HT_VT"]
    assert "2026/27" in ws["A1"].value
    assert ws["B6"].value is None and ws["D6"].value is None
    assert ws["D7"].value.startswith('=IF(OR(')


def test_pdf_und_ungueltige_vorlagenversion(con):
    daten = lade_dokumentdaten(con, "2026/27")
    for art in ("pruefungszettel", "kommission"):
        assert dokument_pdf(daten, art).startswith(b"%PDF-")
    with pytest.raises(DokumentFehler):
        vorlagenpfad("2026/27", "uebersicht", "../../v1")
    with pytest.raises(DokumentFehler):
        vorlagenpfad("2026/99", "uebersicht")

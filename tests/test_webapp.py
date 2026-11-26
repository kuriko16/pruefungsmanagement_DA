"""Automatische Tests für die Weboberfläche (mit Demodaten, eigene Test-Datenbank).

Ausführen:  python -m pytest tests -q
"""
import io
import os
import sys
import tempfile
from pathlib import Path

import openpyxl
import pytest

PROJEKT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def client():
    tmp = tempfile.mkdtemp()
    os.environ["PM_DB"] = str(Path(tmp) / "test.db")   # nie die echte Datenbank verwenden
    sys.path[:0] = [str(PROJEKT / "webapp"), str(PROJEKT / "tools"), str(PROJEKT / "backend")]
    import demodaten
    import app as webapp
    dateien = [demodaten.schreibe_xlsx(k, demodaten.erzeuge_klasse(k, demodaten.random.Random(1), iter(range(10000001, 10099999))))
               for k in demodaten.KLASSEN]
    webapp.app.config["TESTING"] = True
    c = webapp.app.test_client()
    c.dateien = dateien
    return c


def importiere(client, dateien):
    daten = {"jahr": "2026/27", "dateien": [(io.BytesIO(d.read_bytes()), d.name) for d in dateien]}
    return client.post("/import", data=daten, content_type="multipart/form-data")


def test_import_ueber_button(client):
    r = importiere(client, client.dateien)
    assert r.status_code == 200
    seite = r.get_data(as_text=True)
    assert "R05" in seite            # nicht verbindliche Anmeldung wird gemeldet
    assert "importiert" in seite


def test_alle_seiten_laden(client):
    for url in ["/", "/kandidaten", "/zuweisung", "/lehrpersonen", "/import", "/anmeldung/1"]:
        assert client.get(url).status_code == 200, url


def test_zuweisung_note_und_reimport_bleiben_erhalten(client):
    client.post("/lehrpersonen", data={"aktion": "neu", "nachname": "Test", "vorname": "Prüfer", "kuerzel": "tst"})
    import db
    con = db.verbinden()
    lehrer = con.execute("SELECT id FROM lehrperson WHERE nachname='Test'").fetchone()[0]
    fach = con.execute("SELECT id FROM pruefungsfach WHERE anmeldung_id=1 ORDER BY id LIMIT 1").fetchone()[0]
    a = con.execute("SELECT * FROM kandidat k JOIN anmeldung a ON a.personen_id=k.personen_id WHERE a.id=1").fetchone()
    con.close()
    client.post("/anmeldung/1", data={"nachname": a["nachname"], "vorname": a["vorname"],
                                      f"pruefer_{fach}": lehrer, f"tag_{fach}": "2027-06-10", f"note_mp_{fach}": "2"})
    importiere(client, client.dateien)          # gleicher Import noch einmal
    con = db.verbinden()
    z = con.execute("SELECT * FROM pruefungsfach WHERE id=?", (fach,)).fetchone()
    con.close()
    assert (z["pruefer_id"], z["pruefungstag"], z["note_mp"]) == (lehrer, "2027-06-10", 2)


def test_ungueltige_note_wird_abgelehnt(client):
    import db
    con = db.verbinden()
    fach = con.execute("SELECT id FROM pruefungsfach WHERE anmeldung_id=2 LIMIT 1").fetchone()[0]
    a = con.execute("SELECT k.* FROM kandidat k JOIN anmeldung a ON a.personen_id=k.personen_id WHERE a.id=2").fetchone()
    con.close()
    r = client.post("/anmeldung/2", data={"nachname": a["nachname"], "vorname": a["vorname"], f"note_mp_{fach}": "7"},
                    follow_redirects=True)
    assert "ungültig" in r.get_data(as_text=True)


def test_sammelzuweisung_und_filter(client):
    import db
    con = db.verbinden()
    klasse = con.execute("SELECT id FROM klasse WHERE name='5CHWIL'").fetchone()[0]
    lehrer = con.execute("SELECT id FROM lehrperson WHERE nachname='Test'").fetchone()[0]
    con.close()
    client.post("/zuweisung", data={"klasse": klasse, "gruppe": ["schriftlich|Fachtheorie"],
                                    "pruefer": [lehrer], "beisitz": [""], "tag": ["2027-05-06"]})
    con = db.verbinden()
    offen = con.execute("""SELECT COUNT(*) FROM pruefungsfach pf JOIN anmeldung a ON a.id=pf.anmeldung_id
                           WHERE a.klasse_id=? AND pf.fach='Fachtheorie' AND pf.pruefer_id IS NULL""", (klasse,)).fetchone()[0]
    con.close()
    assert offen == 0
    seite = client.get(f"/kandidaten?lehrer={lehrer}").get_data(as_text=True)
    assert "Treffer" in seite and "Keine Treffer" not in seite


def test_export_excel(client):
    r = client.get("/export/uebersicht")
    wb = openpyxl.load_workbook(io.BytesIO(r.data))
    assert {"5AHWIM", "5BHWII", "5CHWIL"} <= set(wb.sheetnames)
    ws = wb["5CHWIL"]
    assert ws["E7"].value == "Prüfungen schriftlich"
    assert any(c.value == "Test" for c in ws[10])   # Prüfer-Nachname steht in Zeile 10


def test_loeschen(client):
    r = client.post("/anmeldung/3/loeschen", follow_redirects=True)
    assert "gelöscht" in r.get_data(as_text=True)
    assert client.get("/anmeldung/3", follow_redirects=True).status_code == 200

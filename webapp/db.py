"""Datenbankzugriff für die Weboberfläche.

Wir verwenden dasselbe SQLite-Schema wie der Import (backend/schema.sql).
Für die Oberfläche fehlen im Schema noch zwei Felder, die wir hier sanft ergänzen
(nur wenn sie noch nicht da sind), damit bestehende Datenbanken weiter funktionieren:

  pruefungsfach.pruefungstag  -> Datum der Prüfung (MS-03 "Prüfungstage eingeben")
  pruefungsfach.note_jn       -> Jahresnote, damit MP und GN daneben stehen (MS-04)

Vorschlag an Sirin: diese Spalten fix in schema.sql übernehmen.
"""
import os
import sqlite3
from pathlib import Path

PROJEKT = Path(__file__).resolve().parents[1]
SCHEMA = PROJEKT / "backend" / "schema.sql"
# Pfad zur Datenbank kann über eine Umgebungsvariable geändert werden (z. B. im Docker-Container)
DB_PFAD = Path(os.environ.get("PM_DB", PROJEKT / "data" / "pruefung.db"))

ERGAENZUNGEN = {
    "pruefungsfach": {"pruefungstag": "TEXT", "note_jn": "REAL"},
}


def verbinden():
    """Neue Verbindung öffnen. row_factory erlaubt Zugriff per Spaltenname: zeile['nachname']."""
    DB_PFAD.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PFAD)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def initialisieren():
    """Schema anlegen (falls neu) und fehlende Spalten ergänzen."""
    con = verbinden()
    con.executescript(SCHEMA.read_text(encoding="utf-8"))
    for tabelle, spalten in ERGAENZUNGEN.items():
        vorhanden = {z["name"] for z in con.execute(f"PRAGMA table_info({tabelle})")}
        for name, typ in spalten.items():
            if name not in vorhanden:
                con.execute(f"ALTER TABLE {tabelle} ADD COLUMN {name} {typ}")
    con.commit()
    con.close()

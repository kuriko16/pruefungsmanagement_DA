"""Zugriff auf die Zieltabellen.

ACHTUNG: Das Datenmodell definiert Sirin. Dieses Schema ist eine ANNAHME, damit
der Import testbar ist. Jedes SQL des Imports steht ausschließlich in dieser
Datei. Kommt Sirins Modell, wird nur diese Datei angepasst.

Schutz manueller Daten: Bei Note, Prüfer und Beisitzer steht in einer eigenen
Spalte, woher der Wert kommt ('import' oder 'manuell'). Der Import überschreibt
nur Werte, die leer sind oder selbst aus einem Import stammen.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS lehrperson (
    personen_id TEXT PRIMARY KEY,
    kuerzel     TEXT NOT NULL UNIQUE,
    vorname     TEXT NOT NULL,
    nachname    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS schueler (
    personen_id TEXT PRIMARY KEY,          -- Sokrates-Personen-ID
    nachname    TEXT NOT NULL,
    vorname     TEXT NOT NULL,
    klasse      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS diplomarbeit (
    da_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    titel       TEXT NOT NULL UNIQUE,
    betreuer_id TEXT REFERENCES lehrperson(personen_id)
);
CREATE TABLE IF NOT EXISTS anmeldung (
    personen_id         TEXT PRIMARY KEY REFERENCES schueler(personen_id),
    da_id               INTEGER REFERENCES diplomarbeit(da_id),
    klausurart          TEXT,
    schwerpunkt         TEXT,
    sprache_schriftlich TEXT,   -- Deutsch | Englisch | Deutsch und Englisch
    sprache_muendlich   TEXT,   -- Deutsch | Englisch | NULL (bei 4+2)
    pm_spf              TEXT,
    wahlfach            TEXT,
    kenntnisnahme       INTEGER NOT NULL DEFAULT 0,
    importiert_am       TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pruefung (
    personen_id      TEXT NOT NULL REFERENCES schueler(personen_id),
    pruefungsteil    TEXT NOT NULL,
    note             INTEGER CHECK (note BETWEEN 1 AND 5),
    pruefer_id       TEXT REFERENCES lehrperson(personen_id),
    beisitzer_id     TEXT REFERENCES lehrperson(personen_id),
    quelle_note      TEXT CHECK (quelle_note IN ('import','manuell')),
    quelle_pruefer   TEXT CHECK (quelle_pruefer IN ('import','manuell')),
    quelle_beisitzer TEXT CHECK (quelle_beisitzer IN ('import','manuell')),
    geaendert_am     TEXT NOT NULL,
    PRIMARY KEY (personen_id, pruefungsteil)
);
"""

GESCHUETZTE_FELDER = {"note": "quelle_note", "pruefer_id": "quelle_pruefer", "beisitzer_id": "quelle_beisitzer"}


def jetzt() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ZielDB:
    def __init__(self, pfad: str = ":memory:") -> None:
        self.conn = sqlite3.connect(pfad)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)

    # --- Stammdaten -----------------------------------------------------------
    def speichere_lehrperson(self, pid, kuerzel, vorname, nachname) -> None:
        self.conn.execute(
            "INSERT INTO lehrperson VALUES (?,?,?,?) ON CONFLICT(personen_id) DO UPDATE SET "
            "kuerzel=excluded.kuerzel, vorname=excluded.vorname, nachname=excluded.nachname",
            (pid, kuerzel, vorname, nachname))

    def speichere_schueler(self, pid, nachname, vorname, klasse) -> None:
        self.conn.execute(
            "INSERT INTO schueler VALUES (?,?,?,?) ON CONFLICT(personen_id) DO UPDATE SET "
            "nachname=excluded.nachname, vorname=excluded.vorname, klasse=excluded.klasse",
            (pid, nachname, vorname, klasse))

    def lehrpersonen(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM lehrperson").fetchall()

    def schueler(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM schueler").fetchall()

    # --- Anmeldung / Diplomarbeit --------------------------------------------
    def speichere_diplomarbeit(self, titel: str, betreuer_id: str) -> int:
        self.conn.execute(
            "INSERT INTO diplomarbeit (titel, betreuer_id) VALUES (?,?) "
            "ON CONFLICT(titel) DO UPDATE SET betreuer_id=excluded.betreuer_id", (titel, betreuer_id))
        return self.conn.execute("SELECT da_id FROM diplomarbeit WHERE titel=?", (titel,)).fetchone()[0]

    ANMELDE_SPALTEN = ["klausurart", "schwerpunkt", "sprache_schriftlich", "sprache_muendlich",
                       "pm_spf", "wahlfach", "kenntnisnahme"]

    def speichere_anmeldung(self, pid: str, da_id: int, d: dict) -> None:
        spalten = self.ANMELDE_SPALTEN
        update = ", ".join(f"{s}=excluded.{s}" for s in ["da_id", *spalten, "importiert_am"])
        self.conn.execute(
            f"INSERT INTO anmeldung (personen_id, da_id, {', '.join(spalten)}, importiert_am) "
            f"VALUES ({', '.join('?' * (len(spalten) + 3))}) "
            f"ON CONFLICT(personen_id) DO UPDATE SET {update}",
            (pid, da_id, *(d[s] for s in spalten), jetzt()))

    # --- Prüfungen mit Schutz manueller Werte --------------------------------
    def pruefung(self, pid: str, teil: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM pruefung WHERE personen_id=? AND pruefungsteil=?", (pid, teil)).fetchone()

    def importiere_pruefungswerte(self, pid: str, teil: str, werte: dict) -> list[str]:
        """Schreibt Import-Werte. Gibt die Felder zurück, die geschützt waren."""
        alt = self.pruefung(pid, teil)
        if alt is None:
            self.conn.execute(
                "INSERT INTO pruefung (personen_id, pruefungsteil, geaendert_am) VALUES (?,?,?)",
                (pid, teil, jetzt()))
            alt = self.pruefung(pid, teil)
        geschuetzt, setzen = [], {}
        for feld, wert in werte.items():
            quelle_spalte = GESCHUETZTE_FELDER[feld]
            if alt[quelle_spalte] == "manuell":
                if alt[feld] != wert:
                    geschuetzt.append(feld)
                continue
            setzen[feld] = wert
            setzen[quelle_spalte] = "import"
        if setzen:
            sql = ", ".join(f"{k}=?" for k in setzen) + ", geaendert_am=?"
            self.conn.execute(f"UPDATE pruefung SET {sql} WHERE personen_id=? AND pruefungsteil=?",
                              (*setzen.values(), jetzt(), pid, teil))
        return geschuetzt

    def manuell_setzen(self, pid: str, teil: str, feld: str, wert) -> None:
        """So schreibt die Oberfläche (Prüfungsverwaltung) einen Wert von Hand."""
        if feld not in GESCHUETZTE_FELDER:
            raise ValueError(f"Feld {feld} ist nicht manuell pflegbar")
        if self.pruefung(pid, teil) is None:
            self.conn.execute(
                "INSERT INTO pruefung (personen_id, pruefungsteil, geaendert_am) VALUES (?,?,?)",
                (pid, teil, jetzt()))
        self.conn.execute(
            f"UPDATE pruefung SET {feld}=?, {GESCHUETZTE_FELDER[feld]}='manuell', geaendert_am=? "
            "WHERE personen_id=? AND pruefungsteil=?", (wert, jetzt(), pid, teil))

    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()

    def close(self) -> None:
        self.conn.close()

    def __del__(self) -> None:
        """Verbindung schließen, wenn das Objekt nicht mehr gebraucht wird (vermeidet ResourceWarning)."""
        try:
            self.conn.close()
        except Exception:
            pass

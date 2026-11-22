"""Liest vorhandene Prüfungsdaten für Yilmaz' Dokumenterstellung."""

import argparse
import sqlite3
from pathlib import Path


def lade_pruefungen(datenbank, pruefungsjahr):
    """Liefert die sieben Spalten, die unser Excel-Prototyp erwartet."""
    datenbank = Path(datenbank).resolve()
    if not datenbank.is_file():
        raise FileNotFoundError(f"Datenbank nicht gefunden: {datenbank}")

    # mode=ro bedeutet: nur lesen, nichts ändern oder neu anlegen.
    adresse = datenbank.as_uri() + "?mode=ro"
    verbindung = sqlite3.connect(adresse, uri=True)

    # JOIN verbindet die Tabellen über ihre IDs.
    # LEFT JOIN erhält auch Prüfungen ohne zugewiesene Lehrperson.
    abfrage = """
        SELECT
            kandidat.personen_id,
            kandidat.vorname || ' ' || kandidat.nachname,
            klasse.name,
            pruefungsfach.fach,
            CASE pruefungsfach.art
                WHEN 'muendlich' THEN 'mündlich'
                ELSE pruefungsfach.art
            END,
            COALESCE(pruefer.vorname || ' ' || pruefer.nachname, ''),
            COALESCE(beisitz.vorname || ' ' || beisitz.nachname, '')
        FROM pruefungsfach
        JOIN anmeldung ON anmeldung.id = pruefungsfach.anmeldung_id
        JOIN kandidat ON kandidat.personen_id = anmeldung.personen_id
        JOIN klasse ON klasse.id = anmeldung.klasse_id
        JOIN pruefungsjahr ON pruefungsjahr.id = klasse.pruefungsjahr_id
        LEFT JOIN lehrperson AS pruefer ON pruefer.id = pruefungsfach.pruefer_id
        LEFT JOIN lehrperson AS beisitz ON beisitz.id = pruefungsfach.beisitz_id
        WHERE pruefungsjahr.bezeichnung = ?
        ORDER BY klasse.name, kandidat.nachname, kandidat.vorname,
                 kandidat.personen_id, pruefungsfach.fach, pruefungsfach.id
    """

    try:
        # Das Fragezeichen wird sicher durch das ausgewählte Jahr ersetzt.
        ergebnis = verbindung.execute(abfrage, (pruefungsjahr,))
        return ergebnis.fetchall()
    finally:
        verbindung.close()


if __name__ == "__main__":
    # Pfad und Prüfungsjahr werden beim Start im Terminal angegeben.
    parser = argparse.ArgumentParser(description="Prüfungsdaten aus SQLite lesen")
    parser.add_argument("--db", required=True, help="Pfad zur vorhandenen Datenbank")
    parser.add_argument("--jahr", required=True, help="Prüfungsjahr, z. B. 2026/27")
    argumente = parser.parse_args()

    try:
        pruefungen = lade_pruefungen(argumente.db, argumente.jahr)
    except (FileNotFoundError, sqlite3.Error) as fehler:
        raise SystemExit(f"Daten konnten nicht gelesen werden: {fehler}")

    # Zur Kontrolle nur die Anzahl ausgeben, keine personenbezogenen Daten.
    print(f"Gefundene Prüfungen für {argumente.jahr}: {len(pruefungen)}")
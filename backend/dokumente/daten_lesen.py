"""Liest vorhandene Prüfungsdaten für Yilmaz' Dokumenterstellung."""

import argparse
import sqlite3
from pathlib import Path

if __package__:
    from .vorlagen import DokumentFehler
else:
    from vorlagen import DokumentFehler


def lade_dokumentdaten(verbindung, pruefungsjahr, klasse_id=None, anmeldung_id=None):
    """Liest alle Ausgabedaten. Schreibt nichts und legt keine Datenbank an.

    Diese Funktion ist die Schnittstelle zu Sirins späterem Datenmodell.
    Die Dokumentgeneratoren brauchen nur die zurückgegebenen Wörterbücher.
    """
    bedingungen = ["j.bezeichnung = ?"]
    parameter = [pruefungsjahr]
    if klasse_id is not None:
        bedingungen.append("k.id = ?")
        parameter.append(klasse_id)
    if anmeldung_id is not None:
        bedingungen.append("a.id = ?")
        parameter.append(anmeldung_id)

    # Das unveränderte Schema v0 hat diese beiden Spalten noch nicht.
    spalten = {r[1] for r in verbindung.execute("PRAGMA table_info(pruefungsfach)")}
    tag = "pf.pruefungstag" if "pruefungstag" in spalten else "NULL"
    jn = "pf.note_jn" if "note_jn" in spalten else "NULL"
    abfrage = f"""
        SELECT k.id AS klasse_id, k.name AS klasse, a.id AS anmeldung_id,
               kd.personen_id, kd.nachname, kd.vorname,
               d.id AS da_id, d.titel AS da_titel,
               b.nachname || ' ' || b.vorname AS betreuer,
               pf.id AS pruefung_id, pf.art, pf.feld, pf.fach,
               p.nachname AS pruefer_nachname,
               p.nachname || ' ' || p.vorname AS pruefer,
               bs.nachname || ' ' || bs.vorname AS beisitz,
               {tag} AS pruefungstag, {jn} AS note_jn, pf.note_mp, pf.note_gn
        FROM anmeldung a
        JOIN kandidat kd ON kd.personen_id = a.personen_id
        JOIN klasse k ON k.id = a.klasse_id
        JOIN pruefungsjahr j ON j.id = k.pruefungsjahr_id
        LEFT JOIN anmeldung_diplomarbeit ad ON ad.anmeldung_id = a.id
        LEFT JOIN diplomarbeit d ON d.id = ad.diplomarbeit_id AND d.pruefungsjahr_id = j.id
        LEFT JOIN lehrperson b ON b.id = d.betreuer_id
        LEFT JOIN pruefungsfach pf ON pf.anmeldung_id = a.id
        LEFT JOIN lehrperson p ON p.id = pf.pruefer_id
        LEFT JOIN lehrperson bs ON bs.id = pf.beisitz_id
        WHERE {' AND '.join(bedingungen)}
        ORDER BY k.name, d.titel IS NULL, d.titel, d.id,
                 kd.nachname, kd.vorname, kd.personen_id, pf.id
    """
    cursor = verbindung.execute(abfrage, parameter)
    namen = [spalte[0] for spalte in cursor.description]
    zeilen = [dict(zip(namen, zeile)) for zeile in cursor]
    if not zeilen:
        raise DokumentFehler("Für diese Auswahl gibt es im gewählten Prüfungsjahr keine Anmeldungen.")

    klassen, personen, pruefungen = {}, {}, []
    for zeile in zeilen:
        klasse = klassen.setdefault(zeile["klasse_id"], {
            "id": zeile["klasse_id"], "name": zeile["klasse"], "kandidaten": [],
        })
        if zeile["anmeldung_id"] not in personen:
            person = {**zeile, "pruefungen": []}
            personen[zeile["anmeldung_id"]] = person
            klasse["kandidaten"].append(person)
        if zeile["pruefung_id"] is not None:
            personen[zeile["anmeldung_id"]]["pruefungen"].append(zeile)
            pruefungen.append(zeile)

    # Betreuung ausschließlich aus der manuellen Zuweisung, niemals aus betreuer_text.
    return {"jahr": pruefungsjahr, "klassen": list(klassen.values()), "pruefungen": pruefungen}


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

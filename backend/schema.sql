-- Datenmodell v0 (Entwurf, Vorschlag fuer Sirin zum Weiterbearbeiten)
-- Alles ist pro Pruefungsjahr getrennt (z. B. '2026/27').
-- Schluessel fuer Personen: Personen-ID aus Sokrates.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS pruefungsjahr (
    id            INTEGER PRIMARY KEY,
    bezeichnung   TEXT NOT NULL UNIQUE          -- z. B. '2026/27'
);

CREATE TABLE IF NOT EXISTS klasse (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,                -- z. B. '5AHWIM'
    schwerpunkt   TEXT,                         -- Maschinenbau, Betriebsinformatik, Logistik
    pruefungsjahr_id INTEGER NOT NULL REFERENCES pruefungsjahr(id),
    UNIQUE (name, pruefungsjahr_id)
);

CREATE TABLE IF NOT EXISTS lehrperson (          -- Stammdaten (Konsole zur Pflege von Lehrkraeften)
    id            INTEGER PRIMARY KEY,
    nachname      TEXT NOT NULL,
    vorname       TEXT NOT NULL,
    kuerzel       TEXT,
    aktiv         INTEGER NOT NULL DEFAULT 1,
    UNIQUE (nachname, vorname)
);

CREATE TABLE IF NOT EXISTS kandidat (
    personen_id   TEXT PRIMARY KEY,             -- Sokrates-Personen-ID (14 Stellen)
    nachname      TEXT NOT NULL,
    vorname       TEXT NOT NULL,
    geburtsdatum  TEXT,                         -- ISO-Datum
    geschlecht    TEXT,
    email         TEXT,
    schulkennzahl TEXT
);

CREATE TABLE IF NOT EXISTS anmeldung (
    id            INTEGER PRIMARY KEY,
    personen_id   TEXT NOT NULL REFERENCES kandidat(personen_id),
    klasse_id     INTEGER NOT NULL REFERENCES klasse(id),
    status        TEXT,                         -- Status in eduFLOW (z. B. 'Abgeschlossen')
    ausgefuellt_am TEXT,
    klausurart    TEXT,                         -- '3 schriftliche ... 3 muendliche' oder '4 ... 2 ...'
    anzahl_schriftlich INTEGER,
    anzahl_muendlich   INTEGER,
    kenntnisnahme TEXT,
    verbindlich   TEXT,
    UNIQUE (personen_id, klasse_id)
);

CREATE TABLE IF NOT EXISTS pruefungsfach (       -- eine Zeile je gewaehltem Fach / Pruefung
    id            INTEGER PRIMARY KEY,
    anmeldung_id  INTEGER NOT NULL REFERENCES anmeldung(id) ON DELETE CASCADE,
    art           TEXT NOT NULL CHECK (art IN ('schriftlich','muendlich')),
    feld          TEXT NOT NULL,               -- Spalte aus eduFLOW, z. B. 'PM_WF_MB'
    fach          TEXT NOT NULL,               -- z. B. 'Religion'
    pruefer_id    INTEGER REFERENCES lehrperson(id),     -- manuell durch Herrn Angerer
    beisitz_id    INTEGER REFERENCES lehrperson(id),     -- manuell durch Herrn Angerer
    note_mp       REAL,                         -- MP: bleibt manuell
    note_gn       REAL                          -- GN: bleibt manuell
);

CREATE TABLE IF NOT EXISTS diplomarbeit (
    id            INTEGER PRIMARY KEY,
    titel         TEXT NOT NULL,
    betreuer_id   INTEGER REFERENCES lehrperson(id),    -- manuell eintragen
    betreuer_text TEXT,                                  -- Rohwert aus eduFLOW
    pruefungsjahr_id INTEGER NOT NULL REFERENCES pruefungsjahr(id),
    UNIQUE (titel, pruefungsjahr_id)
);

CREATE TABLE IF NOT EXISTS anmeldung_diplomarbeit (
    anmeldung_id  INTEGER PRIMARY KEY REFERENCES anmeldung(id) ON DELETE CASCADE,
    diplomarbeit_id INTEGER NOT NULL REFERENCES diplomarbeit(id)
);

-- Protokoll der Importe und Pruefmeldungen (fuer das Fehlerprotokoll)
CREATE TABLE IF NOT EXISTS import_lauf (
    id            INTEGER PRIMARY KEY,
    datei         TEXT NOT NULL,
    zeitpunkt     TEXT NOT NULL,
    zeilen_gelesen INTEGER,
    zeilen_importiert INTEGER
);

CREATE TABLE IF NOT EXISTS import_meldung (
    id            INTEGER PRIMARY KEY,
    import_lauf_id INTEGER NOT NULL REFERENCES import_lauf(id) ON DELETE CASCADE,
    schwere       TEXT NOT NULL CHECK (schwere IN ('FEHLER','WARNUNG','HINWEIS')),
    regel         TEXT NOT NULL,
    personen_id   TEXT,
    text          TEXT NOT NULL
);

"""Datenqualitätsmetriken: Vollständigkeit, Konsistenz, Aktualität.

Jede Kennzahl ist ein Anteil zwischen 0 und 1 (bzw. ein Alter in Tagen) und
direkt aus der Datenbank berechenbar. Definitionen: docs/DSGVO_UND_QUALITAET.md
"""
from __future__ import annotations

from datetime import datetime, timezone

from .ziel_db import ZielDB


def _anteil(zaehler: int, nenner: int) -> float | None:
    return round(zaehler / nenner, 3) if nenner else None


def metriken(db: ZielDB, jetzt: datetime | None = None) -> dict:
    c = db.conn
    jetzt = jetzt or datetime.now(timezone.utc)
    q = lambda sql: c.execute(sql).fetchone()[0]  # noqa: E731

    schueler = q("SELECT COUNT(*) FROM schueler")
    anmeldungen = q("SELECT COUNT(*) FROM anmeldung")
    pruefungen = q("SELECT COUNT(*) FROM pruefung")

    # --- Vollständigkeit -----------------------------------------------------
    v_anmeldequote = _anteil(anmeldungen, schueler)
    felder = ["klausurart", "schwerpunkt", "sprache_schriftlich", "pm_spf", "wahlfach", "da_id"]
    gefuellt = sum(q(f"SELECT COUNT(*) FROM anmeldung WHERE {f} IS NOT NULL AND {f} != ''") for f in felder)
    v_felder = _anteil(gefuellt, anmeldungen * len(felder))
    v_pruefung = _anteil(q("SELECT COUNT(*) FROM pruefung WHERE note IS NOT NULL AND pruefer_id IS NOT NULL "
                           "AND beisitzer_id IS NOT NULL"), pruefungen)

    # --- Konsistenz ------------------------------------------------------------
    k_rollen = _anteil(q("SELECT COUNT(*) FROM pruefung WHERE pruefer_id IS NULL OR beisitzer_id IS NULL "
                         "OR pruefer_id != beisitzer_id"), pruefungen)
    k_betreuer = _anteil(q("SELECT COUNT(*) FROM diplomarbeit d JOIN lehrperson l ON l.personen_id = d.betreuer_id"),
                         q("SELECT COUNT(*) FROM diplomarbeit"))
    k_noten_angemeldet = _anteil(
        q("SELECT COUNT(DISTINCT p.personen_id) FROM pruefung p JOIN anmeldung a USING(personen_id)"),
        q("SELECT COUNT(DISTINCT personen_id) FROM pruefung"))

    # --- Aktualität ------------------------------------------------------------
    letzter = q("SELECT MAX(importiert_am) FROM anmeldung")
    alter_tage = None
    if letzter:
        alter_tage = (jetzt - datetime.fromisoformat(letzter)).days

    return {
        "vollstaendigkeit": {
            "anmeldequote": v_anmeldequote,
            "pflichtfelder_anmeldung": v_felder,
            "pruefungen_komplett": v_pruefung,
        },
        "konsistenz": {
            "pruefer_ungleich_beisitzer": k_rollen,
            "betreuer_in_stammdaten": k_betreuer,
            "noten_nur_fuer_angemeldete": k_noten_angemeldet,
        },
        "aktualitaet": {
            "letzter_import": letzter,
            "alter_tage": alter_tage,
        },
    }

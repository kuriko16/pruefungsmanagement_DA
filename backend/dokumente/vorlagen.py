"""Findet eine unveränderte Vorlagenversion für ein bestimmtes Prüfungsjahr."""

import re
from pathlib import Path

PROJEKT = Path(__file__).resolve().parents[2]
VORLAGEN = PROJEKT / "vorlagen"


class DokumentFehler(ValueError):
    """Verständliche Meldung, die die Weboberfläche anzeigen darf."""


def jahresordner(jahr):
    """Nur Schuljahre wie 2026/27 zulassen, keine beliebigen Dateipfade."""
    if not isinstance(jahr, str) or not re.fullmatch(r"20\d{2}/\d{2}", jahr):
        raise DokumentFehler("Bitte ein Prüfungsjahr auswählen, zum Beispiel 2026/27.")
    if int(jahr[-2:]) != (int(jahr[:4]) + 1) % 100:
        raise DokumentFehler("Das Prüfungsjahr muss zwei aufeinanderfolgende Jahre enthalten.")
    return jahr.replace("/", "_")


def versionen(jahr):
    if not jahr:
        return []
    ordner = VORLAGEN / jahresordner(jahr)
    return sorted(
        (p.name for p in ordner.glob("v*") if p.is_dir() and re.fullmatch(r"v[1-9]\d*", p.name)),
        key=lambda v: int(v[1:]), reverse=True,
    )


def vorlagenpfad(jahr, art, version="v1"):
    dateien = {"uebersicht": "uebersicht_rdp.xlsx", "zeitplan": "zeitplan_muendlich.xlsx"}
    if art not in dateien or not re.fullmatch(r"v[1-9]\d*", version or ""):
        raise DokumentFehler("Diese Dokumentart oder Vorlagenversion gibt es nicht.")
    pfad = VORLAGEN / jahresordner(jahr) / version / dateien[art]
    if not pfad.is_file():
        raise DokumentFehler(f"Für {jahr}, {version} fehlt die Vorlage {dateien[art]}.")
    return pfad

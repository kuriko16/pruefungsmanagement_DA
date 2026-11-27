"""Schnittstelle des bisherigen Excel-Exports zu Yilmaz' Vorlagenmodul."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from dokumente.daten_lesen import lade_dokumentdaten
from dokumente.excel_erstellen import erstelle_uebersicht as vorlage_befuellen


def erstelle_uebersicht(con, jahr, klasse_id=None, version="v1"):
    return vorlage_befuellen(lade_dokumentdaten(con, jahr, klasse_id), version)

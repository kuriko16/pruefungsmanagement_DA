"""Namen und Klassen vergleichbar machen.

Grundidee: Zwei Schreibweisen gelten als gleich, wenn sie nach der
Normalisierung identisch sind. Die Normalisierung entfernt nur Unterschiede,
die keine Bedeutung haben (Groß/Klein, Leerzeichen, Akzente, Titel).
"""
from __future__ import annotations

import re
import unicodedata

# Akademische und Berufstitel, die vor oder nach dem Namen stehen können.
TITEL = {
    "prof", "dr", "di", "dipl", "ing", "mag", "mmag", "msc", "bsc", "ba", "ma",
    "bed", "med", "phd", "ot", "ostr", "stud", "dipl-ing", "diin", "magª", "fh",
}

_UMLAUTE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def norm_text(text: str | None) -> str:
    """Kleinschreibung, Umlaute ausschreiben, Akzente weg, Leerzeichen zusammenfassen.

    >>> norm_text("  Öztürk ")
    'oeztuerk'
    >>> norm_text("Dvořák")
    'dvorak'
    """
    if text is None:
        return ""
    t = str(text).casefold().translate(_UMLAUTE)
    # NFKD zerlegt "ř" in "r" + Hatschek; das Zusatzzeichen fällt dann weg.
    t = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip()


def name_tokens(roh: str | None) -> tuple[list[str], bool]:
    """Zerlegt einen Freitext-Namen in Wörter ohne Titel.

    Gibt zusätzlich zurück, ob ein Komma vorkam. "Brunner, Klaus" heißt
    eindeutig Nachname, Vorname.
    """
    t = norm_text(roh)
    hat_komma = "," in t
    woerter = [w.strip(".") for w in re.split(r"[\s,]+", t) if w.strip(".")]
    woerter = [w for w in woerter if w not in TITEL]
    return woerter, hat_komma


def norm_klasse(roh: str | None) -> str:
    """'5 z hwi' -> '5ZHWI'"""
    return re.sub(r"\s+", "", str(roh or "")).upper()


KLASSEN_MUSTER = re.compile(r"^[1-5][A-Z]{3,6}$")

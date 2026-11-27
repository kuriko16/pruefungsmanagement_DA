"""Fachliche Regeln der Reife- und Diplomprüfung, Abteilung Wirtschaftsingenieure (HWI).

Quelle: Import-Vorlagen in Teams (Blätter "Optionenwahl" und "Spaltenzuordnung"
der drei Klassendateien), gelesen am 2026-11-27. Übernommen wurden NUR Fächer,
Felder und Wertelisten, keine Personendaten.

Ändert die Schule ein Fach, wird nur diese Datei angepasst.
"""
from __future__ import annotations

PM_SPF = "Betriebstechnik/Unternehmensführung und Wirtschaftsrecht"
GGP = "Geografie, Geschichte und Politische Bildung"

KLAUSUR_3_3 = "3 schriftliche Klausuren und 3 mündliche Prüfungen"
KLAUSUR_4_2 = "4 schriftliche Klausuren und 2 mündliche Prüfungen"
KLAUSURARTEN = {KLAUSUR_3_3, KLAUSUR_4_2}

# Klasse -> Ausbildungsschwerpunkt, Wahlfach-Feld und erlaubte Wahlfächer
KLASSEN = {
    "5AHWIM": {
        "schwerpunkt": "Maschinenbau",
        "wahlfach_feld": "PM_WF_MB",
        "wahlfaecher": {"Religion", "Ethik", "Werkstoff- und Fertigungstechnik", "Naturwissenschaften", GGP},
    },
    "5BHWII": {
        "schwerpunkt": "Betriebsinformatik",
        "wahlfach_feld": "PM_WF_BI",
        "wahlfaecher": {"Religion", "Ethik", "Naturwissenschaften", GGP,
                        "Softwareentwicklung und Projektmanagement / Netzwerke und Embedded Software"},
    },
    "5CHWIL": {
        "schwerpunkt": "Logistik",
        "wahlfach_feld": "PM_WF_LOG",
        "wahlfaecher": {"Religion", "Ethik", "Naturwissenschaften", GGP, "Logistik"},
    },
}
WAHLFACH_FELDER = {k["wahlfach_feld"] for k in KLASSEN.values()}

# Alle Antwortfelder des Formulars (Reihenfolge wie im eduFLOW-Export)
ANTWORTFELDER = [
    "Klausurart", "Ausbildungsschwerpunkt", "Titel der Diplomarbeit:", "Diplomarbeitsbetreuer*in:",
    "PS_AM", "PS_FT", "PS_D_oder_E1", "PS_Deutsch", "PS_Englisch", "PM_D", "PM_E", "PM_SPF",
    "PM_WF_BI", "PM_WF_LOG", "PM_WF_MB", "Kenntnisnahme nächster Termin", "Verbindliche Anmeldung",
]

# Stammspalten des eduFLOW-Exports (Blatt "Spaltenzuordnung")
STAMMSPALTEN = ["Schulkennzahl", "Personen-ID", "Nachname", "Vorname", "Klasse", "Empfänger E-Mail",
                "Personentyp", "Geschlecht", "Status"]
# Werden absichtlich NICHT übernommen (Datenminimierung)
NICHT_UEBERNOMMEN = {"Empfänger E-Mail", "Empfänger*in E-Mail", "Geschlecht", "Geburtsdatum",
                     "Personentyp", "Gesehen am", "Ausgefüllt am", "Schulkennzahl"}


def pflichtfelder(klasse: str, klausurart: str) -> list[str]:
    """Welche Felder je nach Klasse und Prüfungsvariante gefüllt sein müssen."""
    basis = ["Klausurart", "Ausbildungsschwerpunkt", "Titel der Diplomarbeit:", "Diplomarbeitsbetreuer*in:",
             "PS_AM", "PS_FT", "PM_SPF", "Verbindliche Anmeldung"]
    if klasse in KLASSEN:
        basis.append(KLASSEN[klasse]["wahlfach_feld"])
    if klausurart == KLAUSUR_4_2:
        basis += ["PS_Deutsch", "PS_Englisch"]
    else:  # 3+3 oder unbekannt: Sprache schriftlich wählen
        basis.append("PS_D_oder_E1")
    return basis


# Prüfungsteile laut Export-Vorlage "Übersicht Reife- und Diplomprüfung"
PRUEFUNGSTEILE = {
    "PS_AM": "Angewandte Mathematik (schriftlich)",
    "PS_D": "Deutsch (schriftlich)",
    "PS_E": "Englisch (schriftlich)",
    "PS_FT": "Fachtheorie (schriftlich)",
    "PM_DA": "Diplomarbeit, Präsentation und Diskussion",
    "PM_SPF": "Schwerpunktfach (mündlich)",
    "PM_D": "Deutsch (mündlich)",
    "PM_E": "Englisch (mündlich)",
    "PM_WF": "Wahlfach (mündlich)",
}

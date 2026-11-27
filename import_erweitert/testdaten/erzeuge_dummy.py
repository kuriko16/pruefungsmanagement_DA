"""Erzeugt erfundene Testdaten im echten Aufbau der Teams-Vorlagen.

Aufbau (Spalten, Fächer, Wertelisten) stammt aus den Import-Vorlagen der
Klassen 5AHWIM, 5BHWII, 5CHWIL (eduFLOW-Export). ALLE Personen, IDs, E-Mails,
Geburtsdaten und DA-Titel sind erfunden.

Absichtliche Fehler: Kennung E01-E15 in der Spalte "Erw. Daten 1" (nur für
Menschen, der Import ignoriert sie) und in FEHLERFAELLE.md.

Aufruf:  python erzeuge_dummy.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT.parent))
from backend import fachkonfig as fk  # noqa: E402

GGP = fk.GGP
KOPF_STAMM = ["Nachname", "Vorname", "Klasse", "Empfänger*in E-Mail", "Personen-ID", "Personentyp",
              "Geschlecht", "Geburtsdatum", "Schulkennzahl", "Status", "Gesehen am", "Ausgefüllt am",
              "Erw. Daten 1"]

LEHRPERSONEN = [  # personen_id, kuerzel, vorname, nachname  (erfunden)
    ("LP-1001", "AIG", "Theresa", "Aigner"),
    ("LP-1002", "BRU", "Klaus", "Brunner"),
    ("LP-1003", "CSA", "Monika", "Csar"),
    ("LP-1004", "DOR", "Stefan", "Dorfer"),
    ("LP-1005", "ENG", "Ruth", "Engel"),
    ("LP-1006", "FRA", "Bernhard", "Frank"),
    ("LP-1007", "LUK", "Martin", "Lukas"),   # Martin Lukas  \  "Lukas Martin" passt auf beide
    ("LP-1008", "MAR", "Lukas", "Martin"),   # Lukas Martin  /
    ("LP-1009", "GRO", "Petra", "Gross"),
    ("LP-1010", "HUT", "Walter", "Huter"),
]


def pid(n: int) -> str:
    """Erfundene 14-stellige Personen-ID (beginnt mit 9999, damit sie sofort als Dummy erkennbar ist)."""
    return f"9999{n:010d}"


def anmeldung(klasse, nr, nachname, vorname, titel, betreuer, sprache="Deutsch", wahlfach=None,
              variante="3+3", geschlecht="weiblich", **abweichungen):
    """Eine gültige Anmeldung; abweichungen überschreibt einzelne Spalten (für Fehlerfälle)."""
    kl = fk.KLASSEN[klasse]
    z = {
        "Nachname": nachname, "Vorname": vorname, "Klasse": klasse,
        "Empfänger*in E-Mail": f"{norm_mail(vorname)}.{norm_mail(nachname)}@schule.example",
        "Personen-ID": pid(nr), "Personentyp": "S", "Geschlecht": geschlecht,
        "Geburtsdatum": f"{(nr % 27) + 1:02d}.{(nr % 12) + 1:02d}.2007", "Schulkennzahl": "999999",
        "Status": "Abgeschlossen", "Gesehen am": "10.11.2026 08:15", "Ausgefüllt am": "10.11.2026 08:20",
        "Erw. Daten 1": "",
        "Klausurart": fk.KLAUSUR_3_3 if variante == "3+3" else fk.KLAUSUR_4_2,
        "Ausbildungsschwerpunkt": kl["schwerpunkt"],
        "Titel der Diplomarbeit:": titel, "Diplomarbeitsbetreuer*in:": betreuer,
        "PS_AM": "Angewandte Mathematik", "PS_FT": "Fachtheorie",
        "PM_SPF": fk.PM_SPF, kl["wahlfach_feld"]: wahlfach or sorted(kl["wahlfaecher"])[nr % len(kl["wahlfaecher"])],
        "Kenntnisnahme nächster Termin": "ja", "Verbindliche Anmeldung": "ja",
    }
    if variante == "3+3":
        z["PS_D_oder_E1"] = sprache
        z["PM_E" if sprache == "Deutsch" else "PM_D"] = "Englisch" if sprache == "Deutsch" else "Deutsch"
    else:
        z["PS_Deutsch"], z["PS_Englisch"] = "Deutsch", "Englisch"
    z.update(abweichungen)
    return z


def norm_mail(s: str) -> str:
    return s.lower().translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "ć": "c", "ř": "r", "á": "a"}))


# --- Klassen (erfunden) ------------------------------------------------------
A, B, C = "5AHWIM", "5BHWII", "5CHWIL"
SCHUELER = {
    A: [
        anmeldung(A, 101, "Ahorn", "Lena", "Wartungsplanung für eine Spritzgussanlage", "Theresa Aigner"),
        anmeldung(A, 102, "Birkner", "Jonas", "Wartungsplanung für eine Spritzgussanlage", "Aigner Theresa",
                  sprache="Englisch", geschlecht="männlich"),
        anmeldung(A, 103, "Cerny", "Mira", "Leichtbau-Greifer aus dem 3D-Drucker", "Herbert Unbekannt",
                  **{"Erw. Daten 1": "E01"}),
        anmeldung(A, 104, "Dvořák", "Tomáš", "Energiekosten einer Druckluftanlage", "Brunner, Klaus",
                  geschlecht="männlich", PM_WF_MB="", PM_WF_BI="Ethik", **{"Erw. Daten 1": "E02"}),
        anmeldung(A, 105, "Ertl", "Sophie", "Energiekosten einer Druckluftanlage", "Brunner Klaus",
                  Status="In Bearbeitung", **{"Erw. Daten 1": "E03"}),
        anmeldung(A, 106, "Feichtinger", "Noah", "Prüfstand für Kugellager", "Prof. DI Ruth Engel",
                  geschlecht="männlich", PM_D="Deutsch", PM_E="", **{"Erw. Daten 1": "E04"}),
        anmeldung(A, 107, "Gaal", "Anna", "Prüfstand für Kugellager", "Ruth Engel", variante="4+2"),
        anmeldung(A, 108, "Haas", "Ben", "Kostenvergleich CNC-Fertigung", "frank bernhard",
                  geschlecht="männlich"),
    ],
    B: [
        anmeldung(B, 201, "Ilić", "Nina", "Smarte Stundenplanung", "Monika Csar"),
        anmeldung(B, 202, "Janda", "Paul", "Smarte Stundenplanung", "Csar Monika", geschlecht="männlich",
                  sprache="Englisch"),
        anmeldung(B, 203, "Kern", "Clara", "Chatbot für die Bibliothek", "Stefan Dorfer", Klasse="5 b hwii"),
        anmeldung(B, 299, "Lindner", "Max", "Chatbot für die Bibliothek", "Stefan Dorfer",
                  geschlecht="männlich", **{"Erw. Daten 1": "E05"}),
        anmeldung(B, 205, "Moser", "Eva", "Netzwerk-Monitoring für KMU", "Petra Gross",
                  **{"Personen-ID": pid(309), "Erw. Daten 1": "E06"}),
        anmeldung(B, 206, "Nagl", "Tim", "Netzwerk-Monitoring für KMU", "Petra Gross", geschlecht="männlich",
                  PM_WF_BI="Kochen", **{"Erw. Daten 1": "E07"}),
        anmeldung(B, 207, "Öztürk", "Deniz", "Webshop für ein Start-up", "Lukas Martin", geschlecht="männlich",
                  **{"Erw. Daten 1": "E08"}),
        anmeldung(B, 208, "Prinz", "Lea", "Webshop für ein Start-up", "Walter Huter", variante="4+2"),
        anmeldung(B, 208, "Prinz", "Lea", "Webshop für ein Start-up", "Walter Huter", variante="4+2",
                  **{"Erw. Daten 1": "E09"}),
    ],
    C: [
        anmeldung(C, 301, "Quast", "Robin", "Routenplanung im Lager", "Walter Huter", geschlecht="männlich"),
        anmeldung(C, 302, "Oeztuerk", "Aylin", "Routenplanung im Lager", "Huter, Walter",
                  wahlfach="Logistik"),
        anmeldung(C, 303, "Reiter", "", "Ökobilanz von Verpackungen", "Theresa Aigner",
                  geschlecht="männlich", **{"Erw. Daten 1": "E10"}),
        anmeldung(C, 304, "Schuster", "Ida", "", "Theresa Aigner", **{"Erw. Daten 1": "E11"}),
        anmeldung(C, 305, "Toth", "Leon", "Kommissionierung mit Pick-by-Light", "Bernhard Frank",
                  geschlecht="männlich", Klasse="5DHWIL", **{"Erw. Daten 1": "E12"}),
        anmeldung(C, 306, "Uhl", "Mara", "Kommissionierung mit Pick-by-Light", "Bernhard Frank",
                  Ausbildungsschwerpunkt="Maschinenbau", **{"Erw. Daten 1": "E13"}),
        anmeldung(C, 307, "Vogl", "Jan", "Lieferantenbewertung", "Klaus Brunner", geschlecht="männlich",
                  **{"Verbindliche Anmeldung": "", "Erw. Daten 1": "E14"}),
        anmeldung(C, 308, "Wagner", "Zoe", "Digitaler Zwilling eines Hochregallagers", "Petra Gross",
                  **{"Erw. Daten 1": "E15"}),
        anmeldung(C, 309, "Yilmaz", "Emre", "Digitaler Zwilling eines Hochregallagers", "Theresa Aigner",
                  geschlecht="männlich", **{"Erw. Daten 1": "E15"}),
    ],
}
EXTRA_SPALTE_B = "Bemerkung"   # unbekannte Spalte in 5BHWII -> R04 Warnung

# Sokrates: alle gültigen IDs. 299 (E05) fehlt absichtlich. Öztürk Aylin heißt in Sokrates mit Umlaut.
SOKRATES = [(z["Personen-ID"], z["Nachname"], z["Vorname"], z["Klasse"]) for kl in SCHUELER.values() for z in kl
            if z["Personen-ID"] != pid(299) and z["Erw. Daten 1"] not in ("E06", "E09", "E10", "E12")]
SOKRATES = [(p, "Öztürk" if n == "Oeztuerk" else n, v, "5BHWII" if k == "5 b hwii" else k)
            for p, n, v, k in SOKRATES]
SOKRATES += [(pid(205), "Moser", "Eva", B), (pid(303), "Reiter", "Felix", C), (pid(305), "Toth", "Leon", C)]
# E06: Moser hat in der Datei die ID 309 (gehört Yilmaz aus 5CHWIL) -> R10


def noten() -> list[tuple]:
    """Noten für die gültigen Personen + absichtlich falsche Zeilen N-E01..N-E06."""
    zeilen = []
    gueltig = [(pid(n), v) for n, v in ((101, "3+3"), (102, "3+3"), (107, "4+2"), (108, "3+3"),
                                        (201, "3+3"), (202, "3+3"), (203, "3+3"), (208, "4+2"),
                                        (301, "3+3"), (302, "3+3"))]
    for i, (p, variante) in enumerate(gueltig):
        teile = ["PS_AM", "PS_FT", "PM_DA", "PM_SPF", "PM_WF"]
        teile += ["PS_D", "PS_E"] if variante == "4+2" else (["PS_D", "PM_E"] if i % 2 == 0 else ["PS_E", "PM_D"])
        for j, teil in enumerate(teile):
            zeilen.append((p, teil, (i + j) % 5 + 1, LEHRPERSONEN[(i + j) % 6][1], LEHRPERSONEN[(i + j + 1) % 6][1]))
    zeilen += [
        (pid(301), "PM_D", 6, "AIG", "BRU"),           # N03 Note außerhalb 1-5
        (pid(301), "PS_E", "sehr gut", "AIG", "BRU"),  # N03 keine Zahl
        (pid(999), "PS_AM", 2, "AIG", "BRU"),          # N01 unbekannte ID
        (pid(208), "PM_D", 3, "XYZ", "BRU"),           # N04 unbekanntes Kürzel
        (pid(208), "PM_E", 2, "CSA", "CSA"),           # N05 Prüfer = Beisitzer
        (pid(101), "PS_AM", 4, "AIG", "BRU"),          # N06 doppelt
        (pid(102), "Turnen", 2, "AIG", "BRU"),         # N02 unbekannter Prüfungsteil
    ]
    return zeilen


def schreibe_klasse(klasse: str, zeilen: list[dict]) -> Path:
    kopf = KOPF_STAMM + fk.ANTWORTFELDER + ([EXTRA_SPALTE_B] if klasse == B else [])
    wb = Workbook()
    ws = wb.active
    ws.title = "Teilnehmer und Ergebnisse"
    ws.append(kopf)
    for z in zeilen:
        ws.append([z.get(k, "") for k in kopf])
    for i, c in enumerate(ws[1]):
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="BDD7EE" if i < len(KOPF_STAMM) else "C6E0B4")
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = ws.dimensions
    sz = wb.create_sheet("Spaltenzuordnung")
    sz.append(["eduFLOW - Spaltenzuordnung für die Import-Daten"])
    sz.append([])
    sz.append(["eduFLOW Spalte", "Import-Datei Spalte"])
    for edu, imp in [("SchoolID", "Schulkennzahl"), ("PersonID", "Personen-ID"), ("LastName", "Nachname"),
                     ("FirstName", "Vorname"), ("CurrentSchoolClassName", "Klasse"), ("EMail", "Empfänger E-Mail"),
                     ("PersonType", "Personentyp"), ("Gender", "Geschlecht"), ("Status", "Status"),
                     *[(f"ExtDataVal0{i}", f"Erw. Daten {i}") for i in range(1, 6)],
                     *[(f, f) for f in fk.ANTWORTFELDER]]:
        sz.append([edu, imp])
    pfad = OUT / f"anmeldung_{klasse}.xlsx"
    wb.save(pfad)
    return pfad


def schreibe_langformat(klasse: str, zeilen: list[dict]) -> Path:
    """Dieselben Daten im Langformat (so wie die 5AHWIM-Datei in Teams aufbereitet ist)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Teilnehmer und Ergebnisse"
    ws.append(["Nachname", "Vorname", "Klasse", "Personen-ID", "Feld", "Wert"])
    for z in zeilen:
        for f in fk.ANTWORTFELDER:
            if z.get(f):
                ws.append([z["Nachname"], z["Vorname"], z["Klasse"], z["Personen-ID"], f, z[f]])
    pfad = OUT / f"anmeldung_{klasse}_langformat.xlsx"
    wb.save(pfad)
    return pfad


def schreibe_csv(name: str, kopf, zeilen) -> None:
    with open(OUT / name, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(kopf)
        w.writerows(zeilen)


def main(ordner: Path | None = None) -> None:
    """Schreibt alle Testdateien nach `ordner` (Standard: dieser Ordner).

    Die Tests übergeben einen Temp-Ordner, damit eine in Excel geöffnete Datei
    hier nie überschrieben werden muss (unter Windows wäre sie gesperrt)."""
    global OUT
    if ordner is not None:
        OUT = Path(ordner)
        OUT.mkdir(parents=True, exist_ok=True)
    for klasse, zeilen in SCHUELER.items():
        schreibe_klasse(klasse, zeilen)
    gueltige_a = [z for z in SCHUELER[A] if not z["Erw. Daten 1"]]
    schreibe_langformat(A, gueltige_a)
    schreibe_csv("lehrpersonen_dummy.csv", ["personen_id", "kuerzel", "vorname", "nachname"], LEHRPERSONEN)
    schreibe_csv("sokrates_export_dummy.csv", ["personen_id", "nachname", "vorname", "klasse"], SOKRATES)
    schreibe_csv("noten_dummy.csv", ["personen_id", "pruefungsteil", "note", "pruefer_kuerzel", "beisitzer_kuerzel"],
                 noten())
    print(f"{sum(len(z) for z in SCHUELER.values())} Anmeldungen in 3 Klassen, {len(SOKRATES)} Sokrates, "
          f"{len(noten())} Noten -> {OUT}")


def stelle_sicher() -> None:
    """Erzeugt die Excel-Dateien, falls sie fehlen (.xlsx ist im Repository per .gitignore ausgeschlossen)."""
    if not all((OUT / f"anmeldung_{k}.xlsx").exists() for k in SCHUELER) or not (OUT / f"anmeldung_{A}_langformat.xlsx").exists():
        main()


if __name__ == "__main__":
    main()

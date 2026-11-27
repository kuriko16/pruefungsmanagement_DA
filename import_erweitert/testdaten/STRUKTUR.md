# Struktur der echten Vorlagen (aus Teams, nur Aufbau)

Quelle: Teams-Kanal der Diplomarbeit → Dateien → `General/00_Vorlagen/`. Gelesen am 2026-11-22 und 2026-11-27.
**Übernommen wurden nur Aufbau, Fächer und Wertelisten.** Keine Namen, IDs, Noten oder Inhalte von Personen. Alle Personendaten in den Dummy-Dateien sind erfunden.

## Ordner

```
General/00_Vorlagen/
├── Vorlagen_Datenimport/
│   ├── Anmeldung zur Reife- und Diplompruefung HWI 5AHWIM.xlsx   (Maschinenbau)
│   ├── Anmeldung zur Reife- und Diplompruefung HWI 5BHWII.xlsx   (Betriebsinformatik)
│   └── Anmeldung zur Reife- und Diplompruefung HWI 5CHWIL.xlsx   (Logistik)
├── Vorlagen_Datenexport/
│   ├── Übersicht_Reife_und_Diplomprüfung_5XHWIX_25_26.xlsx       (Zielformat Export)
│   └── Zeitplan_mündliche_RDP_5AHWIM_V1.xlsx                      (nicht angesehen)
└── Vorlagen_Diplomarbeit/
    ├── Projektmanagement/ · Diplomarbeit_Vorlage.docx · HTL_Betreuungsprotokoll_2016.docx
    └── Zeitaufzeichnung_Leer.xlsx                                  (für den Import nicht relevant)
```

## Importdatei = eduFLOW-Export

Blätter: `Teilnehmer und Ergebnisse`, `Auswertung`, `Optionenwahl`, `Ergebnisse-Optionsfelder`, `<Klasse>`, `Spaltenzuordnung`.

**`Teilnehmer und Ergebnisse`** ist in 5BHWII und 5CHWIL **breit**, also eine Zeile pro Person. In 5AHWIM wurde es ins **Langformat** umgebaut (Feld/Wert). Der Import kann beide Formate lesen.

Spalten laut Blatt `Spaltenzuordnung` (eduFLOW → Importdatei):

| Gruppe | Spalten |
|---|---|
| Stammdaten | Schulkennzahl, **Personen-ID**, Nachname, Vorname, Klasse, Empfänger E-Mail, Personentyp, Geschlecht, Status |
| Zusatz | Erw. Daten 1–5 |
| Antworten | Klausurart, Ausbildungsschwerpunkt, Titel der Diplomarbeit:, Diplomarbeitsbetreuer\*in:, PS_AM, PS_FT, PS_D_oder_E1, PS_Deutsch, PS_Englisch, PM_D, PM_E, PM_SPF, PM_WF_BI, PM_WF_LOG, PM_WF_MB, Kenntnisnahme nächster Termin, Verbindliche Anmeldung |

In der echten Datei stehen zusätzlich Geburtsdatum, „Gesehen am“ und „Ausgefüllt am“. Diese Felder werden **nicht** übernommen (Datenminimierung).

## Fächer und Werte (aus `Optionenwahl` bzw. Spaltenfilter)

| Feld | Werte |
|---|---|
| Klausurart | „3 schriftliche Klausuren und 3 mündliche Prüfungen“ · „4 schriftliche Klausuren und 2 mündliche Prüfungen“ |
| Ausbildungsschwerpunkt | 5AHWIM Maschinenbau · 5BHWII Betriebsinformatik · 5CHWIL Logistik |
| PS_AM / PS_FT | Angewandte Mathematik / Fachtheorie |
| PS_D_oder_E1 | Deutsch / Englisch (nur bei 3+3) |
| PS_Deutsch + PS_Englisch | Deutsch + Englisch (nur bei 4+2) |
| PM_D / PM_E | mündlich die jeweils **andere** Sprache (nur bei 3+3) |
| PM_SPF | Betriebstechnik/Unternehmensführung und Wirtschaftsrecht (alle Klassen) |
| PM_WF_MB (5AHWIM) | Religion · Ethik · Werkstoff- und Fertigungstechnik · Naturwissenschaften · Geografie, Geschichte und Politische Bildung |
| PM_WF_BI (5BHWII) | Religion · Ethik · Naturwissenschaften · Geografie, Geschichte und Politische Bildung · Softwareentwicklung und Projektmanagement / Netzwerke und Embedded Software |
| PM_WF_LOG (5CHWIL) | Religion · Ethik · Naturwissenschaften · Geografie, Geschichte und Politische Bildung · Logistik |
| Status | Abgeschlossen (sonst nicht fertig ausgefüllt) |

Ethik ist in allen drei Klassen wählbar (in den 5AHWIM-Daten kam es zufällig nicht vor). Im Code steht das in `backend/fachkonfig.py`.

## Exportdatei „Übersicht Reife- und Diplomprüfung“ (Zielformat, noch nicht gebaut)

- Ein Blatt pro Klasse plus Nebentermin-Blätter (`5AHWIM`, `5BHWII`, `5CHWIL`, `…_NT`).
- Kopf: Vorsitzende/r, Jahrgangsvorstand, Termin mündliche RDP, Satz „… zur mündlichen Reife- und Diplomprüfung zugelassen“.
- Spalten: Gruppe · Betreuer · Nachname · Vorname · **schriftlich** AM, D, E, FT · **mündlich** Diplomarbeit (Präsentation und Diskussion), Schwerpunktfach, Sprache D/E, Wahlfach (GGP, NAWI, R, LO1 …) · **Kompensationsprüfung** AM, D, E, FT.
- Zellen enthalten „X“ für angetretene Teile. Eine Zeile darüber stehen die Prüfer:innen je Fach, ganz unten Summen, Datum und Abteilungsvorstand.

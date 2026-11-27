# Absichtlich fehlerhafte Datensätze

Alle Personen sind erfunden, die Personen-IDs beginnen mit `9999`. Die Kennung steht in der Spalte „Erw. Daten 1“ der Klassendateien. Der Import ignoriert diese Spalte, sie ist nur für Menschen.

## Anmeldungen (3 Klassendateien)

| Nr | Klasse | Person | Fehler | Erkannt durch |
|---|---|---|---|---|
| E01 | 5AHWIM | Cerny Mira | Betreuer „Herbert Unbekannt“ | R11 |
| E02 | 5AHWIM | Dvořák Tomáš | Wahlfach im Feld der BI-Klasse (PM_WF_BI) statt PM_WF_MB | R05 + R06 |
| E03 | 5AHWIM | Ertl Sophie | Status „In Bearbeitung“ | R07 |
| E04 | 5AHWIM | Feichtinger Noah | schriftlich Deutsch **und** mündlich Deutsch | R14 |
| E05 | 5BHWII | Lindner Max | Personen-ID nicht in Sokrates | R09 |
| E06 | 5BHWII | Moser Eva | Personen-ID gehört einer anderen Person | R10 |
| E07 | 5BHWII | Nagl Tim | Wahlfach „Kochen“ | R06 |
| E08 | 5BHWII | Öztürk Deniz | Betreuer „Lukas Martin“ passt auf zwei Lehrpersonen | R12 |
| E09 | 5BHWII | Prinz Lea | Zeile doppelt | R08 |
| E10 | 5CHWIL | Reiter | Vorname leer | R02 (+ R10) |
| E11 | 5CHWIL | Schuster Ida | Titel der Diplomarbeit leer | R05 |
| E12 | 5CHWIL | Toth Leon | Klasse „5DHWIL“ gibt es nicht | R03 (+ R10) |
| E13 | 5CHWIL | Uhl Mara | Schwerpunkt „Maschinenbau“ in der Logistik-Klasse | R06 |
| E14 | 5CHWIL | Vogl Jan | Verbindliche Anmeldung leer | R05 |
| E15 | 5CHWIL | Wagner Zoe + Yilmaz Emre | gleiches DA-Thema, verschiedene Betreuer | R13 |

## Gültige Sonderfälle (müssen durchgehen)

| Person | Besonderheit | Ergebnis |
|---|---|---|
| Ahorn + Birkner (5AHWIM) | Betreuerin einmal „Theresa Aigner“, einmal „Aigner Theresa“ | ein Team, eine Betreuerin |
| Gaal (5AHWIM), Prinz-Variante | 4 schriftliche + 2 mündliche Prüfungen | importiert |
| Kern Clara (5BHWII) | Klasse „5 b hwii“ | Warnung R03, korrigiert |
| Öztürk Aylin (5CHWIL) | in der Datei „Oeztuerk“, in Sokrates „Öztürk“ | Personen-ID passt, importiert |
| Datei 5BHWII | zusätzliche Spalte „Bemerkung“ | Warnung R04 |

**Ergebnis:** 9 von 26 Zeilen werden importiert.

## Noten (`noten_dummy.csv`)

| Fall | Zeile | Erkannt durch |
|---|---|---|
| Note 6 | 72 | N03 |
| Note „sehr gut“ | 73 | N03 |
| unbekannte Personen-ID | 74 | N01 |
| unbekanntes Prüferkürzel „XYZ“ | 75 | N04 |
| Prüfer = Beisitzer | 76 | N05 |
| Note doppelt | 77 | N06 |
| Prüfungsteil „Turnen“ | 78 | N02 |

**Ergebnis:** 70 von 77 Notenzeilen werden gespeichert.

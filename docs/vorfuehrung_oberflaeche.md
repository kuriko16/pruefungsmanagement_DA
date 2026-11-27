# Vorführung der Oberfläche (ca. 4 Minuten)

Start: `START_Windows.bat` (Mac: `START_Mac.command`, sonst `python start.py`) → http://localhost:9094.
Vorher einmal `Demo_zuruecksetzen_Windows.bat` bzw. `python start.py --reset`, dann ist alles frisch.
Alle Daten sind erfunden.

1. **Dashboard:** Stand pro Klasse. 5AHWIM ist fast fertig, 5BHWII halb, 5CHWIL noch leer.
   Man sieht sofort, wo Prüfer:innen, Beisitz, Tage oder Noten fehlen.
2. **Import:** die drei Dateien aus `data/dummy/` (Julians Testfälle) auswählen → Importieren.
   Das Prüfprotokoll zeigt alle 13 Regeln (R01–R13). Fehlerhafte Zeilen werden nicht übernommen.
   Welche Personen-ID welchen Fehler testet, steht in `docs/testdaten.md`.
3. **Zuweisung:** Klasse 5CHWIL, bei Fachtheorie eine Lehrperson und einen Tag wählen → übernehmen.
   Zurück aufs Dashboard: die offenen Zahlen bei 5CHWIL sinken.
4. **Kandidat:innen:** Filter Fach = Religion, eine Person öffnen. Prüfer, Beisitz, Tag und Noten
   (JN/MP/GN) eintragen → Speichern. Import-Meldungen zur Person stehen oben.
5. **Export Excel:** Übersicht Reife- und Diplomprüfung im Aufbau der Vorlage, ein Blatt pro Klasse.

Umgesetzt: MS-01 bis MS-04 und MS-06 bis MS-09. Als Nächstes: Themengebiete (MS-05),
Notenberechnung (sobald die Formel feststeht), Druck- und Zeitplan-Button.

# Befehle für die Vorführung (PowerShell, der Reihe nach)

## Vorbereitung (vor der Stunde)

```powershell
cd C:\Claude\KI-Start-Talents\system\PROJEKTE\Schule\Diplomarbeit\import_erweitert
python zeige_ergebnis.py
python demo.py --ohne-pause
cls
```

## Vorführung

1. Dummy-Datei im echten eduFLOW-Aufbau zeigen (danach Excel schließen):
```powershell
start testdaten\anmeldung_5BHWII.xlsx
```
2. Automatische Prüfung aller drei Klassen, mit Enter durchklicken:
```powershell
python demo.py
```
3. Live-Fehler eintippen (`a` = Anmeldung, `n` = Note, `h` = Hilfe, `q` = Ende):
```powershell
python eingabe.py
```
   - `a`, alles Enter → OK
   - `a`, Klasse `5 a hwim` → Warnung
   - `a`, Wahlfach `Kochen` → Fehler R06
   - `a`, Sprache mündlich gleich wie schriftlich → Fehler R14
   - `n`, Note `6` → Fehler N03
   - `q`
4. Fehlerprotokoll als Excel:
```powershell
start ergebnisse\ergebnis_dummy.xlsx
```
5. Automatische Tests:
```powershell
python -m unittest discover -s tests -t . -v
```

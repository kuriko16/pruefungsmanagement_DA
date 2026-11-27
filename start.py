#!/usr/bin/env python3
"""Startet die Weboberfläche mit einem Befehl (Windows, Mac, Linux).

Was passiert:
  1. Beim ersten Mal: eigene Python-Umgebung (.venv) anlegen und Flask + openpyxl installieren
     (braucht einmal Internet, danach geht alles offline)
  2. Wenn noch keine Datenbank da ist: erfundene Demodaten laden
  3. Browser öffnen und die Oberfläche starten (http://localhost:9094)

Aufruf:  python start.py            normal starten
         python start.py --reset    Demodaten neu erzeugen (Datenbank wird gelöscht!)
Beenden: Fenster schließen oder Strg+C
"""
import os
import subprocess
import sys
import threading
import time
import venv
import webbrowser
from pathlib import Path

ORDNER = Path(__file__).resolve().parent
VENV = ORDNER / ".venv"
PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
DB = ORDNER / "data" / "pruefung.db"
PORT = os.environ.get("PORT", "9094")


def schritt(text):
    print(f"\n>>> {text}", flush=True)


def main():
    if sys.version_info < (3, 10):
        sys.exit("Python 3.10 oder neuer wird benötigt (python.org). Gefunden: " + sys.version.split()[0])

    # 1) Eigene Umgebung, damit nichts am restlichen System verändert wird
    if not PY.exists():
        schritt("Erster Start: Python-Umgebung wird angelegt (dauert ca. 1 Minute) ...")
        venv.create(VENV, with_pip=True)
    fertig = VENV / "installiert.txt"
    if not fertig.exists():
        schritt("Pakete werden installiert (Flask, openpyxl) ...")
        subprocess.check_call([str(PY), "-m", "pip", "install", "--disable-pip-version-check", "-q",
                               "-r", str(ORDNER / "requirements.txt")])
        fertig.write_text("ok")

    # 2) Demodaten (nur erfundene Namen)
    if "--reset" in sys.argv and DB.exists():
        DB.unlink()
    if not DB.exists():
        schritt("Demodaten werden erzeugt und importiert ...")
        subprocess.check_call([str(PY), str(ORDNER / "tools" / "demodaten.py"), "--db"], cwd=ORDNER)

    # Julians Testdateien (ein Fehler je Prüfregel) für die Import-Vorführung bereitlegen
    if not (ORDNER / "data" / "dummy").exists():
        schritt("Testdateien für den Import werden erzeugt (data/dummy) ...")
        subprocess.check_call([str(PY), str(ORDNER / "tools" / "demodaten.py"), "--testfaelle"], cwd=ORDNER,
                              stdout=subprocess.DEVNULL)

    # 3) Browser kurz nach dem Start öffnen
    url = f"http://localhost:{PORT}"
    threading.Thread(target=lambda: (time.sleep(2), webbrowser.open(url)), daemon=True).start()
    schritt(f"Oberfläche läuft auf {url}  (Beenden: dieses Fenster schließen oder Strg+C)")
    try:
        subprocess.call([str(PY), str(ORDNER / "webapp" / "app.py")], cwd=ORDNER,
                        env={**os.environ, "PORT": PORT})
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

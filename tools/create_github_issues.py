#!/usr/bin/env python3
"""Legt Labels, Meilensteine und Issues (User Stories) in einem GitHub-Repository an.

Quelle: docs/user_stories.csv. Voraussetzung: GitHub CLI (gh) ist installiert und
mit `gh auth login` angemeldet. Das Skript nutzt nur die REST-Schnittstelle (`gh api`).

Standardmaessig ist das ein Probelauf (zeigt nur, was passieren wuerde).
Zum echten Anlegen: --execute. Vorhandene Issues mit gleicher ID im Titel werden
uebersprungen, ein erneuter Lauf legt also nichts doppelt an.

Beispiel:
  python tools/create_github_issues.py --repo MEINNAME/pruefungsmanagement
  python tools/create_github_issues.py --repo MEINNAME/pruefungsmanagement --execute

Das GitHub Project (Board) wird nicht angelegt, das geht ueber die Weboberflaeche:
Projects -> New project -> Board, danach ueber "Add item" die Issues hinzufuegen.
"""
import argparse
import csv
import json
import subprocess
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent.parent / "docs" / "user_stories.csv"

LABELS = {
    "prio: muss": "b60205",
    "prio: soll": "fbca04",
    "prio: kann": "0e8a16",
    "bereich: sirin": "1d76db",
    "bereich: julian": "5319e7",
    "bereich: klenti": "006b75",
    "bereich: yilmaz": "d93f0b",
    "bereich: mikail": "0052cc",
    "bereich: alle": "bfdadc",
    "user story": "ededed",
}

MEILENSTEINE = {
    "MVP (30.11.2026)": "2026-11-30T23:59:00Z",
    "Zwischenpräsentation (14.12.2026)": "2026-12-14T23:59:00Z",
    "Nach der Zwischenpräsentation": "2027-01-25T23:59:00Z",
}


def gh_api(path, execute, method="GET", fields=None, json_body=None):
    cmd = ["gh", "api", path, "-X", method]
    for k, v in (fields or {}).items():
        cmd += ["-f", f"{k}={v}"]
    if json_body is not None:
        cmd += ["--input", "-"]
    print(("$ " if execute else "[Probelauf] ") + f"{method} {path}" + (f" {fields}" if fields else ""))
    if not execute:
        return None
    res = subprocess.run(cmd, capture_output=True, text=True,
                         input=json.dumps(json_body) if json_body is not None else None)
    if res.returncode != 0:
        print("  Hinweis:", (res.stdout or res.stderr).strip()[:200])
        return None
    return json.loads(res.stdout) if res.stdout.strip() else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, help="OWNER/REPO")
    ap.add_argument("--execute", action="store_true", help="wirklich anlegen (sonst Probelauf)")
    args = ap.parse_args()
    ex, repo = args.execute, args.repo

    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        stories = list(csv.DictReader(f))
    print(f"{len(stories)} User Stories aus {CSV_PATH.name} gelesen\n")

    for name, color in LABELS.items():
        gh_api(f"repos/{repo}/labels", ex, "POST", {"name": name, "color": color})

    numbers = {}
    for titel, due in MEILENSTEINE.items():
        res = gh_api(f"repos/{repo}/milestones", ex, "POST", {"title": titel, "due_on": due})
        if res:
            numbers[titel] = res["number"]
    if ex:
        for m in gh_api(f"repos/{repo}/milestones?state=all&per_page=100", True) or []:
            numbers.setdefault(m["title"], m["number"])

    vorhanden = set()
    if ex:
        page = 1
        while True:
            seite = gh_api(f"repos/{repo}/issues?state=all&per_page=100&page={page}", True) or []
            vorhanden |= {i["title"].split(":")[0] for i in seite}
            if len(seite) < 100:
                break
            page += 1

    for s in stories:
        if s["id"] in vorhanden:
            print(f"Übersprungen (existiert schon): {s['id']}")
            continue
        body = (
            f"**{s['id']}** · Priorität: {s['prio']} · Bereich: {s['bereich']}\n\n"
            f"{s['story']}\n\n"
            "### Akzeptanzkriterien\n- [ ] (vom Verantwortlichen zu ergänzen)\n\n"
            "### Aufgaben\n- [ ] (vom Verantwortlichen zu ergänzen)\n"
        )
        payload = {
            "title": f"{s['id']}: {s['titel']}",
            "body": body,
            "labels": [f"prio: {s['prio'].lower()}", f"bereich: {s['bereich'].lower()}", "user story"],
        }
        if s["meilenstein"] in numbers:
            payload["milestone"] = numbers[s["meilenstein"]]
        gh_api(f"repos/{repo}/issues", ex, "POST", json_body=payload)

    print("\nFertig." if ex else "\nProbelauf beendet. Mit --execute wirklich anlegen.")


if __name__ == "__main__":
    main()

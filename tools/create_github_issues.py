#!/usr/bin/env python3
"""Legt Labels, Meilensteine und Issues (User Stories) in einem GitHub-Repository an.

Quelle: docs/user_stories.csv. Voraussetzung: GitHub CLI (gh) ist installiert und
mit `gh auth login` angemeldet.

Standardmaessig ist das ein Probelauf (zeigt nur, was passieren wuerde).
Zum echten Anlegen: --execute

Beispiel:
  python tools/create_github_issues.py --repo MEINNAME/pruefungsmanagement
  python tools/create_github_issues.py --repo MEINNAME/pruefungsmanagement --execute
  python tools/create_github_issues.py --repo MEINNAME/pruefungsmanagement --execute \
      --project "Prüfungsmanagementsystem"   # Issues gleich in ein GitHub Project haengen
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


def run(cmd, execute, check=True):
    print(("$ " if execute else "[Probelauf] ") + " ".join(cmd))
    if not execute:
        return ""
    res = subprocess.run(cmd, capture_output=True, text=True)
    if check and res.returncode != 0:
        print(res.stderr.strip())
    return res.stdout


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, help="OWNER/REPO")
    ap.add_argument("--execute", action="store_true", help="wirklich anlegen (sonst Probelauf)")
    ap.add_argument("--project", help="Titel eines bestehenden GitHub Projects (optional)")
    args = ap.parse_args()

    with open(CSV_PATH, encoding="utf-8", newline="") as f:
        stories = list(csv.DictReader(f))
    print(f"{len(stories)} User Stories aus {CSV_PATH.name} gelesen\n")

    for name, color in LABELS.items():
        run(["gh", "label", "create", name, "--color", color, "--repo", args.repo, "--force"], args.execute)

    for titel, due in MEILENSTEINE.items():
        run(["gh", "api", f"repos/{args.repo}/milestones", "-f", f"title={titel}", "-f", f"due_on={due}"],
            args.execute, check=False)

    for s in stories:
        body = (
            f"**{s['id']}** · Priorität: {s['prio']} · Bereich: {s['bereich']}\n\n"
            f"{s['story']}\n\n"
            "### Akzeptanzkriterien\n- [ ] (vom Verantwortlichen zu ergänzen)\n\n"
            "### Aufgaben\n- [ ] (vom Verantwortlichen zu ergänzen)\n"
        )
        cmd = ["gh", "issue", "create", "--repo", args.repo,
               "--title", f"{s['id']}: {s['titel']}", "--body", body,
               "--label", f"prio: {s['prio'].lower()},bereich: {s['bereich'].lower()},user story",
               "--milestone", s["meilenstein"]]
        if args.project:
            cmd += ["--project", args.project]
        run(cmd, args.execute)

    print("\nFertig." if args.execute else "\nProbelauf beendet. Mit --execute wirklich anlegen.")


if __name__ == "__main__":
    main()

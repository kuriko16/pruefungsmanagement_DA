# GitHub einrichten (ca. 15 Minuten)

Eine Person (Vorschlag: Sirin als Koordinatorin) legt alles an, die anderen werden eingeladen.

## 1. Repository anlegen

1. Auf github.com: **New repository**, Name z. B. `pruefungsmanagement`.
2. Sichtbarkeit **Private** (Schulprojekt mit Prüfungsthemen).
3. Ohne README anlegen, wir haben schon eins.
4. Unter **Settings → Collaborators** alle Teammitglieder und Prof. Ramadani einladen.

## 2. Code hochladen

```bash
unzip pruefungsmanagement.zip
cd pruefungsmanagement
git init -b main
git add .
git status        # prüfen: keine .xlsx, keine .db, nichts aus data/input/
git commit -m "Projektgerüst: Schema und Import-Prototyp"
git remote add origin https://github.com/DEINNAME/pruefungsmanagement.git
git push -u origin main
```

Die Datei `.gitignore` hält Excel-Dateien und Datenbanken mit echten Daten aus dem Repository.
Prüft vor jedem Commit mit `git status`, dass nichts Personenbezogenes dabei ist.

## 3. GitHub CLI vorbereiten

1. `gh` installieren: https://cli.github.com
2. Anmelden: `gh auth login`
3. Für das Project zusätzlich: `gh auth refresh -s project`

## 4. GitHub Project anlegen

Im Repository auf **Projects → New project → Board**. Titel z. B. „Prüfungsmanagementsystem".
Spalten (Status): Backlog, Bereit, In Arbeit, Review, Fertig.
Oder per Kommandozeile: `gh project create --owner DEINNAME --title "Prüfungsmanagementsystem"`.

Danach das Project im Repository verknüpfen (Project → Settings → Linked repositories).

## 5. User Stories als Issues anlegen

Die 48 Anforderungen aus dem Anforderungsdokument stehen in `docs/user_stories.csv`.

```bash
# Probelauf: zeigt nur, was passieren würde
python tools/create_github_issues.py --repo DEINNAME/pruefungsmanagement

# Wirklich anlegen (mit Zuordnung zum Project)
python tools/create_github_issues.py --repo DEINNAME/pruefungsmanagement \
    --execute --project "Prüfungsmanagementsystem"
```

Das Skript legt an:
- **Labels** für Priorität (Muss, Soll, Kann) und Bereich (Sirin, Julian, Klenti, Yilmaz, Mikail, Alle)
- **Meilensteine** MVP (30.11.2026), Zwischenpräsentation (14.12.2026), Nach der Zwischenpräsentation
- **Issues** je Anforderung im Format „Als … möchte ich …, um …", mit Platz für Akzeptanzkriterien und Aufgaben

Führt es nur **einmal** mit `--execute` aus, sonst entstehen Doppelte.

## 6. Arbeitsweise im Team

- Jede Person arbeitet an den Issues mit ihrem Bereichs-Label und trägt sich als **Assignee** ein.
- Pro Aufgabe ein Branch (z. B. `julian/import-betreuer`) und ein Pull Request, den eine andere Person kurz ansieht.
- Im Pull Request `Closes #12` schreiben, dann wird das Issue automatisch geschlossen.
- Änderungen am Datenmodell (`backend/schema.sql`) nur nach Absprache mit Sirin.
- Ergänzt die Akzeptanzkriterien in euren Issues, dann ist klar, wann etwas „fertig" ist.
- Kurzer Abgleich einmal pro Woche (Vorschlag: Freitag), ob alles zusammenpasst.

## 7. Datenschutz

- Keine echten Excel-Dateien, Datenbanken oder Fehlerprotokolle mit Personen-IDs ins Repository.
- Für Tests nur erfundene Beispieldaten verwenden (am besten in `data/beispiel/` ablegen).
- Falls doch etwas Personenbezogenes eingecheckt wurde: sofort Prof. Ramadani informieren. Das Löschen im letzten Commit reicht nicht, die Historie muss bereinigt werden.

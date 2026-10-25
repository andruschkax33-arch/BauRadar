# BauRadar

Eine kleine App mit Nachrichten und Ausschreibungen rund ums Bauen, Schwerpunkt Tragwerksplanung.
Sie aktualisiert sich jeden Morgen um 6:00 Uhr (deutsche Zeit) und läuft kostenlos über GitHub.

## Auf dem Handy installieren

**iPhone (Safari):** Adresse der App öffnen → Teilen-Symbol (Viereck mit Pfeil) → „Zum Home-Bildschirm“ → „Hinzufügen“.

**Android (Chrome):** Adresse der App öffnen → Drei-Punkte-Menü → „App installieren“ oder „Zum Startbildschirm hinzufügen“.

Die Adresse ist die GitHub-Pages-Seite des Repositories (siehe unten).

## Quellen ändern

Datei `sources.yaml` öffnen, dann auf GitHub:

1. Repository `BauRadar` öffnen → Datei `sources.yaml` antippen.
2. Stift-Symbol (Bearbeiten) oben rechts antippen.
3. Ändern, z. B. `enabled: false` setzen, um eine Quelle zu pausieren.
4. Unten „Commit changes“ antippen.

Neue Feed-Quelle: einen Block kopieren und `name`, `url`, `region` (`duesseldorf_dueren`, `nrw` oder `de`) und `filter: true` für allgemeine Nachrichtenseiten ausfüllen. Nur Adressen eintragen, die wirklich Einträge liefern.

## Stichwörter ändern

Datei `keywords.yaml` öffnen (gleiches Vorgehen wie oben):

- `include:` – Begriffe, von denen mindestens einer in einer Meldung vorkommen muss (nur für Feeds mit `filter: true`).
- `exclude:` – Begriffe, bei denen eine Meldung oder Ausschreibung entfällt.
- `regions:` – Orte, die das Regions-Label „Düsseldorf/Düren“ bzw. „NRW“ auslösen.

Groß-/Kleinschreibung spielt keine Rolle.

## Den Sammeljob manuell starten

1. Repository `BauRadar` öffnen → Reiter „Actions“.
2. Links „BauRadar Sammeljob“ antippen → „Run workflow“ → „Run workflow“.
3. Nach wenigen Minuten ist die App aktualisiert.

## Einmalige Einrichtung auf GitHub

- **GitHub Pages:** Repository → „Settings“ → links „Pages“ → unter „Build and deployment“ die Quelle „Deploy from a branch“ wählen, Branch `main`, Ordner `/docs`, dann „Save“.
- **Optional, KI-Kurzfassungen:** Repository → „Settings“ → „Secrets and variables“ → „Actions“ → „New repository secret“ → Name `ANTHROPIC_API_KEY` und den Schlüssel eintragen. In `sources.yaml` danach `ai_summary: enabled: true` setzen.
- **Optional, Handy-Benachrichtigung:** In der App ntfy.sh installieren, ein eigenes Topic wählen, als Secret `NTFY_TOPIC` eintragen und in `sources.yaml` unter `ntfy:` `enabled: true` setzen.

## Technik (kurz)

- `scripts/collect.py` – holt die Feeds und die TED-Ausschreibungen, filtert, entfernt Duplikate und schreibt `docs/items.json`.
- `docs/` – die App (reines HTML, CSS, JavaScript; kein Build nötig).
- `.github/workflows/collect.yml` – der tägliche Zeitplan.

## Ausschreibungen

Ausschreibungen kommen aktuell aus der offiziellen TED-API (EU-Bekanntmachungen) mit den CPV-Codes 71327000 und 71312000 aus `sources.yaml`. TED erfasst nur Aufträge oberhalb der EU-Schwellenwerte, daher werden nicht alle Kommunal-Ausschreibungen in NRW gefunden.

## Rechtliches

Die App zeigt nur Titel, Quelle, Datum, eine kurze Zusammenfassung aus dem Feed-Teaser und den Link zum Original. Volltexte werden nicht übernommen.

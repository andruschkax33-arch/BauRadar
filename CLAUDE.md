# BauRadar – Projektleitfaden für Claude

## Ziel
Eine mobile Web-App (PWA, installierbar auf iOS und Android) mit dem Arbeitstitel „BauRadar“.
Sie sammelt einmal täglich Nachrichten und Ausschreibungen rund ums Bauen und zeigt sie wie in einer
Nachrichten-App an.

**Zielperson:** Tragwerksplanerin bzw. Tragwerksplaner in Düsseldorf/Düren (NRW), kein Entwickler.
Arbeitet ausschließlich mit Handy und GitHub-Webseite im Browser. Anleitungen an die Nutzerin/den Nutzer
sind **kurz, auf Deutsch, mit genauen Menüpfaden**.

## Inhalte
- Schwerpunkt: Tragwerksplanung (Statik, Massiv-, Stahl-, Holz-, Brückenbau, Bauwerksprüfung,
  Sanierung, Eurocodes/Normen, BauO NRW, HOAI, Ingenieurkammer-Bau NRW).
- Regionale Gewichtung: 1. Düsseldorf und Düren (Stadt/Kreis), 2. NRW, 3. Deutschland.
  Jede Meldung trägt ein Regions-Label und wird danach sortiert.
- Ausschreibungen: Tragwerksplanung aus evergabe.nrw (CPV u. a. 71327000, 71312000; Stichwörter
  „Tragwerksplanung“, „Statik“, „Ingenieurbauwerke“). Nur offizielle Zugangswege, kein Scraping
  gegen Nutzungsbedingungen.
- Keine vollständigen Artikeltexte übernehmen (Urheberrecht). Pro Meldung nur Titel, Quelle, Datum,
  Regions-Label, eigene Kurzfassung (2–3 Sätze, aus dem Feed-Teaser), Link zum Original.

## Architektur (geplant, siehe Plan – noch nicht freigegeben)
- `sources.yaml` – editierbare Quellenliste (RSS-Feeds, Regionen, Gewichtung).
- `keywords.yaml` (oder Abschnitte in `sources.yaml`) – Stichwörter und Ausschlussliste.
- `scripts/collect.py` – Python-Sammeljob: Feeds/Ausschreibungen abrufen, filtern, Duplikate
  entfernen, bewerten, als JSON speichern. Optional KI-Kurzfassung über die Claude API (nur wenn
  das GitHub Secret `ANTHROPIC_API_KEY` gesetzt ist).
- `data/items.json` – Ausgabe des Sammeljobs, wird von der App gelesen.
- `docs/` – statische PWA (`index.html`, `app.js`, `style.css`, `manifest.webmanifest`,
  `sw.js`, Icons). Wird über GitHub Pages veröffentlicht.
- `.github/workflows/collect.yml` – täglich 6:00 deutscher Zeit (Cron) sowie manuell
  (`workflow_dispatch`).
- `README.md` – Anleitung für Nutzerin/Nutzer: Quellen ändern, Stichwörter ändern, App auf dem
  Handy installieren.

## Konventionen
- Sprache: Oberfläche und Anleitungen auf Deutsch. Code-Kommentare sparsam, auf Deutsch.
- Python: nur Standardbibliothek plus wenige, klar benannte Pakete (z. B. `feedparser`, `PyYAML`).
  Kostenlos und ohne eigenen Server.
- Konfiguration gehört in `*.yaml`, damit sie ohne Programmieren auf GitHub bearbeitet werden kann.
- Keine Geheimnisse im Repo. API-Schlüssel nur als GitHub Secret.
- Kleine, nachvollziehbare Commits mit klaren deutschen Nachrichten.
- Vor Änderungen am Sammeljob: lokal in der Cloud-Sitzung ausführen und Beispielausgabe zeigen
  (5 Meldungen, 3 Ausschreibungen).
- Entwicklungsbranch: `claude/bauradар-pwa-lxamdh` (Name enthält ein kyrillisches „а“; exakt so verwenden).

## Arbeitsweise
1. Plan erstellen und auf Freigabe warten.
2. In kleinen Schritten umsetzen, Sammeljob testen, Beispielausgabe zeigen.
3. Am Ende: Schritte für GitHub (Pages aktivieren, Actions/Secrets prüfen) kurz erklären.

## Status
- Schritt 1 erledigt: Projektleitfaden angelegt.
- Schritt 2: Plan (Architektur, Quellen, Ausschreibungs-Zugriff) – in Arbeit, wartet auf Freigabe.

#!/usr/bin/env python3
"""BauRadar-Sammeljob: holt Nachrichten (RSS/Atom) und Ausschreibungen (TED),
filtert, entfernt Duplikate, sortiert nach Region und schreibt docs/items.json."""

import hashlib
import html
import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT_FILE = ROOT / "docs" / "items.json"
BERLIN = ZoneInfo("Europe/Berlin")
UA = "BauRadar/0.1 (persoenlicher Feed-Reader)"
TED_URL = "https://api.ted.europa.eu/v3/notices/search"
TED_NOTICE = "https://ted.europa.eu/de/notice/{}/html"

REGION_ORDER = {"duesseldorf_dueren": 1, "nrw": 2, "de": 3}
REGION_LABEL = {"duesseldorf_dueren": "Düsseldorf/Düren", "nrw": "NRW", "de": "Deutschland"}
NEWS_RETENTION_DAYS = 30
MAX_NEWS = 300
TEASER_LEN = 260


def load_yaml(name):
    with open(ROOT / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def http_get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def http_post_json(url, payload, headers=None, timeout=60):
    data = json.dumps(payload).encode("utf-8")
    h = {"User-Agent": UA, "Content-Type": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def strip_html(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def teaser(text, limit=TEASER_LEN):
    """Kurzfassung aus dem Feed-Teaser: höchstens ein paar Sätze, nie der volle Artikel."""
    text = strip_html(text)
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    if end > limit // 2:
        return cut[: end + 1]
    return cut.rsplit(" ", 1)[0] + " …"


def parse_date(value):
    if not value:
        return None
    value = value.strip()
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def local(tag):
    return tag.rsplit("}", 1)[-1]


def child_text(el, *names):
    for child in el:
        if local(child.tag) in names and child.text:
            return child.text.strip()
    return ""


def parse_feed(data):
    """Liest RSS 2.0 und Atom. Gibt Liste von Dicts mit title, link, summary, date zurück."""
    root = ET.fromstring(data)
    entries = []
    for el in root.iter():
        if local(el.tag) not in ("item", "entry"):
            continue
        link = child_text(el, "link")
        if not link:
            for child in el:
                if local(child.tag) == "link" and child.get("href"):
                    link = child.get("href")
                    break
        entries.append({
            "title": strip_html(child_text(el, "title")),
            "link": link,
            "summary": child_text(el, "description", "summary", "content"),
            "date": parse_date(child_text(el, "pubDate", "published", "updated", "date")),
        })
    return entries


def compile_terms(terms):
    # Wortanfang, ohne Groß-/Kleinschreibung
    return [re.compile(r"(?<!\w)" + re.escape(t.lower())) for t in terms or []]


def any_match(patterns, text):
    return any(p.search(text) for p in patterns)


def detect_region(text, default, regions):
    low = text.lower()
    if any_match(regions["duesseldorf_dueren"], low):
        return "duesseldorf_dueren"
    if any_match(regions["nrw"], low):
        return "nrw"
    return default


def make_id(*parts):
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]


def norm_title(title):
    return re.sub(r"[^a-z0-9äöüß]", "", title.lower())


def load_previous():
    if OUT_FILE.exists():
        try:
            return json.loads(OUT_FILE.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return {}
    return {}


def collect_news(cfg, kw, regions, errors, previous_ai):
    include = compile_terms(kw.get("include"))
    exclude = compile_terms(kw.get("exclude"))
    cutoff = datetime.now(timezone.utc) - timedelta(days=NEWS_RETENTION_DAYS)
    items = []
    for feed in cfg.get("feeds", []):
        if not feed.get("enabled", True):
            continue
        try:
            entries = parse_feed(http_get(feed["url"]))
        except Exception as exc:  # eine kaputte Quelle darf den Lauf nicht stoppen
            errors.append(f"{feed['name']}: {exc}")
            continue
        for e in entries:
            if not e["title"] or not e["link"]:
                continue
            text = f"{e['title']} {strip_html(e['summary'])}".lower()
            if any_match(exclude, text):
                continue
            if feed.get("filter", False) and not any_match(include, text):
                continue
            published = e["date"] or datetime.now(timezone.utc)
            if published < cutoff:
                continue
            item_id = make_id(e["link"])
            short = teaser(e["summary"])
            items.append({
                "id": item_id,
                "type": "news",
                "title": e["title"],
                "source": feed["name"],
                "url": e["link"],
                "published": published.isoformat(),
                # Region nur aus Titel und sichtbarem Teaser, sonst erwähnen Meldungen Orte am Rand
                "region": detect_region(f"{e['title']} {short}", feed.get("region", "de"), regions),
                "teaser": short,
                "ai_summary": previous_ai.get(item_id),
            })
    return items


def collect_tenders(cfg, kw, regions, errors, previous_ai):
    tcfg = cfg.get("tenders", {})
    if not tcfg.get("enabled", False):
        return []
    exclude = compile_terms(kw.get("exclude"))
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=tcfg.get("days_back", 30))).strftime("%Y%m%d")
    # Ausschreibungen, deren Frist mehr als eine Woche vorbei ist, werden nicht angezeigt
    expired_before = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    cpv = " ".join(str(c) for c in tcfg.get("cpv", []))
    payload = {
        "query": f"buyer-country={tcfg.get('country', 'DEU')} AND classification-cpv IN ({cpv}) AND publication-date>={since}",
        "fields": ["publication-number", "notice-title", "buyer-name", "publication-date",
                   "deadline-receipt-tender-date-lot", "place-of-performance-city-lot"],
        "limit": 100,
        "page": 1,
    }
    try:
        result = http_post_json(TED_URL, payload)
    except Exception as exc:
        errors.append(f"{tcfg.get('source_name', 'TED')}: {exc}")
        return []

    items = []
    for n in result.get("notices", []):
        # TED-Titel beginnen mit "Land – Kategorie – Titel"; nur den Titel behalten
        title = first_text(n.get("notice-title")).split(" – ")
        title = " – ".join(title[2:]) if len(title) >= 3 else " – ".join(title)
        buyer = first_text(n.get("buyer-name"))
        city = first_text(n.get("place-of-performance-city-lot"))
        pub = n.get("publication-number", "")
        if not title or not pub:
            continue
        if any_match(exclude, title.lower()):
            continue
        deadline = first_text(n.get("deadline-receipt-tender-date-lot"))[:10] or None
        if deadline and deadline < expired_before:
            continue
        published = parse_date(first_text(n.get("publication-date"))[:10] + "T00:00:00+00:00")
        item_id = make_id("ted", pub)
        items.append({
            "id": item_id,
            "type": "tender",
            "title": title,
            "buyer": buyer,
            "city": city,
            "deadline": deadline,
            "source": tcfg.get("source_name", "TED"),
            "url": TED_NOTICE.format(pub),
            "published": published.isoformat() if published else None,
            "region": detect_region(f"{title} {buyer} {city}", "de", regions),
        })
    return items


def first_text(value):
    """TED liefert mehrsprachige Felder als Dict und Listen. Gibt den ersten Text zurück."""
    if isinstance(value, dict):
        return first_text(value.get("deu") or next(iter(value.values()), ""))
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value or "")


def dedupe(items):
    seen_ids, seen_titles, out = set(), set(), []
    for it in items:
        key = norm_title(it["title"])
        if it["id"] in seen_ids or key in seen_titles:
            continue
        seen_ids.add(it["id"])
        seen_titles.add(key)
        out.append(it)
    return out


def apply_first_seen(tenders, previous, now_iso):
    old = {t["id"]: t.get("first_seen") for t in previous.get("tenders", [])}
    for t in tenders:
        t["first_seen"] = old.get(t["id"]) or now_iso
    return tenders


def ai_summarize(items, cfg_ai):
    """Optionale 2–3-Satz-Kurzfassung per Claude API. Nur aus dem Feed-Teaser, nie aus dem Volltext."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not (cfg_ai.get("enabled") and key):
        return
    for it in items:
        if it["type"] != "news" or it.get("ai_summary") or not it.get("teaser"):
            continue
        try:
            resp = http_post_json(
                "https://api.anthropic.com/v1/messages",
                {
                    "model": cfg_ai.get("model", "claude-haiku-5-5"),
                    "max_tokens": 200,
                    "messages": [{"role": "user", "content": (
                        "Fasse die folgende Meldung in 2 bis 3 Sätzen auf Deutsch zusammen. "
                        "Nutze nur die angegebenen Angaben.\n\n"
                        f"Titel: {it['title']}\nTeaser: {it['teaser']}")}],
                },
                headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
            )
            it["ai_summary"] = "".join(b.get("text", "") for b in resp.get("content", [])).strip() or None
        except Exception as exc:
            print(f"KI-Kurzfassung übersprungen: {exc}")
            return


def send_ntfy(cfg_ntfy, new_tenders):
    topic = os.environ.get("NTFY_TOPIC")
    if not (cfg_ntfy.get("enabled") and topic and new_tenders):
        return
    msg = f"{len(new_tenders)} neue Ausschreibung(en) im BauRadar"
    req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=msg.encode("utf-8"),
                                 headers={"Title": "BauRadar", "User-Agent": UA}, method="POST")
    try:
        urllib.request.urlopen(req, timeout=20).read()
    except Exception as exc:
        print(f"ntfy-Benachrichtigung fehlgeschlagen: {exc}")


def main():
    cfg = load_yaml("sources.yaml")
    kw = load_yaml("keywords.yaml")
    regions = {k: compile_terms(v) for k, v in kw.get("regions", {}).items()}
    previous = load_previous()
    previous_ai = {i["id"]: i["ai_summary"] for i in previous.get("news", []) if i.get("ai_summary")}
    errors = []
    now = datetime.now(timezone.utc)

    news = dedupe(collect_news(cfg, kw, regions, errors, previous_ai))
    news.sort(key=lambda i: (REGION_ORDER[i["region"]], -datetime.fromisoformat(i["published"]).timestamp()))
    news = news[:MAX_NEWS]

    tenders = dedupe(collect_tenders(cfg, kw, regions, errors, previous_ai))
    known = {t["id"] for t in previous.get("tenders", [])}
    tenders = apply_first_seen(tenders, previous, now.isoformat())
    new_tenders = [t for t in tenders if t["id"] not in known]
    tenders.sort(key=lambda t: (REGION_ORDER[t["region"]], t["deadline"] or "9999"))

    ai_summarize(news, cfg.get("ai_summary", {}))
    send_ntfy(cfg.get("ntfy", {}), new_tenders)

    result = {
        "generated_at": now.astimezone(BERLIN).strftime("%d.%m.%Y, %H:%M Uhr"),
        "generated_iso": now.isoformat(),
        "region_labels": REGION_LABEL,
        "news": news,
        "tenders": tenders,
        "errors": errors,
    }
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(news)} Meldungen, {len(tenders)} Ausschreibungen ({len(new_tenders)} neu), "
          f"{len(errors)} Fehler -> {OUT_FILE.relative_to(ROOT)}")
    for err in errors:
        print(f"  Fehler: {err}")


if __name__ == "__main__":
    main()

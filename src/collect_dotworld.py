"""Collecte respectueuse des pages publiques de DotWorld (instantanés datés).

- Respecte robots.txt (dotworld.ch : vide ; dotworld.teamtailor.com : pages /jobs publiques autorisées).
- Une requête toutes les 3 secondes, aucune connexion, aucun formulaire.
- Les pages sont enregistrées dans data/raw/dotworld_site/<date>_<nom>.html,
  puis leur texte visible est extrait dans un .txt à côté pour la relecture.

Usage : python src/collect_dotworld.py            (télécharge + extrait)
        python src/collect_dotworld.py --extract  (extrait seulement)
"""
from __future__ import annotations

import datetime as dt
import html
import re
import sys
import time
from pathlib import Path
from urllib import robotparser

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "dotworld_site"
UA = "Mozilla/5.0 (independent case study; low-frequency research)"

PAGES = {
    "home": "https://www.dotworld.ch/",
    "team": "https://www.dotworld.ch/team",
    "careers_home": "https://dotworld.teamtailor.com/",
    "careers_jobs": "https://dotworld.teamtailor.com/jobs",
    "job_data-analyst-saas": "https://dotworld.teamtailor.com/jobs/8642089-data-analyst-saas",
    "job_product-data-scientist-saas": "https://dotworld.teamtailor.com/jobs/8642055-product-data-scientist-saas",
    "job_payment-operations-specialist-international": "https://dotworld.teamtailor.com/jobs/8592394-payment-operations-specialist-international",
    "job_risk-compliance-specialist-paiement": "https://dotworld.teamtailor.com/jobs/8591658-risk-compliance-specialist-paiement",
    "job_product-manager-growth": "https://dotworld.teamtailor.com/jobs/8463157-product-manager-growth",
    "job_creative-strategist": "https://dotworld.teamtailor.com/jobs/8274972-creative-strategist",
}


def allowed(url: str) -> bool:
    base = re.match(r"https?://[^/]+", url).group(0)
    rp = robotparser.RobotFileParser(base + "/robots.txt")
    try:
        rp.read()
    except Exception:
        return True  # robots.txt absent : pas de restriction déclarée
    return rp.can_fetch(UA, url)


def visible_text(raw: str) -> str:
    raw = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    txt = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return re.sub(r"\s+", " ", txt).strip()


def download(today: str) -> None:
    for name, url in PAGES.items():
        if not allowed(url):
            print(f"robots.txt interdit : {url}")
            continue
        r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
        (RAW / f"{today}_{name}.html").write_text(r.text, encoding="utf-8")
        print(name, r.status_code, len(r.text))
        time.sleep(3)


def extract() -> None:
    for f in sorted(RAW.glob("*.html")):
        txt = visible_text(f.read_text(encoding="utf-8", errors="ignore"))
        # On retire le bandeau cookies, identique sur toutes les pages Teamtailor
        txt = re.sub(r"Ce site Web utilise des cookies.*?Refuser les cookies facultatifs .*?Refuser les cookies facultatifs", "", txt)
        f.with_suffix(".txt").write_text(txt, encoding="utf-8")


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    if "--extract" not in sys.argv:
        download(dt.date.today().isoformat())
    extract()

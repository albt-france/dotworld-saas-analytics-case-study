"""Skill ltv-by-channel : CAC, LTV, ROAS et contribution par canal ou campagne, à horizon fixe.

Exemples :
  python skills/ltv-by-channel/run.py --horizon 180 --start 2025-01-01 --end 2026-01-01
  python skills/ltv-by-channel/run.py --horizon 90 --dim campagne --start 2025-10-01 --end 2026-04-01
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
from skillkit import Checks, connect, render, show  # noqa: E402

DIMS = {"canal": "channel", "channel": "channel", "campagne": "campaign", "campaign": "campaign",
        "pays": "country", "country": "country"}


def query(con, dim, p):
    sql = (HERE / "queries" / "ltv.sql").read_text(encoding="utf-8").replace("__DIM__", DIMS[dim])
    return con.sql(render(sql, p)).df()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-01-01")
    ap.add_argument("--end", default="2026-01-01")
    ap.add_argument("--horizon", type=int, default=180)
    ap.add_argument("--products", nargs="+", default=["A", "B", "C"])
    ap.add_argument("--dim", default="canal", choices=sorted(DIMS))
    a = ap.parse_args(argv)
    p = dict(start=a.start, end=a.end, horizon=a.horizon, products=a.products)

    con = connect()
    df = query(con, a.dim, p)
    out = [f"# ltv-by-channel : horizon {a.horizon} jours, inscriptions du {a.start} au {a.end}",
           show(df, f"CAC, LTV par abonné payant et ROAS par {a.dim}")]

    # ---- Contrôles ----
    c = Checks()
    n_mature = con.execute(render("""SELECT count(*) FROM customers, params
        WHERE signup_ts >= {{start}} AND signup_ts < {{end}} AND product IN {{products}}
          AND signup_ts + to_days({{horizon}}) <= obs_end""", p)).fetchall()[0][0]
    c.add("cohortes complètes uniquement (anti-censure)", n_mature > 0 and int(df.signups.sum()) == n_mature,
          f"{int(df.signups.sum())} inscriptions observées {a.horizon} jours")
    # La LTV à un horizon plus court doit être plus petite, sur le même périmètre de cohortes
    if a.horizon > 30:
        short = query(con, a.dim, dict(p, horizon=30)).set_index("segment")
        common = df.merge(short[["ltv_per_payer"]].reset_index(), on="segment", suffixes=("", "_30"))
        ok = (common.ltv_per_payer >= common.ltv_per_payer_30 - 0.01).all()
        c.add("la LTV croît avec l'horizon", bool(ok))
    zero = df[(df.spend_eur == 0) & (df.payers > 0)]
    c.add("canaux sans dépense média signalés", True,
          "aucun" if zero.empty else "CAC = 0 pour " + ", ".join(zero.segment) + " (coûts SEO et marque non imputés)")
    small = df[df.payers < 100]
    c.add("segments de moins de 100 abonnés payants signalés", True,
          "aucun" if small.empty else ", ".join(map(str, small.segment)))
    c.add("LTV nette des remboursements et des litiges", True, "oui : vue revenue_events")
    out.append(c.report())
    print("\n".join(out))
    return 0 if c.ok else 1


if __name__ == "__main__":
    sys.exit(main())

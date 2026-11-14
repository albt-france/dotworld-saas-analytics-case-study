"""Skill cohort-retention : rétention par cohorte et par cycle, churn volontaire / involontaire.

Exemple :
  python skills/cohort-retention/run.py --products A B C --start 2025-01-01 --end 2026-01-01 --grain quarter
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
from skillkit import Checks, connect, render, run, show  # noqa: E402

GRAINS = {"month": "month", "mois": "month", "quarter": "quarter", "trimestre": "quarter"}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-01-01")
    ap.add_argument("--end", default="2026-01-01")
    ap.add_argument("--products", nargs="+", default=["A", "B", "C"])
    ap.add_argument("--grain", default="quarter", choices=sorted(GRAINS))
    ap.add_argument("--max-cycle", type=int, default=12)
    a = ap.parse_args(argv)
    p = dict(start=a.start, end=a.end, products=a.products, max_cycle=a.max_cycle)

    con = connect()
    sql = (HERE / "queries" / "retention.sql").read_text(encoding="utf-8").replace("__GRAIN__", GRAINS[a.grain])
    ret = con.sql(render(sql, p)).df()
    wide = ret.pivot_table(index=["product", "cohort"], columns="cycle", values="retention").reset_index()
    wide.columns = [str(c) if not isinstance(c, int) else f"C{c}" for c in wide.columns]
    churn = run(con, HERE / "queries" / "churn_split.sql", p)
    out = [f"# cohort-retention : produits {', '.join(a.products)}, inscriptions du {a.start} au {a.end}",
           show(wide, "Part des abonnés payants encore payants au cycle k (C1 = 1er cycle payé)"),
           show(churn, "Churn volontaire contre involontaire")]

    # ---- Contrôles ----
    c = Checks()
    c1 = ret[ret.cycle == 1]
    c.add("rétention au cycle 1 = 100 % (définition de la cohorte)", (c1.retention == 1).all())
    mono = ret.sort_values("cycle").groupby(["product", "cohort"])["retention"].apply(lambda s: s.is_monotonic_decreasing).all()
    c.add("la rétention ne remonte jamais d'un cycle au suivant", bool(mono))
    total = con.execute(render("""SELECT count(*) FROM customers WHERE paid_cycles >= 1 AND plan = 'essai_puis_mensuel'
                                  AND signup_ts >= {{start}} AND signup_ts < {{end}} AND product IN {{products}}""", p)).fetchall()[0][0]
    c.add("la somme des cohortes égale le nombre d'abonnés payants", int(c1.cohort_size.sum()) == total,
          f"{int(c1.cohort_size.sum())} contre {total}")
    last_cycle = ret.groupby(["product", "cohort"]).cycle.max()
    c.add("cohortes récentes tronquées (pas de cycle non observable)", True,
          "cycle maximal observé par cohorte : " + ", ".join(f"{k[0]}/{k[1]}={v}" for k, v in last_cycle.tail(3).items()))
    small = c1[c1.cohort_size < 200]
    c.add("cohortes de moins de 200 abonnés signalées", True,
          "aucune" if small.empty else ", ".join(f"{r.product}/{r.cohort}" for r in small.itertuples()))
    out.append(c.report())
    print("\n".join(out))
    return 0 if c.ok else 1


if __name__ == "__main__":
    sys.exit(main())

"""Skill payment-health : acceptation, refus et nouvelles tentatives par PSP, pays, produit.

Exemples :
  python skills/payment-health/run.py --countries ES --start 2026-01-01 --end 2026-07-01 --split 2026-04-01 --dim psp
  python skills/payment-health/run.py --countries BR MX --dim psp
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
from skillkit import Checks, connect, render, run, show  # noqa: E402

# Dimensions autorisées (liste blanche : jamais de nom de colonne libre dans le SQL)
DIMS = {"psp": "psp", "pays": "card_country", "card_country": "card_country", "produit": "product",
        "product": "product", "mid": "mid", "initiateur": "initiator", "initiator": "initiator",
        "type_carte": "card_type", "psp_pays": "psp || ' / ' || card_country"}
ALL = ["FR", "US", "DE", "ES", "IT", "GB", "BR", "MX", "PL", "NL"]
MIN_N = 300  # en dessous, un taux d'acceptation bouge de plus de +/- 3 points par simple hasard


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-01-01")
    ap.add_argument("--end", default="2026-07-01")
    ap.add_argument("--split", default=None, help="date de rupture pour comparer avant / après")
    ap.add_argument("--countries", nargs="+", default=ALL)
    ap.add_argument("--dim", default="psp", choices=sorted(DIMS))
    a = ap.parse_args(argv)
    p = dict(start=a.start, end=a.end, countries=a.countries, split=a.split or a.start)

    con = connect()
    acc_sql = (HERE / "queries" / "acceptance.sql").read_text(encoding="utf-8").replace("__DIM__", DIMS[a.dim])
    acc = con.sql(render(acc_sql, p)).df()
    out = [f"# payment-health : {', '.join(a.countries)} du {a.start} au {a.end}", show(acc, f"Acceptation par {a.dim}")]
    ba = None
    if a.split:
        ba = run(con, HERE / "queries" / "before_after.sql", p)
        out.append(show(ba, f"Acceptation avant / après le {a.split}"))
        codes = run(con, HERE / "queries" / "decline_codes.sql", p)
        codes = codes.sort_values("change_pts", ascending=False).groupby("psp").head(3)
        out.append(show(codes, "Codes de refus qui ont le plus augmenté (en points de % des tentatives)"))
    ret = run(con, HERE / "queries" / "retries.sql", p)
    out.append(show(ret[ret.first_code != "RELANCE APRÈS REFUS DÉFINITIF"],
                    "Nouvelles tentatives (MIT) par code initial et délai"))

    # ---- Contrôles de cohérence ----
    c = Checks()
    base = render("""SELECT count(*) FILTER (WHERE attempt_no = 1) AS first_n,
                            count(DISTINCT payment_id) AS payments,
                            count(*) FILTER (WHERE attempt_no = 1 AND outcome NOT IN ('approved','declined')) AS bad_outcome
                     FROM payment_attempts
                     WHERE ts_utc >= {{start}} AND ts_utc < {{end}} AND card_country IN {{countries}}""", p)
    first_n, payments, bad = con.execute(base).fetchall()[0]
    c.add("une seule tentative initiale par paiement", first_n <= payments and first_n >= 0.97 * payments,
          f"{first_n} tentatives initiales pour {payments} paiements (l'écart = paiements dont la 1re tentative est hors période)")
    c.add("le total des segments égale le total de la période", int(acc.first_attempts.sum()) == first_n,
          f"{int(acc.first_attempts.sum())} contre {first_n}")
    c.add("taux compris entre 0 et 1", acc.acceptance_rate.between(0, 1).all())
    c.add("résultats valides uniquement", bad == 0)
    small = acc[acc.first_attempts < MIN_N]
    c.add(f"segments de moins de {MIN_N} tentatives signalés", True,
          "aucun" if small.empty else "à lire avec prudence : " + ", ".join(map(str, small.segment)))
    hard_n = con.execute(render("""
        SELECT count(*) FROM (
            SELECT attempt_no, lag(decline_type) OVER (PARTITION BY payment_id ORDER BY attempt_no) AS prev_type
            FROM payment_attempts
            WHERE ts_utc >= {{start}} AND ts_utc < {{end}} AND card_country IN {{countries}})
        WHERE attempt_no >= 2 AND prev_type = 'hard'""", p)).fetchall()[0][0]
    c.add("relances après refus définitif (règles des réseaux)", True,
          "aucune" if hard_n == 0 else f"ALERTE CONFORMITÉ : {hard_n} relances à arrêter")
    if ba is not None:
        c.add("au moins 300 tentatives de chaque côté de la rupture", (ba[["n_before", "n_after"]] >= MIN_N).all().all(),
              ", ".join(f"{r.psp} {r.n_before}/{r.n_after}" for r in ba.itertuples()))
    out.append(c.report())
    print("\n".join(out))
    return 0 if c.ok else 1


if __name__ == "__main__":
    sys.exit(main())

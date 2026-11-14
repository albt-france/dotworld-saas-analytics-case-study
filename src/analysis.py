"""Analyses statistiques sur le parcours SIMULÉ, à partir des résultats SQL (data/results).

1. Délai de rentabilisation par canal (courbe de LTV contre CAC)
2. Effet d'un routage entre PSP (simulation « et si ») avec intervalle de confiance
3. Revenu perdu évitable : routage, calendrier des nouvelles tentatives, incident Espagne
4. Pont de réconciliation PSP contre base interne
5. Lecture de l'expérimentation sur le parcours d'essai (SRM, intervalles, puissance)

Sortie : data/results/key_numbers.json (+ quelques CSV)
Usage   : python src/analysis.py   (après src/simulate.py et src/run_sql.py)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "data" / "results"
Z = stats.norm.ppf(0.975)


def r(name: str) -> pd.DataFrame:
    return pd.read_csv(RES / f"{name}.csv")


def diff_prop_ci(x1, n1, x2, n2):
    """Différence de proportions p1 - p2 et IC à 95 % (approximation normale de Wald)."""
    p1, p2 = x1 / n1, x2 / n2
    se = np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    d = p1 - p2
    return d, d - Z * se, d + Z * se


# ------------------------------------------------------------------------------------
# 1. Délai de rentabilisation
# ------------------------------------------------------------------------------------
def payback() -> pd.DataFrame:
    ltv = r("ltv_curve")
    ch = r("channel_ltv_180").set_index("channel")
    rows = []
    for c, g in ltv.groupby("channel"):
        cac = ch.loc[c, "cac_eur"] if c in ch.index else np.nan
        g = g.sort_values("day")
        hit = g[g["ltv_per_payer"] >= cac] if cac > 0 else g.iloc[:1]
        rows.append(dict(channel=c, cac_eur=cac,
                         ltv_365=g.loc[g["day"] == g["day"].max(), "ltv_per_payer"].iloc[0],
                         payback_day=int(hit["day"].iloc[0]) if len(hit) else None))
    out = pd.DataFrame(rows)
    out.to_csv(RES / "payback.csv", index=False)
    return out


# ------------------------------------------------------------------------------------
# 2. Routage : et si l'on envoyait BR et MX vers PSP_A ?
# ------------------------------------------------------------------------------------
def routing() -> dict:
    d = r("routing_whatif_inputs")
    out = {}
    rows = []
    for country in ["BR", "MX"]:
        s = d[(d.card_country == country) & (d.psp == "PSP_S")].iloc[0]
        a = d[(d.card_country == country) & (d.psp == "PSP_A")].iloc[0]
        diff, lo, hi = diff_prop_ci(a.approved, a.first_attempts, s.approved, s.first_attempts)
        # Paiements supplémentaires acceptés si le volume de PSP_S passait sur PSP_A
        n = s.first_attempts
        rev = lambda dd: dd * n * s.avg_amount_eur
        rows.append(dict(country=country, n_psp_s=int(n), acc_psp_s=s.approved / s.first_attempts,
                         acc_psp_a=a.approved / a.first_attempts, diff=diff, diff_lo=lo, diff_hi=hi,
                         extra_approved=diff * n, revenue_eur=rev(diff), revenue_lo=rev(lo), revenue_hi=rev(hi)))
    df = pd.DataFrame(rows)
    df.to_csv(RES / "routing_whatif.csv", index=False)
    out["routing"] = df.round(4).to_dict("records")
    return out


# ------------------------------------------------------------------------------------
# 3. Revenu perdu évitable (sur les 18 mois observés, revenu immédiat uniquement)
# ------------------------------------------------------------------------------------
def avoidable(routing_df: pd.DataFrame) -> dict:
    # a) Calendrier des nouvelles tentatives : passer les relances J0 et J1 à J5 (code par code)
    rc = r("retry_by_code_delay")
    avg_renewal = 24.0  # montant moyen d'un renouvellement en EUR (A 27,95 ; B 14,95 ; C 19,90 pondérés)
    gain, var = 0.0, 0.0
    for code, g in rc.groupby("first_code"):
        g = g.set_index("delay_days")
        p5, n5 = g.loc[5.0, "success_rate"], g.loc[5.0, "retries"]
        for dly in (0.0, 1.0):
            p, n = g.loc[dly, "success_rate"], g.loc[dly, "retries"]
            gain += (p5 - p) * n
            var += n ** 2 * (p5 * (1 - p5) / n5 + p * (1 - p) / n)
    retry = dict(extra_recovered=gain, lo=gain - Z * np.sqrt(var), hi=gain + Z * np.sqrt(var))
    retry.update(revenue_eur=retry["extra_recovered"] * avg_renewal, revenue_lo=retry["lo"] * avg_renewal,
                 revenue_hi=retry["hi"] * avg_renewal)

    # b) Incident Espagne sur PSP_S depuis avril 2026 : écart d'acceptation avant / après
    es = r("acceptance_weekly_es")
    es["week"] = pd.to_datetime(es["week"])
    s = es[es.psp == "PSP_S"]
    before = s[(s.week >= "2025-10-01") & (s.week < "2026-03-30")]
    after = s[s.week >= "2026-03-30"]
    xb = (before.acceptance_rate * before.first_attempts).sum()
    nb = before.first_attempts.sum()
    xa = (after.acceptance_rate * after.first_attempts).sum()
    na = after.first_attempts.sum()
    dd, lo, hi = diff_prop_ci(xb, nb, xa, na)
    avg_es = 22.0
    incident = dict(acc_before=xb / nb, acc_after=xa / na, drop=dd, drop_lo=lo, drop_hi=hi, attempts_after=int(na),
                    revenue_eur=dd * na * avg_es, revenue_lo=lo * na * avg_es, revenue_hi=hi * na * avg_es)

    rt = routing_df
    total = dict(
        revenue_eur=float(rt.revenue_eur.sum() + retry["revenue_eur"] + incident["revenue_eur"]),
        lo=float(rt.revenue_lo.sum() + retry["revenue_lo"] + incident["revenue_lo"]),
        hi=float(rt.revenue_hi.sum() + retry["revenue_hi"] + incident["revenue_hi"]),
    )
    return dict(retry_schedule=retry, es_incident=incident, avoidable_total=total)


# ------------------------------------------------------------------------------------
# 4. Pont de réconciliation
# ------------------------------------------------------------------------------------
def reconciliation() -> dict:
    m = r("reconciliation_monthly")
    b = r("reconciliation_bridge").iloc[0]
    psp_only = r("reconciliation_psp_only_items").set_index("type")
    gap = float(m.gap_gross_eur.sum())  # PSP brut - interne
    bridge = {
        "Doublons dans la base interne (webhooks rejoués)": -float(b.duplicates_internal_eur),
        "Paiements absents de la base interne (webhooks perdus)": float(b.missing_in_internal_eur),
        "Litiges débités par le PSP, absents de la base": float(psp_only.loc["dispute", "gross_eur"]),
        "Change : taux du jour contre taux moyen du mois": float(b.fx_difference_eur),
    }
    explained = sum(bridge.values())
    bridge["Résidu (remboursements, bords de période)"] = gap - explained
    out = dict(gap_total_eur=gap, internal_total_eur=float(m.internal_eur.sum()),
               gap_pct=gap / float(m.internal_eur.sum()), bridge=bridge,
               month_shift_n=int(b.month_shift_n), month_shift_eur=float(b.month_shift_eur),
               psp_fees_eur=float(psp_only.loc["charge", "fee_eur"]))
    pd.DataFrame({"cause": list(bridge), "eur": list(bridge.values())}).to_csv(RES / "reconciliation_bridge_table.csv", index=False)
    return out


# ------------------------------------------------------------------------------------
# 5. Expérimentation
# ------------------------------------------------------------------------------------
def experiment() -> dict:
    u = r("experiment_users")
    g = u.groupby("variant")
    n = g.size()
    # Déséquilibre d'échantillon (SRM) : test du khi-deux contre un partage 50/50
    srm_p = stats.chisquare(n.values).pvalue
    res = {"n": n.to_dict(), "srm_p": srm_p}
    c, t = u[u.variant == "control"], u[u.variant == "prix_transparent"]
    for metric in ["trial_checkout", "paid_first_renewal"]:
        d, lo, hi = diff_prop_ci(t[metric].sum(), len(t), c[metric].sum(), len(c))
        z = d / np.sqrt(u[metric].mean() * (1 - u[metric].mean()) * (1 / len(t) + 1 / len(c)))
        res[metric] = dict(control=c[metric].mean(), variant=t[metric].mean(), diff=d, lo=lo, hi=hi,
                           rel=d / c[metric].mean(), p=2 * (1 - stats.norm.cdf(abs(z))))
    # Revenu net par utilisateur à 60 jours : test de Welch + IC bootstrap
    w = stats.ttest_ind(t.revenue_60d, c.revenue_60d, equal_var=False)
    rng = np.random.default_rng(42)
    boots = [rng.choice(t.revenue_60d.values, len(t)).mean() - rng.choice(c.revenue_60d.values, len(c)).mean()
             for _ in range(2000)]
    res["revenue_60d"] = dict(control=c.revenue_60d.mean(), variant=t.revenue_60d.mean(),
                              diff=t.revenue_60d.mean() - c.revenue_60d.mean(),
                              lo=float(np.percentile(boots, 2.5)), hi=float(np.percentile(boots, 97.5)), p=w.pvalue)
    # Garde-fou : litiges pour 1 000 utilisateurs payants
    cp, tp = c[c.paid_first_renewal == 1], t[t.paid_first_renewal == 1]
    # même définition que METRICS.md et le skill experiment-readout : payants avec au moins un litige
    res["disputes_per_1000_payers"] = dict(control=1000 * (cp.disputes_60d > 0).mean(),
                                           variant=1000 * (tp.disputes_60d > 0).mean(),
                                           control_n=int(cp.disputes_60d.sum()), variant_n=int(tp.disputes_60d.sum()),
                                           payers_control=len(cp), payers_variant=len(tp))
    dd, dlo, dhi = diff_prop_ci((tp.disputes_60d > 0).sum(), len(tp), (cp.disputes_60d > 0).sum(), len(cp))
    res["disputes_per_1000_payers"].update(diff=1000 * dd, lo=1000 * dlo, hi=1000 * dhi)
    # Payeurs nécessaires par groupe pour détecter une baisse de 30 % des litiges (80 %, alpha 5 %)
    q0 = (cp.disputes_60d > 0).mean()
    q1 = q0 * 0.7
    res["payers_per_arm_for_30pct_dispute_drop"] = int(np.ceil(
        (Z + stats.norm.ppf(0.8)) ** 2 * (q0 * (1 - q0) + q1 * (1 - q1)) / (q0 - q1) ** 2))
    # Puissance : effet minimal détectable (80 %, alpha 5 %) sur la conversion payante
    p0 = c.paid_first_renewal.mean()
    mde = (Z + stats.norm.ppf(0.8)) * np.sqrt(2 * p0 * (1 - p0) / min(len(c), len(t)))
    res["mde_paid_abs"] = mde
    res["mde_paid_rel"] = mde / p0
    # Taille nécessaire pour détecter +5 % relatif
    target = 0.05 * p0
    res["n_per_arm_for_5pct_rel"] = int(np.ceil(((Z + stats.norm.ppf(0.8)) ** 2) * 2 * p0 * (1 - p0) / target ** 2))
    return res


def main():
    pb = payback()
    rt = routing()
    rdf = pd.read_csv(RES / "routing_whatif.csv")
    av = avoidable(rdf)
    rec = reconciliation()
    ex = experiment()
    key = dict(payback=pb.to_dict("records"), **rt, **av, reconciliation=rec, experiment=ex)
    (RES / "key_numbers.json").write_text(json.dumps(key, indent=2, ensure_ascii=False, default=float), encoding="utf-8")
    print(json.dumps(key, indent=1, ensure_ascii=False, default=float)[:6000])


if __name__ == "__main__":
    main()

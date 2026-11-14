"""Skill experiment-readout : lecture d'un test A/B au niveau d'un Data Analyst.

Contrôles d'abord (SRM, affectation unique, fenêtre complète), puis effets avec intervalles
de confiance, garde-fous, puissance, et une décision écrite selon une règle fixée à l'avance.

Exemple :
  python skills/experiment-readout/run.py --experiment EXP-A-PRIX-TRANSPARENT --window 60 --primary revenue
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
from skillkit import Checks, connect, render, run, show  # noqa: E402

Z = stats.norm.ppf(0.975)
METRICS = {"trial_checkout": "prop", "paid_first_renewal": "prop", "revenue": "mean"}


def prop_effect(t, c):
    p1, p0 = t.mean(), c.mean()
    se = np.sqrt(p1 * (1 - p1) / len(t) + p0 * (1 - p0) / len(c))
    pooled = np.concatenate([t, c]).mean()
    z = (p1 - p0) / np.sqrt(pooled * (1 - pooled) * (1 / len(t) + 1 / len(c)))
    return p0, p1, p1 - p0, p1 - p0 - Z * se, p1 - p0 + Z * se, 2 * (1 - stats.norm.cdf(abs(z)))


def mean_effect(t, c, seed=42, b=2000):
    rng = np.random.default_rng(seed)
    boots = [rng.choice(t, len(t)).mean() - rng.choice(c, len(c)).mean() for _ in range(b)]
    p = stats.ttest_ind(t, c, equal_var=False).pvalue
    return c.mean(), t.mean(), t.mean() - c.mean(), np.percentile(boots, 2.5), np.percentile(boots, 97.5), p


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--experiment", default="EXP-A-PRIX-TRANSPARENT")
    ap.add_argument("--window", type=int, default=60, help="jours suivis après l'affectation")
    ap.add_argument("--primary", default="revenue", choices=sorted(METRICS))
    ap.add_argument("--control", default="control")
    a = ap.parse_args(argv)
    p = dict(experiment_id=a.experiment, window=a.window)

    con = connect()
    u = run(con, HERE / "queries" / "units.sql", p)
    variants = sorted(set(u.variant) - {a.control})
    if len(variants) != 1:
        sys.exit("Ce skill lit un test à deux groupes (contrôle + une variante).")
    v = variants[0]
    c_, t_ = u[u.variant == a.control], u[u.variant == v]

    # ---- Contrôles AVANT toute lecture d'effet ----
    c = Checks()
    srm_p = stats.chisquare([len(c_), len(t_)]).pvalue
    c.add("pas de déséquilibre d'échantillon (SRM, khi-deux, p > 0,001)", srm_p > 0.001,
          f"{len(c_)} contre {len(t_)}, p = {srm_p:.3f}")
    c.add("chaque utilisateur affecté une seule fois", u.signup_id.is_unique)
    obs_end = pd.Timestamp(con.execute("SELECT obs_end FROM params").fetchall()[0][0])
    last = pd.Timestamp(u.assigned_at.max())
    c.add(f"fenêtre de {a.window} jours complète pour tous", last + pd.Timedelta(days=a.window) <= obs_end,
          f"dernière affectation {last:%Y-%m-%d}, observation jusqu'au {obs_end:%Y-%m-%d}")
    mix = pd.crosstab(u.variant, u.device, normalize="index")
    c.add("répartition des appareils comparable entre groupes", (mix.max() - mix.min()).max() < 0.02,
          "écart max " + f"{(mix.max() - mix.min()).max():.3f}")

    rows = []
    for m, kind in METRICS.items():
        res = prop_effect(t_[m].values, c_[m].values) if kind == "prop" else mean_effect(t_[m].values, c_[m].values)
        rows.append(dict(metric=m + (" (principale)" if m == a.primary else ""), control=res[0], variant=res[1],
                         diff=res[2], ci_low=res[3], ci_high=res[4], p_value=res[5]))
    eff = pd.DataFrame(rows)
    # Garde-fous : litiges et remboursements pour 1 000 abonnés payants
    guard = []
    for name in ["disputes", "refunds"]:
        cp, tp = c_[c_.paid_first_renewal == 1], t_[t_.paid_first_renewal == 1]
        r0, r1 = (cp[name] > 0).mean(), (tp[name] > 0).mean()
        se = np.sqrt(r0 * (1 - r0) / len(cp) + r1 * (1 - r1) / len(tp))
        guard.append(dict(guardrail=name + " pour 1 000 payants", control=1000 * r0, variant=1000 * r1,
                          diff=1000 * (r1 - r0), ci_low=1000 * (r1 - r0 - Z * se), ci_high=1000 * (r1 - r0 + Z * se),
                          events=f"{int(cp[name].sum())} / {int(tp[name].sum())}"))
    guard = pd.DataFrame(guard)
    # Puissance : effet minimal détectable sur la métrique principale (80 %, alpha 5 %)
    n = min(len(c_), len(t_))
    k = Z + stats.norm.ppf(0.8)
    if METRICS[a.primary] == "prop":
        p0 = c_[a.primary].mean()
        mde = k * np.sqrt(2 * p0 * (1 - p0) / n)
    else:
        mde = k * np.sqrt(c_[a.primary].var() / n + t_[a.primary].var() / n)
    base = c_[a.primary].mean()

    # ---- Décision (règle écrite AVANT de regarder les résultats) ----
    prim = eff.iloc[list(METRICS).index(a.primary)]
    disp = guard.iloc[0]
    if not c.ok:
        decision = "AUCUNE : un contrôle échoue, le test n'est pas lisible."
    elif prim.ci_low > 0 and disp.ci_high <= 0.5 * max(disp.control, 1):
        decision = "GÉNÉRALISER : effet positif significatif, garde-fous respectés."
    elif prim.ci_high < 0:
        decision = "ARRÊTER : la variante dégrade la métrique principale."
    else:
        decision = ("PAS DE CONCLUSION sur la métrique principale (l'intervalle contient 0). "
                    f"Effet minimal détectable : {mde:.2f} ({mde / base:.0%} de la valeur de contrôle). "
                    "Ne pas généraliser sur cette base ; décider selon le coût et l'objectif secondaire.")

    out = [f"# experiment-readout : {a.experiment} ({a.control} contre {v}), fenêtre {a.window} jours",
           show(pd.DataFrame({"groupe": [a.control, v], "utilisateurs": [len(c_), len(t_)]}), "Échantillon"),
           c.report(),
           show(eff.round(4), "Effets (différence variante - contrôle, IC à 95 %)"),
           show(guard.round(2), "Garde-fous"),
           f"\nPuissance : effet minimal détectable sur « {a.primary} » = {mde:.3f} (soit {mde / base:.0%} de la valeur de contrôle).",
           f"\nDÉCISION : {decision}"]
    print("\n".join(out))
    return 0 if c.ok else 1


if __name__ == "__main__":
    sys.exit(main())

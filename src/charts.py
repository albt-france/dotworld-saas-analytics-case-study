"""Graphiques du rapport (matplotlib -> SVG), style de l'étude : fond clair, bleu pour la donnée,
gris pour la comparaison, rouge pour les alertes, pointillés pour les seuils, Segoe UI."""
from __future__ import annotations

import io
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

BLUE, BLUE_L, BLUE_D = "#2A78D6", "#86B6EF", "#1C5CAB"
ORANGE, GREEN, AMBER = "#EB6834", "#1BAF7A", "#EDA100"
GRAY, GRAY_D, RED = "#C9C7BF", "#898781", "#D03B3B"
INK, INK2, GRID, CARD = "#0B0B0B", "#52514E", "#E1E0D9", "#FCFCFB"
PRODUCT_COLORS = {"A": BLUE, "B": ORANGE, "C": GREEN}
PSP_COLORS = {"PSP_S": BLUE, "PSP_A": ORANGE}

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 9.5, "text.color": INK2,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "axes.facecolor": CARD, "figure.facecolor": CARD,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": GRID, "grid.linewidth": 0.8,
    "xtick.color": GRAY_D, "ytick.color": GRAY_D, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "xtick.major.size": 0, "ytick.major.size": 0, "legend.frameon": False, "legend.fontsize": 9,
    "svg.fonttype": "none", "axes.axisbelow": True, "hatch.color": "white",
})


def fig(w_px, h_px):
    return plt.subplots(figsize=(w_px / 96, h_px / 96), dpi=96)


def svg(f) -> str:
    buf = io.StringIO()
    f.savefig(buf, format="svg", bbox_inches="tight", pad_inches=0.05)
    plt.close(f)
    s = buf.getvalue()
    s = s[s.find("<svg"):]
    s = re.sub(r'width="[\d.]+pt" height="[\d.]+pt"', 'width="100%" height="100%" preserveAspectRatio="xMidYMid meet"', s, 1)
    s = re.sub(r"<metadata>.*?</metadata>", "", s, flags=re.S)  # pas de métadonnées (outil, date)
    return s


def eur(x, d=0):
    s = f"{x:,.{d}f}".replace(",", " ").replace(".", ",")
    return s + " €"


def pct(x, d=1):
    return f"{100 * x:.{d}f}".replace(".", ",") + " %"


# ---------------------------------------------------------------- page 1 : prix publics
def price_paths(w=560, h=300):
    days = np.arange(0, 366)
    trial = np.where(days >= 0, 2.90, 0) + np.array([27.95 * (((d - 7) // 28) + 1) if d >= 7 else 0 for d in days])
    annual = np.full_like(days, 94.80, dtype=float)
    f, ax = fig(w, h)
    ax.step(days, trial, where="post", color=BLUE, lw=2, label="Essai 2,90 € puis 27,95 € / 4 semaines")
    ax.step(days, annual, where="post", color=GRAY_D, lw=2, label="Accès annuel 94,80 €")
    ax.annotate(f"{eur(trial[-1], 2)} la 1re année", (343, trial[-1]), xytext=(-6, 6), textcoords="offset points",
                ha="right", va="bottom", color=BLUE_D, fontsize=9.5, fontweight="bold")
    ax.annotate("94,80 €", (365, 94.8), xytext=(-4, 4), textcoords="offset points", ha="right", color=INK2)
    ax.axvline(91, color=GRAY_D, ls=(0, (3, 3)), lw=1)
    ax.text(97, 330, "Dès le 4e renouvellement (J+91),\nla formule mensuelle coûte\nplus cher que l'annuel", fontsize=8.5, color=INK2, va="top")
    ax.set_xlim(0, 370); ax.set_ylim(0, 430)
    ax.set_xlabel("Jours après le paiement de l'essai"); ax.set_ylabel("Montant cumulé payé (€)")
    ax.legend(loc="upper left")
    return svg(f)


# ---------------------------------------------------------------- page 2 : KKBox
def kkbox_retention(df, w=560, h=280):
    f, ax = fig(w, h)
    df = df[df.k <= 12]
    piv = df.pivot_table(index="k", columns="cohort", values="retention")
    for c in piv.columns:
        ax.plot(piv.index, piv[c], color=GRAY, lw=1)
    mean = piv.mean(axis=1)
    ax.plot(mean.index, mean.values, color=BLUE, lw=2.5, label="Moyenne des cohortes")
    for k in (1, 6, 12):
        if k in mean.index:
            ax.annotate(pct(mean[k], 0), (k, mean[k]), xytext=(0, 7), textcoords="offset points", ha="center",
                        color=BLUE_D, fontweight="bold")
    ax.set_ylim(0, 1.05); ax.set_xlim(-0.3, 12.5)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    ax.set_xlabel("Mois après le premier paiement"); ax.legend(loc="upper right")
    return svg(f)


def kkbox_bars(labels, values, w=420, h=240, colors=None, fmt=pct, highlight=None):
    f, ax = fig(w, h)
    y = np.arange(len(labels))
    cols = colors or [BLUE if (highlight is None or i == highlight) else GRAY for i in range(len(labels))]
    ax.barh(y, values, color=cols, height=0.55)
    for i, v in enumerate(values):
        ax.text(v, i, " " + fmt(v), va="center", color=INK, fontsize=9.5)
    ax.set_yticks(y, labels); ax.invert_yaxis(); ax.grid(False)
    ax.set_xticks([]); ax.set_xlim(0, max(values) * 1.3)
    ax.tick_params(axis="y", colors=INK2)
    return svg(f)


# ---------------------------------------------------------------- page 3 : acquisition
def cac_vs_ltv(df, w=560, h=300):
    df = df[df.cac_eur > 0].sort_values("roas_180", ascending=True)
    f, ax = fig(w, h)
    y = np.arange(len(df))
    ax.barh(y + 0.18, df.ltv180_per_payer, height=0.34, color=BLUE, label="LTV 180 jours par abonné payant")
    ax.barh(y - 0.18, df.cac_eur, height=0.34, color=GRAY, label="CAC (dépense média par abonné payant)")
    for i, r in enumerate(df.itertuples()):
        ax.text(r.ltv180_per_payer + 1, i + 0.18, eur(r.ltv180_per_payer), va="center", fontsize=9, color=INK)
        ax.text(r.cac_eur + 1, i - 0.18, eur(r.cac_eur), va="center", fontsize=9, color=INK2)
        ax.text(112, i, f"ROAS {r.roas_180:.1f}".replace(".", ","), va="center", ha="right", fontsize=10,
                color=RED if r.roas_180 < 1.5 else BLUE_D, fontweight="bold")
    ax.set_yticks(y, df.channel); ax.tick_params(axis="y", colors=INK, labelsize=10)
    ax.set_xlim(0, 115); ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    ax.legend(loc="lower center", bbox_to_anchor=(0.45, -0.28), ncol=2)
    return svg(f)


def cost_visit_vs_payer(df, w=420, h=300):
    f, ax = fig(w, h)
    df = df.sort_values("cost_per_visit")
    x = np.arange(len(df))
    ax.bar(x - 0.2, df.cost_per_visit / df.cost_per_visit.max(), width=0.38, color=GRAY, label="Coût par visite")
    ax.bar(x + 0.2, df.media_cost_per_payer / df.media_cost_per_payer.max(), width=0.38, color=BLUE, label="Coût par abonné payant")
    for i, r in enumerate(df.itertuples()):
        ax.text(i - 0.2, r.cost_per_visit / df.cost_per_visit.max() + 0.02, eur(r.cost_per_visit, 2), ha="center", fontsize=8.5)
        ax.text(i + 0.2, r.media_cost_per_payer / df.media_cost_per_payer.max() + 0.02, eur(r.media_cost_per_payer), ha="center",
                fontsize=8.5, color=INK)
    ax.set_xticks(x, df.channel); ax.tick_params(axis="x", colors=INK, labelsize=10)
    ax.set_yticks([]); ax.set_ylim(0, 1.2); ax.grid(False)
    ax.set_ylabel("Indice (max = 1)")
    ax.legend(loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.12))
    return svg(f)


# ---------------------------------------------------------------- page 4 : parcours
def funnel_per100(df, w=560, h=280):
    steps = [("signups", "Inscription"), ("checkout", "Paiement de\nl'essai lancé"), ("trial_started", "Essai\nactif"),
             ("first_paid", "1er renouvel-\nlement payé"), ("second_paid", "2e renouvel-\nlement payé")]
    f, ax = fig(w, h)
    x = np.arange(len(steps))
    wdt = 0.26
    for j, prod in enumerate(["A", "B", "C"]):
        r = df[df["product"] == prod].iloc[0]
        vals = [100 * r[s] / r["signups"] for s, _ in steps]
        ax.bar(x + (j - 1) * wdt, vals, width=wdt - 0.03, color=PRODUCT_COLORS[prod], label=f"Produit {prod}")
        for i, v in enumerate(vals[1:], 1):
            ax.text(i + (j - 1) * wdt, v + 1.5, f"{v:.0f}", ha="center", fontsize=8, color=INK2)
    ax.set_xticks(x, [s[1] for s in steps]); ax.tick_params(axis="x", colors=INK, labelsize=8.5)
    ax.set_ylabel("Pour 100 inscrits"); ax.set_ylim(0, 112)
    ax.legend(loc="upper right", ncol=3)
    return svg(f)


def trial_outcomes(df, w=420, h=240):
    cols = [("refus_paiement_essai", "Refus du paiement de l'essai", RED),
            ("annule_pendant_essai", "Annulé pendant l'essai", GRAY),
            ("refus_au_1er_renouvellement", "Refus au 1er renouvellement", ORANGE),
            ("converti", "Converti en abonné payant", BLUE)]
    f, ax = fig(w, h)
    df = df.set_index("product")
    left = np.zeros(len(df))
    others = df["checkout"] - df[[c for c, _, _ in cols]].sum(axis=1)
    for c, lab, colr in cols:
        v = df[c] / df["checkout"]
        ax.barh(df.index, v, left=left, color=colr, label=lab, height=0.55, edgecolor=CARD, linewidth=2)
        for i, (vv, ll) in enumerate(zip(v, left)):
            if vv > 0.07:
                ax.text(ll + vv / 2, i, pct(vv, 0), ha="center", va="center", color="white", fontsize=8.5, fontweight="bold")
        left += v
    ax.set_yticks(range(len(df)), [f"Produit {p}" for p in df.index]); ax.invert_yaxis()
    ax.set_xticks([]); ax.grid(False); ax.set_xlim(0, 1)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=2, fontsize=8)
    return svg(f)


def retention_curves(df, w=420, h=260):
    f, ax = fig(w, h)
    d = df.copy()
    d["w"] = d["eligible"] * d["retention"]
    for prod in ["A", "B", "C"]:
        g = d[d["product"] == prod].groupby("cycle").apply(lambda x: x["w"].sum() / x["eligible"].sum(), include_groups=False)
        g = g[g.index <= 10]
        ax.plot(g.index, g.values, color=PRODUCT_COLORS[prod], lw=2, marker="o", ms=4, label=f"Produit {prod}")
        dy = {"A": 0, "B": 8, "C": -9}[prod]
        ax.annotate(f"{prod} {pct(g.iloc[-1], 0)}", (g.index[-1], g.iloc[-1]), xytext=(6, dy), textcoords="offset points",
                    va="center", fontsize=9, color=INK)
    ax.set_ylim(0, 1.05); ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    ax.set_xlabel("Cycle facturé (1 = premier cycle payé)"); ax.set_xticks(range(1, 11)); ax.set_xlim(0.7, 11.2)
    ax.legend(loc="upper right")
    return svg(f)


def involuntary_by_tenure(df, w=420, h=240):
    f, ax = fig(w, h)
    ten = ["1 cycle", "2-3 cycles", "4 cycles et +"]
    x = np.arange(3)
    for j, prod in enumerate(["A", "B", "C"]):
        g = df[df["product"] == prod].set_index("tenure").loc[ten]
        ax.bar(x + (j - 1) * 0.26, g.share_involuntary, width=0.23, color=PRODUCT_COLORS[prod], label=f"Produit {prod}")
        for i, v in enumerate(g.share_involuntary):
            ax.text(i + (j - 1) * 0.26, v + 0.01, f"{100 * v:.0f}", ha="center", fontsize=8, color=INK2)
    ax.set_xticks(x, ["Départ après\n1 cycle", "Après 2-3\ncycles", "Après 4 cycles\net plus"])
    ax.tick_params(axis="x", colors=INK)
    ax.set_ylim(0, 0.7); ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1, decimals=0))
    ax.legend(loc="upper left", ncol=3)
    return svg(f)


# ---------------------------------------------------------------- page 5 : paiements
def acceptance_country(df, w=560, h=290):
    order = ["FR", "DE", "ES", "IT", "NL", "PL", "GB", "US", "BR", "MX"]
    f, ax = fig(w, h)
    y = np.arange(len(order))
    for psp, off in (("PSP_S", -0.12), ("PSP_A", 0.12)):
        g = df[df.psp == psp].set_index("card_country").reindex(order)
        ax.scatter(g.acceptance_rate, y + off, s=55, color=PSP_COLORS[psp], zorder=3, label=psp,
                   edgecolor=CARD, linewidth=1.5)
    for i, c in enumerate(order):
        a = df[(df.psp == "PSP_A") & (df.card_country == c)].acceptance_rate.iloc[0]
        s = df[(df.psp == "PSP_S") & (df.card_country == c)].acceptance_rate.iloc[0]
        ax.plot([s, a], [i - 0.12, i + 0.12], color=GRAY, lw=1, zorder=2)
        if c in ("BR", "MX"):
            ax.text(max(a, s) + 0.012, i, f"PSP_S {pct(s, 0)} / PSP_A {pct(a, 0)}", ha="left", va="center", fontsize=8.5,
                    color=RED, fontweight="bold")
    ax.axhspan(7.5, 9.5, color="#F6E3E3", zorder=0)
    ax.set_yticks(y, order); ax.invert_yaxis(); ax.tick_params(axis="y", colors=INK)
    ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1, decimals=0))
    ax.set_xlim(0.45, 1.0); ax.set_xlabel("Taux d'acceptation des tentatives initiales")
    ax.legend(loc="lower center", ncol=2, bbox_to_anchor=(0.5, 1.0))
    return svg(f)


def retry_delay(df, w=420, h=250):
    f, ax = fig(w, h)
    lab = [("J0" if d == 0 else f"J+{int(d)}") for d in df.delay_days]
    cols = [RED if d <= 1 else BLUE for d in df.delay_days]
    ax.bar(lab, df.success_rate, color=cols, width=0.6)
    for i, v in enumerate(df.success_rate):
        ax.text(i, v + 0.004, pct(v, 0), ha="center", fontsize=9, color=INK)
    ax.set_ylim(0, df.success_rate.max() * 1.25)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1, decimals=0))
    ax.set_xlabel("Délai avant la nouvelle tentative (refus « soft »)"); ax.tick_params(axis="x", colors=INK)
    return svg(f)


def es_trend(df, w=420, h=250):
    f, ax = fig(w, h)
    df = df.copy(); df["week"] = pd.to_datetime(df["week"])
    for psp in ["PSP_S", "PSP_A"]:
        g = df[df.psp == psp].set_index("week").sort_index()
        acc = (g.acceptance_rate * g.first_attempts).rolling(4).sum() / g.first_attempts.rolling(4).sum()
        ax.plot(acc.index, acc.values, color=PSP_COLORS[psp], lw=2, label=psp)
    ax.axvline(pd.Timestamp("2026-04-01"), color=GRAY_D, ls=(0, (3, 3)), lw=1)
    ax.text(pd.Timestamp("2026-04-04"), 0.92, "1er avril", fontsize=8.5, color=INK2)
    ax.set_ylim(0.72, 0.95); ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1, decimals=0))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%m/%y"))
    ax.legend(loc="lower left", ncol=2); ax.set_ylabel("Acceptation (moyenne 4 semaines)")
    return svg(f)


def avoidable_bars(items, w=560, h=250):
    f, ax = fig(w, h)
    labels = [i[0] for i in items]; vals = [i[1] for i in items]; lo = [i[2] for i in items]; hi = [i[3] for i in items]
    y = np.arange(len(items))
    cols = [BLUE] * (len(items) - 1) + [BLUE_D]
    ax.barh(y, vals, color=cols, height=0.55)
    ax.errorbar(vals, y, xerr=[np.array(vals) - np.array(lo), np.array(hi) - np.array(vals)], fmt="none",
                ecolor=INK2, elinewidth=1, capsize=3)
    for i, (v, l_, h_) in enumerate(zip(vals, lo, hi)):
        ax.text(h_ + max(hi) * 0.02, i, f"{eur(v / 1000, 1).replace(' €', ' K€')}  ({l_ / 1000:.0f} à {h_ / 1000:.0f} K€)",
                va="center", fontsize=9, color=INK)
    ax.set_yticks(y, labels); ax.invert_yaxis(); ax.tick_params(axis="y", colors=INK)
    ax.set_xticks([]); ax.grid(False); ax.set_xlim(0, max(hi) * 1.55)
    return svg(f)


# ---------------------------------------------------------------- page 6 : risques
def vamp_line(df, mid, w=560, h=270):
    d = df[df.mid == mid].copy(); d["month"] = pd.to_datetime(d["month"])
    f, ax = fig(w, h)
    ax.plot(d.month, d.vamp_ratio, color=BLUE, lw=2, marker="o", ms=4, label=f"Ratio litiges + fraude, MID {mid} (Visa)")
    ax.step(d.month, d.visa_threshold, where="mid", color=RED, ls=(0, (4, 3)), lw=1.5, label="Seuil Visa VAMP (2,2 % puis 1,5 %)")
    over = d[d.vamp_ratio > d.visa_threshold]
    ax.scatter(over.month, over.vamp_ratio, color=RED, s=60, zorder=4)
    for r in over.itertuples():
        ax.annotate(pct(r.vamp_ratio, 2), (r.month, r.vamp_ratio), xytext=(0, 8), textcoords="offset points",
                    ha="center", color=RED, fontweight="bold", fontsize=9)
    ax.axvspan(pd.Timestamp("2026-02-15"), pd.Timestamp("2026-03-31"), color="#F6E3E3", zorder=0)
    ax.text(pd.Timestamp("2026-02-17"), 0.003, "campagne\nagressive", fontsize=8, color=RED)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1, decimals=1))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%m/%y"))
    ax.set_ylim(0, max(0.03, d.vamp_ratio.max() * 1.2)); ax.legend(loc="upper left", fontsize=8.5)
    return svg(f)


def disputes_campaign(df, w=420, h=270):
    df = df.sort_values("disputes_per_1000")
    f, ax = fig(w, h)
    cols = [RED if c == "meta_promo_choc" else GRAY for c in df.campaign]
    ax.barh(df.campaign, df.disputes_per_1000, color=cols, height=0.6)
    for i, v in enumerate(df.disputes_per_1000):
        ax.text(v + 0.8, i, f"{v:.0f}", va="center", fontsize=9, color=INK)
    avg = (df.disputes.sum() / df.first_renewals.sum()) * 1000
    ax.axvline(avg, color=GRAY_D, ls=(0, (3, 3)), lw=1)
    ax.text(avg + 1, -0.6, f"moyenne {avg:.0f}", fontsize=8, color=INK2)
    ax.set_xticks([]); ax.grid(False); ax.tick_params(axis="y", colors=INK)
    ax.set_xlabel("Litiges pour 1 000 premiers renouvellements")
    return svg(f)


def disputes_weekly(df, w=560, h=230):
    d = df.copy(); d["week"] = pd.to_datetime(d["week"])
    d = d[d.week < "2026-06-29"]
    f, ax = fig(w, h)
    ax.bar(d.week, d.disputes_other, width=5, color=GRAY, label="Autres clients")
    ax.bar(d.week, d.disputes_promo, width=5, bottom=d.disputes_other, color=RED, label="Clients de la campagne agressive")
    ax.axvspan(pd.Timestamp("2026-02-15"), pd.Timestamp("2026-03-31"), color="#F6E3E3", zorder=0)
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%m/%y")); ax.set_ylabel("Litiges par semaine")
    ax.set_ylim(0, (d.disputes_other + d.disputes_promo).max() * 1.1)
    ax.legend(loc="lower left", ncol=2, bbox_to_anchor=(0, 1.0))
    return svg(f)


# ---------------------------------------------------------------- page 7 : qualité
def recon_bridge(bridge: dict, w=560, h=260):
    f, ax = fig(w, h)
    labels = list(bridge); vals = np.array(list(bridge.values()))
    y = np.arange(len(labels))
    ax.barh(y, vals, color=[RED if v < 0 else BLUE for v in vals], height=0.55)
    for i, v in enumerate(vals):
        ax.text(v + (150 if v >= 0 else -150), i, eur(v), va="center", ha="left" if v >= 0 else "right", fontsize=9, color=INK)
    ax.axvline(0, color=GRAY_D, lw=1)
    ax.set_yticks(y, labels); ax.invert_yaxis(); ax.tick_params(axis="y", colors=INK, labelsize=9)
    ax.set_xticks([]); ax.grid(False)
    lim = np.abs(vals).max() * 1.6
    ax.set_xlim(-lim, lim * 0.9)
    return svg(f)


def recon_monthly(df, w=420, h=230):
    d = df.copy(); d["month"] = pd.to_datetime(d["month"])
    f, ax = fig(w, h)
    ax.bar(d.month, d.gap_pct, width=20, color=RED)
    ax.axhline(0, color=GRAY_D, lw=1)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1, decimals=1))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%m/%y"))
    ax.set_ylabel("(PSP − interne) / interne")
    return svg(f)


# ---------------------------------------------------------------- page 8 : expérimentation
def forest(rows, w=600, h=260):
    f, ax = fig(w, h)
    y = np.arange(len(rows))
    for i, (lab, d, lo, hi, col) in enumerate(rows):
        ax.plot([lo, hi], [i, i], color=col, lw=2.5, solid_capstyle="round")
        ax.scatter([d], [i], color=col, s=60, zorder=3, edgecolor=CARD, linewidth=1.5)
        ax.text(hi + 0.02, i, f"{d * 100:+.0f} %  [{lo * 100:+.0f} ; {hi * 100:+.0f}]".replace(".", ","), va="center", fontsize=9, color=INK)
    ax.axvline(0, color=GRAY_D, ls=(0, (3, 3)), lw=1)
    ax.set_yticks(y, [r[0] for r in rows]); ax.invert_yaxis(); ax.tick_params(axis="y", colors=INK, labelsize=9.5)
    ax.grid(axis="x"); ax.grid(axis="y", visible=False)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1, decimals=0))
    ax.set_xlim(-0.8, 0.75); ax.set_xlabel("Écart relatif variante / contrôle, intervalle de confiance à 95 %")
    return svg(f)

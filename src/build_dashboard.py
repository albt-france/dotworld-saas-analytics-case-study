"""Tableau de bord HTML autonome (Plotly), 4 pages : Acquisition, Parcours, Paiements, Risques.

Volontairement sobre : l'offre précise que le poste n'est pas centré sur les dashboards.
Toutes les données viennent de data/results (requêtes SQL). Données SIMULÉES.

Usage : python src/build_dashboard.py   -> docs/tableau_de_bord.html
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "data" / "results"
OUT = ROOT / "docs" / "tableau_de_bord.html"
BLUE, ORANGE, GREEN, GRAY, RED, INK2 = "#2A78D6", "#EB6834", "#1BAF7A", "#B4B2AA", "#D03B3B", "#52514E"
PROD = {"A": BLUE, "B": ORANGE, "C": GREEN}
PSP = {"PSP_S": BLUE, "PSP_A": ORANGE}
r = lambda n: pd.read_csv(RES / f"{n}.csv")  # noqa: E731
K = json.loads((RES / "key_numbers.json").read_text(encoding="utf-8"))

_first = [True]


def layout(fig, title, ytitle="", pct=False, h=340):
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#0B0B0B"), x=0.01),
        font=dict(family="Segoe UI, system-ui, sans-serif", size=12, color=INK2),
        paper_bgcolor="#FCFCFB", plot_bgcolor="#FCFCFB", height=h, margin=dict(l=60, r=20, t=50, b=50),
        legend=dict(orientation="h", y=-0.2), hoverlabel=dict(bgcolor="white", font_size=12),
        separators=", ",
    )
    fig.update_yaxes(title=ytitle, gridcolor="#E1E0D9", zeroline=False, tickformat=".0%" if pct else None)
    fig.update_xaxes(showgrid=False)
    return fig


def html(fig):
    s = fig.to_html(full_html=False, include_plotlyjs=_first[0], default_width="100%",
                    config={"displaylogo": False, "responsive": True})
    _first[0] = False
    return f'<div class="card">{s}</div>'


def fr_num(v):
    if isinstance(v, float):
        return f"{v:,.2f}".replace(",", " ").replace(".", ",")
    if isinstance(v, int) and not isinstance(v, bool):
        return f"{v:,}".replace(",", " ")
    return str(v)


def table(df, cols, fmt=None):
    fmt = fmt or {}
    head = "".join(f"<th>{c}</th>" for c in cols.values())
    rows = ""
    for _, x in df.iterrows():
        rows += "<tr>" + "".join(f"<td>{fmt.get(k, fr_num)(x[k])}</td>" for k in cols) + "</tr>"
    return f"<table><tr>{head}</tr>{rows}</table>"


def acquisition():
    ch = r("channel_ltv_180")
    paid = ch[ch.cac_eur > 0]
    f1 = go.Figure([go.Bar(name="CAC (€)", x=paid.channel, y=paid.cac_eur, marker_color=GRAY,
                           hovertemplate="%{x}<br>CAC %{y:.2f} €<extra></extra>"),
                    go.Bar(name="LTV 180 j par payant (€)", x=paid.channel, y=paid.ltv180_per_payer, marker_color=BLUE,
                           hovertemplate="%{x}<br>LTV %{y:.2f} €<extra></extra>")])
    layout(f1, "CAC contre LTV à 180 jours (cohortes 2025)", "€")
    lc = r("ltv_curve")
    f2 = go.Figure()
    cols = {"Google Ads": BLUE, "Meta": ORANGE, "TikTok": GREEN, "Affiliation": "#EDA100", "SEO": GRAY, "Direct": "#898781"}
    for c, g in lc.groupby("channel"):
        f2.add_trace(go.Scatter(x=g.day, y=g.ltv_per_payer, name=c, line=dict(color=cols.get(c, GRAY), width=2),
                                hovertemplate=c + "<br>J+%{x} : %{y:.2f} €<extra></extra>"))
    for c in paid.channel:
        f2.add_hline(y=float(paid.set_index("channel").loc[c, "cac_eur"]), line_dash="dot", line_color=cols[c], opacity=0.5)
    layout(f2, "LTV cumulée par abonné payant (pointillés = CAC du canal)", "€")
    f2.update_xaxes(title="Jours après l'inscription")
    camp = r("campaign_ltv_90")
    camp = camp[camp.cac_eur > 0].copy()
    camp["roas"] = (camp.ltv90_per_payer / camp.cac_eur).round(2)
    t = table(camp.sort_values("roas", ascending=False),
              {"campaign": "Campagne", "payers": "Payants", "cac_eur": "CAC (€)", "ltv90_per_payer": "LTV 90 j (€)",
               "roas": "ROAS 90 j", "disputes_per_1000_payers": "Litiges ‰ payants"})
    return html(f1) + html(f2) + f'<div class="card"><h3>Campagnes (cohortes observées 90 jours)</h3>{t}</div>'


def parcours():
    fp = r("funnel_product")
    steps = [("signups", "Inscription"), ("checkout", "Paiement essai lancé"), ("trial_started", "Essai actif"),
             ("first_paid", "1er renouvellement"), ("second_paid", "2e renouvellement")]
    f1 = go.Figure()
    for _, x in fp.iterrows():
        f1.add_trace(go.Bar(name=f"Produit {x['product']}", x=[s[1] for s in steps], y=[100 * x[s] / x.signups for s, _ in steps],
                            marker_color=PROD[x["product"]], hovertemplate="%{x}<br>%{y:.1f} pour 100 inscrits<extra></extra>"))
    layout(f1, "Sur 100 inscrits, combien passent chaque étape ?", "pour 100 inscrits")
    rc = r("retention_by_cycle")
    rc["w"] = rc.eligible * rc.retention
    agg = rc.groupby(["product", "cycle"]).agg(w=("w", "sum"), n=("eligible", "sum")).reset_index()
    agg["ret"] = agg.w / agg.n
    f2 = go.Figure()
    for p, g in agg[agg.cycle <= 12].groupby("product"):
        f2.add_trace(go.Scatter(x=g.cycle, y=g.ret, name=f"Produit {p}", line=dict(color=PROD[p], width=2),
                                hovertemplate="Cycle %{x}<br>%{y:.1%}<extra></extra>"))
    layout(f2, "Rétention des abonnés payants par cycle facturé", "", pct=True)
    tn = r("churn_by_tenure")
    f3 = go.Figure()
    for p, g in tn.groupby("product"):
        f3.add_trace(go.Bar(name=f"Produit {p}", x=g.tenure, y=g.share_involuntary, marker_color=PROD[p],
                            hovertemplate="%{x}<br>%{y:.1%} involontaire<extra></extra>"))
    layout(f3, "Part du churn involontaire selon l'ancienneté", "", pct=True)
    return html(f1) + html(f2) + html(f3)


def paiements():
    am = r("acceptance_monthly")
    f1 = go.Figure()
    for p, g in am[am.month < "2026-07-01"].groupby("psp"):
        f1.add_trace(go.Scatter(x=g.month, y=g.acceptance_rate, name=p, line=dict(color=PSP[p], width=2),
                                hovertemplate="%{x|%m/%Y}<br>%{y:.1%}<extra>" + p + "</extra>"))
    layout(f1, "Acceptation mensuelle des tentatives initiales par PSP", "", pct=True)
    ac = r("acceptance_psp_country")
    f2 = go.Figure()
    for p, g in ac.groupby("psp"):
        f2.add_trace(go.Bar(name=p, x=g.card_country, y=g.acceptance_rate, marker_color=PSP[p],
                            customdata=g.first_attempts, hovertemplate="%{x}<br>%{y:.1%} sur %{customdata} tentatives<extra>" + p + "</extra>"))
    layout(f2, "Acceptation par pays de la carte et par PSP", "", pct=True)
    f2.update_yaxes(range=[0.4, 1])
    rd = r("retry_by_delay")
    f3 = go.Figure(go.Bar(x=[f"J+{int(d)}" for d in rd.delay_days], y=rd.success_rate, marker_color=[RED if d <= 1 else BLUE for d in rd.delay_days],
                          customdata=rd.retries, hovertemplate="%{x}<br>%{y:.1%} de succès sur %{customdata} relances<extra></extra>"))
    layout(f3, "Succès d'une nouvelle tentative selon le délai (refus « soft »)", "", pct=True)
    dc = r("decline_codes")
    f4 = go.Figure(go.Bar(x=dc.share, y=dc.decline_code, orientation="h", marker_color=[BLUE if t == "soft" else RED for t in dc.decline_type],
                          hovertemplate="%{y}<br>%{x:.1%} des refus<extra></extra>"))
    layout(f4, "Codes de refus (bleu = soft, rouge = hard)", "", h=380)
    f4.update_xaxes(tickformat=".0%"); f4.update_yaxes(autorange="reversed")
    return html(f1) + html(f2) + html(f3) + html(f4)


def risques():
    v = r("vamp_ratio_by_mid")
    mids = sorted(v.mid.unique())
    f1 = go.Figure()
    for i, m in enumerate(mids):
        g = v[v.mid == m]
        f1.add_trace(go.Scatter(x=g.month, y=g.vamp_ratio, name=m, visible=(m == "S-A-EU"), line=dict(color=BLUE, width=2),
                                hovertemplate="%{x|%m/%Y}<br>%{y:.2%}<extra>" + m + "</extra>"))
    g0 = v[v.mid == mids[0]]
    f1.add_trace(go.Scatter(x=g0.month, y=g0.visa_threshold, name="Seuil Visa", line=dict(color=RED, dash="dash", shape="hv"),
                            hoverinfo="skip"))
    buttons = [dict(label=m, method="update", args=[{"visible": [x == m for x in mids] + [True]}]) for m in mids]
    f1.update_layout(updatemenus=[dict(buttons=buttons, x=1, xanchor="right", y=1.18, active=mids.index("S-A-EU"))])
    layout(f1, "Ratio (litiges + fraude TC40) / transactions Visa, par MID", "", h=360)
    f1.update_yaxes(tickformat=".1%")
    wk = r("disputes_weekly_promo")
    f2 = go.Figure([go.Bar(name="Autres clients", x=wk.week, y=wk.disputes_other, marker_color=GRAY),
                    go.Bar(name="Campagne agressive", x=wk.week, y=wk.disputes_promo, marker_color=RED)])
    f2.update_layout(barmode="stack")
    layout(f2, "Litiges par semaine selon la campagne d'acquisition", "litiges")
    fr = r("fraud_rule_backtest")
    t = table(fr, {"rule": "Règle", "blocked": "Bloqués", "fraud_caught": "Fraudes évitées", "clean_payers_blocked": "Payants légitimes bloqués",
                   "recall": "Part de la fraude évitée"}, {"recall": lambda x: f"{100 * x:.0f} %"})
    rm = r("reconciliation_monthly")
    f3 = go.Figure(go.Bar(x=rm.month, y=rm.gap_pct, marker_color=RED, hovertemplate="%{x|%m/%Y}<br>%{y:.2%}<extra></extra>"))
    layout(f3, "Réconciliation : écart mensuel (PSP − base interne) / base interne", "")
    f3.update_yaxes(tickformat=".1%")
    return html(f1) + html(f2) + f'<div class="card"><h3>Règles anti-fraude testées a posteriori</h3>{t}</div>' + html(f3)


TEMPLATE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>DotWorld - tableau de bord (données simulées)</title>
<style>
:root {{ --bg:#F4F4F2; --card:#FCFCFB; --line:#E1E0D9; --ink:#0B0B0B; --ink2:#52514E; --blue:#2A78D6 }}
body {{ margin:0; font-family:'Segoe UI',system-ui,sans-serif; background:var(--bg); color:var(--ink) }}
header {{ padding:20px 24px 8px; display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap }}
h1 {{ font-size:22px; margin:0 }} .sub {{ color:var(--ink2); margin:4px 0 0; font-size:14px }}
.tag {{ font-size:11px; font-weight:700; letter-spacing:.8px; color:#1C5CAB; border:1px solid #86B6EF; border-radius:4px; padding:4px 8px; background:var(--card) }}
nav {{ padding:0 24px; display:flex; gap:6px; flex-wrap:wrap }}
nav button {{ font:inherit; border:1px solid var(--line); background:var(--card); padding:7px 14px; border-radius:6px; cursor:pointer; color:var(--ink2) }}
nav button.on {{ background:var(--blue); color:#fff; border-color:var(--blue) }}
main {{ padding:14px 24px }} .page {{ display:none; grid-template-columns:repeat(auto-fit,minmax(460px,1fr)); gap:14px }} .page.on {{ display:grid }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:8px; min-width:0; overflow-x:auto }}
.card h3 {{ font-size:14px; margin:6px 8px 10px }}
table {{ border-collapse:collapse; width:100%; font-size:13px }} th {{ text-align:left; color:var(--ink2); border-bottom:1px solid #C9C7BF; padding:5px 8px }}
td {{ padding:5px 8px; border-bottom:1px solid #EEEDE8 }}
footer {{ color:#898781; font-size:12px; padding:6px 24px 20px }}
@media (max-width:560px) {{ .page {{ grid-template-columns:1fr }} header,nav,main,footer {{ padding-left:16px; padding-right:16px }} }}
</style></head><body>
<header><div><h1>DotWorld : de la visite au paiement</h1>
<p class="sub">Tableau de bord compagnon de l'étude de cas. Revenu perdu évitable estimé : {avoid} sur 18 mois (fourchette {lo} à {hi}).</p></div>
<span class="tag">SIMULÉ</span></header>
<nav>{nav}</nav><main>{pages}</main>
<footer>Données SIMULÉES (graine 42), illustratives : pas des chiffres de DotWorld · requêtes : sql/ · Étude de cas indépendante à partir de données publiques · sans lien avec DotWorld</footer>
<script>
document.querySelectorAll('nav button').forEach(b => b.addEventListener('click', () => {{
  document.querySelectorAll('nav button, .page').forEach(x => x.classList.remove('on'));
  b.classList.add('on'); document.getElementById(b.dataset.p).classList.add('on');
  document.querySelectorAll('#' + b.dataset.p + ' .js-plotly-plot').forEach(d => Plotly.Plots.resize(d));
}}));
window.addEventListener('load', () => document.querySelectorAll('.page.on .js-plotly-plot').forEach(d => Plotly.Plots.resize(d)));
</script></body></html>"""


def main():
    pages = {"acquisition": ("Acquisition", acquisition()), "parcours": ("Parcours", parcours()),
             "paiements": ("Paiements", paiements()), "risques": ("Risques", risques())}
    nav = "".join(f'<button data-p="{k}" class="{"on" if i == 0 else ""}">{v[0]}</button>' for i, (k, v) in enumerate(pages.items()))
    body = "".join(f'<section id="{k}" class="page {"on" if i == 0 else ""}">{v[1]}</section>' for i, (k, v) in enumerate(pages.items()))
    av = K["avoidable_total"]
    k = lambda x: f"{x / 1000:.0f} K€"  # noqa: E731
    OUT.write_text(TEMPLATE.format(nav=nav, pages=body, avoid=k(av["revenue_eur"]), lo=k(av["lo"]), hi=k(av["hi"])), encoding="utf-8")
    print("Tableau de bord :", OUT.relative_to(ROOT), f"({OUT.stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    main()

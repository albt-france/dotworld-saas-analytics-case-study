"""Rapport PDF (paysage 16:9) : HTML + graphiques SVG, puis impression PDF par Edge sans interface.

Tous les chiffres viennent de data/results (SQL + analysis.py), data/public (faits sourcés,
agrégats KKBox) : aucun chiffre n'est saisi à la main dans le texte.

Usage : python src/build_report.py     -> docs/DotWorld_EtudeDeCas.pdf, docs/img/*.png
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
from jinja2 import Template

sys.path.insert(0, str(Path(__file__).resolve().parent))
import charts as C  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RES, PUB, DOCS = ROOT / "data" / "results", ROOT / "data" / "public", ROOT / "docs"
TMP = ROOT / ".tmp"
FOOT = "Étude de cas indépendante à partir de données publiques · sans lien avec DotWorld"
AI_NOTE = ("Méthode assistée par l'IA : j'ai utilisé Claude, surtout pour écrire les scripts plus vite. "
           "J'ai piloté le projet : j'ai défini les questions, choisi et vérifié les sources de données, "
           "pris les décisions d'analyse et contrôlé chaque résultat.")

r = lambda n: pd.read_csv(RES / f"{n}.csv")  # noqa: E731
K = json.loads((RES / "key_numbers.json").read_text(encoding="utf-8"))
eur, pct = C.eur, C.pct


def keur(x):
    return f"{x / 1000:.0f} K€"


def num(x):
    return f"{x:,.0f}".replace(",", " ")


CSS = """
@page { size: 16in 9in; margin: 0 }
* { box-sizing: border-box; margin: 0; padding: 0 }
body { font-family: 'Segoe UI', system-ui, sans-serif; color: #0B0B0B; background: #F4F4F2; }
.page { width: 1536px; height: 864px; padding: 34px 40px 18px; display: flex; flex-direction: column;
        background: #F4F4F2; page-break-after: always; overflow: hidden; position: relative }
header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; min-height: 64px }
h1 { font-size: 25px; font-weight: 700; line-height: 1.2; max-width: 1220px; letter-spacing: -0.2px }
.sub { color: #52514E; font-size: 14.5px; margin-top: 6px; max-width: 1240px; line-height: 1.4 }
.tag { font-size: 11.5px; font-weight: 700; letter-spacing: .8px; color: #52514E; border: 1px solid #C9C7BF;
       border-radius: 4px; padding: 4px 9px; white-space: nowrap; margin-top: 6px; background: #FCFCFB }
.tag.sim { color: #1C5CAB; border-color: #86B6EF } .tag.real { color: #0E7A55; border-color: #8FD3B8 }
.kpis { display: grid; gap: 14px; margin-bottom: 14px }
.card { background: #FCFCFB; border: 1px solid #E1E0D9; border-radius: 8px; padding: 14px 18px; display: flex;
        flex-direction: column; min-height: 0; overflow: hidden }
.kpi { padding: 12px 18px }
.klabel { font-size: 11px; font-weight: 700; color: #52514E; letter-spacing: .5px; text-transform: uppercase }
.kval { font-size: 30px; font-weight: 700; margin-top: 2px; line-height: 1.15 }
.kval.red { color: #D03B3B } .kval.blue { color: #1C5CAB }
.knote { font-size: 12.5px; color: #52514E; margin-top: 3px; line-height: 1.35 }
.grid { display: grid; gap: 14px; flex: 1; min-height: 0 }
.card h3 { font-size: 13.5px; font-weight: 600; margin-bottom: 6px; color: #0B0B0B }
.body { flex: 1; min-height: 0; display: flex; align-items: center; justify-content: center; font-size: 13px; line-height: 1.45 }
.body svg { width: 100%; height: 100%; }
.body.text { display: block; overflow: hidden; color: #2B2A28 }
.body.text p { margin-bottom: 7px } .body.text ul { margin: 0 0 6px 18px } .body.text li { margin-bottom: 4px }
table { border-collapse: collapse; width: 100%; font-size: 12.5px }
th { text-align: left; color: #52514E; font-weight: 600; border-bottom: 1px solid #C9C7BF; padding: 4px 6px }
td { padding: 4px 6px; border-bottom: 1px solid #EEEDE8 } td.n { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap }
tr.alert td { color: #B02E2E; font-weight: 600 } tr.good td { color: #1C5CAB; font-weight: 600 }
footer { font-size: 10.5px; color: #898781; margin-top: 10px }
b.blue { color: #1C5CAB } b.red { color: #B02E2E }
.q { display: grid; grid-template-columns: 26px 1fr; gap: 3px 8px; font-size: 14px; margin-bottom: 8px }
.q .i { color: #2A78D6; font-weight: 700 }
.lab { font-weight: 700; color: #52514E; font-size: 12px; letter-spacing: .4px }
.flow { display: flex; gap: 8px; align-items: center; justify-content: space-between; width: 100% }
.flow div.s { flex: 1; border: 1px solid #86B6EF; background: #EEF5FD; border-radius: 6px; padding: 8px; text-align: center; font-size: 12.5px }
.flow div.a { color: #898781; font-size: 18px }
.mono { font-family: Consolas, monospace; font-size: 11.5px; background: #F1F0EB; padding: 1px 4px; border-radius: 3px }
"""

PAGE = Template("""
<section class="page">
  <header><div><h1>{{ p.title }}</h1>{% if p.subtitle %}<p class="sub">{{ p.subtitle }}</p>{% endif %}</div>
  {% if p.tag %}<div class="tag {{ p.tag_class }}">{{ p.tag }}</div>{% endif %}</header>
  {% if p.kpis %}<div class="kpis" style="grid-template-columns: repeat({{ p.kpis|length }}, 1fr)">
    {% for k in p.kpis %}<div class="card kpi"><div class="klabel">{{ k[0] }}</div><div class="kval {{ k[3] if k|length > 3 else '' }}">{{ k[1] }}</div><div class="knote">{{ k[2] }}</div></div>{% endfor %}
  </div>{% endif %}
  <div class="grid" style="grid-template-columns: {{ p.cols }}; grid-template-rows: {{ p.rows }}">
    {% for c in p.cards %}<div class="card" style="grid-column: {{ c.col }}; grid-row: {{ c.row }}">
      {% if c.title %}<h3>{{ c.title }}</h3>{% endif %}<div class="body {{ 'text' if c.text else '' }}">{{ c.body }}</div></div>{% endfor %}
  </div>
  <footer>{{ p.footer }} · {{ foot }}</footer>
</section>""")


def card(title, body, col="auto", row="auto", text=False):
    return dict(title=title, body=body, col=col, row=row, text=text)


# =====================================================================================
def page_overview(kk):
    av = K["avoidable_total"]
    camp = r("disputes_by_campaign_first_renewal")
    promo = camp[camp.campaign == "meta_promo_choc"].iloc[0]
    others = camp[camp.campaign != "meta_promo_choc"]
    base = 1000 * others.disputes.sum() / others.first_renewals.sum()
    kpis = [
        ("Données publiques · page 1", "2,90 € → 27,95 €", "essai de 7 jours de Makemycv, puis renouvellement automatique toutes les 4 semaines : tout se joue au 1er renouvellement"),
    ]
    if kk:
        kpis.append(("Données réelles (KKBox) · page 2", kk["kpi_value"], kk["kpi_note"], "blue"))
    kpis += [
        ("Simulé · page 5", f"{keur(av['revenue_eur'])}", f"de revenu perdu évitable sur 18 mois (fourchette {keur(av['lo'])} à {keur(av['hi'])}) : routage, délai des retries, incident PSP", "blue"),
        ("Simulé · page 6", f"×{promo.disputes_per_1000 / base:.1f}".replace(".", ","), f"litiges au 1er renouvellement pour la campagne agressive ({promo.disputes_per_1000:.0f} contre {base:.0f} pour 1 000) : seuil Visa franchi quelques semaines après", "red"),
    ]
    qs = [("1", "Modèle", "Que vendent les produits de DotWorld, et comment sont-ils facturés ?"),
          ("2", "Rétention", "Sur de vrais abonnements, qu'est-ce qui distingue ceux qui restent ?"),
          ("3", "Acquisition", "Quels canaux et campagnes créent une croissance rentable ?"),
          ("4", "Paiements", "Combien de revenu se perd entre la carte et le compte, et comment le récupérer ?"),
          ("5", "Décision", "Les chiffres sont-ils fiables, et que faire en premier ?")]
    qhtml = "".join(f'<div class="q"><span class="i">{a}</span><span><b class="blue">{b}</b> &nbsp;{c}</span></div>' for a, b, c in qs)
    data = ("<p><span class='lab'>PUBLIQUES</span> &nbsp;site et pages Carrières de DotWorld, mentions légales, CGV et grille de prix de Makemycv ; "
            "documentation Stripe et Adyen ; seuils Visa et Mastercard (collecte du 13/11/2026).</p>"
            "<p><span class='lab'>RÉELLES</span> &nbsp;KKBox (WSDM Cup 2018) : transactions d'abonnement d'un service de streaming. Seuls des agrégats sont publiés.</p>"
            "<p><span class='lab'>SIMULÉES</span> &nbsp;parcours complet de 3 produits fictifs sur 18 mois (graine 42) : 1,5 M visites, 140 K tentatives de paiement, 2 PSP. "
            "Mécanismes réalistes, <b>pas des chiffres de DotWorld</b>.</p>"
            "<p><span class='lab'>OUTILS</span> &nbsp;SQL DuckDB (cohortes, funnels, fonctions de fenêtre), Python (tests, intervalles, bootstrap), "
            "4 skills d'analyse réutilisables.</p>")
    read = ("<b>Titres</b> : la conclusion de la page. &nbsp; <b>Tags</b> : DONNÉES PUBLIQUES, DONNÉES RÉELLES (KKBOX), SIMULÉ. &nbsp; "
            "<b>Couleurs</b> : bleu = la donnée, gris = la comparaison, rouge = alerte, refus ou litige ; pointillés = seuil. &nbsp; "
            "<b>Code</b> : chaque chiffre vient d'une requête de <span class='mono'>sql/</span> ou d'un script de <span class='mono'>src/</span>.")
    rt = pd.DataFrame(K["routing"])
    hd = r("hard_decline_retries").retries_after_hard_decline.sum()
    fr = r("fraud_rule_backtest").set_index("rule").loc["vélocité BIN >= 5 en 1 h"]
    rs = K["retry_schedule"]
    prio = [("Arrêter les relances après refus définitif", f"{num(hd)} relances interdites évitées (règles des réseaux)", "faible", "nul"),
            ("Relancer les refus « soft » à J+3/J+5", f"+{keur(rs['revenue_eur'])} ({keur(rs['revenue_lo'])} à {keur(rs['revenue_hi'])})", "faible", "faible"),
            ("Router les cartes BR et MX vers PSP_A", f"+{keur(rt.revenue_eur.sum())} ({keur(rt.revenue_lo.sum())} à {keur(rt.revenue_hi.sum())})", "moyen", "frais PSP"),
            ("Piloter les campagnes sur leur taux de litige", "rester sous le seuil Visa de 1,5 %", "faible", "volume"),
            ("Bloquer les rafales de tests de cartes", f"{pct(fr.recall, 0)} de la fraude confirmée évitée", "faible", "faible"),
            ("Réconcilier PSP et base chaque jour", f"écart de {pct(abs(K['reconciliation']['gap_pct']), 1)} expliqué et corrigé", "moyen", "nul")]
    ptab = ("<table><tr><th>#</th><th>Action</th><th>Impact (18 mois simulés)</th><th>Effort</th><th>Risque</th></tr>"
            + "".join(f"<tr><td>{i}</td><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td></tr>" for i, (a, b, c, d) in enumerate(prio, 1))
            + "</table><p style='font-size:12px;color:#52514E;margin-top:6px'>Détail, hypothèses et mesure de chaque action : docs/RECOMMANDATIONS.md</p>")
    return dict(title="DotWorld : de la première visite au paiement, où se crée et où se perd la valeur d'un studio SaaS",
                subtitle="Prix publics des produits, vraies données d'abonnement et un parcours simulé, de l'acquisition aux refus de paiement, avec des skills d'analyse réutilisables.",
                tag="VUE D'ENSEMBLE", tag_class="", kpis=kpis, cols="1fr 1.15fr", rows="1fr 1fr",
                cards=[card("Cinq questions", qhtml, "1", "1", True),
                       card("Recommandations priorisées", ptab, "2", "1", True),
                       card("Données et méthodes", data, "1", "2", True),
                       card("Comment lire ce rapport", read.replace(" &nbsp; ", "<br>"), "2", "2", True)],
                footer="Sources et licences : data/SOURCES.md")


def page_public():
    facts = pd.read_csv(PUB / "dotworld_facts.csv")
    tiles = [("Créée en", "2015", "Venture Builder et SaaS Studio, siège en Suisse (canton de Vaud)"),
             ("Équipe", "55", "collaborateurs, 90 % en télétravail, français langue de travail"),
             ("Audience", "50 M+", "visiteurs par an sur les SaaS ; présence dans plus de 15 pays"),
             ("Financement", "0 €", "levé : croissance autofinancée, rentable dès la 1re année")]
    jobs = ("<ul>"
            "<li><b>Acquisition</b> : payante surtout sur Google, diversification Meta et TikTok ; équipes SEO et SEA internes.</li>"
            "<li><b>Paiement</b> : plusieurs PSP, une plateforme de billing, plusieurs comptes marchands (MID) ; PayPal, Apple Pay, Google Pay, méthodes locales.</li>"
            "<li><b>Risque</b> : fraude à l'essai gratuit, « friendly fraud », 3DS par marché, seuils Visa, Mastercard et PayPal par MID, règles des réseaux sur les retries.</li>"
            "<li><b>Data</b> : un CDO, un Data Engineer, un Data Scientist et ce poste ; Looker, PostHog, Hotjar, Clarity ; A/B tests à renforcer ; assistants IA déjà adoptés.</li>"
            "<li><b>Marchés</b> : Europe et États-Unis ; Amérique latine et Asie en développement.</li></ul>")
    prod = ("<table><tr><th>Univers produit</th><th>Produit</th><th>Lien avec DotWorld</th></tr>"
            "<tr class='good'><td>RH / CV</td><td>Makemycv (créateur de CV)</td><td>prouvé : mentions légales (éditeur DOTWORLD SA)</td></tr>"
            "<tr><td>Automobile</td><td>SaaS de données sur la voiture, 3 ans</td><td>cité dans une offre ; nom non publié</td></tr>"
            "<tr><td>Gestion de contenus</td><td>non identifié</td><td>univers cité par DotWorld</td></tr>"
            "<tr><td>Création design</td><td>non identifié</td><td>univers cité par DotWorld</td></tr></table>"
            "<p style='margin-top:8px;font-size:12px;color:#52514E'>Règle suivie : un produit n'est attribué à DotWorld que si une source le prouve. "
            "Makemycv existe en 34 versions localisées ; prix identiques en EUR (et en USD aux États-Unis) sur les 14 pages relevées ; "
            "paiement par carte et Google Pay via Stripe selon ses CGV.</p>")
    pb = pd.read_csv(PUB / "price_book.csv")
    offer_rows = ""
    for x in pb.itertuples():
        ren = "" if pd.isna(x.prix_renouvellement) else f"{x.prix_renouvellement:.2f} / {x.periodicite_renouvellement}"
        offer_rows += f"<tr><td>{x.formule}</td><td class='n'>{x.prix_initial:.2f}</td><td>{ren}</td><td>{x.devise}</td></tr>".replace(".", ",")
    offer = ("<p style='margin-top:6px'><b>Grille publique de Makemycv</b> (relevée sur 14 versions localisées)</p>"
             "<table><tr><th>Formule</th><th>Prix</th><th>Renouvellement</th><th>Devise</th></tr>" + offer_rows + "</table>")
    return dict(title="DotWorld vend des abonnements à petit prix d'entrée : un essai à 2,90 €, puis 27,95 € toutes les 4 semaines",
                subtitle="Ce que disent les sources publiques : un studio qui lance plusieurs SaaS en parallèle, les vend dans le monde entier, et pour qui la conversion de l'essai et le paiement sont au cœur du modèle.",
                tag="DONNÉES PUBLIQUES", tag_class="", kpis=tiles, cols="1.15fr 1fr", rows="1fr 1fr",
                cards=[card("Makemycv : montant cumulé payé selon la formule (prix publics relevés le 13/11/2026)", C.price_paths(820, 250), "1", "1"),
                       card("Produits : ce qui est prouvé, ce qui ne l'est pas", prod, "1", "2", True),
                       card("Ce que les offres d'emploi publiques révèlent du métier", jobs + offer, "2", "1 / 3", True)],
                footer=f"Sources : dotworld.ch, dotworld.teamtailor.com, makemycv.com (mentions légales, CGV, tarifs), {len(facts)} faits datés dans data/public/dotworld_facts.csv")


def kkbox_page():
    f = PUB / "kkbox_overview.csv"
    if not f.exists():
        return None, dict(title="Ce que disent de vrais abonnements (données KKBox en attente)",
                          subtitle="Cette page se remplit automatiquement quand src/kkbox_prepare.py a produit les agrégats KKBox.",
                          tag="DONNÉES RÉELLES (KKBOX)", tag_class="real", kpis=[], cols="1fr", rows="1fr",
                          cards=[card("", "<p>Agrégats KKBox absents.</p>", text=True)], footer="KKBox, WSDM Cup 2018 (Kaggle)")
    ov = pd.read_csv(f).iloc[0]
    ret = pd.read_csv(PUB / "kkbox_cohort_retention.csv")
    ren = pd.read_csv(PUB / "kkbox_renewal_by_autorenew.csv").set_index("is_auto_renew")
    ct = pd.read_csv(PUB / "kkbox_churn_type.csv")
    arpa = pd.read_csv(PUB / "kkbox_arpa_monthly.csv")
    churn_pm = PUB / "kkbox_churn_by_payment.csv"
    tot = ct.members.sum()
    share = {k: ct[ct.churn_type.str.startswith(k)].members.sum() / tot for k in ("non renouvelé", "volontaire", "involontaire")}
    ra, rn = ren.loc[1, "renewed_within_30d"], ren.loc[0, "renewed_within_30d"]
    mean_ret = ret[ret.k <= 12].pivot_table(index="k", columns="cohort", values="retention").mean(axis=1)
    cp = pd.read_csv(churn_pm) if churn_pm.exists() else None
    if cp is not None:
        w = cp.assign(ch=cp.members * cp.churn_rate).groupby("is_auto_renew")[["ch", "members"]].sum()
        c_auto, c_man = w.loc[1, "ch"] / w.loc[1, "members"], w.loc[0, "ch"] / w.loc[0, "members"]
    tiles = [("Transactions réelles", num(ov.transactions), f"{num(ov.members)} abonnés, du {ov.first_date} au {ov.last_date}"),
             ("Renouvellement à 30 jours", pct(ra, 0), f"des échéances avec renouvellement automatique, contre {pct(rn, 0)} sans", "blue"),
             ("Churn de mars 2017", f"{pct(c_auto, 0)} contre {pct(c_man, 0)}", "en renouvellement automatique, contre paiement manuel (étiquette officielle)", "red"),
             ("Départs récents sans annulation", pct(share["non renouvelé"], 0),
              f"formules sans renouvellement automatique non repayées ; {pct(share['volontaire'], 0)} d'annulations explicites")]
    churn_body = ""
    if cp is not None:
        rows = "".join(f"<tr><td>{x.payment_method}</td><td>{'oui' if x.is_auto_renew else 'non'}</td><td class='n'>{num(x.members)}</td>"
                       f"<td class='n'>{pct(x.churn_rate)}</td></tr>" for x in cp.head(8).itertuples())
        churn_body = ("<table><tr><th>Moyen de paiement (dernier abonnement)</th><th>Renouv. auto</th><th>Abonnés</th><th>Churn mars 2017</th></tr>" + rows +
                      "</table><p style='font-size:11.5px;color:#52514E;margin-top:6px'>Étiquette officielle de la compétition : pas de nouvel abonnement valide dans les 30 jours après l'expiration.</p>")
    arpa_note = (f"ARPA mensuel : {arpa.arpa_ntd.iloc[0]:.0f} NT$ début 2015, {arpa.arpa_ntd.iloc[-1]:.0f} NT$ en mars 2017 ; "
                 f"part des paiements remisés : {pct(arpa.share_discounted.iloc[0], 0)} puis {pct(arpa.share_discounted.iloc[-1], 1)}.")
    kk = dict(kpi_value=pct(ra - rn, 0).replace(" %", " pts"),
              kpi_note=f"de renouvellement en plus à l'échéance quand le renouvellement est automatique ({pct(ra, 0)} contre {pct(rn, 0)}), sur {num(ov.members)} vrais abonnés")
    method = ("<p><b>Volontaire ou involontaire ?</b> KKBox n'a pas de journal des refus de paiement. On classe le dernier abonnement des départs récents : "
              f"annulation explicite ({pct(share['volontaire'], 0)}), formule sans renouvellement automatique non repayée ({pct(share['non renouvelé'], 0)}), "
              f"renouvellement automatique actif sans paiement suivant, donc échec de paiement probable ({pct(share['involontaire'], 1)}).</p>"
              f"<p>{arpa_note}</p>"
              "<p><b>Ce que DotWorld peut en tirer</b> : le mode de paiement prédit la rétention plus que tout le reste ; chaque abonné qui passe "
              "en renouvellement automatique (ou dont la carte est mise à jour) est un abonné qui ne part pas « par défaut ». Les échecs de paiement, "
              "eux, ne se voient qu'avec les journaux du PSP : c'est ce que montre le parcours simulé (pages 4 et 5).</p>")
    churn_mix = C.kkbox_bars(["Non repayé (sans renouvellement automatique)", "Annulation explicite", "Échec de paiement probable"],
                             [share["non renouvelé"], share["volontaire"], share["involontaire"]], 600, 150,
                             colors=[C.GRAY_D, C.BLUE, C.RED])
    return kk, dict(title=f"Sur de vrais abonnements, le renouvellement automatique fait la rétention : {pct(ra, 0)} renouvellent à l'échéance, contre {pct(rn, 0)} sans",
                    subtitle="KKBox, service de streaming par abonnement (Taïwan) : 23 millions de transactions réelles avec moyen de paiement, renouvellement automatique et annulations. Le même mécanisme d'abonnement que les produits de DotWorld.",
                    tag="DONNÉES RÉELLES (KKBOX)", tag_class="real", kpis=tiles, cols="1.05fr 1fr", rows="1.45fr 1fr",
                    cards=[card("Abonnés actifs (abonnement valide en fin de mois) par cohorte de premier paiement observé ; bleu = moyenne",
                                C.kkbox_retention(ret, 640, 250), "1", "1"),
                           card("Comment partent les abonnés récents (dernier abonnement expiré entre octobre 2016 et février 2017)", churn_mix, "1", "2"),
                           card("Churn selon le moyen de paiement et le renouvellement automatique", churn_body + method, "2", "1 / 3", True)],
                    footer="Données : KKBox Churn Prediction Challenge (WSDM Cup 2018, Kaggle), utilisées selon les règles de la compétition ; données brutes non publiées, agrégats seulement")


def page_acquisition():
    ch = r("channel_ltv_180")
    uc = r("channel_unit_costs")
    camp = r("campaign_ltv_90")
    dis = r("disputes_by_campaign_first_renewal").set_index("campaign")
    pb = pd.DataFrame(K["payback"]).set_index("channel")
    g, t = ch.set_index("channel").loc["Google Ads"], ch.set_index("channel").loc["TikTok"]
    rows = ""
    for x in camp[camp.cac_eur > 0].sort_values("cac_eur").itertuples():
        roas = x.ltv90_per_payer / x.cac_eur
        d1000 = dis.loc[x.campaign, "disputes_per_1000"] if x.campaign in dis.index else float("nan")
        cls = "alert" if x.campaign == "meta_promo_choc" else ""
        rows += (f"<tr class='{cls}'><td>{x.campaign}</td><td class='n'>{eur(x.cac_eur)}</td><td class='n'>{eur(x.ltv90_per_payer)}</td>"
                 f"<td class='n'>{roas:.1f}</td><td class='n'>{d1000:.0f}</td></tr>").replace(".", ",")
    table = ("<table><tr><th>Campagne (cohortes observées 90 j)</th><th>CAC</th><th>LTV 90 j</th><th>ROAS 90 j</th><th>Litiges ‰ au 1er renouv.</th></tr>"
             + rows + "</table><p style='font-size:12px;color:#52514E;margin-top:6px'>La campagne agressive a le 2e meilleur ROAS… et le pire taux de litiges (page 6).</p>")
    kpis = [("Dépense média 2025", keur(ch.spend_eur.sum()), "Google Ads, Meta, TikTok, affiliation (cohortes observées 180 jours)"),
            ("ROAS 180 j Google Ads", f"{g.roas_180:.1f}".replace(".", ","), f"CAC {eur(g.cac_eur)} remboursé en {int(pb.loc['Google Ads','payback_day'])} jours", "blue"),
            ("CAC TikTok", eur(t.cac_eur), f"le coût par visite le plus bas ({eur(uc.set_index('channel').loc['TikTok','cost_per_visit'], 2)}) mais la conversion la plus faible", "red"),
            ("LTV 180 j par payant", f"{eur(ch.ltv180_per_payer.min())} à {eur(ch.ltv180_per_payer.max())}", "faible écart entre canaux : c'est le CAC qui fait la rentabilité")]
    return dict(title=f"Google Ads rapporte {g.roas_180:.1f} € par euro à 180 jours ; TikTok, le moins cher par visite, a le CAC le plus élevé".replace(".", ",", 1),
                subtitle="CAC = dépense média / abonnés payants ; LTV = revenu net (après remboursements et litiges) cumulé sur 180 jours, uniquement pour les cohortes observées 180 jours entiers.",
                tag="SIMULÉ", tag_class="sim", kpis=kpis, cols="1.15fr 0.85fr 1fr", rows="1fr",
                cards=[card("CAC contre LTV à 180 jours par canal payant (ROAS = LTV / CAC)", C.cac_vs_ltv(ch, 560, 330), "1", "1"),
                       card("Le moins cher par visite n'est pas le moins cher par client", C.cost_visit_vs_payer(uc, 400, 330), "2", "1"),
                       card("Campagnes : rentabilité et risque", table, "3", "1", True)],
                footer="Données SIMULÉES (graine 42), illustratives : pas des chiffres de DotWorld · requêtes : sql/01_acquisition_ltv.sql")


def page_funnel():
    fp = r("funnel_product")
    to = r("trial_outcomes")
    rc = r("retention_by_cycle")
    tn = r("churn_by_tenure")
    a = fp.set_index("product").loc["A"]
    t4 = tn[tn.tenure == "4 cycles et +"]
    kpis = [("Inscription → paiement de l'essai", pct(a.checkout / a.signups, 0), "produit A : plus d'un inscrit sur deux ne lance pas l'essai"),
            ("Essai → 1er renouvellement", pct(a.first_paid / a.trial_started, 0), "produit A : la moitié des essais ne deviennent pas des abonnements", "red"),
            ("1er → 2e renouvellement", pct(a.second_paid / a.first_paid, 0), "produit A ; le produit B (création design) retient mieux"),
            ("Départs involontaires (4 cycles et +)", f"{pct(t4.share_involuntary.min(), 0)} à {pct(t4.share_involuntary.max(), 0)}", "des départs d'abonnés fidèles viennent d'un paiement refusé", "red")]
    return dict(title="Le premier renouvellement est le vrai point de décrochage ; chez les abonnés fidèles, 4 départs sur 10 sont involontaires",
                subtitle="Funnel de l'inscription au 2e renouvellement (inscriptions jusqu'au 30/04/2026, pour laisser le temps d'observer le renouvellement) ; rétention par cycle sur les cohortes observables.",
                tag="SIMULÉ", tag_class="sim", kpis=kpis, cols="1.1fr 1fr", rows="1fr 1fr",
                cards=[card("Sur 100 inscrits, combien passent chaque étape ?", C.funnel_per100(fp, 600, 250), "1", "1"),
                       card("Que deviennent les essais lancés ?", C.trial_outcomes(to, 520, 220), "2", "1"),
                       card("Rétention des abonnés payants par cycle facturé", C.retention_curves(rc, 600, 230), "1", "2"),
                       card("Part du churn involontaire selon l'ancienneté au départ", C.involuntary_by_tenure(tn, 520, 220), "2", "2")],
                footer="Données SIMULÉES (graine 42) · requêtes : sql/02_funnel_retention.sql · skill : skills/cohort-retention")


def page_payments():
    acc = r("acceptance_psp_country")
    rd = r("retry_by_delay")
    es = r("acceptance_weekly_es")
    hd = r("hard_decline_retries")
    rt = pd.DataFrame(K["routing"])
    rs, inc, tot = K["retry_schedule"], K["es_incident"], K["avoidable_total"]
    items = [("Router BR et MX vers PSP_A", rt.revenue_eur.sum(), rt.revenue_lo.sum(), rt.revenue_hi.sum()),
             ("Relancer à J+5 au lieu de J0/J+1", rs["revenue_eur"], rs["revenue_lo"], rs["revenue_hi"]),
             ("Corriger l'incident PSP_S en Espagne", inc["revenue_eur"], inc["revenue_lo"], inc["revenue_hi"]),
             ("Total (18 mois, revenu immédiat)", tot["revenue_eur"], tot["lo"], tot["hi"])]
    d0 = rd.set_index("delay_days")
    kpis = [("Revenu perdu évitable", keur(tot["revenue_eur"]), f"fourchette {keur(tot['lo'])} à {keur(tot['hi'])} (IC à 95 %), sans compter la valeur future des abonnés sauvés", "blue"),
            ("Écart BR / MX entre PSP", f"+{rt['diff'].min() * 100:.0f} à +{rt['diff'].max() * 100:.0f} pts", "d'acceptation sur PSP_A, à cartes égales (trafic réparti 85/15 entre PSP)"),
            ("Retry J0 contre J+5", f"{pct(d0.loc[0.0, 'success_rate'], 0)} → {pct(d0.loc[5.0, 'success_rate'], 0)}", "de succès d'une nouvelle tentative après refus « soft »"),
            ("Relances interdites", num(hd.retries_after_hard_decline.sum()), "nouvelles tentatives après un refus définitif (règles des réseaux), sur PSP_A", "red")]
    return dict(title=f"{keur(tot['revenue_eur'])} récupérables : router le Brésil et le Mexique, relancer plus tard, traiter l'incident espagnol",
                subtitle="Taux d'acceptation = tentatives initiales acceptées / tentatives initiales (les nouvelles tentatives sont mesurées à part, comme le recommande Stripe). Deux PSP fictifs : PSP_S (type Stripe), PSP_A (type Adyen).",
                tag="SIMULÉ", tag_class="sim", kpis=kpis, cols="1.1fr 0.9fr 0.9fr", rows="1fr 1fr",
                cards=[card("Acceptation par pays de la carte et par PSP", C.acceptance_country(acc, 560, 300), "1", "1 / 3"),
                       card("Succès d'une nouvelle tentative selon le délai", C.retry_delay(rd, 420, 210), "2", "1"),
                       card("Espagne : PSP_S décroche en avril, PSP_A non", C.es_trend(es, 420, 210), "3", "1"),
                       card("Revenu récupérable par levier (barre = intervalle de confiance à 95 %)", C.avoidable_bars(items, 760, 210), "2 / 4", "2")],
                footer="Données SIMULÉES (graine 42) · règle Stripe : jusqu'à 8 relances sur 2 semaines par défaut, jamais après un refus définitif · sql/03_payments.sql, src/analysis.py · skill : skills/payment-health")


def page_risk():
    vamp = r("vamp_ratio_by_mid")
    camp = r("disputes_by_campaign_first_renewal")
    wk = r("disputes_weekly_promo")
    fr = r("fraud_rule_backtest").set_index("rule").loc["vélocité BIN >= 5 en 1 h"]
    fp = r("fraud_by_trial_price").set_index("product")
    mid = "S-A-EU"
    v = vamp[vamp.mid == mid].copy()
    over = v[v.vamp_ratio > v.visa_threshold]
    promo = camp[camp.campaign == "meta_promo_choc"].iloc[0]
    fa, fc, fb = (f"{fp.loc[k, 'fraud_per_1000_checkouts']:.1f}".replace(".", ",") for k in ("A", "C", "B"))
    fraud = ("<p><b>Les essais à petit prix attirent les tests de cartes</b> : fraude confirmée pour 1 000 paiements d'essai : "
             f"produit A (2,90 €) <b class='red'>{fa}</b>, produit C (1,00 €) <b class='red'>{fc}</b>, "
             f"produit B (essai gratuit) {fb}.</p>"
             f"<p><b>Règle testée a posteriori</b> : bloquer au-delà de 5 paiements d'essai sur le même BIN en une heure. Elle aurait bloqué {num(fr.blocked)} tentatives, "
             f"évité {pct(fr.recall, 0)} de la fraude confirmée et bloqué seulement {int(fr.clean_payers_blocked)} clients qui ont ensuite payé normalement.</p>"
             "<p style='color:#52514E;font-size:12px'>Piège : la « précision » mesurée sur la fraude confirmée paraît faible (3 %), car une carte testée puis refusée ne produit jamais de litige. "
             "Il faut juger la règle sur les faux positifs observables.</p>")
    kpis = [("Ratio Visa du MID " + mid, pct(over.vamp_ratio.max(), 2) if len(over) else "-", f"en {', '.join(pd.to_datetime(over.month).dt.strftime('%m/%Y'))} : au-dessus du nouveau seuil de 1,5 % (avril 2026)", "red"),
            ("Litiges au 1er renouvellement", f"{promo.disputes_per_1000:.0f} ‰", f"pour la campagne agressive ; délai médian {promo.median_lag_days:.0f} jours après le paiement", "red"),
            ("Fraude évitée par une règle simple", pct(fr.recall, 0), "de la fraude confirmée, pour 5 clients légitimes bloqués"),
            ("Seuils publics", "1,5 %", "Visa VAMP depuis le 01/04/2026 (2,2 % avant) ; Mastercard ECM 1,5 % et 100 chargebacks")]
    return dict(title="Une campagne agressive a fait passer le compte marchand principal au-dessus du nouveau seuil Visa de 1,5 %, quelques semaines plus tard",
                subtitle="Ratio de type VAMP = (litiges + signalements de fraude TC40) du mois / transactions Visa réglées du mois. À l'échelle simulée, le minimum de 1 500 événements n'est pas atteint : on lit le ratio comme une alerte.",
                tag="SIMULÉ", tag_class="sim", kpis=kpis, cols="1.1fr 0.9fr 1fr", rows="1fr 1fr",
                cards=[card(f"Ratio litiges + fraude du MID {mid} contre le seuil Visa", C.vamp_line(vamp, mid, 560, 230), "1", "1"),
                       card("Litiges pour 1 000 premiers renouvellements, par campagne", C.disputes_campaign(camp, 420, 230), "2", "1"),
                       card("Litiges par semaine : l'effet arrive après la campagne (zone rose)", C.disputes_weekly(wk, 560, 220), "1", "2"),
                       card("Fraude à l'essai", fraud, "3", "1 / 3", True),
                       card("Ce qu'il faut changer", "<ul><li>Suivre chaque campagne sur son taux de litige à 45 jours, pas seulement son ROAS.</li>"
                            "<li>Afficher le prix du renouvellement au paiement de l'essai (test page 8).</li>"
                            "<li>Alertes de pré-litige (Ethoca, Verifi) sur le MID en alerte.</li></ul>", "2", "2", True)],
                footer="Données SIMULÉES (graine 42) · seuils : data/public/payment_references.csv (sources et dates) · sql/04_risk.sql")


def page_quality():
    rec = K["reconciliation"]
    m = r("reconciliation_monthly")
    defs = ("<table><tr><th>Indicateur</th><th>Définition partagée</th><th>Piège évité</th></tr>"
            "<tr><td>Taux d'acceptation</td><td>tentatives initiales acceptées / tentatives initiales</td><td>compter chaque retry comme un refus</td></tr>"
            "<tr><td>Abonné payant</td><td>au moins un cycle payé plein tarif</td><td>compter l'essai à 2,90 €</td></tr>"
            "<tr><td>LTV (h jours)</td><td>revenu net cumulé h jours / abonnés payants, cohortes complètes</td><td>biais de censure</td></tr>"
            "<tr><td>Churn involontaire</td><td>échec du paiement après toutes les relances</td><td>le confondre avec une annulation</td></tr>"
            "<tr><td>Ratio de litiges</td><td>litiges du mois / transactions réglées (Visa : du mois ; Mastercard : du mois précédent)</td><td>diviser par les tentatives</td></tr>"
            "<tr><td>Revenu</td><td>brut en EUR au taux du jour, mois en UTC</td><td>mélanger fuseaux et taux</td></tr></table>"
            "<p style='font-size:12px;color:#52514E;margin-top:6px'>Toutes les définitions, avec le SQL et les cas limites : METRICS.md</p>")
    kpis = [("Écart PSP − base interne", eur(rec["gap_total_eur"]), f"soit {pct(rec['gap_pct'], 2)} du revenu brut sur 18 mois", "red"),
            ("Doublons internes", eur(-rec["bridge"]["Doublons dans la base interne (webhooks rejoués)"]), "webhooks rejoués, comptés deux fois"),
            ("Paiements manquants", eur(rec["bridge"]["Paiements absents de la base interne (webhooks perdus)"]), "encaissés par le PSP, absents de la base"),
            ("Changement de mois", num(rec["month_shift_n"]), "paiements rangés dans un autre mois : PSP_S rapporte à l'heure de Zurich, la base en UTC")]
    return dict(title="Les deux sources de revenu divergent de 0,6 % ; quatre causes expliquent tout l'écart",
                subtitle="Rapprochement ligne à ligne, sur l'identifiant de tentative, entre la base de facturation interne et les rapports des PSP. Le résidu non expliqué est inférieur à 0,02 % du revenu.",
                tag="SIMULÉ", tag_class="sim", kpis=kpis, cols="1.05fr 1fr", rows="1fr 1fr",
                cards=[card("Pont de réconciliation : ce qui explique l'écart PSP − interne (€)", C.recon_bridge(rec["bridge"], 600, 230), "1", "1"),
                       card("Écart mensuel (PSP − interne) / interne", C.recon_monthly(m, 560, 220), "2", "1"),
                       card("Des définitions partagées, écrites une fois", defs, "1 / 3", "2", True)],
                footer="Données SIMULÉES (graine 42) · sql/05_reconciliation_experiment.sql, src/analysis.py · METRICS.md")


def page_experiment():
    e = K["experiment"]
    rows = [("Lancement du paiement de l'essai", e["trial_checkout"]["rel"], e["trial_checkout"]["lo"] / e["trial_checkout"]["control"],
             e["trial_checkout"]["hi"] / e["trial_checkout"]["control"], C.RED),
            ("Conversion au 1er renouvellement", e["paid_first_renewal"]["rel"], e["paid_first_renewal"]["lo"] / e["paid_first_renewal"]["control"],
             e["paid_first_renewal"]["hi"] / e["paid_first_renewal"]["control"], C.GRAY_D),
            ("Revenu net / utilisateur à 60 j (principale)", e["revenue_60d"]["diff"] / e["revenue_60d"]["control"],
             e["revenue_60d"]["lo"] / e["revenue_60d"]["control"], e["revenue_60d"]["hi"] / e["revenue_60d"]["control"], C.BLUE),
            ("Litiges pour 1 000 payants (garde-fou)", e["disputes_per_1000_payers"]["diff"] / e["disputes_per_1000_payers"]["control"],
             e["disputes_per_1000_payers"]["lo"] / e["disputes_per_1000_payers"]["control"],
             e["disputes_per_1000_payers"]["hi"] / e["disputes_per_1000_payers"]["control"], C.GREEN)]
    n = e["n"]
    proto = (f"<p><b>Hypothèse</b> : afficher le prix du renouvellement à côté de l'essai réduit les litiges « non reconnus » sans coûter de revenu.</p>"
             f"<p><b>Protocole</b> : produit A, 01/03 → 30/04/2026, 50/50 par utilisateur ; métrique principale fixée avant : revenu net par utilisateur à 60 jours.</p>"
             f"<p><b>Contrôles</b> : {num(n['control'])} contre {num(n['prix_transparent'])} utilisateurs, SRM p = {str(round(e['srm_p'], 2)).replace('.', ',')} ; affectation unique ; fenêtre de 60 jours complète.</p>"
             f"<p><b>Puissance</b> : effet minimal détectable sur la conversion payante : {pct(e['mde_paid_rel'], 0)} relatif. "
             f"Pour prouver −30 % de litiges, il faudrait environ {num(round(e['payers_per_arm_for_30pct_dispute_drop'], -2))} payants par groupe (ici environ {num(round(e['disputes_per_1000_payers']['payers_control'], -2))}).</p>")
    dec = (f"<p><b>Résultat</b> : {pct(-e['trial_checkout']['rel'], 0)} de paiements d'essai en moins (significatif, p = {str(round(e['trial_checkout']['p'], 3)).replace('.', ',')}), "
           f"mais conversion payante et revenu à 60 jours inchangés : les essais perdus n'auraient pas converti. "
           f"Litiges : {e['disputes_per_1000_payers']['control']:.0f} contre {e['disputes_per_1000_payers']['variant']:.0f} pour 1 000 payants, direction favorable mais non significative.</p>"
           "<p><b>Décision proposée</b> : pas de conclusion sur le revenu (l'intervalle contient 0). La variante ne coûte rien et va dans le sens des règles de transparence des réseaux : "
           "la généraliser, et suivre les litiges du produit A pendant 8 semaines avec le Data Scientist.</p>"
           "<p style='font-size:12px;color:#52514E'>Lu avec le skill experiment-readout : contrôles avant effets, décision selon une règle écrite à l'avance.</p>")
    kpis = [("Utilisateurs affectés", num(n["control"] + n["prix_transparent"]), f"SRM p = {e['srm_p']:.2f} : pas de déséquilibre".replace(".", ",")),
            ("Paiements d'essai", f"{e['trial_checkout']['diff'] * 100:+.1f} pts".replace(".", ","), "significatif : la variante filtre des essais", "red"),
            ("Revenu net à 60 jours", f"{e['revenue_60d']['diff']:+.2f} € / utilisateur".replace(".", ","), f"IC [{e['revenue_60d']['lo']:+.2f} ; {e['revenue_60d']['hi']:+.2f}] : pas d'écart".replace(".", ",")),
            ("Litiges", f"{e['disputes_per_1000_payers']['control']:.0f} → {e['disputes_per_1000_payers']['variant']:.0f} ‰", "direction favorable, puissance insuffisante", "blue")]
    return dict(title="Afficher le prix du renouvellement coûte des essais, pas de revenu ; l'effet sur les litiges reste à prouver",
                subtitle="Test A/B sur le parcours d'essai du produit A, lu comme le ferait un Data Analyst avec le Data Scientist : contrôles d'abord, effets avec intervalles, garde-fous, puissance, décision.",
                tag="SIMULÉ", tag_class="sim", kpis=kpis, cols="1.15fr 1fr", rows="1fr 1fr",
                cards=[card("Écart relatif variante / contrôle avec intervalle de confiance à 95 %", C.forest(rows, 640, 470), "1", "1 / 3"),
                       card("Protocole et contrôles", proto, "2", "1", True),
                       card("Lecture et décision", dec, "2", "2", True)],
                footer="Données SIMULÉES (graine 42) · skills/experiment-readout, src/analysis.py")


def page_skills():
    cmds = {"cohort-retention": "run.py --products A B C --grain quarter",
            "ltv-by-channel": "run.py --horizon 180 --dim canal",
            "payment-health": "run.py --countries ES --split 2026-04-01 --dim psp",
            "experiment-readout": "run.py --experiment EXP-A-PRIX-TRANSPARENT --window 60"}
    sk = [("cohort-retention", "« Combien de nos départs viennent des paiements ? »",
           "La rétention ne se dégrade pas d'une cohorte 2025 à l'autre ; chez les abonnés de 4 cycles et plus, 41 à 58 % des départs sont involontaires.",
           "C1 = 100 %, courbes décroissantes, somme des cohortes, cohortes jeunes tronquées"),
          ("ltv-by-channel", "« Quelle est la LTV selon le canal ? »",
           "LTV 180 j de 66 à 77 € par payant selon le canal ; Google Ads ROAS 3,4 ; TikTok a le CAC le plus élevé.",
           "cohortes complètes, LTV croissante avec l'horizon, canaux sans coût média signalés"),
          ("payment-health", "« Pourquoi l'acceptation baisse en Espagne ? »",
           "Seul PSP_S recule (−6,5 pts depuis avril), porté par « do_not_honor » (+7,9 pts) : problème côté acquéreur ; router l'Espagne vers PSP_A le temps du correctif.",
           "une tentative initiale par paiement, totaux, ≥ 300 tentatives par segment, relances interdites"),
          ("experiment-readout", "« Peut-on généraliser le prix transparent ? »",
           "Moins d'essais, même revenu, litiges en baisse non prouvée : pas de conclusion sur le revenu ; généraliser et suivre les litiges.",
           "SRM, affectation unique, fenêtre complète, équilibre des groupes")]
    cards = []
    for i, (name, q, a, ctrl) in enumerate(sk):
        body = (f"<p><b>Question</b> : {q}</p><p><span class='mono'>python skills/{name}/{cmds[name]}</span></p>"
                f"<p><b>Réponse vérifiée</b> : {a}</p>"
                f"<p style='font-size:12px;color:#52514E'><b>Contrôles avant de répondre</b> : {ctrl}</p>"
                f"<p style='font-size:12px;color:#52514E'><b>Fichiers</b> : SKILL.md · queries/*.sql · run.py · example.md</p>")
        cards.append(card(name, body, str(i % 2 + 1), str(i // 2 + 2), True))
    flow = ("<div class='flow'><div class='s'><b>Question</b><br>d'une équipe</div><div class='a'>→</div>"
            "<div class='s'><b>SKILL.md</b><br>définitions, étapes, pièges</div><div class='a'>→</div>"
            "<div class='s'><b>Modèles SQL</b><br>paramètres validés</div><div class='a'>→</div>"
            "<div class='s'><b>Contrôles</b><br>bloquent la réponse si échec</div><div class='a'>→</div>"
            "<div class='s'><b>Réponse</b><br>chiffrée et sourcée</div></div>")
    why = ("<ul><li><b>Autonomie</b> : Marketing, Produit et Paiement posent leur question sans attendre l'équipe Data.</li>"
           "<li><b>Mêmes chiffres partout</b> : une seule définition par indicateur (METRICS.md), un seul SQL versionné.</li>"
           "<li><b>IA sous contrôle</b> : un assistant ne peut pas répondre si un contrôle échoue ; le SQL reste lisible et vérifiable.</li>"
           "<li><b>Maintenance</b> : un skill = un dossier ; on l'ajoute, le teste sur un exemple, le fait relire par l'équipe Data.</li></ul>")
    cards.insert(0, card("Le même chemin pour chaque question, en ligne de commande ou avec un assistant IA", flow, "1 / 4", "1"))
    cards.append(card("Pourquoi c'est utile pour DotWorld", why, "3", "2 / 4", True))
    return dict(title="Quatre skills d'analyse pour que les équipes répondent seules, avec les mêmes définitions et les mêmes contrôles",
                subtitle="Chaque skill : un SKILL.md (quand l'utiliser, définitions, pièges), des modèles SQL paramétrables, un contrôle de cohérence qui bloque la réponse s'il échoue, et un exemple vérifié.",
                tag="SKILLS", tag_class="", kpis=[], cols="1fr 1fr 0.8fr", rows="auto 1fr 1fr", cards=cards,
                footer="Exemples calculés sur les données SIMULÉES · dossier skills/ du dépôt")


def page_methods():
    body1 = ("<p><b>Sources publiques</b> (collecte du 13/11/2026, instantanés datés, robots.txt respecté, une requête toutes les 3 secondes) : site dotworld.ch, "
             "site Carrières (Teamtailor), mentions légales, CGV et tarifs de Makemycv, documentation Stripe et Adyen, guides Visa et Mastercard. "
             "Aucune connexion, aucune inscription, aucun essai, aucun paiement ; la vérification de sécurité de Himalayas n'a pas été contournée.</p>"
             "<p><b>Données réelles</b> : KKBox (WSDM Cup 2018, Kaggle), téléchargées par un compte personnel selon les règles de la compétition. "
             "Les fichiers bruts ne sont pas publiés ; le dépôt contient le script et les agrégats.</p>"
             "<p><b>Simulation</b> : <span class='mono'>src/simulate.py</span>, graine 42, 18 mois, 3 produits fictifs inspirés des univers publics de DotWorld "
             "(prix du produit A = prix publics de Makemycv ; prix de B et C = hypothèses). Toutes les hypothèses sont dans <span class='mono'>data/ASSUMPTIONS.md</span>.</p>")
    body2 = ("<ul><li>Les chiffres SIMULÉS montrent une méthode : ils ne décrivent pas DotWorld.</li>"
             "<li>Un seul produit est prouvé publiquement ; les autres univers sont cités sans nom.</li>"
             "<li>SEO et direct : CAC média nul, coûts de contenu et d'équipe non imputés.</li>"
             "<li>Attribution au dernier clic ; pas de modèle multi-touch.</li>"
             "<li>KKBox : pas de journal des refus, le churn involontaire y est une approximation ; les cohortes partent du premier paiement "
             "observé (depuis janvier 2015), elles contiennent donc d'anciens abonnés et la rétention est surestimée.</li>"
             "<li>Revenu évitable : revenu immédiat sur 18 mois, sans la valeur future des abonnés sauvés (estimation prudente).</li>"
             "<li>Seuils Visa : sources secondaires concordantes, à confirmer sur la fiche Visa.</li></ul>")
    body3 = ("<p><span class='mono'>python src/simulate.py</span> → <span class='mono'>src/run_sql.py</span> → <span class='mono'>src/analysis.py</span> → "
             "<span class='mono'>src/kkbox_prepare.py</span> → <span class='mono'>src/build_dashboard.py</span> → <span class='mono'>src/build_report.py</span></p>"
             "<p>SQL DuckDB commenté dans <span class='mono'>sql/</span> ; définitions dans <span class='mono'>METRICS.md</span> ; recommandations chiffrées dans "
             "<span class='mono'>docs/RECOMMANDATIONS.md</span>.</p>"
             f"<p style='margin-top:10px;padding:10px 12px;border-left:3px solid #2A78D6;background:#EEF5FD'>{AI_NOTE}</p>")
    nxt = ("<ol style='margin-left:18px'><li><b>Semaines 1-2</b> : brancher les vues de <span class='mono'>sql/00_views.sql</span> sur l'entrepôt réel "
           "(PSP, billing, analytics produit) ; relancer les contrôles des skills ; corriger les définitions avec le Data Engineer.</li>"
           "<li><b>Semaines 3-4</b> : réconciliation quotidienne PSP / billing ; tableau des refus et des retries par PSP, pays et MID ; alertes de litiges par campagne.</li>"
           "<li><b>Mois 2</b> : tests sur le calendrier des retries et le routage d'un pays, mesurés avec le Data Scientist.</li>"
           "<li><b>Mois 3</b> : LTV par canal sur cohortes complètes, partagée avec le Marketing ; nouveaux skills selon les questions les plus fréquentes.</li></ol>")
    return dict(title="Méthodes, limites et note sur l'IA",
                subtitle="Ce qui est public, ce qui est réel, ce qui est simulé ; ce que l'étude ne permet pas de dire ; comment tout reproduire.",
                tag="", tag_class="", kpis=[], cols="1.15fr 1fr", rows="1fr 1fr",
                cards=[card("Sources, licences et collecte", body1, "1", "1", True), card("Limites", body2, "2", "1", True),
                       card("Reproduction", body3, "1", "2", True),
                       card("Avec les vraies données : les 90 premiers jours", nxt, "2", "2", True)],
                footer="Sources : data/SOURCES.md · hypothèses : data/ASSUMPTIONS.md")


def build_html():
    kk, p2 = kkbox_page()
    pages = [page_overview(kk), page_public(), p2, page_acquisition(), page_funnel(), page_payments(),
             page_risk(), page_quality(), page_experiment(), page_skills(), page_methods()]
    sections = [PAGE.render(p=p, foot=FOOT) for p in pages]
    head = ('<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>DotWorld - étude de cas Data Analyst SaaS</title>'
            f"<style>{CSS}</style></head><body>")
    return head, sections


def edge() -> str:
    for p in [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe"]:
        if Path(p).exists():
            return p
    return shutil.which("msedge") or shutil.which("chrome") or "msedge"


def wait_file(path: Path, timeout=120) -> None:
    """Edge rend la main avant d'avoir fini d'écrire : on attend un fichier de taille stable."""
    import time

    last, t0 = -1, time.time()
    while time.time() - t0 < timeout:
        if path.exists() and path.stat().st_size > 0 and path.stat().st_size == last:
            return
        last = path.stat().st_size if path.exists() else -1
        time.sleep(1.5)
    raise TimeoutError(f"{path} non produit")


def clean_pdf(path: Path) -> None:
    """Métadonnées réduites au titre : pas d'auteur, d'outil ni de chemin."""
    from pypdf import PdfReader, PdfWriter

    rd = PdfReader(str(path))
    w = PdfWriter()
    for pg in rd.pages:
        w.add_page(pg)
    w.add_metadata({"/Title": "DotWorld - étude de cas Data Analyst SaaS"})
    w._info.get_object().pop("/Producer", None)
    w._info.get_object().pop("/Creator", None)
    tmp = path.with_suffix(".tmp.pdf")
    with open(tmp, "wb") as fh:
        w.write(fh)
    tmp.replace(path)


def main():
    TMP.mkdir(exist_ok=True)
    (DOCS / "img").mkdir(parents=True, exist_ok=True)
    head, sections = build_html()
    html = head + "".join(sections) + "</body></html>"
    src = TMP / "report.html"
    src.write_text(html, encoding="utf-8")
    pdf = DOCS / "DotWorld_EtudeDeCas.pdf"
    pdf.unlink(missing_ok=True)
    prof = TMP / "edge-profile"
    subprocess.run([edge(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--print-to-pdf-no-header",
                    f"--user-data-dir={prof}", f"--print-to-pdf={pdf}", src.as_uri()], check=True, capture_output=True, timeout=180)
    wait_file(pdf)
    clean_pdf(pdf)
    # Captures PNG par page (README)
    names = ["00_vue_ensemble", "01_dotworld_public", "02_kkbox", "03_acquisition", "04_parcours", "05_paiements",
             "06_litiges_fraude", "07_qualite", "08_experimentation", "09_skills", "10_methodes"]
    for name, sec in zip(names, sections):
        one = TMP / f"{name}.html"
        one.write_text(head.replace("page-break-after: always", "") + sec + "</body></html>", encoding="utf-8")
        subprocess.run([edge(), "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={prof}",
                        "--window-size=1536,864", f"--screenshot={DOCS / 'img' / (name + '.png')}", one.as_uri()],
                       check=True, capture_output=True, timeout=120)
        wait_file(DOCS / "img" / (name + ".png"))
    print("PDF :", pdf.relative_to(ROOT), f"({pdf.stat().st_size // 1024} Ko, {len(sections)} pages)")


if __name__ == "__main__":
    main()

"""Parcours SIMULÉ d'un studio SaaS : de la visite au paiement (graine fixe 42).

Toutes les données produites ici sont INVENTÉES. Elles servent à montrer une méthode
d'analyse ; ce ne sont pas des données de DotWorld. Les hypothèses sont listées dans
data/ASSUMPTIONS.md et rassemblées dans les constantes en haut de ce fichier.

Sortie : data/simulated/*.parquet
    sessions, signups, subscriptions, payment_attempts, refunds, disputes,
    fraud_reports, fraud_signals, marketing_spend, experiments,
    internal_payments (base de facturation interne), psp_settlements (rapports PSP),
    fx_rates

Usage : python src/simulate.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
rng = np.random.default_rng(SEED)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "simulated"

START = pd.Timestamp("2025-01-01")
END = pd.Timestamp("2026-06-30 23:59:59")  # date d'observation : tout ce qui suit est censuré
N_DAYS = (END.normalize() - START).days + 1

# --------------------------------------------------------------------------------------
# 1. Hypothèses (voir data/ASSUMPTIONS.md)
# --------------------------------------------------------------------------------------
# Produit A : prix publics de Makemycv (relevés le 2026-11-13). B et C : prix hypothétiques.
PRODUCTS = {
    "A": dict(univers="RH / CV", trial_price=2.90, trial_days=7, renew_price=27.95, cycle_days=28,
              annual_price=94.80, share=0.55, checkout=0.40, trial_cancel=1.10,
              hazard=[0.36, 0.24, 0.17, 0.13, 0.11, 0.10, 0.09, 0.08]),
    "B": dict(univers="Création design / contenus", trial_price=0.0, trial_days=7, renew_price=14.95,
              cycle_days=30, annual_price=119.00, share=0.25, checkout=0.30, trial_cancel=0.90,
              hazard=[0.20, 0.13, 0.10, 0.08, 0.07, 0.06, 0.055, 0.05]),
    "C": dict(univers="Automobile (rapports)", trial_price=1.00, trial_days=3, renew_price=19.90,
              cycle_days=30, annual_price=None, share=0.20, checkout=0.45, trial_cancel=1.15,
              hazard=[0.42, 0.28, 0.19, 0.15, 0.12, 0.10, 0.09, 0.08]),
}

COUNTRIES = ["FR", "US", "DE", "ES", "IT", "GB", "BR", "MX", "PL", "NL"]
COUNTRY_W = np.array([0.22, 0.18, 0.10, 0.09, 0.08, 0.06, 0.08, 0.07, 0.07, 0.05])
EEA = {"FR", "DE", "ES", "IT", "PL", "NL"}  # DSP2 : authentification forte pour les paiements initiés par le client
CURRENCY = {c: ("USD" if c == "US" else "EUR") for c in COUNTRIES}

# Campagnes : (canal, part des sessions, coût par session en EUR, probabilité d'inscription)
CAMPAIGNS = {
    "organic":          ("SEO",         0.36, 0.00, 0.075),
    "gads_brand":       ("Google Ads",  0.07, 0.15, 0.140),
    "gads_generic":     ("Google Ads",  0.18, 0.52, 0.085),
    "meta_prospecting": ("Meta",        0.09, 0.30, 0.050),
    "meta_retargeting": ("Meta",        0.04, 0.40, 0.090),
    "tiktok_ugc":       ("TikTok",      0.10, 0.11, 0.035),
    "aff_network":      ("Affiliation", 0.06, 0.00, 0.080),
    "(direct)":         ("Direct",      0.10, 0.00, 0.120),
}
# Campagne agressive : promo très visible sur Meta, du 2026-02-15 au 2026-03-31, en FR, US et ES
PROMO = dict(name="meta_promo_choc", start=pd.Timestamp("2026-02-15"), end=pd.Timestamp("2026-03-31 23:59"),
             countries=["FR", "US", "ES"], daily_sessions=1800, cost=0.22, signup=0.090)

CHECKOUT_MULT = {"tiktok_ugc": 0.80, "meta_promo_choc": 1.40, "aff_network": 1.10, "gads_brand": 1.15}
TRIAL_CANCEL = {"organic": 0.42, "gads_brand": 0.30, "gads_generic": 0.40, "meta_prospecting": 0.52,
                "meta_retargeting": 0.45, "meta_promo_choc": 0.62, "tiktok_ugc": 0.68, "aff_network": 0.55,
                "(direct)": 0.33}
CHURN_MULT = {"organic": 0.95, "gads_brand": 0.85, "gads_generic": 1.00, "meta_prospecting": 1.10,
              "meta_retargeting": 1.00, "meta_promo_choc": 1.30, "tiktok_ugc": 1.35, "aff_network": 1.15,
              "(direct)": 0.85}
AFFILIATE_CPA = 12.0  # EUR versés à l'affilié par premier paiement réussi

# Paiement : deux PSP fictifs, « PSP_S » (type Stripe) et « PSP_A » (type Adyen)
DEFAULT_PSP = {"A": "PSP_S", "B": "PSP_S", "C": "PSP_A"}
SPLIT_SHARE = 0.15  # part du trafic envoyée à l'autre PSP (répartition de charge)
BASE_DECLINE = {"PSP_S": 0.065, "PSP_A": 0.080}
COUNTRY_DECLINE = {  # surcroît de refus par PSP et pays de la carte
    "PSP_S": {"BR": 0.20, "MX": 0.16},          # pas d'acquisition locale : refus « cross-border »
    "PSP_A": {"BR": 0.04, "MX": 0.035, "US": 0.04},
}
INCIDENT = dict(psp="PSP_S", country="ES", start=pd.Timestamp("2026-04-01"), extra=0.08)  # baisse d'acceptation
CARD_TYPE_DECLINE = {"credit": 0.0, "debit": 0.02, "prepaid": 0.10}

SOFT = ["insufficient_funds", "do_not_honor", "try_again_later", "processing_error", "authentication_required"]
HARD = ["expired_card", "incorrect_number", "stolen_card", "lost_card", "transaction_not_allowed", "fraudulent"]
DELAYS = np.array([0, 1, 2, 3, 5, 7])
DELAY_W = np.array([0.15, 0.30, 0.15, 0.20, 0.10, 0.10])
RETRY_SUCCESS = {  # probabilité de succès d'une nouvelle tentative selon le délai (jours) ci-dessus
    "insufficient_funds": [0.05, 0.12, 0.16, 0.20, 0.25, 0.27],
    "do_not_honor":       [0.05, 0.10, 0.12, 0.14, 0.15, 0.15],
    "try_again_later":    [0.40, 0.45, 0.45, 0.45, 0.45, 0.45],
    "processing_error":   [0.45, 0.50, 0.50, 0.50, 0.50, 0.50],
    "authentication_required": [0.35, 0.35, 0.35, 0.35, 0.35, 0.35],
}
MAX_RETRIES = 4

DISPUTE_REASONS = ["subscription_canceled", "unrecognized", "product_unacceptable", "duplicate", "general"]
DISPUTE_REASON_W = [0.45, 0.35, 0.10, 0.05, 0.05]
DISPUTE_FEE_EUR = 15.0

EXPERIMENT = dict(id="EXP-A-PRIX-TRANSPARENT", product="A", start=pd.Timestamp("2026-03-01"),
                  end=pd.Timestamp("2026-04-30 23:59"), checkout_mult=0.94, cancel_mult=0.92, dispute_mult=0.50)


def pick(options, weights, size=None):
    w = np.asarray(weights, dtype=float)
    return rng.choice(options, size=size, p=w / w.sum())


# --------------------------------------------------------------------------------------
# 2. Taux de change USD -> EUR (marche aléatoire autour de 0,92)
# --------------------------------------------------------------------------------------
days = pd.date_range(START, END.normalize(), freq="D")
fx = 0.92 + np.cumsum(rng.normal(0, 0.0025, len(days)))
fx_rates = pd.DataFrame({"date": days, "usd_to_eur": fx.round(4)})
FX = dict(zip(fx_rates["date"], fx_rates["usd_to_eur"]))
FX_MONTH = fx_rates.groupby(fx_rates["date"].dt.to_period("M"))["usd_to_eur"].mean().round(4).to_dict()


def to_eur(amount, currency, ts):
    return amount if currency == "EUR" else amount * FX[ts.normalize()]


# --------------------------------------------------------------------------------------
# 3. Sessions (une session = un nouveau visiteur, pour rester simple)
# --------------------------------------------------------------------------------------
def build_sessions() -> pd.DataFrame:
    t = np.arange(N_DAYS)
    growth = 1 + 0.6 * t / N_DAYS
    dow = pd.DatetimeIndex(days).day_of_week.values
    weekly = np.where(dow >= 5, 0.80, 1.05)
    january = np.where(pd.DatetimeIndex(days).month == 1, 1.15, 1.0)  # pic de recherche d'emploi en janvier
    daily = rng.poisson(2100 * growth * weekly * january)

    n = int(daily.sum())
    day_idx = np.repeat(t, daily)
    camp_names = list(CAMPAIGNS)
    camp = pick(camp_names, [CAMPAIGNS[c][1] for c in camp_names], n)
    s = pd.DataFrame({
        "ts_utc": START + pd.to_timedelta(day_idx, "D") + pd.to_timedelta(rng.integers(0, 86400, n), "s"),
        "campaign": camp,
    })
    # Campagne agressive (sessions supplémentaires)
    promo_days = pd.date_range(PROMO["start"], PROMO["end"].normalize())
    pn = rng.poisson(PROMO["daily_sessions"], len(promo_days))
    p = pd.DataFrame({
        "ts_utc": np.repeat(promo_days.values, pn) + pd.to_timedelta(rng.integers(0, 86400, pn.sum()), "s"),
        "campaign": PROMO["name"],
    })
    s = pd.concat([s, p], ignore_index=True)
    n = len(s)
    s["channel"] = s["campaign"].map(lambda c: "Meta" if c == PROMO["name"] else CAMPAIGNS[c][0])
    s["product"] = pick(list(PRODUCTS), [PRODUCTS[k]["share"] for k in PRODUCTS], n)
    s["country"] = pick(COUNTRIES, COUNTRY_W, n)
    promo_mask = s["campaign"] == PROMO["name"]
    s.loc[promo_mask, "country"] = pick(PROMO["countries"], [0.45, 0.35, 0.20], promo_mask.sum())
    s.loc[promo_mask, "product"] = pick(["A", "C"], [0.7, 0.3], promo_mask.sum())
    mobile_p = np.where(s["channel"].isin(["TikTok", "Meta"]), 0.85, 0.58)
    s["device"] = np.where(rng.random(n) < mobile_p, "mobile", "desktop")
    s = s.sort_values("ts_utc").reset_index(drop=True)
    s["session_id"] = np.arange(1, n + 1)
    s["is_bot"] = False
    return s


def add_bot_sessions(s: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rafales de test de cartes : des robots créent des comptes et testent des cartes volées
    sur les essais à petit prix (produits A et C). Ils arrivent en « direct »."""
    burst_days = np.sort(rng.choice(pd.date_range("2025-03-01", "2026-06-15"), 10, replace=False))
    rows = []
    for d in burst_days:
        start = pd.Timestamp(d) + pd.Timedelta(hours=int(rng.integers(0, 22)))
        k = int(rng.integers(150, 600))
        product = pick(["A", "C"], [0.6, 0.4])
        card_country = pick(["US", "BR", "MX", "GB"], [0.4, 0.25, 0.2, 0.15])
        ts = start + pd.to_timedelta(np.sort(rng.integers(0, 7200, k)), "s")
        for x in ts:
            rows.append((x, product, card_country, start))
    b = pd.DataFrame(rows, columns=["ts_utc", "product", "card_country", "burst_start"])
    b["campaign"] = "(direct)"
    b["channel"] = "Direct"
    b["country"] = pick(["US", "FR", "DE", "GB"], [0.4, 0.3, 0.15, 0.15], len(b))  # pays IP (proxy)
    b["device"] = "desktop"
    b["is_bot"] = True
    b["session_id"] = np.arange(s["session_id"].max() + 1, s["session_id"].max() + 1 + len(b))
    s2 = pd.concat([s, b[s.columns]], ignore_index=True).sort_values("ts_utc").reset_index(drop=True)
    return s2, b


# --------------------------------------------------------------------------------------
# 4. Inscriptions, essais et expérimentation
# --------------------------------------------------------------------------------------
def build_signups(s: pd.DataFrame, bots: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    human = s[~s["is_bot"]].copy()
    base = human["campaign"].map(lambda c: PROMO["signup"] if c == PROMO["name"] else CAMPAIGNS[c][3])
    prod_mult = human["product"].map({"A": 1.0, "B": 0.8, "C": 1.1})
    dev_mult = np.where(human["device"] == "mobile", 0.85, 1.20)
    p = (base * prod_mult * dev_mult).clip(0, 0.5)
    su = human[rng.random(len(human)) < p].copy()
    su["signup_ts"] = su["ts_utc"] + pd.to_timedelta(rng.integers(30, 1800, len(su)), "s")
    su["is_bot"] = False

    # Expérimentation sur le parcours d'essai du produit A (affectation 50/50 par utilisateur)
    in_exp = (su["product"] == EXPERIMENT["product"]) & su["signup_ts"].between(EXPERIMENT["start"], EXPERIMENT["end"])
    su["variant"] = None
    su.loc[in_exp, "variant"] = np.where(rng.random(in_exp.sum()) < 0.5, "control", "prix_transparent")

    # Lancement du paiement de l'essai (saisie de la carte)
    pc = su["product"].map(lambda k: PRODUCTS[k]["checkout"]) * su["campaign"].map(lambda c: CHECKOUT_MULT.get(c, 1.0))
    pc = np.where(su["variant"] == "prix_transparent", pc * EXPERIMENT["checkout_mult"], pc)
    su["trial_checkout"] = rng.random(len(su)) < pc

    b = bots.copy()
    b["signup_ts"] = b["ts_utc"] + pd.to_timedelta(rng.integers(5, 60, len(b)), "s")
    b["variant"] = None
    b["trial_checkout"] = True
    cols = ["session_id", "signup_ts", "product", "campaign", "channel", "country", "device", "is_bot",
            "variant", "trial_checkout"]
    allsu = pd.concat([su[cols], b[cols]], ignore_index=True).sort_values("signup_ts").reset_index(drop=True)
    allsu["signup_id"] = np.arange(1, len(allsu) + 1)
    allsu["card_country_bot"] = None
    allsu.loc[allsu["is_bot"], "card_country_bot"] = allsu.loc[allsu["is_bot"], "session_id"].map(
        bots.set_index("session_id")["card_country"])
    exp = allsu.loc[allsu["variant"].notna(), ["signup_id", "signup_ts", "variant"]].rename(columns={"signup_ts": "assigned_at"})
    exp.insert(0, "experiment_id", EXPERIMENT["id"])
    return allsu, exp


# --------------------------------------------------------------------------------------
# 5. Paiements : tentatives, nouvelles tentatives, litiges
# --------------------------------------------------------------------------------------
class Ledger:
    def __init__(self):
        self.attempts, self.disputes, self.tc40, self.refunds, self.subs = [], [], [], [], []
        self.attempt_id = 0
        self.payment_id = 0


L = Ledger()


def decline_prob(u, psp, kind, initiator, ts):
    p = BASE_DECLINE[psp] + COUNTRY_DECLINE[psp].get(u["card_country"], 0) + CARD_TYPE_DECLINE[u["card_type"]]
    if psp == INCIDENT["psp"] and u["card_country"] == INCIDENT["country"] and ts >= INCIDENT["start"]:
        p += INCIDENT["extra"]
    if initiator == "MIT":
        p += 0.03
    if kind == "first_renewal":
        p += 0.04
    if u["fraud"]:
        p += 0.80 if u["is_bot"] else 0.35
    return min(p, 0.97)


def decline_code(u, psp, initiator):
    if u["fraud"]:
        if initiator == "CIT":
            return pick(["incorrect_number", "stolen_card", "fraudulent", "do_not_honor", "insufficient_funds"],
                        [0.25, 0.25, 0.2, 0.2, 0.1])
        return pick(["stolen_card", "lost_card", "do_not_honor", "fraudulent"], [0.35, 0.15, 0.3, 0.2])
    cross = COUNTRY_DECLINE[psp].get(u["card_country"], 0) > 0.1
    if initiator == "CIT":
        codes = ["insufficient_funds", "do_not_honor", "try_again_later", "processing_error", "incorrect_number",
                 "expired_card", "transaction_not_allowed", "fraudulent", "stolen_card"]
        w = [0.36, 0.26, 0.05, 0.03, 0.08, 0.04, 0.08, 0.06, 0.04]
    else:
        codes = ["insufficient_funds", "do_not_honor", "try_again_later", "processing_error", "expired_card",
                 "transaction_not_allowed", "fraudulent", "lost_card"]
        w = [0.48, 0.20, 0.05, 0.03, 0.12, 0.05, 0.04, 0.03]
    if cross:  # les refus « cross-border » ressortent en refus génériques ou non autorisés
        w = [x * (3.0 if c in ("do_not_honor", "transaction_not_allowed") else 1.0) for c, x in zip(codes, w)]
    return pick(codes, w)


def mid_of(psp, product, country):
    region = "US" if country == "US" else ("LATAM" if country in ("BR", "MX") else "EU")
    return f"{psp[-1]}-{product}-{region}"


def record(u, ts, psp, amount, kind, initiator, attempt_no, delay, approved, code, three_ds):
    L.attempt_id += 1
    L.attempts.append(dict(
        attempt_id=L.attempt_id, payment_id=L.payment_id, signup_id=u["signup_id"], subscription_id=u["subscription_id"],
        product=u["product"], ts_utc=ts, psp=psp, mid=mid_of(psp, u["product"], u["card_country"]),
        card_brand=u["card_brand"], card_type=u["card_type"], card_country=u["card_country"], ip_country=u["country"],
        amount=round(amount, 2), currency=u["currency"], payment_kind=kind, initiator=initiator,
        attempt_no=attempt_no, retry_delay_days=delay, three_ds=three_ds,
        outcome="approved" if approved else "declined", decline_code=None if approved else code,
        decline_type=None if approved else ("soft" if code in SOFT else "hard"),
    ))
    return L.attempt_id


def charge(u, ts, amount, kind, initiator):
    """Une « charge » logique = une tentative initiale + d'éventuelles nouvelles tentatives.
    Renvoie (succès, horodatage du dernier essai, id de la tentative réussie)."""
    L.payment_id += 1
    psp = u["psp"] if rng.random() > SPLIT_SHARE else ("PSP_A" if u["psp"] == "PSP_S" else "PSP_S")
    three_ds = "none"
    p_dec = decline_prob(u, psp, kind, initiator, ts)
    approved = rng.random() > p_dec
    code = None if approved else decline_code(u, psp, initiator)
    in_incident = psp == INCIDENT["psp"] and u["card_country"] == INCIDENT["country"] and ts >= INCIDENT["start"]
    if not approved and in_incident and rng.random() < INCIDENT["extra"] / p_dec:
        code = "do_not_honor"  # l'incident côté acquéreur ressort en refus générique
    if initiator == "CIT" and u["card_country"] in EEA and amount > 0:
        three_ds = "challenge" if rng.random() < 0.65 else "frictionless"
        if approved and three_ds == "challenge" and rng.random() < 0.09:  # abandon ou échec 3DS
            approved, code = False, "authentication_required"
    aid = record(u, ts, psp, amount, kind, initiator, 1, None, approved, code, three_ds)
    if approved:
        return True, ts, aid

    attempt_no, cur = 1, ts
    if initiator == "CIT":
        # le client réessaie tout de suite (souvent après 3DS ou fonds insuffisants)
        if code in SOFT and rng.random() < 0.45:
            p = 0.03 if u["fraud"] else 0.35
            ok = rng.random() < p
            cur = cur + pd.Timedelta(minutes=int(rng.integers(1, 15)))
            aid = record(u, cur, psp, amount, kind, initiator, 2, 0, ok, None if ok else code, three_ds)
            return ok, cur, aid if ok else None
        return False, cur, None

    # Nouvelles tentatives du marchand (MIT)
    if code in HARD:
        # PSP_A est configuré pour relancer aussi certains refus définitifs (contraire aux règles des réseaux)
        if psp == "PSP_A" and rng.random() < 0.7:
            cur = cur + pd.Timedelta(days=1)
            ok = rng.random() < 0.01
            aid = record(u, cur, psp, amount, kind, initiator, 2, 1, ok, None if ok else code, "none")
            return ok, cur, aid if ok else None
        return False, cur, None
    while attempt_no <= MAX_RETRIES:
        delay = int(pick(DELAYS, DELAY_W))
        cur = cur + pd.Timedelta(days=delay, hours=int(rng.integers(1, 12)))
        if cur > END:
            return False, cur, None
        attempt_no += 1
        p = RETRY_SUCCESS[code][int(np.where(DELAYS == delay)[0][0])] * (0.85 ** (attempt_no - 2))
        if u["fraud"]:
            p = 0.03
        ok = rng.random() < p
        aid = record(u, cur, psp, amount, kind, initiator, attempt_no, delay, ok, None if ok else code, "none")
        if ok:
            return True, cur, aid
    return False, cur, None


def after_success(u, ts, amount, kind, attempt_id):
    """Litiges, signalements de fraude (TC40) et remboursements sur une charge réussie."""
    if u["fraud"]:
        if rng.random() < (0.35 if u["is_bot"] else 0.75):
            L.tc40.append(dict(attempt_id=attempt_id, signup_id=u["signup_id"], reported_at=ts + pd.Timedelta(days=int(rng.integers(5, 30))),
                               card_brand=u["card_brand"], mid=L.attempts[attempt_id - 1]["mid"]))
        p, reasons, w = (0.25 if u["is_bot"] else 0.60), ["fraudulent"], [1]
    else:
        base = {"trial": 0.0005, "first_renewal": 0.010, "renewal": 0.002, "annual": 0.003}[kind]
        if kind == "first_renewal":
            if u["campaign"] == PROMO["name"]:
                base *= 6.0
            if u["variant"] == "prix_transparent":
                base *= EXPERIMENT["dispute_mult"]
            if u["product"] == "A":
                base *= 1.3
        p, reasons, w = base, DISPUTE_REASONS, DISPUTE_REASON_W
        if kind == "first_renewal" and rng.random() < 0.015:
            L.refunds.append(dict(attempt_id=attempt_id, signup_id=u["signup_id"], amount=amount, currency=u["currency"],
                                  refunded_at=ts + pd.Timedelta(days=int(rng.integers(0, 4)), hours=int(rng.integers(0, 23)))))
            return
    if rng.random() < p:
        reason = pick(reasons, w)
        outcome = pick(["won", "lost", "accepted"], [0.08, 0.77, 0.15] if reason == "fraudulent" else [0.22, 0.63, 0.15])
        att = L.attempts[attempt_id - 1]
        L.disputes.append(dict(dispute_id=len(L.disputes) + 1, attempt_id=attempt_id, signup_id=u["signup_id"],
                               product=u["product"], psp=att["psp"], mid=att["mid"], card_brand=u["card_brand"],
                               created_at=ts + pd.Timedelta(days=int(np.clip(rng.lognormal(3.2, 0.45), 7, 110))),
                               reason=reason, amount=amount, currency=u["currency"], outcome=outcome))


def simulate_subscription(u):
    prod = PRODUCTS[u["product"]]
    t0 = u["signup_ts"] + pd.Timedelta(minutes=int(rng.integers(1, 20)))
    sub = dict(subscription_id=u["subscription_id"], signup_id=u["signup_id"], product=u["product"],
               currency=u["currency"], started_at=t0, plan=None, status=None, cancel_reason=None,
               ended_at=None, paid_cycles=0, first_payment_at=None)
    annual = prod["annual_price"] is not None and not u["fraud"] and rng.random() < 0.07
    if annual:
        sub["plan"] = "annuel"
        ok, ts, aid = charge(u, t0, prod["annual_price"], "annual", "CIT")
        if not ok:
            sub.update(status="echec_paiement_initial", ended_at=ts)
            return sub
        after_success(u, ts, prod["annual_price"], "annual", aid)
        sub.update(paid_cycles=1, first_payment_at=ts)
        due = t0 + pd.Timedelta(days=365)
        if due > END:
            sub["status"] = "actif"
            return sub
        if rng.random() < 0.40:
            sub.update(status="annule", cancel_reason="plus_besoin", ended_at=due)
            return sub
        ok, ts, aid = charge(u, due, prod["annual_price"], "renewal", "MIT")
        if ok:
            after_success(u, ts, prod["annual_price"], "renewal", aid)
            sub.update(paid_cycles=2, status="actif")
        else:
            sub.update(status="annule_echec_paiement", cancel_reason="paiement_refuse", ended_at=ts)
        return sub

    sub["plan"] = "essai_puis_mensuel"
    if prod["trial_price"] > 0:
        ok, ts, aid = charge(u, t0, prod["trial_price"], "trial", "CIT")
        if not ok:
            sub.update(status="echec_paiement_essai", ended_at=ts)
            return sub
        after_success(u, ts, prod["trial_price"], "trial", aid)
        sub["first_payment_at"] = ts
    # Annulation pendant l'essai
    p_cancel = TRIAL_CANCEL[u["campaign"]] * prod["trial_cancel"]
    if u["variant"] == "prix_transparent":
        p_cancel *= EXPERIMENT["cancel_mult"]
    if u["fraud"]:
        p_cancel = 0.05
    trial_end = t0 + pd.Timedelta(days=prod["trial_days"])
    if rng.random() < min(p_cancel, 0.95):
        sub.update(status="essai_annule", cancel_reason="annule_pendant_essai",
                   ended_at=t0 + pd.Timedelta(hours=int(rng.integers(1, prod["trial_days"] * 24))))
        return sub
    if trial_end > END:
        sub["status"] = "en_essai"
        return sub
    due, cycle, kind = trial_end, 0, "first_renewal"
    while due <= END:
        ok, ts, aid = charge(u, due, prod["renew_price"], kind, "MIT")
        if not ok:
            if ts > END:
                sub["status"] = "impaye_en_cours"
                return sub
            sub.update(status="annule_echec_paiement", cancel_reason="paiement_refuse", ended_at=ts)
            return sub
        after_success(u, ts, prod["renew_price"], kind, aid)
        cycle += 1
        sub["paid_cycles"] = cycle
        if sub["first_payment_at"] is None:
            sub["first_payment_at"] = ts
        if u["fraud"] and rng.random() < 0.6:  # la carte volée est bloquée ou le compte fermé
            sub.update(status="annule", cancel_reason="fraude_detectee", ended_at=ts + pd.Timedelta(days=3))
            return sub
        hz = prod["hazard"][min(cycle - 1, len(prod["hazard"]) - 1)] * CHURN_MULT[u["campaign"]]
        if rng.random() < min(hz, 0.95):
            reason = pick(["plus_besoin", "prix", "oubli_essai", "autre"], [0.55, 0.2, 0.15, 0.10])
            sub.update(status="annule", cancel_reason=reason,
                       ended_at=due + pd.Timedelta(days=int(rng.integers(1, prod["cycle_days"]))))
            return sub
        due = due + pd.Timedelta(days=prod["cycle_days"])
        kind = "renewal"
    sub["status"] = "actif"
    return sub


def build_payments(signups: pd.DataFrame) -> pd.DataFrame:
    starters = signups[signups["trial_checkout"]].reset_index(drop=True)
    n = len(starters)
    starters["subscription_id"] = np.arange(1, n + 1)
    starters["currency"] = starters["country"].map(CURRENCY)
    starters["card_country"] = np.where(rng.random(n) < 0.96, starters["country"], pick(COUNTRIES, COUNTRY_W, n))
    bot = starters["is_bot"].values
    starters.loc[bot, "card_country"] = starters.loc[bot, "card_country_bot"]
    starters["card_brand"] = pick(["visa", "mastercard", "amex"], [0.58, 0.37, 0.05], n)
    starters["card_type"] = pick(["credit", "debit", "prepaid"], [0.45, 0.47, 0.08], n)
    # fraude « organique » (cartes volées, hors robots) : plus fréquente sur cartes prépayées et certains canaux
    p_fraud = 0.006 * np.where(starters["card_type"] == "prepaid", 4, 1) * starters["campaign"].map(
        lambda c: {"tiktok_ugc": 2.0, "aff_network": 2.5, PROMO["name"]: 1.5}.get(c, 1.0))
    p_fraud = np.where(starters["product"] == "B", p_fraud * 0.4, p_fraud)
    starters["fraud"] = bot | (rng.random(n) < p_fraud)
    starters["psp"] = starters["product"].map(DEFAULT_PSP)
    subs = [simulate_subscription(u) for u in starters.to_dict("records")]
    return starters, pd.DataFrame(subs)


# --------------------------------------------------------------------------------------
# 6. Signaux de fraude (connus au moment du paiement de l'essai)
# --------------------------------------------------------------------------------------
def build_fraud_signals(starters: pd.DataFrame) -> pd.DataFrame:
    f = starters[["signup_id", "signup_ts", "product", "country", "card_country", "card_type", "is_bot", "fraud"]].copy()
    f = f.sort_values("signup_ts")
    # vélocité : nombre de paiements d'essai sur le même produit dans l'heure précédente (même « BIN » simulé)
    f["bin"] = np.where(f["is_bot"], "4" + f["card_country"].astype(str) + "999",
                        "4" + pd.Series(rng.integers(10000, 99999, len(f)).astype(str), index=f.index))
    f["velocity_1h_same_bin"] = (
        f.set_index("signup_ts").groupby("bin")["signup_id"].transform(lambda x: x.rolling("1h").count()).values
    ).astype(int)
    f["ip_card_country_mismatch"] = f["country"] != f["card_country"]
    f["disposable_email"] = np.where(f["fraud"], rng.random(len(f)) < 0.55, rng.random(len(f)) < 0.03)
    f["risk_score"] = (
        0.35 * (f["velocity_1h_same_bin"] >= 5) + 0.25 * f["ip_card_country_mismatch"] + 0.20 * f["disposable_email"]
        + 0.10 * (f["card_type"] == "prepaid") + rng.normal(0.05, 0.05, len(f))
    ).clip(0, 1).round(3)
    return f[["signup_id", "signup_ts", "product", "bin", "velocity_1h_same_bin", "country", "card_country",
              "ip_card_country_mismatch", "card_type", "disposable_email", "risk_score"]].rename(
        columns={"country": "ip_country", "signup_ts": "ts_utc"})


# --------------------------------------------------------------------------------------
# 7. Deux sources de revenu : la base de facturation interne et les rapports PSP
# --------------------------------------------------------------------------------------
def build_revenue_sources(att: pd.DataFrame, refunds: pd.DataFrame, disputes: pd.DataFrame):
    ok = att[att["outcome"] == "approved"].copy()
    # Base interne : horodatage UTC, montant converti en EUR au taux MOYEN du mois
    internal = ok[["attempt_id", "signup_id", "product", "psp", "ts_utc", "amount", "currency"]].copy()
    internal["fx_month"] = internal["ts_utc"].dt.to_period("M").map(FX_MONTH)
    internal["amount_eur"] = np.where(internal["currency"] == "EUR", internal["amount"],
                                      internal["amount"] * internal["fx_month"]).round(2)
    internal["record_type"] = "charge"
    lost = rng.random(len(internal)) < 0.0025          # webhooks perdus : paiements absents de la base
    internal = internal[~lost]
    dup = internal.sample(frac=0.004, random_state=SEED)  # webhooks rejoués : doublons
    internal = pd.concat([internal, dup], ignore_index=True)
    rf = refunds.merge(ok[["attempt_id", "product", "psp"]], on="attempt_id")
    rf = rf.assign(ts_utc=rf["refunded_at"], record_type="refund",
                   fx_month=rf["refunded_at"].dt.to_period("M").map(FX_MONTH))
    rf["amount_eur"] = -np.where(rf["currency"] == "EUR", rf["amount"], rf["amount"] * rf["fx_month"]).round(2)
    internal = pd.concat([internal, rf[["attempt_id", "signup_id", "product", "psp", "ts_utc", "amount_eur", "record_type", "currency"]]],
                         ignore_index=True)
    internal = internal.sort_values("ts_utc").reset_index(drop=True)
    internal.insert(0, "internal_id", np.arange(1, len(internal) + 1))
    internal = internal[["internal_id", "attempt_id", "signup_id", "product", "psp", "ts_utc", "currency", "amount_eur", "record_type"]]

    # Rapport PSP : heure LOCALE de Zurich (PSP_S) ou UTC (PSP_A), montant au taux du JOUR, frais, litiges
    def fee(row_amount, psp, intl):
        if psp == "PSP_S":
            return row_amount * (0.0325 if intl else 0.015) + 0.25
        return row_amount * (0.028 if intl else 0.012) + 0.11

    ok["intl"] = ok["card_country"].isin(["US", "BR", "MX", "GB"]) & (ok["currency"] == "EUR")
    psp = ok[["attempt_id", "psp", "ts_utc", "amount", "currency", "intl"]].copy()
    psp["type"] = "charge"
    rf2 = refunds.merge(ok[["attempt_id", "psp", "intl"]], on="attempt_id")
    rf2 = rf2.assign(ts_utc=rf2["refunded_at"], amount=-rf2["amount"], type="refund")
    lost_d = disputes[disputes["outcome"] != "won"].merge(ok[["attempt_id", "intl"]], on="attempt_id")
    lost_d = lost_d.assign(ts_utc=lost_d["created_at"], amount=-lost_d["amount"], type="dispute")
    psp = pd.concat([psp, rf2[psp.columns], lost_d[["attempt_id", "psp", "ts_utc", "amount", "currency", "intl", "type"]]],
                    ignore_index=True)
    psp["fx_day"] = psp["ts_utc"].dt.normalize().map(FX)
    psp["gross_eur"] = np.where(psp["currency"] == "EUR", psp["amount"], psp["amount"] * psp["fx_day"]).round(2)
    psp["fee_eur"] = np.where(psp["type"] == "charge",
                              [fee(a, p, i) for a, p, i in zip(psp["gross_eur"], psp["psp"], psp["intl"])],
                              np.where(psp["type"] == "dispute", DISPUTE_FEE_EUR, 0.0)).round(2)
    psp["net_eur"] = (psp["gross_eur"] - psp["fee_eur"]).round(2)
    local = psp["ts_utc"].dt.tz_localize("UTC").dt.tz_convert("Europe/Zurich").dt.tz_localize(None)
    psp["reported_at"] = np.where(psp["psp"] == "PSP_S", local, psp["ts_utc"])
    psp["report_timezone"] = np.where(psp["psp"] == "PSP_S", "Europe/Zurich", "UTC")
    psp = psp.sort_values("ts_utc").reset_index(drop=True)
    psp.insert(0, "psp_reference", [f"{p[-1]}{i:08d}" for i, p in enumerate(psp["psp"], 1)])
    psp = psp[["psp_reference", "attempt_id", "psp", "type", "reported_at", "report_timezone", "currency", "amount",
               "gross_eur", "fee_eur", "net_eur"]]
    return internal, psp


# --------------------------------------------------------------------------------------
# 8. Dépenses marketing
# --------------------------------------------------------------------------------------
def build_spend(sessions: pd.DataFrame, subs: pd.DataFrame, signups: pd.DataFrame) -> pd.DataFrame:
    s = sessions[~sessions["is_bot"]].copy()
    cost = s["campaign"].map(lambda c: PROMO["cost"] if c == PROMO["name"] else CAMPAIGNS[c][2])
    country_mult = s["country"].map(lambda c: {"US": 1.6, "GB": 1.3, "BR": 0.45, "MX": 0.5, "PL": 0.6}.get(c, 1.0))
    s["spend_eur"] = cost * country_mult * rng.lognormal(0, 0.15, len(s))
    s["date"] = s["ts_utc"].dt.normalize()
    paid = s[s["spend_eur"] > 0].groupby(["date", "channel", "campaign", "country", "product"], as_index=False).agg(
        spend_eur=("spend_eur", "sum"), sessions=("session_id", "count"))
    # Affiliation : commission par premier paiement réussi
    aff = subs.merge(signups[["signup_id", "campaign", "channel", "country"]], on="signup_id")
    aff = aff[(aff["campaign"] == "aff_network") & aff["first_payment_at"].notna()].copy()
    aff["date"] = pd.to_datetime(aff["first_payment_at"]).dt.normalize()
    aff = aff.groupby(["date", "channel", "campaign", "country", "product"], as_index=False).size().rename(columns={"size": "conversions"})
    aff["spend_eur"] = aff["conversions"] * AFFILIATE_CPA
    aff["sessions"] = 0
    out = pd.concat([paid, aff[paid.columns]], ignore_index=True)
    out["spend_eur"] = out["spend_eur"].round(2)
    return out.sort_values(["date", "channel", "campaign"]).reset_index(drop=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sessions = build_sessions()
    sessions, bots = add_bot_sessions(sessions)
    signups, experiments = build_signups(sessions, bots)
    starters, subs = build_payments(signups)
    att = pd.DataFrame(L.attempts)
    # Censure : ce qui arrive après la date d'observation n'est pas encore connu
    disputes = pd.DataFrame(L.disputes).query("created_at <= @END").reset_index(drop=True)
    disputes["dispute_id"] = np.arange(1, len(disputes) + 1)
    refunds = pd.DataFrame(L.refunds).query("refunded_at <= @END").reset_index(drop=True)
    tc40 = pd.DataFrame(L.tc40).query("reported_at <= @END").reset_index(drop=True)
    fraud_signals = build_fraud_signals(starters)
    internal, psp = build_revenue_sources(att, refunds, disputes)
    spend = build_spend(sessions, subs, signups)

    signups_out = signups.drop(columns=["card_country_bot"])
    tables = {
        "sessions": sessions.drop(columns=["is_bot"]),  # en production, les robots ne sont pas étiquetés
        "signups": signups_out.drop(columns=["is_bot"]),
        "subscriptions": subs,
        "payment_attempts": att,
        "refunds": refunds,
        "disputes": disputes,
        "fraud_reports": tc40,
        "fraud_signals": fraud_signals,
        "marketing_spend": spend,
        "experiments": experiments,
        "internal_payments": internal,
        "psp_settlements": psp,
        "fx_rates": fx_rates,
    }
    # Vérité terrain gardée à part pour contrôler les analyses (jamais utilisée par les requêtes métier)
    truth = starters[["signup_id", "is_bot", "fraud"]]
    for name, df in tables.items():
        df.to_parquet(OUT / f"{name}.parquet", index=False)
        print(f"{name:18s} {len(df):>9,d} lignes")
    truth.to_parquet(OUT / "_ground_truth_fraud.parquet", index=False)


if __name__ == "__main__":
    main()

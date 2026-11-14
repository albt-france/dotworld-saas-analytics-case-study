"""DONNÉES RÉELLES (KKBOX, WSDM Cup 2018 sur Kaggle) : agrégats d'abonnement.

Les fichiers bruts restent dans data/raw/kkbox/ (jamais publiés, règles de la compétition).
Ce script ne publie que des AGRÉGATS dans data/public/kkbox_*.csv.

Fichiers attendus (archives .7z de Kaggle ou CSV décompressés) :
    transactions.csv (optionnel, historique 2015-2017), transactions_v2.csv, members_v3.csv, train_v2.csv

Colonnes utilisées (dictionnaire Kaggle) :
    transactions : msno, payment_method_id, payment_plan_days, plan_list_price, actual_amount_paid,
                   is_auto_renew, transaction_date, membership_expire_date, is_cancel
    train_v2     : msno, is_churn (pas de nouvel abonnement valide dans les 30 jours après expiration, mars 2017)

Usage : python src/kkbox_prepare.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "kkbox"
OUT = ROOT / "data" / "public"


def extract_archives() -> None:
    """Décompresse les .7z déposés par l'utilisateur (py7zr, sans exécuter de binaire tiers)."""
    import py7zr

    for arc in RAW.glob("*.7z"):
        target = arc.with_suffix("")
        if target.exists() or any(RAW.rglob(target.name)):
            continue
        print("décompression", arc.name)
        with py7zr.SevenZipFile(arc, "r") as z:
            z.extractall(RAW)


def find(name: str) -> Path | None:
    hits = sorted(RAW.rglob(name))
    return hits[0] if hits else None


def main() -> None:
    extract_archives()
    tx_files = [p for p in (find("transactions.csv"), find("transactions_v2.csv")) if p]
    train = find("train_v2.csv")
    if not tx_files:
        sys.exit("Aucun fichier de transactions KKBox dans data/raw/kkbox/ : étape ignorée.")

    con = duckdb.connect()
    files = ", ".join(f"'{p.as_posix()}'" for p in tx_files)
    con.execute(f"""
        CREATE TABLE tx AS
        SELECT DISTINCT msno, payment_method_id, payment_plan_days, plan_list_price, actual_amount_paid,
               is_auto_renew, is_cancel,
               strptime(CAST(transaction_date AS VARCHAR), '%Y%m%d')::DATE      AS tx_date,
               strptime(CAST(membership_expire_date AS VARCHAR), '%Y%m%d')::DATE AS expire_date
        FROM read_csv_auto([{files}])
        WHERE transaction_date BETWEEN 20150101 AND 20170331
    """)
    obs_end = con.execute("SELECT max(tx_date) FROM tx").fetchall()[0][0]
    print("transactions :", con.execute("SELECT count(*), count(DISTINCT msno) FROM tx").fetchall()[0], "jusqu'au", obs_end)

    q = {}
    # 1. Vue d'ensemble
    q["kkbox_overview"] = """
        SELECT count(*) AS transactions, count(DISTINCT msno) AS members,
               min(tx_date) AS first_date, max(tx_date) AS last_date,
               round(avg(is_auto_renew), 4) AS share_auto_renew_tx,
               round(avg(is_cancel), 4) AS share_cancel_tx,
               round(avg((payment_plan_days = 30)::INT), 4) AS share_30_day_plans
        FROM tx"""
    # 2. Rétention mensuelle par cohorte (premier mois payé), anti-censure
    q["kkbox_cohort_retention"] = f"""
        -- Actif au mois m = abonnement valide le dernier jour du mois m (les formules longues comptent
        -- donc chaque mois couvert, pas seulement le mois du paiement). Dates d'expiration aberrantes exclues.
        WITH paid AS (
            SELECT msno, tx_date, expire_date FROM tx
            WHERE is_cancel = 0 AND actual_amount_paid > 0
              AND expire_date > tx_date AND expire_date <= tx_date + INTERVAL 450 DAY
        ),
        first AS (SELECT msno, date_trunc('month', min(tx_date)) AS cohort FROM paid GROUP BY 1),
        cover AS (
            SELECT msno, m FROM (
                SELECT msno, expire_date,
                       unnest(generate_series(date_trunc('month', tx_date), date_trunc('month', expire_date), INTERVAL 1 MONTH)) AS m
                FROM paid)
            WHERE last_day(m) < expire_date
        ),
        months AS (SELECT DISTINCT msno, CAST(m AS DATE) AS m FROM cover),
        j AS (SELECT f.cohort, date_diff('month', f.cohort, m.m) AS k, m.msno
              FROM first f JOIN months m USING (msno))
        SELECT strftime(cohort, '%Y-%m') AS cohort, k,
               count(DISTINCT msno) AS active,
               round(count(DISTINCT msno) / first_value(count(DISTINCT msno)) OVER (PARTITION BY cohort ORDER BY k), 4) AS retention
        FROM j
        WHERE cohort >= DATE '2015-07-01' AND cohort + to_months(k) <= DATE '{obs_end}'
        GROUP BY cohort, k ORDER BY cohort, k"""
    # 3. Renouvellement à l'échéance selon le renouvellement automatique (fonction de fenêtre LEAD)
    q["kkbox_renewal_by_autorenew"] = f"""
        WITH s AS (
            SELECT msno, tx_date, expire_date, is_auto_renew, is_cancel, payment_plan_days,
                   lead(tx_date) OVER (PARTITION BY msno ORDER BY tx_date, expire_date) AS next_tx
            FROM tx WHERE actual_amount_paid > 0 AND is_cancel = 0
        )
        SELECT is_auto_renew, count(*) AS expirations,
               round(avg((next_tx IS NOT NULL AND next_tx <= expire_date + INTERVAL 30 DAY)::INT), 4) AS renewed_within_30d
        FROM s
        WHERE expire_date + INTERVAL 30 DAY <= DATE '{obs_end}' AND payment_plan_days BETWEEN 28 AND 31
        GROUP BY 1 ORDER BY 1"""
    # 4. Churn volontaire contre involontaire (approximation, voir la note dans le rapport)
    q["kkbox_churn_type"] = f"""
        WITH last AS (
            SELECT * FROM (
                SELECT *, row_number() OVER (PARTITION BY msno ORDER BY tx_date DESC, expire_date DESC) AS rn
                FROM tx) WHERE rn = 1
        )
        SELECT CASE WHEN is_cancel = 1 THEN 'volontaire : annulation explicite'
                    WHEN is_auto_renew = 0 THEN 'non renouvelé : formule sans renouvellement automatique'
                    ELSE 'involontaire probable : renouvellement auto actif, aucun paiement suivant' END AS churn_type,
               count(*) AS members
        FROM last
        WHERE expire_date + INTERVAL 30 DAY <= DATE '{obs_end}'
          AND expire_date >= DATE '{obs_end}' - INTERVAL 180 DAY
        GROUP BY 1 ORDER BY 2 DESC"""
    # 5. ARPA mensuel (en dollars taïwanais, NT$)
    q["kkbox_arpa_monthly"] = """
        SELECT strftime(date_trunc('month', tx_date), '%Y-%m') AS month,
               count(DISTINCT msno) AS paying_members,
               round(sum(actual_amount_paid) / count(DISTINCT msno), 1) AS arpa_ntd,
               round(avg((actual_amount_paid < plan_list_price)::INT), 4) AS share_discounted
        FROM tx WHERE actual_amount_paid > 0 AND is_cancel = 0
        GROUP BY 1 ORDER BY 1"""
    if train:
        con.execute(f"CREATE TABLE train AS SELECT * FROM read_csv_auto('{train.as_posix()}')")
        # 6. Churn de mars 2017 (étiquette officielle) selon le moyen de paiement et le renouvellement auto
        q["kkbox_churn_by_payment"] = """
            WITH last AS (
                SELECT * FROM (SELECT *, row_number() OVER (PARTITION BY msno ORDER BY tx_date DESC) AS rn FROM tx)
                WHERE rn = 1
            ),
            j AS (SELECT t.is_churn, l.payment_method_id, l.is_auto_renew FROM train t JOIN last l USING (msno)),
            top AS (SELECT payment_method_id FROM j GROUP BY 1 ORDER BY count(*) DESC LIMIT 6)
            SELECT CASE WHEN payment_method_id IN (SELECT * FROM top) THEN 'moyen ' || payment_method_id ELSE 'autres' END AS payment_method,
                   is_auto_renew, count(*) AS members, round(avg(is_churn), 4) AS churn_rate
            FROM j GROUP BY 1, 2 HAVING count(*) >= 500 ORDER BY members DESC"""
        q["kkbox_churn_overall"] = """
            SELECT count(*) AS members, round(avg(is_churn), 4) AS churn_rate FROM train"""
    OUT.mkdir(parents=True, exist_ok=True)
    for name, sql in q.items():
        df = con.sql(sql).df()
        df.to_csv(OUT / f"{name}.csv", index=False)
        print(f"{name:32s} {len(df):>5d} lignes")


if __name__ == "__main__":
    main()

"""Exécute les fichiers sql/*.sql dans DuckDB et enregistre chaque requête nommée
(« -- name: xxx ») dans data/results/xxx.csv.

Usage : python src/run_sql.py            (toutes les requêtes)
        python src/run_sql.py routing     (seulement les requêtes dont le nom contient « routing »)
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data" / "results"


def connect() -> duckdb.DuckDBPyConnection:
    os.chdir(ROOT)  # les vues lisent data/simulated/*.parquet en chemin relatif
    con = duckdb.connect()
    con.execute((ROOT / "sql" / "00_views.sql").read_text(encoding="utf-8"))
    return con


def named_queries(path: Path):
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"^-- name: (\w+)\s*$", text, flags=re.M)
    for i in range(1, len(parts), 2):
        yield parts[i], parts[i + 1].strip().rstrip(";")


def main(filter_: str | None = None) -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    con = connect()
    for path in sorted((ROOT / "sql").glob("0[1-9]_*.sql")):
        for name, query in named_queries(path):
            if filter_ and filter_ not in name:
                continue
            df = con.sql(query).df()
            df.to_csv(RESULTS / f"{name}.csv", index=False)
            print(f"{path.name:36s} {name:38s} {len(df):>6d} lignes")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)

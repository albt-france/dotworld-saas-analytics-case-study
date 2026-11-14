"""Boîte à outils commune aux skills d'analyse.

- connect()        : ouvre DuckDB et crée les vues métier (sql/00_views.sql)
- render(sql, p)   : remplace les paramètres {{nom}} par des valeurs VALIDÉES
                     (dates ISO, codes pays, listes de noms simples) : pas d'injection SQL possible
- run(con, path,p) : exécute un modèle SQL paramétré et renvoie un DataFrame
- Checks           : collecte les contrôles de cohérence et refuse de conclure si l'un échoue
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_WORD = re.compile(r"^[A-Za-z0-9_ ()\-\.]+$")


def connect() -> duckdb.DuckDBPyConnection:
    os.chdir(ROOT)
    con = duckdb.connect()
    con.execute((ROOT / "sql" / "00_views.sql").read_text(encoding="utf-8"))
    return con


def _literal(value) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, (list, tuple)):
        return "(" + ", ".join(_literal(v) for v in value) + ")"
    s = str(value)
    if _DATE.match(s):
        return f"DATE '{s}'"
    if _WORD.match(s):
        return "'" + s + "'"
    raise ValueError(f"Paramètre refusé (caractères non autorisés) : {s!r}")


def render(sql: str, params: dict) -> str:
    def sub(m):
        key = m.group(1)
        if key not in params:
            raise KeyError(f"Paramètre manquant : {key}")
        return _literal(params[key])
    return re.sub(r"\{\{(\w+)\}\}", sub, sql)


def run(con, path: Path, params: dict) -> pd.DataFrame:
    return con.sql(render(path.read_text(encoding="utf-8"), params)).df()


@dataclass
class Checks:
    results: list = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.results.append((name, bool(ok), detail))

    @property
    def ok(self) -> bool:
        return all(ok for _, ok, _ in self.results)

    def report(self) -> str:
        lines = ["", "CONTRÔLES DE COHÉRENCE"]
        for name, ok, detail in self.results:
            lines.append(f"  [{'OK' if ok else 'ÉCHEC'}] {name}" + (f" - {detail}" if detail else ""))
        lines.append("  => " + ("tous les contrôles passent : le résultat peut être communiqué."
                                if self.ok else "au moins un contrôle échoue : NE PAS conclure, investiguer d'abord."))
        return "\n".join(lines)


def show(df: pd.DataFrame, title: str) -> str:
    return f"\n## {title}\n\n" + df.to_markdown(index=False) if hasattr(df, "to_markdown") else df.to_string(index=False)

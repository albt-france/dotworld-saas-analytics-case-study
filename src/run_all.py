"""Reproduit toute l'étude dans l'ordre : simulation, SQL, statistiques, KKBox (si présent),
tableau de bord, rapport PDF, puis lance les 4 skills sur leur exemple.

Usage : python src/run_all.py            (tout)
        python src/run_all.py --no-pdf   (sans Edge : pas de PDF ni de captures)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def step(*args):
    print("\n>>>", " ".join(args), flush=True)
    subprocess.run([PY, *args], cwd=ROOT, check=True)


def main():
    step("src/simulate.py")
    step("src/run_sql.py")
    step("src/analysis.py")
    if any((ROOT / "data" / "raw" / "kkbox").glob("*transactions*")):
        step("src/kkbox_prepare.py")
    else:
        print("\n(KKBox absent de data/raw/kkbox/ : les agrégats publiés dans data/public/ sont conservés)")
    step("src/build_dashboard.py")
    if "--no-pdf" not in sys.argv:
        step("src/build_report.py")
    step("skills/cohort-retention/run.py", "--products", "A", "B", "C", "--grain", "quarter", "--max-cycle", "8")
    step("skills/ltv-by-channel/run.py", "--horizon", "180")
    step("skills/payment-health/run.py", "--countries", "ES", "--start", "2026-01-01", "--end", "2026-07-01",
         "--split", "2026-04-01", "--dim", "psp")
    step("skills/experiment-readout/run.py", "--experiment", "EXP-A-PRIX-TRANSPARENT", "--window", "60")


if __name__ == "__main__":
    main()

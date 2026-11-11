"""Konstanta, pembaca hasil, dan format angka untuk pembangun Laporan Akhir."""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.environ.get("SR_RESULTS", os.path.join(ROOT, "results"))
FIGL = os.path.join(ROOT, "figures", "laporan")
OUT = os.path.join(ROOT, "docs", "output")
os.makedirs(OUT, exist_ok=True)

JUDUL = ("Pengembangan Prototipe Simulasi Web-Based Decision Support System untuk Penyelesaian Multi-Trip "
         "Multi-Compartment Vehicle Routing Problem pada Distribusi BBM Multi-Produk dengan Hybrid Metaheuristic AI")
TIM = [
    ("Ketua", "Dr. Ir. Asepta Surya Wardhana, S.T., M.T.", "19810909 201012 1 001"),
    ("Anggota", "Astrie Kusuma Dewi, S.T., M.Eng.", "19790329 200604 2 001"),
    ("Anggota", "Chalidia Nurin Hamdani, S.T., M.T.", "19901122 201503 1 003"),
    ("Anggota", "Nano Koes Ardhiyanto, M.T.", "19870827 202202 1 001"),
]
NIDN_KETUA = "0009098102"
SP3 = "046/SP3/Penelitian/DIPA2026/PEM Akamigas"
DIREKTUR = "Dr. Erdila Indriani, S.Si., M.T."
REPO = "https://github.com/asw09zoom-netizen/smartroute-bbm"
SHEET = "https://docs.google.com/spreadsheets/d/1CohYmRvhwtAD3y34z9DmqEYkp-sfHlJ1g_Zs4YWPRq4"
VAR = ["GA", "GA-SA", "GA-SA-RL"]


def J(name):
    p = os.path.join(RES, name)
    return json.load(open(p)) if os.path.exists(p) else None


def C(name):
    p = os.path.join(RES, name)
    return pd.read_csv(p) if os.path.exists(p) else None


def f(x, d=1):
    """Angka gaya Indonesia: koma desimal, titik ribuan."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    s = f"{x:,.{d}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def rp(x):
    return "Rp" + f(x, 0)


def pv(p):
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "–"
    return "< 0,001" if p < 0.001 else f(p, 3)


def pct(new, old, d=1):
    v = (new - old) / old * 100
    return ("+" if v >= 0 else "−") + f(abs(v), d) + "%"


def jam(menit_sejak_06):
    """Menit sejak 06.00 -> 'hh.mm'."""
    t = 360 + float(menit_sejak_06)
    return f"{int(t // 60):02d}.{int(round(t % 60)) % 60:02d}"


def load_results():
    return dict(e0=J("E0_audit.json"), e1=J("E1_summary.json"), e2=J("E2_summary.json"), e4=J("E4_scenarios.json"),
                e4b=J("E4b_fleet_remedy.json"), e5=J("E5_summary.json"), e5b=J("E5b_summary.json"),
                e3=C("E3_pareto.csv"), e3b=C("E3b_pareto.csv"), e3c=C("E3c_pareto.csv"), e3s=C("E3_sens_fixedcost.csv"),
                e6=C("E6_montecarlo.csv"), e7=C("E7_cvrplib.csv"), e8=J("E8_summary.json"), e9=J("E9_summary.json"),
                e10=J("E10_summary.json"), e10r=C("E10_scalability.csv"), app=J("APP_check.json"), e5r=C("E5_dynamic.csv"),
                e1r=C("E1_runs.csv"))


def pareto_pts(df):
    fe = df[df.unassigned == 0]
    return fe, fe[fe.pareto_cost_co2].sort_values("cost_rp").drop_duplicates(["cost_rp", "co2_kg"])


def e7_tests(e7):
    """Uji Wilcoxon berpasangan satu sisi GA-SA-RL < GA dan < GA-SA pada instance yang memuat ketiga varian."""
    from scipy import stats as ss
    inst = [i for i in e7.instance.unique() if e7[e7.instance == i].variant.nunique() == 3]
    d = e7[e7.instance.isin(inst)]
    out = dict(n_inst=len(inst))
    piv = d.groupby(["instance", "variant"]).gap_pct.mean().unstack()
    for o in ["GA", "GA-SA"]:
        # utama: Wilcoxon atas rerata per instance (blok = instance)
        out[o] = float(ss.wilcoxon(piv["GA-SA-RL"], piv[o], alternative="less").pvalue)
        # pelengkap: Wilcoxon atas pasangan instance x seed
        a = d[d.variant == "GA-SA-RL"].sort_values(["instance", "seed"]).gap_pct.values
        b = d[d.variant == o].sort_values(["instance", "seed"]).gap_pct.values
        out[o + "_run"] = float(ss.wilcoxon(a, b, alternative="less").pvalue)
        out["n_pairs"] = len(a)
    out["mean"] = {v: float(piv[v].mean()) for v in VAR if v in piv}
    try:
        fr = ss.friedmanchisquare(*[piv[v].values for v in VAR])
        out["friedman"] = (float(fr.statistic), float(fr.pvalue))
    except Exception:
        out["friedman"] = None
    return out

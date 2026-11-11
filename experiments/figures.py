"""Membuat gambar untuk laporan & artikel dari folder results/."""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from smartroute.data import BASELINE_ROUTES, build_instance  # noqa: E402

RES = os.path.join(ROOT, "results")
FIG = os.path.join(ROOT, "figures")
os.makedirs(FIG, exist_ok=True)
plt.rcParams.update({"font.size": 10, "figure.dpi": 150, "savefig.bbox": "tight", "font.family": "DejaVu Sans"})
C3 = {"GA": "#7f7f7f", "GA-SA": "#1f77b4", "GA-SA-RL": "#d62728"}


def J(name):
    p = os.path.join(RES, name)
    return json.load(open(p)) if os.path.exists(p) else None


def save(fig, name):
    fig.savefig(os.path.join(FIG, name)); plt.close(fig); print("saved", name)


def fig_map():
    inst = build_instance()
    C = inst.coords
    e2 = J("E2_summary.json")
    panels = [("(a) Saving Matrix (baseline capstone)", [list(r) for r in BASELINE_ROUTES])]
    if e2:
        lab = {l: i for i, l in enumerate(inst.labels)}
        rts = [[lab[x] for x in t["rute"].split("-")] for t in e2["multiproduk"]["best_trips"]]
        panels.append(("(b) GA-SA-RL, MC-MP-MT-VRP (multi-produk)", rts))
    fig, axes = plt.subplots(1, len(panels), figsize=(6 * len(panels), 5))
    axes = np.atleast_1d(axes)
    cols = plt.cm.tab10.colors
    for ax, (title, routes) in zip(axes, panels):
        for k, r in enumerate(routes):
            idx = [0] + r + [0]
            ax.plot(C[idx, 1], C[idx, 0], "-o", color=cols[k % 10], lw=2, ms=4,
                    label="R%d: %s" % (k + 1, "-".join(inst.labels[i] for i in r)))
        ax.scatter(C[0, 1], C[0, 0], s=180, marker="*", c="red", zorder=5)
        ax.annotate("FT Gelumbang", (C[0, 1], C[0, 0]), xytext=(4, 6), textcoords="offset points", fontsize=8)
        for i in range(1, inst.n + 1):
            ax.annotate(inst.labels[i], (C[i, 1], C[i, 0]), xytext=(3, 3), textcoords="offset points", fontsize=7)
        ax.set_title(title); ax.set_xlabel("Bujur"); ax.set_ylabel("Lintang")
        ax.legend(fontsize=7, loc="lower right"); ax.grid(alpha=.3)
    save(fig, "fig01_peta_rute.png")


def fig_e1():
    df = pd.read_csv(os.path.join(RES, "E1_runs.csv")) if os.path.exists(os.path.join(RES, "E1_runs.csv")) else None
    s = J("E1_summary.json")
    if df is None or s is None:
        return
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    order = ["GA", "GA-SA", "GA-SA-RL"]
    ax[0].boxplot([df[df.variant == v].dist for v in order], tick_labels=order)
    ax[0].axhline(s["baseline_capstone"], color="orange", ls="--", label=f"Saving Matrix {s['baseline_capstone']:.1f} km")
    ax[0].axhline(s["milp_opt"], color="green", ls=":", label=f"Optimum MILP {s['milp_opt']:.1f} km")
    ax[0].axhline(s["nn"], color="gray", ls="-.", label=f"Nearest Neighbour {s['nn']:.1f} km")
    ax[0].set_ylabel("Total jarak (km)"); ax[0].set_title("(a) 30 replikasi, setting capstone"); ax[0].legend(fontsize=8)
    names = ["Direct\ndelivery", "Nearest\nNeighbour", "Saving Matrix\n(capstone)", "Clarke-Wright\n(re-impl.)",
             "GA-SA-RL\n(rerata 30)", "Optimum\nMILP"]
    vals = [s["direct"], s["nn"], s["baseline_capstone"], s["cw_reimpl"], s["stats"]["GA-SA-RL"]["mean"], s["milp_opt"]]
    cols = ["#bbbbbb", "#999999", "orange", "#ffbb78", "#d62728", "green"]
    b = ax[1].bar(range(len(vals)), vals, color=cols)
    for i, v in enumerate(vals):
        ax[1].text(i, v + 8, f"{v:.1f}".replace(".", ","), ha="center", fontsize=8)
    ax[1].set_xticks(range(len(vals))); ax[1].set_xticklabels(names, fontsize=7)
    ax[1].set_ylabel("Total jarak (km)"); ax[1].set_title("(b) Perbandingan metode")
    ax[1].set_ylim(0, max(vals) * 1.12)
    save(fig, "fig02_validasi_capstone.png")


def fig_e2():
    for key in ["multiproduk", "agregat"]:
        p = os.path.join(RES, f"E2_runs_{key}.csv")
        if not os.path.exists(p):
            continue
        df = pd.read_csv(p)
        s = J("E2_summary.json")[key]
        order = ["GA", "GA-SA", "GA-SA-RL"]
        fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
        for a, col, lab in zip(ax, ["fitness", "co2_kg", "cost_rp"], ["Fitness tertimbang", "Emisi CO$_2$ (kg/hari)", "Biaya (Rp/hari)"]):
            a.boxplot([df[df.variant == v][col] for v in order], tick_labels=order)
            b = s["baseline"][col]
            if s["baseline"]["unassigned"] == 0 or col != "fitness":
                a.axhline(b, color="orange", ls="--", label="Saving Matrix" + (" (tidak layak)" if s["baseline"]["unassigned"] else ""))
                a.legend(fontsize=8)
            a.set_title(lab)
        fig.suptitle(f"Model lengkap MC-MP-MT-VRP ({key}), 30 replikasi per varian")
        save(fig, f"fig03_e2_{key}.png")


def fig_e3():
    p = os.path.join(RES, "E3_pareto.csv")
    if not os.path.exists(p):
        return
    df = pd.read_csv(p)
    df = df[df.unassigned == 0]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].scatter(df.cost_rp / 1e6, df.co2_kg, c="lightgray", s=15, label="solusi (sapuan bobot)")
    pf = df[df.pareto_cost_co2].sort_values("cost_rp")
    ax[0].plot(pf.cost_rp / 1e6, pf.co2_kg, "o-", color="#d62728", label="Pareto front biaya-emisi")
    pb = os.path.join(RES, "E3b_pareto.csv")
    if os.path.exists(pb):
        db = pd.read_csv(pb); db = db[db.unassigned == 0]
        ax[0].scatter(db.cost_rp / 1e6, db.co2_kg, c="#aec7e8", s=12, marker="^")
        pfb = db[db.pareto_cost_co2].sort_values("cost_rp")
        ax[0].plot(pfb.cost_rp / 1e6, pfb.co2_kg, "s-", color="#1f77b4", label="armada diperluas (E3b)")
    pc = os.path.join(RES, "E3c_pareto.csv")
    if os.path.exists(pc):
        dc = pd.read_csv(pc); dc = dc[dc.unassigned == 0]
        ax[0].scatter(dc.cost_rp / 1e6, dc.co2_kg, c="#98df8a", s=12, marker="v")
        pfc = dc[dc.pareto_cost_co2].sort_values("cost_rp")
        ax[0].plot(pfc.cost_rp / 1e6, pfc.co2_kg, "D-", color="#2ca02c", label="armada diperluas, jalan legal-truk (E3c)")
    ax[0].set_xlabel("Biaya distribusi (juta Rp/hari)"); ax[0].set_ylabel("Emisi CO$_2$ (kg/hari)"); ax[0].legend()
    ax[0].set_title("(a) Trade-off biaya vs emisi")
    s = os.path.join(RES, "E3_sens_fixedcost.csv")
    if os.path.exists(s):
        d = pd.read_csv(s).groupby("fixed_cost_mult").mean(numeric_only=True)
        ax[1].plot(d.index, d.dist_km, "o-", label="jarak (km)")
        ax2 = ax[1].twinx(); ax2.plot(d.index, d.trucks, "s--", color="green", label="truk")
        ax[1].set_xlabel("Pengali biaya tetap truk"); ax[1].set_ylabel("Jarak (km)"); ax2.set_ylabel("Jumlah truk")
        ax[1].set_title("(b) Sensitivitas biaya tetap")
    save(fig, "fig04_pareto.png")


def fig_e5():
    p = os.path.join(RES, "E5_dynamic.csv")
    if not os.path.exists(p):
        return
    df = pd.read_csv(p)
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    for a, col, lab in zip(ax, ["fitness", "late_min"], ["Fitness residual", "Keterlambatan tertimbang (menit)"]):
        g = df.groupby("event")[[f"naive_{col}", f"reopt_{col}"]].mean()
        g.columns = ["Tanpa re-routing", "Re-optimasi GA-SA-RL"]
        g.plot.bar(ax=a, rot=0); a.set_title(lab)
    save(fig, "fig05_dinamis.png")


def fig_e6():
    p = os.path.join(RES, "E6_montecarlo.csv")
    if not os.path.exists(p):
        return
    df = pd.read_csv(p)
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    for a, key in zip(ax, ["agregat", "multiproduk"]):
        d = df[df.produk == key]
        for plan, g in d.groupby("plan"):
            a.plot(g.cv, g.service_level * 100, "o-", label=plan)
        a.set_xlabel("Koefisien variasi permintaan"); a.set_ylabel("Service level (%)"); a.set_title(key); a.legend(fontsize=8)
    save(fig, "fig06_montecarlo.png")


def fig_e7():
    p = os.path.join(RES, "E7_cvrplib.csv")
    if not os.path.exists(p):
        return
    df = pd.read_csv(p)
    d = df[df.variant == "GA-SA-RL"].groupby("instance").agg(gap=("gap_pct", "mean"), sd=("gap_pct", "std"),
                                                              cw=("cw_gap_pct", "first"))
    fig, ax = plt.subplots(figsize=(10, 3.8))
    x = np.arange(len(d))
    ax.bar(x - 0.2, d.cw, 0.4, label="Clarke-Wright", color="orange")
    ax.bar(x + 0.2, d.gap, 0.4, yerr=d.sd, label="GA-SA-RL (rerata ± SD)", color="#d62728")
    ax.set_xticks(x); ax.set_xticklabels(d.index, rotation=30); ax.set_ylabel("Gap terhadap BKS (%)")
    ax.legend(); ax.set_title("Validasi CVRPLIB set X (Uchoa et al., 2017)")
    save(fig, "fig07_cvrplib.png")


def fig_alur():
    """Diagram alir Hybrid GA-SA-RL + DSS."""
    from matplotlib.patches import FancyBboxPatch
    fig, ax = plt.subplots(figsize=(10, 5.2)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 6)
    def box(x, y, w, h, t, c):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", fc=c, ec="k", lw=0.8))
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=8)
    def arr(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", lw=1))
    box(0.1, 4.6, 2.2, 1.1, "Google Sheets / CSV\nSPBU, jarak, armada,\nproduk", "#e8f0fe")
    box(0.1, 2.9, 2.2, 1.1, "Skenario what-if\n(10 kategori)", "#e8f0fe")
    box(0.1, 1.2, 2.2, 1.1, "Fuzzy Mamdani\nprioritas SPBU", "#e8f0fe")
    box(3.0, 4.6, 2.2, 1.1, "GA: populasi permutasi\nturnamen, OX, mutasi\nadaptif, elitisme", "#fde8e8")
    box(3.0, 2.9, 2.2, 1.1, "SA: T0=1000, a=0,995\nE = 1e6 F/F_GA", "#fde8e8")
    box(3.0, 1.2, 2.2, 1.1, "Q-Learning: pilih 1 dari\n5 operator (2-opt, relocate,\nswap, or-opt, seg-swap)", "#fde8e8")
    box(6.0, 3.6, 2.3, 1.6, "Evaluator\nSplit heterogen +\nkelayakan kompartemen\n+ penjadwalan multi-ritase\n(time-dependent)", "#e6f4ea")
    box(6.0, 1.2, 2.3, 1.4, "Z1 biaya, Z2 CO2 (IPCC),\nZ3 waktu + penalti\n-> fitness ternormalisasi", "#e6f4ea")
    box(8.6, 2.6, 1.3, 1.8, "Keluaran DSS\npeta, Gantt,\nKPI, log,\nTelegram", "#fff4e5")
    arr(2.3, 5.15, 3.0, 5.15); arr(2.3, 3.45, 3.0, 3.45); arr(2.3, 1.75, 3.0, 1.75)
    arr(4.1, 4.6, 4.1, 4.0); arr(4.1, 2.3, 4.1, 2.9); arr(5.2, 5.15, 6.0, 4.6); arr(5.2, 3.45, 6.0, 4.0)
    arr(7.15, 3.6, 7.15, 2.6); arr(8.3, 4.4, 8.6, 3.8); arr(8.3, 1.9, 8.6, 2.8)
    ax.text(4.1, 0.75, "imbalan = perbaikan relatif (+1 bila solusi terbaik baru)", ha="center", fontsize=7, style="italic")
    save(fig, "fig00_alur.png")


def fig_e4():
    s = J("E4_scenarios.json")
    if not s:
        return
    rows = [(k, v) for k, v in s.items() if "hybrid" in v]
    lab = [k.split(". ", 1)[0] + ". " + k.split(". ", 1)[1][:22] for k, _ in rows]
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2))
    y = np.arange(len(rows))
    ax[0].barh(y, [v["hybrid"]["cost_rp"] / 1e6 for _, v in rows], color="#1f77b4")
    ax[0].set_yticks(y); ax[0].set_yticklabels(lab, fontsize=8); ax[0].invert_yaxis()
    ax[0].set_xlabel("Biaya (juta Rp/hari)"); ax[0].set_title("(a) Biaya GA-SA-RL per skenario")
    ax[1].barh(y, [v["hybrid"]["co2_kg"] for _, v in rows], color="#2ca02c")
    for i, (_, v) in enumerate(rows):
        if v["hybrid"]["unassigned"]:
            ax[1].text(v["hybrid"]["co2_kg"], i, "  %d ritase tak terlayani" % v["hybrid"]["unassigned"], va="center", fontsize=7, color="red")
    ax[1].set_yticks(y); ax[1].set_yticklabels([]); ax[1].invert_yaxis()
    ax[1].set_xlabel("Emisi CO$_2$ (kg/hari)"); ax[1].set_title("(b) Emisi per skenario")
    save(fig, "fig08_skenario.png")


def fig_osm(lang="id", out=None):
    """Jaringan jalan OSM: ruas legal per tipe truk + rute terbaik E8 (jalan nyata)."""
    EN = lang == "en"
    import csv as _csv
    from smartroute import roadnet as R
    kelas, jalan = R.load_rules()
    arm = {r["tipe"]: r for r in _csv.DictReader(open(os.path.join(ROOT, "data", "armada.csv")))}
    idx, ll, ways = R.parse_osm(R.load_osm())
    inst = build_instance(road="osm")
    C = inst.coords
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6))
    ax = axes[0]
    layers = [("not legal for B/C/D" if EN else "tidak legal untuk B/C/D", "#d9d9d9", 0.5),
              ("legal for B & C (class II)" if EN else "legal B & C (kelas II)", "#1f77b4", 1.2),
              ("legal for D (class I)" if EN else "legal D (kelas I)", "#d62728", 1.8)]
    for _, nds, tags in ways:
        s_ = [idx[n] for n in nds if n in idx]
        if len(s_) < 2:
            continue
        okC = R.edge_allowed(tags, arm["C"], R.truck_class_required(arm["C"], kelas), jalan)[0]
        okD = R.edge_allowed(tags, arm["D"], R.truck_class_required(arm["D"], kelas), jalan)[0]
        lay = layers[2] if okD else layers[1] if okC else layers[0]
        ax.plot(ll[s_, 1], ll[s_, 0], color=lay[1], lw=lay[2], zorder=2 if okC else 1)
    for name, col, lw in layers:
        ax.plot([], [], color=col, lw=lw * 2, label=name)
    ax.scatter(C[1:, 1], C[1:, 0], s=25, c="k", zorder=5, label="station" if EN else "SPBU")
    ax.scatter(C[0, 1], C[0, 0], s=160, marker="*", c="orange", ec="k", zorder=6, label="FT Gelumbang")
    for i in range(1, inst.n + 1):
        ax.annotate(inst.labels[i], (C[i, 1], C[i, 0]), xytext=(3, 3), textcoords="offset points", fontsize=7)
    ax.set_title("(a) Truck-legal OSM links by truck type" if EN else "(a) Ruas OSM legal per tipe truk")
    ax.set_xlabel("Longitude" if EN else "Bujur"); ax.set_ylabel("Latitude" if EN else "Lintang")
    ax.legend(fontsize=7, loc="lower right"); ax.set_aspect("equal")
    ax = axes[1]
    e8 = J("E8_summary.json")
    geom = R.load_geometry()
    if e8:
        trips = e8["eksisting_multiproduk"]["osm"]["best_trips"]
        cols = plt.cm.tab10.colors
        for k, t in enumerate(trips):
            seq = ["FT"] + t["rute"].split("-") + ["FT"]
            poly = R.route_polyline(geom, t["tipe"], seq)
            if poly:
                P = np.array(poly)
                ax.plot(P[:, 1], P[:, 0], color=cols[k % 10], lw=2,
                        label=f"{t['tipe']}-{t['unit']} R{t['ritase']}: {t['rute']} ({t['jarak_km']:.1f} km)")
        ax.legend(fontsize=7, loc="lower right")
    ax.scatter(C[1:, 1], C[1:, 0], s=25, c="k", zorder=5)
    ax.scatter(C[0, 1], C[0, 0], s=160, marker="*", c="orange", ec="k", zorder=6)
    for i in range(1, inst.n + 1):
        ax.annotate(inst.labels[i], (C[i, 1], C[i, 0]), xytext=(3, 3), textcoords="offset points", fontsize=7)
    ax.set_title("(b) GA-SA-RL routes on truck-legal roads" if EN else "(b) Rute GA-SA-RL pada jalan legal-truk")
    ax.set_xlabel("Longitude" if EN else "Bujur"); ax.set_aspect("equal")
    fig.tight_layout()
    if out:
        fig.savefig(out, dpi=300); plt.close(fig); print("saved", out)
    else:
        save(fig, "fig09_osm_legal.png")


if __name__ == "__main__":
    for f in [fig_alur, fig_e4, fig_osm, fig_map, fig_e1, fig_e2, fig_e3, fig_e5, fig_e6, fig_e7]:
        try:
            f()
        except Exception as e:  # tetap lanjut
            print("gagal", f.__name__, e)

"""English-language figures for the journal manuscript (same data as figures.py)."""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from experiments.figures import C3, FIG, RES, J, plt  # noqa: E402
from smartroute.data import BASELINE_ROUTES, build_instance  # noqa: E402

OUT = os.path.join(FIG, "en")
os.makedirs(OUT, exist_ok=True)


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=300); plt.close(fig); print("saved en/", name)


def fig_framework():
    from matplotlib.patches import FancyBboxPatch
    fig, ax = plt.subplots(figsize=(10, 5.0)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0.5, 6)

    def box(x, y, w, h, t, c):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", fc=c, ec="k", lw=0.8))
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=8)

    def arr(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", lw=1))
    box(0.1, 4.6, 2.2, 1.1, "Google Sheets / CSV\nstations, distances,\nfleet, products", "#e8f0fe")
    box(0.1, 2.9, 2.2, 1.1, "What-if scenarios\n(10 categories)", "#e8f0fe")
    box(0.1, 1.2, 2.2, 1.1, "Mamdani fuzzy\nstation priority", "#e8f0fe")
    box(3.0, 4.6, 2.2, 1.1, "GA: permutation population,\ntournament, OX, adaptive\nmutation, elitism", "#fde8e8")
    box(3.0, 2.9, 2.2, 1.1, "SA: T0 = 1000, a = 0.995\nE = 1e6 F / F_GA", "#fde8e8")
    box(3.0, 1.2, 2.2, 1.1, "Q-learning selects 1 of 5\nmoves (2-opt, relocate,\nswap, or-opt, seg-swap)", "#fde8e8")
    box(6.0, 3.6, 2.3, 1.6, "Evaluator\nheterogeneous Split +\nexact compartment check\n+ multi-trip scheduling\n(time-dependent)", "#e6f4ea")
    box(6.0, 1.2, 2.3, 1.4, "Z1 cost, Z2 CO2 (IPCC),\nZ3 time + penalties\n-> normalised fitness", "#e6f4ea")
    box(8.6, 2.6, 1.3, 1.8, "DSS output\nmap, Gantt,\nKPIs, audit log,\nTelegram", "#fff4e5")
    arr(2.3, 5.15, 3.0, 5.15); arr(2.3, 3.45, 3.0, 3.45); arr(2.3, 1.75, 3.0, 1.75)
    arr(4.1, 4.6, 4.1, 4.0); arr(4.1, 2.3, 4.1, 2.9); arr(5.2, 5.15, 6.0, 4.6); arr(5.2, 3.45, 6.0, 4.0)
    arr(7.15, 3.6, 7.15, 2.6); arr(8.3, 4.4, 8.6, 3.8); arr(8.3, 1.9, 8.6, 2.8)
    ax.text(4.1, 0.8, "reward = relative improvement (+1 for a new best)", ha="center", fontsize=7, style="italic")
    save(fig, "fig1_framework.png")


def fig_routes():
    inst = build_instance()
    C = inst.coords
    e2 = J("E2_summary.json")
    panels = [("(a) Savings plan (capstone baseline)", [list(r) for r in BASELINE_ROUTES])]
    if e2:
        lab = {l: i for i, l in enumerate(inst.labels)}
        panels.append(("(b) GA-SA-RL, multi-product MC-MP-MT-VRP",
                       [[lab[x] for x in t["rute"].split("-")] for t in e2["multiproduk"]["best_trips"]]))
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
        ax.set_title(title); ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
        ax.legend(fontsize=7, loc="lower right"); ax.grid(alpha=.3)
    save(fig, "fig2_routes.png")


def fig_validation():
    s = J("E1_summary.json")
    if s is None:
        return
    names = ["Direct", "Nearest\nNeighbour", "Savings\n(capstone)", "Clarke-Wright\n(re-impl.)", "GA-SA-RL\n(mean of 30)",
             "MILP\noptimum"]
    vals = [s["direct"], s["nn"], s["baseline_capstone"], s["cw_reimpl"], s["stats"]["GA-SA-RL"]["mean"], s["milp_opt"]]
    cols = ["#bbbbbb", "#999999", "orange", "#ffbb78", "#d62728", "green"]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.bar(range(len(vals)), vals, color=cols)
    for i, v in enumerate(vals):
        ax.text(i, v + 8, f"{v:.1f}", ha="center", fontsize=8)
    ax.set_xticks(range(len(vals))); ax.set_xticklabels(names, fontsize=8)
    ax.set_ylabel("Total distance (km)"); ax.set_ylim(0, max(vals) * 1.12)
    save(fig, "fig3_validation.png")


def fig_e2():
    p = os.path.join(RES, "E2_runs_multiproduk.csv")
    if not os.path.exists(p):
        return
    df = pd.read_csv(p)
    s = J("E2_summary.json")["multiproduk"]
    order = ["GA", "GA-SA", "GA-SA-RL"]
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.6))
    for a, col, lab in zip(ax, ["fitness", "co2_kg", "cost_rp"], ["Weighted fitness", "CO$_2$ (kg/day)", "Cost (IDR/day)"]):
        a.boxplot([df[df.variant == v][col] for v in order], tick_labels=order)
        if col != "fitness":
            a.axhline(s["baseline"][col], color="orange", ls="--", label="Savings plan (infeasible)" if s["baseline"]["unassigned"] else "Savings plan")
            a.legend(fontsize=7)
        a.set_title(lab)
    save(fig, "fig4_ablation_case.png")


def fig_pareto():
    p = os.path.join(RES, "E3_pareto.csv")
    if not os.path.exists(p):
        return
    df = pd.read_csv(p)
    df = df[df.unassigned == 0]
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.8))
    ax[0].scatter(df.cost_rp / 1e6, df.co2_kg, c="lightgray", s=15, label="weight-sweep solutions")
    pf = df[df.pareto_cost_co2].sort_values("cost_rp")
    ax[0].plot(pf.cost_rp / 1e6, pf.co2_kg, "o-", color="#d62728", label="cost–CO$_2$ Pareto front")
    pb = os.path.join(RES, "E3b_pareto.csv")
    if os.path.exists(pb):
        db = pd.read_csv(pb); db = db[db.unassigned == 0]
        ax[0].scatter(db.cost_rp / 1e6, db.co2_kg, c="#aec7e8", s=12, marker="^")
        pfb = db[db.pareto_cost_co2].sort_values("cost_rp")
        ax[0].plot(pfb.cost_rp / 1e6, pfb.co2_kg, "s-", color="#1f77b4", label="extended fleet (E3b)")
    ax[0].set_xlabel("Cost (million IDR/day)"); ax[0].set_ylabel("CO$_2$ (kg/day)"); ax[0].legend(fontsize=8)
    ax[0].set_title("(a) Cost–emission trade-off")
    s = os.path.join(RES, "E3_sens_fixedcost.csv")
    if os.path.exists(s):
        d = pd.read_csv(s).groupby("fixed_cost_mult").mean(numeric_only=True)
        ax[1].plot(d.index, d.dist_km, "o-", label="distance (km)")
        ax2 = ax[1].twinx(); ax2.plot(d.index, d.trucks, "s--", color="green", label="trucks")
        ax[1].set_xlabel("Truck fixed-cost multiplier"); ax[1].set_ylabel("Distance (km)"); ax2.set_ylabel("Trucks used")
        ax[1].set_title("(b) Sensitivity to truck fixed cost")
    save(fig, "fig5_pareto.png")


def fig_cvrplib():
    p = os.path.join(RES, "E7_cvrplib.csv")
    if not os.path.exists(p):
        return
    df = pd.read_csv(p)
    d = df[df.variant == "GA-SA-RL"].groupby("instance").agg(gap=("gap_pct", "mean"), sd=("gap_pct", "std"),
                                                              cw=("cw_gap_pct", "first"))
    fig, ax = plt.subplots(figsize=(10, 3.6))
    x = np.arange(len(d))
    ax.bar(x - 0.2, d.cw, 0.4, label="Clarke-Wright", color="orange")
    ax.bar(x + 0.2, d.gap, 0.4, yerr=d.sd, label="GA-SA-RL (mean ± SD, 10 runs)", color="#d62728")
    ax.set_xticks(x); ax.set_xticklabels(d.index, rotation=30); ax.set_ylabel("Gap to BKS (%)")
    ax.legend()
    save(fig, "fig6_cvrplib.png")


if __name__ == "__main__":
    for f in [fig_framework, fig_routes, fig_validation, fig_e2, fig_pareto, fig_cvrplib]:
        try:
            f()
        except Exception as e:
            print("failed", f.__name__, e)

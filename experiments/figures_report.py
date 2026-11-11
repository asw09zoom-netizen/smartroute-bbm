"""Gambar Laporan Akhir (lebar cetak 14 cm, huruf serif) dari folder results/ dan tangkapan layar aplikasi.

Jalankan: python -m experiments.figures_report [folder_tangkapan_layar]
Keluaran: figures/laporan/*.png
"""
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
OUT = os.path.join(ROOT, "figures", "laporan")
os.makedirs(OUT, exist_ok=True)
W = 6.3  # inci; dicetak 14 cm (5,5 in) -> huruf 9 pt tampil sekitar 8 pt
plt.rcParams.update({"font.size": 9, "figure.dpi": 220, "savefig.dpi": 220, "savefig.bbox": "tight",
                     "font.family": "serif", "font.serif": ["Liberation Serif", "Times New Roman", "DejaVu Serif"],
                     "mathtext.fontset": "stix", "axes.titlesize": 9, "legend.fontsize": 7.5,
                     "axes.spines.top": False, "axes.spines.right": False})
C3 = {"GA": "#8c8c8c", "GA-SA": "#1f77b4", "GA-SA-ALNS": "#2e8b57", "GA-SA-RL": "#c0392b"}
ORDER = ["GA", "GA-SA", "GA-SA-ALNS", "GA-SA-RL"]
TICKS = ["GA", "GA-SA", "GA-SA-\nALNS", "GA-SA-\nRL"]


def J(name):
    p = os.path.join(RES, name)
    return json.load(open(p)) if os.path.exists(p) else None


def C(name):
    p = os.path.join(RES, name)
    return pd.read_csv(p) if os.path.exists(p) else None


def save(fig, name):
    fig.savefig(os.path.join(OUT, name)); plt.close(fig); print("saved", name)


def idn(x, d=1):
    s = f"{x:,.{d}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


# ---------------------------------------------------------------------------
def fig_alur():
    from matplotlib.patches import FancyBboxPatch
    fig, ax = plt.subplots(figsize=(W, 3.6)); ax.axis("off"); ax.set_xlim(-0.15, 10.15); ax.set_ylim(0.75, 6.3)

    def box(x, y, w, h, t, c):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04", fc=c, ec="k", lw=0.7))
        ax.text(x + w / 2, y + h / 2, t, ha="center", va="center", fontsize=7.2)

    def arr(x1, y1, x2, y2):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", lw=0.8, color="k"))
    box(0.0, 4.9, 2.4, 1.2, "Basis data\nGoogle Sheets / CSV\nSPBU, armada, produk", "#e8f0fe")
    box(0.0, 3.2, 2.4, 1.2, "Jaringan jalan OSM\nlegal per tipe truk\n(kelas, rambu, lebar)", "#e8f0fe")
    box(0.0, 1.5, 2.4, 1.2, "Skenario what-if\n& prioritas fuzzy", "#e8f0fe")
    box(3.0, 4.9, 2.4, 1.2, "GA: permutasi,\nturnamen, OX,\nmutasi adaptif", "#fdecea")
    box(3.0, 3.2, 2.4, 1.2, "SA: T$_0$ = 1000\n$\\alpha$ = 0,995; 5000 iterasi", "#fdecea")
    box(3.0, 1.5, 2.4, 1.2, "Q-Learning memilih\n1 dari 5 operator SA", "#fdecea")
    box(6.0, 3.6, 2.2, 2.5, "Evaluator\nSplit heterogen\n+ kompartemen\n+ penjadwalan\nmulti-ritase", "#e6f4ea")
    box(6.0, 1.5, 2.2, 1.6, "Z$_1$ biaya, Z$_2$ CO$_2$,\nZ$_3$ waktu, penalti\n→ fitness", "#e6f4ea")
    box(8.6, 1.5, 1.4, 4.6, "DSS web\npeta rute\nGantt\nsimulasi\n3D\nKPI & log", "#fff4e5")
    for y in (5.5, 3.8, 2.1):
        arr(2.4, y, 3.0, y)
    arr(4.2, 4.9, 4.2, 4.4); arr(4.2, 2.7, 4.2, 3.2)
    arr(5.4, 5.5, 6.0, 5.2); arr(5.4, 3.8, 6.0, 4.2)
    arr(7.1, 3.6, 7.1, 3.1); arr(8.2, 4.8, 8.6, 4.8); arr(8.2, 2.3, 8.6, 2.3)
    ax.text(4.2, 1.05, "imbalan = perbaikan relatif; +1 bila solusi terbaik baru", ha="center", fontsize=6.8, style="italic")
    save(fig, "L01_arsitektur.png")


def fig_prosedur():
    from matplotlib.patches import FancyBboxPatch
    steps = ["Pengumpulan data capstone\n(13 SPBU, matriks 14×14, armada)",
             "Unduh jaringan jalan OSM; saring ruas\nlegal per tipe truk (UU 22/2009)",
             "Formulasi MC-MP-MT-VRP\n(persamaan 1–14)",
             "Implementasi Hybrid GA-SA-RL\n+ kalibrasi skala energi SA",
             "Validasi: MILP optimum, CVRPLIB,\nuji unit perangkat lunak",
             "Eksperimen E1–E10\n(30 replikasi, uji statistik)",
             "Prototipe DSS web + simulasi\npergerakan truk; uji fungsional",
             "Analisis, pembahasan,\ndan penyusunan luaran"]
    fig, ax = plt.subplots(figsize=(W, 5.0)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 10)
    pos = [(0.3, 8.2), (0.3, 6.0), (0.3, 3.8), (0.3, 1.6), (5.4, 1.6), (5.4, 3.8), (5.4, 6.0), (5.4, 8.2)]
    for k, ((x, y), t) in enumerate(zip(pos, steps)):
        ax.add_patch(FancyBboxPatch((x, y), 4.3, 1.5, boxstyle="round,pad=0.05", fc="#f2f2f2" if k % 2 else "#e8f0fe",
                                    ec="k", lw=0.7))
        ax.text(x + 2.15, y + 0.75, f"{k + 1}. {t}", ha="center", va="center", fontsize=7.4)
    for a, b in zip(pos[:-1], pos[1:]):
        if a[0] == b[0]:
            y1, y2 = (a[1], b[1] + 1.5) if b[1] < a[1] else (a[1] + 1.5, b[1])
            ax.annotate("", xy=(a[0] + 2.15, y2), xytext=(a[0] + 2.15, y1), arrowprops=dict(arrowstyle="-|>", lw=0.8))
        else:
            ax.annotate("", xy=(b[0], b[1] + 0.75), xytext=(a[0] + 4.3, a[1] + 0.75), arrowprops=dict(arrowstyle="-|>", lw=0.8))
    save(fig, "L02_prosedur.png")


def fig_e1():
    df, s = C("E1_runs.csv"), J("E1_summary.json")
    if df is None or s is None:
        return
    fig, ax = plt.subplots(1, 2, figsize=(W, 2.9), gridspec_kw=dict(width_ratios=[1, 1.25]))
    ax[0].boxplot([df[df.variant == v].dist for v in ORDER], tick_labels=TICKS, widths=0.5)
    ax[0].axhline(s["baseline_capstone"], color="#e67e22", ls="--", lw=1, label="Saving Matrix")
    ax[0].axhline(s["milp_opt"], color="#27ae60", ls=":", lw=1.2, label="Optimum MILP")
    ax[0].set_ylabel("Total jarak (km)"); ax[0].set_title("(a) 30 replikasi per varian"); ax[0].legend(loc="center right")
    ax[0].set_ylim(s["milp_opt"] - 4, s["baseline_capstone"] + 4)
    names = ["Direct", "NN", "Saving\nMatrix", "CW\n(ulang)", "GA-SA-RL", "MILP"]
    vals = [s["direct"], s["nn"], s["baseline_capstone"], s["cw_reimpl"], s["stats"]["GA-SA-RL"]["mean"], s["milp_opt"]]
    cols = ["#bdbdbd", "#969696", "#e67e22", "#f5b041", "#c0392b", "#27ae60"]
    ax[1].bar(range(len(vals)), vals, color=cols)
    for i, v in enumerate(vals):
        ax[1].text(i, v + 10, idn(v), ha="center", fontsize=7)
    ax[1].set_xticks(range(len(vals))); ax[1].set_xticklabels(names, fontsize=7.5)
    ax[1].set_ylabel("Total jarak (km)"); ax[1].set_title("(b) Perbandingan metode"); ax[1].set_ylim(0, max(vals) * 1.12)
    fig.tight_layout()
    save(fig, "L10_e1_validasi.png")


def fig_e2():
    s = J("E2_summary.json")
    fig, axes = plt.subplots(2, 3, figsize=(W, 4.4))
    for r, key in enumerate(["agregat", "multiproduk"]):
        df = C(f"E2_runs_{key}.csv")
        for a, col, lab in zip(axes[r], ["fitness", "cost_rp", "co2_kg"], ["Fitness", "Biaya (juta Rp/hari)", "CO$_2$ (kg/hari)"]):
            sc = 1e6 if col == "cost_rp" else 1
            a.boxplot([df[df.variant == v][col] / sc for v in ORDER], tick_labels=TICKS, widths=0.5)
            b = s[key]["baseline"]
            if b["unassigned"] == 0 or col != "fitness":
                a.axhline(b[col] / sc, color="#e67e22", ls="--", lw=1)
            a.set_title(f"{'(a)' if r == 0 else '(b)'} {key}: {lab}", fontsize=8)
            a.tick_params(labelsize=7)
    fig.tight_layout()
    save(fig, "L11_e2_replikasi.png")


def fig_osm():
    import csv as _csv
    from smartroute import roadnet as R
    kelas, jalan = R.load_rules()
    arm = {r["tipe"]: r for r in _csv.DictReader(open(os.path.join(ROOT, "data", "armada.csv")))}
    idx, ll, ways = R.parse_osm(R.load_osm())
    inst = build_instance(road="osm")
    Cc = inst.coords
    fig, axes = plt.subplots(1, 2, figsize=(W, 3.6))
    ax = axes[0]
    layers = [("tidak legal B/C/D", "#d9d9d9", 0.35), ("legal B & C (kelas II)", "#2e86c1", 0.8), ("legal D (kelas I)", "#c0392b", 1.2)]
    for _, nds, tags in ways:
        s_ = [idx[n] for n in nds if n in idx]
        if len(s_) < 2:
            continue
        okC = R.edge_allowed(tags, arm["C"], R.truck_class_required(arm["C"], kelas), jalan)[0]
        okD = R.edge_allowed(tags, arm["D"], R.truck_class_required(arm["D"], kelas), jalan)[0]
        lay = layers[2] if okD else layers[1] if okC else layers[0]
        ax.plot(ll[s_, 1], ll[s_, 0], color=lay[1], lw=lay[2], zorder=2 if okC else 1)
    for name, col, lw in layers:
        ax.plot([], [], color=col, lw=lw * 2.5, label=name)
    ax.scatter(Cc[1:, 1], Cc[1:, 0], s=10, c="k", zorder=5, label="SPBU")
    ax.scatter(Cc[0, 1], Cc[0, 0], s=70, marker="*", c="orange", ec="k", lw=0.5, zorder=6, label="FT Gelumbang")
    ax.set_title("(a) Ruas OSM legal per tipe truk"); ax.set_aspect("equal")
    ax.legend(fontsize=6, loc="lower right"); ax.tick_params(labelsize=6.5)
    ax = axes[1]
    e8 = J("E8_summary.json")
    geom = R.load_geometry()
    cols = ["#8e44ad", "#16a085", "#2e86c1", "#f39c12", "#e74c3c", "#7f8c8d"]
    if e8:
        for k, t in enumerate(e8["eksisting_multiproduk"]["osm"]["best_trips"]):
            seq = ["FT"] + t["rute"].split("-") + ["FT"]
            poly = R.route_polyline(geom, t["tipe"], seq)
            if poly:
                P = np.array(poly)
                ax.plot(P[:, 1], P[:, 0], color=cols[k % 6], lw=1.3,
                        label=f"{t['tipe']}-{t['unit']} R{t['ritase']}: {t['rute']}")
    ax.scatter(Cc[1:, 1], Cc[1:, 0], s=10, c="k", zorder=5)
    ax.scatter(Cc[0, 1], Cc[0, 0], s=70, marker="*", c="orange", ec="k", lw=0.5, zorder=6)
    for i in range(1, inst.n + 1):
        ax.annotate(inst.labels[i], (Cc[i, 1], Cc[i, 0]), xytext=(2, 2), textcoords="offset points", fontsize=5.5)
    ax.set_title("(b) Rute GA-SA-RL pada jalan legal-truk"); ax.set_aspect("equal")
    ax.legend(fontsize=5.8, loc="lower right"); ax.tick_params(labelsize=6.5)
    fig.tight_layout()
    save(fig, "L12_osm_legal.png")


def _pareto(df):
    df = df[df.unassigned == 0]
    return df, df[df.pareto_cost_co2].sort_values("cost_rp")


def fig_e3():
    fig, ax = plt.subplots(1, 2, figsize=(W, 2.9))
    for name, f, mk, col, lab in [("E3", "E3_pareto.csv", "o", "#c0392b", "armada eksisting"),
                                  ("E3b", "E3b_pareto.csv", "s", "#2e86c1", "armada diperluas (matriks capstone)"),
                                  ("E3c", "E3c_pareto.csv", "D", "#27ae60", "armada diperluas (jalan legal-truk)")]:
        d = C(f)
        if d is None:
            continue
        al, pf = _pareto(d)
        ax[0].scatter(al.cost_rp / 1e6, al.co2_kg, s=6, c=col, alpha=0.25)
        ax[0].plot(pf.cost_rp / 1e6, pf.co2_kg, mk + "-", color=col, ms=3.5, lw=1, label=lab)
    ax[0].set_xlabel("Biaya (juta Rp/hari)"); ax[0].set_ylabel("Emisi CO$_2$ (kg/hari)")
    ax[0].set_title("(a) Front Pareto biaya–emisi"); ax[0].legend(fontsize=6.3)
    s = C("E3_sens_fixedcost.csv")
    if s is not None:
        d = s.groupby("fixed_cost_mult").mean(numeric_only=True)
        ax[1].plot(d.index, d.cost_rp / 1e6, "o-", color="#c0392b", ms=3, label="biaya")
        ax2 = ax[1].twinx(); ax2.plot(d.index, d.trucks, "s--", color="#27ae60", ms=3, label="truk")
        ax2.spines["right"].set_visible(True)
        ax[1].set_xlabel("Pengali biaya tetap truk"); ax[1].set_ylabel("Biaya (juta Rp/hari)"); ax2.set_ylabel("Jumlah truk")
        ax2.set_ylim(0, max(4, d.trucks.max() + 1))
        ax[1].set_title("(b) Sensitivitas biaya tetap")
    fig.tight_layout()
    save(fig, "L13_pareto.png")


def fig_e4():
    s = J("E4_scenarios.json")
    if not s:
        return
    rows = [(k, v) for k, v in s.items() if "hybrid" in v]
    lab = [k.split(". ", 1)[0] + ". " + k.split(". ", 1)[1][:24] for k, _ in rows]
    fig, ax = plt.subplots(1, 2, figsize=(W, 3.3), gridspec_kw=dict(width_ratios=[1.1, 1]))
    y = np.arange(len(rows))
    ax[0].barh(y, [v["hybrid"]["cost_rp"] / 1e6 for _, v in rows], color="#2e86c1")
    ax[0].set_yticks(y); ax[0].set_yticklabels(lab, fontsize=6.8); ax[0].invert_yaxis()
    ax[0].set_xlabel("Biaya (juta Rp/hari)"); ax[0].set_title("(a) Biaya")
    ax[1].barh(y, [v["hybrid"]["co2_kg"] for _, v in rows], color="#27ae60")
    for i, (_, v) in enumerate(rows):
        if v["hybrid"]["unassigned"]:
            ax[1].text(v["hybrid"]["co2_kg"] * 0.03, i, f"{v['hybrid']['unassigned']} ritase tak terlayani", va="center",
                       fontsize=6, color="white", fontweight="bold")
    ax[1].set_yticks(y); ax[1].set_yticklabels([]); ax[1].invert_yaxis()
    ax[1].set_xlabel("Emisi CO$_2$ (kg/hari)"); ax[1].set_title("(b) Emisi")
    fig.tight_layout()
    save(fig, "L14_skenario.png")


def fig_e5():
    df = C("E5_dynamic.csv")
    if df is None:
        return
    fig, ax = plt.subplots(1, 2, figsize=(W, 2.6))
    ev = [e for e in ["breakdown", "kemacetan"] if e in set(df.event)]
    lab = {"breakdown": "kerusakan truk", "kemacetan": "kemacetan mendadak"}
    imp = [((df[df.event == e].naive_fitness - df[df.event == e].reopt_fitness) / df[df.event == e].naive_fitness * 100).values
           for e in ev]
    rng = np.random.default_rng(0)
    for k, d in enumerate(imp):
        ax[0].scatter(k + rng.uniform(-0.12, 0.12, len(d)), d, s=10, color="#c0392b", alpha=0.7)
        ax[0].hlines(np.mean(d), k - 0.25, k + 0.25, color="k", lw=1)
    ax[0].axhline(0, color="#999", lw=0.8, ls="--")
    ax[0].set_xticks(range(len(ev))); ax[0].set_xticklabels([lab[e] for e in ev]); ax[0].set_xlim(-0.6, len(ev) - 0.4)
    ax[0].set_ylabel("Perbaikan fitness sisa (%)"); ax[0].set_title("(a) Perbaikan per kasus (garis = rerata)")
    for k, e in enumerate(ev):
        ax[1].scatter(k + rng.uniform(-0.12, 0.12, (df.event == e).sum()), df[df.event == e].compute_s, s=10,
                      color="#1f77b4", alpha=0.7)
    ax[1].set_xticks(range(len(ev))); ax[1].set_xticklabels([lab[e] for e in ev]); ax[1].set_xlim(-0.6, len(ev) - 0.4)
    ax[1].set_ylabel("Waktu re-optimasi (detik)"); ax[1].set_title("(b) Waktu komputasi")
    fig.tight_layout()
    save(fig, "L15_dinamis.png")


def fig_e6():
    df = C("E6_montecarlo.csv")
    if df is None:
        return
    fig, ax = plt.subplots(1, 2, figsize=(W, 2.6), sharey=True)
    st = {"Saving Matrix": ("#e67e22", "o"), "GA-SA-RL": ("#c0392b", "s"), "GA-SA-RL robust (90%)": ("#27ae60", "D")}
    for a, key in zip(ax, ["agregat", "multiproduk"]):
        d = df[df.produk == key]
        for plan, g in d.groupby("plan"):
            c, m = st.get(plan, ("k", "o"))
            a.plot(g.cv, g.service_level * 100, marker=m, color=c, ms=3.5, lw=1, label=plan)
        a.set_xlabel("Koefisien variasi permintaan"); a.set_title(f"({'a' if key == 'agregat' else 'b'}) {key}")
    ax[0].set_ylabel("Service level (%)"); ax[0].legend(fontsize=6.5)
    fig.tight_layout()
    save(fig, "L16_montecarlo.png")


def fig_e9():
    df = C("E9_microsim.csv")
    if df is None:
        return
    fig, ax = plt.subplots(1, 2, figsize=(W, 2.8))
    for a, case, title in zip(ax, ["multiproduk", "multiproduk_tw"], ["(a) Tanpa jendela waktu", "(b) Jendela waktu 06.00–11.00"]):
        d = df[df.case == case]
        data, pos, colors = [], [], []
        for i, cv in enumerate(sorted(d.cv.unique())):
            for j, plan in enumerate(["Saving Matrix", "GA-SA-RL"]):
                data.append((d[(d.cv == cv) & (d.plan == plan)].t_end / 60 + 6).values)
                pos.append(i * 3 + j); colors.append("#e67e22" if j == 0 else "#c0392b")
        bp = a.boxplot(data, positions=pos, widths=0.7, patch_artist=True, flierprops=dict(ms=1.5))
        for patch, c in zip(bp["boxes"], colors):
            patch.set_facecolor(c); patch.set_alpha(0.55)
        a.set_xticks([i * 3 + 0.5 for i in range(len(d.cv.unique()))])
        a.set_xticklabels([f"CV {idn(c, 1)}" for c in sorted(d.cv.unique())])
        a.axhline(18, color="k", ls=":", lw=0.8)
        a.set_title(title); a.set_ylabel("Jam selesai seluruh ritase")
    ax[0].plot([], [], color="#e67e22", lw=5, alpha=0.55, label="Saving Matrix")
    ax[0].plot([], [], color="#c0392b", lw=5, alpha=0.55, label="GA-SA-RL")
    ax[0].legend(fontsize=6.5, loc="upper left")
    fig.tight_layout()
    save(fig, "L17_simulasi_mikro.png")


def fig_e7():
    df = C("E7_cvrplib.csv")
    if df is None:
        return
    ok = df.groupby("instance").variant.nunique()
    df = df[df.instance.isin(ok[ok == len(ORDER)].index)]
    g = df.groupby(["instance", "variant"]).gap_pct.agg(["mean", "std"]).unstack()
    meta = df.groupby("instance").agg(cw=("cw_gap_pct", "first"), n=("n", "first")).sort_values("n")
    fig, ax = plt.subplots(figsize=(W, 2.7))
    x = np.arange(len(meta)); w = 0.16
    ax.bar(x - 2 * w, meta.cw, w, label="Clarke-Wright", color="#f5b041")
    for k, v in enumerate(ORDER):
        ax.bar(x + (k - 1) * w, g["mean"][v].reindex(meta.index), w, yerr=g["std"][v].reindex(meta.index),
               label=v, color=C3[v], error_kw=dict(lw=0.6, capsize=1.5))
    ax.set_xticks(x); ax.set_xticklabels(meta.index, rotation=30, fontsize=7); ax.set_ylabel("Gap terhadap BKS (%)")
    ax.legend(fontsize=6.5, ncol=5, loc="upper left")
    ax.set_ylim(0, max(meta.cw.max(), g["mean"].max().max()) * 1.25)
    fig.tight_layout()
    save(fig, "L18_cvrplib.png")


def fig_e10():
    df = C("E11_runs.csv")
    if df is None:
        return
    ns = sorted(df.n.unique())
    fig, ax = plt.subplots(1, 3, figsize=(W, 2.8), gridspec_kw=dict(width_ratios=[1.5, 1, 1]))
    pos = np.arange(len(ns)); w = 0.18
    for k, v in enumerate(ORDER):
        data = [df[(df.n == n) & (df.variant == v)].fitness for n in ns]
        bp = ax[0].boxplot(data, positions=pos + (k - 1.5) * w, widths=w * 0.85, patch_artist=True,
                           flierprops=dict(ms=2))
        for b in bp["boxes"]:
            b.set_facecolor(C3[v]); b.set_alpha(0.7)
        ax[0].plot([], [], color=C3[v], lw=6, alpha=0.7, label=v)
    for v, m, c in [("Clarke-Wright", "v", "#e67e22"), ("OR-Tools", "D", "#6a3d9a")]:
        y = [df[(df.n == n) & (df.variant == v)].fitness.mean() for n in ns]
        ax[0].scatter(pos, y, marker=m, color=c, s=18, zorder=5, label=v)
    ax[0].set_yscale("log"); ax[0].set_xticks(pos); ax[0].set_xticklabels([str(n) for n in ns])
    ax[0].set_xlabel("Jumlah SPBU"); ax[0].set_ylabel("Fitness (skala log)"); ax[0].set_title("(a) Fitness, 10 seed")
    h, l = ax[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=6, fontsize=6.5, frameon=False, bbox_to_anchor=(0.5, -0.06))
    meth = ["Clarke-Wright", "OR-Tools", "GA-SA-RL"]; cols = ["#e67e22", "#6a3d9a", "#c0392b"]
    for j, (col, lab, t) in enumerate([("late_min", "Keterlambatan (menit)", "(b) Terlambat"),
                                       ("overtime_min", "Lembur (menit)", "(c) Lembur")]):
        for k, (v, c) in enumerate(zip(meth, cols)):
            y = [df[(df.n == n) & (df.variant == v)][col].mean() for n in ns]
            ax[j + 1].bar(pos + (k - 1) * 0.26, y, 0.26, color=c, label=v)
        ax[j + 1].set_xticks(pos); ax[j + 1].set_xticklabels([str(n) for n in ns])
        ax[j + 1].set_xlabel("Jumlah SPBU"); ax[j + 1].set_ylabel(lab); ax[j + 1].set_title(t)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    save(fig, "L19_skalabilitas.png")


def crops(shots):
    """Potong tangkapan layar aplikasi (buang panel kiri) dan simpan ke figures/laporan."""
    from PIL import Image
    spec = {"app_01_data.png": ("L03_app_data.png", (560, 0, 2400, 1500)),
            "app_02_optimasi.png": ("L04_app_optimasi.png", (560, 200, 2400, 1380)),
            "app_03_gantt.png": ("L05_app_gantt.png", (560, 0, 2400, 1500)),
            "sim_0830.png": ("L06_app_sim3d.png", None),
            "sim_1100_2d.png": ("L07_app_sim2d.png", None),
            "app_07_timeline.png": ("L08_app_timeline.png", (560, 0, 2400, 1500)),
            "app_08_dinamis.png": ("L09_app_dinamis.png", (560, 0, 2400, 1500))}
    for src, (dst, box) in spec.items():
        p = os.path.join(shots, src)
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert("RGB")
        if box:
            im = im.crop(box)
        im.save(os.path.join(OUT, dst), optimize=True)
        print("saved", dst)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        crops(sys.argv[1])
    for f in [fig_alur, fig_prosedur, fig_e1, fig_e2, fig_osm, fig_e3, fig_e4, fig_e5, fig_e6, fig_e9, fig_e7, fig_e10]:
        try:
            f()
        except Exception as e:
            print("gagal", f.__name__, repr(e))

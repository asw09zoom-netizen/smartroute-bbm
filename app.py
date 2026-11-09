"""
SMARTROUTE-BBM — Web-based Decision Support System
MC-MP-MT-VRP distribusi BBM multi-produk dengan Hybrid GA-SA-RL
Studi kasus: FT Gelumbang (13 SPBU) — Penelitian PEM Akamigas 2026

Jalankan lokal :  pip install -r requirements.txt && streamlit run app.py
Deploy          :  Streamlit Community Cloud -> pilih repositori GitHub ini, file app.py
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from smartroute import scenarios as sc
from smartroute.data import BASELINE_DIST_KM, BASELINE_ROUTES, DIRECT_DIST_KM, build_instance
from smartroute.dynamic import breakdown_event
from smartroute.hybrid import HybridConfig, HybridGASARL
from smartroute.model import Evaluator, Params, evaluate_routes
from smartroute.sheets import from_streamlit_secrets
from smartroute import telegram_bot

st.set_page_config(page_title="SMARTROUTE-BBM", page_icon="⛽", layout="wide")
ROOT = os.path.dirname(os.path.abspath(__file__))
COLORS = px.colors.qualitative.Bold


# ---------------------------------------------------------------------------
@st.cache_resource
def get_db():
    return from_streamlit_secrets(st)


@st.cache_data(ttl=300)
def get_tables(_mode: str):
    return get_db().load_tables()


db = get_db()
try:
    tables = get_tables(db.mode)
    data_src = {"read-write": "Google Sheets (baca-tulis)", "read-only": "Google Sheets (baca)",
                "lokal": "CSV lokal"}[db.mode]
except Exception as e:  # fallback bila Sheets gagal
    from smartroute.data import load_tables
    tables = load_tables()
    data_src = f"CSV lokal (Sheets gagal: {e})"

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## ⛽ SMARTROUTE-BBM")
    st.caption("DSS MC-MP-MT-VRP · Hybrid GA-SA-RL · PEM Akamigas 2026")
    st.caption(f"Sumber data: **{data_src}**")
    st.divider()
    st.markdown("### Model")
    multiproduct = st.toggle("Multi-produk (proporsi asumsi tb_produk)", value=True)
    single_trip = st.toggle("Satu ritase per truk (setara baseline)", value=False)
    st.markdown("**Armada tersedia (unit)**")
    fleet = {}
    cols = st.columns(4)
    for c, r in zip(cols, tables["armada"]):
        fleet[r["tipe"]] = c.number_input(r["tipe"], 0, 20, int(float(r["jumlah_unit"])), key=f"f_{r['tipe']}")
    st.markdown("### Bobot objektif")
    w1 = st.slider("w₁ biaya", 0.0, 1.0, 0.50, 0.05)
    w2 = st.slider("w₂ emisi CO₂", 0.0, 1.0 - w1, min(0.30, 1.0 - w1), 0.05)
    w3 = round(1 - w1 - w2, 2)
    st.caption(f"w₃ waktu = {w3:.2f}")
    st.markdown("### Algoritma")
    variant = st.selectbox("Varian", ["GA-SA-RL", "GA-SA", "GA"])
    pop = st.slider("Populasi N", 20, 200, 100, 10)
    gens = st.slider("Generasi", 20, 500, 200, 10)
    sa_iters = st.slider("Iterasi SA", 0, 10000, 5000, 500)
    seed = st.number_input("Seed", 0, 9999, 1)
    st.markdown("### Skenario")
    scen = st.multiselect("Aktifkan skenario", [s for s in sc.SCENARIOS if not s.startswith(("3.", "4."))])
    with st.expander("Parameter skenario"):
        peak_cf = st.slider("CF jam sibuk", 0.2, 1.0, 0.5, 0.05)
        surge = st.slider("Faktor surge (SF)", 1.0, 5.0, 1.5, 0.1)
        quota = st.slider("Kuota Biosolar (% permintaan)", 50, 100, 95)
        racks = st.number_input("Jumlah loading rack", 1, 8, 4)
        other_trucks = st.slider("Kedatangan truk lain (unit/jam)", 0.0, 4.5, 2.5, 0.5)
    run = st.button("▶ JALANKAN OPTIMASI", type="primary", use_container_width=True)


def make_instance():
    p = Params(w=(w1, w2, w3), single_trip=single_trip)
    inst = build_instance(tables, multiproduct=multiproduct, fleet=fleet, params=p)
    notes = []
    for s in scen:
        if s.startswith("1."):
            inst = sc.apply_congestion(inst, peak_cf, 0.85); notes.append(f"CF puncak {peak_cf}")
        elif s.startswith("2."):
            inst = sc.apply_road_restriction(inst, {2: 5.0, 3: 5.0, 4: 5.0, 5: 5.0}); notes.append("S2-S5 jalan 5 m")
        elif s.startswith("5."):
            inst = sc.apply_time_windows(inst, {i: (6, 11) for i in [7, 8, 9, 11, 12, 13]}); notes.append("TW Prabumulih 06-11")
        elif s.startswith("6."):
            inst = inst.with_params(w=(0.1, 0.8, 0.1)); notes.append("bobot emisi 0,8")
        elif s.startswith("7."):
            rng = np.random.default_rng(int(seed))
            inst = sc.apply_tank_management(inst, np.concatenate([[1.0], rng.uniform(0.15, 0.6, inst.n)]))
            notes.append("stok awal acak 15-60%")
        elif s.startswith("8."):
            inst = sc.apply_loading_rack(inst, int(racks), other_trucks)
            notes.append(f"Wq rack {inst.params.rack_wait:.1f} mnt")
        elif s.startswith("9."):
            inst = sc.apply_surge(inst, surge); notes.append(f"SF {surge}")
        elif s.startswith("10."):
            inst = sc.apply_bph_quota(inst, quota / 100); notes.append(f"kuota {quota}%")
    return inst, notes


def trips_df(inst, sol):
    rows = []
    for t in sol.trips:
        rows.append({"Unit": f"{inst.vtypes[t.vtype].name}-{t.truck}" if t.truck >= 0 else "TIDAK ADA TRUK",
                     "Ritase": t.trip_no, "Rute": "FT → " + " → ".join(inst.labels[i] for i in t.seq) + " → FT",
                     "Muatan (KL)": round(t.load, 2), "Jarak (km)": round(t.dist, 1), "CO₂ (kg)": round(t.co2, 1),
                     "Berangkat": hhmm(inst, t.start), "Kembali": hhmm(inst, t.end),
                     "Kompartemen": ", ".join(f"{c:g}KL:{inst.products[p] if p >= 0 else '-'}"
                                             for c, p in zip(inst.vtypes[t.vtype].compartments, t.comp_assign))})
    return pd.DataFrame(rows)


def hhmm(inst, m):
    t = inst.params.shift_start_h * 60 + m
    return f"{int(t // 60) % 24:02d}:{int(t % 60):02d}"


def route_map(inst, sol, title=""):
    fig = go.Figure()
    C = inst.coords
    for k, t in enumerate(sol.trips):
        idx = [0] + t.seq + [0]
        fig.add_trace(go.Scattermap(lat=C[idx, 0], lon=C[idx, 1], mode="lines+markers",
                                    line=dict(width=3, color=COLORS[k % len(COLORS)]),
                                    name=f"{inst.vtypes[t.vtype].name}-{t.truck} R{t.trip_no}: "
                                         + "-".join(inst.labels[i] for i in t.seq)))
    fig.add_trace(go.Scattermap(lat=C[1:, 0], lon=C[1:, 1], mode="markers+text", text=inst.labels[1:],
                                textposition="top right", marker=dict(size=10, color="#1f77b4"), name="SPBU"))
    fig.add_trace(go.Scattermap(lat=[C[0, 0]], lon=[C[0, 1]], mode="markers+text", text=["FT Gelumbang"],
                                marker=dict(size=16, color="red"), name="FT"))
    fig.update_layout(map=dict(style="open-street-map", center=dict(lat=C[:, 0].mean(), lon=C[:, 1].mean()), zoom=9.3),
                      height=520, margin=dict(l=0, r=0, t=30, b=0), title=title,
                      legend=dict(orientation="h", y=-0.05))
    return fig


def gantt(inst, sol):
    rows = []
    base = datetime(2026, 1, 1)
    for t in sol.trips:
        s = base + pd.Timedelta(minutes=inst.params.shift_start_h * 60 + t.start)
        e = base + pd.Timedelta(minutes=inst.params.shift_start_h * 60 + t.end)
        rows.append(dict(Unit=f"{inst.vtypes[t.vtype].name}-{t.truck}", Mulai=s, Selesai=e,
                         Ritase=f"R{t.trip_no}: " + "-".join(inst.labels[i] for i in t.seq)))
    if not rows:
        return None
    fig = px.timeline(pd.DataFrame(rows), x_start="Mulai", x_end="Selesai", y="Unit", color="Ritase", text="Ritase")
    end_shift = base + pd.Timedelta(minutes=inst.params.shift_start_h * 60 + inst.params.shift_len)
    fig.add_vline(x=end_shift, line_dash="dash", line_color="red")
    fig.update_layout(height=300, showlegend=False, margin=dict(l=0, r=0, t=10, b=0))
    return fig


# ---------------------------------------------------------------------------
st.title("SMARTROUTE-BBM · Simulasi Distribusi BBM FT Gelumbang")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📍 Data & Peta", "🧬 Optimasi GA-SA-RL", "🚨 Re-routing Dinamis",
                                        "📊 Hasil Penelitian", "📄 Laporan & Log"])

with tab1:
    inst0 = build_instance(tables, multiproduct=multiproduct, fleet=fleet)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("SPBU dilayani", inst0.n)
    c2.metric("Total permintaan", f"{inst0.total_demand().sum():.2f} KL/hari")
    c3.metric("Baseline Saving Matrix", f"{BASELINE_DIST_KM} km", f"-{(1 - BASELINE_DIST_KM / DIRECT_DIST_KM) * 100:.1f}% vs direct")
    c4.metric("Armada", " + ".join(f"{v}×{k}" for k, v in fleet.items() if v))
    l, r = st.columns([1.2, 1])
    with l:
        base_sol = evaluate_routes(Evaluator(inst0), BASELINE_ROUTES)
        st.plotly_chart(route_map(inst0, base_sol, "Baseline Saving Matrix (capstone)"), use_container_width=True)
        st.caption("Garis rute digambar lurus antar-titik; jarak model memakai matriks jarak jalan capstone.")
    with r:
        st.markdown("**tb_spbu**")
        st.dataframe(pd.DataFrame(tables["spbu"]), hide_index=True, height=300)
        st.markdown("**tb_armada** (ukuran kompartemen = asumsi)")
        st.dataframe(pd.DataFrame(tables["armada"]), hide_index=True)
        st.markdown("**tb_produk** (proporsi = asumsi skenario)")
        st.dataframe(pd.DataFrame(tables["produk"]), hide_index=True)
    with st.expander("Matriks jarak jalan (km) — tb_jarak"):
        J = tables["jarak"]
        st.dataframe(pd.DataFrame(J[1:], columns=J[0]), hide_index=True)

with tab2:
    if run:
        inst, notes = make_instance()
        ev = Evaluator(inst)
        prog = st.progress(0.0, text="Inisialisasi populasi…")

        def cb(phase, i, n, f):
            prog.progress(min(1.0, i / max(n, 1)), text=f"{phase} {i}/{n} · fitness terbaik {f:.4f}")
        cfg = HybridConfig(variant=variant, pop_size=pop, generations=gens, sa_iters=sa_iters, seed=int(seed))
        res = HybridGASARL(ev, cfg, progress=cb).run()
        prog.progress(1.0, text=f"Selesai dalam {res.runtime:.1f} s")
        base = evaluate_routes(ev, BASELINE_ROUTES)
        st.session_state["last"] = dict(inst=inst, res=res, base=base, notes=notes, variant=variant, seed=int(seed))
        rec = dict(skenario="; ".join(scen) or "normal", algoritma=variant, seed=int(seed), fitness=round(res.best.fitness, 5),
                   jarak_km=round(res.best.dist, 2), biaya_rp=round(res.best.Z1), co2_kg=round(res.best.Z2, 2),
                   waktu_menit=round(res.best.Z3, 1), jumlah_ritase=len(res.best.trips), jumlah_truk=res.best.trucks_used,
                   terlambat_menit=round(res.best.late_min, 1), lembur_menit=round(res.best.overtime_min, 1),
                   tidak_terlayani=res.best.unassigned, waktu_komputasi_s=round(res.runtime, 2),
                   rute=" | ".join("-".join(inst.labels[i] for i in t.seq) for t in res.best.trips))
        try:
            where = db.log_run(rec)
            st.toast(f"Log tersimpan ke {where}")
        except Exception as e:
            st.warning(f"Log gagal disimpan: {e}")
    if "last" in st.session_state:
        L = st.session_state["last"]
        inst, res, base = L["inst"], L["res"], L["base"]
        s = res.best
        if L["notes"]:
            st.info("Skenario aktif: " + "; ".join(L["notes"]))
        if base.unassigned:
            st.warning(f"Rencana baseline Saving Matrix memiliki {base.unassigned} ritase yang TIDAK LAYAK "
                       "pada model kompartemen/armada ini (tidak ada truk yang dapat membawanya).")
        if s.unassigned:
            st.error(f"{s.unassigned} ritase tidak mendapat truk — tambah armada atau ubah skenario.")
        m = st.columns(6)
        def delta(a, b):
            return f"{(a - b) / b * 100:+.1f}% vs baseline" if b else None
        m[0].metric("Fitness", f"{s.fitness:.4f}", delta(s.fitness, base.fitness) if not base.unassigned
                    else "baseline tidak layak", delta_color="inverse" if not base.unassigned else "off")
        m[1].metric("Jarak", f"{s.dist:.1f} km", delta(s.dist, base.dist), delta_color="inverse")
        m[2].metric("Biaya", f"Rp {s.Z1 / 1e6:.2f} jt", delta(s.Z1, base.Z1), delta_color="inverse")
        m[3].metric("Emisi CO₂", f"{s.Z2:.1f} kg", delta(s.Z2, base.Z2), delta_color="inverse")
        m[4].metric("Truk / ritase", f"{s.trucks_used} / {len(s.trips)}", f"baseline {base.trucks_used} / {len(base.trips)}",
                    delta_color="off")
        m[5].metric("Terlambat / lembur", f"{s.late_min:.0f} / {s.overtime_min:.0f} mnt")
        a, b = st.columns([1.2, 1])
        with a:
            st.plotly_chart(route_map(inst, s, f"Rute {L['variant']}"), use_container_width=True)
        with b:
            h = pd.DataFrame(dict(iterasi=range(len(res.history)), fitness=res.history, fase=res.phase))
            st.plotly_chart(px.line(h, x="iterasi", y="fitness", color="fase", title="Kurva konvergensi"),
                            use_container_width=True)
            if res.op_counts:
                op = pd.DataFrame(dict(operator=list(res.op_counts), dipilih=list(res.op_counts.values()),
                                       sukses=[res.op_success.get(k, 0) for k in res.op_counts]))
                st.plotly_chart(px.bar(op, x="operator", y=["dipilih", "sukses"], barmode="group",
                                       title="Pemilihan operator SA (Q-Learning)" if L["variant"] == "GA-SA-RL" else "Operator SA"),
                                use_container_width=True)
        st.markdown("**Jadwal ritase (multi-trip)**")
        g = gantt(inst, s)
        if g:
            st.plotly_chart(g, use_container_width=True)
        st.dataframe(trips_df(inst, s), hide_index=True, use_container_width=True)
        with st.expander("Bandingkan: rencana baseline Saving Matrix pada model yang sama"):
            st.dataframe(trips_df(inst, base), hide_index=True, use_container_width=True)
            st.write(pd.DataFrame([base.summary(), s.summary()], index=["Saving Matrix", L["variant"]]).T)
    else:
        st.info("Atur parameter di sidebar lalu klik **JALANKAN OPTIMASI**.")

with tab3:
    st.markdown("Simulasikan kerusakan truk di tengah shift, lalu bandingkan **tanpa re-routing** "
                "vs **re-optimasi GA-SA-RL** (operator dipilih Q-Learning).")
    if "last" not in st.session_state:
        st.info("Jalankan optimasi terlebih dahulu.")
    else:
        L = st.session_state["last"]
        inst, s = L["inst"], L["res"].best
        units = sorted({t.truck for t in s.trips if t.truck >= 0})
        c1, c2 = st.columns(2)
        u = c1.selectbox("Unit truk yang rusak", units, format_func=lambda x: f"Unit {x}")
        tb = c2.slider("Waktu kejadian (menit sejak 06:00)", 0, int(inst.params.shift_len), 120, 15)
        if st.button("Simulasikan breakdown"):
            o = breakdown_event(inst, s, u, float(tb), seed=L["seed"])
            if o.get("n_affected", 0) == 0:
                st.success("Tidak ada SPBU yang terdampak pada waktu tersebut.")
            else:
                st.write(f"SPBU terdampak: **{o['n_affected']}** (tertahan di truk rusak: {o['n_stranded']}); "
                         f"waktu re-optimasi {o['compute_s']:.2f} s")
                st.dataframe(pd.DataFrame(dict(Tanpa_rerouting=o["naive"], Reoptimasi_GA_SA_RL=o["reopt"])),
                             use_container_width=True)
                sub_labels = [inst.labels[i] for i in o["idx"]]
                rows = []
                for name, sol in [("Tanpa re-routing", o["naive_sol"]), ("Re-optimasi", o["reopt_sol"])]:
                    for t in sol.trips:
                        rows.append(dict(Kebijakan=name, Unit=t.truck, Rute="-".join(sub_labels[i] for i in t.seq),
                                         Berangkat=hhmm(inst, t.start), Kembali=hhmm(inst, t.end)))
                st.dataframe(pd.DataFrame(rows), hide_index=True)

with tab4:
    st.markdown("Ringkasan eksperimen (`python -m experiments.run_all`). Angka dibaca langsung dari folder `results/`.")
    resdir = os.path.join(ROOT, "results")
    figdir = os.path.join(ROOT, "figures")
    if os.path.isdir(figdir):
        figs = sorted(f for f in os.listdir(figdir) if f.endswith(".png"))
        for i in range(0, len(figs), 2):
            cc = st.columns(2)
            for c, f in zip(cc, figs[i:i + 2]):
                c.image(os.path.join(figdir, f), caption=f)
    for f in sorted(os.listdir(resdir)) if os.path.isdir(resdir) else []:
        if f.endswith(".csv") and f != "simulasi_log.csv":
            with st.expander(f):
                st.dataframe(pd.read_csv(os.path.join(resdir, f)), use_container_width=True)

with tab5:
    if "last" in st.session_state:
        L = st.session_state["last"]
        inst, s = L["inst"], L["res"].best
        txt = [f"LAPORAN SIMULASI SMARTROUTE-BBM — {datetime.now():%d-%m-%Y %H:%M}",
               f"Algoritma: {L['variant']} (seed {L['seed']})", f"Skenario: {', '.join(L['notes']) or 'normal'}",
               f"Jarak {s.dist:.1f} km | Biaya Rp {s.Z1:,.0f} | CO2 {s.Z2:.1f} kg | Truk {s.trucks_used} | Ritase {len(s.trips)}",
               ""]
        for t in s.trips:
            txt.append(f"Unit {t.truck} R{t.trip_no} {hhmm(inst, t.start)}-{hhmm(inst, t.end)}: FT-"
                       + "-".join(inst.labels[i] for i in t.seq) + f"-FT ({t.load:.2f} KL, {t.dist:.1f} km)")
        report = "\n".join(txt)
        st.code(report)
        st.download_button("Unduh laporan (.txt)", report, "laporan_smartroute.txt")
        st.download_button("Unduh rute (.csv)", trips_df(inst, s).to_csv(index=False), "rute_smartroute.csv")
        if telegram_bot.configured(st):
            if st.button("Kirim ke Telegram"):
                ok, msg = telegram_bot.send(st, report)
                (st.success if ok else st.error)(msg)
        else:
            st.caption("Telegram Bot belum dikonfigurasi (isi [telegram] bot_token & chat_id di secrets).")
    logp = os.path.join(ROOT, "results", "simulasi_log.csv")
    if db.mode != "read-write" and os.path.exists(logp):
        st.markdown("**Log simulasi lokal**")
        st.dataframe(pd.read_csv(logp), hide_index=True)

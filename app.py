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
from smartroute import anim, roadnet, telegram_bot
from smartroute import simulate as simmod

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
    road_opts = (["Jalan nyata OSM (legal truk)"] if roadnet.available() else []) + ["Matriks jarak capstone"]
    road_choice = st.radio("Jaringan jalan", road_opts, index=0,
                           help="Jalan nyata OSM: tiap tipe truk hanya boleh lewat ruas yang sesuai kelas jalan "
                                "(UU 22/2009 Pasal 19), rambu batas, dan lebar jalan minimum truk.")
    road_mode = "osm" if road_choice.startswith("Jalan nyata") else "capstone"
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
    inst = build_instance(tables, multiproduct=multiproduct, fleet=fleet, params=p, road=road_mode)
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
    geom = roadnet.load_geometry() if inst.Dk is not None else {}
    for k, t in enumerate(sol.trips):
        idx = [0] + t.seq + [0]
        lat, lon = C[idx, 0], C[idx, 1]
        poly = roadnet.route_polyline(geom, inst.vtypes[t.vtype].name, [inst.labels[i] for i in idx]) if geom else None
        if poly:
            lat, lon = [p[0] for p in poly], [p[1] for p in poly]
        fig.add_trace(go.Scattermap(lat=lat, lon=lon, mode="lines",
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
st.markdown("<style>.block-container{padding-top:1.6rem;padding-bottom:1rem;max-width:100%}"
            "h1{font-size:1.7rem!important;padding-bottom:.2rem!important}</style>", unsafe_allow_html=True)
st.title("SMARTROUTE-BBM · Simulasi Distribusi BBM FT Gelumbang")
tab1, tab2, tab_sim, tab_tbl, tab3, tab4, tab5 = st.tabs(["📍 Data & Peta", "🧬 Optimasi GA-SA-RL", "🚚 Simulasi Pergerakan",
                                                 "📋 Data Simulasi",
                                                 "🚨 Re-routing Dinamis",
                                        "📊 Hasil Penelitian", "📄 Laporan & Log"])

with tab1:
    inst0 = build_instance(tables, multiproduct=multiproduct, fleet=fleet, road=road_mode)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("SPBU dilayani", inst0.n)
    c2.metric("Total permintaan", f"{inst0.total_demand().sum():.2f} KL/hari")
    c3.metric("Baseline Saving Matrix", f"{BASELINE_DIST_KM} km", f"-{(1 - BASELINE_DIST_KM / DIRECT_DIST_KM) * 100:.1f}% vs direct")
    c4.metric("Armada", " + ".join(f"{v}×{k}" for k, v in fleet.items() if v))
    l, r = st.columns([1.2, 1])
    with l:
        base_sol = evaluate_routes(Evaluator(inst0), BASELINE_ROUTES)
        st.plotly_chart(route_map(inst0, base_sol, "Baseline Saving Matrix (capstone)"), use_container_width=True)
        if road_mode == "osm":
            st.caption("Rute digambar mengikuti jalan OpenStreetMap yang legal untuk tipe truk ritase tsb. "
                       "Jarak baseline dihitung ulang pada jaringan jalan legal-truk.")
        else:
            st.caption("Garis rute digambar lurus antar-titik; jarak model memakai matriks jarak jalan capstone.")
    with r:
        st.markdown("**tb_spbu**")
        st.dataframe(pd.DataFrame(tables["spbu"]), hide_index=True, height=300)
        st.markdown("**tb_armada** (ukuran kompartemen = asumsi)")
        st.dataframe(pd.DataFrame(tables["armada"]), hide_index=True)
        st.markdown("**tb_produk** (proporsi = asumsi skenario)")
        st.dataframe(pd.DataFrame(tables["produk"]), hide_index=True)
    with st.expander("Aturan jalan untuk truk tangki (kelas jalan, rambu, lebar jalan)"):
        st.markdown(
            "Sebuah ruas OSM boleh dilalui truk tipe k bila: (a) jenis ruas termasuk jalan umum yang boleh "
            "dilalui truk; (b) tidak ada larangan `access`/`hgv`; (c) **kelas jalan** ruas mengizinkan dimensi "
            "dan MST truk (UU 22/2009 Pasal 19, PP 79/2013); (d) rambu batas OSM (`maxwidth`, `maxlength`, "
            "`maxheight`, `maxweight`, `maxaxleload`) tidak dilanggar; (e) **lebar badan jalan** ≥ lebar jalan "
            "minimum truk (kolom `lebar_jalan_min_m`); (f) arah satu jalur dipatuhi. Kelas & lebar bawaan per jenis "
            "ruas adalah ASUMSI bila OSM tidak memuat tag `width`/`lanes` — dapat diubah di `data/osm_jalan.csv`.")
        dd = os.path.join(ROOT, "data")
        st.markdown("**Batas dimensi & MST per kelas jalan**")
        st.dataframe(pd.read_csv(os.path.join(dd, "aturan_kelas_jalan.csv")), hide_index=True)
        st.markdown("**Pemetaan jenis ruas OSM → kelas & lebar bawaan (asumsi)**")
        st.dataframe(pd.read_csv(os.path.join(dd, "osm_jalan.csv")), hide_index=True)
        rs = os.path.join(dd, "osm", "ringkasan_ruas.csv")
        if os.path.exists(rs):
            st.markdown("**Ringkasan ruas legal per tipe truk** (km ruas OSM di wilayah studi)")
            st.dataframe(pd.read_csv(rs), hide_index=True)
        if inst0.Dk is not None:
            t_sel = st.selectbox("Matriks jarak jalan legal untuk tipe truk", [v.name for v in inst0.vtypes])
            kk = [v.name for v in inst0.vtypes].index(t_sel)
            st.dataframe(pd.DataFrame(np.round(inst0.Dk[kk], 1), index=inst0.labels, columns=inst0.labels))
            st.caption("Kosong = tidak ada lintasan legal untuk tipe truk tsb. Data jalan © kontributor OpenStreetMap (ODbL).")
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

with tab_sim:
    with st.popover("ℹ️ Cara kerja simulasi"):
        st.markdown("Rencana ritase dijalankan ulang secara rinci di sepanjang jalan legal-truk. Kecepatan tiap segmen = "
               "min(batas kecepatan jenis jalan, kecepatan maks truk) × faktor kemacetan jam × pengaruh muatan × variasi "
               "lalu lintas; waktu bongkar = waktu tetap + volume ÷ laju bongkar tipe truk. Nilai default adalah ASUMSI "
               "dan dapat diubah di bawah.")
    srcs = (["Hasil optimasi terakhir"] if "last" in st.session_state else []) + ["Baseline Saving Matrix (capstone)"]
    c1, c2 = st.columns([1, 2])
    src = c1.radio("Rencana yang disimulasikan", srcs, horizontal=True)
    if src.startswith("Hasil"):
        sim_inst, sim_sol = st.session_state["last"]["inst"], st.session_state["last"]["res"].best
    else:
        sim_inst = inst0
        sim_sol = evaluate_routes(Evaluator(inst0), BASELINE_ROUTES)
    if sim_inst.Dk is None:
        c2.info("Mode matriks capstone: truk bergerak lurus antar-titik dengan kecepatan rata-rata model. "
                "Pilih **Jalan nyata OSM (legal truk)** di panel kiri agar truk mengikuti jalan dan kecepatan per jenis jalan.")
    dcfg = simmod.default_config()
    map_slot = st.container()
    with st.expander("⚙️ Parameter simulasi (kecepatan truk, batas kecepatan jalan, laju bongkar, variasi)", expanded=False):
        a, b = st.columns(2)
        types_used = sorted({sim_inst.vtypes[t.vtype].name for t in sim_sol.trips})
        tdf = pd.DataFrame({"tipe": [v.name for v in sim_inst.vtypes],
                            "kapasitas (KL)": [v.capacity for v in sim_inst.vtypes],
                            "kecepatan maks (km/jam)": [dcfg.v_truck.get(v.name, 60.0) for v in sim_inst.vtypes],
                            "laju bongkar (L/menit)": [dcfg.unload_rate.get(v.name, 400.0) for v in sim_inst.vtypes]})
        tdf = a.data_editor(tdf, hide_index=True, disabled=["tipe", "kapasitas (KL)"], key="sim_types")
        a.caption("Tipe yang dipakai rencana ini: " + ", ".join(types_used))
        rdf = pd.DataFrame({"jenis jalan": list(dcfg.road_speed), "batas kecepatan (km/jam)": list(dcfg.road_speed.values())})
        rdf = b.data_editor(rdf, hide_index=True, disabled=["jenis jalan"], height=260, key="sim_roads")
        x1, x2, x3, x4, x5 = st.columns(5)
        u_fix = x1.number_input("Waktu tetap bongkar (mnt)", 0.0, 60.0, float(sim_inst.params.unload_fixed), 1.0)
        gamma = x2.slider("Perlambatan saat muatan penuh", 0.0, 0.4, 0.15, 0.05)
        tcv = x3.slider("Variasi lalu lintas (CV)", 0.0, 0.5, 0.15, 0.05)
        ucv = x4.slider("Variasi waktu bongkar (CV)", 0.0, 0.5, 0.15, 0.05)
        sseed = x5.number_input("Seed simulasi", 0, 9999, 1)
        use_cf = st.toggle("Pakai profil kemacetan per jam (skenario aktif)", value=True)
    cfg_sim = simmod.SimConfig(
        v_truck=dict(zip(tdf["tipe"], tdf["kecepatan maks (km/jam)"].astype(float))),
        unload_rate=dict(zip(tdf["tipe"], tdf["laju bongkar (L/menit)"].astype(float))),
        road_speed=dict(zip(rdf["jenis jalan"], rdf["batas kecepatan (km/jam)"].astype(float))),
        unload_fixed=float(u_fix), load_gamma=float(gamma), traffic_cv=float(tcv), unload_cv=float(ucv),
        seed=int(sseed), use_congestion=use_cf)
    simres = simmod.simulate(sim_inst, sim_sol, cfg_sim)
    stations = [dict(id=sim_inst.labels[i], lat=float(sim_inst.coords[i, 0]), lon=float(sim_inst.coords[i, 1]))
                for i in range(1, sim_inst.n + 1)]
    depot = dict(lat=float(sim_inst.coords[0, 0]), lon=float(sim_inst.coords[0, 1]))
    import streamlit.components.v1 as components
    with map_slot:
        components.html(anim.build_html(simres, stations, depot, height=820), height=830, scrolling=False)
    st.session_state["sim"] = dict(res=simres, inst=sim_inst)
    over = simres["t_end"] - sim_inst.params.shift_len
    if over > 0:
        st.warning(f"Pada simulasi ini armada baru selesai {hhmm(sim_inst, simres['t_end'])}, melewati akhir shift {over:.0f} menit.")
    st.caption("Seret untuk menggeser, klik kanan/Ctrl+seret untuk memutar dan memiringkan peta. Tabel rinci ada di menu "
               "**📋 Data Simulasi**. Peta dasar © Esri / © OpenStreetMap contributors.")

with tab_tbl:
    if "sim" not in st.session_state:
        st.info("Buka menu Simulasi Pergerakan terlebih dahulu.")
    else:
        simres, sim_inst = st.session_state["sim"]["res"], st.session_state["sim"]["inst"]
        k1, k2 = st.columns([1.1, 1])
        with k1:
            st.markdown("**Ringkasan per truk (hasil simulasi)**")
            ud = pd.DataFrame([dict(Unit=u["unit"], Tipe=u["tipe"], **{"Jarak (km)": u["km"], "Mengemudi (mnt)": u["drive_min"],
                                     "Rerata (km/jam)": round(u["km"] / max(u["drive_min"], 1e-9) * 60, 1),
                                     "Muat (mnt)": u["load_min"], "Bongkar (mnt)": u["unload_min"], "Siaga (mnt)": u["wait_min"],
                                     "Kembali terakhir": hhmm(sim_inst, u["selesai"])}) for u in simres["units"]])
            st.dataframe(ud, hide_index=True)
        with k2:
            st.markdown("**Kedatangan di SPBU: rencana model vs simulasi**")
            sd = pd.DataFrame([dict(Unit=x["unit"], R=x["ritase"], SPBU=x["spbu"], **{"Vol (KL)": x["volume_kl"],
                                     "Rencana": hhmm(sim_inst, x["tiba_rencana"]), "Simulasi": hhmm(sim_inst, x["tiba_simulasi"]),
                                     "Selisih (mnt)": round(x["tiba_simulasi"] - x["tiba_rencana"], 0),
                                     "Bongkar (mnt)": round(x["bongkar_menit"], 0)}) for x in simres["stops"]])
            st.dataframe(sd, hide_index=True, height=300)
        rows = []
        base = datetime(2026, 1, 1)
        for u in simres["units"]:
            for a, b, txt in u["spans"]:
                if b is None or b <= a:
                    continue
                kind = ("Muat di FT" if txt.startswith("Muat") else "Bongkar" if txt.startswith("Bongkar") else
                        "Kembali" if txt.startswith("Kembali") else "Siaga" if txt.startswith("Siaga") else "Menuju SPBU")
                rows.append(dict(Unit=u["unit"], Aktivitas=kind, Keterangan=txt,
                                 Mulai=base + pd.Timedelta(minutes=sim_inst.params.shift_start_h * 60 + a),
                                 Selesai=base + pd.Timedelta(minutes=sim_inst.params.shift_start_h * 60 + b)))
        if rows:
            fig = px.timeline(pd.DataFrame(rows), x_start="Mulai", x_end="Selesai", y="Unit", color="Aktivitas",
                              hover_data=["Keterangan"], title="Lini masa aktivitas truk (hasil simulasi)",
                              color_discrete_map={"Muat di FT": "#40a9ff", "Menuju SPBU": "#36cfc9", "Bongkar": "#ffa940",
                                                  "Kembali": "#9254de", "Siaga": "#8c8c8c"})
            fig.update_layout(height=320, margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)
        st.markdown("**Log kejadian**")
        st.dataframe(pd.DataFrame([dict(Jam=hhmm(sim_inst, e["t"]), Unit=e["unit"], Kejadian=e["ev"], Lokasi=e["tempat"])
                                   for e in simres["events"]]), hide_index=True, height=260)


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

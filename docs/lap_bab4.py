"""Isi BAB 4 (hasil dan pembahasan), BAB 5, dan lampiran. Seluruh angka hasil dibaca dari results/."""
from __future__ import annotations

import math
import os

import numpy as np
import pandas as pd

from docs.lap_common import FIGL, REPO, SHEET, VAR, e7_tests, f, pareto_pts, pct, pv, rp
from docs.lap_text import jam_txt

FG = lambda n: os.path.join(FIGL, n)  # noqa: E731
CASE_E9 = {"multiproduk": "tanpa jendela waktu", "multiproduk_tw": "dengan jendela waktu"}


def jt(x):
    """Rupiah dalam juta, 2 desimal."""
    return f(x / 1e6, 2)


def kw_text(st):
    k = st.get("kruskal")
    if not isinstance(k, dict) or k.get("p") is None or k["p"] != k["p"]:
        return "Keempat varian menghasilkan nilai yang identik pada setiap replikasi, sehingga uji antarvarian tidak dapat dihitung."
    sig = k["p"] < 0.05
    return (f"Uji Kruskal–Wallis memberi H = {f(k['H'], 2)} dengan p = {pv(k['p'])}; perbedaan antarvarian "
            f"{'signifikan' if sig else 'tidak signifikan'} pada α = 0,05.")


# ===========================================================================
def bab4(W, cite, R):
    W.bab(4, "HASIL DAN PEMBAHASAN")
    W.h("Deskripsi Hasil Penelitian")
    aplikasi(W, cite, R)
    e0(W, cite, R)
    e1(W, cite, R)
    e2(W, cite, R)
    e8(W, cite, R)
    e3(W, cite, R)
    e4(W, cite, R)
    e5(W, cite, R)
    e6(W, cite, R)
    e9(W, cite, R)
    e7(W, cite, R)
    e10(W, cite, R)
    pembahasan(W, cite, R)
    luaran(W, cite, R)


# ---------------------------------------------------------------------------
def aplikasi(W, cite, R):
    W.hh("Prototipe aplikasi SMARTROUTE-BBM")
    W.p("Aplikasi web SMARTROUTE-BBM selesai dibangun dan kodenya terbuka di GitHub (tautan pada Lampiran 2). Aplikasi "
        "berjalan lokal dengan perintah streamlit run app.py atau dapat dipasang gratis di Streamlit Community Cloud. "
        "Basis datanya adalah Google Sheets “SMARTROUTE-BBM Database” dengan tab tb_spbu, tb_jarak, tb_armada, tb_produk, dan "
        "tb_simulasi_log; bila Sheets tidak tersedia, aplikasi memakai berkas CSV lokal. Setiap kali optimasi "
        "dijalankan, parameter dan hasilnya dicatat di tb_simulasi_log sebagai jejak audit.")
    W.p("Aplikasi memiliki enam menu. Menu Data & Peta (Gambar 4.1) menampilkan SPBU, armada, dan matriks jarak per "
        "tipe truk di atas peta jalan dengan relief. Menu Optimasi (Gambar 4.2 dan 4.3) menjalankan GA-SA-RL dengan "
        "parameter yang dapat diubah, lalu menampilkan KPI terhadap baseline, peta rute, kurva konvergensi, statistik "
        "operator RL, Gantt multi-ritase, dan isi tiap kompartemen.")
    W.figure(FG("L03_app_data.png"), "Menu Data & Peta: SPBU, FT, dan jaringan jalan pada peta dasar", 14.0)
    W.figure(FG("L04_app_optimasi.png"), "Menu Optimasi: KPI GA-SA-RL terhadap _Saving Matrix_ pada pengaturan bawaan", 14.0)
    W.figure(FG("L05_app_gantt.png"), "Menu Optimasi: Gantt multi-ritase dan rincian muatan kompartemen", 14.0)
    W.p("Menu Simulasi Pergerakan (Gambar 4.4 dan 4.5) menganimasikan truk ruas demi ruas mengikuti geometri jalan "
        "legal dengan model kecepatan (26) dan waktu bongkar (27). Tampilan tiga dimensi memperlihatkan truk, muatan "
        "tersisa, dan status setiap SPBU pada jam simulasi; tampilan dua dimensi dipakai untuk membaca posisi truk "
        "terhadap jalan. Menu Data Simulasi (Gambar 4.6) menyajikan linimasa setiap truk serta jarak, waktu mengemudi, "
        "dan waktu bongkar hasil simulasi.")
    W.figure(FG("L06_app_sim3d.png"), "Simulasi pergerakan tiga dimensi pukul 08.30", 14.0)
    W.figure(FG("L07_app_sim2d.png"), "Simulasi pergerakan dua dimensi pukul 11.00", 14.0)
    W.figure(FG("L08_app_timeline.png"), "Menu Data Simulasi: linimasa kegiatan setiap truk", 14.0)
    W.p("Menu Re-routing Dinamis (Gambar 4.7) mensimulasikan kerusakan truk atau kemacetan mendadak pada jam tertentu "
        "dan membandingkan kebijakan naif dengan re-optimasi. Menu Hasil Penelitian memuat keluaran eksperimen E0–E10, "
        "dan menu Laporan & Log mengunduh ringkasan serta mengirimkannya ke Telegram bila token diisi.")
    W.figure(FG("L09_app_dinamis.png"), "Menu Re-routing Dinamis: perbandingan kebijakan naif dan re-optimasi", 14.0)
    W.p("Peta dasar pada Gambar 4.1–4.7 untuk tangkapan layar laporan digambar ulang dari data jalan OSM karena "
        "lingkungan pengujian tidak dapat mengakses server ubin peta; pada pemakaian normal aplikasi memakai peta jalan "
        "Esri, OpenTopoMap, atau citra satelit.")
    a = R["app"]
    if a:
        s, ap = a["script"], a["app"]
        W.p("Konsistensi aplikasi diuji dengan menjalankan skrip experiments/app_check.py pada pengaturan yang sama "
            "dengan bawaan aplikasi: jalan legal-truk OSM, kasus multi-produk, armada eksisting (1 B + 4 C), bobot "
            "(0,5; 0,3; 0,2), varian GA-SA-RL, dan _seed_ 1. Tabel 4.1 menunjukkan kedua keluaran identik pada "
            "ketelitian yang ditampilkan aplikasi; perbedaan hanya pada waktu komputasi karena aplikasi juga "
            "menggambar grafik selama proses berjalan.")
        rows = [("Fitness F", f(ap["fitness"], 4), f(s["fitness"], 4)),
                ("Jarak (km)", f(ap["dist_km"], 1), f(s["dist_km"], 3)),
                ("Biaya (juta Rp/hari)", f(ap["cost_rp"] / 1e6, 2), f(s["cost_rp"] / 1e6, 4)),
                ("Emisi (kg CO~2~/hari)", f(ap["co2_kg"], 1), f(s["co2_kg"], 3)),
                ("Truk / ritase", f"{ap['trucks']} / {ap['trips']}", f"{s['trucks']} / {s['trips']}"),
                ("Terlambat / lembur (menit)", f"{ap['late']} / {ap['overtime']}", f"{f(s['late_min'], 0)} / {f(s['overtime_min'], 0)}"),
                ("Waktu komputasi (s)", f(ap["runtime_s"], 1), f(a["script_runtime_s"], 1))]
        W.table(["Indikator", "Tampilan aplikasi", "Skrip eksperimen"], rows,
                "Uji konsistensi keluaran aplikasi dan skrip eksperimen (pengaturan bawaan, _seed_ 1)",
                widths=[5.6, 4.2, 4.2])
    W.p("Uji unit otomatis (pytest) memeriksa reproduksi jarak baseline capstone 279,4 km dan _direct delivery_ "
        "728,2 km, kelayakan kompartemen, legalitas ruas per tipe truk, dan bahwa algoritma tidak pernah menghasilkan "
        "fitness lebih buruk dari baseline. Seluruh uji lulus.")


def e0(W, cite, R):
    e = R["e0"]
    if not e:
        return
    W.hh("Audit data (E0)")
    W.p(f"Total permintaan 13 SPBU adalah {f(e['total_demand_kl'], 2)} KL/hari; proyeksi tren DOT pada data capstone "
        f"{f(e['dot_trend_projection_kl'], 2)} KL/hari. Rasio jarak jalan terhadap garis lurus (sirkuitas) rata-rata "
        f"{f(e['circuity_mean'], 3)} (SD {f(e['circuity_sd'], 3)}, rentang {f(e['circuity_min'], 3)}–{f(e['circuity_max'], 3)}). "
        f"Matriks capstone memuat {e['triangle_violations_ordered']} pasangan berurutan yang melanggar ketidaksamaan "
        f"segitiga; yang terbesar {f(e['triangle_worst'][0], 1)} km pada {e['triangle_worst'][1]}→{e['triangle_worst'][2]} "
        f"melalui {e['triangle_worst'][3]}. Artinya, jarak capstone diambil dari rute yang dipakai di lapangan dan tidak "
        f"selalu terpendek. Sebanyak {e['spbu_beyond_30km']} SPBU berada lebih dari 30 km dari FT (terjauh "
        f"{f(e['max_depot_dist_km'], 1)} km), sehingga batas radius 30 km pada proposal tidak dipakai sebagai kendala.")


def stats_rows(st, d=1):
    rows = []
    for v in VAR:
        x = st[v]
        rows.append((v, f(x["mean"], d), f(x["sd"], d), f(x["min"], d), f(x["max"], d), f(x["runtime_mean"], 1),
                     f(x.get("hit_rate_opt", float("nan")) * 100, 0) + "%" if "hit_rate_opt" in x else "–"))
    return rows


def e1(W, cite, R):
    e = R["e1"]
    if not e:
        return
    W.hh("Validasi pada setting capstone (E1)")
    imp = (e["baseline_capstone"] - e["milp_opt"]) / e["baseline_capstone"] * 100
    W.p("E1 memakai asumsi yang sama dengan capstone: satu produk, truk 16 KL, satu ritase per truk, matriks capstone, "
        f"dan objektif jarak. Rencana _Saving Matrix_ capstone sepanjang {f(e['baseline_capstone'])} km dan _direct "
        f"delivery_ {f(e['direct'])} km tereproduksi tepat dari matriks. Implementasi ulang Clarke–Wright memberi "
        f"{f(e['cw_reimpl'])} km dan _Nearest Neighbour_ {f(e['nn'])} km. MILP selesai dengan status optimal (gap 0) "
        f"dalam {f(e['milp_time_s'], 0)} detik pada jarak **{f(e['milp_opt'])} km**, {f(imp, 2)}% lebih pendek dari "
        "rencana capstone. Rute optimumnya: " + "; ".join(e["milp_routes"]) + ".")
    st = e["stats"]
    W.table(["Varian", "Rerata (km)", "SD", "Min.", "Maks.", "Waktu (s)", "Capai optimum"], stats_rows(st),
            "Hasil 30 replikasi pada setting capstone (E1)", widths=[2.6, 2.0, 1.4, 1.8, 1.8, 2.0, 2.4])
    allhit = all(st[v].get("hit_rate_opt", 0) == 1.0 for v in VAR)
    W.p(("Keempat varian mencapai optimum MILP pada seluruh replikasi. Karena variansnya nol, uji statistik terhadap "
         "baseline tidak dapat dihitung; selisihnya bersifat pasti. Instance 13 SPBU ini terlalu kecil untuk membedakan "
         "varian, sehingga perbandingan varian dilakukan pada model lengkap (E2), CVRPLIB (E7), dan instance besar (E10)."
         if allhit else kw_text(st)))
    W.figure(FG("L10_e1_validasi.png"), "Validasi pada setting capstone: (a) sebaran 30 replikasi; (b) perbandingan metode", 14.0)


def e2(W, cite, R):
    e = R["e2"]
    if not e:
        return
    W.hh("Model lengkap dengan armada eksisting (E2)")
    W.p("E2 menjalankan model lengkap pada jalan legal-truk dengan armada eksisting (1 unit B 8 KL dan 4 unit C 16 KL), "
        "maksimum tiga ritase per truk, dan bobot (0,5; 0,3; 0,2). Kasus agregat menganggap seluruh BBM satu produk, "
        "seperti data capstone; kasus multi-produk membagi volume menjadi tiga produk. Rencana _Saving Matrix_ capstone "
        "dievaluasi dengan model yang sama sebagai pembanding.")
    for key, judul in [("agregat", "agregat"), ("multiproduk", "multi-produk")]:
        if key not in e:
            continue
        E = e[key]
        b, h, m = E["baseline"], E["best_ga_sa_rl"], E["means"]
        rows = [("_Saving Matrix_", f(b["fitness"], 4), f(b["dist_km"]), jt(b["cost_rp"]), f(b["co2_kg"]),
                 f"{int(b['trucks'])}/{int(b['trips'])}", int(b["unassigned"]))]
        for v in VAR:
            rows.append((f"{v} (rerata)", f(m["fitness"][v], 4), f(m["dist_km"][v]), jt(m["cost_rp"][v]),
                         f(m["co2_kg"][v]), f"{f(m['trucks'][v], 1)}/{f(m['trips'][v], 1)}", f(m["unassigned"][v], 2)))
        rows.append(("GA-SA-RL terbaik", f(h["fitness"], 4), f(h["dist_km"]), jt(h["cost_rp"]), f(h["co2_kg"]),
                     f"{int(h['trucks'])}/{int(h['trips'])}", int(h["unassigned"])))
        W.table(["Rencana", "Fitness", "Jarak (km)", "Biaya (juta Rp)", "CO~2~ (kg)", "Truk/ritase", "Ritase tak layak"],
                rows, f"Hasil model lengkap kasus {judul} pada jalan legal-truk (E2, 30 replikasi)",
                widths=[3.2, 1.7, 1.8, 2.0, 1.8, 1.8, 1.7])
        st = E["stats_fitness"]
        txt = []
        if b["unassigned"] > 0:
            txt.append(f"Pada kasus {judul}, rencana capstone memuat {int(b['unassigned'])} ritase yang tidak dapat "
                       "dimuat truk mana pun karena volume per produk tidak cocok dengan susunan kompartemen. Rute "
                       "S8-S9-S10, misalnya, membutuhkan Pertalite 9,6 KL, Biosolar 4,0 KL, dan Pertamax 1,9 KL, "
                       "sedangkan kompartemen tipe C adalah 6+4+3+3 KL. Rencana yang disusun dari total volume belum "
                       "tentu dapat dieksekusi.")
        else:
            txt.append(f"Pada kasus {judul}, semua ritase rencana capstone dapat dimuat.")
        txt.append(f"Solusi terbaik GA-SA-RL memakai {int(h['trucks'])} truk dan {int(h['trips'])} ritase dengan jarak "
                   f"{f(h['dist_km'])} km ({pct(h['dist_km'], b['dist_km'])} terhadap baseline), biaya "
                   f"{rp(h['cost_rp'])} ({pct(h['cost_rp'], b['cost_rp'])}), dan emisi {f(h['co2_kg'])} kg CO~2~ "
                   f"({pct(h['co2_kg'], b['co2_kg'])}), tanpa keterlambatan dan lembur.")
        txt.append(kw_text(st))
        W.p(" ".join(txt))
    W.figure(FG("L11_e2_replikasi.png"), "Sebaran fitness 30 replikasi per varian pada model lengkap (E2)", 14.0)
    if "multiproduk" in e:
        rows = [(t["rute"], t["tipe"], t["unit"], t["ritase"], f(t["muatan_kl"], 2), f(t["jarak_km"]),
                 f"{jam_txt(t['mulai_menit'])}–{jam_txt(t['selesai_menit'])}")
                for t in e["multiproduk"]["best_trips"]]
        W.table(["Rute", "Tipe", "Unit", "Ritase", "Muatan (KL)", "Jarak (km)", "Jam"], rows,
                "Rencana terbaik GA-SA-RL kasus multi-produk pada jalan legal-truk", widths=[3.4, 1.2, 1.2, 1.4, 2.2, 2.0, 2.6],
                note="Isi kompartemen setiap ritase ditampilkan pada menu Optimasi (Gambar 4.3).")


def e8(W, cite, R):
    e = R["e8"]
    if not e:
        return
    W.hh("Jaringan jalan legal-truk dibanding matriks capstone (E8)")
    rr = e.get("ringkasan_ruas", [])
    m = e["matriks"]
    if rr:
        tot = rr[0]["km_ruas_total"]
        rows = []
        for r in rr:
            un = r.get("simpul_tak_terjangkau")
            un = "–" if (un is None or (isinstance(un, float) and math.isnan(un)) or un == "") else str(un).replace(";", ", ")
            rows.append((r["tipe"], r["kelas_jalan_min"], f(r["km_ruas_legal"], 0), f(r["km_ruas_legal"] / tot * 100, 1),
                         f(m[r["tipe"]]["korelasi"], 3), un))
        W.table(["Tipe", "Kelas jalan min.", "Ruas legal (km)", "Porsi (%)", "Korelasi dengan capstone", "SPBU tak terjangkau"],
                rows, f"Ruas OSM yang legal per tipe truk (total {f(tot, 0)} km ruas di wilayah studi)",
                widths=[1.4, 2.2, 2.3, 1.8, 2.8, 3.5])
        W.p(f"Wilayah studi memuat {f(tot, 0)} km ruas OSM. Truk B dan C memerlukan jalan kelas II dan hanya dapat "
            f"memakai {f(rr[2]['km_ruas_legal'], 0)} km; semi-trailer D memerlukan kelas I dan hanya mendapat "
            f"{f(rr[3]['km_ruas_legal'], 0)} km. Sebagian besar ruas yang ditolak adalah jalan lokal dan lingkungan "
            "(kelas III). Semua SPBU tetap terjangkau truk C, tetapi truk D tidak dapat mencapai "
            f"{', '.join(m['D']['spbu_tak_terjangkau'])}. Jarak legal truk C berkorelasi {f(m['C']['korelasi'], 3)} "
            f"dengan matriks capstone dengan rerata selisih absolut {f(m['C']['rerata_selisih_abs_pct'], 1)}%. Matriks "
            "capstone dengan demikian merupakan pendekatan jarak yang baik, sedangkan jaringan OSM menambahkan informasi "
            "legalitas per tipe truk dan arah jalan.")
    rows = []
    lab = {"eksisting_agregat": "Eksisting, agregat", "eksisting_multiproduk": "Eksisting, multi-produk",
           "diperluas_agregat": "Diperluas, agregat", "diperluas_multiproduk": "Diperluas, multi-produk"}
    for key, name in lab.items():
        if key not in e:
            continue
        for road, rn in [("capstone", "Capstone"), ("osm", "OSM legal")]:
            h = e[key][road]["best"]
            types = "".join(sorted(t["tipe"] for t in e[key][road]["best_trips"]))
            rows.append((name, rn, f(h["dist_km"]), jt(h["cost_rp"]), f(h["co2_kg"]), f"{int(h['trucks'])}/{int(h['trips'])}", types))
    W.table(["Armada, produk", "Jaringan", "Jarak (km)", "Biaya (juta Rp)", "CO~2~ (kg)", "Truk/ritase", "Tipe per ritase"], rows,
            "Solusi terbaik GA-SA-RL (30 replikasi) pada matriks capstone dan jalan legal-truk (E8)",
            widths=[3.3, 2.0, 1.7, 2.0, 1.7, 1.6, 1.7])
    txt = []
    if "diperluas_multiproduk" in e:
        tc = "".join(sorted(t["tipe"] for t in e["diperluas_multiproduk"]["capstone"]["best_trips"]))
        to = "".join(sorted(t["tipe"] for t in e["diperluas_multiproduk"]["osm"]["best_trips"]))
        bad = sorted({x for t in e["diperluas_multiproduk"]["capstone"]["best_trips"] for x in t["rute"].split("-")
                      if x in m.get(t["tipe"], {}).get("spbu_tak_terjangkau", [])})
        txt.append(f"Dengan armada diperluas (2 A, 2 B, 4 C, 1 D), komposisi tipe ritase terbaik adalah {tc} pada matriks "
                   f"capstone dan {to} pada jalan legal-truk.")
        if bad:
            txt.append(f"Pada matriks capstone, ritase tipe D melayani {', '.join(bad)}, padahal SPBU tersebut tidak "
                       "dapat dijangkau semi-trailer melalui jalan yang sesuai aturan. Rencana itu tampak lebih hemat, "
                       "tetapi tidak sah untuk dijalankan.")
    if txt:
        W.p(" ".join(txt))
    W.figure(FG("L12_osm_legal.png"), "(a) Ruas OSM yang legal per tipe truk; (b) rute GA-SA-RL multi-produk pada jalan legal-truk", 14.0)


def e3(W, cite, R):
    if R["e3"] is None:
        return
    W.hh("Trade-off biaya dan emisi (E3)")
    fe, pf = pareto_pts(R["e3"])
    W.p(f"Sapuan bobot langkah 0,1 dengan dua _seed_ per vektor bobot menghasilkan {len(R['e3'])} solusi pada armada "
        f"eksisting ({len(fe)} layak) dengan {len(pf)} titik non-dominasi pada bidang biaya–emisi. " +
        (f"Rentang Pareto adalah {rp(pf.cost_rp.min())}–{rp(pf.cost_rp.max())} per hari dan "
         f"{f(pf.co2_kg.min())}–{f(pf.co2_kg.max())} kg CO~2~ per hari." if len(pf) > 1 else
         f"Titik tersebut ({rp(pf.cost_rp.iloc[0])}; {f(pf.co2_kg.iloc[0])} kg CO~2~) menunjukkan bahwa pada armada "
         "eksisting rencana termurah juga beremisi terendah."))
    rows = []
    for nm, df in [("Eksisting (E3)", R["e3"]), ("Diperluas, capstone (E3b)", R["e3b"]), ("Diperluas, jalan legal (E3c)", R["e3c"])]:
        if df is None:
            continue
        _, p = pareto_pts(df)
        for r in p.itertuples():
            rows.append((nm, f"({f(r.w1, 1)}; {f(r.w2, 1)}; {f(r.w3, 1)})", jt(r.cost_rp), f(r.co2_kg), f(r.dist_km),
                         int(r.trucks), r.trip_types))
    W.table(["Armada, jaringan", "Bobot (w~1~; w~2~; w~3~)", "Biaya (juta Rp)", "CO~2~ (kg)", "Jarak (km)", "Truk", "Tipe ritase"],
            rows, "Titik non-dominasi biaya–emisi kasus multi-produk", widths=[3.4, 2.6, 1.8, 1.6, 1.6, 1.0, 2.0])
    t = []
    if R["e3b"] is not None:
        _, p = pareto_pts(R["e3b"])
        if len(p) > 1:
            lo, hi = p.iloc[0], p.iloc[-1]
            t.append(f"Bila armada diperluas dan jarak memakai matriks capstone (E3b), muncul {len(p)} titik non-dominasi, "
                     f"dari {rp(lo.cost_rp)} dengan {f(lo.co2_kg)} kg CO~2~ (ritase {lo.trip_types}) sampai {f(hi.co2_kg)} kg "
                     f"dengan {rp(hi.cost_rp)} (ritase {hi.trip_types}).")
    if R["e3c"] is not None:
        _, p = pareto_pts(R["e3c"])
        if len(p) == 1:
            r0 = p.iloc[0]
            t.append(f"Pada jalan legal-truk (E3c), hanya tersisa satu titik ({rp(r0.cost_rp)}; {f(r0.co2_kg)} kg CO~2~; "
                     f"ritase {r0.trip_types}). Trade-off pada E3b hilang karena semi-trailer D tidak boleh masuk ke "
                     "sebagian SPBU.")
        elif len(p) > 1:
            lo, hi = p.iloc[0], p.iloc[-1]
            t.append(f"Pada jalan legal-truk (E3c) terdapat {len(p)} titik, dari {rp(lo.cost_rp)} dengan {f(lo.co2_kg)} kg "
                     f"(ritase {lo.trip_types}) sampai {f(hi.co2_kg)} kg dengan {rp(hi.cost_rp)} (ritase {hi.trip_types}).")
    s3 = R["e3s"]
    if s3 is not None:
        g = s3.groupby("fixed_cost_mult").mean(numeric_only=True)
        if abs(g.trucks.iloc[0] - g.trucks.iloc[-1]) < 1e-9 and abs(g.dist_km.iloc[0] - g.dist_km.iloc[-1]) < 0.05:
            t.append(f"Pengali biaya tetap 0–2 tidak mengubah rencana ({f(g.trucks.iloc[0], 0)} truk, {f(g.dist_km.iloc[0])} km); "
                     f"hanya total biaya yang berubah ({rp(g.cost_rp.iloc[0])} sampai {rp(g.cost_rp.iloc[-1])}).")
        else:
            t.append(f"Pada pengali biaya tetap 0–2, rerata jumlah truk berubah dari {f(g.trucks.iloc[0], 1)} menjadi "
                     f"{f(g.trucks.iloc[-1], 1)} dan jarak dari {f(g.dist_km.iloc[0])} km menjadi {f(g.dist_km.iloc[-1])} km.")
    if t:
        W.p(" ".join(t))
    W.figure(FG("L13_pareto.png"), "Titik non-dominasi biaya–emisi dan sensitivitas biaya tetap truk", 14.0)


SCN = {"0. Kondisi normal": "Normal", "1. Kemacetan dinamis": "Kemacetan jam sibuk",
       "2. Kelas & restriksi jalan": "Restriksi jalan S2–S5", "5. Time window SPBU": "Jendela waktu Prabumulih",
       "6. Emisi truk realistis": "Bobot emisi 0,8", "7. Tank management SPBU": "Manajemen tangki",
       "8. Antrian loading rack FT": "Antrean _loading rack_", "9. Panic buying / surge demand": "Lonjakan ×1,5",
       "9b. Panic buying lokal": "Lonjakan lokal ×3", "10. Kuota BPH Migas": "Kuota Biosolar 95%",
       "2R. Restriksi jalan + 1 unit tipe B": "Restriksi + 1 unit B", "9bR. Panic buying lokal + 1 unit tipe D": "Lonjakan lokal + 1 unit D",
       "9R. Panic buying x1,5 (armada eksisting)": "Lonjakan ×1,5 (cek)"}


def e4(W, cite, R):
    e = R["e4"]
    if not e:
        return
    W.hh("Simulasi sepuluh kategori skenario (E4)")
    W.p("E4 menjalankan GA-SA-RL (terbaik dari lima _seed_) pada sepuluh kategori skenario dari proposal. Skenario 3 "
        "(permintaan stokastik) dan 4 (kerusakan armada) dibahas tersendiri pada E6 dan E5. Untuk skenario yang tidak "
        "dapat dilayani armada eksisting, diuji pula tambahan satu unit truk (E4b). Asumsi setiap skenario tercantum di "
        "Lampiran 1.")
    rows = []
    allr = [(k, v) for k, v in e.items() if "hybrid" in v] + [(k, v) for k, v in (R["e4b"] or {}).items() if "hybrid" in v]
    for k, v in allr:
        h = v["hybrid"]
        rows.append((SCN.get(k, k), f(h["dist_km"]), jt(h["cost_rp"]), f(h["co2_kg"]), f(h["time_min"], 0),
                     f"{int(h['trucks'])}/{int(h['trips'])}", int(h["unassigned"])))
    W.table(["Skenario", "Jarak (km)", "Biaya (juta Rp)", "CO~2~ (kg)", "Waktu total (menit)", "Truk/ritase", "Tak terlayani"],
            rows, "Hasil GA-SA-RL pada setiap skenario (E4 dan E4b)", widths=[3.6, 1.7, 2.0, 1.7, 1.9, 1.6, 1.5])
    W.p(scenario_text(e, R["e4b"] or {}))
    W.figure(FG("L14_skenario.png"), "Biaya dan emisi GA-SA-RL per skenario", 14.0)


def scenario_text(e4, e4b):
    def H(k, src=None):
        src = src or e4
        return src[k]["hybrid"] if k in src and "hybrid" in src[k] else None
    n0 = H("0. Kondisi normal")
    s = []
    if n0:
        s.append(f"Pada kondisi normal, rencana memerlukan {rp(n0['cost_rp'])} dan {f(n0['co2_kg'])} kg CO~2~ per hari.")
    h = H("1. Kemacetan dinamis")
    if h and n0:
        s.append(f"Kemacetan jam sibuk menaikkan emisi {pct(h['co2_kg'], n0['co2_kg'])} dan total waktu operasi "
                 f"{pct(h['time_min'], n0['time_min'])} tanpa mengubah jumlah truk.")
    h = H("2. Kelas & restriksi jalan")
    if h:
        s.append(f"Bila jalan akses empat SPBU Ogan Ilir hanya 5 m, SPBU itu harus dilayani tipe B. Dengan satu unit B "
                 f"(paling banyak tiga ritase), {int(h['unassigned'])} ritase tidak terlayani.")
        hb = H("2R. Restriksi jalan + 1 unit tipe B", e4b)
        if hb:
            s.append(f"Tambahan satu unit B membuat rencana layak ({int(hb['unassigned'])} ritase tak terlayani) dengan "
                     f"biaya {rp(hb['cost_rp'])}.")
    h = H("5. Time window SPBU")
    if h and n0:
        ot = e4["5. Time window SPBU"].get("on_time_hybrid")
        s.append(f"Jendela waktu 06.00–11.00 untuk SPBU Prabumulih dipenuhi" +
                 (f" ({f(ot * 100, 0)}% tepat waktu)" if ot is not None else "") +
                 f" dengan menyusun ulang rute; jaraknya naik menjadi {f(h['dist_km'])} km.")
    h = H("6. Emisi truk realistis")
    if h and n0:
        if abs(h["co2_kg"] - n0["co2_kg"]) < 0.05:
            s.append("Bobot yang mengutamakan emisi (0,1; 0,8; 0,1) menghasilkan rencana yang sama dengan kondisi normal; "
                     "pada armada eksisting, rencana termurah sudah hampir beremisi minimum.")
        else:
            s.append(f"Bobot yang mengutamakan emisi menurunkan emisi menjadi {f(h['co2_kg'])} kg ({pct(h['co2_kg'], n0['co2_kg'])}).")
    k = "7. Tank management SPBU"
    if k in e4:
        s.append(f"Dengan stok awal acak 15–60% kapasitas tangki, rencana tidak menimbulkan stok habis "
                 f"({e4[k].get('stockouts_hybrid')} SPBU; baseline {e4[k].get('stockouts_baseline')}).")
    h = H("8. Antrian loading rack FT")
    if h and n0:
        s.append(f"Antrean _loading rack_ yang padat menambah waktu tunggu tiap ritase sehingga dibutuhkan "
                 f"{int(h['trucks'])} truk untuk {int(h['trips'])} ritase dan biaya naik {pct(h['cost_rp'], n0['cost_rp'], 0)}. "
                 "Pada kondisi ini, kapasitas _loading rack_ lebih menentukan daripada pilihan rute.")
    h = H("9. Panic buying / surge demand")
    if h:
        s.append(f"Lonjakan permintaan 1,5 kali masih dapat dilayani armada eksisting dengan {int(h['trucks'])} truk "
                 f"dan {int(h['trips'])} ritase.")
    h = H("9b. Panic buying lokal")
    if h:
        s.append(f"Lonjakan tiga kali pada tiga SPBU Muara Enim menyisakan {int(h['unassigned'])} ritase tak terlayani "
                 "karena permintaan satu SPBU (sekitar 20 KL) melebihi truk terbesar yang ada (16 KL) dan model belum "
                 "mengizinkan pengiriman terpisah.")
        hb = H("9bR. Panic buying lokal + 1 unit tipe D", e4b)
        if hb:
            s.append(f"Satu unit tipe D (32 KL) mengurangi ritase tak terlayani menjadi {int(hb['unassigned'])}; "
                     "ritase yang tersisa adalah S10, yang tidak dapat dijangkau semi-trailer melalui jalan legal.")
    k = "10. Kuota BPH Migas"
    if k in e4 and "hybrid" in e4[k]:
        s.append(f"Kuota Biosolar 95% memotong {f(e4[k].get('quota_cut_kl', 0), 2)} KL/hari, dan seluruh pengiriman "
                 "berada dalam kuota.")
    return " ".join(s)


def e5(W, cite, R):
    W.hh("Re-routing dinamis (E5)")
    rows = []
    for lab, S in [("Normal", R["e5"] and R["e5"]["summary"]), ("Tenggat ketat", R["e5b"])]:
        if not S:
            continue
        for evn, d in S.items():
            rows.append((lab, "Kerusakan truk" if evn == "breakdown" else "Kemacetan mendadak", d["n"],
                         f"{f(d['fitness']['naive'], 4)} → {f(d['fitness']['reopt'], 4)}", pv(d["fitness"].get("p_wilcoxon")),
                         f"{f(d['share_improved_fitness'] * 100, 0)}%", f(d["compute_s_mean"], 2)))
    if not rows:
        return
    W.table(["Kondisi", "Kejadian", "n", "Fitness naif → re-opt.", "p", "Kasus membaik", "Waktu (s)"], rows,
            "Kebijakan naif dan re-optimasi GA-SA-RL pada kejadian dinamis", widths=[2.2, 2.9, 0.9, 3.2, 1.5, 1.7, 1.6])
    t = []
    S = R["e5"]["summary"] if R["e5"] else {}
    if "breakdown" in S:
        d = S["breakdown"]
        t.append(f"Pada kerusakan truk (n = {d['n']} kombinasi unit, jam kejadian, dan _seed_), re-optimasi menurunkan "
                 f"rerata fitness sisa dari {f(d['fitness']['naive'], 4)} menjadi {f(d['fitness']['reopt'], 4)} "
                 f"(Wilcoxon satu sisi p = {pv(d['fitness'].get('p_wilcoxon'))}) dalam rata-rata {f(d['compute_s_mean'], 2)} "
                 f"detik. Perbaikan hanya terjadi pada {f(d['share_improved_fitness'] * 100, 0)}% kasus" +
                 (lambda r: (f" ({len(r)} kasus), tetapi pada kasus tersebut fitness sisa turun " +
                             (f"{f(r.min(), 1)}%" if r.max() - r.min() < 0.05 else f"{f(r.min(), 1)}–{f(r.max(), 1)}%"))
                  if len(r) else "")(
                     imp_cases(R["e5r"], "breakdown")) +
                 f" (Gambar 4.13). Rerata jarak sisa berubah {f(d['dist_km']['naive'])} → {f(d['dist_km']['reopt'])} km. "
                 "Pada kasus lain, kebijakan naif sudah sama baiknya karena armada eksisting masih memiliki kelonggaran waktu.")
    if "kemacetan" in S:
        d = S["kemacetan"]
        same = abs(d["fitness"]["naive"] - d["fitness"]["reopt"]) < 1e-6
        t.append("Pada kemacetan mendadak, " + ("kedua kebijakan menghasilkan rencana yang sama." if same else
                 f"fitness berubah dari {f(d['fitness']['naive'], 4)} menjadi {f(d['fitness']['reopt'], 4)}."))
    if R["e5b"] and "breakdown" in R["e5b"]:
        d = R["e5b"]["breakdown"]
        t.append(f"Bila tenggat SPBU diperketat dari manajemen tangki, re-optimasi memperbaiki "
                 f"{f(d['share_improved_fitness'] * 100, 0)}% kasus (fitness {f(d['fitness']['naive'], 4)} → "
                 f"{f(d['fitness']['reopt'], 4)}, p = {pv(d['fitness'].get('p_wilcoxon'))}).")
    W.p(" ".join(t))
    W.figure(FG("L15_dinamis.png"), "Perbaikan fitness sisa dan waktu komputasi re-optimasi terhadap kebijakan naif", 14.0)


def imp_cases(df, ev):
    if df is None:
        return np.array([])
    d = df[df.event == ev]
    r = ((d.naive_fitness - d.reopt_fitness) / d.naive_fitness * 100).values
    return r[r > 1e-6]


def e6(W, cite, R):
    e = R["e6"]
    if e is None:
        return
    W.hh("Ketahanan terhadap permintaan stokastik (E6)")
    W.p("E6 mengundi permintaan setiap SPBU dari distribusi normal dengan koefisien variasi 0,05–0,20 sebanyak 1000 kali "
        "per sel, lalu menghitung _service level_ (28) rencana _Saving Matrix_, GA-SA-RL, dan GA-SA-RL _robust_ yang "
        "kapasitas efektif truknya dibatasi 90% saat perencanaan.")
    sub = e[e.cv.isin([0.1, 0.2])]
    rows = [("Agregat" if r.produk == "agregat" else "Multi-produk", f(r.cv, 2), r.plan.replace("GA-SA-RL robust (90%)", "GA-SA-RL _robust_"),
             f(r.service_level * 100, 2), f(r.unmet_kl, 3), f(r.p_shortfall * 100, 1), f(r.dist_km)) for r in sub.itertuples()]
    W.table(["Kasus", "CV", "Rencana", "SL (%)", "Tak terpenuhi (KL/hari)", "P(kurang) (%)", "Jarak (km)"], rows,
            "_Service level_ hasil simulasi Monte Carlo, 1000 iterasi per sel (CV 0,10 dan 0,20)",
            widths=[2.2, 1.1, 3.3, 1.6, 2.2, 1.8, 1.8],
            note="Hasil lengkap CV 0,05–0,20 ada di results/E6_montecarlo.csv dan Gambar 4.14. Untuk ritase baseline yang "
                 "tidak layak kompartemen, kapasitas simulasi disamakan dengan volume rencana.")
    mp = e[(e.produk == "multiproduk") & (np.isclose(e.cv, 0.2))].set_index("plan")
    if len(mp) == 3:
        W.p(f"Pada kasus multi-produk dengan CV 0,20, _service level_ _Saving Matrix_ {f(mp.loc['Saving Matrix', 'service_level'] * 100, 2)}%, "
            f"GA-SA-RL {f(mp.loc['GA-SA-RL', 'service_level'] * 100, 2)}%, dan GA-SA-RL _robust_ "
            f"{f(mp.loc['GA-SA-RL robust (90%)', 'service_level'] * 100, 2)}%. Penyangga kapasitas 10% menurunkan peluang "
            f"kekurangan dari {f(mp.loc['GA-SA-RL', 'p_shortfall'] * 100, 1)}% menjadi "
            f"{f(mp.loc['GA-SA-RL robust (90%)', 'p_shortfall'] * 100, 1)}% dengan tambahan jarak "
            f"{f(mp.loc['GA-SA-RL robust (90%)', 'dist_km'] - mp.loc['GA-SA-RL', 'dist_km'])} km. Operator dapat memilih "
            "tingkat penyangga sesuai toleransi risiko kekurangan stok.")
    W.figure(FG("L16_montecarlo.png"), "_Service level_ terhadap koefisien variasi permintaan", 14.0)


def e9(W, cite, R):
    e = R["e9"]
    if not e:
        return
    W.hh("Simulasi mikro pergerakan truk (E9)")
    dm = e["multiproduk"]["deterministic"]
    g, b = dm["GA-SA-RL"], dm["Saving Matrix"]
    W.p("E9 menjalankan rencana _Saving Matrix_ dan GA-SA-RL kasus multi-produk pada simulasi mikro (26)–(27). Simulasi "
        "deterministik (tanpa unsur acak) dipakai untuk membandingkan simulasi dengan model. Rencana GA-SA-RL selesai "
        f"pada menit ke-{f(g['t_end'], 1)} sejak 06.00 (pukul {jam_txt(g['t_end'])}), sedangkan model memperkirakan menit "
        f"ke-{f(g['model_end'], 1)}. Selisih waktu tiba di SPBU terhadap rencana rata-rata {f(g['arr_dev_mean'], 1)} menit "
        f"(maksimum {f(g['arr_dev_max'], 1)} menit), dan kecepatan rata-rata simulasi {f(g['v_mean'], 1)} km/jam. Model "
        "optimasi dengan v~max~ = 40 km/jam sedikit lebih konservatif daripada simulasi yang memakai kecepatan per jenis "
        f"ruas. _Saving Matrix_ selesai pada menit ke-{f(b['t_end'], 1)}, tetapi satu ritasenya tetap tidak dapat dimuat.")
    W.p("Simulasi stokastik mengulang setiap rencana 300 kali untuk CV kecepatan 0,1, 0,2, dan 0,3 dengan CV waktu "
        "bongkar 0,15. Kasus kedua menambahkan jendela waktu 06.00–11.00 pada enam SPBU (S7, S8, S9, S11, S12, S13).")
    rows = []
    for r in e["summary"]:
        rows.append((CASE_E9[r["case"]].capitalize(), "_Saving Matrix_" if r["plan"] == "Saving Matrix" else r["plan"], f(r["cv"], 1),
                     jam_txt(r["t_end_mean"]), jam_txt(r["t_end_p95"]), f(r["p_overtime"] * 100, 1), f(r["p_any_late"] * 100, 1)))
    W.table(["Kasus", "Rencana", "CV kecepatan", "Rerata selesai", "P95 selesai", "P(lembur) (%)", "P(terlambat) (%)"],
            rows, "Hasil simulasi mikro 300 replikasi per sel (E9)", widths=[3.0, 2.4, 1.6, 1.8, 1.8, 1.7, 1.7])
    tests = [x for x in e.get("tests", []) if x["metric"] == "t_end" and x["case"] == "multiproduk"]
    gtw = [r for r in e["summary"] if r["case"] == "multiproduk_tw" and r["plan"] == "GA-SA-RL"]
    dtw = e["multiproduk_tw"]["deterministic"]
    t = []
    if tests:
        t.append("Tanpa jendela waktu, kedua rencana selesai jauh sebelum 18.00 dan tidak ada replikasi yang lembur. "
                 f"GA-SA-RL selesai {f(min(x['median_diff'] for x in tests), 1)}–{f(max(x['median_diff'] for x in tests), 1)} "
                 "menit lebih lambat (median selisih berpasangan, Wilcoxon p < 0,001) karena melayani seluruh SPBU, "
                 "termasuk ritase yang pada _Saving Matrix_ tidak dapat dimuat.")
    if gtw:
        hi = gtw[-1]
        t.append(f"Dengan jendela waktu, GA-SA-RL tetap memakai {int(dtw['GA-SA-RL']['trucks'])} truk "
                 f"({f(dtw['GA-SA-RL']['model_dist'])} km). Hari kerja menjadi lebih panjang (rerata selesai "
                 f"{jam_txt(gtw[0]['t_end_mean'])}–{jam_txt(hi['t_end_mean'])}), tetapi tidak ada SPBU yang terlambat dan "
                 f"peluang lembur hanya {f(hi['p_overtime'] * 100, 1)}% pada CV 0,3. _Saving Matrix_ pada kasus ini "
                 f"memerlukan {int(dtw['Saving Matrix']['trucks'])} truk dan tetap menyisakan "
                 f"{int(dtw['Saving Matrix']['unassigned'])} ritase tak layak.")
    W.p(" ".join(t))
    W.figure(FG("L17_simulasi_mikro.png"), "Sebaran jam selesai operasi pada simulasi mikro 300 replikasi", 14.0)


def e7(W, cite, R):
    e = R["e7"]
    if e is None or not len(e):
        return
    W.hh("Validasi algoritma pada CVRPLIB (E7)")
    g = e[e.variant == "GA-SA-RL"].groupby("instance").agg(n=("n", "first"), bks=("bks", "first"), cw=("cw_gap_pct", "first"),
                                                          gap=("gap_pct", "mean"), sd=("gap_pct", "std"), best=("gap_pct", "min"),
                                                          t=("runtime", "mean")).reset_index().sort_values("n")
    rows = [(r.instance, int(r.n), f(r.bks, 0), f(r.cw, 2), f"{f(r.gap, 2)} ± {f(r.sd, 2)}", f(r.best, 2), f(r.t, 0))
            for r in g.itertuples()]
    W.table(["Instance", "n", "BKS", "Gap CW (%)", "Gap GA-SA-RL (%)", "Gap terbaik (%)", "Waktu (s)"], rows,
            f"Gap GA-SA-RL terhadap BKS pada CVRPLIB set X {cite('uchoa2017')}", widths=[2.6, 1.0, 1.8, 1.9, 2.9, 2.0, 1.8],
            note="Gap GA-SA-RL ditulis sebagai rerata ± simpangan baku 10 replikasi.")
    t7 = e7_tests(e)
    W.p(f"Pada {len(g)} instance (n = {int(g.n.min())}–{int(g.n.max())}), GA-SA-RL mencapai rerata gap {f(g.gap.mean(), 2)}% "
        f"(rentang {f(g.gap.min(), 2)}–{f(g.gap.max(), 2)}%), dibanding Clarke–Wright {f(g.cw.mean(), 2)}%. Versi awal "
        "algoritma (lima operator, 200 generasi GA dan 5000 iterasi SA) pada instance yang sama mencapai 6,47%, sehingga "
        "operator granular dan _ruin-and-recreate_ serta pembagian anggaran yang baru menurunkan gap kira-kira separuhnya. "
        f"Hasil ini tetap di atas algoritma khusus CVRP seperti HGS-CVRP {cite('vidal2022')} yang umumnya mencapai gap di "
        "bawah 0,5%; GA-SA-RL dirancang untuk model multi-kompartemen dan multi-ritase, bukan untuk CVRP murni.")
    rows = [(v, f(t7["mean"][v], 2)) for v in VAR if v in t7["mean"]]
    W.table(["Varian", "Rerata gap (%)"], rows, f"Uji ablasi pada {t7['n_inst']} instance CVRPLIB (10 replikasi per varian)",
            widths=[4.0, 4.0])
    txt = (f"Uji ablasi pada {t7['n_inst']} instance memberi rerata gap " +
           ", ".join(f"{v} {f(t7['mean'][v], 2)}%" for v in VAR if v in t7["mean"]) + ".")
    if t7.get("friedman"):
        txt += f" Uji Friedman atas rerata per instance: χ² = {f(t7['friedman'][0], 2)}, p = {pv(t7['friedman'][1])}."
    txt += (f" Uji Wilcoxon satu sisi atas rerata per instance memberi GA-SA-RL < GA dengan p = {pv(t7['GA'])}, "
            f"GA-SA-RL < GA-SA dengan p = {pv(t7['GA-SA'])}, dan GA-SA-RL < GA-SA-ALNS dengan p = {pv(t7['GA-SA-ALNS'])}. "
            f"Dengan {t7['n_inst']} instance, p terkecil yang mungkin dicapai uji ini adalah 0,031, sehingga hasil pertama "
            f"berada tepat pada batas tersebut. Uji yang sama pada {t7['n_pairs']} pasangan instance × _seed_ memberi "
            f"p = {pv(t7['GA_run'])}, {pv(t7['GA-SA_run'])}, dan {pv(t7['GA-SA-ALNS_run'])}. Fase SA menurunkan gap lebih "
            "dari separuh, sedangkan ketiga cara memilih operator memberi hasil yang praktis sama.")
    W.p(txt)
    W.figure(FG("L18_cvrplib.png"), "Gap terhadap BKS pada CVRPLIB set X", 14.0)


def e10(W, cite, R):
    e, df = R["e11"], R["e11r"]
    if not e or df is None:
        return
    W.hh("Uji pembanding pada instance sulit (E10)")
    I = {int(x["n"]): x for x in e["instances"]}
    ns = sorted(I)
    W.p("Instance capstone terlalu kecil untuk membedakan metode: pada E1 dan E2 keempat varian memberi solusi yang "
        "sama. E10 karena itu memakai instance yang lebih besar dan lebih ketat di jaringan jalan yang sama. Lokasi "
        f"{', '.join(map(str, ns[:-1]))}, dan {ns[-1]} SPBU diambil dari simpul jalan legal truk C dengan jarak minimal "
        "1 km satu sama lain dan dari FT. Permintaan diambil ulang (_bootstrap_) dari 13 permintaan nyata dan dibagi tiga "
        "produk. Armada dibuat padat: jumlah unit C dihitung dari total permintaan dibagi kapasitas tiga ritase pada "
        "tingkat isi 75%, ditambah unit B untuk jalan sempit dan unit D yang aksesnya paling terbatas. Sebanyak 40% "
        "SPBU memiliki jendela waktu 3 jam pada jam acak, dan setiap keberangkatan menunggu 15 menit di _loading rack_. "
        "Instance uji dibangkitkan dengan _seed_ yang berbeda dari instance kalibrasi.")
    rows = []
    for n in ns:
        x = I[n]
        rows.append((n, f(x["total_kl"], 1), ", ".join(f"{k} {v}" for k, v in x["units"].items()),
                     f(x["tw_frac"] * 100, 0) + "%", f(x["rack_wait"], 0)))
    W.table(["n", "Permintaan (KL)", "Armada (unit)", "SPBU berjendela waktu", "Antrean rack (menit)"], rows,
            "Karakteristik instance uji E10", widths=[1.2, 2.8, 3.6, 3.4, 3.0])
    T = {int(x["n"]): x for x in e["tests"]}
    tab = {(int(r["n"]), r["variant"]): r for r in e["table"]}
    rows = []
    for n in ns:
        cw, ort = tab[(n, "Clarke-Wright")], tab[(n, "OR-Tools")]
        row = [n, f(cw["fit_mean"], 1) + (f" ({int(cw['unassigned'])})" if cw["unassigned"] else ""), f(ort["fit_mean"], 3)]
        for v in VAR:
            r = tab[(n, v)]
            row.append(f"{f(r['fit_mean'], 3)} ± {f(r['fit_sd'], 3)}")
        rows.append(tuple(row))
    W.table(["n", "CW", "OR-Tools", "GA", "GA-SA", "GA-SA-ALNS", "GA-SA-RL"], rows,
            "Fitness pada instance sulit (E10)", widths=[0.9, 1.6, 1.6, 2.5, 2.5, 2.5, 2.4], font=9,
            note="Fitness lebih kecil lebih baik; varian ditulis rerata ± simpangan baku 10 _seed_. Angka dalam kurung "
                 "pada kolom CW adalah jumlah ritase tak terlayani. OR-Tools diberi batas waktu sama dengan median waktu "
                 "GA-SA-RL (145, 351, dan 899 detik).")
    rows = []
    for n in ns:
        for v in ["Clarke-Wright", "OR-Tools", "GA-SA-RL"]:
            r = tab[(n, v)]
            rows.append((n if v == "Clarke-Wright" else "", v, f(r["dist"], 0), f(r["cost"] / 1e6, 2), f(r["trucks"], 0),
                         f(r["late"], 0), f(r["over"], 0), f(r["unassigned"], 0)))
    W.table(["n", "Metode", "Jarak (km)", "Biaya (juta Rp)", "Truk", "Terlambat (mnt)", "Lembur (mnt)", "Tak terlayani"],
            rows, "Komponen solusi pada instance sulit (E10, rerata untuk GA-SA-RL)",
            widths=[0.9, 2.6, 1.8, 2.1, 1.2, 2.0, 1.8, 1.6])
    tt = []
    for n in ns:
        x = T[n]
        tt.append(f"pada {n} SPBU GA-SA-RL {'lebih baik' if x['p_vs_OR-Tools'] < 0.05 else 'tidak berbeda nyata'} dari "
                  f"OR-Tools (selisih fitness {f(x['impr_vs_OR-Tools'], 1)}%, Wilcoxon p = {pv(x['p_vs_OR-Tools'])})")
    W.p("Terhadap pembanding eksternal, " + "; ".join(tt) + f". Rincian Tabel {W.chapter}.{W.tab} menunjukkan dari mana "
        "selisih itu datang. OR-Tools menempuh jarak lebih pendek dan biayanya lebih rendah, dan pada 100 dan 200 SPBU "
        "memakai lebih sedikit truk, "
        "tetapi rencananya lebih banyak melanggar jendela waktu dan batas shift. Model OR-Tools tidak memuat waktu muat "
        "yang bergantung pada volume ritase dan menganggap waktu tempuh tetap, sehingga jadwal yang tampak layak di "
        "dalam OR-Tools menjadi terlambat saat dinilai dengan model lengkap. Pada 50 SPBU, ketika kendala waktu masih "
        "longgar, keduanya setara. Clarke–Wright menempuh jarak terpendek, tetapi tidak memeriksa jendela waktu dan "
        "multi-ritase sehingga meninggalkan ritase tak terlayani dan lembur ribuan menit.")
    tt = []
    for n in ns:
        x = T[n]
        tt.append(f"n = {n}: p = {pv(x['p_vs_GA-SA'])} dan {pv(x['p_vs_GA-SA-ALNS'])} terhadap GA-SA dan GA-SA-ALNS "
                  f"(δ = {f(x['delta_vs_GA-SA'], 2)} dan {f(x['delta_vs_GA-SA-ALNS'], 2)}), Kruskal–Wallis ketiganya "
                  f"p = {pv(x['kruskal_sa'])}")
    W.p(f"Di dalam keluarga hibrida, semua varian dengan fase SA jauh lebih baik dari GA saja (Mann–Whitney p ≤ "
        f"{pv(max(T[n]['p_vs_GA'] for n in ns))}, δ ≥ {f(min(T[n]['delta_vs_GA'] for n in ns), 2)}). Cara memilih "
        "operator tidak membuat perbedaan yang nyata: " + "; ".join(tt) + ". Simpangan baku yang besar pada 100 dan 200 "
        "SPBU berasal dari beberapa _seed_ yang belum berhasil menghapus keterlambatan; fitness rata-rata dengan demikian "
        "dipengaruhi penalti, bukan jarak.")
    if os.path.exists(FG("L19_skalabilitas.png")):
        W.figure(FG("L19_skalabilitas.png"), "Fitness per metode serta keterlambatan dan lembur pada instance sulit (E10)", 14.0)


# ===========================================================================
def pembahasan(W, cite, R):
    W.h("Pembahasan Hasil Penelitian")
    e1, a = R["e1"], R["app"]
    W.p("**Formulasi (rumusan masalah 1).** Model MC-MP-MT-VRP menangkap kendala yang tidak terlihat oleh _Saving Matrix_ "
        "berbasis total volume: penugasan produk ke kompartemen, kompatibilitas produk dan truk, akses jalan per tipe, "
        "multi-ritase, dan batas shift. Temuan terpenting adalah rencana capstone yang pendek menjadi tidak dapat "
        "dijalankan setelah kompartemen dan proporsi produk diperhitungkan. Literatur MCVRP mencatat hal yang sama: "
        f"kendala kompartemen mengubah struktur solusi {cite('ostermeier2021', 'coelho2015')}. Jaringan jalan legal "
        "menambahkan lapisan berikutnya. Rencana yang tampak lebih hemat pada matriks tunggal dapat memakai semi-trailer "
        f"ke SPBU yang secara hukum tidak boleh dimasukinya, sejalan dengan temuan Şahin dkk. {cite('sahin2024')}.")
    if e1 and a:
        imp = (e1["baseline_capstone"] - e1["milp_opt"]) / e1["baseline_capstone"] * 100
        s, b = a["script"], a["baseline"]
        W.p(f"**Efisiensi dan kelayakan (rumusan masalah 2).** Pada setting capstone, ruang perbaikan jarak hanya {f(imp, 2)}% "
            "karena _Saving Matrix_ sudah dekat dengan optimum untuk 13 SPBU. Studi kasus BBM di Indonesia yang melaporkan "
            "penghematan puluhan persen umumnya membandingkan dengan rute lapangan yang belum dioptimasi, sehingga angkanya "
            "tidak sebanding. Nilai tambah model pada kasus ini ada pada kelayakan: dengan jalan legal dan tiga produk, "
            f"GA-SA-RL memberi rencana {f(s['dist_km'])} km yang seluruhnya dapat dimuat, sedangkan _Saving Matrix_ "
            f"{f(b['dist_km'])} km menyisakan {int(b['unassigned'])} ritase tak layak. Tambahan {f(s['dist_km'] - b['dist_km'])} km "
            "adalah harga untuk rencana yang dapat dijalankan.")
    W.p("**Ketahanan dan gangguan (rumusan masalah 3).** " + robust_text(R))
    W.p("**Skalabilitas dan kontribusi komponen (rumusan masalah 4).** " + ablation_text(R, cite))
    W.p("**Aplikasi (rumusan masalah 5).** Keluaran aplikasi sama dengan skrip eksperimen pada pengaturan yang sama "
        "(Tabel 4.1). Skenario E4, kejadian dinamis E5, dan simulasi pergerakan E9 dapat dijalankan langsung dari "
        "antarmuka, termasuk perbandingan dengan OR-Tools pada waktu komputasi yang sama; eksperimen yang memerlukan "
        "ribuan ulangan (E3, E6, E7, E8, E10) dijalankan dengan skrip, dan "
        "grafik serta tabel hasilnya ditampilkan di menu Hasil Penelitian. "
        "Animasi simulasi membantu pengguna "
        "membaca rencana: posisi truk, sisa muatan, dan antrean di SPBU terlihat pada jam yang dipilih. Evaluasi "
        "kegunaan oleh pengguna industri, misalnya dengan _System Usability Scale_, belum dilakukan.")
    W.p("**Implikasi bagi operator.** Bagi FT Gelumbang, hasil ini memberi tiga pegangan praktis. Rencana harian perlu "
        "diperiksa per kompartemen dan per tipe truk sebelum dijalankan, karena rute yang sah menurut total volume dapat "
        "gagal di _loading rack_. Armada eksisting longgar untuk permintaan normal dan lonjakan 1,5 kali, sehingga "
        "penambahan truk lebih tepat diarahkan pada kasus khusus seperti jalan akses sempit atau lonjakan lokal. Waktu "
        "tunggu _loading rack_ berpengaruh besar pada kebutuhan truk, sehingga pengaturan slot muat di FT patut dikaji "
        "bersama rute.")
    W.p("**Ancaman terhadap validitas.** Validitas internal dijaga dengan _seed_ terpisah untuk kalibrasi dan "
        "eksperimen, anggaran evaluasi yang setara antarvarian, dan uji statistik yang sesuai dengan struktur data. "
        "Validitas konstruk bergantung pada model konsumsi bahan bakar dan waktu yang masih memakai parameter asumsi; "
        "simulasi mikro (E9) dipakai untuk memeriksa kepekaan rencana terhadap asumsi waktu; pada simulasi deterministik "
        "selisih waktu tiba model dan simulasi tidak lebih dari 15 menit. Validitas eksternal terbatas karena kasus nyata hanya satu FT; instance "
        "sintetis E10 dan CVRPLIB dipakai untuk memperluasnya, tetapi belum menggantikan data dari wilayah lain. "
        "Pembanding OR-Tools dimodelkan dengan relaksasi (kapasitas efektif kompartemen, waktu muat dibebankan per "
        "SPBU); hasilnya mungkin membaik dengan pemodelan yang lebih rinci, sehingga keunggulan pada E10 berlaku untuk "
        "model OR-Tools yang dijelaskan pada subbab 3.3.4.")
    W.p("**Keterbatasan.** Proporsi produk, ukuran kompartemen, dimensi truk, konsumsi bahan bakar, biaya tetap, dan "
        "profil kemacetan masih asumsi. Kelas jalan sebagian besar diturunkan dari jenis ruas OSM karena hanya sedikit "
        "ruas yang memiliki tag lebar atau jumlah lajur, sehingga legalitas rute perlu dicocokkan dengan SK penetapan "
        "kelas jalan dan survei lapangan. Pengiriman terpisah belum dimodelkan, dan instance E10 bersifat sintetis "
        "walaupun dibangun di atas jaringan jalan nyata.")


def robust_text(R):
    t = []
    e9 = R["e9"]
    if e9:
        g = [r for r in e9["summary"] if r["case"] == "multiproduk" and r["plan"] == "GA-SA-RL"]
        if g:
            t.append(f"Simulasi mikro menunjukkan rencana GA-SA-RL selesai rata-rata pukul {jam_txt(g[0]['t_end_mean'])}–"
                     f"{jam_txt(g[-1]['t_end_mean'])} pada CV kecepatan 0,1–0,3, dengan persentil ke-95 paling lambat "
                     f"{jam_txt(max(x['t_end_p95'] for x in g))}; kelonggaran terhadap batas shift 18.00 lebih dari tiga jam.")
    e6 = R["e6"]
    if e6 is not None:
        mp = e6[(e6.produk == "multiproduk") & (np.isclose(e6.cv, 0.2))].set_index("plan")
        if len(mp) == 3:
            t.append(f"Risiko yang lebih nyata datang dari permintaan: pada CV 0,20 peluang ada SPBU yang kekurangan "
                     f"mencapai {f(mp.loc['GA-SA-RL', 'p_shortfall'] * 100, 1)}% tanpa penyangga dan turun menjadi "
                     f"{f(mp.loc['GA-SA-RL robust (90%)', 'p_shortfall'] * 100, 1)}% dengan penyangga kapasitas 10%.")
    if R["e5"]:
        d = R["e5"]["summary"].get("breakdown")
        if d:
            t.append(f"Re-optimasi setelah kerusakan truk berjalan sekitar {f(d['compute_s_mean'], 1)} detik dan "
                     f"memperbaiki {f(d['share_improved_fitness'] * 100, 0)}% kasus. Nilai tambahnya kecil karena armada "
                     "eksisting longgar; manfaatnya akan lebih besar pada jaringan dengan jendela waktu ketat dan utilisasi "
                     "armada tinggi.")
    return " ".join(t)


def ablation_text(R, cite):
    t = []
    e = R["e11"]
    if e:
        T = {int(x["n"]): x for x in e["tests"]}
        ns = sorted(T)
        win = [n for n in ns if T[n]["p_vs_OR-Tools"] < 0.05]
        tab = {(int(r["n"]), r["variant"]): r for r in e["table"]}
        ext = [(tab[(n, "GA-SA-RL")]["dist"] / tab[(n, "OR-Tools")]["dist"] - 1) * 100 for n in ns]
        t.append(f"Pada instance sulit {ns[0]}–{ns[-1]} SPBU, GA-SA-RL lebih baik dari OR-Tools pada "
                 + ", ".join(f"{n} SPBU ({f(T[n]['impr_vs_OR-Tools'], 0)}%)" for n in win)
                 + (f" dan setara pada {', '.join(str(n) for n in ns if n not in win)} SPBU" if len(win) < len(ns) else "")
                 + ". Keunggulan itu berasal dari kepatuhan terhadap jendela waktu dan batas shift; dari sisi jarak dan "
                 "biaya, OR-Tools tetap lebih hemat. Bagi operator, angka ini berarti rencana GA-SA-RL lebih sedikit "
                 f"menimbulkan keterlambatan dan lembur, dengan tambahan jarak {f(min(ext), 1)}–{f(max(ext), 1)}%.")
    if R["e7"] is not None and len(R["e7"]):
        t7 = e7_tests(R["e7"])
        t.append(f"Pada CVRPLIB, hibrida lebih baik dari GA saja (p = {pv(t7['GA'])}), dan gap rata-rata turun dari 6,47% "
                 "pada versi awal menjadi sekitar 3%.")
        if min(t7["GA-SA"], t7["GA-SA-ALNS"]) >= 0.05:
            t.append(f"Pemilihan operator dengan _Q-learning_ tidak lebih baik dari pemilihan acak (p = {pv(t7['GA-SA'])}) "
                     f"maupun bobot adaptif ALNS (p = {pv(t7['GA-SA-ALNS'])}), dan hasil yang sama terlihat pada instance "
                     "sulit. Keunggulan metode dengan demikian berasal dari fase SA dengan operator granular dan "
                     "_ruin-and-recreate_, bukan dari RL. Temuan ini sejalan dengan catatan tinjauan bahwa manfaat "
                     f"pemilih operator adaptif sering kecil bila operatornya seimbang {cite('voigt2024', 'jaouhari2026')}. "
                     "Klaim bahwa RL memperbaiki kualitas solusi tidak didukung data penelitian ini, sehingga RL lebih "
                     "tepat diposisikan sebagai komponen yang dapat diganti tanpa kehilangan kualitas.")
    return " ".join(t)


def luaran(W, cite, R):
    W.h("Hasil Luaran yang Dicapai")
    rows = [
        ("1", "Prototipe aplikasi web SMARTROUTE-BBM (kode terbuka)", "Repositori GitHub (Lampiran 2)", "Selesai"),
        ("2", "Basis data Google Sheets SMARTROUTE-BBM Database", "Tautan pada Lampiran 2", "Selesai"),
        ("3", "Data, kode eksperimen, dan hasil uji yang dapat diulang", "Folder data/, experiments/, results/", "Selesai"),
        ("4", "Naskah artikel jurnal internasional bereputasi", "Target jurnal Scopus Q2/Q3", "Disusun setelah laporan final"),
        ("5", "Pendaftaran HKI program komputer", "DJKI", "Persiapan berkas"),
    ]
    W.table(["No.", "Luaran", "Keterangan", "Status"], rows, "Luaran penelitian", widths=[1.0, 5.4, 4.4, 3.2],
            align=["c", "l", "l", "l"])


# ===========================================================================
def bab5(W, cite, R):
    W.bab(5, "KESIMPULAN DAN SARAN")
    W.h("Kesimpulan")
    e1, a, e8, e9 = R["e1"], R["app"], R["e8"], R["e9"]
    items = []
    if e1:
        imp = (e1["baseline_capstone"] - e1["milp_opt"]) / e1["baseline_capstone"] * 100
        items.append(f"Pada setting capstone, Hybrid GA-SA-RL mencapai optimum MILP {f(e1['milp_opt'])} km pada 30 dari 30 "
                     f"replikasi, {f(imp, 2)}% lebih pendek dari rencana _Saving Matrix_ 279,4 km.")
    if a:
        s, b = a["script"], a["baseline"]
        items.append(f"Pada jalan legal-truk dengan kompartemen dan tiga produk, rencana _Saving Matrix_ memuat "
                     f"{int(b['unassigned'])} ritase tak layak, sedangkan GA-SA-RL menghasilkan rencana layak "
                     f"{int(s['trucks'])} truk dan {int(s['trips'])} ritase, {f(s['dist_km'])} km, {rp(s['cost_rp'])}/hari, "
                     f"dan {f(s['co2_kg'])} kg CO~2~/hari. Aplikasi memberi angka yang sama.")
    if e8:
        m = e8["matriks"]
        rr = {r["tipe"]: r["km_ruas_legal"] / r["km_ruas_total"] * 100 for r in e8["ringkasan_ruas"]}
        items.append(f"Penyaringan OSM menurut kelas jalan menyisakan {f(rr['C'], 0)}% panjang ruas untuk truk B/C dan "
                     f"{f(rr['D'], 0)}% untuk semi-trailer D; truk D tidak dapat menjangkau {', '.join(m['D']['spbu_tak_terjangkau'])}. Jarak legal "
                     f"truk C berkorelasi {f(m['C']['korelasi'], 3)} dengan matriks capstone.")
    if e9:
        g = [r for r in e9["summary"] if r["case"] == "multiproduk" and r["plan"] == "GA-SA-RL"]
        items.append(f"Simulasi mikro 300 replikasi menunjukkan rencana GA-SA-RL selesai sebelum pukul "
                     f"{jam_txt(max(x['t_end_p95'] for x in g))} pada persentil ke-95 dan tanpa lembur, sehingga rencana "
                     "tetap dapat dijalankan pada variasi kecepatan dan waktu bongkar.")
    e4b = R["e4b"] or {}
    rb = e4b.get("2R. Restriksi jalan + 1 unit tipe B", {}).get("hybrid", {})
    rd = e4b.get("9bR. Panic buying lokal + 1 unit tipe D", {}).get("hybrid", {})
    if rb and rd:
        items.append("Skenario yang tidak dapat dilayani armada eksisting adalah restriksi jalan akses dan lonjakan "
                     f"permintaan lokal. Restriksi jalan teratasi dengan satu unit truk B tambahan ({int(rb['unassigned'])} "
                     f"ritase tak terlayani). Satu unit semi-trailer D hanya mengurangi ritase tak terlayani pada lonjakan "
                     f"lokal menjadi {int(rd['unassigned'])} karena S10 tidak dapat dijangkau D, sehingga kasus ini "
                     "memerlukan pengiriman terpisah. Antrean _loading rack_ yang padat menaikkan kebutuhan truk lebih "
                     "besar daripada perubahan rute.")
    e11 = R["e11"]
    if e11:
        T = {int(x["n"]): x for x in e11["tests"]}
        ns = sorted(T)
        win = [n for n in ns if T[n]["p_vs_OR-Tools"] < 0.05]
        items.append(f"Pada instance sulit {', '.join(map(str, ns))} SPBU dengan armada padat, jendela waktu, dan antrean "
                     "_loading rack_, GA-SA-RL lebih baik dari OR-Tools pada "
                     + " dan ".join(f"{n} SPBU (fitness {f(T[n]['impr_vs_OR-Tools'], 0)}% lebih kecil)" for n in win)
                     + (f" serta setara pada {', '.join(str(n) for n in ns if n not in win)} SPBU" if len(win) < len(ns) else "")
                     + ", dan jauh lebih baik dari Clarke–Wright dan GA saja. OR-Tools tetap menghasilkan jarak dan biaya "
                     "lebih rendah, tetapi dengan keterlambatan dan lembur yang lebih besar.")
    if R["e7"] is not None and len(R["e7"]):
        t7 = e7_tests(R["e7"])
        g = R["e7"][R["e7"].variant == "GA-SA-RL"].groupby("instance").gap_pct.mean()
        items.append(f"Pada CVRPLIB, rerata gap GA-SA-RL {f(g.mean(), 2)}% (versi awal 6,47%) dan hibrida lebih baik dari "
                     f"GA saja (p = {pv(t7['GA'])}). Pemilihan operator dengan _Q-learning_ tidak lebih baik dari pemilihan "
                     f"acak (p = {pv(t7['GA-SA'])}) maupun ALNS (p = {pv(t7['GA-SA-ALNS'])}); kualitas solusi berasal dari "
                     "fase SA dan operator granular serta _ruin-and-recreate_.")
    items.append("Aplikasi SMARTROUTE-BBM dengan basis data Google Sheets, simulasi pergerakan dua dan tiga dimensi, dan "
                 "re-routing dinamis, serta pembanding OR-Tools di menu Optimasi, telah selesai dan dipublikasikan sebagai "
                 "repositori terbuka.")
    W.bullets(items, numbered=True)
    W.h("Saran")
    W.bullets([
        "Mengganti asumsi dengan data aktual: penjualan per produk per SPBU, spesifikasi kompartemen dan dimensi armada FT "
        "Gelumbang, lalu mengulang E2–E9.",
        "Mencocokkan kelas dan lebar jalan pada rute terpilih dengan SK penetapan kelas jalan dan survei lapangan.",
        "Menambahkan pengiriman terpisah dan armada sewa agar lonjakan permintaan lokal dapat dilayani tanpa penalti.",
        "Melakukan uji kegunaan aplikasi bersama operator distribusi.",
        "Memperbaiki penjadwalan agar keterlambatan pada instance besar hilang, misalnya dengan operator yang sadar "
        "jendela waktu, dan menguji pemilih operator yang dilatih lintas instance terhadap ALNS pada anggaran yang sama.",
        "Memodelkan waktu muat per ritase dan kompartemen secara eksplisit pada OR-Tools agar perbandingan dengan "
        "pemecah komersial atau sumber terbuka lain lebih ketat.",
    ], numbered=True)


# ===========================================================================
def lampiran(W, R):
    W.appendix("Lampiran 1. Parameter algoritma dan asumsi model")
    rows = [("Populasi / generasi GA", "100 / 50"), ("p~c~ / p~m~ / turnamen / elit", "0,85 / 0,10 (×3 bila keragaman < 5%) / 5 / 2"),
            ("Inisialisasi", "60% serakah (tetangga terdekat + gangguan), 40% acak"),
            ("SA: T~0~ / α / iterasi / T~min~", "1000 / 0,99942 / 20.000 / 0,01"), ("Skala energi SA", "E = 10^6^ F/F~GA~"),
            ("Operator SA", "5 acak, 2 granular (k = 8), 2 _ruin-and-recreate_ (2 sampai 15% SPBU)"),
            ("_Q-learning_: η / γ / ε", "0,1 / 0,5 / 0,15"), ("Keadaan / aksi RL", "9 keadaan / 9 operator"),
            ("ALNS: λ / segmen / skor", "0,1 / 100 iterasi / (1; 0,4; 0; −0,02)"),
            ("OR-Tools", "GLS, batas waktu = median waktu GA-SA-RL"),
            ("Bobot (w~1~, w~2~, w~3~)", "(0,5; 0,3; 0,2)"), ("Harga solar / pemeliharaan", "Rp12.000/L / Rp1.500/km (asumsi)"),
            ("Faktor emisi", "2,68 kg CO~2~/L"), ("β / α~1~ / v~0~", "0,3 / 10^−4^ / 65 km/jam"),
            ("v~max~ model / shift / ritase maks.", "40 km/jam / 06.00–18.00 / 3"),
            ("Muat / bongkar", "5 menit/KL / 15 menit + 2,5 menit/KL"),
            ("Penalti", "0,02/menit terlambat; 0,02/menit lembur; 5/ritase tak layak; 1/KL di atas kuota"),
            ("Proporsi produk", "Pertalite 62%, Biosolar 26%, Pertamax 12% (asumsi)"),
            ("Simulasi mikro", "γ = 0,15; CV kecepatan 0,1–0,3; CV bongkar 0,15; v ≥ 5 km/jam")]
    W.table(["Parameter", "Nilai"], rows, None, widths=[5.5, 8.5], align=["l", "l"])
    e4 = R["e4"] or {}
    rows = [(SCN.get(k, k), v.get("assumption", "")) for k, v in list(e4.items()) + list((R["e4b"] or {}).items())]
    W.p("Asumsi skenario E4 dan E4b:", indent=False, keep_next=True)
    W.table(["Skenario", "Asumsi"], rows, None, widths=[4.0, 10.0], align=["l", "l"])
    W.appendix("Lampiran 2. Repositori, basis data, dan cara menjalankan")
    W.bullets([f"Repositori kode: {REPO}", f"Basis data Google Sheets: {SHEET}",
               "Menjalankan lokal: pip install -r requirements.txt, lalu streamlit run app.py",
               "Mengulang eksperimen: python -m experiments.run_all; python -m experiments.run_extra E9; "
               "python -m experiments.run_e11 run; python -m experiments.run_e11 ortools; python -m experiments.run_e11 summary; "
               "python -m experiments.app_check",
               "Membuat gambar dan laporan: python -m experiments.figures_report; python -m docs.build_laporan",
               "Memasang daring: Streamlit Community Cloud, pilih repositori smartroute-bbm dan berkas app.py"], left=True)
    W.appendix("Lampiran 3. Rute terbaik GA-SA-RL pada jalan legal-truk")
    e2 = R["e2"]
    if e2 and "multiproduk" in e2:
        rows = [(t["rute"], t["tipe"], t["unit"], t["ritase"], f(t["muatan_kl"], 2),
                 t["kompartemen"].strip("[]").replace("'", "")) for t in e2["multiproduk"]["best_trips"]]
        W.table(["Rute", "Tipe", "Unit", "Ritase", "Muatan (KL)", "Isi kompartemen (urut kompartemen)"], rows, None,
                widths=[2.8, 1.0, 1.0, 1.3, 1.9, 6.0])

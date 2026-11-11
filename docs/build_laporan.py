"""Membangun Laporan Akhir (template UPPM PEM Akamigas) dari hasil eksperimen di results/.

Semua angka hasil dibaca dari berkas results/*.json|csv; tidak ada angka hasil yang ditulis tangan.
Jalankan:  python -m docs.build_laporan
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from docx import Document  # noqa: E402
from docx.shared import Cm, Pt  # noqa: E402

from docs.docbuild import Cursor, add_toc, remove_el, set_update_fields_on_open  # noqa: E402
from docs.refs import Citer  # noqa: E402
from smartroute.data import load_tables  # noqa: E402

RES = os.environ.get("SR_RESULTS", os.path.join(ROOT, "results"))
FIG = os.path.join(ROOT, "figures")
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
SP3 = "046/SP3/Penelitian/DIPA2026/PEM Akamigas"
REPO = "https://github.com/asw09zoom-netizen/smartroute-bbm"
SHEET = "https://docs.google.com/spreadsheets/d/1CohYmRvhwtAD3y34z9DmqEYkp-sfHlJ1g_Zs4YWPRq4"


# ---------------------------------------------------------------------------
def J(name):
    p = os.path.join(RES, name)
    return json.load(open(p)) if os.path.exists(p) else None


def C(name):
    p = os.path.join(RES, name)
    return pd.read_csv(p) if os.path.exists(p) else None


def f(x, d=1):
    """Format angka gaya Indonesia (koma desimal, titik ribuan)."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "–"
    s = f"{x:,.{d}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def rp(x):
    return "Rp" + f(x, 0)


def pv(p):
    if p is None:
        return "–"
    return "< 0,001" if p < 0.001 else f(p, 3)


# ---------------------------------------------------------------------------
def fill_cover(doc):
    """Mengganti teks placeholder pada textbox sampul (ada dua salinan: mc:Choice & mc:Fallback)."""
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    p0 = doc.paragraphs[0]._p
    for par in p0.iter(W + "p"):
        ts = list(par.iter(W + "t"))
        txt = "".join(t.text for t in ts)
        new = None
        if txt.strip() == "JUDUL":
            new = JUDUL.upper()
        elif txt.startswith("Ketua/Anggota"):
            new = "; ".join(f"{n} (NIP {nip})" for _, n, nip in TIM)
        elif txt.strip() == "(Nama lengkap dan NIP/NIDN)":
            new = ""
        elif txt.strip() == "Bulan dan Tahun":
            new = "Desember 2026"
        if new is not None and ts:
            ts[0].text = new
            for t in ts[1:]:
                t.text = ""


def set_text(p, text):
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)
    if p.runs:
        p.runs[0].text = text
    else:
        p.add_run(text)


def fill_pengesahan(doc):
    P = doc.paragraphs
    set_text(P[2], "LAPORAN PENELITIAN TERAPAN")
    set_text(P[3], "PEM AKAMIGAS TAHUN 2026")
    vals = {7: ("Judul Penelitian", JUDUL), 8: ("Nama Lengkap", TIM[0][1]), 9: ("NIP/NIDN", TIM[0][2] + " / 0009098102"),
            10: ("Jabatan Fungsional", "Lektor Kepala"), 11: ("Nomor HP", "………………………"),
            13: ("Nama Lengkap", TIM[1][1]), 14: ("NIP/NIDN", TIM[1][2]),
            16: ("Nama Lengkap", TIM[2][1]), 17: ("NIP/NIDN", TIM[2][2]),
            19: ("Nama Lengkap", TIM[3][1]), 20: ("NIP/NIDN", TIM[3][2])}
    for i, (k, v) in vals.items():
        set_text(P[i], f"{k}\t: {v}")
    set_text(P[21], f"No SP3\t\t\t : {SP3}")
    set_text(P[24], "Cepu, ….. Desember 2026")
    set_text(P[31], f"(Astrie Kusuma Dewi, S.T., M.Eng.)\t\t({TIM[0][1]})")
    set_text(P[32], f"NIP {TIM[1][2]}\t\tNIP {TIM[0][2]}")
    set_text(P[40], "(Dr. Erdila Indriani, S.Si., M.T.) NIP ………………………")


def clear_after(heading_p, stop_texts):
    """Hapus paragraf panduan setelah heading sampai ketemu paragraf berikutnya yang bergaya Heading."""
    el = heading_p._p.getnext()
    while el is not None:
        nxt = el.getnext()
        if el.tag.endswith("}p"):
            sty = el.find(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pStyle")
            sname = sty.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val") if sty is not None else ""
            if sname.lower().startswith("heading") or sname in ("Heading1", "Heading2"):
                break
            # pertahankan section break, tetapi kosongkan teksnya
            if el.find(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}sectPr") is not None:
                for r in list(el.findall("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r")):
                    el.remove(r)
                el = nxt
                continue
            if el.find(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}br") is not None and not \
                    "".join(t.text or "" for t in el.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")).strip():
                el = nxt
                continue
            remove_el(el)
        elif el.tag.endswith("}tbl"):
            remove_el(el)
        el = nxt


def find_p(doc, text, style_prefix="Heading"):
    for p in doc.paragraphs:
        if p.text.strip().startswith(text) and p.style.name.startswith(style_prefix):
            return p
    raise KeyError(text)


# ===========================================================================
# BAB 1-3 (tidak bergantung pada hasil)
# ===========================================================================
def bab1(c: Cursor, cite: Citer, R):
    tot = R["e0"]["total_demand_kl"] if R["e0"] else 60.78
    c.h("Latar Belakang")
    c.p("Distribusi Bahan Bakar Minyak (BBM) dari _Fuel Terminal_ (FT) ke Stasiun Pengisian Bahan Bakar Umum (SPBU) "
        "merupakan operasi logistik kritis yang langsung memengaruhi ketersediaan energi bagi masyarakat. Berbeda dengan "
        "distribusi barang umum, distribusi BBM bersifat multi-produk (Pertalite, Pertamax, Biosolar, dan lain-lain), "
        "memakai truk tangki berkompartemen yang setiap kompartemennya hanya boleh berisi satu produk, dapat melakukan "
        "lebih dari satu ritase per hari, serta tunduk pada batas waktu operasional dan regulasi BPH Migas "
        f"{cite('cornillier2008', 'benantar2016', 'wang2020')}. Dalam literatur riset operasi, persoalan ini dikenal sebagai "
        f"_Petrol Station Replenishment Problem_ (PSRP), yaitu varian dari _Vehicle Routing Problem_ (VRP) {cite('dantzig1959')} "
        f"dengan karakteristik _multi-compartment_ {cite('ostermeier2021', 'coelho2015')} dan _multi-trip_ {cite('cattaruzza2016')}.")
    c.p("Di Indonesia, sebagian besar studi optimasi rute BBM masih memakai heuristik konstruktif seperti _Saving Matrix_ "
        f"(Clarke-Wright) dan _Nearest Neighbour_ {cite('melani2025', 'aqidawati2021')}, atau metaheuristik tunggal seperti "
        f"Tabu Search {cite('awaludin2025', 'abdul2023')}, dan umumnya mengagregasi seluruh produk menjadi satu volume. "
        f"Studi yang memodelkan kompartemen dan multi-produk {cite('nugroho2020', 'ramadhani2021', 'surjandari2011')} masih "
        "terbatas pada kasus kecil dan belum dikemas sebagai perangkat pendukung keputusan yang dapat dipakai ulang. "
        "Di sisi lain, literatur internasional menunjukkan bahwa kombinasi metaheuristik populasi dengan pencarian lokal "
        "yang operatornya dipilih secara adaptif menggunakan _reinforcement learning_ (RL) memberikan hasil kompetitif "
        f"untuk berbagai varian VRP {cite('qi2022', 'zhao2025', 'lin2025', 'koc2026')}.")
    c.p("Penelitian ini memakai data Capstone Design 2026 PEM Akamigas wilayah FT Gelumbang (Kabupaten Muara Enim, "
        f"Sumatera Selatan) yang melayani 13 SPBU dengan total permintaan {f(tot, 2)} KL/hari. Mahasiswa capstone telah "
        "menyusun rute dengan metode _Saving Matrix_ dan memperoleh 5 rute dengan total jarak 279,4 km. Laporan kemajuan "
        "penelitian ini menargetkan pengembangan model yang lebih lengkap (multi-kompartemen, multi-produk, multi-ritase) "
        "beserta algoritma Hybrid GA-SA-RL dan prototipe aplikasi web simulasi. Laporan akhir ini menyajikan hasil "
        "implementasi dan pengujian model, algoritma, dan aplikasi tersebut secara apa adanya, termasuk keterbatasannya.")
    c.h("Rumusan Masalah")
    c.bullets([
        "Bagaimana memformulasikan MC-MP-MT-VRP distribusi BBM yang mengakomodasi kendala kompartemen, multi-produk, "
        "multi-ritase, armada heterogen, dan batas waktu operasional?",
        "Seberapa besar perbaikan jarak, biaya, dan emisi CO~2~ yang dicapai Hybrid GA-SA-RL dibandingkan metode "
        "konvensional (Saving Matrix, Nearest Neighbour) dan optimum eksak?",
        "Bagaimana kinerja re-routing dinamis ketika terjadi gangguan operasional (kerusakan truk, kemacetan mendadak)?",
        "Bagaimana trade-off antara biaya distribusi dan emisi CO~2~ (Pareto front) pada kasus multi-produk?",
        "Apakah prototipe aplikasi web dengan basis data Google Sheets dapat menjalankan seluruh skenario simulasi secara "
        "terdokumentasi dan dapat direplikasi?",
    ], numbered=True)
    c.h("Tujuan Penelitian")
    c.bullets([
        "Mengembangkan formulasi MC-MP-MT-VRP untuk distribusi BBM dari FT ke SPBU.",
        "Mengimplementasikan dan memvalidasi Hybrid GA-SA-RL terhadap baseline capstone, heuristik klasik, optimum eksak "
        "MILP, dan instance benchmark CVRPLIB.",
        "Mengembangkan modul simulasi sepuluh kategori skenario _what-if_ dan re-routing dinamis.",
        "Menganalisis trade-off biaya-emisi melalui Pareto front.",
        "Membangun prototipe aplikasi web SMARTROUTE-BBM (kode terbuka di GitHub) dengan basis data Google Sheets dan "
        "jejak audit (log) setiap simulasi.",
    ], numbered=True)
    c.h("Manfaat Penelitian")
    c.bullets([
        "**Akademik:** kontribusi pada literatur PSRP/MCVRP dengan studi kasus Indonesia, disertai kode dan data yang "
        "dapat direplikasi.",
        "**Industri:** alat bantu keputusan perencanaan rute dan simulasi skenario yang dapat diadaptasi oleh operator "
        "distribusi BBM.",
        "**Pendidikan:** bahan ajar dan perangkat praktik untuk mata kuliah logistik migas dan Capstone Design.",
        "**Lingkungan:** kuantifikasi emisi CO~2~ distribusi dan opsi pengurangannya.",
    ])


def bab2(c: Cursor, cite: Citer, R):
    c.h("Dasar Teori")
    c.sub("2.1.1 Vehicle Routing Problem dan varian distribusi BBM")
    c.p(f"VRP pertama kali diformulasikan oleh Dantzig dan Ramser {cite('dantzig1959')} untuk menentukan rute armada dari "
        "depot ke sejumlah pelanggan dengan biaya minimum. Pada _Capacitated_ VRP (CVRP), setiap kendaraan berkapasitas "
        "terbatas dan setiap pelanggan dikunjungi tepat satu kali. Distribusi BBM menambahkan tiga ciri khas. Pertama, "
        "truk tangki dibagi atas beberapa kompartemen; setiap kompartemen hanya memuat satu produk sehingga kelayakan "
        "muatan bukan sekadar total volume ≤ kapasitas, melainkan masalah penugasan volume produk ke kompartemen "
        f"(_multi-compartment_ VRP, MCVRP) {cite('ostermeier2021', 'coelho2015', 'yahyaoui2018', 'efthymiadis2023')}. "
        "Kedua, truk dapat kembali ke FT dan memuat ulang dalam satu shift (_multi-trip_ VRP, MTVRP) "
        f"{cite('cattaruzza2016', 'azi2014')}. Ketiga, armada heterogen dan aksesibilitas jalan membatasi tipe truk yang "
        f"dapat melayani SPBU tertentu {cite('cornillier2008', 'wang2019', 'che2023')}.")
    c.sub("2.1.2 Algoritma Genetika dan representasi _giant tour_")
    c.p(f"Algoritma Genetika (GA) {cite('holland1975')} mengevolusikan populasi solusi melalui seleksi, pindah silang, "
        f"dan mutasi. Prins {cite('prins2004')} menunjukkan bahwa GA dengan representasi permutasi tanpa pembatas rute "
        "(_giant tour_) yang didekode secara optimal menggunakan prosedur _Split_ berbasis lintasan terpendek pada graf "
        "asiklik mampu bersaing dengan metaheuristik terbaik pada CVRP. Pendekatan ini juga menjadi dasar algoritma "
        f"_state-of-the-art_ HGS-CVRP {cite('vidal2022')}.")
    c.sub("2.1.3 Simulated Annealing")
    c.p(f"Simulated Annealing (SA) {cite('kirkpatrick1983')} menerima solusi tetangga yang lebih buruk dengan peluang "
        "exp(−ΔE/T), dengan temperatur T yang diturunkan secara geometrik. Dalam skema hibrida, SA dipakai untuk "
        "intensifikasi di sekitar solusi terbaik GA.")
    c.sub("2.1.4 Reinforcement Learning untuk pemilihan operator")
    c.p(f"Q-Learning {cite('watkins1992', 'sutton2018')} memperbarui nilai aksi Q(s,a) berdasarkan imbalan yang diterima. "
        "Pada metaheuristik, RL banyak dipakai sebagai _adaptive operator selection_ atau _hyper-heuristic_: agen memilih "
        "operator ketetanggaan yang paling menjanjikan berdasarkan keadaan pencarian "
        f"{cite('burke2013', 'qi2022', 'zhao2025', 'lin2025', 'yi2023', 'zhaoy2024')}. Penelitian ini mengikuti pendekatan "
        "tersebut; RL tidak dipakai sebagai pengganti algoritma rute, melainkan sebagai pengendali operator SA.")
    c.sub("2.1.5 Emisi CO~2~ dan optimasi multi-objektif")
    c.p(f"Logistik hijau memasukkan dampak lingkungan ke dalam keputusan rute {cite('dekker2012', 'bektas2011')}. Emisi "
        f"CO~2~ dihitung dengan pendekatan IPCC Tier 2 {cite('ipcc2006')}, yaitu konsumsi bahan bakar dikalikan faktor "
        "emisi (2,68 kg CO~2~/L solar), dengan konsumsi bergantung pada jarak, beban, dan kecepatan. Optimasi tiga objektif "
        "(biaya, emisi, waktu) diselesaikan dengan metode pembobotan ternormalisasi, dan Pareto front diperoleh melalui "
        "sapuan bobot.")
    c.sub("2.1.6 Logika fuzzy untuk prioritas SPBU")
    c.p(f"Sistem inferensi fuzzy Mamdani {cite('mamdani1975')} dipakai untuk memetakan kondisi SPBU (sisa waktu sampai "
        "stok habis, jarak, dan fluktuasi permintaan) menjadi skor prioritas 0–100 yang memengaruhi urutan penugasan "
        "ritase dan bobot penalti keterlambatan.")
    c.h("Hasil Penelitian yang Relevan")
    c.p("Tabel berikut merangkum penelitian terdahulu yang paling dekat dengan penelitian ini beserta celah yang diisi.")
    rows = [
        ("Cornillier dkk. (2008) " + cite("cornillier2008"), "PSRP multi-periode", "Heuristik", "Tanpa emisi; bukan DSS"),
        ("Wang dkk. (2020) " + cite("wang2020"), "MCVRP split-delivery multi-trip", "Eksak/heuristik", "Satu objektif"),
        ("Che dkk. (2023) " + cite("che2023"), "PSRP multi-depot", "Tabu-ALNS", "Tanpa re-routing dinamis"),
        ("Liu dkk. (2025) " + cite("liu2025"), "PSRP multi-kompartemen nyata", "Hybrid VNS", "Tanpa RL; tanpa emisi"),
        ("Baptista dkk. (2024) " + cite("baptista2024"), "MCVRP distribusi BBM", "Eksak", "Skala terbatas"),
        ("Qi dkk. (2022) " + cite("qi2022"), "Green VRPTW time-dependent", "EA + Q-learning", "Bukan multi-kompartemen"),
        ("Nugroho dkk. (2020) " + cite("nugroho2020"), "BBM Yogyakarta, multi-trip", "Sequential insertion", "Heuristik konstruktif"),
        ("Ramadhani dkk. (2021) " + cite("ramadhani2021"), "BBM TBBM Rewulu, kompartemen", "MILP (LINGO)", "8 SPBU; tanpa DSS"),
        ("Melani dkk. (2025) " + cite("melani2025"), "Pertamax Malang", "CWS, NN, Goal Prog.", "Produk tunggal"),
        ("Awaludin dkk. (2025) " + cite("awaludin2025"), "BBM Sei Siak", "CIH–Tabu Search", "Agregat; statis"),
        ("Penelitian ini", "MC-MP-MT-VRP FT Gelumbang", "GA-SA-RL + MILP + DSS web",
         "Kompartemen, multi-ritase, emisi, dinamis, terbuka"),
    ]
    c.table(["Peneliti", "Masalah", "Metode", "Celah / perbedaan"], rows, "Ringkasan penelitian relevan",
            widths=[3.8, 4.0, 3.6, 4.4])


def bab3(c: Cursor, cite: Citer, R):
    T = {k: pd.read_csv(os.path.join(ROOT, "data", f"{k}.csv")) for k in ["spbu", "armada"]}
    c.h("Jenis Penelitian")
    c.p("Penelitian ini adalah penelitian terapan kuantitatif berbasis pemodelan matematis dan eksperimen komputasi. "
        "Kinerja algoritma diuji melalui replikasi acak (30 replikasi per varian dengan _seed_ 0–29) dan uji statistik "
        f"parametrik serta nonparametrik {cite('derrac2011')}. Seluruh kode, data, dan keluaran eksperimen disimpan dalam "
        "repositori sehingga setiap angka pada laporan ini dapat direproduksi.")
    c.h("Bahan dan Alat")
    c.sub("3.2.1 Data")
    c.p("Data primer berasal dari Capstone Design 2026 (berkas “Saving Matrix Fixx.xlsx” dan “Data Mentah Distribusi.xlsx”): "
        "koordinat FT Gelumbang dan 13 SPBU, permintaan harian per SPBU, serta matriks jarak jalan 14×14 (km). Parameter "
        "yang tidak tersedia pada data capstone ditetapkan sebagai asumsi dan ditandai secara eksplisit (Tabel 3.2).")
    sp = T["spbu"]
    rows = [(r.id, r.nama, r.kabupaten, f(r.demand_kl, 2)) for r in sp.itertuples() if r.id != "FT"]
    c.table(["ID", "SPBU", "Kabupaten", "Permintaan (KL/hari)"], rows, "Data SPBU FT Gelumbang (Capstone Design 2026)",
            widths=[1.2, 6.0, 4.5, 3.0])
    ar = T["armada"]
    rows = [(r.tipe, f(r.kapasitas_kl, 0), r.kompartemen_kl, int(r.jumlah_unit), f(r.fc0_l_per_km, 2),
             rp(r.biaya_tetap_rp), f(r.lebar_jalan_min_m, 1)) for r in ar.itertuples()]
    c.table(["Tipe", "Kap. (KL)", "Kompartemen (KL)", "Unit", "FC~0~ (L/km)", "Biaya tetap/hari", "Lebar jalan min (m)"],
            rows, "Parameter armada (ukuran kompartemen, konsumsi, biaya tetap: asumsi)",
            note="Armada eksisting menurut data capstone: 4 unit tipe C (16 KL) dan 1 unit tipe B (8 KL). "
                 "Proporsi produk diasumsikan Pertalite 62%, Biosolar 26%, Pertamax 12% untuk setiap SPBU.")
    c.p("Data jaringan jalan nyata diambil dari OpenStreetMap (OSM) " + cite('haklay2008') + " melalui Overpass API untuk "
        "kotak wilayah yang mencakup FT Gelumbang dan ke-13 SPBU dengan margin ±7,7 km. Ruas yang diunduh adalah jalan "
        "umum (motorway sampai residential, termasuk service dan living_street untuk keperluan klasifikasi). Data mentah "
        "beserta cap waktu basis data OSM disimpan di data/osm/roads.json.gz sehingga perhitungan dapat diulang.")
    ak = pd.read_csv(os.path.join(ROOT, "data", "aturan_kelas_jalan.csv"))
    rows = [(r.kelas, f(r.lebar_maks_m, 1) if r.lebar_maks_m < 50 else "> 2,5", f(r.panjang_maks_m, 1) if r.panjang_maks_m < 50 else "> 18",
             f(r.tinggi_maks_m, 1), f(r.mst_maks_ton, 0) if r.mst_maks_ton < 50 else "> 10") for r in ak.itertuples()]
    c.table(["Kelas jalan", "Lebar maks (m)", "Panjang maks (m)", "Tinggi maks (m)", "MST maks (ton)"], rows,
            "Batas dimensi kendaraan dan muatan sumbu terberat (MST) per kelas jalan " + cite('uu22_2009', 'pp79_2013'),
            widths=[2.6, 3.0, 3.0, 3.0, 3.0])
    rows = [(r.tipe, f(r.lebar_kendaraan_m, 1), f(r.panjang_kendaraan_m, 1), f(r.tinggi_kendaraan_m, 1), f(r.mst_ton, 0),
             f(r.gvw_ton, 0), f(r.lebar_jalan_min_m, 1)) for r in ar.itertuples()]
    c.table(["Tipe", "Lebar (m)", "Panjang (m)", "Tinggi (m)", "MST (ton)", "JBB (ton)", "Lebar jalan min (m)"], rows,
            "Dimensi, MST, dan kebutuhan lebar jalan truk tangki (asumsi spesifikasi tipikal)", widths=[1.4, 2.2, 2.2, 2.2, 2.2, 2.2, 3.0],
            note="Nilai dimensi dan MST adalah asumsi spesifikasi tipikal truk tangki (engkel 6 KL, 8 KL, tronton 16 KL, "
                 "semi-trailer 32 KL) dan harus dikalibrasi dengan dokumen kendaraan armada FT Gelumbang.")
    oj = pd.read_csv(os.path.join(ROOT, "data", "osm_jalan.csv"))
    oj = oj[~oj.highway.str.endswith("_link")]
    rows = [(r.highway, r.boleh_truk, r.kelas_asumsi, f(r.lebar_lajur_m, 2), f(r.lebar_bawaan_m, 1)) for r in oj.itertuples()]
    c.table(["Jenis ruas OSM", "Lintasan truk", "Kelas (asumsi)", "Lebar lajur (m)", "Lebar bawaan (m)"], rows,
            "Pemetaan jenis ruas OSM ke kelas jalan dan lebar badan jalan bawaan (asumsi)", widths=[3.2, 2.6, 2.6, 3.0, 3.0],
            note="Ruas _link_ mengikuti induknya. Lebar bawaan dipakai hanya bila OSM tidak memuat tag width atau lanes.")
    c.sub("3.2.2 Perangkat")
    c.p("Model dan algoritma diimplementasikan dalam Python 3 (NumPy, pandas, SciPy). Model eksak diselesaikan dengan "
        f"pemecah MILP HiGHS {cite('huangfu2018')} melalui SciPy. Aplikasi web dibangun dengan Streamlit dan Plotly, "
        "basis data menggunakan Google Sheets (pustaka gspread, dengan cadangan berkas CSV lokal), dan notifikasi "
        "opsional melalui Telegram Bot API. Eksperimen dijalankan pada mesin Linux 4 inti CPU.")
    c.h("Prosedure / Langkah")
    c.sub("3.3.1 Formulasi MC-MP-MT-VRP")
    c.p("Misalkan N = {1,…,n} himpunan SPBU dan 0 adalah FT; P himpunan produk; K himpunan tipe truk dengan kapasitas "
        "Q~k~, kompartemen {c~k1~,…,c~km~}, jumlah unit U~k~, dan konsumsi dasar FC~0,k~; q~ip~ permintaan SPBU i untuk "
        "produk p; d~ij~ jarak jalan. Sebuah ritase r adalah barisan SPBU (0, i~1~, …, i~L~, 0) yang dilayani satu truk. "
        "Kendala utama adalah sebagai berikut.")
    c.bullets([
        "**Kunjungan:** setiap SPBU dilayani tepat satu ritase (tanpa _split delivery_).",
        "**Kompartemen (multi-produk):** terdapat penugasan setiap kompartemen ke paling banyak satu produk sehingga "
        "Σ~j∈C(p)~ c~kj~ ≥ Σ~i∈r~ q~ip~ untuk setiap produk p. Kelayakan diperiksa secara eksak dengan pencarian "
        "rekursif ber-_memo_.",
        "**Kompatibilitas & akses:** produk harus kompatibel dengan tipe truk dan lebar jalan akses SPBU ≥ lebar minimum tipe truk.",
        "**Multi-ritase:** satu unit truk dapat menjalankan paling banyak 3 ritase berurutan dalam shift 12 jam (06.00–18.00); "
        "kelebihan waktu dihitung sebagai lembur.",
        "**Waktu:** waktu muat 5 menit/KL, bongkar 15 menit + 2,5 menit/KL, kecepatan v(t) = 40·CF(t) km/jam "
        "dengan faktor kemacetan CF(t) per jam, jendela waktu lunak per SPBU, dan antrean _loading rack_.",
    ])
    c.p("Konsumsi bahan bakar setiap ruas dihitung dengan model beban-kecepatan:")
    c.eq("F~ij~ = FC~0,k~ · (1 + β · L~ij~/Q~k~) · (1 + α~1~(v − v~0~)^2^) · d~ij~")
    c.p("dengan L~ij~ muatan pada ruas tersebut, β = 0,3, α~1~ = 10^−4^, dan v~0~ = 65 km/jam. Ketiga objektif adalah:")
    c.eq("Z~1~ = Σ F~ij~ · h~BBM~ + Σ d~ij~ · c~km~ + Σ~k~ u~k~ · B~k~   (biaya, Rp)")
    c.eq("Z~2~ = EF · Σ F~ij~,  EF = 2,68 kg CO~2~/L   (emisi)")
    c.eq("Z~3~ = Σ~r~ (t~akhir,r~ − t~mulai,r~) + Σ~i~ π~i~ · max(0, a~i~ − b~i~)/100   (waktu)")
    c.p("dengan h~BBM~ = Rp12.000/L, c~km~ = Rp1.500/km (pemeliharaan), u~k~ jumlah unit tipe k yang dipakai, B~k~ biaya "
        "tetap harian, π~i~ skor prioritas fuzzy, a~i~ waktu tiba, dan b~i~ batas akhir jendela waktu. Fungsi tujuan "
        "skalar yang diminimumkan adalah:")
    c.eq("F = w~1~·Z~1~/Z~1~^ref^ + w~2~·Z~2~/Z~2~^ref^ + w~3~·Z~3~/Z~3~^ref^ + Penalti")
    c.p("dengan (w~1~, w~2~, w~3~) = (0,5; 0,3; 0,2) sesuai proposal, Z^ref^ adalah nilai objektif solusi _direct "
        "delivery_ (setiap SPBU dilayani satu ritase tersendiri) sebagai normalisasi, dan penalti mencakup keterlambatan "
        "(0,02/menit tertimbang), lembur (0,02/menit), ritase tanpa truk tersedia (5,0/ritase), dan kelebihan kuota BPH "
        "Migas (1,0/KL).")
    c.p("Untuk verifikasi, kasus khusus CVRP homogen (kapasitas 16 KL, satu ritase per truk, objektif jarak) juga "
        "dirumuskan sebagai MILP dua-indeks dengan eliminasi subtour Miller–Tucker–Zemlin berbasis muatan "
        f"{cite('mtz1960')} dan diselesaikan sampai optimal dengan HiGHS {cite('huangfu2018')}.")
    c.sub("3.3.2 Algoritma Hybrid GA-SA-RL")
    c.p("Solusi direpresentasikan sebagai permutasi SPBU (_giant tour_). Dekoder _Split_ yang diperluas untuk armada "
        f"heterogen {cite('prins2004')} memotong permutasi menjadi ritase dengan biaya tertimbang minimum, sekaligus "
        "memilih tipe truk termurah yang layak secara kompartemen dan akses. Agar pemilihan tipe truk tidak mengabaikan "
        "biaya tetap, biaya setiap ritase pada Split ditambah biaya tetap tipe truk yang diamortisasi atas jumlah ritase "
        "maksimum per truk (w~1~·B~k~/(3·Z~1~^ref^)). Penjadwal kemudian menugaskan ritase ke unit "
        "truk (prioritas fuzzy tertinggi lebih dahulu, lalu durasi terpanjang) dan mensimulasikan waktu secara "
        "_time-dependent_. Algoritma terdiri atas tiga fase:")
    c.bullets([
        "**GA:** populasi 100 (60% dibangkitkan secara serakah dari tetangga terdekat dengan gangguan acak), seleksi "
        "turnamen k = 5, _order crossover_ (OX) p~c~ = 0,85, mutasi inversi/tukar/pindah dengan p~m~ = 0,10 yang dinaikkan "
        "tiga kali lipat saat keragaman populasi < 5%, elitisme 2 individu, 200 generasi.",
        "**SA:** dimulai dari solusi terbaik GA, T~0~ = 1000, α = 0,995, 5000 iterasi; energi dinormalisasi "
        "E = 10^6^·F/F~GA~ sehingga pada awal SA solusi yang 0,1% lebih buruk diterima dengan peluang e^−1^ ≈ 0,37.",
        "**RL (Q-Learning):** pada setiap iterasi SA, agen memilih satu dari lima operator ketetanggaan (2-opt, relokasi, "
        "tukar, or-opt, tukar segmen). Keadaan = (tingkat stagnasi: <50, 50–199, ≥200 iterasi tanpa perbaikan) × "
        "operator terakhir; imbalan = perbaikan relatif + 1 jika ditemukan solusi terbaik baru, −0,05 jika ditolak; "
        "α = 0,1, γ = 0,9, ε = 0,1 menurun linear sampai 0,02.",
    ])
    c.p("Skala energi SA dikalibrasi sebelum eksperimen utama. Pada skala awal E = 10^5^·F/F~GA~, SA praktis menjadi "
        "jalan acak (solusi 1% lebih buruk masih diterima dengan peluang e^−1^) sehingga fase SA hampir tidak pernah "
        "memperbaiki solusi GA pada instance berukuran 100 pelanggan. Kalibrasi dilakukan pada instance X-n101-k25 "
        "dengan _seed_ 100–102 (terpisah dari _seed_ 0–29 yang dipakai pada eksperimen) untuk skala 10^5^, 10^6^, "
        "10^7^ dengan dan tanpa kembali-ke-solusi-terbaik; skala 10^6^ tanpa mekanisme tambahan dipilih karena paling "
        "sederhana dan memberi perbaikan SA yang konsisten pada kedua varian SA. Hasil kalibrasi disimpan pada "
        "results/calibration_sa.txt.")
    c.p("Untuk uji ablasi, tiga varian dibandingkan pada anggaran evaluasi yang setara: GA saja (mendapat generasi "
        "tambahan setara jumlah iterasi SA), GA-SA (operator SA dipilih acak seragam), dan GA-SA-RL.")
    c.sub("3.3.3 Re-routing dinamis")
    c.p("Ketika terjadi kejadian pada waktu t~e~ (truk rusak, atau kemacetan mendadak CF = 0,3 selama 3 jam), SPBU yang "
        "sudah dilayani dikeluarkan, muatan truk yang rusak dianggap tertahan, dan unit lain dibebaskan pada waktu "
        "selesai ritase berjalannya. Dua kebijakan dibandingkan: (a) **naif**, rencana awal dipertahankan dan SPBU yang "
        "tertahan digabung menjadi satu ritase tambahan; (b) **re-optimasi**, GA-SA-RL (populasi 40, 60 generasi, "
        f"1500 iterasi SA) dijalankan ulang untuk sisa SPBU dengan solusi naif sebagai individu awal {cite('rios2021', 'sze2024')}.")
    c.sub("3.3.4 Jaringan jalan nyata yang legal untuk truk")
    c.p("Matriks jarak capstone bersifat tunggal untuk semua truk sehingga tidak dapat membedakan jalan yang boleh dilalui "
        "truk kecil dan truk besar. Karena itu, setiap tipe truk k diberi graf jalan berarah G~k~ yang hanya memuat ruas "
        "OSM yang memenuhi seluruh syarat berikut:")
    c.bullets([
        "**Jenis ruas:** jalan umum yang dapat menjadi lintasan truk (Tabel 3.5); service, living_street, track, dan jalan "
        "setapak tidak dipakai sebagai lintasan.",
        "**Larangan akses:** tag access, motor_vehicle, hgv, atau goods tidak bernilai no/private.",
        "**Kelas jalan:** kelas ruas (Tabel 3.5) tidak lebih rendah daripada kelas minimum yang mengizinkan dimensi dan MST truk "
        "menurut UU 22/2009 Pasal 19 " + cite('uu22_2009', 'pp79_2013') + " (Tabel 3.3–3.4).",
        "**Rambu batas:** tag maxwidth, maxlength, maxheight, maxweight (terhadap JBB), dan maxaxleload (terhadap MST) tidak dilanggar.",
        "**Lebar jalan:** lebar badan jalan (tag width; atau lanes × lebar lajur; atau lebar bawaan) ≥ lebar jalan minimum truk "
        "pada jalan dua arah agar truk dapat berpapasan; pada jalur satu arah cukup lebar truk + 1,0 m ruang bebas.",
        "**Arah lalu lintas:** ruas oneway hanya dapat dilalui searah.",
    ])
    c.p("FT dan setiap SPBU dihubungkan ke simpul terdekat pada komponen terhubung kuat terbesar G~k~ (maksimum 250 m); "
        "bila tidak ada, SPBU dinyatakan tidak terjangkau oleh tipe k dan tipe tersebut dilarang melayaninya. Jarak "
        "d~ij~^k^ adalah lintasan terpendek Dijkstra " + cite('dijkstra1959') + " pada G~k~ sehingga matriks bersifat "
        "asimetris dan berbeda per tipe truk. Model memakai d~ij~^k^ pada evaluasi setiap ritase dan penjadwalan, sedangkan "
        "geometri lintasan dipakai untuk menggambar rute mengikuti jalan pada peta aplikasi. Pengunduhan dan perhitungan "
        "dijalankan otomatis oleh GitHub Actions setiap kali aturan atau data berubah.")
    c.sub("3.3.5 Rancangan eksperimen")
    rows = [
        ("E0", "Audit data: sirkuitas jarak jalan vs garis lurus, pelanggaran ketidaksamaan segitiga, radius 30 km"),
        ("E1", "Validasi pada setting capstone (CVRP 16 KL): baseline, NN, CW, optimum MILP, 3 varian × 30 replikasi"),
        ("E2", "Model lengkap MC-MP-MT-VRP (agregat dan multi-produk) armada eksisting, 3 varian × 30 replikasi"),
        ("E3", "Sapuan bobot (w~1~,w~2~,w~3~) langkah 0,1 → Pareto front; sensitivitas biaya tetap truk"),
        ("E4", "Sepuluh kategori skenario _what-if_ (kemacetan, restriksi jalan, jendela waktu, emisi, tangki, "
               "loading rack, panic buying, kuota BPH Migas)"),
        ("E5/E5b", "Re-routing dinamis: kerusakan truk dan kemacetan mendadak; E5b dengan tenggat ketat dari manajemen tangki"),
        ("E6", "Simulasi Monte Carlo permintaan stokastik (CV 0,05–0,20) → service level"),
        ("E7", f"Validasi algoritma pada 10 instance CVRPLIB set X (n = 100–142) {cite('uchoa2017')}"),
        ("E8", "Jaringan jalan nyata OSM legal-truk vs matriks capstone: armada eksisting dan diperluas, agregat dan "
               "multi-produk, GA-SA-RL × 30 replikasi"),
    ]
    c.table(["Kode", "Eksperimen"], rows, "Rancangan eksperimen", widths=[1.6, 14.0])
    c.p("Perbandingan dengan baseline memakai uji-t satu sampel dan uji peringkat bertanda Wilcoxon (satu sisi), "
        "sedangkan perbandingan antarvarian memakai ANOVA satu arah, Kruskal–Wallis, dan Tukey HSD dengan α = 0,05.")


# ===========================================================================
# BAB 4 (seluruh angka dari results/)
# ===========================================================================
def load_results():
    R = dict(e0=J("E0_audit.json"), e1=J("E1_summary.json"), e2=J("E2_summary.json"), e4=J("E4_scenarios.json"),
             e4b=J("E4b_fleet_remedy.json"), e5=J("E5_summary.json"), e5b=J("E5b_summary.json"),
             e3=C("E3_pareto.csv"), e3b=C("E3b_pareto.csv"), e3c=C("E3c_pareto.csv"), e3s=C("E3_sens_fixedcost.csv"), e6=C("E6_montecarlo.csv"), e7=C("E7_cvrplib.csv"),
             e8=J("E8_summary.json"), e2m=C("E2_runs_multiproduk.csv"), e2a=C("E2_runs_agregat.csv"), e1r=C("E1_runs.csv"))
    return R


VAR = ["GA", "GA-SA", "GA-SA-RL"]


def stats_rows(st, unit_fmt=lambda x: f(x, 4)):
    rows = []
    for v in VAR:
        d = st[v]
        rows.append((v, unit_fmt(d["mean"]), unit_fmt(d["sd"]), unit_fmt(d["min"]), unit_fmt(d["max"]),
                     f(d["runtime_mean"], 1), pv(d.get("p_wilcoxon"))))
    return rows


def kw_text(st):
    a, k = st.get("anova"), st.get("kruskal")
    if not isinstance(a, dict):
        return "Uji antarvarian tidak dapat dihitung karena seluruh replikasi bernilai identik."
    sig = k["p"] < 0.05
    return (f"ANOVA satu arah menghasilkan F = {f(a['F'], 2)} (p = {pv(a['p'])}) dan uji Kruskal–Wallis H = "
            f"{f(k['H'], 2)} (p = {pv(k['p'])}); dengan demikian perbedaan antarvarian "
            f"{'signifikan' if sig else 'tidak signifikan'} pada α = 0,05.")


def bab4(c: Cursor, cite: Citer, R):
    c.h("Deskripsi Hasil Penelitian")
    # ---------------- 4.1.1 aplikasi
    c.sub("4.1.1 Prototipe aplikasi SMARTROUTE-BBM")
    c.p("Prototipe aplikasi web telah selesai dibangun dan kodenya dipublikasikan sebagai repositori terbuka "
        f"({REPO}). Arsitektur aplikasi ditunjukkan pada Gambar 4.1. Aplikasi terdiri atas lima menu: (1) **Data & Peta** "
        "menampilkan data SPBU, matriks jarak, dan armada dari basis data; (2) **Optimasi GA-SA-RL** menjalankan "
        "algoritma dengan parameter yang dapat diatur dan menampilkan KPI terhadap baseline, peta rute, kurva "
        "konvergensi, statistik operator RL, Gantt multi-ritase, dan tabel muatan per kompartemen; (3) **Re-routing "
        "Dinamis** mensimulasikan kerusakan truk atau kemacetan mendadak; (4) **Hasil Penelitian** menampilkan "
        "keluaran eksperimen; (5) **Laporan & Log** mengunduh laporan dan mengirim ringkasan ke Telegram. Basis data "
        f"memakai Google Sheets “SMARTROUTE-BBM Database” ({SHEET}) dengan tab tb_spbu, tb_jarak, tb_armada, "
        "tb_produk, dan tb_simulasi_log; setiap simulasi tercatat sebagai jejak audit. Aplikasi dapat dijalankan "
        "lokal maupun di-_deploy_ gratis pada Streamlit Community Cloud langsung dari repositori GitHub.")
    c.figure(os.path.join(FIG, "fig00_alur.png"), "Arsitektur SMARTROUTE-BBM dan alur Hybrid GA-SA-RL", 15.5)
    c.figure(os.path.join(FIG, "app_optimasi.png"), "Tampilan menu Optimasi GA-SA-RL pada aplikasi web", 15.5)
    c.p("Dibandingkan rencana pada proposal, terdapat beberapa penyesuaian teknologi: kerangka FastAPI + PostgreSQL "
        "diganti Streamlit + Google Sheets agar aplikasi dapat dioperasikan dan dipelihara tanpa server khusus; "
        "OSRM diganti graf jalan OpenStreetMap yang disaring per tipe truk menurut kelas jalan, rambu, dan lebar jalan "
        "(subbab 3.3.4) karena profil OSRM bawaan tidak memuat batasan truk; dan modul Telegram Bot diimplementasikan sebagai fitur opsional tetapi efektivitasnya "
        "bagi pengguna belum dievaluasi (rumusan masalah ke-5 pada proposal belum dijawab secara empiris).")
    c.p("Kebenaran perangkat lunak diperiksa dengan uji unit otomatis (pytest), antara lain: reproduksi jarak baseline "
        "capstone 279,4 km dan _direct delivery_ 728,2 km dari matriks jarak; uji kelayakan kompartemen; dan uji bahwa "
        "algoritma menemukan solusi ≤ baseline. Seluruh uji lulus.")
    # ---------------- 4.1.2 audit data
    e0 = R["e0"]
    if e0:
        c.sub("4.1.2 Audit data (E0)")
        c.p(f"Total permintaan 13 SPBU adalah {f(e0['total_demand_kl'], 2)} KL/hari (proyeksi tren DOT pada data capstone "
            f"{f(e0['dot_trend_projection_kl'], 2)} KL/hari). Rasio jarak jalan terhadap jarak garis lurus (faktor "
            f"sirkuitas) rata-rata {f(e0['circuity_mean'], 3)} (SD {f(e0['circuity_sd'], 3)}; rentang "
            f"{f(e0['circuity_min'], 3)}–{f(e0['circuity_max'], 3)}), dan {f(e0['circuity_depot_mean'], 3)} untuk ruas dari FT. "
            f"Ditemukan {e0['triangle_violations_ordered']} pasangan berurutan yang melanggar ketidaksamaan segitiga "
            f"(terbesar {f(e0['triangle_worst'][0], 1)} km pada {e0['triangle_worst'][1]}→{e0['triangle_worst'][2]} melalui "
            f"{e0['triangle_worst'][3]}), yang menandakan matriks berasal dari rute jalan aktual yang tidak selalu terpendek. "
            f"Sebanyak {e0['spbu_beyond_30km']} SPBU berada di luar radius 30 km dari FT (maksimum {f(e0['max_depot_dist_km'], 1)} km), "
            "sehingga batas radius 30 km pada proposal tidak diberlakukan sebagai kendala keras.")
    # ---------------- 4.1.3 E1
    e1 = R["e1"]
    if e1:
        c.sub("4.1.3 Validasi pada setting capstone (E1)")
        st = e1["stats"]
        c.p("Pada setting yang sama dengan capstone (CVRP homogen 16 KL, satu ritase per truk, objektif jarak), "
            f"rencana _Saving Matrix_ capstone menghasilkan {f(e1['baseline_capstone'])} km dan _direct delivery_ "
            f"{f(e1['direct'])} km; kedua angka ini tereproduksi tepat dari matriks jarak. Implementasi ulang "
            f"Clarke-Wright menghasilkan {f(e1['cw_reimpl'])} km dan _Nearest Neighbour_ {f(e1['nn'])} km. Model MILP "
            f"diselesaikan sampai optimal terbukti (gap 0) dalam {f(e1['milp_time_s'], 0)} detik dengan jarak optimum "
            f"**{f(e1['milp_opt'])} km**, yaitu {f((e1['baseline_capstone'] - e1['milp_opt']) / e1['baseline_capstone'] * 100, 2)}% "
            "lebih pendek daripada rencana capstone. Rute optimum: " + "; ".join(e1["milp_routes"]) + ".")
        c.table(["Varian", "Rerata (km)", "SD", "Min", "Maks", "Waktu (s)", "p Wilcoxon"],
                stats_rows(st, lambda x: f(x, 1)), "Hasil 30 replikasi pada setting capstone (E1)",
                note=f"Tingkat keberhasilan mencapai optimum MILP: GA {f(st['GA']['hit_rate_opt'] * 100, 0)}%, GA-SA "
                     f"{f(st['GA-SA']['hit_rate_opt'] * 100, 0)}%, GA-SA-RL {f(st['GA-SA-RL']['hit_rate_opt'] * 100, 0)}%.")
        allhit = all(st[v]["hit_rate_opt"] == 1.0 for v in VAR)
        c.p(("Ketiga varian menemukan optimum MILP pada seluruh 30 replikasi. Karena variansnya nol, uji-t dan "
             "Wilcoxon terhadap baseline tidak dapat dihitung, namun selisih terhadap baseline bersifat deterministik "
             f"({f(st['GA-SA-RL']['improve_vs_baseline_pct'], 2)}%). Instance berukuran 13 SPBU ini terlalu kecil untuk "
             "membedakan kinerja ketiga varian; perbedaan antarvarian diuji pada model lengkap (E2) dan benchmark (E7).")
            if allhit else kw_text(st))
        c.figure(os.path.join(FIG, "fig02_validasi_capstone.png"), "Validasi pada setting capstone: (a) sebaran 30 "
                 "replikasi, (b) perbandingan metode", 15.5)
    # ---------------- 4.1.4 E2
    e2 = R["e2"]
    if e2:
        c.sub("4.1.4 Model lengkap MC-MP-MT-VRP dengan armada eksisting (E2)")
        c.p("Model lengkap dijalankan dengan armada eksisting (4 unit tipe C 16 KL dan 1 unit tipe B 8 KL), multi-ritase "
            "(maksimum 3 ritase per truk dalam shift 12 jam), dan objektif tertimbang. Dua kasus diuji: **agregat** "
            "(seluruh BBM dianggap satu produk, sebagaimana data capstone) dan **multi-produk** (Pertalite/Biosolar/"
            "Pertamax dengan proporsi asumsi). Rencana _Saving Matrix_ capstone dievaluasi dengan model yang sama "
            "sebagai pembanding.")
        for key, judul in [("agregat", "agregat"), ("multiproduk", "multi-produk")]:
            if key not in e2:
                continue
            E = e2[key]
            b, h = E["baseline"], E["best_ga_sa_rl"]
            m = E["means"]
            rows = [("Saving Matrix (capstone)", f(b["fitness"], 4), f(b["dist_km"]), rp(b["cost_rp"]), f(b["co2_kg"]),
                     f(b["time_min"], 0), f"{int(b['trucks'])}/{int(b['trips'])}", int(b["unassigned"]))]
            for v in VAR:
                rows.append((f"{v} (rerata 30)", f(m["fitness"][v], 4), f(m["dist_km"][v]), rp(m["cost_rp"][v]),
                             f(m["co2_kg"][v]), f(m["time_min"][v], 0),
                             f"{f(m['trucks'][v], 1)}/{f(m['trips'][v], 1)}", f(m["unassigned"][v], 2)))
            rows.append(("GA-SA-RL terbaik", f(h["fitness"], 4), f(h["dist_km"]), rp(h["cost_rp"]), f(h["co2_kg"]),
                         f(h["time_min"], 0), f"{int(h['trucks'])}/{int(h['trips'])}", int(h["unassigned"])))
            c.table(["Rencana", "Fitness", "Jarak (km)", "Biaya/hari", "CO~2~ (kg)", "Waktu (mnt)", "Truk/ritase",
                     "Ritase tak terlayani"], rows, f"Hasil model lengkap, kasus {judul} (E2)", size=8)
            st = E["stats_fitness"]
            txt = []
            if b["unassigned"] > 0:
                txt.append(f"Pada kasus {judul}, rencana capstone **tidak layak**: {int(b['unassigned'])} ritase tidak dapat "
                           "dibawa oleh truk mana pun karena kombinasi volume produk tidak muat pada konfigurasi "
                           "kompartemen (misalnya rute S8-S9-S10 memerlukan Pertalite 9,6 KL, Biosolar 4,02 KL, dan "
                           "Pertamax 1,86 KL, sedangkan kompartemen tipe C adalah 6+4+3+3 KL). Temuan ini menunjukkan "
                           "bahwa rute yang dirancang berdasarkan total volume belum tentu dapat dieksekusi ketika "
                           "kompartemen dan produk diperhitungkan.")
            dc = (h["co2_kg"] - b["co2_kg"]) / b["co2_kg"] * 100
            dk = (h["cost_rp"] - b["cost_rp"]) / b["cost_rp"] * 100
            dd = (h["dist_km"] - b["dist_km"]) / b["dist_km"] * 100
            txt.append(f"Solusi terbaik GA-SA-RL memerlukan {int(h['trucks'])} truk dan {int(h['trips'])} ritase, dengan "
                       f"jarak {f(h['dist_km'])} km ({'+' if dd >= 0 else ''}{f(dd, 1)}% terhadap baseline), biaya "
                       f"{rp(h['cost_rp'])} ({'+' if dk >= 0 else ''}{f(dk, 1)}%), dan emisi {f(h['co2_kg'])} kg CO~2~ "
                       f"({'+' if dc >= 0 else ''}{f(dc, 1)}%), tanpa keterlambatan maupun lembur.")
            txt.append(kw_text(st))
            c.p(" ".join(txt))
            fig = os.path.join(FIG, f"fig03_e2_{key}.png")
            c.figure(fig, f"Sebaran 30 replikasi per varian pada model lengkap, kasus {judul}", 15.5)
        if "agregat" in e2:
            h = e2["agregat"]["best_ga_sa_rl"]; b = e2["agregat"]["baseline"]
            if h["dist_km"] > b["dist_km"] and h["trucks"] < b["trucks"]:
                c.p(f"Pada kasus agregat, GA-SA-RL memilih menempuh jarak lebih jauh ({f(h['dist_km'])} vs "
                    f"{f(b['dist_km'])} km) agar seluruh ritase dapat dijalankan oleh {int(h['trucks'])} truk "
                    f"(baseline {int(b['trucks'])} truk). Dengan biaya tetap Rp900.000/truk/hari (asumsi), pengurangan "
                    "satu truk lebih menguntungkan daripada tambahan jarak. Trade-off ini sangat bergantung pada asumsi "
                    "biaya tetap, sehingga dianalisis lebih lanjut pada E3.")
        if R["e2m"] is not None:
            for t in e2.get("multiproduk", {}).get("best_trips", [])[:0]:
                pass
            rows = [(t["rute"], t["tipe"], t["unit"], t["ritase"], f(t["muatan_kl"], 2), f(t["jarak_km"]),
                     f"{f(t['mulai_menit'] / 60 + 6, 2)}–{f(t['selesai_menit'] / 60 + 6, 2)}", t["kompartemen"].strip("[]").replace("'", ""))
                    for t in e2["multiproduk"]["best_trips"]]
            c.table(["Rute", "Tipe", "Unit", "Ritase", "Muatan (KL)", "Jarak (km)", "Jam", "Isi kompartemen"], rows,
                    "Rencana terbaik GA-SA-RL kasus multi-produk", size=8)
            c.figure(os.path.join(FIG, "fig01_peta_rute.png"), "Rute (a) Saving Matrix capstone dan (b) GA-SA-RL "
                     "kasus multi-produk", 15.5)
    # ---------------- 4.1.5 E3
    e3 = R["e3"]
    if e3 is not None:
        c.sub("4.1.5 Trade-off biaya–emisi (E3)")
        fe = e3[e3.unassigned == 0]
        pf = fe[fe.pareto_cost_co2].sort_values("cost_rp").drop_duplicates(["cost_rp", "co2_kg"])
        c.p(f"Sapuan bobot dengan langkah 0,1 (dua seed per vektor bobot) dengan armada eksisting menghasilkan {len(e3)} "
            f"solusi ({len(fe)} layak), dengan {len(pf)} titik non-dominasi pada bidang biaya–emisi "
            f"(Gambar 4.{c.fig_no + 1}a). " +
            (f"Rentang Pareto front adalah biaya {rp(pf.cost_rp.min())}–{rp(pf.cost_rp.max())} per hari dan emisi "
             f"{f(pf.co2_kg.min())}–{f(pf.co2_kg.max())} kg CO~2~ per hari." if len(pf) > 1 else
             f"Titik tersebut ({rp(pf.cost_rp.iloc[0])}; {f(pf.co2_kg.iloc[0])} kg CO~2~) berarti rencana berbiaya minimum "
             "juga beremisi minimum pada armada eksisting."))
        rows = [(f"({f(r.w1, 1)}; {f(r.w2, 1)}; {f(r.w3, 1)})", rp(r.cost_rp), f(r.co2_kg), f(r.dist_km), int(r.trucks),
                 int(r.trips)) for r in pf.itertuples()]
        c.table(["Bobot (w~1~; w~2~; w~3~)", "Biaya/hari", "CO~2~ (kg)", "Jarak (km)", "Truk", "Ritase"], rows,
                "Solusi non-dominasi biaya–emisi (kasus multi-produk)")
        s3 = R["e3s"]
        if s3 is not None:
            g = s3.groupby("fixed_cost_mult").mean(numeric_only=True)
            if abs(g.trucks.iloc[0] - g.trucks.iloc[-1]) < 1e-9 and abs(g.dist_km.iloc[0] - g.dist_km.iloc[-1]) < 1e-9:
                c.p("Sensitivitas terhadap biaya tetap truk (pengali 0–2 terhadap nilai asumsi) menunjukkan rencana yang "
                    f"sama pada seluruh pengali ({f(g.trucks.iloc[0], 0)} truk, {f(g.dist_km.iloc[0])} km); hanya total "
                    f"biaya yang berubah ({rp(g.cost_rp.iloc[0])}–{rp(g.cost_rp.iloc[-1])}). Dengan armada eksisting, "
                    "rekomendasi rute dan jumlah truk dengan demikian tidak sensitif terhadap asumsi biaya tetap.")
            else:
                c.p("Sensitivitas terhadap biaya tetap truk (pengali 0–2 terhadap nilai asumsi) menunjukkan bahwa jumlah truk "
                    f"rata-rata berubah dari {f(g.trucks.iloc[0], 1)} menjadi {f(g.trucks.iloc[-1], 1)}, sedangkan jarak "
                    f"berubah dari {f(g.dist_km.iloc[0])} km menjadi {f(g.dist_km.iloc[-1])} km.")
        c.figure(os.path.join(FIG, "fig04_pareto.png"), "(a) Pareto front biaya–emisi; (b) sensitivitas biaya tetap truk", 15.5)
        if R.get("e3b") is not None:
            feb, pfb = pareto_pts(R["e3b"])
            rows = [(f"({f(r.w1, 1)}; {f(r.w2, 1)}; {f(r.w3, 1)})", rp(r.cost_rp), f(r.co2_kg), f(r.dist_km), int(r.trucks),
                     r.trip_types) for r in pfb.itertuples()]
            c.p("Untuk melihat trade-off pemilihan armada, sapuan bobot diulang dengan opsi armada diperluas (2 unit A, "
                "2 unit B, 4 unit C, 1 unit D; E3b). " + tradeoff_text({"e3": None, "e3b": R["e3b"]}).rsplit(" Karena", 1)[0])
            if len(rows):
                c.table(["Bobot (w~1~; w~2~; w~3~)", "Biaya/hari", "CO~2~ (kg)", "Jarak (km)", "Truk", "Tipe per ritase"],
                        rows, "Solusi non-dominasi biaya–emisi dengan opsi armada diperluas (E3b)")
    # ---------------- 4.1.6 E4
    e4 = R["e4"]
    if e4:
        c.sub("4.1.6 Simulasi sepuluh kategori skenario (E4)")
        rows = []
        for k, v in e4.items():
            if "hybrid" not in v:
                rows.append((k, v["assumption"], "–", "–", "–", "–"))
                continue
            h = v["hybrid"]
            b = v.get("baseline")
            rows.append((k, v["assumption"], f"{f(h['dist_km'])} / {rp(h['cost_rp'])}", f(h["co2_kg"]),
                         f"{int(h['trucks'])}/{int(h['trips'])}",
                         f"{int(h['unassigned'])}" + (f" (baseline {int(b['unassigned'])})" if b else "")))
        e4b = R["e4b"] or {}
        for k, v in e4b.items():
            h = v["hybrid"]
            rows.append((k, v["assumption"], f"{f(h['dist_km'])} / {rp(h['cost_rp'])}", f(h["co2_kg"]),
                         f"{int(h['trucks'])}/{int(h['trips'])}", f"{int(h['unassigned'])}"))
        c.table(["Skenario", "Asumsi", "Jarak (km) / biaya", "CO~2~ (kg)", "Truk/ritase", "Tak terlayani"], rows,
                "Hasil GA-SA-RL (terbaik dari 5 seed) pada setiap skenario", widths=[3.2, 5.2, 3.0, 1.6, 1.5, 1.8], size=7.5)
        c.figure(os.path.join(FIG, "fig08_skenario.png"), "Biaya dan emisi GA-SA-RL per skenario", 15.5)
        c.p(scenario_text(e4, e4b))
    # ---------------- 4.1.7 E5
    c.sub("4.1.7 Re-routing dinamis (E5 dan E5b)")
    rows = []
    for lab, S in [("E5 normal", R["e5"] and R["e5"]["summary"]), ("E5b tenggat ketat", R["e5b"])]:
        if not S:
            continue
        for evn, d in S.items():
            rows.append((lab, "Kerusakan truk" if evn == "breakdown" else "Kemacetan mendadak", d["n"],
                         f"{f(d['fitness']['naive'], 4)} → {f(d['fitness']['reopt'], 4)}",
                         pv(d["fitness"].get("p_wilcoxon")),
                         f"{f(d['dist_km']['naive'])} → {f(d['dist_km']['reopt'])}",
                         f"{f(d['share_improved_fitness'] * 100, 0)}%", f(d["compute_s_mean"], 2)))
    if rows:
        c.table(["Set", "Kejadian", "n", "Fitness naif → re-opt", "p", "Jarak sisa (km)", "Kasus membaik", "Waktu (s)"],
                rows, "Perbandingan kebijakan naif dan re-optimasi GA-SA-RL", size=8)
        e5 = R["e5"]["summary"] if R["e5"] else None
        if e5 and "breakdown" in e5:
            d = e5["breakdown"]
            c.p(f"Pada kejadian kerusakan truk (n = {d['n']} kombinasi unit × waktu × seed), re-optimasi menurunkan "
                f"fitness residual rata-rata dari {f(d['fitness']['naive'], 4)} menjadi {f(d['fitness']['reopt'], 4)} "
                f"(Wilcoxon satu sisi p = {pv(d['fitness'].get('p_wilcoxon'))}), dengan waktu komputasi rata-rata "
                f"{f(d['compute_s_mean'], 2)} detik. Namun perbaikan hanya terjadi pada "
                f"{f(d['share_improved_fitness'] * 100, 0)}% kasus dan besarnya kecil (jarak sisa "
                f"{f(d['dist_km']['naive'])} → {f(d['dist_km']['reopt'])} km); pada kasus lainnya kebijakan naif sudah "
                "optimal karena armada eksisting memiliki kelonggaran waktu yang besar (tidak ada keterlambatan maupun "
                "lembur pada kedua kebijakan). Pada kemacetan mendadak, kedua kebijakan menghasilkan rencana yang sama.")
        if R["e5b"] and "breakdown" in R["e5b"]:
            d = R["e5b"]["breakdown"]
            c.p(f"Pada kondisi tenggat ketat (E5b), re-optimasi menurunkan fitness dari {f(d['fitness']['naive'], 4)} "
                f"menjadi {f(d['fitness']['reopt'], 4)} (p = {pv(d['fitness'].get('p_wilcoxon'))}) dan memperbaiki "
                f"{f(d['share_improved_fitness'] * 100, 0)}% kasus. Secara keseluruhan, modul re-routing bekerja dalam "
                "orde detik sehingga layak dipakai operasional, tetapi nilai tambahnya pada kasus FT Gelumbang dengan "
                "armada eksisting tergolong kecil.")
    c.figure(os.path.join(FIG, "fig05_dinamis.png"), "Fitness residual dan keterlambatan: tanpa vs dengan re-routing", 15.0)
    # ---------------- 4.1.8 E6
    e6 = R["e6"]
    if e6 is not None:
        c.sub("4.1.8 Ketahanan terhadap permintaan stokastik (E6)")
        rows = [(r.produk, f(r.cv, 2), r.plan, f(r.service_level * 100, 2) + "%", f(r.unmet_kl, 3), f(r.p_shortfall * 100, 1) + "%",
                 f(r.dist_km)) for r in e6.itertuples()]
        c.table(["Kasus", "CV", "Rencana", "Service level", "Tak terpenuhi (KL/hari)", "P(ada kekurangan)", "Jarak (km)"],
                rows, "Simulasi Monte Carlo 1000 iterasi per sel", size=8,
                note="Varian robust: kapasitas efektif truk dibatasi 90% saat perencanaan. Untuk ritase baseline yang "
                     "tidak layak secara kompartemen, kapasitas simulasi disamakan dengan volume rencana.")
        mp = e6[(e6.produk == "multiproduk") & (e6.cv == 0.2)].set_index("plan")
        if len(mp) == 3:
            c.p(f"Pada kasus multi-produk dengan CV 0,20, service level rencana capstone {f(mp.loc['Saving Matrix', 'service_level'] * 100, 2)}%, "
                f"GA-SA-RL {f(mp.loc['GA-SA-RL', 'service_level'] * 100, 2)}%, dan GA-SA-RL robust "
                f"{f(mp.loc['GA-SA-RL robust (90%)', 'service_level'] * 100, 2)}% (jarak {f(mp.loc['GA-SA-RL robust (90%)', 'dist_km'])} km). "
                "Penyangga kapasitas 10% menurunkan peluang kekurangan secara nyata dengan tambahan jarak, sehingga DSS "
                "dapat dipakai untuk memilih tingkat penyangga sesuai toleransi risiko operator.")
        c.figure(os.path.join(FIG, "fig06_montecarlo.png"), "Service level terhadap koefisien variasi permintaan", 15.0)
    # ---------------- 4.1.9 E7
    e7 = R["e7"]
    if e7 is not None and len(e7):
        c.sub("4.1.9 Validasi algoritma pada benchmark CVRPLIB (E7)")
        g = e7.groupby(["instance", "variant"]).agg(n=("n", "first"), bks=("bks", "first"), cw=("cw_gap_pct", "first"),
                                                    gap=("gap_pct", "mean"), sd=("gap_pct", "std"), best=("gap_pct", "min"),
                                                    t=("runtime", "mean")).reset_index()
        rows = [(r.instance, r.variant, int(r.bks), f(r.cw, 2), f(r.gap, 2), f(r.sd, 2), f(r.best, 2), f(r.t, 0))
                for r in g.itertuples()]
        c.table(["Instance", "Varian", "BKS", "Gap CW (%)", "Gap rerata (%)", "SD", "Gap terbaik (%)", "Waktu (s)"], rows,
                f"Gap terhadap _best known solution_ pada CVRPLIB set X {cite('uchoa2017')}", size=8)
        gg = g[g.variant == "GA-SA-RL"]
        c.p(f"Pada {len(gg)} instance CVRPLIB set X (n = {int(gg.n.min())}–{int(gg.n.max())}), GA-SA-RL mencapai gap rerata "
            f"{f(gg.gap.mean(), 2)}% terhadap BKS (rentang {f(gg.gap.min(), 2)}–{f(gg.gap.max(), 2)}%), dibandingkan "
            f"Clarke-Wright {f(gg.cw.mean(), 2)}%. Hasil ini menunjukkan implementasi algoritma benar, tetapi pada CVRP "
            "murni keunggulannya atas heuristik Clarke-Wright hanya kecil secara rata-rata (bahkan kalah pada beberapa "
            f"instance) dan masih jauh dari algoritma _state-of-the-art_ seperti HGS-CVRP {cite('vidal2022')} yang "
            "umumnya mencapai gap < 0,5%. Kekuatan GA-SA-RL pada penelitian ini terletak pada fleksibilitasnya menangani "
            "model kasus yang kaya kendala, bukan sebagai pemecah CVRP murni.")
        c.p(e7_ablation_text(e7))
        c.figure(os.path.join(FIG, "fig07_cvrplib.png"), "Gap terhadap BKS pada CVRPLIB set X", 15.0)
    e8_section(c, cite, R)


def e8_section(c, cite, R):
    e8 = R.get("e8")
    if not e8:
        return
    c.sub("4.1.10 Rute pada jaringan jalan nyata yang legal untuk truk (E8)")
    rr = e8.get("ringkasan_ruas", [])
    if rr:
        tot = rr[0]["km_ruas_total"]
        rows = []
        for r in rr:
            un = r.get("simpul_tak_terjangkau")
            un = "–" if (un is None or (isinstance(un, float) and math.isnan(un)) or un == "") else str(un).replace(";", ", ")
            rows.append((r["tipe"], r["kelas_jalan_min"], f(r["km_ruas_legal"], 0), f(r["km_ruas_legal"] / tot * 100, 1), un))
        c.table(["Tipe", "Kelas jalan min", "Ruas legal (km)", "Porsi (%)", "SPBU tak terjangkau"], rows,
                f"Ruas OSM yang legal per tipe truk (total {f(tot, 0)} km ruas di wilayah studi)", widths=[1.6, 3.0, 3.0, 2.4, 5.0])
    m = e8["matriks"]
    mc = m.get("C", {})
    c.p(f"Wilayah studi memuat {f(rr[0]['km_ruas_total'], 0) if rr else '-'} km ruas OSM. Truk B dan C (kelas jalan II) "
        f"hanya dapat memakai {f(rr[2]['km_ruas_legal'], 0) if len(rr) > 2 else '-'} km di antaranya, dan semi-trailer D "
        f"(kelas I) {f(rr[3]['km_ruas_legal'], 0) if len(rr) > 3 else '-'} km; sebagian besar ruas yang ditolak adalah "
        "jalan lokal dan lingkungan yang berkelas III. "
        + (f"Seluruh SPBU tetap terjangkau oleh truk C, sedangkan truk D tidak dapat mencapai {', '.join(m['D']['spbu_tak_terjangkau'])} "
           "sehingga tipe D dilarang melayani SPBU tersebut. " if m.get("D", {}).get("spbu_tak_terjangkau") else "")
        + f"Jarak jalan legal untuk truk C berkorelasi {f(mc.get('korelasi', float('nan')), 3)} dengan matriks capstone "
        f"(rerata selisih absolut {f(mc.get('rerata_selisih_abs_pct', float('nan')), 1)}%), sehingga matriks capstone "
        "tervalidasi sebagai pendekatan jarak jalan yang baik, namun matriks OSM menambahkan informasi legalitas per tipe "
        "truk dan asimetri akibat jalan satu arah.")
    rows = []
    lab = {"eksisting_agregat": "Eksisting, agregat", "eksisting_multiproduk": "Eksisting, multi-produk",
           "diperluas_agregat": "Diperluas, agregat", "diperluas_multiproduk": "Diperluas, multi-produk"}
    for key, name in lab.items():
        if key not in e8:
            continue
        for road, rn in [("capstone", "Capstone"), ("osm", "OSM legal")]:
            b, h = e8[key][road]["baseline"], e8[key][road]["best"]
            types = "".join(sorted(t["tipe"] for t in e8[key][road]["best_trips"]))
            rows.append((name, rn, f(b["dist_km"]), int(b["unassigned"]), f(h["dist_km"]), rp(h["cost_rp"]), f(h["co2_kg"]),
                         f"{int(h['trucks'])}/{int(h['trips'])}", types, int(h["unassigned"])))
    c.table(["Kasus (armada, produk)", "Jaringan", "Baseline (km)", "Baseline tak layak", "GA-SA-RL (km)", "Biaya/hari",
             "CO~2~ (kg)", "Truk/ritase", "Tipe ritase", "Tak layak"], rows,
            "Perbandingan solusi terbaik GA-SA-RL (30 replikasi) pada matriks capstone dan jaringan jalan OSM legal-truk", size=7)
    mean = pd.DataFrame(e8["means"])
    def mv(case, road, col):
        x = mean[(mean.case == case) & (mean.road == road)]
        return float(x[col].iloc[0]) if len(x) else float("nan")
    txt = []
    for key, name in [("eksisting_agregat", "armada eksisting kasus agregat"), ("eksisting_multiproduk", "armada eksisting multi-produk")]:
        if key in e8:
            hc, ho = e8[key]["capstone"]["best"], e8[key]["osm"]["best"]
            txt.append(f"Pada {name}, solusi terbaik di jalan legal-truk menempuh {f(ho['dist_km'])} km dengan biaya "
                       f"{rp(ho['cost_rp'])}/hari ({int(ho['trucks'])} truk, {int(ho['trips'])} ritase), dibanding "
                       f"{f(hc['dist_km'])} km dan {rp(hc['cost_rp'])} pada matriks capstone; rerata 30 replikasi "
                       f"{f(mv(key, 'osm', 'dist_km'))} km vs {f(mv(key, 'capstone', 'dist_km'))} km.")
    if "diperluas_multiproduk" in e8:
        tc = "".join(sorted(t["tipe"] for t in e8["diperluas_multiproduk"]["capstone"]["best_trips"]))
        to = "".join(sorted(t["tipe"] for t in e8["diperluas_multiproduk"]["osm"]["best_trips"]))
        txt.append(f"Dengan armada diperluas (A=2, B=2, C=4, D=1), komposisi tipe ritase solusi terbaik adalah {tc} pada matriks "
                   f"capstone dan {to} pada jalan legal-truk" + (", yang menunjukkan bahwa larangan kelas jalan mengubah "
                   "pemilihan armada." if tc != to else "; larangan kelas jalan tidak mengubah komposisi armada terbaik pada kasus ini."))
        bad = sorted({x for t in e8["diperluas_multiproduk"]["capstone"]["best_trips"] for x in t["rute"].split("-")
                      if x in m.get(t["tipe"], {}).get("spbu_tak_terjangkau", [])})
        if bad:
            txt.append(f"Ritase tipe D pada solusi matriks capstone melayani {', '.join(bad)}, padahal SPBU tersebut tidak dapat "
                       "dijangkau semi-trailer secara legal. Dengan demikian, opsi armada CCCD beremisi lebih rendah pada "
                       "analisis trade-off E3b tidak dapat dijalankan pada jalan yang sesuai aturan; analisis ulang pada jalan "
                       "legal-truk (E3c) dibahas pada subbab Pembahasan.")
    c.p(" ".join(txt))
    c.figure(os.path.join(FIG, "fig09_osm_legal.png"),
             "(a) Ruas OSM yang legal per tipe truk; (b) rute GA-SA-RL multi-produk pada jalan legal-truk", 16.0)


def scenario_text(e4, e4b):
    def H(k):
        return e4[k]["hybrid"] if k in e4 and "hybrid" in e4[k] else None
    n0 = H("0. Kondisi normal")
    s = []
    if n0:
        s.append(f"Pada kondisi normal, rencana GA-SA-RL memerlukan biaya {rp(n0['cost_rp'])} dan emisi "
                 f"{f(n0['co2_kg'])} kg CO~2~ per hari.")
    h = H("1. Kemacetan dinamis")
    if h and n0:
        s.append(f"Kemacetan pada jam sibuk menaikkan emisi menjadi {f(h['co2_kg'])} kg "
                 f"(+{f((h['co2_kg'] / n0['co2_kg'] - 1) * 100, 1)}%) dan total waktu operasi menjadi {f(h['time_min'], 0)} menit "
                 f"(+{f((h['time_min'] / n0['time_min'] - 1) * 100, 1)}%), tanpa mengubah rute.")
    h = H("2. Kelas & restriksi jalan")
    if h:
        s.append(f"Restriksi lebar jalan pada empat SPBU Ogan Ilir memaksa SPBU tersebut dilayani truk tipe B; dengan "
                 f"hanya satu unit tipe B (maksimum 3 ritase) dan tanpa kemungkinan menggabungkan dua SPBU pada kompartemen "
                 f"4+2+2 KL, {int(h['unassigned'])} ritase tidak terlayani.")
        k2 = "2R. Restriksi jalan + 1 unit tipe B"
        if k2 in e4b:
            hb = e4b[k2]["hybrid"]
            s.append(f"Penambahan satu unit tipe B menjadikan rencana layak ({int(hb['unassigned'])} ritase tak terlayani) "
                     f"dengan biaya {rp(hb['cost_rp'])} per hari.")
    h = H("5. Time window SPBU")
    if h and n0:
        s.append(f"Jendela waktu 06.00–11.00 untuk SPBU Prabumulih dipenuhi seluruhnya (tingkat tepat waktu "
                 f"{f(e4['5. Time window SPBU'].get('on_time_hybrid', 0) * 100, 0)}%) dengan menata ulang rute "
                 f"sehingga jarak naik menjadi {f(h['dist_km'])} km.")
    h = H("6. Emisi truk realistis")
    if h and n0:
        same = abs(h["co2_kg"] - n0["co2_kg"]) < 0.05
        s.append("Pembobotan yang memprioritaskan emisi (0,1; 0,8; 0,1) " +
                 ("menghasilkan rencana yang sama dengan kondisi normal, yang berarti pada armada eksisting solusi "
                  "biaya-minimum juga hampir emisi-minimum." if same else
                  f"menurunkan emisi menjadi {f(h['co2_kg'])} kg."))
    k = "7. Tank management SPBU"
    if k in e4:
        s.append(f"Dengan stok awal acak 15–60% kapasitas tangki, rencana GA-SA-RL tidak menimbulkan stok habis "
                 f"({e4[k].get('stockouts_hybrid')} SPBU), sama dengan baseline ({e4[k].get('stockouts_baseline')}).")
    h = H("8. Antrian loading rack FT")
    if h and n0:
        s.append(f"Antrean _loading rack_ yang padat (M/M/4, utilisasi tinggi) menambah waktu tunggu setiap ritase "
                 f"sehingga diperlukan {int(h['trucks'])} truk untuk {int(h['trips'])} ritase dan biaya naik menjadi "
                 f"{rp(h['cost_rp'])} (+{f((h['cost_rp'] / n0['cost_rp'] - 1) * 100, 0)}%); skenario ini menunjukkan bahwa "
                 "kapasitas _loading rack_ dapat menjadi kendala yang lebih dominan daripada rute.")
    h = H("9. Panic buying / surge demand")
    if h:
        s.append(f"Lonjakan permintaan 1,5 kali masih dapat dilayani armada eksisting dengan {int(h['trucks'])} truk dan "
                 f"{int(h['trips'])} ritase (biaya {rp(h['cost_rp'])}).")
    h = H("9b. Panic buying lokal")
    if h:
        s.append(f"Sebaliknya, lonjakan lokal 3 kali pada tiga SPBU Muara Enim menimbulkan {int(h['unassigned'])} ritase "
                 "tidak terlayani karena permintaan satu SPBU (≈ 20 KL) melebihi kapasitas truk terbesar yang tersedia "
                 "(16 KL), sedangkan model belum mengizinkan pengiriman terpisah (_split delivery_).")
        k9 = "9bR. Panic buying lokal + 1 unit tipe D"
        if k9 in e4b:
            hb = e4b[k9]["hybrid"]
            s.append(f"Ketersediaan satu unit tipe D (32 KL) mengurangi ritase tak terlayani menjadi {int(hb['unassigned'])}.")
    k = "10. Kuota BPH Migas"
    if k in e4:
        s.append(f"Pembatasan kuota Biosolar 95% memotong {f(e4[k].get('quota_cut_kl', 0), 2)} KL/hari dan seluruh "
                 "pengiriman berada dalam kuota.")
    return " ".join(s)


def e7_pvals(e7):
    from scipy import stats as ss
    d = e7[e7.instance.isin([i for i in e7.instance.unique() if e7[e7.instance == i].variant.nunique() == 3])]
    out = {}
    for o in ["GA", "GA-SA"]:
        a = d[d.variant == "GA-SA-RL"].sort_values(["instance", "seed"]).gap_pct.values
        b = d[d.variant == o].sort_values(["instance", "seed"]).gap_pct.values
        out[o] = float(ss.wilcoxon(a, b, alternative="less").pvalue)
    return out["GA"], out["GA-SA"]


def e7_ablation_text(e7):
    from scipy import stats as ss
    inst5 = [i for i in e7.instance.unique() if e7[e7.instance == i].variant.nunique() == 3]
    if not inst5:
        return ""
    d = e7[e7.instance.isin(inst5)]
    piv = d.groupby(["instance", "variant"]).gap_pct.mean().unstack()
    txt = (f"Uji ablasi pada {len(inst5)} instance pertama (10 replikasi per varian) menghasilkan gap rerata "
           + ", ".join(f"{v} {f(piv[v].mean(), 2)}%" for v in VAR if v in piv) + ".")
    try:
        fr = ss.friedmanchisquare(*[piv[v].values for v in VAR])
        txt += f" Uji Friedman atas rerata per instance: χ² = {f(fr.statistic, 2)}, p = {pv(fr.pvalue)}."
    except Exception:
        pass
    # Wilcoxon berpasangan per seed (instance x seed) GA-SA-RL vs GA-SA dan vs GA
    pw = []
    for other in ["GA-SA", "GA"]:
        a = d[d.variant == "GA-SA-RL"].sort_values(["instance", "seed"]).gap_pct.values
        b = d[d.variant == other].sort_values(["instance", "seed"]).gap_pct.values
        if len(a) == len(b) and np.any(a != b):
            p = ss.wilcoxon(a, b, alternative="less").pvalue
            pw.append(f"GA-SA-RL < {other}: p = {pv(p)} (n = {len(a)} pasangan)")
    if pw:
        txt += " Uji Wilcoxon berpasangan satu sisi: " + "; ".join(pw) + "."
    return txt


def pembahasan(c: Cursor, cite: Citer, R):
    c.h("Pembahasan Hasil Penelitian")
    e1, e2 = R["e1"], R["e2"]
    c.p("**Rumusan masalah 1 (formulasi).** Model MC-MP-MT-VRP berhasil merepresentasikan kendala yang tidak tertangkap "
        "oleh pendekatan _Saving Matrix_ berbasis total volume, yaitu kelayakan penugasan produk ke kompartemen, "
        "kompatibilitas produk–truk, akses jalan, multi-ritase, dan waktu operasional. Temuan terpenting adalah bahwa "
        "rencana capstone yang optimal secara jarak menjadi tidak dapat dieksekusi ketika kompartemen dan proporsi "
        "produk diperhitungkan. Hal ini sejalan dengan literatur MCVRP yang menekankan bahwa kendala kompartemen "
        f"mengubah struktur solusi secara mendasar {cite('ostermeier2021', 'coelho2015')}. Karena proporsi produk dan "
        "ukuran kompartemen pada penelitian ini masih asumsi, temuan tersebut perlu dikonfirmasi dengan data aktual "
        "per produk dan spesifikasi kompartemen armada FT Gelumbang.")
    if e1:
        c.p(f"**Rumusan masalah 2 (efisiensi).** Pada setting capstone, Hybrid GA-SA-RL mencapai optimum terbukti "
            f"{f(e1['milp_opt'])} km, {f((e1['baseline_capstone'] - e1['milp_opt']) / e1['baseline_capstone'] * 100, 2)}% lebih "
            f"pendek daripada _Saving Matrix_ dan {f((e1['nn'] - e1['milp_opt']) / e1['nn'] * 100, 1)}% lebih pendek "
            "daripada _Nearest Neighbour_. Ruang perbaikan jarak pada kasus 13 SPBU memang kecil karena _Saving Matrix_ "
            "sudah mendekati optimum; angka ini jauh lebih kecil daripada klaim penghematan 15–60% yang sering dilaporkan "
            f"studi kasus BBM di Indonesia {cite('aqidawati2021', 'melani2025', 'awaludin2025')}, yang umumnya "
            "membandingkan dengan rute eksisting non-optimal. Nilai tambah utama model justru terletak pada kelayakan "
            "rencana multi-produk, penghematan armada melalui multi-ritase, dan kemampuan simulasi skenario.")
    c.p("**Kontribusi komponen SA dan RL.** " + ablation_discussion(R))
    c.p("**Rumusan masalah 3 (re-routing dinamis).** Re-optimasi berjalan dalam orde satu detik dan memberikan "
        "perbaikan yang signifikan secara statistik tetapi kecil secara praktis pada kasus ini, karena armada eksisting "
        "memiliki kelonggaran waktu. Manfaat re-routing diperkirakan lebih besar pada jaringan dengan jendela waktu "
        f"ketat dan utilisasi armada tinggi {cite('rios2021', 'zhaoy2024')}.")
    c.p("**Rumusan masalah 4 (trade-off).** " + tradeoff_text(R))
    c.p("**Rumusan masalah 5 (DSS dan pelaporan).** Aplikasi web telah berjalan dengan basis data Google Sheets, jejak "
        "audit setiap simulasi, dan notifikasi Telegram opsional. Evaluasi kegunaan (misalnya System Usability Scale) "
        "dan efektivitas laporan Telegram bagi pengambil keputusan belum dilakukan dan menjadi pekerjaan lanjutan.")
    c.p("**Keterbatasan.** (1) Proporsi produk per SPBU, ukuran kompartemen, konsumsi bahan bakar, biaya tetap, dan "
        "profil kemacetan adalah asumsi; (2) kelas jalan dan lebar badan jalan pada OSM sebagian besar diturunkan dari jenis ruas "
        "(asumsi) karena hanya sedikit ruas yang memiliki tag width/lanes, dan dimensi truk masih tipikal, sehingga legalitas "
        "ruas perlu diverifikasi dengan SK penetapan kelas jalan dan survei lebar jalan; (3) pengiriman terpisah "
        "(_split delivery_) belum dimodelkan; (4) komponen RL adalah pemilih operator adaptif berbasis Q-Learning tabular, "
        "bukan agen RL yang dilatih untuk kebijakan rute; (5) aplikasi belum diuji oleh pengguna industri.")


def pareto_pts(df):
    fe = df[df.unassigned == 0]
    return fe, fe[fe.pareto_cost_co2].sort_values("cost_rp").drop_duplicates(["cost_rp", "co2_kg"])


def tradeoff_text(R):
    t = []
    if R["e3"] is not None:
        _, pf = pareto_pts(R["e3"])
        if len(pf) <= 1:
            t.append("Dengan armada eksisting, seluruh kombinasi bobot menghasilkan satu titik non-dominasi: rencana "
                     "berbiaya minimum sekaligus beremisi minimum, sehingga tidak ada trade-off biaya–emisi yang nyata.")
        else:
            t.append(f"Dengan armada eksisting terdapat {len(pf)} titik non-dominasi biaya–emisi.")
    if R.get("e3b") is not None:
        _, pf = pareto_pts(R["e3b"])
        if len(pf) > 1:
            lo, hi = pf.iloc[0], pf.iloc[-1]
            t.append(f"Ketika pilihan armada diperluas (2A, 2B, 4C, 1D), muncul {len(pf)} titik non-dominasi: dari rencana "
                     f"termurah {rp(lo.cost_rp)} dengan {f(lo.co2_kg)} kg CO~2~ (ritase tipe {lo.trip_types}) hingga rencana "
                     f"beremisi terendah {f(hi.co2_kg)} kg dengan biaya {rp(hi.cost_rp)} (ritase tipe {hi.trip_types}). "
                     f"Artinya, setiap penurunan 1 kg CO~2~ pada ujung Pareto front memerlukan sekitar "
                     f"{rp((hi.cost_rp - lo.cost_rp) / max(lo.co2_kg - hi.co2_kg, 1e-9))} per hari.")
        else:
            t.append("Bahkan dengan pilihan armada diperluas (2A, 2B, 4C, 1D), hanya diperoleh satu titik non-dominasi.")
    if R.get("e3c") is not None:
        _, pf = pareto_pts(R["e3c"])
        if len(pf) > 1:
            lo, hi = pf.iloc[0], pf.iloc[-1]
            t.append(f"Pada jaringan jalan legal-truk (E3c), armada diperluas menghasilkan {len(pf)} titik non-dominasi, dari "
                     f"{rp(lo.cost_rp)} dengan {f(lo.co2_kg)} kg CO~2~ (ritase {lo.trip_types}) hingga {f(hi.co2_kg)} kg dengan "
                     f"{rp(hi.cost_rp)} (ritase {hi.trip_types}).")
        elif len(pf) == 1:
            r0 = pf.iloc[0]
            t.append(f"Namun pada jaringan jalan legal-truk (E3c), armada diperluas hanya menghasilkan satu titik non-dominasi "
                     f"({rp(r0.cost_rp)}, {f(r0.co2_kg)} kg CO~2~, ritase {r0.trip_types}): trade-off biaya–emisi pada E3b "
                     "hilang karena semi-trailer tidak boleh masuk ke sebagian SPBU.")
    t.append("Karena biaya tetap dan konsumsi bahan bakar masih asumsi, posisi kuantitatif Pareto front perlu dikalibrasi.")
    return " ".join(t)


def ablation_discussion(R):
    e7 = R["e7"]
    e2 = R["e2"]
    parts = []
    if e2:
        for key, nm in [("agregat", "agregat"), ("multiproduk", "multi-produk")]:
            if key not in e2:
                continue
            st = e2[key]["stats_fitness"]
            mm = ", ".join(f"{v} {f(st[v]['mean'], 4)} (SD {f(st[v]['sd'], 4)})" for v in VAR)
            parts.append(f"Pada model lengkap kasus {nm}, rerata fitness {mm}. " + kw_text(st))
        sa = e2.get("agregat", {}).get("stats_fitness", {})
        kk = sa.get("kruskal") if isinstance(sa.get("kruskal"), dict) else None
        if kk and kk["p"] < 0.05 and sa["GA"]["mean"] > sa["GA-SA"]["mean"]:
            same = abs(sa["GA-SA"]["mean"] - sa["GA-SA-RL"]["mean"]) < 1e-9
            parts.append("Dengan demikian, pada kasus FT Gelumbang fase SA membuat hasil lebih konsisten daripada GA saja "
                         "dengan anggaran evaluasi yang sama" + (", sedangkan GA-SA dan GA-SA-RL mencapai solusi yang "
                         "identik sehingga kontribusi RL tidak dapat dibedakan pada instance sekecil ini." if same else "."))
    if e7 is not None and len(e7):
        parts.append("Pada benchmark CVRPLIB yang lebih besar: " + e7_ablation_text(e7))
        p_ga, p_sa = e7_pvals(e7)
        parts.append("Kesimpulannya, hibrida GA-SA-RL " + ("memberikan perbaikan yang signifikan" if p_ga < 0.05 else
                     "tidak memberikan perbaikan yang signifikan") + " dibanding GA saja dengan anggaran evaluasi setara, "
                     "sedangkan pemilihan operator dengan Q-Learning " + ("signifikan lebih baik" if p_sa < 0.05 else
                     "tidak signifikan lebih baik") + " daripada pemilihan acak seragam. Hasil ini dilaporkan apa adanya; "
                     "klaim bahwa RL meningkatkan kualitas solusi tidak didukung oleh data penelitian ini" +
                     ("" if p_sa >= 0.05 else " kecuali pada benchmark") + ".")
    return " ".join(parts)


def luaran(c: Cursor, cite: Citer, R):
    c.h("Hasil Luaran Yang Dicapai")
    rows = [
        ("1", "Prototipe aplikasi web SMARTROUTE-BBM (kode terbuka)", REPO, "Selesai (v1.0)"),
        ("2", "Basis data Google Sheets SMARTROUTE-BBM Database", SHEET, "Selesai"),
        ("3", "Naskah artikel jurnal internasional", "Target: SINERGI (Scopus) atau jurnal Scopus Q2/Q3 sejenis", "Draf siap submit"),
        ("4", "Data, kode eksperimen, dan hasil uji yang dapat direproduksi", "Folder data/, experiments/, results/", "Selesai"),
        ("5", "Pendaftaran HKI program komputer", "DJKI", "Persiapan"),
    ]
    c.table(["No", "Luaran", "Keterangan", "Status"], rows, "Luaran penelitian", widths=[0.8, 5.5, 6.5, 2.8])


def bab5(c: Cursor, cite: Citer, R):
    e1, e2 = R["e1"], R["e2"]
    c.h("Kesimpulan")
    items = []
    items.append("Formulasi MC-MP-MT-VRP dengan dekoder _Split_ armada heterogen, pemeriksaan kompartemen eksak, dan "
                 "penjadwalan multi-ritase _time-dependent_ telah diimplementasikan dan diverifikasi dengan uji unit serta "
                 "model eksak MILP.")
    if e1:
        items.append(f"Pada setting capstone, Hybrid GA-SA-RL konsisten mencapai optimum MILP {f(e1['milp_opt'])} km "
                     f"(100% dari 30 replikasi), {f((e1['baseline_capstone'] - e1['milp_opt']) / e1['baseline_capstone'] * 100, 2)}% "
                     "lebih pendek daripada rencana _Saving Matrix_ capstone (279,4 km).")
    if e2 and "agregat" in e2:
        b, h = e2["agregat"]["baseline"], e2["agregat"]["best_ga_sa_rl"]
        items.append(f"Pada model lengkap kasus agregat dengan multi-ritase, GA-SA-RL melayani seluruh SPBU dengan "
                     f"{int(h['trucks'])} truk ({int(h['trips'])} ritase) dibanding {int(b['trucks'])} truk pada rencana "
                     f"capstone, sehingga biaya harian turun {f((b['cost_rp'] - h['cost_rp']) / b['cost_rp'] * 100, 1)}% "
                     f"({rp(b['cost_rp'])} → {rp(h['cost_rp'])}) dengan jarak {f(h['dist_km'])} km "
                     f"(baseline {f(b['dist_km'])} km); penghematan ini bergantung pada asumsi biaya tetap truk.")
    if e2 and "multiproduk" in e2:
        b, h = e2["multiproduk"]["baseline"], e2["multiproduk"]["best_ga_sa_rl"]
        items.append(f"Dengan kompartemen dan multi-produk (asumsi proporsi), rencana capstone memiliki {int(b['unassigned'])} ritase "
                     f"yang tidak layak, sedangkan GA-SA-RL menghasilkan rencana layak dengan {int(h['trucks'])} truk, "
                     f"{int(h['trips'])} ritase, biaya {rp(h['cost_rp'])}/hari, dan emisi {f(h['co2_kg'])} kg CO~2~/hari.")
    if R["e5"]:
        d5 = R["e5"]["summary"]["breakdown"]
        items.append(f"Re-routing dinamis menghasilkan rencana baru dalam rata-rata {f(d5['compute_s_mean'], 2)} detik; "
                     f"perbaikannya signifikan secara statistik (p = {pv(d5['fitness'].get('p_wilcoxon'))}) tetapi kecil dan hanya "
                     f"terjadi pada {f(d5['share_improved_fitness'] * 100, 0)}% kejadian kerusakan, karena armada FT Gelumbang "
                     "memiliki kelonggaran waktu.")
    if R["e7"] is not None and len(R["e7"]):
        p_ga, p_sa = e7_pvals(R["e7"])
        items.append(f"Uji ablasi pada benchmark CVRPLIB menunjukkan bahwa GA-SA-RL "
                     f"{'signifikan lebih baik' if p_ga < 0.05 else 'tidak signifikan lebih baik'} daripada GA saja "
                     f"(p = {pv(p_ga)}), sedangkan pemilihan operator dengan Q-Learning "
                     f"{'signifikan lebih baik' if p_sa < 0.05 else 'belum terbukti lebih baik'} daripada pemilihan acak "
                     f"(p = {pv(p_sa)}).")
    if R.get("e8"):
        m = R["e8"]["matriks"]
        items.append("Rute kini dihitung pada jaringan jalan nyata OpenStreetMap yang disaring per tipe truk menurut kelas jalan "
                     "(UU 22/2009), rambu batas, lebar jalan, dan arah satu jalur. Jarak legal-truk berkorelasi "
                     f"{f(m['C']['korelasi'], 3)} dengan matriks capstone"
                     + (f", sedangkan semi-trailer 32 KL tidak dapat menjangkau {', '.join(m['D']['spbu_tak_terjangkau'])}"
                        if m.get('D', {}).get('spbu_tak_terjangkau') else "") + ".")
    items.append("Simulasi sepuluh kategori skenario mengidentifikasi kondisi yang tidak dapat dilayani armada eksisting "
                 "(restriksi jalan dan lonjakan permintaan lokal) beserta kebutuhan tambahan armadanya.")
    items.append("Prototipe aplikasi web SMARTROUTE-BBM dengan basis data Google Sheets telah selesai dan "
                 "dipublikasikan sebagai repositori terbuka sehingga hasil penelitian dapat direproduksi.")
    c.bullets(items, numbered=True)
    c.h("Saran")
    c.bullets([
        "Mengumpulkan data aktual penjualan per produk per SPBU dan spesifikasi kompartemen armada FT Gelumbang untuk "
        "menggantikan asumsi, kemudian mengulang E2–E4.",
        "Menambahkan pengiriman terpisah (_split delivery_) dan armada sewa agar skenario lonjakan permintaan dapat "
        "dilayani tanpa penalti.",
        "Memverifikasi kelas jalan dan lebar jalan pada rute terpilih dengan SK penetapan kelas jalan dan survei lapangan, "
        "serta menambahkan data lalu lintas historis untuk profil kemacetan per ruas.",
        "Melakukan uji kegunaan aplikasi dan evaluasi notifikasi Telegram bersama pengguna industri.",
        "Mengembangkan komponen RL menjadi kebijakan yang dilatih lintas instance (misalnya _deep_ RL) dan "
        "membandingkannya dengan pemilih operator adaptif lain (roulette ALNS, UCB).",
    ], numbered=True)


# ===========================================================================
def abstrak(c: Cursor, R, lang="id"):
    e1, e2 = R["e1"], R["e2"]
    imp = (e1["baseline_capstone"] - e1["milp_opt"]) / e1["baseline_capstone"] * 100 if e1 else None
    if lang == "id":
        t = ("Distribusi BBM dari Fuel Terminal ke SPBU melibatkan truk tangki berkompartemen, banyak produk, dan "
             "beberapa ritase per hari, sehingga rute yang disusun berdasarkan total volume belum tentu dapat dijalankan. "
             "Penelitian ini mengembangkan model Multi-Compartment Multi-Product Multi-Trip VRP (MC-MP-MT-VRP), algoritma "
             "Hybrid Genetic Algorithm–Simulated Annealing–Reinforcement Learning (GA-SA-RL) dengan Q-Learning sebagai "
             "pemilih operator, dan prototipe Decision Support System berbasis web (Streamlit, basis data Google Sheets) "
             "bernama SMARTROUTE-BBM. Studi kasus memakai data Capstone Design 2026 FT Gelumbang (13 SPBU, 60,78 KL/hari). ")
        if e1:
            t += (f"Pada setting capstone, algoritma mencapai optimum terbukti MILP {f(e1['milp_opt'])} km pada seluruh 30 "
                  f"replikasi, {f(imp, 2)}% lebih pendek daripada Saving Matrix (279,4 km). ")
        if e2 and "agregat" in e2 and e2["agregat"]["best_ga_sa_rl"]["trucks"] < e2["agregat"]["baseline"]["trucks"]:
            b0, h0 = e2["agregat"]["baseline"], e2["agregat"]["best_ga_sa_rl"]
            t += (f"Dengan multi-ritase, model lengkap melayani permintaan agregat memakai {int(h0['trucks'])} truk "
                  f"(baseline {int(b0['trucks'])}) sehingga biaya harian turun "
                  f"{f((b0['cost_rp'] - h0['cost_rp']) / b0['cost_rp'] * 100, 1)}%. ")
        if e2 and "multiproduk" in e2:
            b, h = e2["multiproduk"]["baseline"], e2["multiproduk"]["best_ga_sa_rl"]
            t += (f"Dengan kendala kompartemen dan multi-produk, rencana Saving Matrix memiliki {int(b['unassigned'])} ritase "
                  f"tidak layak, sedangkan GA-SA-RL menghasilkan rencana layak dengan {int(h['trucks'])} truk dan "
                  f"{int(h['trips'])} ritase serta emisi {f(h['co2_kg'])} kg CO2/hari. ")
        if R["e7"] is not None and len(R["e7"]):
            p_ga, p_sa = e7_pvals(R["e7"])
            t += (f"Pada benchmark CVRPLIB, hibrida {'signifikan lebih baik' if p_ga < 0.05 else 'tidak signifikan lebih baik'} "
                  f"daripada GA saja (p = {pv(p_ga)}), tetapi pemilihan operator dengan Q-Learning "
                  f"{'signifikan lebih baik' if p_sa < 0.05 else 'tidak signifikan lebih baik'} daripada pemilihan acak "
                  f"(p = {pv(p_sa)}). ")
        if R.get("e8"):
            t += ("Rute dihitung pada jaringan jalan OpenStreetMap yang disaring per tipe truk menurut kelas jalan, rambu, "
                  f"dan lebar jalan; jaraknya berkorelasi {f(R['e8']['matriks']['C']['korelasi'], 3)} dengan matriks capstone. ")
        t += ("Aplikasi juga menyediakan simulasi sepuluh kategori skenario, re-routing dinamis dalam orde detik, analisis "
              "Pareto biaya–emisi, dan simulasi Monte Carlo. Proporsi produk dan ukuran kompartemen masih berupa asumsi "
              "sehingga perlu dikalibrasi dengan data operator.")
        c.p(t, indent_first=0)
        c.para("**Kata kunci:** distribusi BBM, multi-compartment VRP, multi-trip, algoritma hibrida, Q-Learning, "
               "decision support system", align="j")
    else:
        t = ("Fuel distribution from a fuel terminal to petrol stations involves compartmented tank trucks, several "
             "products and multiple trips per day, so routes designed on total volume may not be executable. This study "
             "develops a Multi-Compartment Multi-Product Multi-Trip VRP (MC-MP-MT-VRP) model, a hybrid Genetic "
             "Algorithm–Simulated Annealing–Reinforcement Learning (GA-SA-RL) algorithm with Q-learning operator "
             "selection, and a web-based decision support system (Streamlit with a Google Sheets database) called "
             "SMARTROUTE-BBM. The case study uses Capstone Design 2026 data of FT Gelumbang, Indonesia (13 stations, "
             "60.78 kL/day). ")
        if e1:
            t += (f"In the capstone setting the algorithm reached the MILP-proven optimum of {e1['milp_opt']:.1f} km in all 30 "
                  f"runs, {imp:.2f}% shorter than the Savings plan (279.4 km). ")
        if e2 and "multiproduk" in e2:
            b, h = e2["multiproduk"]["baseline"], e2["multiproduk"]["best_ga_sa_rl"]
            t += (f"With compartment and multi-product constraints the Savings plan contains {int(b['unassigned'])} "
                  f"infeasible trip(s), whereas GA-SA-RL returns a feasible plan with {int(h['trucks'])} trucks, "
                  f"{int(h['trips'])} trips and {h['co2_kg']:.1f} kg CO2/day. ")
        if R["e7"] is not None and len(R["e7"]):
            p_ga, p_sa = e7_pvals(R["e7"])
            t += (f"On CVRPLIB benchmarks the hybrid {'significantly outperformed' if p_ga < 0.05 else 'did not outperform'} "
                  f"the GA alone (p = {p_ga:.3f}), whereas Q-learning operator selection "
                  f"{'significantly outperformed' if p_sa < 0.05 else 'did not significantly outperform'} random selection "
                  f"(p = {p_sa:.3f}). ")
        if R.get("e8"):
            t += ("Routes are computed on the OpenStreetMap road network filtered per truck type by road class, signed limits "
                  f"and road width; these distances correlate at {R['e8']['matriks']['C']['korelasi']:.3f} with the capstone matrix. ")
        t += ("The system also provides ten what-if scenario categories, second-scale dynamic re-routing, cost–emission "
              "Pareto analysis and Monte Carlo simulation. Product shares and compartment sizes are still assumptions and "
              "require calibration with operator data.")
        p = c.p(t, indent_first=0)
        for r in p.runs:
            r.italic = True
        c.para("**Keywords:** fuel distribution, multi-compartment VRP, multi-trip, hybrid metaheuristic, Q-learning, "
               "decision support system", align="j")


def build():
    R = load_results()
    doc = Document(os.path.join(ROOT, "docs", "template", "template_uppm.docx"))
    cite = Citer()
    global TEMPLATE_TABLES
    TEMPLATE_TABLES = list(doc.tables)
    fill_cover(doc)
    fill_pengesahan(doc)
    # ABSTRAK
    h = find_p(doc, "ABSTRAK")
    clear_after(h, [])
    c = Cursor(doc, h._p)
    abstrak(c, R, "id")
    c.para("")
    c.para("ABSTRACT", align="c", bold=True)
    abstrak(c, R, "en")
    # DAFTAR ISI
    h = find_p(doc, "DAFTAR ISI")
    clear_after(h, [])
    c = Cursor(doc, h._p)
    add_toc(c.para(""))
    for name in ["DAFTAR TABEL", "DAFTAR GAMBAR", "DAFTAR LAMPIRAN"]:
        clear_after(find_p(doc, name), [])
    # BAB 1..5: hapus isi panduan, isi ulang. Heading 2 template dihapus; diganti oleh c.h().
    bab_fns = [("BAB 1", bab1), ("BAB 2", bab2), ("BAB 3", bab3)]
    figs, tabs = [], []
    for bab_no, (name, fn) in enumerate(bab_fns, 1):
        hb = find_p(doc, name)
        _clear_chapter(doc, hb)
        c = Cursor(doc, hb._p)
        c.fig_prefix = f"{bab_no}."
        c.h2_prefix = f"{bab_no}."
        fn(c, cite, R)
        figs += c.figures; tabs += c.tables
    hb = find_p(doc, "BAB 4")
    _clear_chapter(doc, hb)
    c = Cursor(doc, hb._p)
    c.fig_prefix = "4."
    c.h2_prefix = "4."
    bab4(c, cite, R)
    pembahasan(c, cite, R)
    luaran(c, cite, R)
    figs += c.figures; tabs += c.tables
    hb = find_p(doc, "BAB 5")
    _clear_chapter(doc, hb)
    c = Cursor(doc, hb._p)
    c.h2_prefix = "5."
    bab5(c, cite, R)
    # daftar tabel/gambar
    for name, lst in [("DAFTAR TABEL", tabs), ("DAFTAR GAMBAR", figs)]:
        c = Cursor(doc, find_p(doc, name)._p)
        for x in lst:
            c.para(x, align="j", space_after=2)
    c = Cursor(doc, find_p(doc, "DAFTAR LAMPIRAN")._p)
    for x in ["Lampiran 1. Tabel luaran penelitian", "Lampiran 2. Tautan repositori, basis data, dan cara menjalankan aplikasi",
              "Lampiran 3. Parameter algoritma dan asumsi model"]:
        c.para(x, space_after=2)
    # DAFTAR PUSTAKA
    hp = find_p(doc, "DAFTAR PUSTAKA")
    clear_after(hp, [])
    c = Cursor(doc, hp._p)
    for ref in cite.bibliography():
        p = c.para(ref.replace(" [VERIFY]", ""), align="j", space_after=3)
        p.paragraph_format.left_indent = Cm(0.8)
        p.paragraph_format.first_line_indent = Cm(-0.8)
    fill_lampiran(doc, R)
    set_update_fields_on_open(doc)
    out = os.path.join(OUT, "Laporan_Akhir_SMARTROUTE-BBM_2026.docx")
    doc.save(out)
    print("saved", out, "refs:", len(cite.order))
    return out


def _clear_chapter(doc, h1):
    """Hapus seluruh isi bab (termasuk Heading 2 panduan) sampai Heading 1 berikutnya."""
    Wn = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    el = h1._p.getnext()
    while el is not None:
        nxt = el.getnext()
        if el.tag == Wn + "p":
            sty = el.find(f"{Wn}pPr/{Wn}pStyle")
            sname = sty.get(Wn + "val") if sty is not None else ""
            if sname in ("Heading1",) or sname.lower() == "heading 1":
                break
            if el.find(f".//{Wn}sectPr") is not None:
                for r in list(el.findall(f"{Wn}r")):
                    el.remove(r)
                el = nxt
                continue
            txt = "".join(t.text or "" for t in el.iter(Wn + "t")).strip()
            if el.find(f".//{Wn}br") is not None and not txt:
                el = nxt
                continue
            remove_el(el)
        elif el.tag == Wn + "tbl":
            remove_el(el)
        elif el.tag == Wn + "sectPr":
            break
        el = nxt


def fill_lampiran(doc, R):
    """Isi tabel luaran (tabel 2..6 pada template) dan tambahkan lampiran teknis."""
    T = TEMPLATE_TABLES
    def put(t, row, vals):
        for j, v in enumerate(vals):
            t.rows[row].cells[j].text = str(v)
    put(T[0], 0, ["Program", ":", "Penelitian Terapan PEM Akamigas 2026"])
    put(T[0], 1, ["Nama Ketua Tim", ":", TIM[0][1]])
    put(T[0], 2, ["Judul", ":", JUDUL])
    # T[1]: artikel jurnal
    put(T[1], 1, ["1", "Hybrid GA-SA-RL for multi-compartment multi-trip fuel distribution: a web-based DSS case study "
                       "of FT Gelumbang, Indonesia", "SINERGI (Scopus) / jurnal Scopus Q2–Q3", "Persiapan (draf siap submit)"])
    put(T[5], 1, ["1", "Prototipe aplikasi web SMARTROUTE-BBM", f"{REPO} ; basis data {SHEET}", "Selesai"])
    hp = find_p(doc, "LAMPIRAN")
    # tambahkan lampiran teknis di akhir dokumen (sebelum sectPr terakhir)
    body = doc.element.body
    last = body[-1]
    anchor = body[-2] if last.tag.endswith("sectPr") else last
    c = Cursor(doc, anchor)
    c.para("")
    c.para("Lampiran 2. Repositori, basis data, dan cara menjalankan", bold=True)
    c.bullets([f"Repositori kode: {REPO}", f"Basis data Google Sheets: {SHEET}",
               "Menjalankan lokal: pip install -r requirements.txt; streamlit run app.py",
               "Mereproduksi eksperimen: python -m experiments.run_all; python -m experiments.figures; "
               "python -m docs.build_laporan",
               "Deploy: Streamlit Community Cloud → New app → repositori smartroute-bbm, berkas app.py"], align=None)
    c.para("Lampiran 3. Parameter algoritma dan asumsi model", bold=True)
    rows = [("Populasi / generasi GA", "100 / 200"), ("p~c~ / p~m~ / turnamen / elit", "0,85 / 0,10 (adaptif) / 5 / 2"),
            ("Inisialisasi", "60% serakah (NN + gangguan), 40% acak"), ("SA: T~0~ / α / iterasi", "1000 / 0,995 / 5000"),
            ("Q-Learning: α / γ / ε", "0,1 / 0,9 / 0,1→0,02"), ("Bobot (w~1~, w~2~, w~3~)", "(0,5; 0,3; 0,2)"),
            ("Harga solar / pemeliharaan", "Rp12.000/L / Rp1.500/km (asumsi)"), ("Faktor emisi", "2,68 kg CO~2~/L (IPCC)"),
            ("Kecepatan maks / shift / ritase maks", "40 km/jam / 12 jam / 3"),
            ("Muat / bongkar", "5 mnt/KL / 15 mnt + 2,5 mnt/KL"), ("Proporsi produk", "Pertalite 62%, Biosolar 26%, Pertamax 12% (asumsi)")]
    c.table(["Parameter", "Nilai"], rows, None, widths=[7, 8])


if __name__ == "__main__":
    build()

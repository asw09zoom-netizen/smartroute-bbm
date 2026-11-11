"""Isi BAB 1–3 dan abstrak Laporan Akhir. Angka hasil dibaca dari results/; data dari data/*.csv."""
from __future__ import annotations

import os

import pandas as pd

from docs.lap_common import FIGL, REPO, ROOT, SHEET, VAR, f, pareto_pts, pct, pv, rp, e7_tests

D = lambda name: pd.read_csv(os.path.join(ROOT, "data", f"{name}.csv"))  # noqa: E731


# ===========================================================================
def abstract_text(R, lang):
    e1, app, e8, e9, e10 = R["e1"], R["app"], R["e8"], R["e9"], R["e10"]
    imp = (e1["baseline_capstone"] - e1["milp_opt"]) / e1["baseline_capstone"] * 100
    s, b = app["script"], app["baseline"]
    t7 = e7_tests(R["e7"]) if R["e7"] is not None else None
    sc = (e10 or {}).get("tests", [])
    if lang == "id":
        p1 = ("Rute distribusi BBM yang disusun hanya dari total volume sering tidak dapat dijalankan, karena truk "
              "tangki bersekat (kompartemen), produk lebih dari satu, dan satu truk dapat kembali memuat dua atau tiga "
              "kali dalam satu shift. Penelitian ini merumuskan _Multi-Trip Multi-Compartment Vehicle Routing Problem_ "
              "multi-produk (MC-MP-MT-VRP) untuk distribusi dari FT Gelumbang ke 13 SPBU (60,78 KL/hari), lalu "
              "menyelesaikannya dengan algoritma hibrida _Genetic Algorithm_–_Simulated Annealing_ yang operatornya "
              "dipilih oleh agen _Q-learning_ (GA-SA-RL). Jarak dihitung pada jaringan jalan OpenStreetMap yang disaring "
              "per tipe truk menurut kelas jalan UU 22/2009, rambu batas, lebar jalan, dan arah satu jalur. Model, "
              "algoritma, simulasi mikro pergerakan truk, dan re-routing dinamis dikemas dalam aplikasi web "
              "SMARTROUTE-BBM berbasis Streamlit dengan basis data Google Sheets.")
        p2 = (f"Pada setting capstone (CVRP 16 KL), GA-SA-RL mencapai optimum MILP {f(e1['milp_opt'])} km pada "
              f"30 dari 30 replikasi, {f(imp, 2)}% lebih pendek dari _Saving Matrix_ (279,4 km). Pada jalan legal-truk "
              f"dengan kompartemen dan tiga produk, rencana _Saving Matrix_ memuat {int(b['unassigned'])} ritase yang "
              f"tidak dapat dimuat truk mana pun; GA-SA-RL memberi rencana layak {int(s['trucks'])} truk/"
              f"{int(s['trips'])} ritase, {f(s['dist_km'])} km, {rp(s['cost_rp'])}/hari, dan {f(s['co2_kg'])} kg "
              "CO~2~/hari. Angka ini sama dengan keluaran aplikasi pada pengaturan bawaan. ")
        if e9:
            g = [r for r in e9["summary"] if r["case"] == "multiproduk" and r["plan"] == "GA-SA-RL" and abs(r["cv"] - 0.3) < 1e-9][0]
            p2 += (f"Simulasi mikro 300 replikasi per tingkat ketidakpastian menunjukkan rencana tersebut selesai "
                   f"rata-rata pukul {jam_txt(g['t_end_mean'])} (persentil ke-95 pukul {jam_txt(g['t_end_p95'])}) pada "
                   f"CV kecepatan 0,3 tanpa lembur. ")
        if t7:
            p2 += (f"Pada uji ablasi {t7['n_inst']} instance CVRPLIB, hibrida lebih baik dari GA saja (Wilcoxon p = {pv(t7['GA'])}), tetapi "
                   f"pemilihan operator dengan _Q-learning_ belum terbukti lebih baik dari pemilihan acak "
                   f"(p = {pv(t7['GA-SA'])}). ")
        if sc:
            ns = ", ".join(str(int(x["n"])) for x in sc)
            sig = all(x["p_vs_ga"] < 0.05 for x in sc)
            p2 += (f"Uji skalabilitas pada instance sintetis {ns} SPBU di jaringan jalan yang sama "
                   + ("menunjukkan GA-SA-RL lebih baik dari GA pada semua ukuran. " if sig else
                      "menghasilkan rencana layak pada semua ukuran, tetapi selisih fitness GA-SA-RL dan GA di bawah "
                      "0,5% dan tidak signifikan. "))
        p2 += "Proporsi produk, ukuran kompartemen, dan dimensi truk masih asumsi sehingga perlu dikalibrasi dengan data operator."
        kw = ("distribusi BBM; _multi-compartment vehicle routing_; _multi-trip_; algoritma hibrida; _Q-learning_; "
              "jaringan jalan legal-truk; sistem pendukung keputusan")
        return [p1, p2], kw
    p1 = ("Fuel delivery plans built from total volume alone are often not executable, because tank trucks have "
          "separate compartments, several products are carried, and one truck may reload two or three times per shift. "
          "This study formulates a multi-product Multi-Trip Multi-Compartment Vehicle Routing Problem (MC-MP-MT-VRP) "
          "for deliveries from the Gelumbang fuel terminal to 13 petrol stations (60.78 kL/day) and solves it with a "
          "hybrid genetic algorithm and simulated annealing whose neighbourhood operators are chosen by a Q-learning "
          "agent (GA-SA-RL). Distances come from an OpenStreetMap network filtered per truck type by Indonesian road "
          "class rules (Law 22/2009), signed limits, road width and one-way restrictions. The model, the algorithm, a "
          "truck-movement micro-simulation and dynamic re-routing are packaged in SMARTROUTE-BBM, a Streamlit web "
          "application backed by Google Sheets.")
    p2 = (f"In the capstone setting (CVRP, 16 kL) GA-SA-RL reached the MILP optimum of {e1['milp_opt']:.1f} km in all 30 "
          f"runs, {imp:.2f}% shorter than the Savings plan (279.4 km). On the truck-legal network with compartments and "
          f"three products, the Savings plan contains {int(b['unassigned'])} trip that no truck can load, while GA-SA-RL "
          f"returns a feasible plan with {int(s['trucks'])} trucks and {int(s['trips'])} trips, {s['dist_km']:.1f} km, "
          f"IDR {s['cost_rp']:,.0f}/day and {s['co2_kg']:.1f} kg CO2/day; the web application reproduces these values. ")
    if e9:
        g = [r for r in e9["summary"] if r["case"] == "multiproduk" and r["plan"] == "GA-SA-RL" and abs(r["cv"] - 0.3) < 1e-9][0]
        p2 += (f"A micro-simulation with 300 replications per uncertainty level shows the plan finishing on average at "
               f"{jam_txt(g['t_end_mean']).replace('.', ':')} (95th percentile {jam_txt(g['t_end_p95']).replace('.', ':')}) "
               "under a speed CV of 0.3, with no overtime. ")
    if t7:
        p2 += (f"In an ablation on {t7['n_inst']} CVRPLIB instances the hybrid beat the GA alone (Wilcoxon p = {t7['GA']:.3f}), but Q-learning "
               f"operator selection did not beat random selection (p = {t7['GA-SA']:.3f}). ")
    if sc:
        ns = ", ".join(str(int(x["n"])) for x in sc)
        sig = all(x["p_vs_ga"] < 0.05 for x in sc)
        p2 += (f"Scalability tests on synthetic instances with {ns} stations on the same network "
               + ("show GA-SA-RL ahead of the GA at every size. " if sig else
                  "yield feasible plans at every size, but GA-SA-RL and the GA differ by less than 0.5% in fitness, "
                  "which is not significant. "))
    p2 += "Product shares, compartment sizes and truck dimensions are still assumptions and need calibration with operator data."
    kw = ("fuel distribution; multi-compartment vehicle routing; multi-trip; hybrid metaheuristic; Q-learning; "
          "truck-legal road network; decision support system")
    return [p1, p2], kw


def jam_txt(menit):
    t = 360 + float(menit)
    h, m = int(t // 60), int(round(t % 60))
    if m == 60:
        h, m = h + 1, 0
    return f"{h:02d}.{m:02d}"


# ===========================================================================
def bab1(W, cite, R):
    W.bab(1, "PENDAHULUAN")
    W.h("Latar Belakang")
    W.p("Truk tangki yang berangkat dari _Fuel Terminal_ (FT) membawa beberapa jenis BBM sekaligus. Setiap jenis "
        "harus menempati kompartemen tersendiri, dan satu truk biasanya kembali ke FT untuk memuat ulang sebelum shift "
        "berakhir. Persoalan perencanaannya dikenal sebagai _Petrol Station Replenishment Problem_ (PSRP), turunan dari "
        f"_Vehicle Routing Problem_ (VRP) {cite('dantzig1959', 'cornillier2008', 'benantar2016')}. Varian dengan "
        f"kompartemen disebut _multi-compartment_ VRP {cite('ostermeier2021', 'coelho2015')}, sedangkan varian dengan "
        f"pemuatan ulang disebut _multi-trip_ VRP {cite('cattaruzza2016')}. Pada kasus nyata keduanya muncul bersamaan "
        f"dengan armada heterogen dan jendela waktu SPBU {cite('wang2020', 'cornillier2009', 'bani2023')}.")
    W.p("Data Capstone Design 2026 PEM Akamigas untuk FT Gelumbang (Kabupaten Muara Enim, Sumatera Selatan) mencatat 13 "
        "SPBU dengan total permintaan 60,78 KL/hari. Mahasiswa capstone menyusun lima rute dengan metode _Saving Matrix_ "
        f"{cite('clarke1964')} sepanjang 279,4 km. Perhitungan tersebut memakai total volume per SPBU dan satu matriks "
        "jarak untuk semua truk; produk, kompartemen, ritase berulang, dan larangan kelas jalan belum diperhitungkan. "
        "Rencana yang terlihat pendek di atas kertas dapat gagal dijalankan ketika volume tiap produk tidak muat pada "
        "susunan kompartemen, atau ketika rute melewati jalan yang tidak boleh dilalui truk besar.")
    W.p("Penelitian PSRP di Indonesia umumnya berhenti pada model agregat atau kasus kecil yang diselesaikan dengan "
        f"pemrograman bilangan bulat {cite('surjandari2011', 'ramadhani2021', 'febriandini2020')}. Literatur "
        "internasional bergerak ke arah metaheuristik hibrida yang operatornya dipilih secara adaptif dengan "
        f"_reinforcement learning_ (RL) {cite('qi2022', 'zhao2025', 'koc2026', 'lin2025')}, dan ke arah sistem pendukung "
        f"keputusan (DSS) berbasis peta {cite('santos2011', 'cavecchia2024')}. Belum ada perangkat terbuka yang "
        "menggabungkan kompartemen, multi-produk, multi-ritase, legalitas jalan per tipe truk, dan simulasi pergerakan "
        "untuk kasus distribusi BBM di Indonesia.")
    W.p("Laporan ini menyajikan model MC-MP-MT-VRP, algoritma Hybrid GA-SA-RL, dan aplikasi web SMARTROUTE-BBM beserta "
        "hasil pengujiannya. Semua angka hasil diambil dari berkas keluaran eksperimen di repositori; angka yang tampil "
        "di aplikasi diperiksa ulang terhadap skrip eksperimen dengan pengaturan yang sama. Hasil yang tidak mendukung "
        "hipotesis awal, misalnya kontribusi RL, dilaporkan apa adanya.")
    W.h("Rumusan Masalah")
    W.bullets([
        "Bagaimana merumuskan MC-MP-MT-VRP distribusi BBM yang memuat kendala kompartemen, multi-produk, multi-ritase, "
        "armada heterogen, legalitas jalan per tipe truk, dan batas waktu shift?",
        "Seberapa besar perbedaan jarak, biaya, emisi CO~2~, dan kelayakan rencana Hybrid GA-SA-RL dibanding _Saving "
        "Matrix_, _Nearest Neighbour_, dan optimum eksak MILP?",
        "Bagaimana kinerja rencana ketika kecepatan, waktu bongkar, dan permintaan bersifat acak, serta ketika terjadi "
        "kerusakan truk atau kemacetan mendadak?",
        "Bagaimana kinerja algoritma ketika jumlah SPBU bertambah hingga 100 dan pada instance benchmark CVRPLIB?",
        "Apakah aplikasi web yang dibangun memberi keluaran yang sama dengan skrip eksperimen dan dapat dipakai untuk "
        "simulasi skenario _what-if_?",
    ], numbered=True)
    W.h("Tujuan Penelitian")
    W.bullets([
        "Menyusun formulasi MC-MP-MT-VRP dan jaringan jalan legal-truk untuk distribusi FT Gelumbang.",
        "Mengimplementasikan Hybrid GA-SA-RL dan membandingkannya dengan heuristik klasik, MILP, dan varian ablasi.",
        "Menguji ketahanan rencana dengan simulasi Monte Carlo, simulasi mikro pergerakan truk, dan re-routing dinamis.",
        "Menguji skalabilitas pada instance sintetis 25, 50, dan 100 SPBU serta pada CVRPLIB set X.",
        "Membangun aplikasi web SMARTROUTE-BBM berkode terbuka dan memverifikasi keluarannya terhadap skrip eksperimen.",
    ], numbered=True)
    W.h("Batasan Masalah")
    W.bullets([
        "Kasus utama adalah satu FT dan 13 SPBU pada data Capstone Design 2026 dengan horizon satu hari dan satu shift "
        "06.00–18.00.",
        "Setiap SPBU dilayani oleh satu ritase (tanpa _split delivery_); satu truk menjalankan paling banyak tiga ritase.",
        "Proporsi produk per SPBU (Pertalite 62%, Biosolar 26%, Pertamax 12%), ukuran kompartemen, dimensi truk, "
        "konsumsi bahan bakar, dan biaya tetap adalah asumsi karena tidak tersedia pada data capstone.",
        "Jaringan jalan diambil dari OpenStreetMap pada satu titik waktu; kelas jalan diturunkan dari jenis ruas bila "
        "tidak ada tag yang lebih rinci.",
        "Komponen RL adalah pemilih operator _Q-learning_ tabular di dalam SA, bukan agen yang dilatih lintas instance.",
        "Aplikasi diuji fungsinya oleh tim peneliti; uji kegunaan oleh pengguna industri belum dilakukan.",
    ])
    W.h("Kontribusi Penelitian")
    W.p("Kontribusi penelitian ini dirumuskan sebagai berikut.", keep_next=True)
    W.bullets([
        "Formulasi MC-MP-MT-VRP yang menggabungkan kompartemen, multi-produk, multi-ritase, armada heterogen, dan "
        "legalitas jalan per tipe truk menurut UU 22/2009, dengan matriks jarak asimetris yang berbeda untuk setiap tipe.",
        "Dekoder _Split_ armada heterogen dengan pemeriksaan kompartemen eksak dan amortisasi biaya tetap truk, dipadukan "
        "dengan GA, SA, dan pemilih operator _Q-learning_, beserta uji ablasi yang memisahkan kontribusi setiap komponen.",
        "Validasi berlapis: optimum MILP, CVRPLIB, instance sintetis sampai 100 SPBU, Monte Carlo permintaan, dan simulasi "
        "mikro pergerakan truk pada geometri jalan nyata.",
        "Aplikasi web berkode terbuka yang keluarannya identik dengan skrip eksperimen, sehingga hasil dapat diperiksa dan "
        "diulang oleh pihak lain.",
    ], numbered=True)
    W.h("Manfaat Penelitian")
    W.bullets([
        "**Akademik:** model PSRP multi-kompartemen multi-ritase dengan studi kasus Indonesia, lengkap dengan kode, data, "
        "dan hasil uji yang dapat diulang.",
        "**Industri:** alat bantu untuk menyusun rute harian, memeriksa kelayakan muatan per kompartemen, dan menilai "
        "skenario gangguan sebelum terjadi.",
        "**Pendidikan:** perangkat praktik untuk mata kuliah logistik migas dan Capstone Design.",
        "**Lingkungan:** perhitungan emisi CO~2~ per rencana sehingga pilihan armada dapat dibandingkan dari sisi emisi.",
    ])


# ===========================================================================
def bab2(W, cite, R):
    W.bab(2, "TINJAUAN PUSTAKA")
    W.h("Dasar Teori")
    W.hh("VRP dan _Petrol Station Replenishment Problem_")
    W.p(f"VRP diperkenalkan Dantzig dan Ramser {cite('dantzig1959')} untuk menentukan rute armada dari depot ke "
        "sejumlah pelanggan dengan biaya minimum. Clarke dan Wright kemudian mengusulkan heuristik penghematan "
        f"(_savings_) yang hingga kini dipakai sebagai pembanding {cite('clarke1964')}. Pada PSRP, depot adalah FT, "
        "pelanggan adalah SPBU, dan muatan adalah beberapa jenis BBM. Cornillier dkk. merumuskan PSRP multi-periode, "
        f"versi eksak, dan versi dengan jendela waktu {cite('cornillier2008', 'cornillier2008b', 'cornillier2009')}. "
        f"Benantar dkk. menambahkan varian baru dengan kendala kompatibilitas {cite('benantar2016')}, sedangkan Wu dkk. "
        f"memasukkan risiko bahaya beruntun pada truk dan gandengan {cite('wu2024')}. Studi kasus berskala nyata "
        f"dengan banyak depot dan kendala pemuatan rumit dilaporkan oleh Che dkk., Bani dkk., dan Liu dkk. "
        f"{cite('che2023', 'bani2023', 'liu2025')}. Haseltalab dkk. menggabungkan rute dan persediaan produk minyak "
        f"dengan armada heterogen {cite('haseltalab2024')}.")
    W.hh("Kendala kompartemen dan multi-produk")
    W.p("Pada _multi-compartment_ VRP, kelayakan muatan tidak cukup diperiksa dengan total volume ≤ kapasitas. Setiap "
        "kompartemen hanya boleh berisi satu produk, sehingga yang diperiksa adalah ada tidaknya penugasan kompartemen "
        "ke produk yang menampung seluruh volume. Ostermeier dkk. dan Coelho serta Laporte menyusun klasifikasi dan "
        f"model umum persoalan ini {cite('ostermeier2021', 'coelho2015')}. Metaheuristik untuk varian armada homogen "
        f"dan heterogen dibahas Yahyaoui dkk. dan Efthymiadis dkk. {cite('yahyaoui2018', 'efthymiadis2023')}, "
        f"sedangkan pendekatan eksak untuk perusahaan distribusi BBM diberikan Baptista dkk. {cite('baptista2024')}. "
        f"Hajba dkk. memakai MILP yang dipadukan dengan pengelompokan untuk kasus PSRP khusus {cite('hajba2023')}.")
    W.hh("Multi-ritase dan armada heterogen")
    W.p("Truk tangki yang berangkat pagi biasanya kembali ke FT sebelum siang dan berangkat lagi. Cattaruzza dkk. "
        f"merangkum varian VRP dengan banyak ritase dan memberikan algoritma memetik untuknya {cite('cattaruzza2016', 'cattaruzza2014')}; "
        f"Azi dkk. memakai _adaptive large neighborhood search_ {cite('azi2014')}. Zhao dkk. memecah _giant tour_ "
        f"menjadi ritase dengan pemrograman dinamis pada kasus waktu tempuh bergantung jam {cite('zhaoj2024')}. Untuk "
        f"armada heterogen, Prins serta Subramanian dkk. menunjukkan efektivitas algoritma hibrida "
        f"{cite('prins2009', 'subramanian2012')}, dan Şahin dkk. memberikan metode eksak _branch-and-price_ untuk "
        f"armada heterogen multi-depot multi-ritase {cite('sahin2022')}. Pada distribusi BBM, Wang dkk. memodelkan "
        f"truk yang dapat kembali ke depot berkali-kali {cite('wang2019', 'wang2020')}.")
    W.hh("Algoritma Genetika dan dekoder _Split_")
    W.p(f"Algoritma Genetika (GA) {cite('holland1975')} mengembangkan populasi solusi melalui seleksi, pindah silang, dan "
        f"mutasi. Prins {cite('prins2004')} merepresentasikan solusi VRP sebagai permutasi pelanggan tanpa pemisah rute "
        "(_giant tour_) dan memotongnya menjadi rute secara optimal dengan prosedur _Split_, yaitu lintasan terpendek "
        "pada graf asiklik. Gagasan ini menjadi dasar _hybrid genetic search_ yang termasuk algoritma terbaik untuk "
        f"banyak varian VRP {cite('vidal2012', 'vidal2022')}. Ariyani dkk. memadukan GA dan SA untuk VRP multi-ritase "
        f"dengan jendela waktu {cite('ariyani2018')}.")
    W.hh("_Simulated Annealing_")
    W.p(f"_Simulated Annealing_ (SA) {cite('kirkpatrick1983')} menerima solusi tetangga yang lebih buruk dengan peluang "
        "yang menurun seiring turunnya temperatur. Dalam skema hibrida, SA bekerja sebagai pencarian lokal di sekitar "
        "solusi terbaik GA. Keberhasilannya bergantung pada skala energi: bila selisih energi terlalu kecil terhadap "
        "temperatur, SA berubah menjadi jalan acak; bila terlalu besar, SA menjadi _hill climbing_.")
    W.hh("_Reinforcement learning_ untuk pemilihan operator")
    W.p(f"_Q-learning_ {cite('watkins1992', 'sutton2018')} memperbarui nilai aksi Q(s, a) dari imbalan yang diterima "
        "setelah aksi a diambil pada keadaan s. Pada metaheuristik, cara ini dipakai sebagai pemilih operator adaptif "
        f"atau _hyper-heuristic_ {cite('burke2013', 'voigt2024')}. Contohnya antara lain QMOEA untuk VRP hijau "
        f"bergantung waktu {cite('qi2022')}, GA berbantuan RL untuk CVRP dengan jendela waktu {cite('koc2026')}, "
        f"_hyper-heuristic_ berbasis _Q-learning_ untuk kendaraan listrik {cite('lin2025')}, VNS berbasis RL "
        f"{cite('kalatzantonakis2022')}, dan RL untuk armada heterogen {cite('qin2021')}. Kajian lain memakai RL untuk "
        f"merancang metaheuristik secara otomatis {cite('yi2023', 'tian2023')} atau memadukan _Q-learning_ ke dalam "
        f"_iterated greedy_ {cite('mohammadi2022')}. Tinjauan terbaru mencatat bahwa klaim keunggulan RL perlu diuji "
        f"terhadap pemilihan acak dengan anggaran evaluasi yang sama {cite('jaouhari2026', 'zhao2025')}.")
    W.hh("Konsumsi bahan bakar dan emisi CO~2~")
    W.p(f"Logistik hijau memasukkan dampak lingkungan ke dalam keputusan rute {cite('dekker2012', 'bektas2011')}. "
        f"Konsumsi bahan bakar truk naik seiring muatan dan menyimpang dari kecepatan efisiennya {cite('xiao2012')}, "
        f"dan pilihan tipe truk pada armada heterogen ikut menentukan emisi {cite('kopfer2014')}. Emisi bergantung pula "
        f"pada jam keberangkatan di wilayah padat {cite('ehmke2016')}. Turkensteen {cite('turkensteen2017')} "
        "menunjukkan bahwa model konsumsi yang terlalu sederhana dapat menyesatkan peringkat rencana. Penelitian ini "
        f"memakai faktor emisi IPCC Tier 2 untuk solar, 2,68 kg CO~2~/L {cite('ipcc2006')}.")
    W.hh("Kelas jalan dan jaringan OpenStreetMap")
    W.p("UU 22/2009 Pasal 19 membagi jalan menjadi kelas I, II, III, dan khusus berdasarkan dimensi kendaraan dan "
        f"muatan sumbu terberat (MST) yang diizinkan {cite('uu22_2009')}; PP 79/2013 mengatur jaringan lalu lintas "
        f"yang menjadi acuannya {cite('pp79_2013')}. OpenStreetMap (OSM) menyediakan data ruas jalan beserta tag jenis "
        f"ruas, lebar, jumlah lajur, arah, dan rambu batas {cite('haklay2008')}. Jarak antar-titik pada graf jalan "
        f"dihitung dengan algoritma lintasan terpendek Dijkstra {cite('dijkstra1959')}. Şahin dkk. menunjukkan bahwa "
        f"larangan akses kendaraan mengubah struktur solusi VRP {cite('sahin2024')}, dan Ray membangun DSS rute "
        f"untuk kendaraan dengan dimensi dan berat berlebih {cite('ray2007')}.")
    W.hh("Ketidakpastian, antrean, dan gangguan dinamis")
    W.p("Waktu tempuh dan permintaan di lapangan tidak pasti. Taş dkk. memodelkan waktu tempuh stokastik dengan "
        f"jendela waktu lunak {cite('tas2012')}; Hu dkk., Munari dkk., dan Zhang dkk. menyusun versi robust "
        f"{cite('hu2018', 'munari2019', 'zhang2021')}; Xu dkk. menerapkan optimasi robust multi-objektif pada distribusi "
        f"BBM multi-depot {cite('xu2021')}. Abdullahi dkk. memakai _simheuristic_, yaitu metaheuristik "
        f"yang dievaluasi ulang dengan simulasi {cite('abdullahi2025')}. Antrean truk di _loading rack_ FT dapat "
        f"dimodelkan sebagai sistem M/M/c {cite('gross2008')}. Untuk gangguan selama operasi, Rios dkk. merangkum "
        f"VRP dinamis {cite('rios2021')}, dan Sze dkk. memakai VNS adaptif untuk re-optimasi {cite('sze2024')}.")
    W.hh("Sistem pendukung keputusan dan prioritas SPBU")
    W.p("DSS rute menggabungkan basis data, model optimasi, dan antarmuka peta. Santos dkk. membangun DSS spasial "
        f"berbasis web dengan Google Maps {cite('santos2011')}, Cavecchia dkk. membuat DSS untuk VRP multi-ritase "
        f"{cite('cavecchia2024')}, Andersson dkk. mengembangkan RuttOpt untuk truk kayu {cite('andersson2008')}, dan "
        f"Peng dkk. menyediakan perangkat visualisasi rute {cite('peng2020')}. Prioritas SPBU pada penelitian ini "
        f"dihitung dengan inferensi fuzzy Mamdani {cite('mamdani1975')} dari sisa waktu sebelum stok habis, jarak, "
        "dan fluktuasi permintaan.")
    W.h("Hasil Penelitian yang Relevan")
    W.p("Tabel 2.1 merangkum penelitian yang paling dekat dengan penelitian ini. Kolom terakhir menunjukkan aspek yang "
        "belum dicakup dan menjadi celah yang diisi.")
    rows = [
        (f"Cornillier dkk. (2009) {cite('cornillier2009')}", "PSRP jendela waktu", "Heuristik", "Tanpa emisi, tanpa DSS"),
        (f"Wang dkk. (2020) {cite('wang2020')}", "MCVRP _split_, multi-ritase", "Eksak dan heuristik", "Satu objektif"),
        (f"Che dkk. (2023) {cite('che2023')}", "PSRP multi-depot", "Tabu-ALNS", "Tanpa re-routing dinamis"),
        (f"Bani dkk. (2023) {cite('bani2023')}", "PSRP multi-periode nyata", "Matheuristik", "Tanpa legalitas jalan"),
        (f"Baptista dkk. (2024) {cite('baptista2024')}", "MCVRP BBM", "Eksak", "Skala terbatas"),
        (f"Wu dkk. (2024) {cite('wu2024')}", "PSRP truk-gandengan", "Eksak dan heuristik", "Tanpa simulasi pergerakan"),
        (f"Liu dkk. (2025) {cite('liu2025')}", "PSRP multi-kompartemen", "Hybrid VNS", "Tanpa RL, tanpa emisi"),
        (f"Qi dkk. (2022) {cite('qi2022')}", "VRP hijau bergantung waktu", "EA + _Q-learning_", "Bukan multi-kompartemen"),
        (f"Koç dkk. (2026) {cite('koc2026')}", "CVRPTW multi-objektif", "GA + RL", "Bukan distribusi BBM"),
        (f"Cavecchia dkk. (2024) {cite('cavecchia2024')}", "DSS VRP multi-ritase", "Optimasi + antarmuka", "Tanpa kompartemen"),
        (f"Surjandari dkk. (2011) {cite('surjandari2011')}", "PSRP multi-produk Indonesia", "Heuristik", "Tanpa multi-ritase"),
        (f"Ramadhani dkk. (2021) {cite('ramadhani2021')}", "BBM _split_, kompartemen", "MILP", "8 SPBU, tanpa DSS"),
        ("Penelitian ini", "MC-MP-MT-VRP, jalan legal-truk", "GA-SA-RL, MILP, simulasi",
         "Kompartemen, multi-ritase, kelas jalan, simulasi mikro, aplikasi terbuka"),
    ]
    W.table(["Peneliti", "Persoalan", "Metode", "Celah atau perbedaan"], rows, "Ringkasan penelitian yang relevan",
            widths=[3.8, 3.5, 3.0, 3.7], align=["l", "l", "l", "l"])
    W.p("Dari tabel tersebut, celah yang diisi penelitian ini ada pada gabungan kendala. Kompartemen, multi-produk, "
        "multi-ritase, dan armada heterogen dimodelkan bersama; jarak dihitung per tipe truk pada jalan yang legal; dan "
        "rencana diuji ulang dengan simulasi pergerakan truk, bukan hanya dengan nilai fungsi tujuan. Semua komponen "
        "itu tersedia dalam satu aplikasi berkode terbuka.")


# ===========================================================================
def bab3(W, cite, R):
    W.bab(3, "METODE PENELITIAN")
    W.h("Jenis Penelitian")
    W.p("Penelitian ini adalah penelitian terapan kuantitatif dengan pemodelan matematis, eksperimen komputasi, dan "
        "pengembangan perangkat lunak. Kinerja algoritma diuji dengan replikasi acak (_seed_ berbeda) dan uji statistik "
        f"nonparametrik {cite('derrac2011')}. Kode, data, dan keluaran eksperimen disimpan dalam repositori publik "
        f"(Lampiran 2) sehingga setiap angka di BAB 4 dapat dihasilkan ulang dengan satu perintah.")
    W.h("Bahan dan Alat")
    W.hh("Data")
    W.p("Data primer berasal dari berkas Capstone Design 2026: koordinat FT Gelumbang dan 13 SPBU, permintaan harian "
        "per SPBU, dan matriks jarak jalan 14×14 km. Tabel 3.1 memuat data SPBU. Parameter yang tidak tersedia pada data "
        "capstone ditetapkan sebagai asumsi dan diberi tanda pada Tabel 3.2 sampai Tabel 3.5.")
    sp = D("spbu")
    rows = [(r.id, r.nama, r.kabupaten, f(r.demand_kl, 2)) for r in sp.itertuples() if r.id != "FT"]
    rows.append(("", "**Jumlah**", "", f"**{f(sp.demand_kl.sum(), 2)}**"))
    W.table(["ID", "Nama SPBU", "Kabupaten/Kota", "Permintaan (KL/hari)"], rows,
            "Data SPBU wilayah FT Gelumbang (Capstone Design 2026)", widths=[1.3, 5.2, 4.3, 3.2], align=["c", "l", "l", "c"])
    ar = D("armada")
    rows = [(r.tipe, f(r.kapasitas_kl, 0), r.kompartemen_kl, int(r.jumlah_unit), f(r.fc0_l_per_km, 2),
             f(r.biaya_tetap_rp / 1000, 0), f(r.lebar_jalan_min_m, 1)) for r in ar.itertuples()]
    W.table(["Tipe", "Kapasitas (KL)", "Kompartemen (KL)", "Unit eksisting", "FC~0~ (L/km)", "Biaya tetap (ribu Rp/hari)",
             "Lebar jalan min. (m)"], rows, "Parameter armada truk tangki",
            widths=[1.2, 1.8, 2.4, 1.8, 1.9, 2.6, 2.3],
            note="Armada eksisting menurut data capstone: 4 unit tipe C dan 1 unit tipe B. Ukuran kompartemen, FC~0~, "
                 "biaya tetap, dan lebar jalan minimum adalah asumsi. Tipe A dan D dipakai pada skenario armada diperluas.")
    pr = D("produk")
    W.p("Data capstone hanya memuat total volume per SPBU. Untuk kasus multi-produk, volume dibagi menurut proporsi "
        "Pertalite " + f(pr.proporsi[0] * 100, 0) + "%, Biosolar " + f(pr.proporsi[1] * 100, 0) + "%, dan Pertamax "
        + f(pr.proporsi[2] * 100, 0) + "% untuk setiap SPBU. Proporsi ini adalah asumsi skenario dan perlu diganti "
        "data penjualan aktual per produk.")
    ak = D("aturan_kelas_jalan")
    rows = [(r.kelas, f(r.lebar_maks_m, 1) if r.lebar_maks_m < 50 else "> 2,5",
             f(r.panjang_maks_m, 1) if r.panjang_maks_m < 50 else "> 18", f(r.tinggi_maks_m, 1),
             f(r.mst_maks_ton, 0) if r.mst_maks_ton < 50 else "> 10") for r in ak.itertuples()]
    W.table(["Kelas jalan", "Lebar maks. (m)", "Panjang maks. (m)", "Tinggi maks. (m)", "MST maks. (ton)"], rows,
            "Batas dimensi kendaraan dan MST per kelas jalan " + cite('uu22_2009', 'pp79_2013'),
            widths=[2.8, 2.8, 2.8, 2.8, 2.8])
    rows = [(r.tipe, f(r.lebar_kendaraan_m, 1), f(r.panjang_kendaraan_m, 1), f(r.tinggi_kendaraan_m, 1), f(r.mst_ton, 0),
             f(r.gvw_ton, 0), f(r.v_maks_kmh, 0)) for r in ar.itertuples()]
    W.table(["Tipe", "Lebar (m)", "Panjang (m)", "Tinggi (m)", "MST (ton)", "JBB (ton)", "v maks. (km/jam)"], rows,
            "Dimensi, MST, jumlah berat yang diizinkan (JBB), dan kecepatan maksimum truk (asumsi spesifikasi tipikal)",
            widths=[1.4, 2.0, 2.0, 2.0, 2.0, 2.0, 2.6])
    oj = D("osm_jalan"); oj = oj[~oj.highway.str.endswith("_link")]
    rows = [(r.highway, r.boleh_truk, r.kelas_asumsi, f(r.lebar_lajur_m, 2), f(r.lebar_bawaan_m, 1),
             f(r.kecepatan_maks_kmh, 0)) for r in oj.itertuples()]
    W.table(["Jenis ruas OSM", "Lintasan truk", "Kelas (asumsi)", "Lebar lajur (m)", "Lebar bawaan (m)", "v jalan (km/jam)"],
            rows, "Pemetaan jenis ruas OSM ke kelas jalan, lebar, dan kecepatan ruas",
            widths=[2.9, 2.0, 2.1, 2.3, 2.4, 2.3],
            note="Ruas _link_ mengikuti induknya. Lebar bawaan dipakai bila OSM tidak memuat tag width atau lanes.")
    W.p(f"Data jaringan jalan diambil dari OSM {cite('haklay2008')} melalui Overpass API untuk kotak wilayah yang "
        "mencakup FT dan ke-13 SPBU dengan margin ±7,7 km. Data mentah beserta cap waktunya disimpan di "
        "data/osm/roads.json.gz. Pengunduhan dan perhitungan matriks dijalankan otomatis oleh GitHub Actions setiap "
        "kali aturan atau data berubah.")
    W.hh("Perangkat")
    W.p("Model dan algoritma ditulis dalam Python 3 (NumPy, SciPy, pandas). Model eksak diselesaikan dengan pemecah "
        f"MILP HiGHS {cite('huangfu2018')} melalui SciPy. Aplikasi web dibangun dengan Streamlit dan Plotly; peta "
        "rute dan simulasi tiga dimensi memakai MapLibre GL dan deck.gl. Basis data memakai Google Sheets (pustaka "
        "gspread) dengan cadangan berkas CSV lokal. Eksperimen dijalankan pada mesin Linux dengan 4 inti CPU.")
    W.h("Prosedur Penelitian")
    W.p("Gambar 3.1 menunjukkan delapan tahap penelitian, dari pengumpulan data sampai penyusunan laporan. Subbab "
        "berikut menjelaskan model, algoritma, simulasi, dan rancangan eksperimen.")
    W.figure(os.path.join(FIGL, "L02_prosedur.png"), "Diagram alir prosedur penelitian", 13.0)
    # ---- notasi
    W.hh("Notasi")
    rows = [
        ("N = {1,…,n}; 0", "Himpunan SPBU; simpul FT"),
        ("P; K", "Himpunan produk; himpunan tipe truk"),
        ("U~k~; Q~k~; κ~kc~", "Jumlah unit, kapasitas, dan volume kompartemen c tipe k"),
        ("q~ip~", "Permintaan SPBU i untuk produk p (KL)"),
        ("d~ij~^k^", "Jarak jalan legal dari i ke j untuk tipe k (km)"),
        ("R; r", "Himpunan ritase; satu ritase (0, i~1~, …, i~L~, 0)"),
        ("y~ir~; z~rk~; x~rcp~", "Biner: SPBU i pada ritase r; ritase r memakai tipe k; kompartemen c diisi produk p"),
        ("u~k~", "Jumlah unit tipe k yang dipakai"),
        ("L~ij~", "Muatan truk pada ruas (i, j) (KL)"),
        ("τ~r~^s^, τ~r~^e^; a~i~; [e~i~, b~i~]", "Waktu mulai dan selesai ritase; waktu tiba; jendela waktu SPBU i"),
        ("π~i~", "Skor prioritas fuzzy SPBU i (0–100)"),
        ("w~1~, w~2~, w~3~", "Bobot biaya, emisi, dan waktu"),
    ]
    W.table(["Simbol", "Arti"], rows, "Notasi model", widths=[4.4, 9.6], align=["l", "l"])
    # ---- formulasi
    W.hh("Formulasi MC-MP-MT-VRP")
    W.p("Fungsi tujuan adalah jumlah tertimbang tiga objektif yang dinormalisasi ditambah penalti pelanggaran kendala "
        "lunak, seperti pada persamaan (1).", keep_next=True)
    e_obj = W.eqn(r"\min F=\sum_{o=1}^{3} w_o\,\frac{Z_o}{Z_o^{\mathrm{ref}}}+\Phi")
    W.p("dengan (w~1~, w~2~, w~3~) = (0,5; 0,3; 0,2) sesuai proposal dan Z~o~^ref^ nilai objektif rencana _direct "
        "delivery_ (satu ritase untuk setiap SPBU) sebagai pembagi normalisasi. Objektif biaya Z~1~ (Rp/hari) adalah:",
        indent=False, keep_next=True)
    W.eqn(r"Z_1=c_f\sum_{r\in R}\sum_{(i,j)\in r}F_{ij}+c_d\sum_{r\in R}\sum_{(i,j)\in r}d_{ij}^{k(r)}+\sum_{k\in K}B_k\,u_k")
    W.p("dengan c~f~ = Rp12.000/L harga solar, c~d~ = Rp1.500/km biaya pemeliharaan, dan B~k~ biaya tetap harian tipe k. "
        f"Konsumsi bahan bakar setiap ruas F~ij~ (L) mengikuti model beban dan kecepatan {cite('xiao2012', 'bektas2011')}:",
        indent=False, keep_next=True)
    e_fuel = W.eqn(r"F_{ij}=FC_{0,k}\left(1+\beta\,\frac{L_{ij}}{Q_k}\right)\left(1+\alpha_1\left(v_{ij}-v_0\right)^2\right)d_{ij}^{k}")
    W.p("dengan β = 0,3, α~1~ = 10^−4^, v~0~ = 65 km/jam, dan v~ij~ kecepatan pada ruas tersebut. Ruas kembali ke FT "
        "dihitung dengan muatan nol. Objektif emisi Z~2~ (kg CO~2~) dan objektif waktu Z~3~ (menit) adalah:",
        indent=False, keep_next=True)
    W.eqn(r"Z_2=EF\sum_{r\in R}\sum_{(i,j)\in r}F_{ij},\qquad EF=2{,}68\ \mathrm{kg\,CO_2/L}")
    W.eqn(r"Z_3=\sum_{r\in R}\left(\tau_r^{e}-\tau_r^{s}\right)+\sum_{i\in N}\frac{\pi_i}{100}\max\left(0,a_i-b_i\right)")
    W.p("Kendala kunjungan (6) menjamin setiap SPBU dilayani tepat satu ritase. Kendala kompartemen (7)–(8) menjamin "
        "volume setiap produk tertampung oleh kompartemen yang ditugaskan kepadanya dan setiap kompartemen berisi paling "
        "banyak satu produk.", keep_next=True)
    W.eqn(r"\sum_{r\in R}y_{ir}=1\qquad\forall i\in N")
    W.eqn(r"\sum_{c\in C_k}\kappa_{kc}\,x_{rcp}\ \ge\ \sum_{i\in N}q_{ip}\,y_{ir}\qquad\forall r\in R,\ p\in P,\ k=k(r)")
    W.eqn(r"\sum_{p\in P}x_{rcp}\le 1\qquad\forall r\in R,\ c\in C_{k(r)}")
    W.p("Kelayakan (7)–(8) diperiksa secara eksak dengan pencarian rekursif ber-_memo_ atas semua penugasan kompartemen. "
        "Kendala akses (9) melarang tipe k melayani SPBU yang tidak terjangkau melalui jalan legal tipe tersebut, dengan "
        "A~ik~ = 1 bila SPBU i terhubung ke FT pada graf G~k~ (subbab 3.3.3).", keep_next=True)
    W.eqn(r"z_{rk}\,y_{ir}\le A_{ik}\qquad\forall i\in N,\ r\in R,\ k\in K")
    W.p("Kendala multi-ritase (10) mengatur urutan ritase m pada unit truk yang sama dan membatasi jumlahnya:",
        indent=False, keep_next=True)
    W.eqn(r"\tau_{m+1}^{s}\ge\tau_{m}^{e},\qquad m\le M=3,\qquad \tau^{e}_{M}\le T_{\mathrm{shift}}+\Delta^{\mathrm{OT}}")
    W.p("dengan τ~M~^e^ waktu selesai ritase terakhir unit tersebut, T~shift~ = 720 menit (06.00–18.00), dan Δ^OT^ lembur yang dikenai penalti. Waktu tempuh ruas (11) "
        "bergantung pada jam keberangkatan melalui faktor kemacetan CF(t), sedangkan waktu muat dan bongkar mengikuti "
        "(12)–(13).", keep_next=True)
    W.eqn(r"t_{ij}=\frac{60\,d_{ij}^{k}}{v_{\max}\,CF(t)}")
    W.eqn(r"s^{\mathrm{muat}}_r=W_q+5\sum_{i\in r}\sum_{p\in P}q_{ip}")
    W.eqn(r"s^{\mathrm{bongkar}}_i=15+2{,}5\sum_{p\in P}q_{ip}")
    W.p("dengan v~max~ = 40 km/jam, CF(t) ∈ [0,2; 1] per jam, dan W~q~ rerata waktu tunggu _loading rack_ dari model "
        f"Erlang-C {cite('gross2008')} (nol pada kondisi normal). Penalti Φ pada (1) adalah:",
        indent=False, keep_next=True)
    W.eqn(r"\Phi=0{,}02\,T^{\mathrm{late}}+0{,}02\,T^{\mathrm{OT}}+5\,N^{\mathrm{tt}}+1\,V^{\mathrm{kuota}}")
    W.p("dengan T^late^ menit keterlambatan tertimbang prioritas, T^OT^ menit lembur, N^tt^ jumlah ritase yang tidak "
        "mendapat truk atau tidak layak muat, dan V^kuota^ volume (KL) di atas kuota BPH Migas. Nilai 5 per ritase "
        "membuat satu ritase tak layak lebih mahal daripada seluruh biaya normal (F ≈ 0,5), sehingga solusi tak layak "
        "mudah dikenali dari nilai F > 1.")
    W.p(f"Untuk validasi, kasus khusus CVRP homogen (kapasitas 16 KL, satu ritase per truk, objektif jarak) dirumuskan "
        f"juga sebagai MILP dua indeks dengan eliminasi subtur Miller–Tucker–Zemlin berbasis muatan {cite('mtz1960')}:",
        keep_next=True)
    W.eqn(r"\ell_i-\ell_j+Q\,x_{ij}\le Q-q_j,\qquad q_i\le \ell_i\le Q\qquad\forall i\ne j\in N")
    W.p(f"dengan ℓ~i~ muatan kumulatif setelah SPBU i. Model ini diselesaikan sampai optimal dengan HiGHS {cite('huangfu2018')}.",
        indent=False)
    # ---- jalan legal
    W.hh("Jaringan jalan legal per tipe truk")
    W.p("Matriks capstone berlaku untuk semua truk dan tidak membedakan jalan yang boleh dilalui truk kecil dan truk "
        "besar. Untuk setiap tipe k dibentuk graf berarah G~k~ = (V, E~k~) yang hanya memuat ruas OSM yang memenuhi "
        "syarat (16):", keep_next=True)
    W.eqn(r"E_k=\left\{e\in E:\ h(e)\in H,\ \lambda(e)\succeq\lambda_k,\ b(e)\ge W_k,\ g(e)=1\right\}")
    W.p("dengan h(e) jenis ruas, H himpunan jenis ruas yang dapat menjadi lintasan truk (Tabel 3.5), λ(e) kelas ruas, "
        "λ~k~ kelas jalan minimum yang mengizinkan dimensi dan MST truk k (Tabel 3.3–3.4), b(e) lebar badan jalan, dan "
        "W~k~ lebar jalan minimum (Tabel 3.2) untuk jalan dua arah; pada ruas satu arah cukup lebar truk ditambah 1,0 m. "
        "Indikator g(e) bernilai 1 bila rambu ruas dipenuhi, yaitu tag maxwidth, maxlength, maxheight, maxweight terhadap "
        "JBB, maxaxleload terhadap MST, dan tidak ada larangan access/hgv. FT dan SPBU dihubungkan "
        "ke simpul terdekat pada komponen terhubung kuat terbesar G~k~ dalam radius 250 m. Jarak per tipe dihitung dengan "
        f"Dijkstra {cite('dijkstra1959')}:", keep_next=True)
    W.eqn(r"d_{ij}^{k}=\min_{\rho\in\Pi_k(i,j)}\sum_{e\in\rho}\ell_e")
    W.p("dengan Π~k~(i, j) himpunan lintasan dari i ke j pada G~k~ dan ℓ~e~ panjang ruas e. Indikator akses A~ik~ pada (9) "
        "bernilai 1 bila d~0i~^k^ dan d~i0~^k^ berhingga. Matriks yang dihasilkan bersifat asimetris akibat jalan satu arah dan berbeda antartipe truk. Geometri "
        "lintasannya dipakai untuk menggambar rute mengikuti jalan pada peta aplikasi.", indent=False)
    # ---- algoritma
    W.hh("Algoritma Hybrid GA-SA-RL")
    W.p("Gambar 3.2 memperlihatkan arsitektur aplikasi dan alur algoritma. Solusi direpresentasikan sebagai permutasi "
        f"SPBU (_giant tour_). Dekoder _Split_ {cite('prins2004')} yang diperluas untuk armada heterogen memotong "
        "permutasi π menjadi ritase dengan rekursi (18):", keep_next=True)
    W.eqn(r"V(j)=\min_{0\le i<j}\left\{V(i)+\min_{k\in K_{ij}}c_k\left(\pi_{i+1},\dots,\pi_j\right)\right\},\qquad V(0)=0")
    W.p("dengan K~ij~ himpunan tipe truk yang layak secara kompartemen, akses, dan kompatibilitas produk untuk "
        "potongan π~i+1~…π~j~, dan c~k~ biaya tertimbang ritase tersebut. Agar pemilihan tipe tidak mengabaikan biaya "
        "tetap, c~k~ ditambah biaya tetap yang diamortisasi atas jumlah ritase maksimum, w~1~B~k~/(3Z~1~^ref^). Potongan "
        "satu SPBU yang tidak layak untuk tipe mana pun tetap dibentuk dengan tipe terbesar yang memiliki akses, lalu "
        "dikenai penalti. Penjadwal kemudian menugaskan ritase ke unit truk, mendahulukan prioritas fuzzy tertinggi lalu "
        "durasi terpanjang, dan menghitung waktu dengan (11)–(13).", indent=False)
    W.figure(os.path.join(FIGL, "L01_arsitektur.png"), "Arsitektur SMARTROUTE-BBM dan alur Hybrid GA-SA-RL", 14.0)
    W.p("**Fase GA.** Populasi 100 individu; 60% dibangkitkan serakah dari tetangga terdekat dengan gangguan acak dan "
        "40% acak. Seleksi turnamen berukuran 5, _order crossover_ dengan p~c~ = 0,85, mutasi inversi/tukar/pindah dengan "
        "p~m~ = 0,10 yang dinaikkan tiga kali lipat bila keragaman populasi di bawah 5%, elitisme 2 individu, dan 200 "
        "generasi.")
    W.p("**Fase SA.** SA dimulai dari solusi terbaik GA dengan T~0~ = 1000, laju pendinginan α = 0,995, batas bawah "
        "temperatur 0,01, dan 5000 iterasi. Energi dinormalisasi terhadap fitness terbaik GA, dan solusi tetangga "
        "diterima dengan peluang Metropolis (19):", keep_next=True)
    W.eqn(r"E=10^{6}\,\frac{F}{F_{\mathrm{GA}}},\qquad P(\text{terima})=\begin{cases}1, & \Delta E\le 0\\ \exp\left(-\Delta E/T\right), & \Delta E>0\end{cases},\qquad T_{t+1}=\alpha\,T_t")
    W.p("Dengan skala ini, solusi yang 0,1% lebih buruk diterima dengan peluang e^−1^ ≈ 0,37 pada awal SA. Skala "
        "dikalibrasi pada instance X-n101-k25 dengan _seed_ 100–102 yang terpisah dari _seed_ eksperimen; pada skala "
        "10^5^ SA berubah menjadi jalan acak (results/calibration_sa.txt).", indent=False)
    W.p("**Komponen RL.** Pada setiap iterasi SA, agen _Q-learning_ memilih satu dari lima operator ketetanggaan: "
        "2-opt, relokasi, tukar, or-opt, dan tukar segmen. Keadaan s menggabungkan tingkat stagnasi (jumlah iterasi tanpa "
        "solusi terbaik baru: < 50, 50–199, ≥ 200) dan operator terakhir, sehingga terdapat 3 × 5 = 15 keadaan. Aksi "
        "dipilih secara ε-_greedy_ (20), nilai Q diperbarui dengan (21), dan imbalan mengikuti (22).", keep_next=True)
    W.eqn(r"a_t=\begin{cases}\arg\max_{a}Q(s_t,a), & \text{peluang } 1-\varepsilon_t\\ \text{acak}, & \text{peluang } \varepsilon_t\end{cases},\qquad \varepsilon_t=\max\left(0{,}02;\ 0{,}1\left(1-\frac{t}{T_{\mathrm{SA}}}\right)\right)")
    W.eqn(r"Q(s_t,a_t)\leftarrow Q(s_t,a_t)+\eta\left[r_t+\gamma\max_{a'}Q(s_{t+1},a')-Q(s_t,a_t)\right]")
    W.eqn(r"r_t=\begin{cases}-0{,}05, & \text{ditolak}\\ 10^{6}\left(F_{\mathrm{kini}}-F_{\mathrm{baru}}\right)/F_{\mathrm{GA}}, & \text{diterima, membaik}\\ 0, & \text{diterima, tidak membaik}\end{cases}\ +\ I_t")
    W.p("dengan I~t~ = 1 bila iterasi t menemukan solusi terbaik baru dan 0 bila tidak, η = 0,1, γ = 0,9, dan T~SA~ = 5000. Uji ablasi membandingkan tiga varian dengan anggaran evaluasi "
        "setara: GA saja (mendapat generasi tambahan sebanding dengan iterasi SA), GA-SA (operator dipilih acak seragam), "
        "dan GA-SA-RL.", indent=False)
    W.p(f"Skor prioritas π~i~ dihitung dengan inferensi fuzzy Mamdani {cite('mamdani1975')} dari tiga masukan: sisa "
        "waktu sampai stok habis (TTE), jarak dari FT, dan koefisien variasi permintaan. Keluaran ditegaskan dengan "
        "metode pusat massa (23).", keep_next=True)
    W.eqn(r"\pi_i=\frac{\int z\,\mu_{\mathrm{out}}(z)\,dz}{\int\mu_{\mathrm{out}}(z)\,dz},\qquad z\in[0,100]")
    # ---- dinamis
    W.hh("Re-routing dinamis")
    W.p("Ketika kejadian muncul pada waktu t~e~, SPBU yang sudah dilayani dikeluarkan dari persoalan. Pada kerusakan "
        "truk, muatan truk yang rusak dianggap tertahan dan unit lain baru tersedia setelah ritase berjalannya selesai. "
        "Pada kemacetan mendadak, CF = 0,3 selama 3 jam sejak t~e~. Dua kebijakan dibandingkan. Kebijakan naif "
        "mempertahankan rencana awal dan menggabungkan SPBU yang tertahan menjadi satu ritase tambahan. Kebijakan "
        "re-optimasi menjalankan ulang GA-SA-RL (populasi 40, 60 generasi, 1500 iterasi SA) untuk sisa SPBU dengan "
        f"solusi naif sebagai salah satu individu awal {cite('rios2021', 'sze2024')}.")
    # ---- simulasi mikro
    W.hh("Simulasi mikro pergerakan truk")
    W.p("Model optimasi memakai kecepatan rata-rata v~max~ untuk semua ruas. Untuk memeriksa apakah rencana tetap dapat "
        "dijalankan pada kondisi jalan yang lebih rinci, setiap ritase disimulasikan ruas demi ruas mengikuti geometri "
        f"jalan legal. Pendekatan ini serupa dengan _simheuristic_ {cite('abdullahi2025', 'tas2012')}. Kecepatan pada "
        "segmen jalan berjenis h adalah:", keep_next=True)
    W.eqn(r"v=\max\left\{5;\ \min\left(v_h,\ v_k^{\max}\right)CF(t)\left(1-\gamma\,\frac{L}{Q_k}\right)\varepsilon_h\right\},\qquad \varepsilon_h\sim\mathrm{LN}\left(-\tfrac{1}{2}\sigma^2,\ \sigma^2\right)")
    W.p("dengan v~h~ kecepatan ruas (Tabel 3.5), v~k~^max^ kecepatan maksimum truk (Tabel 3.4), γ = 0,15 penurunan "
        "kecepatan saat muatan penuh, dan ε~h~ pengali acak lognormal berekspektasi 1 yang diundi sekali untuk setiap "
        "rangkaian segmen sejenis; σ adalah koefisien variasi (CV) kecepatan. Waktu bongkar di SPBU i adalah:",
        indent=False, keep_next=True)
    W.eqn(r"s_i^{\mathrm{sim}}=\left(s_0+\frac{1000\sum_p q_{ip}}{\rho_k}\right)\xi_i,\qquad \xi_i\sim\mathrm{LN}\left(-\tfrac{1}{2}\sigma_u^2,\ \sigma_u^2\right)")
    W.p("dengan s~0~ = 15 menit, ρ~k~ laju bongkar truk (asumsi 350–500 L/menit menurut tipe) dan σ~u~ = 0,15. Keluaran simulasi adalah "
        "jam selesai setiap truk, lembur, keterlambatan terhadap jendela waktu, dan selisih waktu tiba terhadap rencana. "
        "Simulasi yang sama ditampilkan sebagai animasi dua dan tiga dimensi di aplikasi.", indent=False)
    # ---- desain eksperimen
    W.hh("Rancangan eksperimen")
    W.p("Tabel 3.7 merangkum sebelas eksperimen. Eksperimen E2 sampai E6, E9, dan E10 memakai jaringan jalan "
        "legal-truk OSM, sama dengan pengaturan bawaan aplikasi. E1 memakai matriks capstone agar dapat dibandingkan "
        "dengan rencana _Saving Matrix_ dan optimum MILP. E8, serta varian E3b pada sapuan bobot, memakai kedua "
        "jaringan untuk melihat pengaruh legalitas jalan secara langsung.")
    rows = [
        ("E0", "Audit data: sirkuitas jarak, ketidaksamaan segitiga, radius layanan", "–"),
        ("E1", "Validasi setting capstone (CVRP 16 KL): baseline, NN, CW, MILP, 3 varian", "30 replikasi"),
        ("E2", "Model lengkap, armada eksisting, kasus agregat dan multi-produk, 3 varian", "30 replikasi"),
        ("E3", "Sapuan bobot w langkah 0,1 → Pareto biaya–emisi; sensitivitas biaya tetap", "2 _seed_ × 66 bobot"),
        ("E4", "Sepuluh kategori skenario _what-if_ dan perbaikan armadanya", "5 _seed_"),
        ("E5", "Re-routing dinamis: kerusakan truk, kemacetan mendadak, tenggat ketat", "30 + 12 kasus"),
        ("E6", "Monte Carlo permintaan stokastik (CV 0,05–0,20) → _service level_", "1000 iterasi"),
        ("E7", f"CVRPLIB set X, n = 100–142 {cite('uchoa2017')}", "10 instance"),
        ("E8", "Jalan legal-truk OSM vs matriks capstone, armada eksisting dan diperluas", "30 replikasi"),
        ("E9", "Simulasi mikro: CV kecepatan 0,1–0,3, CV bongkar 0,15, dengan dan tanpa jendela waktu", "300 replikasi"),
        ("E10", "Skalabilitas: instance sintetis 25, 50, 100 SPBU pada jaringan OSM", "10 _seed_"),
    ]
    W.table(["Kode", "Eksperimen", "Ulangan"], rows, "Rancangan eksperimen", widths=[1.4, 9.6, 3.0],
            align=["c", "l", "c"])
    W.hh("Ukuran kinerja dan uji statistik")
    W.p(f"Pada CVRPLIB, kualitas solusi diukur dengan selisih relatif terhadap _best known solution_ (BKS) {cite('uchoa2017')}. "
        "Pada E6, ketahanan rencana diukur dengan _service level_ SL, yaitu bagian permintaan yang terpenuhi.",
        keep_next=True)
    W.eqn(r"\mathrm{gap}=\frac{z-z_{\mathrm{BKS}}}{z_{\mathrm{BKS}}}\times 100\%,\qquad \mathrm{SL}=1-\frac{\mathbb{E}\left[\sum_i\max\left(0,\tilde q_i-\hat q_i\right)\right]}{\mathbb{E}\left[\sum_i\tilde q_i\right]}")
    W.p("dengan q̃~i~ permintaan acak dan q̂~i~ volume yang dapat dibawa sesuai rencana. Data berpasangan (misalnya "
        "rerata per instance, atau dua kebijakan pada kejadian yang sama) diuji dengan peringkat bertanda Wilcoxon satu "
        "sisi. Replikasi dua algoritma yang saling bebas diuji dengan Mann–Whitney U satu sisi, dan perbandingan lebih "
        f"dari dua varian memakai Kruskal–Wallis atau Friedman {cite('derrac2011')} dengan α = 0,05. Besar efek pada E10 dinyatakan dengan Cliff's δ:",
        indent=False, keep_next=True)
    W.eqn(r"\delta=\frac{1}{n_a n_b}\sum_{i=1}^{n_a}\sum_{j=1}^{n_b}\mathrm{sgn}\left(b_j-a_i\right)")
    W.p("dengan a~i~ fitness GA-SA-RL dan b~j~ fitness GA. Nilai δ > 0 berarti GA-SA-RL cenderung lebih kecil (lebih "
        "baik); |δ| ≥ 0,474 tergolong efek besar.", indent=False)

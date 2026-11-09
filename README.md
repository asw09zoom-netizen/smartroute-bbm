# SMARTROUTE-BBM

**Web-based Decision Support System untuk Multi-Trip Multi-Compartment Multi-Product Vehicle Routing Problem (MC-MP-MT-VRP) pada distribusi BBM, dengan Hybrid Metaheuristic GA-SA-RL.**

Penelitian Terapan PEM Akamigas 2026 (SP3 No. 046/SP3/Penelitian/DIPA2026/PEM Akamigas).
Studi kasus: **FT Gelumbang** (Kab. Muara Enim, Sumatera Selatan), 13 SPBU, data Capstone Design 2026.

## Isi repositori

| Folder/berkas | Isi |
|---|---|
| `app.py` | Aplikasi web Streamlit (peta, optimasi, re-routing dinamis, hasil penelitian, laporan & log) |
| `smartroute/model.py` | Model MC-MP-MT-VRP: kelayakan kompartemen, decoder *Split* armada heterogen, penjadwalan multi-ritase, fungsi objektif Z1 biaya, Z2 emisi CO₂ (IPCC Tier 2), Z3 waktu, dan penalti |
| `smartroute/hybrid.py` | Hybrid GA-SA-RL (GA + Simulated Annealing + Q-Learning untuk pemilihan operator) beserta varian ablasi GA dan GA-SA |
| `smartroute/fuzzy.py` | Fuzzy Priority Scoring (Mamdani, defuzzifikasi centroid) |
| `smartroute/heuristics.py` | Pembanding: direct delivery, Nearest Neighbour, Clarke-Wright Savings |
| `smartroute/exact.py` | Model eksak MILP (HiGHS) untuk verifikasi optimum kasus kecil |
| `smartroute/scenarios.py` | 10 kategori skenario What-If |
| `smartroute/dynamic.py` | Re-routing dinamis (breakdown, kemacetan mendadak) |
| `smartroute/sheets.py` | Basis data Google Sheets (fallback CSV lokal) |
| `smartroute/telegram_bot.py` | Notifikasi laporan via Telegram (opsional) |
| `data/` | Data capstone (SPBU, matriks jarak jalan) + parameter asumsi (armada, proporsi produk) + instance CVRPLIB |
| `experiments/run_all.py` | Seluruh eksperimen penelitian (E0–E7) |
| `experiments/figures.py`, `figures_en.py` | Pembuat gambar laporan (ID) dan artikel (EN) |
| `experiments/calibrate_sa.py` | Kalibrasi skala energi SA (seed 100–102, terpisah dari seed uji) |
| `docs/build_laporan.py` | Generator Laporan Akhir (template UPPM) langsung dari `results/` |
| `docs/build_manuscript.py` | Generator naskah artikel jurnal (bahasa Inggris) dari `results/` |
| `results/`, `figures/` | Keluaran eksperimen |
| `tests/` | Unit test (`pytest`) |

## Menjalankan

```bash
pip install -r requirements.txt
streamlit run app.py              # aplikasi, buka http://localhost:8501
python -m pytest -q tests          # uji unit
python -m experiments.run_all E1   # eksperimen tertentu (E0..E7, E4b, E5b); tanpa argumen = semua
python -m experiments.figures      # gambar
python -m experiments.figures_en   # gambar artikel (EN)
python -m docs.build_laporan       # Laporan Akhir .docx -> docs/output/
python -m docs.build_manuscript    # naskah jurnal .docx -> docs/output/
```

## Deploy gratis (Streamlit Community Cloud)

1. Buka <https://share.streamlit.io> → *New app* → pilih repositori ini, branch `main`, file `app.py`.
2. *Advanced settings → Secrets*: tempel isi `.streamlit/secrets.toml.example` (minimal `[sheets] spreadsheet_id`).
3. Aplikasi membaca data dari Google Sheets "SMARTROUTE-BBM Database". Agar mode baca berfungsi tanpa kredensial, bagikan spreadsheet sebagai *Siapa saja yang memiliki link → Viewer*. Untuk menulis log simulasi ke tab `tb_simulasi_log`, tambahkan `[gcp_service_account]` dan bagikan spreadsheet ke email service account sebagai Editor.

Tanpa secrets, aplikasi otomatis memakai CSV di folder `data/`.

## Struktur Google Sheets

`tb_spbu` (id, kode, nama, kabupaten, lat, lon, demand_kl) · `tb_jarak` (matriks km) · `tb_armada` (tipe, kapasitas, kompartemen "6+4+3+3", jumlah unit, konsumsi BBM, biaya tetap, produk kompatibel, lebar jalan minimum) · `tb_produk` (proporsi produk) · `tb_simulasi_log` (audit trail setiap run).

## Catatan data dan asumsi

- **Data primer** (tidak diubah): koordinat dan permintaan 13 SPBU, serta matriks jarak jalan 14×14 dari berkas *Saving_Matrix_Fixx.xlsx* (Capstone Design 2026).
- **Asumsi model** (ditandai di `tb_armada`/`tb_produk`, dapat diubah): ukuran kompartemen per tipe truk, konsumsi BBM truk, biaya tetap harian, harga solar, proporsi produk per SPBU (data capstone hanya memuat total), kecepatan rata-rata 40 km/jam, waktu bongkar-muat.
- OSRM tidak dipakai pada versi ini; jarak memakai matriks jarak jalan capstone. Faktor sirkuitas terhadap jarak garis lurus dilaporkan pada `results/E0_audit.json`.

## Sitasi

Wardhana, A. S., Dewi, A. K., Hamdani, C. N., & Ardhiyanto, N. K. (2026). *SMARTROUTE-BBM: Web-based DSS for multi-trip multi-compartment fuel distribution with hybrid GA-SA-RL* (v1.0) [Perangkat lunak]. Politeknik Energi dan Mineral Akamigas.

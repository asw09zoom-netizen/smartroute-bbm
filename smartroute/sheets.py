"""Lapisan basis data Google Sheets dengan fallback CSV lokal.

Worksheet (tab) yang dipakai — nama mengikuti skema tabel proposal:
  tb_spbu, tb_jarak, tb_armada, tb_produk  : data masukan
  tb_simulasi_log                          : log hasil setiap run (audit trail)

Mode koneksi:
  1. read-write : st.secrets["gcp_service_account"] (JSON service account) +
                  st.secrets["sheets"]["spreadsheet_id"]  -> gspread
  2. read-only  : st.secrets["sheets"]["spreadsheet_id"] saja, spreadsheet dibagikan
                  "Siapa saja yang memiliki link dapat melihat" -> ekspor CSV publik
  3. lokal      : folder data/ (CSV) dan results/simulasi_log.csv
"""
from __future__ import annotations

import csv
import io
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Dict, List, Optional

from .data import DATA_DIR, load_tables

TABS = {"spbu": "tb_spbu", "jarak": "tb_jarak", "armada": "tb_armada", "produk": "tb_produk"}
LOG_TAB = "tb_simulasi_log"
LOG_COLS = ["timestamp", "skenario", "algoritma", "seed", "fitness", "jarak_km", "biaya_rp", "co2_kg",
            "waktu_menit", "jumlah_ritase", "jumlah_truk", "terlambat_menit", "lembur_menit",
            "tidak_terlayani", "waktu_komputasi_s", "rute"]


class SheetsDB:
    def __init__(self, spreadsheet_id: Optional[str] = None, service_account: Optional[Dict] = None):
        self.sid = spreadsheet_id
        self.sa = service_account
        self.mode = "lokal"
        self._gc = None
        self._sh = None
        if self.sid and self.sa:
            try:
                import gspread
                self._gc = gspread.service_account_from_dict(dict(self.sa))
                self._sh = self._gc.open_by_key(self.sid)
                self.mode = "read-write"
            except Exception as e:  # pragma: no cover
                self.error = str(e)
                self.mode = "read-only"
        elif self.sid:
            self.mode = "read-only"

    # -- baca -------------------------------------------------------------------
    def _read_rows(self, tab: str) -> List[List[str]]:
        if self.mode == "read-write":
            return self._sh.worksheet(tab).get_all_values()
        url = (f"https://docs.google.com/spreadsheets/d/{self.sid}/gviz/tq?tqx=out:csv&sheet="
               + urllib.parse.quote(tab))
        with urllib.request.urlopen(url, timeout=20) as r:
            txt = r.read().decode("utf-8")
        return list(csv.reader(io.StringIO(txt)))

    def load_tables(self) -> Dict:
        if self.mode == "lokal":
            return load_tables()
        out = {}
        for key, tab in TABS.items():
            rows = self._read_rows(tab)
            if key == "jarak":
                out[key] = rows
            else:
                hdr = rows[0]
                out[key] = [dict(zip(hdr, r)) for r in rows[1:] if any(c.strip() for c in r)]
        return out

    # -- tulis ------------------------------------------------------------------
    def log_run(self, rec: Dict) -> str:
        rec = dict(rec)
        rec.setdefault("timestamp", datetime.now().isoformat(timespec="seconds"))
        row = [str(rec.get(c, "")) for c in LOG_COLS]
        if self.mode == "read-write":
            try:
                ws = self._sh.worksheet(LOG_TAB)
            except Exception:
                ws = self._sh.add_worksheet(LOG_TAB, rows=1000, cols=len(LOG_COLS))
                ws.append_row(LOG_COLS)
            ws.append_row(row, value_input_option="USER_ENTERED")
            return "Google Sheets"
        path = os.path.join(os.path.dirname(DATA_DIR), "results", "simulasi_log.csv")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        new = not os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(LOG_COLS)
            w.writerow(row)
        return "CSV lokal"

    def push_seed_data(self) -> None:
        """Isi spreadsheet kosong dengan data awal dari folder data/ (mode read-write)."""
        if self.mode != "read-write":
            raise RuntimeError("Perlu service account untuk menulis ke Google Sheets")
        for key, tab in TABS.items():
            with open(os.path.join(DATA_DIR, "jarak_km.csv" if key == "jarak" else f"{key}.csv"),
                      encoding="utf-8") as f:
                rows = list(csv.reader(f))
            try:
                ws = self._sh.worksheet(tab)
                ws.clear()
            except Exception:
                ws = self._sh.add_worksheet(tab, rows=len(rows) + 10, cols=len(rows[0]) + 2)
            ws.update(rows, "A1")


def from_streamlit_secrets(st) -> SheetsDB:
    try:
        cfg = st.secrets.get("sheets", {})
        sid = cfg.get("spreadsheet_id") if cfg else None
        sa = st.secrets.get("gcp_service_account", None)
        return SheetsDB(sid, dict(sa) if sa else None)
    except Exception:
        return SheetsDB()

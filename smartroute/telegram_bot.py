"""Notifikasi laporan via Telegram Bot API (opsional).

Isi secrets:
  [telegram]
  bot_token = "123:ABC"
  chat_id   = "-100xxxx"
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request


def configured(st) -> bool:
    try:
        t = st.secrets.get("telegram", {})
        return bool(t and t.get("bot_token") and t.get("chat_id"))
    except Exception:
        return False


def send_text(token: str, chat_id: str, text: str):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:4000]}).encode()
    with urllib.request.urlopen(url, data=data, timeout=15) as r:
        return json.loads(r.read().decode())


def send(st, text: str):
    try:
        t = st.secrets["telegram"]
        out = send_text(t["bot_token"], t["chat_id"], text)
        return bool(out.get("ok")), "Terkirim ke Telegram" if out.get("ok") else str(out)
    except Exception as e:
        return False, f"Gagal: {e}"

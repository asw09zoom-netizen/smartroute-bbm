"""Unduh ruas jalan OpenStreetMap di sekitar FT Gelumbang + 13 SPBU (Overpass API).

Pemakaian:  python tools/fetch_osm.py            -> data/osm/roads.json.gz
Lalu      :  python -m smartroute.roadnet          -> matriks & geometri legal-truk
Data OSM (c) kontributor OpenStreetMap, lisensi ODbL.
"""
import csv
import gzip
import json
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "osm", "roads.json.gz")
MARGIN = 0.07  # derajat (~7.7 km) di sekeliling titik terluar
SERVERS = ["https://overpass-api.de/api/interpreter",
           "https://overpass.kumi.systems/api/interpreter",
           "https://overpass.private.coffee/api/interpreter"]
HW = ("motorway|motorway_link|trunk|trunk_link|primary|primary_link|secondary|secondary_link|"
      "tertiary|tertiary_link|unclassified|residential|road|living_street|service")


def bbox():
    with open(os.path.join(ROOT, "data", "spbu.csv"), newline="", encoding="utf-8") as f:
        r = list(csv.DictReader(f))
    la = [float(x["lat"]) for x in r]; lo = [float(x["lon"]) for x in r]
    return min(la) - MARGIN, min(lo) - MARGIN, max(la) + MARGIN, max(lo) + MARGIN


def main():
    s, w, n, e = bbox()
    q = f'[out:json][timeout:180];way["highway"~"^({HW})$"]({s:.4f},{w:.4f},{n:.4f},{e:.4f});(._;>;);out body;'
    data = urllib.parse.urlencode({"data": q}).encode()
    last = None
    for url in SERVERS:
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, data=data, headers={"User-Agent": "smartroute-bbm-research/1.0"})
                with urllib.request.urlopen(req, timeout=240) as resp:
                    js = json.loads(resp.read().decode("utf-8"))
                if not js.get("elements"):
                    raise RuntimeError("respons kosong")
                js["_meta"] = {"bbox": [s, w, n, e], "server": url, "query": q,
                               "osm_base": js.get("osm3s", {}).get("timestamp_osm_base"),
                               "license": "ODbL, (c) OpenStreetMap contributors"}
                os.makedirs(os.path.dirname(OUT), exist_ok=True)
                with gzip.open(OUT, "wt", encoding="utf-8") as f:
                    json.dump(js, f, separators=(",", ":"))
                ways = sum(1 for el in js["elements"] if el["type"] == "way")
                print(f"OK {url}: {ways} ruas, {len(js['elements'])} elemen -> {OUT}")
                return 0
            except Exception as ex:  # coba lagi / server lain
                last = ex
                print(f"gagal {url} (percobaan {attempt + 1}): {ex}", file=sys.stderr)
                time.sleep(5 * (attempt + 1))
    print("semua server gagal:", last, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())

import csv
import os
import sys
import json
import math
from pano import get_pano_meta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "BASE DE DADOS", "lista_postes.csv")
PROXIMITY_M = 8.0  # flag as ambiguous if another *real* pole (non-empty poste_numero) is within this distance


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def load_rows():
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        r = csv.DictReader(f, delimiter=";")
        return list(r)


def main():
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 25
    done_path = sys.argv[3] if len(sys.argv) > 3 else None

    rows = load_rows()
    # Ignore "ghost" duplicate inventory entries (empty poste_numero, not used) that sit
    # ~2m from almost every real pole -- these are data-modeling duplicates, not a second
    # physically distinguishable pole, so they should not trigger an ambiguity flag.
    all_pts = [(float(r["lat"]), float(r["lon"]), r["cod_id"]) for r in rows if r.get("poste_numero", "").strip()]

    done_ids = set()
    if done_path:
        try:
            with open(done_path, encoding="utf-8") as f:
                done_ids = set(json.load(f))
        except FileNotFoundError:
            pass

    utilizados = [r for r in rows if r["poste_utilizado"] == "True" and r["cod_id"] not in done_ids]

    ready = []
    flagged = []
    i = 0
    n_checked = 0
    while len(ready) < count and i < len(utilizados):
        r = utilizados[i]
        i += 1
        n_checked += 1
        lat, lon, cod_id = float(r["lat"]), float(r["lon"]), r["cod_id"]
        transformador = r["transformador"]

        neighbors = []
        for (lat2, lon2, cod2) in all_pts:
            if cod2 == cod_id:
                continue
            d = haversine_m(lat, lon, lat2, lon2)
            if d <= PROXIMITY_M:
                neighbors.append((cod2, round(d, 1)))

        meta = get_pano_meta(lat, lon)
        if meta is None:
            flagged.append({"cod_id": cod_id, "reason": "sem_cobertura_street_view", "lat": lat, "lon": lon})
            continue

        ready.append({
            "cod_id": cod_id, "lat": lat, "lon": lon, "transformador": transformador,
            "endereco": r.get("endereco_lote_mais_proximo", ""),
            "panoid": meta["panoid"],
            "nearby_real_poles": neighbors,  # informational: watch out for these when framing
        })

    result = {"ready": ready, "flagged": flagged, "checked": n_checked, "next_index_hint": i}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

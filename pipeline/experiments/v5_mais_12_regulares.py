"""Lote de teste (fase 1, v5): mais 12 postes REGULARES (nao-esquina), novos
(nao usados em nenhum lote anterior), processados com o pipeline atual
(rumo geometrico + forma integrada + classificacao v3). Tudo cai em fila de
revisao -- nada vai pra raiz de POSTES UTILIZADOS automaticamente.
"""
import csv
import json
import os
import time
import traceback

from pano import (
    get_pano_meta, fetch_panorama, remove_watermark_band,
    bearing_deg, auto_find_pole_yaw_constrained, refine_yaw_for_centering,
    equirect_to_perspective,
)
from routing import dest_dir_for, is_esquina

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAPDATA = "mapdata.json"
PITCH, FOV = 8, 80
OUT_W, OUT_H = 1000, 1333
WINDOW_DEG = 55
N_NEW = 12

ALREADY_TOUCHED = {
    # 13 esquina originais + 7 regulares originais/teste ja processados
    "1496652853", "350236509", "350236589", "350236609", "350236636",
    "350236640", "350236667", "350236704", "922742634",
    "350236610", "350236642", "350236705", "350236720",
    "350236645", "350236668",
    # 10 esquina do lote de teste
    "219298049", "219298157", "219298164", "219298165", "219298197",
    "219298202", "219298203", "219298247", "219298278", "219298283",
    # 10 regulares do lote de teste (inclui o sem cobertura)
    "350236584", "350236545", "350236699", "350236743", "350236666",
    "1358664738", "1684853981", "350236605", "350236687", "350236576",
    "350236533",
}


def classify(twin_edge, wire_count):
    if twin_edge and wire_count >= 2:
        return "ok", ""
    if twin_edge:
        return "poste_casa", "poucos fios no topo - possivel ramal residencial, confirmar"
    return "baixa_confianca", "sem par de bordas confiavel - possivel arvore, sinalizacao ou objeto nao identificado"


def load_candidates():
    D = json.load(open(MAPDATA, encoding="utf-8"))
    poles = {p[0]: p for p in D["poles"]}
    esquina_ids = set()
    with open(os.path.join(ROOT, "esquina_index.csv"), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            esquina_ids.add(row["cod_id"])
    regular_pending = [cid for cid in poles if cid not in esquina_ids and cid not in ALREADY_TOUCHED]
    return poles, regular_pending


def process_one(cod_id, addr, lat, lon, log):
    t0 = time.time()
    try:
        meta = get_pano_meta(lat, lon)
        if meta is None or meta.get("lat") is None:
            log.append(dict(cod_id=cod_id, endereco=addr, resultado="SEM_COBERTURA_OU_SEM_POSICAO"))
            return False

        hint_yaw = bearing_deg(meta["lat"], meta["lon"], lat, lon)
        pano_img = fetch_panorama(meta["panoid"], meta["levels"], meta["tile_size"], zoom=4)
        pano_img, wm_hits = remove_watermark_band(pano_img)

        coarse_yaw, _ = auto_find_pole_yaw_constrained(pano_img, hint_yaw, window_deg=WINDOW_DEG, fov_deg=70)
        final_yaw, centered_ok, offset_frac, twin_edge, wire_count = refine_yaw_for_centering(
            pano_img, coarse_yaw, pitch_deg=PITCH, fov_deg=FOV
        )
        confidence, note = classify(twin_edge, wire_count)

        crop = equirect_to_perspective(pano_img, yaw_deg=final_yaw, pitch_deg=PITCH,
                                        fov_deg=FOV, out_w=OUT_W, out_h=OUT_H)

        dest = dest_dir_for(cod_id, confidence=confidence)
        name = f"COD ID_{cod_id}" + (f" ({note})" if note else "") + ".jpg"
        crop.save(f"{dest}\\{name}", quality=92)

        pasta = "BAIXA_CONFIANCA" if confidence == "baixa_confianca" else (
            "POSTE_CASA" if confidence == "poste_casa" else ("ESQUINA" if is_esquina(cod_id) else "REVISAO_AUTOMATICA")
        )
        log.append(dict(
            cod_id=cod_id, endereco=addr, confianca=confidence, pasta=pasta,
            twin_edge=twin_edge, wire_count=wire_count,
            hint_bearing=round(hint_yaw, 1), yaw=round(final_yaw, 1),
            offset_centro_pct=round(offset_frac * 100, 1) if offset_frac is not None else "",
            watermark_hits=wm_hits, segundos=round(time.time() - t0, 1),
        ))
        return True
    except Exception as e:
        log.append(dict(cod_id=cod_id, endereco=addr, resultado=f"ERRO: {e}"))
        traceback.print_exc()
        return False


def main():
    poles, regular_pending = load_candidates()
    print(f"candidatos regulares novos disponiveis: {len(regular_pending)}")
    log = []
    n = 0
    for cod_id in regular_pending:
        if n >= N_NEW:
            break
        p = poles[cod_id]
        print(f"[{n+1}/{N_NEW}] {cod_id} ...", flush=True)
        if process_one(cod_id, p[3], p[4], p[5], log):
            n += 1

    out_csv = os.path.join(ROOT, "lote_teste_05_log.csv")
    fields = ["cod_id", "endereco", "confianca", "pasta", "twin_edge", "wire_count",
              "hint_bearing", "yaw", "offset_centro_pct", "watermark_hits", "segundos", "resultado"]
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(log)

    from collections import Counter
    print(f"\nconcluido: {dict(Counter(r.get('confianca','erro') for r in log))}")
    print("log salvo em", out_csv)


if __name__ == "__main__":
    main()

"""Lote de teste (fase 1): gera fotos automaticamente para uma amostra mista
de postes de esquina e regulares, exercitando o pipeline ponta a ponta:
cobertura -> pano -> remocao de marca d'agua -> escolha de angulo (com
refinamento de centralizacao) -> recorte final -> pasta correta.

Nenhum sufixo TRANSFORMADOR/CHAVE e aplicado automaticamente: o guia exige que
o sufixo reflita o que se ve na foto, nao o cadastro -- fica para o time
decidir na revisao.
"""
import csv
import json
import os
import sys
import time
import traceback

from pano import (
    get_pano_meta, fetch_panorama, remove_watermark_band,
    auto_find_pole_yaw, refine_yaw_for_centering, equirect_to_perspective,
)
from routing import dest_dir_for, is_esquina

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAPDATA = "mapdata.json"
INDEX_CSV = os.path.join(ROOT, "esquina_index.csv")
N_ESQUINA = 10
N_REGULAR = 10
PITCH, FOV = 8, 80
OUT_W, OUT_H = 1000, 1333

ALREADY_DONE = {
    "1496652853", "350236509", "350236589", "350236609", "350236636",
    "350236640", "350236667", "350236704", "922742634",  # esquina, ja prontos
    "350236610", "350236642", "350236705", "350236720",  # esquina, ex-PRECISA REVISAO
    "350236645", "350236668",  # regulares, ja prontos
}


def load_candidates():
    D = json.load(open(MAPDATA, encoding="utf-8"))
    poles = {p[0]: p for p in D["poles"]}  # cod_id -> [id,x,y,addr,lat,lon]

    esquina_pending = []
    with open(INDEX_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            if row["status"] == "pendente_geracao":
                esquina_pending.append(row["cod_id"])

    esquina_ids = set()
    with open(INDEX_CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            esquina_ids.add(row["cod_id"])

    regular_pending = [cid for cid in poles if cid not in esquina_ids and cid not in ALREADY_DONE]

    return poles, esquina_pending, regular_pending


def process_one(cod_id, addr, lat, lon, tipo, log):
    t0 = time.time()
    try:
        meta = get_pano_meta(lat, lon)
        if meta is None:
            log.append(dict(cod_id=cod_id, tipo=tipo, endereco=addr, resultado="SEM_COBERTURA_STREETVIEW"))
            return False

        pano_img = fetch_panorama(meta["panoid"], meta["levels"], meta["tile_size"], zoom=4)
        pano_img, wm_hits = remove_watermark_band(pano_img)

        coarse_yaw, _ = auto_find_pole_yaw(pano_img, coarse_step=15, fov_deg=70)
        final_yaw, centered_ok, offset_frac = refine_yaw_for_centering(
            pano_img, coarse_yaw, pitch_deg=PITCH, fov_deg=FOV
        )

        crop = equirect_to_perspective(pano_img, yaw_deg=final_yaw, pitch_deg=PITCH,
                                        fov_deg=FOV, out_w=OUT_W, out_h=OUT_H)

        dest = dest_dir_for(cod_id)
        out_path = f"{dest}\\COD ID_{cod_id}.jpg"
        crop.save(out_path, quality=92)

        log.append(dict(
            cod_id=cod_id, tipo=tipo, endereco=addr,
            resultado="OK" if centered_ok else "OK_VERIFICAR_CENTRALIZACAO",
            pasta="ESQUINA" if is_esquina(cod_id) else "POSTES UTILIZADOS",
            yaw=round(final_yaw, 1),
            offset_centro_pct=round(offset_frac * 100, 1) if offset_frac is not None else "",
            watermark_hits=wm_hits,
            segundos=round(time.time() - t0, 1),
        ))
        return True
    except Exception as e:
        log.append(dict(cod_id=cod_id, tipo=tipo, endereco=addr, resultado=f"ERRO: {e}"))
        traceback.print_exc()
        return False


def main():
    poles, esquina_pending, regular_pending = load_candidates()
    log = []

    n_esq = n_reg = 0
    print(f"candidatos esquina disponiveis: {len(esquina_pending)} | regulares disponiveis: {len(regular_pending)}")

    for cod_id in esquina_pending:
        if n_esq >= N_ESQUINA:
            break
        p = poles.get(cod_id)
        if not p:
            continue
        print(f"[esquina {n_esq+1}/{N_ESQUINA}] {cod_id} ...", flush=True)
        if process_one(cod_id, p[3], p[4], p[5], "esquina", log):
            n_esq += 1

    for cod_id in regular_pending:
        if n_reg >= N_REGULAR:
            break
        p = poles.get(cod_id)
        if not p:
            continue
        print(f"[regular {n_reg+1}/{N_REGULAR}] {cod_id} ...", flush=True)
        if process_one(cod_id, p[3], p[4], p[5], "regular", log):
            n_reg += 1

    out_csv = os.path.join(ROOT, "lote_teste_01_log.csv")
    fields = ["cod_id", "tipo", "endereco", "resultado", "pasta", "yaw", "offset_centro_pct", "watermark_hits", "segundos"]
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(log)

    ok = sum(1 for r in log if r["resultado"].startswith("OK"))
    warn = sum(1 for r in log if r["resultado"] == "OK_VERIFICAR_CENTRALIZACAO")
    fail = len(log) - ok
    print(f"\nconcluido: {ok}/{len(log)} ok ({warn} para conferir centralizacao), {fail-warn if fail>=warn else fail} falhas")
    print("log salvo em", out_csv)


if __name__ == "__main__":
    main()

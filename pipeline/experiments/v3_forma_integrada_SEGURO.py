"""Lote de teste (fase 1, v3): reprocessa os mesmos 20 postes, agora com o
sinal de forma (par de bordas paralelas + fios convergindo no topo) integrado
diretamente na escolha fina do angulo, e usado tambem para classificar a
confianca do resultado em 3 filas:

  ok              -> confiante que e um poste de rede real; roteia por
                     esquina/regular normalmente
  poste_casa      -> forma de poste confirmada (par de bordas) mas poucos
                     fios no topo -- indicio de ramal residencial unico, nao
                     rede de distribuicao. Fila de confirmacao (POSTE_CASA).
  baixa_confianca -- nenhum objeto com forma de poste confiavel encontrado
                     (arvore encobrindo, poste de sinalizacao/semaforo,
                     objeto nao identificado). Fila de revisao manual
                     (BAIXA_CONFIANCA).
"""
import csv
import glob
import json
import os
import time
import traceback

from pano import (
    get_pano_meta, fetch_panorama, remove_watermark_band,
    bearing_deg, auto_find_pole_yaw_constrained, refine_yaw_for_centering,
    equirect_to_perspective,
)
from routing import dest_dir_for, is_esquina, BASE_DIR, ESQUINA_DIR, POSTE_CASA_DIR, BAIXA_CONFIANCA_DIR


def cleanup_prior(cod_id):
    """Remove any file from a previous test-batch run for this cod_id, in any
    of the destination folders (classification can move it between runs)."""
    for d in (BASE_DIR, ESQUINA_DIR, POSTE_CASA_DIR, BAIXA_CONFIANCA_DIR):
        for f in glob.glob(os.path.join(d, f"COD ID_{cod_id}*.jpg")):
            os.remove(f)

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAPDATA = "mapdata.json"
PITCH, FOV = 8, 80
OUT_W, OUT_H = 1000, 1333
WINDOW_DEG = 55

PREV_LOG = os.path.join(ROOT, "lote_teste_01_log.csv")


def load_batch():
    D = json.load(open(MAPDATA, encoding="utf-8"))
    poles = {p[0]: p for p in D["poles"]}
    rows = list(csv.DictReader(open(PREV_LOG, encoding="utf-8-sig")))
    items = []
    for r in rows:
        cid = r["cod_id"]
        if cid in poles:
            items.append((cid, r["tipo"], poles[cid]))
    return items


def classify(twin_edge, wire_count):
    if twin_edge and wire_count >= 2:
        return "ok", ""
    if twin_edge:
        return "poste_casa", "poucos fios no topo - possivel ramal residencial, confirmar"
    return "baixa_confianca", "sem par de bordas confiavel - possivel arvore, sinalizacao ou objeto nao identificado"


def process_one(cod_id, addr, lat, lon, tipo, log):
    t0 = time.time()
    try:
        meta = get_pano_meta(lat, lon)
        if meta is None or meta.get("lat") is None:
            log.append(dict(cod_id=cod_id, tipo=tipo, endereco=addr, resultado="SEM_COBERTURA_OU_SEM_POSICAO"))
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

        cleanup_prior(cod_id)
        dest = dest_dir_for(cod_id, confidence=confidence)
        name = f"COD ID_{cod_id}"
        if note:
            name += f" ({note})"
        out_path = f"{dest}\\{name}.jpg"
        crop.save(out_path, quality=92)

        pasta = "BAIXA_CONFIANCA" if confidence == "baixa_confianca" else (
            "POSTE_CASA" if confidence == "poste_casa" else ("ESQUINA" if is_esquina(cod_id) else "POSTES UTILIZADOS")
        )
        log.append(dict(
            cod_id=cod_id, tipo=tipo, endereco=addr,
            confianca=confidence,
            resultado="OK" if centered_ok else "OK_VERIFICAR_CENTRALIZACAO",
            pasta=pasta,
            twin_edge=twin_edge, wire_count=wire_count,
            hint_bearing=round(hint_yaw, 1), yaw=round(final_yaw, 1),
            offset_centro_pct=round(offset_frac * 100, 1) if offset_frac is not None else "",
            watermark_hits=wm_hits, segundos=round(time.time() - t0, 1),
        ))
        return True
    except Exception as e:
        log.append(dict(cod_id=cod_id, tipo=tipo, endereco=addr, resultado=f"ERRO: {e}"))
        traceback.print_exc()
        return False


def main():
    items = load_batch()
    print(f"reprocessando {len(items)} postes com sinal de forma (bordas+fios) integrado a busca")
    log = []
    for i, (cod_id, tipo, p) in enumerate(items, 1):
        print(f"[{i}/{len(items)}] {cod_id} ({tipo}) ...", flush=True)
        process_one(cod_id, p[3], p[4], p[5], tipo, log)

    out_csv = os.path.join(ROOT, "lote_teste_03_log.csv")
    fields = ["cod_id", "tipo", "endereco", "confianca", "resultado", "pasta", "twin_edge", "wire_count",
               "hint_bearing", "yaw", "offset_centro_pct", "watermark_hits", "segundos"]
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(log)

    from collections import Counter
    c = Counter(r.get("confianca", "erro") for r in log)
    print(f"\nconcluido: {dict(c)}")
    print("log salvo em", out_csv)


if __name__ == "__main__":
    main()

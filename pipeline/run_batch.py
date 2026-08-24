"""Script de lote CANONICO do pipeline (pos fase-1, criterio "v3" -- o mais
seguro dos testados). Uso:

    python run_batch.py --esquina 20          # 20 postes de esquina novos
    python run_batch.py --regular 20          # 20 postes regulares novos
    python run_batch.py --esquina 10 --regular 10   # os dois

O que faz, por poste: checa cobertura de Street View -> baixa o panorama ->
remove a marca d'agua -> aponta o angulo pelo rumo geometrico camera->poste
(+-55) -> refina a centralizacao fio a fio (1 grau), avaliando forma (par de
bordas + fios convergindo no topo) em cada candidato -> classifica confianca
-> salva na fila de revisao certa (nunca na raiz de POSTES UTILIZADOS -- veja
routing.py e o README.md do projeto para o porque).

"Ja processado" e checado varrendo a pasta real (routing.all_processed_ids),
nao uma lista fixa no codigo -- entao rodar de novo sempre pega postes novos.
"""
import argparse
import csv
import json
import os
import time
import traceback

from pano import (
    get_pano_meta, fetch_panorama, remove_watermark_band,
    bearing_deg, yaw_from_bearing, auto_find_pole_yaw_constrained, refine_yaw_for_centering,
    equirect_to_perspective,
)
from routing import dest_dir_for, is_esquina, all_processed_ids

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(HERE)
MAPDATA = os.path.join(HERE, "mapdata.json")
ESQUINA_INDEX = os.path.join(PROJECT_ROOT, "BASE DE DADOS", "esquina_index.csv")
LOG_DIR = os.path.join(PROJECT_ROOT, "RELATORIOS")

PITCH, FOV = 8, 80
OUT_W, OUT_H = 1000, 1333
WINDOW_DEG = 55


def classify(twin_edge, wire_count):
    """Criterio travado apos o teste v4 (contagem de fios sozinha deixa
    passar semaforo/antena como 'ok'). Ver README.md - secao 'Historico'."""
    if twin_edge and wire_count >= 2:
        return "ok", ""
    if twin_edge:
        return "poste_casa", "poucos fios no topo - possivel ramal residencial, confirmar"
    return "baixa_confianca", "sem par de bordas confiavel - possivel arvore, sinalizacao ou objeto nao identificado"


def load_pole_index():
    if not os.path.exists(MAPDATA):
        raise SystemExit(f"mapdata.json nao encontrado em {MAPDATA}. Rode export_map.py primeiro.")
    D = json.load(open(MAPDATA, encoding="utf-8"))
    return {p[0]: p for p in D["poles"]}  # cod_id -> [id, x, y, endereco, lat, lon]


def load_esquina_pending():
    ids = []
    with open(ESQUINA_INDEX, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            if row["status"] == "pendente_geracao":
                ids.append(row["cod_id"])
    return ids


def load_esquina_all():
    ids = set()
    with open(ESQUINA_INDEX, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            ids.add(row["cod_id"])
    return ids


def process_one(cod_id, addr, lat, lon, tipo, log):
    t0 = time.time()
    try:
        meta = get_pano_meta(lat, lon)
        if meta is None or meta.get("lat") is None:
            log.append(dict(cod_id=cod_id, tipo=tipo, endereco=addr, resultado="SEM_COBERTURA_OU_SEM_POSICAO"))
            return False

        # bearing_deg() gives a true-north compass bearing; yaw_from_bearing()
        # converts it into the panorama's own (non-north-aligned) pixel frame --
        # see pano.yaw_from_bearing docstring, bug found+fixed 22/ago.
        raw_bearing = bearing_deg(meta["lat"], meta["lon"], lat, lon)
        hint_yaw = yaw_from_bearing(raw_bearing, meta.get("heading"))
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
        crop.save(os.path.join(dest, name), quality=92)

        pasta = os.path.basename(dest)  # dest_dir_for() sempre devolve uma fila "... - REVISAO"
        log.append(dict(
            cod_id=cod_id, tipo=tipo, endereco=addr, confianca=confidence,
            resultado="OK" if centered_ok else "OK_VERIFICAR_CENTRALIZACAO",
            pasta=pasta, twin_edge=twin_edge, wire_count=wire_count,
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
    ap = argparse.ArgumentParser()
    ap.add_argument("--esquina", type=int, default=0, help="quantos postes de esquina novos processar")
    ap.add_argument("--regular", type=int, default=0, help="quantos postes regulares novos processar")
    args = ap.parse_args()
    if not args.esquina and not args.regular:
        raise SystemExit("use --esquina N e/ou --regular N")

    poles = load_pole_index()
    done = all_processed_ids()
    log = []

    if args.esquina:
        pending = [c for c in load_esquina_pending() if c not in done]
        print(f"esquina: {len(pending)} candidatos pendentes disponiveis")
        n = 0
        for cod_id in pending:
            if n >= args.esquina:
                break
            p = poles.get(cod_id)
            if not p:
                continue
            print(f"[esquina {n+1}/{args.esquina}] {cod_id} ...", flush=True)
            if process_one(cod_id, p[3], p[4], p[5], "esquina", log):
                n += 1

    if args.regular:
        esquina_ids = load_esquina_all()
        pending = [c for c in poles if c not in esquina_ids and c not in done]
        print(f"regular: {len(pending)} candidatos pendentes disponiveis")
        n = 0
        for cod_id in pending:
            if n >= args.regular:
                break
            p = poles[cod_id]
            print(f"[regular {n+1}/{args.regular}] {cod_id} ...", flush=True)
            if process_one(cod_id, p[3], p[4], p[5], "regular", log):
                n += 1

    ts = time.strftime("%Y%m%d_%H%M%S")
    os.makedirs(LOG_DIR, exist_ok=True)
    out_csv = os.path.join(LOG_DIR, f"lote_log_{ts}.csv")
    fields = ["cod_id", "tipo", "endereco", "confianca", "resultado", "pasta", "twin_edge", "wire_count",
              "hint_bearing", "yaw", "offset_centro_pct", "watermark_hits", "segundos"]
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(log)

    from collections import Counter
    print(f"\nconcluido: {dict(Counter(r.get('confianca', 'erro') for r in log))}")
    print("log salvo em", out_csv)
    print("LEMBRETE: tudo caiu numa fila '... - REVISAO'. Nada foi pra uma pasta '... - OK' direto.")


if __name__ == "__main__":
    main()

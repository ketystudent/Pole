# -*- coding: utf-8 -*-
"""Script de TESTE avulso: gera imagens a partir de links do Street View e
salva na pasta TESTE/ na raiz do projeto -- nao mexe em nenhuma planilha
(links_pendentes.xlsx, relatorios, etc) nem em POSTES UTILIZADOS. Serve so
pra conferir visualmente o resultado do recorte/remocao de marca d'agua
antes de rodar o pipeline de verdade.

Uso: python teste_gerar_imagens.py "<url1>" "<url2>" ...
"""
import os
import sys
import math

import numpy as np
import cv2
from PIL import Image
from playwright.sync_api import sync_playwright

from link_cleanup import remove_watermark_v3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DIR = os.path.join(ROOT, "TESTE")

VIEWPORT = {"width": 2547, "height": 1532}
TOP_MARGIN, BOTTOM_MARGIN = 175, 145
LEFT_UI_EXCLUDE = 350
RIGHT_UI_EXCLUDE = 2547 - 120
OUT_W, OUT_H = 1000, 1333


def find_pole_x(arr):
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edges[:, :LEFT_UI_EXCLUDE] = 0
    edges[:, RIGHT_UI_EXCLUDE:] = 0
    h, w = edges.shape
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80, minLineLength=int(h * 0.25), maxLineGap=15)
    if lines is None:
        return None
    cx = (LEFT_UI_EXCLUDE + RIGHT_UI_EXCLUDE) / 2
    best_score, best_mid = 0.0, None
    for (x1, y1, x2, y2) in lines[:, 0, :]:
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length < 1:
            continue
        angle = abs(math.degrees(math.atan2(dx, dy)))
        if angle > 6:
            continue
        mid_x = (x1 + x2) / 2
        centrality = max(0.0, 1 - abs(mid_x - cx) / (w * 0.4))
        lowness = max(0.0, 1 - (min(y1, y2) / (h * 0.75)))
        score = length * (0.3 + 0.7 * centrality) * (0.4 + 0.6 * lowness)
        if score > best_score:
            best_score, best_mid = score, mid_x
    return best_mid


def main():
    urls = sys.argv[1:]
    if not urls:
        print("uso: python teste_gerar_imagens.py <url1> <url2> ...")
        return

    os.makedirs(TEST_DIR, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, channel="chrome",
                                     args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(viewport=VIEWPORT, locale="pt-BR", device_scale_factor=1)
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        for i, url in enumerate(urls, 1):
            raw_path = os.path.join(TEST_DIR, "raw_teste_%d.png" % i)
            try:
                page.goto(url, wait_until="load", timeout=45000)
                page.wait_for_timeout(6000)
                page.screenshot(path=raw_path)
                img = Image.open(raw_path).convert("RGB")
                arr = np.asarray(img)
                h, w = arr.shape[:2]

                pole_x = find_pole_x(arr)
                if pole_x is None:
                    pole_x = (LEFT_UI_EXCLUDE + RIGHT_UI_EXCLUDE) / 2

                usable_h = h - TOP_MARGIN - BOTTOM_MARGIN
                crop_w = int(usable_h * (OUT_W / OUT_H))
                x0 = int(max(0, min(w - crop_w, pole_x - crop_w / 2)))
                x1 = x0 + crop_w
                crop = arr[TOP_MARGIN:h - BOTTOM_MARGIN, x0:x1]
                crop_img = Image.fromarray(crop).resize((OUT_W, OUT_H), Image.LANCZOS)
                clean, wm_hits, _ = remove_watermark_v3(np.asarray(crop_img))

                out_path = os.path.join(TEST_DIR, "teste_%d.jpg" % i)
                Image.fromarray(clean).save(out_path, quality=92)
                print(i, "OK ->", out_path)
            except Exception as e:
                print(i, "ERRO", e)
            finally:
                if os.path.exists(raw_path):
                    os.remove(raw_path)

        browser.close()

    print("\nDONE. Imagens em:", TEST_DIR)


if __name__ == "__main__":
    main()

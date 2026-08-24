import re
import json
import math
import time
import unicodedata
import requests
import numpy as np
import cv2
from io import BytesIO
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

_STREET_PREFIX_RE = re.compile(
    r"^(RUA|AVENIDA|AV|R|PRACA|ALAMEDA|TRAVESSA|ESTRADA|RODOVIA|VIA|LARGO|BECO|ACESSO)\b\.?\s*"
)


def normalize_street_name(text):
    """Mesma normalizacao usada em pipeline/export_map.py pro criterio de
    esquina (base()): remove numero de casa, acento, tipo de logradouro
    (RUA/AV/...) e pontuacao, deixa so o nome nu em maiusculo -- pra
    comparar 'R. Pedro Dias de Carvalho' com 'RUA PEDRO DIAS DE CARVALHO
    381, 381, SANTA TEREZINHA' e reconhecer que e a mesma rua."""
    if not text:
        return ""
    s = text.split(",")[0]
    s = re.sub(r"^\s*\d+\s+", "", s)  # numero de casa na frente (endereco do Google)
    s = re.sub(r"\s+\d+\s*$", "", s)  # numero de casa no fim (endereco da base)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = _STREET_PREFIX_RE.sub("", s)
    return re.sub(r"\s+", " ", s).strip()

HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
    "referer": "https://www.google.com/",
}

META_URL = "https://www.google.com/maps/photometa/si/v1"


def _get_with_retry(url, params=None, retries=4, timeout=20):
    last_exc = None
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as e:
            last_exc = e
            time.sleep(0.6 * (attempt + 1))
    raise last_exc


def get_pano_meta(lat, lon):
    pb = (
        f"!1m4!1smaps_sv.tactile!11m2!2m1!1b1!2m4!1m2!3d{lat}!4d{lon}!2d50"
        "!3m17!1m2!1m1!1e2!2m2!1sen!2s!9m1!1e2!11m8!1m3!1e2!2b1!3e2!1m3!1e3!2b1!3e2"
        "!4m61!1e1!1e2!1e3!1e4!1e5!1e6!1e8!1e12!1e17!2m1!1e1!4m1!1i48!5m1!1e1!5m1!1e2"
        "!6m1!1e1!6m1!1e2!9m36!1m3!1e2!2b1!3e2!1m3!1e2!2b0!3e3!1m3!1e3!2b1!3e2!1m3!1e3!2b0!3e3"
        "!1m3!1e8!2b0!3e3!1m3!1e1!2b0!3e3!1m3!1e4!2b0!3e3!1m3!1e10!2b1!3e2!1m3!1e10!2b0!3e3!11m2!3m1!4b1"
    )
    r = _get_with_retry(META_URL, params={"authuser": "0", "hl": "en", "pb": pb})
    text = r.content.decode("utf-8")  # r.text sozinho as vezes adivinha a
    # codificacao errada e destroi acento (visto 23/ago com nomes de rua)
    if text.startswith(")]}'"):
        text = text[4:]
    data = json.loads(text)

    pano_block = data[1]
    if not pano_block or len(pano_block) < 2 or pano_block[1] is None:
        return None  # no imagery here

    panoid = pano_block[1][1]
    levels_raw = pano_block[2][3][0]  # list of [ [w,h] ] per zoom level
    levels = [lvl[0] for lvl in levels_raw]  # [[w,h], [w,h], ...]
    tile_w, tile_h = pano_block[2][3][1]

    heading = pitch = roll = None
    try:
        cam = pano_block[5][0][1][2]
        heading, pitch, roll = cam[0], cam[1], cam[2]
    except Exception:
        pass

    lat_actual = lon_actual = None
    try:
        lat_actual = pano_block[5][0][1][0][2]
        lon_actual = pano_block[5][0][1][0][3]
    except Exception:
        pass

    # endereco que o proprio Google mostra no cartao de info do Street View
    # pra essa coordenada (achado 23/ago) -- mesma resposta, sem custo extra
    # de request nem OCR. Usado pra cross-check de nome de rua contra o
    # cod_id escolhido pelo match de distancia/rumo (ver README).
    address = None
    try:
        address = pano_block[3][2][0][0]
    except Exception:
        pass

    return {
        "panoid": panoid,
        "levels": levels,  # index = zoom, value = [width, height] pixels
        "tile_size": (tile_w, tile_h),
        "heading": heading,
        "pitch": pitch,
        "roll": roll,
        "lat": lat_actual,
        "lon": lon_actual,
        "address": address,
    }


def fetch_tile(panoid, zoom, x, y):
    url = "https://streetviewpixels-pa.googleapis.com/v1/tile"
    params = {"cb_client": "maps_sv.tactile", "panoid": panoid, "x": x, "y": y, "zoom": zoom, "nbt": 1, "fover": 2}
    r = _get_with_retry(url, params=params)
    return Image.open(BytesIO(r.content)).convert("RGB")


def fetch_panorama(panoid, levels, tile_size, zoom, max_workers=8):
    height, width = levels[zoom]
    tw, th = tile_size
    cols = -(-width // tw)
    rows = -(-height // th)

    canvas = Image.new("RGB", (cols * tw, rows * th))

    def get(coord):
        x, y = coord
        try:
            return (x, y, fetch_tile(panoid, zoom, x, y))
        except Exception as e:
            return (x, y, None)

    coords = [(x, y) for y in range(rows) for x in range(cols)]
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for x, y, tile in ex.map(get, coords):
            if tile is not None:
                canvas.paste(tile, (x * tw, y * th))

    canvas = canvas.crop((0, 0, width, height))
    return canvas


WATERMARK_BAND_FRAC = (0.10, 0.36)  # empirically observed elevation band where Google tiles its repeating
# copyright watermark ("(c) YYYY Google") across the full 360 sphere.


def remove_watermark_band(equirect_img, band_frac=WATERMARK_BAND_FRAC):
    """Detect and inpaint just the small watermark stamps within the known
    elevation band, leaving real scene content (clouds, wires, rooftops) intact."""
    arr = np.asarray(equirect_img)
    h, w = arr.shape[:2]
    y0 = int(h * band_frac[0])
    y1 = int(h * band_frac[1])

    band = arr[y0:y1, :, :]
    gray = cv2.cvtColor(band, cv2.COLOR_RGB2GRAY).astype(np.float32)
    blurred = cv2.GaussianBlur(gray, (0, 0), sigmaX=6)
    diff = gray - blurred

    scale = w / 8192.0
    mask = ((diff > 2.5) & (diff < 25)).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (max(1, int(35 * scale)), max(1, int(5 * scale)))))

    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    final_mask = np.zeros_like(mask)
    min_w, max_w = 30 * scale, 200 * scale
    min_h, max_h = 6 * scale, 40 * scale
    for i in range(1, n):
        x, y, cw, ch, area = stats[i]
        if min_w < cw < max_w and min_h < ch < max_h and cw > ch * 1.8:
            final_mask[labels == i] = 255

    final_mask = cv2.dilate(final_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (max(1, int(9 * scale)), max(1, int(9 * scale)))))

    band_bgr = cv2.cvtColor(band, cv2.COLOR_RGB2BGR)
    inpainted = cv2.inpaint(band_bgr, final_mask, 4, cv2.INPAINT_TELEA)
    inpainted_rgb = cv2.cvtColor(inpainted, cv2.COLOR_BGR2RGB)

    out = arr.copy()
    out[y0:y1, :, :] = inpainted_rgb
    n_hits = int((final_mask > 0).sum())
    return Image.fromarray(out), n_hits


def score_pole_at_yaw(equirect_img, yaw_deg, fov_deg=70, size=300):
    """Heuristic score for 'is there a tall vertical pole roughly centered here':
    renders a small preview and scores near-vertical Hough line segments that sit
    in the central strip and reach from the lower half up toward the top."""
    view = equirect_to_perspective(equirect_img, yaw_deg=yaw_deg, pitch_deg=0, fov_deg=fov_deg, out_w=size, out_h=int(size * 1.33))
    arr = cv2.cvtColor(np.asarray(view), cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(arr, 60, 160)
    h, w = edges.shape
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=25, minLineLength=int(h * 0.18), maxLineGap=8)
    best = 0.0
    if lines is not None:
        cx = w / 2
        for (x1, y1, x2, y2) in lines[:, 0, :]:
            dx, dy = x2 - x1, y2 - y1
            length = math.hypot(dx, dy)
            if length < 1:
                continue
            angle = abs(math.degrees(math.atan2(dx, dy)))  # 0 = perfectly vertical
            if angle > 12:
                continue
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2
            centrality = max(0.0, 1 - abs(mid_x - cx) / (w * 0.35))
            lowness = max(0.0, 1 - (min(y1, y2) / (h * 0.7)))  # reaches up from lower area
            score = length * (0.4 + 0.6 * centrality) * (0.5 + 0.5 * lowness)
            best = max(best, score)
    return best


def bearing_deg(lat1, lon1, lat2, lon2):
    """Compass bearing (0=N, 90=E, ...) from point 1 to point 2. This is a
    true-north bearing -- it is NOT the same as the yaw_deg parameter used
    elsewhere in this module. See yaw_from_bearing() below."""
    la1, la2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(la2)
    y = math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(dl)
    return math.degrees(math.atan2(x, y)) % 360


def yaw_from_bearing(bearing, pano_heading):
    """Convert a true-north compass bearing into the yaw_deg parameter used by
    equirect_to_perspective / score_pole_at_yaw / etc.

    IMPORTANT (found 22/ago, calibrated against 3 links the user hand-aimed in
    the real Google Maps UI and re-verified by screenshotting those exact
    links in a real browser): Google's raw Street View equirectangular tiles
    are NOT north-aligned. Pixel column x=0 corresponds to the panorama's own
    recorded heading -- the compass direction the capture vehicle happened to
    be facing -- not true north. Using a compass bearing directly as yaw_deg
    (what this module did before) was confirmed wrong on all 3 calibration
    links, off by the panorama's own heading value (39, 130 and 215 degrees
    in those 3 cases) -- i.e. this was a systematic bug, not GPS noise.

    pano_heading is meta['heading'] from get_pano_meta(). Falls back to the
    raw bearing (old, wrong-but-harmless-default behavior) if heading is
    unavailable for a given panorama."""
    if pano_heading is None:
        return bearing % 360
    return (bearing - pano_heading) % 360


def horizontal_fov_from_google_y(y_deg, out_w, out_h):
    """Convert the 'y' value from a Google Maps Street View URL
    (.../@lat,lon,3a,<y>y,<h>h,<t>t/...) into the horizontal fov_deg expected
    by equirect_to_perspective.

    IMPORTANT (found 22/ago, same calibration links as yaw_from_bearing):
    Google's 'y' is a VERTICAL field of view, not horizontal. Treating it as
    horizontal (this module's behavior before) reproduced the right *direction*
    but rendered too narrow a vertical slice -- for a pole close to the camera
    this visibly cut off the top of the pole, even though yaw/pitch were both
    already correct. Confirmed by rendering both interpretations at the
    user-supplied link's own aspect ratio and comparing against a real
    browser screenshot of that exact link: the vertical-fov interpretation
    matched pixel-for-pixel; the horizontal-fov one cropped the pole's top.

    out_w/out_h should be the dimensions you're about to pass to
    equirect_to_perspective (the vertical fov depends on aspect ratio)."""
    aspect_hw = out_h / out_w
    fov_v = math.radians(y_deg)
    fov_h = 2 * math.atan(math.tan(fov_v / 2) / aspect_hw)
    return math.degrees(fov_h)


def auto_find_pole_yaw_constrained(equirect_img, hint_yaw, window_deg=55, coarse_step=8, fov_deg=70):
    """Like auto_find_pole_yaw, but only searches within +/-window_deg of a
    geometric hint heading (typically the compass bearing from the camera's
    own recorded position to the target pole's cadastral coordinate). This
    keeps the vertical-line heuristic from latching onto tall buildings, tree
    trunks or sign posts elsewhere in the 360 degree sphere that have nothing
    to do with the actual pole. Returns (best_yaw, scored_list)."""
    scores = []
    n = int(window_deg / coarse_step)
    for i in range(-n, n + 1):
        yaw = (hint_yaw + i * coarse_step) % 360
        s = score_pole_at_yaw(equirect_img, yaw, fov_deg=fov_deg)
        scores.append((yaw, s))
    best_yaw, best_score = max(scores, key=lambda t: t[1])
    fine_scores = []
    for dy in range(-coarse_step, coarse_step + 1, 3):
        yaw = (best_yaw + dy) % 360
        s = score_pole_at_yaw(equirect_img, yaw, fov_deg=fov_deg)
        fine_scores.append((yaw, s))
    best_yaw2, best_score2 = max(fine_scores, key=lambda t: t[1])
    return best_yaw2, sorted(scores, key=lambda t: -t[1])


def auto_find_pole_yaw(equirect_img, coarse_step=15, fov_deg=70):
    """Sweep 360 degrees to find the heading that most likely centers a pole.
    Returns (best_yaw, scored_list) for inspection."""
    scores = []
    for yaw in range(0, 360, coarse_step):
        s = score_pole_at_yaw(equirect_img, yaw, fov_deg=fov_deg)
        scores.append((yaw, s))
    best_yaw, best_score = max(scores, key=lambda t: t[1])
    # refine around the coarse best
    fine_scores = []
    for dy in range(-coarse_step, coarse_step + 1, 3):
        yaw = (best_yaw + dy) % 360
        s = score_pole_at_yaw(equirect_img, yaw, fov_deg=fov_deg)
        fine_scores.append((yaw, s))
    best_yaw2, best_score2 = max(fine_scores, key=lambda t: t[1])
    return best_yaw2, sorted(scores, key=lambda t: -t[1])


def _centering_probe(equirect_img, yaw_deg, pitch_deg, fov_deg, size=360):
    """Render a small preview and locate the most prominent near-vertical line
    reaching up from the lower half, checking two things that separate a real
    pole from a building corner, sign post or tree trunk: a twin parallel edge
    (a pole is a solid cylinder, not a bare edge) and wires converging near its
    top. Returns (line_score, mid_x_frac, w, twin_edge, wire_count) where
    mid_x_frac is the line's horizontal midpoint as a fraction of width
    (0.5 = dead center), or (0.0, None, w, False, 0) if nothing is found."""
    view = equirect_to_perspective(equirect_img, yaw_deg=yaw_deg, pitch_deg=pitch_deg,
                                    fov_deg=fov_deg, out_w=size, out_h=int(size * 1.33))
    arr = cv2.cvtColor(np.asarray(view), cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(arr, 60, 160)
    h, w = edges.shape
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=25, minLineLength=int(h * 0.18), maxLineGap=8)
    if lines is None:
        return 0.0, None, w, False, 0
    cx = w / 2
    vertical, other = [], []
    for (x1, y1, x2, y2) in lines[:, 0, :]:
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length < 1:
            continue
        angle = abs(math.degrees(math.atan2(dx, dy)))
        (vertical if angle <= 8 else other).append((x1, y1, x2, y2, length))

    best_score, best_mid, best_line = 0.0, None, None
    for (x1, y1, x2, y2, length) in vertical:
        mid_x = (x1 + x2) / 2
        centrality = max(0.0, 1 - abs(mid_x - cx) / (w * 0.35))
        lowness = max(0.0, 1 - (min(y1, y2) / (h * 0.7)))
        score = length * (0.15 + 0.85 * centrality ** 2) * (0.5 + 0.5 * lowness)
        if score > best_score:
            best_score, best_mid, best_line = score, mid_x, (x1, y1, x2, y2, length)
    if best_mid is None:
        return 0.0, None, w, False, 0

    x1, y1, x2, y2, _ = best_line
    top_x, top_y = (x1, y1) if y1 < y2 else (x2, y2)
    pole_w_min, pole_w_max = w * 0.01, w * 0.07
    twin_edge = any(
        pole_w_min < abs(((vx1 + vx2) / 2) - best_mid) < pole_w_max
        for (vx1, vy1, vx2, vy2, vlen) in vertical
        if abs(((vx1 + vx2) / 2) - best_mid) > 1
    )
    radius = w * 0.10
    wire_count = sum(
        1 for (ox1, oy1, ox2, oy2, olen) in other
        if min(math.hypot(ox1 - top_x, oy1 - top_y), math.hypot(ox2 - top_x, oy2 - top_y)) <= radius
    )
    return best_score, best_mid / w, w, twin_edge, wire_count


def refine_yaw_for_centering(equirect_img, coarse_yaw, pitch_deg=8, fov_deg=80,
                              window_deg=9, step_deg=1.0, tolerance_frac=0.06):
    """Fine sweep (default 1 degree steps) around a coarse yaw estimate. Each
    candidate heading is scored on how close its strongest vertical line sits
    to the horizontal center AND on pole-shape confidence (twin edge + wire
    convergence at the top) -- so among nearby verticals (say, a tree right
    next to the real pole) the one that actually looks like a pole wins, not
    just whichever happens to be more centered.
    Returns (final_yaw, centered_ok, offset_frac, twin_edge, wire_count)."""
    n_steps = int(round(window_deg / step_deg))
    candidates = []
    for i in range(-n_steps, n_steps + 1):
        yaw = (coarse_yaw + i * step_deg) % 360
        score, mid_frac, _, twin_edge, wire_count = _centering_probe(equirect_img, yaw, pitch_deg, fov_deg)
        if mid_frac is None:
            continue
        offset = abs(mid_frac - 0.5)
        shape_bonus = (1 if twin_edge else 0) + min(wire_count, 3) * 0.5
        # rank primarily by shape confidence, then by how centered it is
        candidates.append((-shape_bonus, offset, yaw, mid_frac, twin_edge, wire_count))
    if not candidates:
        return coarse_yaw, False, None, False, 0
    candidates.sort()
    _, offset, best_yaw, mid_frac, twin_edge, wire_count = candidates[0]
    return best_yaw, offset <= tolerance_frac, (mid_frac - 0.5), twin_edge, wire_count


def equirect_to_perspective(equirect_img, yaw_deg, pitch_deg, fov_deg, out_w=1024, out_h=1365):
    """Render a normal-looking perspective view from an equirectangular panorama.
    yaw_deg: horizontal look direction, 0-360, relative to pano's own pixel x=0 origin.
    pitch_deg: vertical look direction, positive = up.
    fov_deg: horizontal field of view of the virtual camera.
    """
    equirect = np.asarray(equirect_img)
    pano_h, pano_w = equirect.shape[:2]

    fov_h = np.deg2rad(fov_deg)
    aspect = out_h / out_w
    fov_v = 2 * np.arctan(np.tan(fov_h / 2) * aspect)

    yaw = np.deg2rad(yaw_deg)
    pitch = np.deg2rad(pitch_deg)

    xs = np.linspace(-np.tan(fov_h / 2), np.tan(fov_h / 2), out_w)
    ys = np.linspace(-np.tan(fov_v / 2), np.tan(fov_v / 2), out_h)
    xv, yv = np.meshgrid(xs, ys)
    zv = np.ones_like(xv)

    # normalize ray directions (camera space: x=right, y=down, z=forward)
    norm = np.sqrt(xv**2 + yv**2 + zv**2)
    xv, yv, zv = xv / norm, yv / norm, zv / norm

    # pitch rotation (around x axis)
    cos_p, sin_p = np.cos(pitch), np.sin(pitch)
    y2 = yv * cos_p - zv * sin_p
    z2 = yv * sin_p + zv * cos_p
    x2 = xv

    # yaw rotation (around y axis)
    cos_y, sin_y = np.cos(yaw), np.sin(yaw)
    x3 = x2 * cos_y + z2 * sin_y
    z3 = -x2 * sin_y + z2 * cos_y
    y3 = y2

    theta = np.arctan2(x3, z3)  # -pi..pi, azimuth
    phi = np.arcsin(np.clip(y3, -1, 1))  # -pi/2..pi/2, elevation

    src_x = (theta / (2 * np.pi) + 0.5) * pano_w
    src_y = (0.5 + phi / np.pi) * pano_h

    map_x = src_x.astype(np.float32)
    map_y = src_y.astype(np.float32)

    result = cv2.remap(equirect, map_x, map_y, interpolation=cv2.INTER_CUBIC, borderMode=cv2.BORDER_WRAP)
    return Image.fromarray(result)

import sys
from pano import get_pano_meta, fetch_panorama, equirect_to_perspective, remove_watermark_band
from PIL import Image

lat = float(sys.argv[1])
lon = float(sys.argv[2])
cod_id = sys.argv[3]
n_headings = int(sys.argv[4]) if len(sys.argv) > 4 else 12

meta = get_pano_meta(lat, lon)
if meta is None:
    print("NO_COVERAGE")
    sys.exit(0)

print("panoid", meta["panoid"], "pano_own_pos", meta["lat"], meta["lon"])

pano_img = fetch_panorama(meta["panoid"], meta["levels"], meta["tile_size"], zoom=4)
pano_img, _ = remove_watermark_band(pano_img)
print("pano size", pano_img.size)
pano_img.save(f"{cod_id}_equirect.jpg", quality=88)

cell_w, cell_h = 320, 480
cols = 4
rows = -(-n_headings // cols)
sheet = Image.new("RGB", (cell_w * cols, cell_h * rows), "black")
step = 360 / n_headings
for i in range(n_headings):
    yaw = i * step
    crop = equirect_to_perspective(pano_img, yaw_deg=yaw, pitch_deg=8, fov_deg=80, out_w=cell_w, out_h=cell_h)
    x = (i % cols) * cell_w
    y = (i // cols) * cell_h
    sheet.paste(crop, (x, y))
sheet.save(f"{cod_id}_scan.jpg", quality=88)
print("saved scan sheet:", f"{cod_id}_scan.jpg", "n_headings", n_headings, "step", step)

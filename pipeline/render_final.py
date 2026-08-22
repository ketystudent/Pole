import sys
from pano import equirect_to_perspective
from routing import dest_dir_for
from PIL import Image

cod_id = sys.argv[1]
yaw = float(sys.argv[2])
pitch = float(sys.argv[3])
fov = float(sys.argv[4])
suffix = sys.argv[5] if len(sys.argv) > 5 else ""  # "" or "TRANSFORMADOR"
# dest_dir: pass explicitly to override, otherwise auto-routed via esquina_index.csv
dest_dir = sys.argv[6] if len(sys.argv) > 6 else dest_dir_for(cod_id)

pano_img = Image.open(f"{cod_id}_equirect.jpg")
crop = equirect_to_perspective(pano_img, yaw_deg=yaw, pitch_deg=pitch, fov_deg=fov, out_w=1000, out_h=1333)

name = f"COD ID_{cod_id}"
if suffix:
    name += f" {suffix}"
out_path = f"{dest_dir}\\{name}.jpg"
crop.save(out_path, quality=92)
print("saved", out_path)

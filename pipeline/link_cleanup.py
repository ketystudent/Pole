# -*- coding: utf-8 -*-
import numpy as np
import cv2
from PIL import Image
import glob

def text_mask(arr, sigma, lo, hi, min_w, max_w, min_h, max_h, close_w, close_h):
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY).astype(np.float32)
    blurred = cv2.GaussianBlur(gray, (0,0), sigmaX=sigma)
    diff = gray - blurred
    mask = ((diff > lo) & (diff < hi)).astype(np.uint8)*255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_w, close_h)))
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    out = np.zeros_like(mask)
    for i in range(1, n):
        x,y,cw,ch,area = stats[i]
        if min_w < cw < max_w and min_h < ch < max_h and cw > ch*1.3:
            out[labels==i] = 255
    return out

def remove_watermark_v3(arr, extra_boxes=None):
    h, w = arr.shape[:2]
    scale = w/1000.0
    m1 = text_mask(arr, 5,  1.5, 18, int(18*scale), int(200*scale), int(4*scale), int(30*scale), max(1,int(28*scale)), max(1,int(6*scale)))
    m2 = text_mask(arr, 10, 1.2, 26, int(25*scale), int(300*scale), int(5*scale), int(48*scale), max(1,int(45*scale)), max(1,int(9*scale)))
    combined = cv2.bitwise_or(m1, m2)
    if extra_boxes:
        for (bx0,by0,bx1,by1) in extra_boxes:
            combined[by0:by1, bx0:bx1] = 255
    combined = cv2.dilate(combined, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (max(1,int(5*scale)), max(1,int(5*scale)))))
    n_hits = int((combined>0).sum())
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    inpainted = cv2.inpaint(bgr, combined, 4, cv2.INPAINT_TELEA)
    return cv2.cvtColor(inpainted, cv2.COLOR_BGR2RGB), n_hits, combined

# manual boxes only for the 2 known real leftover issues (L6 POI icons, L9 strong corner watermark)
MANUAL_BOXES = {
    "L6": [(455, 930, 520, 985), (860, 1000, 940, 1060)],  # 2 blue POI icons, approx
    "L9": [(620, 0, 1000, 90)],  # strong readable corner watermark
}

if __name__ == "__main__":
    for path in sorted(glob.glob("batch_L*.jpg")):
        # find which link this is
        key = None
        for k in MANUAL_BOXES:
            if (k + "_") in path:
                key = k
        img = Image.open(path).convert("RGB")
        arr = np.asarray(img)
        extra = MANUAL_BOXES.get(key)
        clean, hits, mask = remove_watermark_v3(arr, extra_boxes=extra)
        out = path.replace("batch_", "batch3_")
        Image.fromarray(clean).save(out, quality=92)
        print(path, "->", out, "hits=", hits)

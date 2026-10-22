"""Вырезает фигуру с ровного зелёного фона (хромакей): python3 tools/greenkey.py in.png out.png"""
import sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage


def greenkey(img, bg=None):
    arr = np.array(img.convert("RGB")).astype(int)
    if bg is None:
        bg = np.median(np.concatenate([arr[0], arr[:, 0], arr[:, -1]]), axis=0)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    dist = np.sqrt(((arr - bg) ** 2).sum(-1))
    keyish = (dist < 24) | ((g - np.maximum(r, b) > 12) & (g > 38))
    lab, _ = ndimage.label(keyish)
    border = set(np.unique(np.concatenate([lab[0], lab[:, 0], lab[:, -1]]))) - {0}
    bgm = np.isin(lab, list(border))
    sizes = ndimage.sum(keyish, lab, range(1, lab.max() + 1))
    bgm |= np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > 80])
    fg = ndimage.binary_opening(~bgm, iterations=1)
    fg = ndimage.binary_erosion(fg, iterations=1)
    a = np.array(Image.fromarray((fg * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(1.0))).astype(float) / 255
    out = arr.astype(float)
    spill = out[..., 1] > np.maximum(out[..., 0], out[..., 2]) + 4
    out[..., 1] = np.where(spill & (a < 1), np.maximum(out[..., 0], out[..., 2]) + 4, out[..., 1])
    rgba = Image.fromarray(np.dstack([out.clip(0, 255), a * 255]).astype("uint8"), "RGBA")
    return rgba.crop(rgba.split()[3].point(lambda v: 255 if v > 20 else 0).getbbox())


if __name__ == "__main__":
    greenkey(Image.open(sys.argv[1])).save(sys.argv[2])

"""Вырезает фигуру с белого/светло-серого фона: python3 tools/cutout.py in.png out.png"""
import sys
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage


def cutout(src, dst, max_side=1400):
    arr = np.array(Image.open(src).convert("RGB")).astype(int)
    sat = arr.max(axis=2) - arr.min(axis=2)
    light = (arr.min(axis=2) > 165) & (sat < 35)
    lab, _ = ndimage.label(light)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bg = np.isin(lab, list(border))
    pure = (arr.min(axis=2) > 190) & (sat < 22)
    lab2, n2 = ndimage.label(pure)
    sizes = ndimage.sum(pure, lab2, range(1, n2 + 1))
    bg |= np.isin(lab2, [i + 1 for i, s in enumerate(sizes) if s > 150])
    fg = ndimage.binary_erosion(ndimage.binary_opening(~bg, iterations=2), iterations=3)
    a = np.array(Image.fromarray((fg * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(1.5))).astype(float) / 255
    rgb = arr.astype(float)
    edge = (a > 0) & (a < 0.98)
    rgb[edge] *= 0.55
    img = Image.fromarray(np.dstack([rgb.clip(0, 255), a * 255]).astype("uint8"), "RGBA")
    img = img.crop(img.split()[3].point(lambda v: 255 if v > 20 else 0).getbbox())
    img.thumbnail((max_side // 2, max_side))
    img.save(dst)


if __name__ == "__main__":
    cutout(sys.argv[1], sys.argv[2])

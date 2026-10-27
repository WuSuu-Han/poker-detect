# -*- coding: utf-8 -*-
"""看一张图在内存里长什么样：维度、BGR 顺序、通道、灰度公式。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
from PIL import Image

from cardlib import imageio

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "data", "cards_sample.jpg")
OUT = os.path.join(ROOT, "output", "lesson1")


def main():
    os.makedirs(OUT, exist_ok=True)
    img = imageio.imread(IMG)

    print("shape", img.shape, "dtype", img.dtype, "MB %.2f" % (img.nbytes / 1024.0 / 1024))

    y, x = 300, 500
    pil = np.array(Image.open(IMG))
    print("cv2 ", img[y, x], "BGR")
    print("pil ", pil[y, x], "RGB")

    b, g, r = cv2.split(img)
    for name, ch in (("B", b), ("G", g), ("R", r)):
        cv2.imwrite(os.path.join(OUT, "channel_%s.png" % name), ch)
        print("channel", name, "mean %.1f" % ch.mean())

    roi = img[0:200, 0:260]
    print("roi", roi.shape)
    imageio.imwrite(os.path.join(OUT, "roi_topleft.jpg"), roi)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    bb, gg, rr = [int(v) for v in img[y, x]]
    print("by hand %.2f" % (0.299 * rr + 0.587 * gg + 0.114 * bb), "cv2", gray[y, x])
    imageio.imwrite(os.path.join(OUT, "gray.png"), gray)


if __name__ == "__main__":
    main()

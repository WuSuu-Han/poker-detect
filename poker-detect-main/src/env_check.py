# -*- coding: utf-8 -*-
"""环境自检，跑通了再往下做。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
import PIL
import tkinter

from cardlib import imageio

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "data", "cards_sample.jpg")


def main():
    print("python", sys.version.split()[0], sys.executable)
    print("cv2", cv2.__version__, "| numpy", np.__version__, "| pillow", PIL.__version__)
    print("tk", tkinter.TkVersion)

    img = imageio.imread(SAMPLE)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    print("image", img.shape, "gray mean/std %.1f/%.1f" % (gray.mean(), gray.std()))

    out = os.path.join(ROOT, "output", "step1_loaded.jpg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    print("save", imageio.imwrite(out, img))


if __name__ == "__main__":
    main()

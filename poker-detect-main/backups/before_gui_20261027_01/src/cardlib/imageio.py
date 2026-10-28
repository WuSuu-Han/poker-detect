# -*- coding: utf-8 -*-
"""读写图片。cv2.imread 不认中文路径，这里绕一下。"""

import os

import cv2
import numpy as np


def imread(path, flags=cv2.IMREAD_COLOR):
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), flags)
    if img is None:
        raise ValueError("decode failed: " + path)
    return img


def imwrite(path, img, quality=95):
    ext = os.path.splitext(path)[1].lower() or ".png"
    params = [cv2.IMWRITE_JPEG_QUALITY, int(quality)] if ext in (".jpg", ".jpeg") else []
    ok, buf = cv2.imencode(ext, img, params)
    if not ok:
        return False
    buf.tofile(path)
    return True


def to_rgb(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

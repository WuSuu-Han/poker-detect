# -*- coding: utf-8 -*-
"""在图片上跑一遍定位，输出掩膜、四角框、摆正后的牌。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np

from cardlib import detector, imageio

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output")
SAMPLE = os.path.join(ROOT, "data", "cards_sample.jpg")


def make_grid(cards, cols=4, pad=12):
    if not cards:
        return np.zeros((10, 10, 3), np.uint8)

    w, h = detector.CARD_W, detector.CARD_H
    rows = int(np.ceil(len(cards) / float(cols)))
    canvas = np.full((rows * (h + pad) + pad, cols * (w + pad) + pad, 3), 30, np.uint8)
    for i, c in enumerate(cards):
        r, q = divmod(i, cols)
        y, x = pad + r * (h + pad), pad + q * (w + pad)
        canvas[y:y + h, x:x + w] = c.warped
        cv2.putText(canvas, "#{}".format(i + 1), (x + 4, y + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA)
    return canvas


def main():
    os.makedirs(OUT, exist_ok=True)
    img = imageio.imread(SAMPLE)
    print("原图 {}x{}".format(img.shape[1], img.shape[0]))

    diagnostic = detector.analyze(img)
    mask = diagnostic['mask']
    imageio.imwrite(os.path.join(OUT, "step2_mask.png"), mask)
    print("掩膜覆盖率 {:.1f}%".format(100.0 * (mask > 0).mean()))

    cards = diagnostic['cards']
    print('selected threshold candidate:', diagnostic['candidate'])
    print("检测到 {} 张".format(len(cards)))
    for i, c in enumerate(cards):
        print("  #{:<2} ({:>4.0f},{:>4.0f})  area={:<7.0f} aspect={:.2f}".format(
            i + 1, c.center[0], c.center[1], c.area, c.aspect))

    imageio.imwrite(os.path.join(OUT, "step2_quads.jpg"), detector.draw_results(img, cards))
    imageio.imwrite(os.path.join(OUT, "step2_cards.jpg"), make_grid(cards))


if __name__ == "__main__":
    main()

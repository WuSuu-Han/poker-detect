# -*- coding: utf-8 -*-
"""跑完整流程：定位 -> 摆正 -> 点数 / 花色，并把结果画到图上。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np

from cardlib import SUIT_SYMBOL
from cardlib import detector, imageio, ranksuit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output")
DEFAULT = os.path.join(ROOT, "data", "cards_sample.jpg")


def label_of(rank, suit):
    return "{}{}".format(rank or "?", (suit or "?").upper())


def draw_cards(cards, cols=4, pad=10):
    w, h = detector.CARD_W, detector.CARD_H
    rows = max(1, (len(cards) + cols - 1) // cols)
    canvas = np.full((rows * (h + pad) + pad, cols * (w + pad) + pad, 3), 28, np.uint8)
    for i, c in enumerate(cards):
        r, q = divmod(i, cols)
        y, x = pad + r * (h + pad), pad + q * (w + pad)
        canvas[y:y + h, x:x + w] = c.warped
        text = "#{}".format(i + 1)
        cv2.putText(canvas, text, (x + 5, y + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 1, cv2.LINE_AA)
    return canvas


def main(argv):
    sample = argv[1] if len(argv) > 1 else DEFAULT
    img = imageio.imread(sample)
    print("image {}x{}".format(img.shape[1], img.shape[0]))

    cards = detector.detect_cards(img)
    print("detected {} cards".format(len(cards)))

    os.makedirs(OUT, exist_ok=True)
    for i, c in enumerate(cards):
        r = ranksuit.read_card(c.warped)
        c.rank, c.suit, c.confidence = r["rank"], r["suit"], r["score"]
        c.rot = r["rot"]
        print("  #{:<2} {:>2}{}  rot={} dist={:.2f}/{:.2f} conf={:.2f}".format(
            i + 1, c.rank or "?", (c.suit or "?").upper(),
            c.rot, r.get("rank_dist", 0), r.get("suit_dist", 0), r["score"]))

    def tag(i, c):
        return "#{} {}".format(i + 1, label_of(c.rank, c.suit) if c.rank else "?")

    imageio.imwrite(os.path.join(OUT, "step3_cards.jpg"), draw_cards(cards))
    imageio.imwrite(os.path.join(OUT, "step3_result.jpg"),
                    detector.draw_results(img, cards, label_fn=tag))
    print("wrote output/step3_result.jpg, output/step3_cards.jpg")


if __name__ == "__main__":
    main(sys.argv)

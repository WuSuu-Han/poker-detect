# -*- coding: utf-8 -*-
"""鲁棒性自测：在示例图上叠加光照、模糊、压缩、旋转、透视，检查定位和识别还剩多少。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np

from cardlib import detector, imageio, ranksuit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE = os.path.join(ROOT, "data", "cards_sample.jpg")

# 示例图的正确答案（阅读顺序）
TRUTH = ["9S", "AD", "AC", "7C", "6C", "QS", "10H", "4S"]


def degrade(img):
    """返回 [(名字, 图), ...]。"""
    out = [("原图", img)]

    out.append(("暗光 45%", np.clip(img.astype(np.float32) * 0.45, 0, 255).astype(np.uint8)))
    out.append(("过曝 1.35", np.clip(img.astype(np.float32) * 1.35, 0, 255).astype(np.uint8)))
    out.append(("模糊 7x7", cv2.GaussianBlur(img, (7, 7), 0)))

    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 20])
    out.append(("JPEG q20", cv2.imdecode(buf, cv2.IMREAD_COLOR)))

    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2.0, h / 2.0), 20, 1.0)
    out.append(("旋转 20°", cv2.warpAffine(img, m, (w, h), borderValue=(60, 60, 60))))

    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dst = np.float32([[0.06 * w, 0.10 * h], [0.94 * w, 0], [w, 0.92 * h], [0.10 * w, h]])
    out.append(("透视", cv2.warpPerspective(img, cv2.getPerspectiveTransform(src, dst), (w, h))))

    return out


def code_of(card):
    if not card.rank or not card.suit:
        return "?"
    return "{}{}".format(card.rank, card.suit.upper())


def run():
    base = imageio.imread(SAMPLE)
    print("{:<12}{:>6}{:>8}{:>8}".format("场景", "检出", "识别对", "备注"))
    total_ok = total = 0

    for name, img in degrade(base):
        cards = detector.detect_cards(img)
        got = []
        for c in cards:
            r = ranksuit.read_card(c.warped)
            c.rank, c.suit = r["rank"], r["suit"]
            got.append(code_of(c))

        hit = sum(1 for g, t in zip(got, TRUTH) if g == t)
        # 旋转 / 透视之后牌的先后顺序会变，按多重集合再算一遍
        pool = list(TRUTH)
        matched = 0
        for g in got:
            if g in pool:
                pool.remove(g)
                matched += 1
        hit = max(hit, matched)
        note = "" if hit == len(TRUTH) else " ".join(got)
        print("{:<12}{:>6}{:>8}{:>8}".format(name, len(cards), "{}/{}".format(hit, len(TRUTH)), note))
        total_ok += hit
        total += len(TRUTH)

    print("\n合计 {}/{}（{:.1f}%）".format(total_ok, total, 100.0 * total_ok / total))


if __name__ == "__main__":
    run()

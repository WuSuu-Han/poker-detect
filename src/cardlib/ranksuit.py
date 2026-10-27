# -*- coding: utf-8 -*-
"""点数与花色识别：索引区切分 + 倒角距离模板匹配。"""

import os

import cv2
import numpy as np

from . import RANKS, SUIT_SYMBOL

RECOG_W, RECOG_H = 300, 420      # 识别用尺寸，索引区太小会糊
SHAPE = 48                       # 形状归一化到 SHAPE*SHAPE
SHAPE_PAD = 4
ROT_PENALTY = 0.02               # 同分时偏向原方向

IDX_X0, IDX_X1 = 0.025, 0.200    # 索引区占比，宽度只到 0.20 免得切进中间的大花色
IDX_Y0, IDX_Y1 = 0.020, 0.300

MIN_COMP_AREA = 18
MAX_COMP_AREA = 1400
MAX_COMP_W = 0.80

WAIST_SPLIT = 0.68               # 黑桃收腰，梅花不收腰

_FONT_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
_RANK_FONTS = ("times.ttf", "timesbd.ttf", "georgia.ttf", "constan.ttf",
               "arial.ttf", "arialbd.ttf", "tahoma.ttf", "cambria.ttf")
_SUIT_FONT = "seguisym.ttf"


# ------------------------------------------------------------------ 基础工具

def ink_mask(bgr):
    """索引区墨迹：Otsu 取暗的，再并上有颜色的。"""
    g = cv2.GaussianBlur(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), (3, 3), 0)
    _, dark = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    sat = ((hsv[:, :, 1] > 110) & (hsv[:, :, 2] > 60)).astype(np.uint8) * 255
    m = cv2.bitwise_or(dark, sat)
    return cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))


def is_red_ink(bgr, mask):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    m = (mask > 0) & (hsv[:, :, 1] > 140) & (hsv[:, :, 2] > 40)
    if m.sum() < 20:
        return False
    hh = hsv[:, :, 0][m]
    return float(((hh < 12) | (hh > 165)).mean()) > 0.6


def _bbox(mask):
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def norm_shape(mask, size=SHAPE, pad=SHAPE_PAD):
    """裁到外接框，拉伸成正方形。牌面上的字是窄体，按长宽比缩放反而对不齐。"""
    box = _bbox(mask)
    if box is None:
        return None
    x0, y0, x1, y1 = box
    g = (mask[y0:y1, x0:x1] > 0).astype(np.uint8) * 255
    inner = size - 2 * pad
    g = cv2.resize(g, (inner, inner), interpolation=cv2.INTER_AREA)
    out = np.zeros((size, size), np.uint8)
    out[pad:size - pad, pad:size - pad] = (g > 127).astype(np.uint8)
    return out.astype(bool)


def _dt(shape):
    return cv2.distanceTransform((~shape).astype(np.uint8), cv2.DIST_L2, 3)


def chamfer(a, b, dt_b=None):
    """双向平均距离，越小越像。对笔画粗细和细微形变比相关系数宽容。"""
    if a is None or b is None:
        return 9.9
    da = _dt(a)
    db = _dt(b) if dt_b is None else dt_b
    return 0.5 * (float(db[a].mean()) + float(da[b].mean()))


def _largest(mask):
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask, 8)
    if n < 2:
        return mask
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    return np.uint8(lab == i) * 255


# ------------------------------------------------------------------ 模板

def _render(text, font_file):
    from PIL import Image, ImageDraw, ImageFont

    px = 200
    font = ImageFont.truetype(os.path.join(_FONT_DIR, font_file), px)
    img = Image.new("L", (px * 3, px * 3), 0)
    ImageDraw.Draw(img).text((px // 2, px // 4), text, fill=255, font=font)
    return np.array(img)


_RANK_TPL = {}
_SUIT_TPL = {}


def rank_templates():
    """{点数: [(归一化形状, 距离变换), ...]}，第一次调用时渲染并缓存。"""
    if _RANK_TPL:
        return _RANK_TPL
    for rank in RANKS:
        lst = []
        for ff in _RANK_FONTS:
            if not os.path.exists(os.path.join(_FONT_DIR, ff)):
                continue
            s = norm_shape(_render(rank, ff))
            if s is not None:
                lst.append((s, _dt(s)))
        if lst:
            _RANK_TPL[rank] = lst
    return _RANK_TPL


def suit_templates():
    if _SUIT_TPL:
        return _SUIT_TPL
    path = os.path.join(_FONT_DIR, _SUIT_FONT)
    if os.path.exists(path):
        for suit in SUIT_SYMBOL:
            s = norm_shape(_render(SUIT_SYMBOL[suit], _SUIT_FONT))
            if s is not None:
                _SUIT_TPL[suit] = [(s, _dt(s))]
    return _SUIT_TPL


# ------------------------------------------------------------------ 索引区

def index_crop(card):
    h, w = card.shape[:2]
    x0, x1 = int(IDX_X0 * w), int(IDX_X1 * w)
    y0, y1 = int(IDX_Y0 * h), int(IDX_Y1 * h)
    return card[y0:y1, x0:x1]


def _components(mask):
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask, 8)
    h, w = mask.shape[:2]
    out = []
    for i in range(1, n):
        x, y, bw, bh, area = [int(v) for v in st[i]]
        if area < MIN_COMP_AREA or area > MAX_COMP_AREA:
            continue
        if bw >= MAX_COMP_W * w or x + bw >= w - 2 or x <= 1 or y <= 1:
            continue
        out.append([x, y, x + bw, y + bh, area])
    return out


def _merge_rank(mask):
    """按行合并：“10”是两个字符，间距小、上下对齐。"""
    boxes = sorted(_components(mask), key=lambda b: b[1])
    merged = []
    for b in boxes:
        if merged:
            p = merged[-1]
            hgt = min(p[3] - p[1], b[3] - b[1])
            ov = min(p[3], b[3]) - max(p[1], b[1])
            if ov > 0.6 * hgt and b[0] - p[2] < 0.25 * hgt:
                p[2] = max(p[2], b[2])
                p[1] = min(p[1], b[1])
                p[3] = max(p[3], b[3])
                continue
        merged.append(list(b))
    return merged


def split_index(crop):
    """切成 ((点数图, 花色图, 花色原图), (点数框, 花色框))，切不开返回 (None, boxes)。"""
    m = ink_mask(crop)
    boxes = _merge_rank(m)
    if len(boxes) < 2:
        return None, boxes

    boxes.sort(key=lambda b: b[1])
    rank_box, suit_box = boxes[0], None
    rank_h = rank_box[3] - rank_box[1]
    for b in boxes[1:]:
        if b[1] > rank_box[1] + 0.35 * rank_h:
            suit_box = b
            break
    if suit_box is None:
        return None, boxes

    rank_m = m[rank_box[1]:rank_box[3], rank_box[0]:rank_box[2]]
    suit_m = _largest(m[suit_box[1]:suit_box[3], suit_box[0]:suit_box[2]])
    suit_bgr = crop[suit_box[1]:suit_box[3], suit_box[0]:suit_box[2]]
    return (rank_m, suit_m, suit_bgr), (rank_box, suit_box)


# ------------------------------------------------------------------ 判别

def _is_ten(mask):
    """“10”是唯一由两个字符组成的点数。两条竖笔画高度接近、一窄一宽，就判 10。"""
    n, lab, st, _ = cv2.connectedComponentsWithStats(mask, 8)
    comps = [st[i] for i in range(1, n) if st[i, cv2.CC_STAT_AREA] >= 20]
    if len(comps) != 2:
        return False
    (x1, y1, w1, h1, _), (x2, y2, w2, h2, _) = comps
    hi, lo = max(h1, h2), max(1, min(h1, h2))
    wi, wo = max(w1, w2), max(1, min(w1, w2))
    return lo >= 0.6 * hi and wo <= 0.6 * wi


def classify_rank(mask):
    """返回 (点数, 距离)。"""
    if _is_ten(mask):
        return "10", 0.1

    a = norm_shape(mask)
    best, best_d = None, 9.9
    for rank, lst in rank_templates().items():
        if rank == "10":             # 10 用上面的结构判断，模板匹配对它没优势
            continue
        d = min(chamfer(a, t, dt) for t, dt in lst)
        if d < best_d:
            best, best_d = rank, d
    return best, best_d


def waist_ratio(mask):
    """腰部宽度占比。黑桃是三角顶，这里还很宽；梅花是三瓣，这里收腰。"""
    box = _bbox(mask)
    if box is None:
        return 0.0
    x0, y0, x1, y1 = box
    g = (mask[y0:y1, x0:x1] > 0).astype(np.uint8)
    h, w = g.shape
    rows = g[int(0.35 * h):int(0.50 * h) + 1, :]
    spans = []
    for row in rows:
        xs = row.nonzero()[0]
        if len(xs):
            spans.append(float(xs.max() - xs.min() + 1) / float(w))
    if not spans:
        return 0.0
    return float(np.median(spans))


def classify_suit(mask, suit_bgr):
    """返回 (花色, 距离)。颜色定红黑；红的两选一看形状，黑的两选一看腰部。"""
    a = norm_shape(mask)
    red = is_red_ink(suit_bgr, mask)
    tpl = suit_templates()

    if red:
        best, best_d = None, 9.9
        for suit in ("h", "d"):
            d = min(chamfer(a, t, dt) for t, dt in tpl.get(suit, []))
            if d < best_d:
                best, best_d = suit, d
        return best or "h", best_d

    ratio = waist_ratio(mask)
    best = "s" if ratio >= WAIST_SPLIT else "c"
    best_d = min(chamfer(a, t, dt) for t, dt in tpl.get(best, [(None, None)]))
    return best, best_d


def read_card(card):
    """读一张牌：四个方向各试一次，取“点数 + 花色”总距离最小的那个方向。

    返回 dict(rank, suit, score, rot, boxes)，识别失败时 rank/suit 为 None。
    """
    if card.shape[:2] != (RECOG_H, RECOG_W):
        card = cv2.resize(card, (RECOG_W, RECOG_H), interpolation=cv2.INTER_CUBIC)

    best = None
    for r in range(4):
        rot = np.rot90(card, r).copy()
        parts, boxes = split_index(index_crop(rot))
        if parts is None:
            continue
        rank, rd = classify_rank(parts[0])
        suit, sd = classify_suit(parts[1], parts[2])
        # 方向只看点数：点数模板对 90/180 度很敏感，花色在黑色两选一里靠形状规则，不适合参与定方向
        total = rd + ROT_PENALTY * r
        if best is None or total < best[0]:
            best = (total, r, rank, rd, suit, sd, boxes)

    if best is None:
        return {"rank": None, "suit": None, "score": 0.0, "rot": 0, "boxes": []}

    total, r, rank, rd, suit, sd, boxes = best
    return {
        "rank": rank, "suit": suit,
        "score": max(0.0, 1.0 - 0.5 * total),
        "rank_dist": rd, "suit_dist": sd,
        "rot": r, "boxes": boxes,
    }

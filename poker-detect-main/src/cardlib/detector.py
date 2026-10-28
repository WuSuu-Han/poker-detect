# -*- coding: utf-8 -*-
"""牌面定位：颜色分割 -> 轮廓 -> 四边形 -> 透视校正"""

import cv2
import numpy as np

CARD_W, CARD_H = 210, 294  # 标准牌 2.5 : 3.5
MAX_SIDE = 1280            # 检测前长边不超过这个，手机图也能跑

DEFAULT_PARAMS = {
    "v_min": 130,             # 白纸亮度下限
    "s_max": 95,              # 饱和度上限
    "blur": 3,
    "open_k": 3,
    "close_k": 9,
    "min_area_ratio": 0.003,
    "max_area_ratio": 0.5,
    "aspect_tol": 0.34,
}

MIN_FILL = 0.80       # 四边形填充率，低于这个可能两张牌粘一起
MIN_WHITE = 70        # 牌面白度绝对下限，防止全黑图上乱认
WHITE_GAIN = 1.9      # 牌面要比背景亮这么多倍，光照变了也成立


class DetectedCard(object):
    def __init__(self, quad, warped, area, aspect):
        self.quad = quad          # 4x2, 左上/右上/右下/左下
        self.warped = warped
        self.area = area
        self.aspect = aspect
        self.center = quad.mean(axis=0)

        # 识别结果，第 3 步填
        self.rank = None
        self.suit = None
        self.confidence = 0.0
        self.rot = 0
        self.accepted = False
        self.oriented = warped


def _odd(k, lo=1):
    k = max(lo, int(k))
    return k if k % 2 else k + 1


def _resize_for_detect(img, max_side=MAX_SIDE):
    h, w = img.shape[:2]
    s = min(1.0, float(max_side) / max(h, w))
    if s >= 1.0:
        return img, 1.0
    return cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA), s


# ---------------------------------------------------------------- 阈值

def estimate_params(img):
    """用 Otsu 从图里估阈值，省得每换一张图都手调。"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    tv, _ = cv2.threshold(hsv[:, :, 2], 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    ts, _ = cv2.threshold(hsv[:, :, 1], 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    p = dict(DEFAULT_PARAMS)
    p["v_min"] = float(np.clip(tv, 60, 210))
    p["s_max"] = float(np.clip(ts, 35, 150))
    return p


def _percentile_params(img):
    """Otsu 在极端光照下会失手，再给一组按分位数估的。"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    p = dict(DEFAULT_PARAMS)
    p["v_min"] = float(np.clip(np.percentile(hsv[:, :, 2], 62), 70, 220))
    p["s_max"] = float(np.clip(np.percentile(hsv[:, :, 1], 55), 30, 160))
    return p


def _param_candidates(img):
    out = [("otsu", estimate_params(img)),
           ("percentile", _percentile_params(img)),
           ("fixed", dict(DEFAULT_PARAMS))]
    seen = []
    for name, p in out:
        key = (round(p["v_min"]), round(p["s_max"]))
        if key not in seen:
            seen.append(key)
            yield name, p


# ---------------------------------------------------------------- 分割

def make_card_mask(img, params=None):
    """白牌的二值掩膜，255 是牌。params 为空时自动估。"""
    p = dict(estimate_params(img))
    p.update(params or {})

    src = img
    if p["blur"] > 1:
        src = cv2.GaussianBlur(img, (_odd(p["blur"]),) * 2, 0)

    hsv = cv2.cvtColor(src, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv,
                       np.array([0, 0, p["v_min"]], np.uint8),
                       np.array([180, p["s_max"], 255], np.uint8))

    k_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (_odd(p["open_k"]),) * 2)
    k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (_odd(p["close_k"]),) * 2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k_open)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k_close)

    # 去掉小碎块
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    h, w = mask.shape[:2]
    min_area = p["min_area_ratio"] * h * w * 0.5
    keep = np.zeros_like(mask)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_AREA] >= min_area:
            keep[labels == i] = 255
    mask = keep

    # 填洞，不然点数花纹会把轮廓切碎
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros_like(mask)
    cv2.drawContours(filled, cnts, -1, 255, cv2.FILLED)
    return filled


# ---------------------------------------------------------------- 四边形

def order_quad(pts):
    """排成左上、右上、右下、左下。"""
    pts = np.asarray(pts, np.float32).reshape(4, 2)
    c = pts.mean(axis=0)
    ang = np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0])
    pts = pts[np.argsort(ang)]
    pts = np.roll(pts, -int(np.argmin(pts.sum(axis=1))), axis=0)
    return pts.astype(np.float32)


def _quad_from_contour(cnt):
    """轮廓的四个角点。"""
    # approxPolyDP 在圆角处会缩角，先用 minAreaRect 定方向，再在凸包上找极值点
    hull = cv2.convexHull(cnt)
    pts = hull.reshape(-1, 2).astype(np.float32)
    (cx, cy), (rw, rh), ang = cv2.minAreaRect(hull)
    t = np.deg2rad(ang)
    u = np.array([np.cos(t), np.sin(t)], np.float32)
    v = np.array([-np.sin(t), np.cos(t)], np.float32)

    corners = []
    for su in (1.0, -1.0):
        for sv in (1.0, -1.0):
            corners.append(pts[int(np.argmax(pts.dot(su * u + sv * v)))])
    quad = np.array(corners, np.float32)

    if len(np.unique(np.round(quad, 1), axis=0)) < 4:
        quad = cv2.boxPoints(((cx, cy), (rw, rh), ang)).astype(np.float32)
    return quad


def _rect_info(cnt):
    """(宽高比, 填充率)。宽高比用旋转矩形的，跟旋转角无关；
    填充率 = 轮廓面积 / 外接旋转矩形面积，粘连成 L 形时会明显变小。"""
    hull = cv2.convexHull(cnt)
    (_, _), (rw, rh), _ = cv2.minAreaRect(hull)
    lo, hi = min(rw, rh), max(rw, rh)
    aspect = lo / hi if hi > 1e-6 else 0.0
    rect_area = rw * rh
    fill = cv2.contourArea(hull) / rect_area if rect_area > 1e-6 else 0.0
    return aspect, fill


def warp_card(img, quad, size=(CARD_W, CARD_H), pad=0.03):
    """透视变换成正面。pad 把框放大一点，免得切掉牌边。"""
    w, h = size
    quad = order_quad(quad)
    if np.linalg.norm(quad[1]-quad[0]) > np.linalg.norm(quad[2]-quad[1]):
        quad = np.roll(quad, -1, axis=0)
    if pad > 0:
        c = quad.mean(axis=0)
        quad = c + (quad - c) * (1.0 + 2.0 * pad)

    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], np.float32)
    M = cv2.getPerspectiveTransform(quad.astype(np.float32), dst)
    return cv2.warpPerspective(img, M, (w, h), flags=cv2.INTER_CUBIC)


def _split_blob(cnt):
    """两张牌粘成一个连通域时，反复腐蚀直到断开，再把两半还原回去。"""
    x, y, w, h = cv2.boundingRect(cnt)
    m = np.zeros((h + 2, w + 2), np.uint8)
    cv2.drawContours(m, [cnt], -1, 255, cv2.FILLED, offset=(-x + 1, -y + 1))
    total = float((m > 0).sum())
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))

    for it in range(3, 16):
        er = cv2.erode(m, k, iterations=it)
        n, lab, st, _ = cv2.connectedComponentsWithStats(er, 8)
        idx = [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 0.12 * total]
        if len(idx) >= 2:
            idx = sorted(idx, key=lambda i: -st[i, cv2.CC_STAT_AREA])[:2]
            parts = []
            for i in idx:
                pm = np.uint8(lab == i) * 255
                pm = cv2.dilate(pm, k, iterations=it)
                cs, _ = cv2.findContours(pm, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                c = max(cs, key=cv2.contourArea) + np.array([x - 1, y - 1], np.int32)
                parts.append(c)
            return parts
    return None


def _white_ratio(img, quad):
    """牌面白度，用来挡掉反光块、浅色桌面。

    不能只看平均亮度：J/Q/K 中间一大片彩色人头，平均值会被拉低。
    改成中位数 + 边缘环带中位数各占一半，牌边一定是白的。
    """
    small = warp_card(img, quad, size=(40, 56), pad=0.02)
    g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    ring = np.concatenate([g[:4, :].ravel(), g[-4:, :].ravel(),
                           g[:, :4].ravel(), g[:, -4:].ravel()])
    return 0.5 * float(np.median(g)) + 0.5 * float(np.median(ring))


def _pick_quads(img, params):
    """一组阈值下，把掩膜里的候选挑出来。返回 (quads, rejects)。"""
    mask = make_card_mask(img, params)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = img.shape[:2]
    area_all = float(h * w)

    # 白度阈值跟着背景走，不然拍暗了全被判成“不是牌”
    bg = float(np.median(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)))
    white_thr = min(235.0, max(MIN_WHITE, WHITE_GAIN * bg))

    quads, rejects = [], []
    for cnt in cnts:
        area = cv2.contourArea(cnt)
        if not (params["min_area_ratio"] * area_all < area < params["max_area_ratio"] * area_all):
            continue

        aspect, fill = _rect_info(cnt)
        if abs(aspect - CARD_W / float(CARD_H)) > params["aspect_tol"]:
            rejects.append(("aspect", area, aspect, fill))
            continue

        parts = None
        if fill < MIN_FILL:
            parts = _split_blob(cnt)

        for c in (parts if parts else [cnt]):
            q = _quad_from_contour(c)
            if len(q) != 4:
                continue
            white = _white_ratio(img, q)
            if white < white_thr:
                rejects.append(("not white (%.0f<%.0f)" % (white, white_thr), area, aspect, fill))
                continue
            a2, f2 = _rect_info(c)
            quads.append((order_quad(q), cv2.contourArea(c), a2, f2))

    return mask, quads, rejects


def find_card_quads(img, params=None):
    """返回 [(quad, area, aspect, fill), ...]。params 为空时在几组阈值里挑最好的。"""
    if params is not None:
        _, quads, _ = _pick_quads(img, dict(params))
        return quads

    best = None
    for _, p in _param_candidates(img):
        _, quads, _ = _pick_quads(img, p)
        if best is None or len(quads) > len(best):
            best = quads
    return best or []


def _reading_order(cards):
    """按行排，方便界面从上往下、从左往右列。"""
    if not cards:
        return cards
    cards = sorted(cards, key=lambda c: c.center[1])
    rows, cur = [], [cards[0]]
    for c in cards[1:]:
        if abs(c.center[1] - cur[-1].center[1]) < CARD_H * 0.5:
            cur.append(c)
        else:
            rows.append(cur)
            cur = [c]
    rows.append(cur)

    out = []
    for row in rows:
        out.extend(sorted(row, key=lambda c: c.center[0]))
    return out


def detect_cards(img, params=None):
    """定位 + 摆正。返回按阅读顺序排好的 DetectedCard。"""
    small, scale = _resize_for_detect(img)
    quads = find_card_quads(small, params)

    cards = []
    for quad, area, aspect, _ in quads:
        q = quad / scale
        cards.append(DetectedCard(q, warp_card(img, q), area / (scale * scale), aspect))
    return _reading_order(cards)


def analyze(img, params=None):
    """调参用的诊断信息：掩膜、用了哪组阈值、被丢掉的原因。"""
    small, scale = _resize_for_detect(img)
    candidates = [("custom", dict(params))] if params is not None else list(_param_candidates(small))
    chosen = None
    for name, candidate in candidates:
        cmask, cquads, crejects = _pick_quads(small, candidate)
        if chosen is None or len(cquads) > len(chosen[2]):
            chosen = (name, cmask, cquads, crejects, candidate)
    name, mask, quads, rejects, p = chosen
    cards = [DetectedCard(q / scale, warp_card(img, q / scale),
                          a / (scale * scale), asp) for q, a, asp, _ in quads]
    return {
        "mask": mask,
        "candidate": name,
        "params": p,
        "scale": scale,
        "cards": _reading_order(cards),
        "rejects": rejects,
    }


def draw_results(img, cards, color=(0, 255, 0), thickness=2, label_fn=None):
    vis = img.copy()
    for i, c in enumerate(cards):
        pts = c.quad.astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(vis, [pts], True, color, thickness, cv2.LINE_AA)

        text = label_fn(i, c) if label_fn else "#{}".format(i + 1)
        if text:
            x, y = int(c.quad[:, 0].min()), int(c.quad[:, 1].min())
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            y = max(y, th + 6)
            cv2.rectangle(vis, (x, y - th - 8), (x + tw + 8, y + 4), color, -1)
            cv2.putText(vis, text, (x + 4, y - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2, cv2.LINE_AA)
    return vis

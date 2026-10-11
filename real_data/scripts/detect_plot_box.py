"""First-pass detection of the plot (axis) frame in the published AstroExplorer figures.

The AVM astrometry was fitted to the axis ticks, so it is correct, but the stored images
are page crops (running heads, colorbars, captions, sometimes neighbouring text). The
angular width/height of the *plotted* region therefore needs the axis frame, not the
whole JPEG. This script proposes that frame as 4 corner points, for human review in
Label Studio (see scripts/label_studio/README.md).

Method (OpenCV):
  1. Otsu-threshold the greyscale image (dark ink -> 1).
  2. Morphological opening with long horizontal / vertical kernels keeps only long
     straight ink runs -- axis lines, frame edges, colorbar edges, table rules.
  3. Candidate A ("closed"): contours of the combined line mask, simplified to
     quadrilaterals; keep convex, near-rectangular (angles 90+/-12 deg) quads covering
     >= 5% of the image.
  4. Candidate B ("photo"): for frameless halftone/greyscale panels (axes are only tick
     marks around the photograph), the large non-paper region containing the reference
     pixel after heavy blurring, as a minimum-area rectangle.
  5. Candidate C ("lines"): when no closed quad works (e.g. a frame cut by the crop),
     build a box from the longest horizontal and vertical segments; a missing side is
     replaced by the image edge and flagged as truncated.
  6. Among candidates, prefer ones containing the AVM reference pixel (the astrometric
     solution is anchored there, so it lies on/inside the frame for the panel that was
     solved), then the largest.
Every proposal gets a method + flags so review can be prioritised.

Usage:
  ~/.venvs/plotbox/bin/python detect_plot_box.py <real_data_dir> [--overlays]
Writes <real_data_dir>/plot_boxes/auto_boxes.json (and overlays/ if asked).
Corner coordinates are image pixels, origin TOP-LEFT, order TL, TR, BR, BL.
"""
import glob, json, os, sys
import cv2
import numpy as np

root = sys.argv[1]
want_overlays = "--overlays" in sys.argv
out_dir = os.path.join(root, "plot_boxes")
os.makedirs(out_dir, exist_ok=True)
if want_overlays:
    os.makedirs(os.path.join(out_dir, "overlays"), exist_ok=True)

QA_DIR = os.path.expanduser("~/astro_sky_image_vqa/VQA_realskyimages/qa_jsons")
IMG_DIR = os.path.join(root, "images_nometa")      # what the model was shown


def order_corners(pts):
    """TL, TR, BR, BL for 4 points (image coords, y down)."""
    pts = np.asarray(pts, dtype=float)
    s, d = pts.sum(1), pts[:, 1] - pts[:, 0]
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]])


def line_masks(gray):
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    H, W = gray.shape
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (max(15, W // 8), 1))
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(15, H // 8)))
    hor = cv2.morphologyEx(bw, cv2.MORPH_OPEN, hk)
    ver = cv2.morphologyEx(bw, cv2.MORPH_OPEN, vk)
    # bridge 1-2 px gaps where axis lines meet at the corners
    both = cv2.dilate(cv2.bitwise_or(hor, ver), np.ones((5, 5), np.uint8))
    return hor, ver, both


def near_rectangular(quad, tol_deg=12):
    """All four interior angles within tol of 90 deg (rejects diagonals/trapezoids)."""
    for i in range(4):
        a, b, c = quad[i - 1], quad[i], quad[(i + 1) % 4]
        v1, v2 = a - b, c - b
        cosang = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9)
        if abs(np.degrees(np.arccos(np.clip(cosang, -1, 1))) - 90) > tol_deg:
            return False
    return True


def closed_quads(both, W, H):
    cnts, _ = cv2.findContours(both, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    for c in cnts:
        if cv2.contourArea(c) < 0.05 * W * H:
            continue
        approx = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            q = order_corners(approx.reshape(4, 2))
            if near_rectangular(q):
                out.append(q)
    return out


def photo_region(gray, W, H, ref):
    """Frameless halftone/greyscale panels: the large non-paper region holding the ref pixel.

    Heavy blur fills halftone dots and contour gaps; text paragraphs stay as separate
    blocks. Returns the min-area rectangle (so slight skew is kept) of the component
    containing the reference pixel, or None.
    """
    k = max(15, (min(W, H) // 40) | 1)
    blur = cv2.GaussianBlur(gray, (k, k), 0)
    paper = np.percentile(blur, 95)
    # text blurs to a light grey, a photograph stays darker: a stricter threshold and a
    # small closing keep captions/running heads from merging into the panel
    mask = (blur < paper - 45).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((k // 2, k // 2), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((k // 3 | 1, k // 3 | 1), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask)
    rx, ry = int(np.clip(ref[0], 0, W - 1)), int(np.clip(ref[1], 0, H - 1))
    i = lab[ry, rx]
    if i == 0 or stats[i, cv2.CC_STAT_AREA] < 0.05 * W * H:
        return None
    pts = np.column_stack(np.where(lab == i))[:, ::-1].astype(np.float32)
    (_, _), (_, _), ang = cv2.minAreaRect(pts)
    # scans are skewed by a degree or two at most; a strongly rotated rectangle means the
    # component is a blob inside a line-drawn plot, not a photographic panel
    if min(abs(ang) % 90, 90 - abs(ang) % 90) > 4:
        return None
    return order_corners(cv2.boxPoints(cv2.minAreaRect(pts)))


def segments(mask, axis):
    """(start, end, position, length) of long ink runs; axis=0 horizontal, 1 vertical."""
    n, _, stats, _ = cv2.connectedComponentsWithStats(mask)
    segs = []
    for x, y, w, h, _ in stats[1:]:
        if axis == 0:
            segs.append((x, x + w, y + h / 2, w))
        else:
            segs.append((y, y + h, x + w / 2, h))
    return sorted(segs, key=lambda s: -s[3])


def box_from_lines(hor, ver, W, H):
    hs, vs = segments(hor, 0), segments(ver, 1)
    if not hs and not vs:
        return None, []
    flags = []
    # two longest horizontal segments that overlap in x and are well separated in y
    top = bot = None
    for i, a in enumerate(hs[:8]):
        for b in hs[i + 1:8]:
            if abs(a[2] - b[2]) > 0.15 * H and min(a[1], b[1]) - max(a[0], b[0]) > 0.5 * min(a[3], b[3]):
                top, bot = sorted([a, b], key=lambda s: s[2]); break
        if top:
            break
    left = right = None
    for i, a in enumerate(vs[:8]):
        for b in vs[i + 1:8]:
            if abs(a[2] - b[2]) > 0.15 * W and min(a[1], b[1]) - max(a[0], b[0]) > 0.5 * min(a[3], b[3]):
                left, right = sorted([a, b], key=lambda s: s[2]); break
        if left:
            break
    if top is None and bot is None and left is None:
        return None, []
    # fill missing sides from the other pair's extent, else the image edge (=> truncated)
    x0 = left[2] if left else (min(top[0], bot[0]) if top else 0)
    x1 = right[2] if right else (max(top[1], bot[1]) if top else W - 1)
    y0 = top[2] if top else (min(left[0], right[0]) if left else 0)
    y1 = bot[2] if bot else (max(left[1], right[1]) if left else H - 1)
    if not left:
        flags.append("no vertical frame pair: left/right from horizontal-line extent or image edge")
    if not top:
        flags.append("no horizontal frame pair: top/bottom from vertical-line extent or image edge")
    return order_corners([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]), flags


def contains(quad, pt):
    return cv2.pointPolygonTest(quad.astype(np.float32).reshape(-1, 1, 2), (float(pt[0]), float(pt[1])), False) >= 0


results = {}
for qf in sorted(glob.glob(os.path.join(QA_DIR, "*_qa.json"))):
    rec = json.loads(json.load(open(qf)))
    vid, src = rec["vqa_id"], rec["source"]
    img_path = os.path.join(IMG_DIR, rec["image"]["stripped_file"])
    gray = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    H, W = gray.shape
    # AVM reference pixel is measured from the BOTTOM-left; convert to top-left image coords
    rx, ry = float(src["wwt"]["x"]), H - float(src["wwt"]["y"])

    hor, ver, both = line_masks(gray)
    cands = [("closed", q, []) for q in closed_quads(both, W, H)]
    if not any(contains(q, (rx, ry)) for _, q, _ in cands):
        q = photo_region(gray, W, H, (rx, ry))
        if q is not None:
            cands = [c for c in cands if not contains(c[1], (rx, ry))] + [("photo", q, [])]
        else:
            q, fl = box_from_lines(hor, ver, W, H)
            if q is not None:
                cands.append(("lines", q, fl))

    flags = []
    if not cands:
        quad, method = order_corners([[0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]]), "fallback_full_image"
        flags.append("no frame found: proposal is the whole image")
    else:
        inside = [c for c in cands if contains(c[1], (rx, ry))]
        # the inner and outer edge of one thick axis line give two near-identical quads;
        # collapse candidates whose corners all agree to within 3% of the image size
        uniq = []
        for c in sorted(inside, key=lambda c: -cv2.contourArea(c[1].astype(np.float32))):
            if not any(np.all(np.abs(c[1] - u[1]) < 0.03 * max(W, H)) for u in uniq):
                uniq.append(c)
        inside = uniq
        pool = inside or cands
        if not inside:
            flags.append("AVM reference pixel is outside every candidate frame")
        # largest candidate that contains the reference pixel (the panel that was solved)
        method, quad, fl = max(pool, key=lambda c: cv2.contourArea(c[1].astype(np.float32)))
        flags += fl
        if len(inside) > 1:
            flags.append(f"{len(inside)} nested candidate frames contain the reference pixel -- check the right one was picked")

    edge = 3
    if (quad[:, 0].min() <= edge or quad[:, 1].min() <= edge or
            quad[:, 0].max() >= W - 1 - edge or quad[:, 1].max() >= H - 1 - edge):
        flags.append("frame touches the image edge: plot may be truncated by the crop")
    area_frac = cv2.contourArea(quad.astype(np.float32)) / (W * H)
    if area_frac > 0.9:
        flags.append(f"frame covers {area_frac:.0%} of the image (no margins detected?)")

    results[vid] = {
        "vqa_id": vid, "astroexplorer_id": src["id"], "image": rec["image"]["stripped_file"],
        "width": W, "height": H,
        "corners_xy_topleft": [[round(float(x), 1), round(float(y), 1)] for x, y in quad],
        "corner_order": "TL, TR, BR, BL",
        "method": method, "flags": flags,
        "needs_attention": bool(flags) or method in ("lines", "fallback_full_image"),
        "avm_ref_pixel_topleft": [round(rx, 1), round(ry, 1)],
        "area_fraction": round(area_frac, 3),
    }

    if want_overlays:
        img = cv2.imread(img_path)
        cv2.polylines(img, [quad.astype(np.int32).reshape(-1, 1, 2)], True, (0, 0, 255), max(2, W // 300))
        cv2.circle(img, (int(rx), int(ry)), max(6, W // 120), (255, 0, 0), -1)
        s = 600 / max(W, H)
        cv2.imwrite(os.path.join(out_dir, "overlays", vid + ".jpg"), cv2.resize(img, (int(W * s), int(H * s))))

json.dump(results, open(os.path.join(out_dir, "auto_boxes.json"), "w"), indent=1)
from collections import Counter
print("figures:", len(results))
print("methods:", dict(Counter(r["method"] for r in results.values())))
print("needs attention:", sum(r["needs_attention"] for r in results.values()))

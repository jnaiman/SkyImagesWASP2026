"""Turn reviewed plot boxes (Label Studio JSON export) into plot-region ground truth.

For each published figure this keeps the full detail -- the 4 reviewed corners (image
pixels, origin top-left, TL/TR/BR/BL), the reviewer's flags and notes, and whether the
box was reviewed or is still the detector's proposal -- and derives the quantities below.
A reviewed figure whose box was DELETED, or that carries an "exclude" flag, is kept in the
output with exclude=True and an exclude_reason, and must be dropped from the analysis.

Derived quantities:

  * plot_box_rect_px      axis-aligned bounding rectangle of the corners [x0, y0, x1, y1]
  * field_width_arcmin    angular length of the box along RA: mean of the top and bottom
                          edges, each measured on the sky through the AVM astrometry
  * field_height_arcmin   same along Dec: mean of the left and right edges
  * pixel_scale_arcsec    arcsec per pixel of the image the model saw (the AVM scale)
  * center_radec_deg      J2000 RA/Dec of the box centre (mean of the corners, via the WCS)

Edge lengths go through a TAN WCS built from the AVM/WWT parameters (scale arcsec/px,
reference pixel from the bottom-left, rotation = east-of-north + 180), so a skewed box
is measured correctly rather than as width x scale.

Usage:
  ~/.venvs/plotbox/bin/python apply_plot_boxes.py <real_data_dir> <label_studio_export.json>
Writes <real_data_dir>/plot_boxes/reviewed_boxes.json. Nothing in the released VQA
files is changed; folding these into VQA_realskyimages is a separate step.
"""
import glob, json, os, sys
from collections import Counter
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.wcs import WCS
import astropy.units as u

root, export_path = os.path.abspath(sys.argv[1]), sys.argv[2]
QA_DIR = os.path.expanduser("~/astro_sky_image_vqa/VQA_realskyimages/qa_jsons")
records = {}
for f in glob.glob(os.path.join(QA_DIR, "*_qa.json")):
    r = json.loads(json.load(open(f)))
    records[r["vqa_id"]] = r


def wcs_for(src, H):
    w = src["wwt"]
    scale = float(w["scale"]) / 3600.0
    pa = np.deg2rad(float(w.get("rotation", 180.0)) - 180.0)
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crval = [float(w["ra"]), float(w["dec"])]
    wcs.wcs.crpix = [float(w["x"]) + 0.5, float(w["y"]) + 0.5]        # FITS, bottom-left origin
    wcs.wcs.cd = [[-scale * np.cos(pa), scale * np.sin(pa)], [scale * np.sin(pa), scale * np.cos(pa)]]
    return wcs


def sky(wcs, H, pt):
    x, y = pt                                    # top-left image pixel coords
    ra, dec = wcs.all_pix2world([[x + 0.5, H - y + 0.5]], 1)[0]
    return SkyCoord(ra * u.deg, dec * u.deg)


def pick_result(task):
    """(polygon result, choices, notes, status) -- latest non-cancelled annotation, else prediction."""
    anns = [a for a in task.get("annotations", []) if not a.get("was_cancelled")]
    if anns:
        res, status = sorted(anns, key=lambda a: a.get("updated_at") or "")[-1]["result"], "reviewed"
    elif task.get("predictions"):
        res, status = task["predictions"][0]["result"], "unreviewed (detector proposal)"
    else:
        return None, [], "", "missing"
    poly = next((x for x in res if x["type"] == "polygonlabels"), None)
    choices = sum((x["value"].get("choices", []) for x in res if x["type"] == "choices"), [])
    notes = " ".join(sum((x["value"].get("text", []) for x in res if x["type"] == "textarea"), []))
    return poly, choices, notes, status


out, status_count = {}, Counter()
for task in json.load(open(export_path)):
    vid = task["data"]["vqa_id"]
    rec = records[vid]
    W, H = rec["image"]["width"], rec["image"]["height"]
    poly, choices, notes, status = pick_result(task)
    status_count[status] += 1
    entry = {"vqa_id": vid, "astroexplorer_id": rec["source"]["id"], "status": status,
             "flags": choices, "notes": notes, "image_size_px": [W, H]}
    if poly is None:
        # A reviewed figure whose box was deleted is a deliberate rejection (e.g. the crop
        # cuts the plot badly): keep the record, but exclude it from the analysis.
        if status == "reviewed":
            entry.update({"exclude": True,
                          "exclude_reason": "box deleted by reviewer" + (" (" + "; ".join(choices) + ")" if choices else "")})
        else:
            entry.update({"exclude": True, "exclude_reason": "no box available (" + status + ")"})
        out[vid] = entry
        continue
    pts = np.array([[p[0] * W / 100.0, p[1] * H / 100.0] for p in poly["value"]["points"]])
    if len(pts) != 4:
        entry["warning"] = f"polygon has {len(pts)} points; using its bounding rectangle"
        x0, y0 = pts.min(0); x1, y1 = pts.max(0)
        pts = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
    s, d = pts.sum(1), pts[:, 1] - pts[:, 0]               # order TL, TR, BR, BL
    tl, tr, br, bl = pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]
    wcs = wcs_for(rec["source"], H)
    c = {k: sky(wcs, H, p) for k, p in (("tl", tl), ("tr", tr), ("br", br), ("bl", bl))}
    cen = sky(wcs, H, pts.mean(0))                         # sky position of the box centre
    width = 0.5 * (c["tl"].separation(c["tr"]) + c["bl"].separation(c["br"])).to(u.arcmin).value
    height = 0.5 * (c["tl"].separation(c["bl"]) + c["tr"].separation(c["br"])).to(u.arcmin).value
    entry.update({
        "corners_xy_topleft": [[round(float(v), 1) for v in p] for p in (tl, tr, br, bl)],
        "corner_order": "TL, TR, BR, BL",
        "plot_box_rect_px": [round(float(v), 1) for v in (*pts.min(0), *pts.max(0))],
        "field_width_arcmin": round(float(width), 4),
        "field_height_arcmin": round(float(height), 4),
        "pixel_scale_arcsec": round(float(rec["source"]["wwt"]["scale"]), 6),
        "center_radec_deg": [round(float(cen.ra.deg % 360.0), 6), round(float(cen.dec.deg), 6)],
        "full_image_field_arcmin": [round(W * float(rec["source"]["wwt"]["scale"]) / 60, 4),
                                    round(H * float(rec["source"]["wwt"]["scale"]) / 60, 4)],
        "exclude": any("exclude" in ch for ch in choices),
    })
    if entry["exclude"]:
        entry["exclude_reason"] = "flagged by reviewer: " + "; ".join(ch for ch in choices if "exclude" in ch)
    out[vid] = entry

dst = os.path.join(root, "plot_boxes", "reviewed_boxes.json")
json.dump(out, open(dst, "w"), indent=1)
ratio = [e["field_height_arcmin"] / e["full_image_field_arcmin"][1] for e in out.values() if "field_height_arcmin" in e]
print(f"wrote {len(out)} boxes -> {dst}")
print("status:", dict(status_count))
excl = [e for e in out.values() if e.get("exclude")]
print(f"excluded from analysis: {len(excl)}")
for e in excl:
    print(f"   {e['vqa_id']}: {e['exclude_reason']}")
print(f"plot-box height / full-image height: median {np.median(ratio):.2f} (range {min(ratio):.2f}-{max(ratio):.2f})")

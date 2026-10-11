"""Record the plot-box review (kept boxes AND exclusions) in the metadata, in both places.

  real_data/metadata/<astroexplorer_id>.json   + "plot_box_review" block (all 163 figures)
  real_data/index.csv                           + analysis_status / analysis_exclude_reason columns
  astro_sky_image_vqa/VQA_realskyimages/selection_manifest.json
        one entry per scraped figure (163): analysis status, reason if excluded, the
        astrometry-check result, and the human-verified plot box (corners etc.) when reviewed.

analysis_status values:
  included                      -> in VQA_realskyimages (104)
  excluded_plot_box_review      -> human reviewer deleted the box / flagged exclude (52)
  excluded_astrometry_check     -> marginal_correctness=true, never reviewed (7)

Usage: python3 record_plot_box_metadata.py <real_data_dir> [<dataset_dir>]   (idempotent)
"""
import csv, glob, json, os, sys
from collections import Counter

real = os.path.abspath(sys.argv[1])
ds = os.path.expanduser(sys.argv[2] if len(sys.argv) > 2 else "~/astro_sky_image_vqa")
boxes = json.load(open(os.path.join(real, "plot_boxes", "reviewed_boxes.json")))
by_aid = {b["astroexplorer_id"]: b for b in boxes.values()}

manifest, status_count = [], Counter()
for f in sorted(glob.glob(os.path.join(real, "metadata", "*.json"))):
    m = json.load(open(f))
    aid = m["id"]
    b = by_aid.get(aid)
    if m["astrometry_check"]["marginal_correctness"]:
        status, reason = "excluded_astrometry_check", "; ".join(m["astrometry_check"]["reasons"])
    elif b is None:
        raise RuntimeError(f"{aid} passed the astrometry check but has no plot-box review")
    elif b.get("exclude"):
        status, reason = "excluded_plot_box_review", b.get("exclude_reason", "")
    else:
        status, reason = "included", ""
    review = None
    if b is not None:
        review = {k: b.get(k) for k in (
            "vqa_id", "status", "flags", "notes", "corners_xy_topleft", "corner_order",
            "plot_box_rect_px", "field_width_arcmin", "field_height_arcmin", "center_radec_deg",
            "pixel_scale_arcsec", "full_image_field_arcmin", "image_size_px")}
        review["coordinates"] = "image pixels of images_nometa/<vqa_id>.jpeg, origin top-left"
        review["method"] = "OpenCV first pass (detect_plot_box.py), human verified in Label Studio"
    m["plot_box_review"] = {"analysis_status": status, "exclude_reason": reason, "box": review}
    json.dump(m, open(f, "w"), indent=1)
    status_count[status] += 1
    manifest.append({"astroexplorer_id": aid, "vqa_id": b["vqa_id"] if b else None,
                     "title": m["title"], "citation": m["citation"], "doi": m["doi"],
                     "analysis_status": status, "exclude_reason": reason,
                     "astrometry_check": {k: m["astrometry_check"][k] for k in ("marginal_correctness", "reasons", "notes")},
                     "plot_box": review})

# index.csv: add/refresh two columns
idx_path = os.path.join(real, "index.csv")
rows = list(csv.DictReader(open(idx_path)))
st = {e["astroexplorer_id"]: e for e in manifest}
for r in rows:
    r["analysis_status"] = st[r["id"]]["analysis_status"]
    r["analysis_exclude_reason"] = st[r["id"]]["exclude_reason"]
with open(idx_path, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

out = os.path.join(ds, "VQA_realskyimages", "selection_manifest.json")
json.dump({"description": "Every AstroExplorer 'Images with astrometry' figure that was scraped (163), "
                          "whether it is used in VQA_realskyimages, why not if excluded, and the "
                          "human-verified plot box where one was reviewed.",
           "counts": dict(status_count), "figures": manifest}, open(out, "w"), indent=1)
print(dict(status_count), "->", out)

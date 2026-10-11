"""Fold the human-verified plot boxes into the released real-sky dataset.

Run after scripts/apply_plot_boxes.py. For astro_sky_image_vqa/:

  * EXCLUDED figures (box deleted by the reviewer, or an exclude flag): delete
    VQA_realskyimages/qa_jsons/<id>_qa.json and every
    LMM_outputs_realskyimages/<model>/<id>_qa.pickle. (The repo is under git, so
    `git checkout -- <path>` restores them.)
  * KEPT figures: ground truth re-derived from the plot box --
        field width / field height       angular size of the verified plot box
        center right ascension / declination   sky position of the box centre
        pixel scale                       unchanged (arcsec per image pixel)
    The previous full-image values are kept in source['ground_truth_full_image'],
    and the box itself (corners, rectangle, reviewer flags/notes) in source['plot_box'].

The model-answer pickles are NOT rewritten (they hold vendor SDK objects), so their stored
'A' is the old full-image truth: score real-sky answers against the qa_jsons, as
mean_med_calcs_figure_realsky.ipynb does.

Usage: python3 update_realsky_dataset.py <real_data_dir> [<dataset_dir>]   (idempotent)
"""
import glob, json, os, sys

real_data = os.path.abspath(sys.argv[1])
ds = os.path.expanduser(sys.argv[2] if len(sys.argv) > 2 else "~/astro_sky_image_vqa")
qa_dir = os.path.join(ds, "VQA_realskyimages", "qa_jsons")
boxes = json.load(open(os.path.join(real_data, "plot_boxes", "reviewed_boxes.json")))

# question name in the qa_json -> key in reviewed_boxes.json (index for 2-vectors)
NEW_TRUTH = {
    "field width": ("field_width_arcmin", None, 4),
    "field height": ("field_height_arcmin", None, 4),
    "center right ascension": ("center_radec_deg", 0, 6),
    "center declination": ("center_radec_deg", 1, 6),
}

removed, updated, already = [], 0, 0
for vid, b in sorted(boxes.items()):
    qa_path = os.path.join(qa_dir, vid + "_qa.json")
    if b.get("exclude"):
        hits = [qa_path] + glob.glob(os.path.join(ds, "LMM_outputs_realskyimages", "*", vid + "_qa.pickle"))
        for h in hits:
            if os.path.exists(h):
                os.remove(h)
                removed.append(os.path.relpath(h, ds))
        continue
    if not os.path.exists(qa_path):
        raise FileNotFoundError(f"{vid} is kept but {qa_path} is missing")
    rec = json.loads(json.load(open(qa_path)))
    if "plot_box" in rec["source"]:
        already += 1
        continue
    full = {}
    for lvl in rec["VQA"].values():
        for qs in lvl.values():
            for name, e in qs.items():
                if name in NEW_TRUTH:
                    key, idx, nd = NEW_TRUTH[name]
                    val = b[key] if idx is None else b[key][idx]
                    full[name] = e["A"][name]
                    e["A"] = {name: round(float(val), nd)}
    rec["source"]["ground_truth_full_image"] = full
    rec["source"]["plot_box"] = {
        "corners_xy_topleft": b["corners_xy_topleft"], "corner_order": b["corner_order"],
        "rect_px": b["plot_box_rect_px"], "field_width_arcmin": b["field_width_arcmin"],
        "field_height_arcmin": b["field_height_arcmin"], "center_radec_deg": b["center_radec_deg"],
        "reviewer_flags": b["flags"], "reviewer_notes": b["notes"], "status": b["status"],
        "method": "OpenCV first pass (detect_plot_box.py), human verified in Label Studio",
    }
    with open(qa_path, "w") as f:
        json.dump(json.dumps(rec), f)
    updated += 1

left = len(glob.glob(os.path.join(qa_dir, "*_qa.json")))
print(f"updated {updated} records ({already} already had a plot box); removed {len(removed)} files")
print(f"qa_jsons now: {left}")
for d in sorted(glob.glob(os.path.join(ds, "LMM_outputs_realskyimages", "*"))):
    print(f"  {os.path.basename(d)}: {len(glob.glob(os.path.join(d, '*_qa.pickle')))} pickles")

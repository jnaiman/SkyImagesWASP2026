"""Turn plot_boxes/auto_boxes.json into Label Studio tasks with editable pre-annotations.

Each task shows the stripped image (what the model saw) with the detector's 4-corner
polygon pre-placed; drag corners to fix, tick flags, Submit.

Usage: python make_tasks.py <real_data_dir>
Writes <real_data_dir>/plot_boxes/label_studio_tasks.json
Images are served by Label Studio's local-file storage, rooted at <real_data_dir>.
"""
import json, os, sys

root = os.path.abspath(sys.argv[1])
boxes = json.load(open(os.path.join(root, "plot_boxes", "auto_boxes.json")))
MODEL_VERSION = "detect_plot_box_v1"   # must match setup_project.py

tasks = []
for vid, b in sorted(boxes.items()):
    W, H = b["width"], b["height"]
    pts = [[100.0 * x / W, 100.0 * y / H] for x, y in b["corners_xy_topleft"]]   # LS uses % of image
    info = (f"{vid} | detector: {b['method']}"
            + (" | NEEDS ATTENTION: " + "; ".join(b["flags"]) if b["flags"] else "")
            + " | blue dot in overlays = AVM reference pixel " + str(b["avm_ref_pixel_topleft"]))
    tasks.append({
        "data": {
            "image": "/data/local-files/?d=images_nometa/" + b["image"],
            "vqa_id": vid,
            "astroexplorer_id": b["astroexplorer_id"],
            "title": vid + ("   [check carefully]" if b["needs_attention"] else ""),
            "info": info,
        },
        "predictions": [{
            "model_version": MODEL_VERSION,      # one version, so LS can pre-label from it
            "score": 0.5 if b["needs_attention"] else 0.9,
            "result": [{
                "id": "auto_" + vid,
                "from_name": "box", "to_name": "image", "type": "polygonlabels",
                "original_width": W, "original_height": H, "image_rotation": 0,
                "value": {"points": pts, "closed": True, "polygonlabels": ["plot box"]},
            }],
        }],
    })

out = os.path.join(root, "plot_boxes", "label_studio_tasks.json")
json.dump(tasks, open(out, "w"), indent=1)
print(f"wrote {len(tasks)} tasks -> {out}")

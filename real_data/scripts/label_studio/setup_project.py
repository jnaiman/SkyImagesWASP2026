"""Create the plot-box review project in a running local Label Studio (run once).

Creates the project with label_config.xml, attaches a local-file storage pointing at
real_data/images_nometa (so the images can be served), and imports the pre-annotated
tasks from plot_boxes/label_studio_tasks.json. Safe to re-run: it skips an existing project.

Usage: ~/.venvs/plotbox/bin/python setup_project.py <real_data_dir>
"""
import json, os, sys
import requests

root = os.path.abspath(sys.argv[1])
here = os.path.dirname(os.path.abspath(__file__))
cred = dict(l.strip().split("=", 1) for l in open(os.path.expanduser("~/.labelstudio_plotbox/credentials.env")) if "=" in l)
url = f"http://localhost:{cred['LS_PORT']}"
hdr = {"Authorization": "Token " + cred["LS_TOKEN"]}
TITLE = "Plot boxes (AstroExplorer published figures)"

existing = requests.get(f"{url}/api/projects", headers=hdr, params={"page_size": 100}).json()
existing = existing.get("results", existing) if isinstance(existing, dict) else existing
proj = next((p for p in existing if p["title"] == TITLE), None)
if proj:
    print(f"project already exists (id {proj['id']}, {proj.get('task_number')} tasks) -- nothing to do")
    sys.exit(0)

proj = requests.post(f"{url}/api/projects", headers=hdr, json={
    "title": TITLE,
    "description": "Drag the 4 corners onto the plot (axis) frame; tick flags; Submit. "
                   "Pre-annotations come from scripts/detect_plot_box.py.",
    "label_config": open(os.path.join(here, "label_config.xml")).read(),
    "show_collab_predictions": True,     # pre-annotations appear as editable regions
    "model_version": "detect_plot_box_v1",   # pre-label from these predictions (matches make_tasks.py)
}).json()
pid = proj["id"]

st = requests.post(f"{url}/api/storages/localfiles", headers=hdr, json={
    "project": pid, "title": "images_nometa",
    "path": os.path.join(root, "images_nometa"), "use_blob_urls": True,
})
st.raise_for_status()

tasks = json.load(open(os.path.join(root, "plot_boxes", "label_studio_tasks.json")))
r = requests.post(f"{url}/api/projects/{pid}/import", headers=hdr, json=tasks)
r.raise_for_status()
print(f"project {pid}: imported {r.json().get('task_count')} tasks -> {url}/projects/{pid}/data")

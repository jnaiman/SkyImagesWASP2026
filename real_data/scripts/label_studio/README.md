# Plot-box review for the published (AstroExplorer) figures

**Why this is needed.** The AVM astrometry in each figure was fitted to the axis ticks, so it is correct. But the stored JPEGs are page crops that include running heads, colorbars, captions and sometimes neighbouring text. The real-sky ground truth for `field width` / `field height` was computed as the whole image size × scale, which overstates the plotted region (the median plot box is ~0.66 of the image height). We need the plot (axis) frame of each figure.

## Steps

0. **One-time environment:**
   ```bash
   /opt/anaconda3/bin/python3 -m venv ~/.venvs/plotbox
   ~/.venvs/plotbox/bin/pip install label-studio opencv-python-headless astropy pillow numpy
   ```

1. **Automatic first pass:**
   ```bash
   cd real_data
   ~/.venvs/plotbox/bin/python scripts/detect_plot_box.py . --overlays   # -> plot_boxes/auto_boxes.json (+ overlays/)
   ~/.venvs/plotbox/bin/python scripts/label_studio/make_tasks.py .      # -> plot_boxes/label_studio_tasks.json
   ```
   The detector proposes 4 corners per figure (method `closed` / `photo` / `lines`, see the docstring). `plot_boxes/overlays/` shows each proposal in red, with the AVM reference pixel as a blue dot. A visual check of all 156 found roughly 75–80% correct or nearly so. Tasks titled `[check carefully]` were flagged by the detector (frame touching the image edge, nested frames, no frame found).

2. **Start Label Studio** (local only, no online account):
   ```bash
   bash scripts/label_studio/start_label_studio.sh
   ```
   Open <http://localhost:8089>. The login is created automatically on first run and stored in `~/.labelstudio_plotbox/credentials.env`; the start script also prints it. The database lives in `~/.labelstudio_plotbox/`, outside the repository.

3. **Create the project** (once per machine):
   ```bash
   ~/.venvs/plotbox/bin/python scripts/label_studio/setup_project.py .
   ```

4. **Review.** Open the project and click *Label All Tasks*. For each figure:
   - drag the 4 red corners onto the **plot frame**, i.e. the box the axis ticks sit on, excluding tick labels, colorbars and captions;
   - for a frameless photo with ticks only, use the photo edge;
   - for a multi-panel figure, box the panel that the AVM astrometry belongs to (the panel whose axis values match the target);
   - tick the flags that apply (`auto box correct as-is`, `corners adjusted`, `plot truncated by the image crop`, …) and press *Submit*.

   Keep it as 4 points even if the scan is slightly skewed; the corners are stored exactly.
   - **Badly cropped figure** (the crop cuts the plot so its extent can't be read): **delete the box** (select it, then Backspace), tick `badly cropped: exclude from comparison`, and **Submit**. Use Submit, not *Skip*: a skipped task is treated as unreviewed and keeps the detector's box. `apply_plot_boxes.py` marks any reviewed figure without a box, or with an `exclude` flag, as `exclude: true` (with an `exclude_reason`), and it lists them when it runs. Those figures must be dropped from the real-vs-synthetic comparison.

5. **Export.** Go to *Export → JSON* and save the file as `real_data/plot_boxes/label_studio_export.json`.

6. **Derive the corrected ground truth:**
   ```bash
   ~/.venvs/plotbox/bin/python scripts/apply_plot_boxes.py . plot_boxes/label_studio_export.json
   ```
   This writes `plot_boxes/reviewed_boxes.json`. For each figure it keeps the corners, flags, notes and review status, and gives the plot box's angular width and height, measured along its edges through the AVM WCS (so skew is handled). It does **not** modify `VQA_realskyimages`; updating that ground truth and re-scoring Gemini's existing answers is the next step (no new API calls are needed).

## Moving to another computer

The Label Studio database is per machine. On a new machine, do step 0, then steps 2–3. If you have not finished reviewing, also export first on the old machine. You can then re-import your partial work by importing the export JSON into the new project (*Import*), or just continue on the old machine.

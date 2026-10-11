# real_data -- the published-figure comparison set

Code that builds `VQA_realskyimages/` in the
[dataset](https://huggingface.co/datasets/ReadingTimeMachine/astro_sky_image_vqa):
104 sky figures from published journal articles, with ground truth taken from
the astrometry embedded in each image. It downloads the AAS Astronomy Image
Explorer (AstroExplorer) figures tagged "Images with astrometry", checks that
astrometry, and locates the plotted region of every figure by a human-verified
plot box.

**163 → 156 → 104.** The automated astrometry check removes 7 figures, and the
plot-box review removes 52 more. The dataset's
[`VQA_realskyimages/README.md`](https://huggingface.co/datasets/ReadingTimeMachine/astro_sky_image_vqa/blob/main/VQA_realskyimages/README.md)
gives the exclusion criteria and the stored fields; this file covers how to
re-run the pipeline.

## No images or working data in this repo

The figures are under the journals' copyright, so this folder holds code only.
Running the pipeline creates the data alongside `scripts/` -- `images/`,
`images_nometa/`, `metadata/`, `details_html/`, `index.csv`, `plot_boxes/`, ... --
and `.gitignore` keeps all of it out of git.

## Pipeline

Run from this folder (`real_data/`), in order. Paths default to
`~/astro_sky_image_vqa` for the dataset; each script's docstring gives its
arguments.

| Step | Script | What it does |
|---|---|---|
| 1 | `scripts/ae_download.py scripts/ids.txt .` | Downloads the 163 hi-res JPEGs (AVM metadata in their XMP header) and parses the metadata into `metadata/<id>.json` and `index.csv`. `ids.txt` lists the AstroExplorer ids. |
| 2 | `scripts/wwt_check.py . <id> ...` | Optional spot check: rebuilds each image's WorldWide Telescope link and predicts its sky footprint. |
| 3 | `scripts/astrometry_check.py .` | **Automated astrometry check.** Flags `marginal_correctness` when the object named in the title (resolved through SIMBAD/Sesame) is far outside the field, the coordinates are copied from another article, or the field is too wide for one TAN projection. 7 figures are flagged. |
| 4 | `../create_vqa_from_datas_realsky.ipynb` | Builds `VQA_realskyimages/` (questions and astrometric ground truth) from the 156 unflagged figures, and the metadata-stripped `images_nometa/` sent to the model. Set `real_data_dir` in its config cell to this folder. |
| 5 | `../models/test_models/gemini_withapi_realskyimages.ipynb` | Asks Gemini the questions. |
| 6 | `scripts/detect_plot_box.py . --overlays` | **Plot-box proposal.** OpenCV first pass for the axis frame of each figure, as 4 corners. |
| 7 | `scripts/label_studio/` | **Human verification** in a local Label Studio: every proposal accepted, corrected or deleted. See [`scripts/label_studio/README.md`](scripts/label_studio/README.md). |
| 8 | `scripts/apply_plot_boxes.py . plot_boxes/label_studio_export.json` | Turns the reviewed corners into angular width and height (edge lengths through the AVM TAN WCS) and the box centre; marks deleted boxes `exclude`. |
| 9 | `scripts/update_realsky_dataset.py .` | Folds the reviewed boxes into `VQA_realskyimages/`: drops the 52 excluded figures, and re-derives the kept figures' ground truth from their box. |
| 10 | `scripts/record_plot_box_metadata.py .` | Writes `selection_manifest.json` (all 163 figures: kept or excluded, why, and the box) and records the review in the local metadata. |

Steps 6–10 need the environment in `scripts/label_studio/README.md` (Label
Studio, OpenCV, astropy); steps 1–3 need only astropy and the standard library.

## What the analysis uses

Gemini's answers are scored against the released qa_jsons -- not the stored
run pickles, whose ground truth predates the plot-box review -- in
`models/figure_notebooks/mean_med_calcs_figure_realsky.ipynb` (Fig. 4) and
`models/figure_notebooks/stats_tests.ipynb`. `models/figure_notebooks/question_tables.ipynb`
generates the published-figure question table and checks that the released
widths reproduce from the stored box corners.

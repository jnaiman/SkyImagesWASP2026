# SkyImagesWASP2026

Synthetic astronomical figure generation, narrowed to the two plot types this
project needs: **`contour`** and **`image of the sky`**.

Each generated figure is saved as a raster image plus a JSON record of every
bounding box in it (plot area, axes, tick labels, titles, x/y labels, colorbar,
colorbar label) and the data behind the plot — i.e. labelled training data for
figure/figure-element detection.

The code is ported from
[`~/ArXiv_figure_injection`](file:///Users/jnaiman/ArXiv_figure_injection): the
plotting machinery is the newer `make_random_plot` / `FigureRun` architecture
that lives inside `create_inject_figures_and_PDFmine_OCR_batch.py`, driven by a
standalone batch script in the style of the older
`synthetic_training_figures/create_figures_batch.py`. Nothing from the ArXiv
mining, figure injection, PDF mining or OCR halves of that pipeline came along.

---

## Quick start

```bash
conda env create -f environment.yml
conda activate SkyImages
python -m spacy download en_core_web_sm
python -c "import nltk; nltk.download('stopwords')"

./fetch_resources.sh                 # populate resources/ (see below)

# serial
python create_figures_batch.py -save_dir ./synthetic_figures/ -number_of_figures 20

# parallel
mpirun -np 4 python create_figures_batch.py \
    -save_dir ./synthetic_figures/ -number_of_figures 700 -nProcs 4
```

A working LaTeX (`pdflatex`, with `amsmath` and `amssymb`) must be on `$PATH` —
matplotlib runs with `text.usetex=True`. macOS's `/Library/TeX/texbin` is added
automatically if present; elsewhere pass `-texbin`.

### Output

Every successful figure writes four files under `-save_dir`:

```
imgs/Picture_000001.jpeg       the figure
jsons/Picture_000001.json      every bounding box + the data behind the plot
pickles/Picture_000001.pickle  the same, unserialised
diags/Picture_000001.jpeg      the figure with the boxes drawn on it
```

Re-running skips any index that already has both an image and a JSON; pass
`-restart 1` to regenerate.

### The knobs that matter

| flag | default | |
|---|---|---|
| `-save_dir` | *(Dropbox path)* | where `imgs/`, `jsons/`, `pickles/`, `diags/` go |
| `-number_of_figures` | 700 | |
| `-nProcs` | 2 | work-chunk count handed to `yt`'s `parallel_objects` |
| `-plot_types` | `contour,image of the sky` | comma-separated subset; pass one to generate only that kind |
| `-sky_source` | `both` | `astroquery` = real SkyView cutouts, `gmm` = synthetic gaussian-mixture sky, `both` = a mix |
| `-panel_median` / `-panel_max` | 4 / 25 | panels per figure; `-panel_median 1 -panel_max 2` for fast single-panel debugging |
| `-resources_dir` | *(see below)* | the static lookup tables |
| `-astroquery_img_dir` | *(Dropbox path)* | cache of downloaded SkyView `.fits` |
| `-max_tries` | 50 | attempts per figure before every parameter is re-randomised |
| `-time_out` | 5 | per-stage timeout, minutes |
| `-grace_ticks` | 5 | tick labels allowed to overlap before a figure is rejected |
| `-save_diagnostic_plot` | 1 | write `diags/` |

Only `-plot_types` and `-sky_source` are new; the rest carry over from the
upstream batch script.

### Resources

The generator reads several corpus-derived lookup tables (fonts, the noun and
inline-math pools for labels, and the object/wavelength pool that
`image of the sky` draws real targets from). They are data, not code, so they
are not tracked here — `./fetch_resources.sh` copies them from a local
`ArXiv_figure_injection` checkout. See [resources/README.md](resources/README.md)
for what each one is.

Resolution order: `-resources_dir` → `$SKYFIGS_RESOURCES` → `resources/`.

---

## How a figure gets made

`create_figures_batch.py` builds the probability tables once, then calls
`skyfigs.main_plot_utils.make_random_plot` per figure. That function is a retry
loop: it samples parameters, builds the figure stage by stage, and on any
failure resets whatever went wrong and starts the stage again — so most of its
bulk is error recovery, not plotting.

```
create_figures_batch.py
  └── make_plotplotparams()            skyfigs/plot_params_setup.py
  └── make_random_plot()               skyfigs/main_plot_utils.py
        │   ... reset_figure() -> FigureRun()   skyfigs/figure_class.py
        │       holds every parameter, RNG and partial result for one figure
        │
        ├── make_base_plot()           the blank figure: size, dpi, style, panel grid
        ├── get_plot_data()            pick plot type + distribution, sample data
        │     └── get_data()                     skyfigs/utils/data_utils.py
        │           get_contour_data() / get_image_of_the_sky_data()
        │             └── get_gmm_data(), get_sky_image_data()
        │                                        skyfigs/utils/distribution_utils.py
        ├── generate_data()            draw it -> make_plot() / get_image_of_the_sky_plot()
        │                                        skyfigs/utils/plot_utils.py
        ├── add_titles_and_labels()    random nouns / inline math, or RA-DEC pairs
        │                                        skyfigs/utils/synthetic_fig_utils.py
        ├── parse_colorbar_data()      colorbar + its label
        ├── flip_colors()              optionally invert text vs. face colour
        ├── fill_datas()               pixel coordinates of every element
        │     └── get_data_pixel_locations()     skyfigs/utils/figure_gen_utils/
        ├── checks                     aspect ratio, labels off-page, overlapping
        │                              boxes, plot-area fraction
        │                                        skyfigs/utils/plot_check_utils.py
        └── close_plot_success()       write the image, json, pickle and diagnostic
```

The two plot types differ mainly in where the underlying array comes from and
what the axes are:

- **`contour`** — a gaussian-mixture / random / linear field on a plain x-y
  grid, drawn as filled image, contour lines, or both. Axis labels are random
  nouns and inline math.
- **`image of the sky`** — the same, but on WCS axes with RA/DEC tick labels and
  an epoch (`J2000`, `(B1950)`, ...). The array is either a real SkyView cutout
  (`-sky_source astroquery`: a random object+wavelength is drawn from
  `object_wavelength_pairs.pickle`, mapped to a survey by
  `distribution_utils.surveys_by_wl`, queried through astroquery and cached as
  `.fits`) or a synthetic gaussian-mixture sky at a random centre and scale
  (`-sky_source gmm`).

---

## Provenance

Everything below is a copy from `~/ArXiv_figure_injection`. Filenames are
unchanged except where noted, so that changes can still be diffed back.

### New in this repo

| file | |
|---|---|
| `create_figures_batch.py` | standalone batch driver. Same role as `synthetic_training_figures/create_figures_batch.py`, but built on the newer `make_random_plot` rather than that script's inlined loop, and restricted to two plot types |
| `skyfigs/paths.py` | resolves the resources directory (was hard-coded to `~/ArXiv_figure_injection/resources/` in three places) |
| `skyfigs/__init__.py`, `fetch_resources.sh`, `environment.yml`, `.gitignore` | |

### Copied

| here | from |
|---|---|
| `skyfigs/main_plot_utils.py` | `utils/main_plot_utils.py` |
| `skyfigs/figure_class.py` | `utils/figure_class.py` |
| `skyfigs/plot_params_setup.py` | `utils/misc_plot_utils.py` (`make_plotplotparams`) |
| `skyfigs/utils/figure_build_utils.py` | `synthetic_training_figures/utils/tmp_port_from_script.py` **(renamed)** |
| `skyfigs/utils/plot_parameters.py` | `synthetic_training_figures/utils/plot_parameters.py` |
| `skyfigs/utils/plot_classes_utils.py` | `synthetic_training_figures/utils/plot_classes_utils.py` |
| `skyfigs/utils/data_utils.py` | `synthetic_training_figures/utils/data_utils.py` |
| `skyfigs/utils/distribution_utils.py` | `synthetic_training_figures/utils/distribution_utils.py` |
| `skyfigs/utils/synthetic_fig_utils.py` | `synthetic_training_figures/utils/synthetic_fig_utils.py` |
| `skyfigs/utils/plot_utils.py` | `synthetic_training_figures/utils/plot_utils.py` |
| `skyfigs/utils/plot_check_utils.py` | `synthetic_training_figures/utils/plot_check_utils.py` |
| `skyfigs/utils/text_utils.py` | `synthetic_training_figures/utils/text_utils.py` |
| `skyfigs/utils/figure_gen_utils/` | `synthetic_training_figures/utils/figure_gen_utils/` (`misc.py`, `pixel_location_utils.py`) |
| `skyfigs/utils/metric_utils/utilities.py` | `synthetic_training_figures/utils/metric_utils/utilities.py` |
| `skyfigs/utils/TexSoupUtils/` | `synthetic_training_figures/utils/TexSoupUtils/` (`preprocessing.py`, `postprocess.py`) |
| `yt/` | `yt/` — stripped-down copy of yt's MPI helpers (`parallel_objects`, `is_root`). Not a real yt install |
| `resources/fonts.csv` | `resources/fonts.csv` |

### Changes made to the copied files

Kept deliberately small.

1. **Import rewiring.** The two packages were mutually dependent upstream
   (`tmp_port_from_script.py` imported `utils.figure_class`, which imported back
   into `synthetic_training_figures.utils`); they are now one package, so those
   are relative imports.
2. **`plot_params_setup.py` builds only `contour` and `image of the sky`.** The
   scatter / line / histogram blocks of `make_plotplotparams` are gone. Plot
   type is chosen from the keys of this dict (`get_plot_data`), so dropping the
   keys is what restricts generation. It also takes arguments for what used to
   be edited in place — plot-type weights, panel counts, and the astroquery
   paths — and `-sky_source` maps onto its `sky_from_astroquery_prob` /
   `sky_from_gmm_prob`.
3. **`data_utils.py`: `FitzNumpyEncoder` and `fitz_object_hook` removed.** They
   serialise PyMuPDF geometry produced by the PDF-mining half of the upstream
   pipeline; nothing in figure generation emits fitz objects. This drops PyMuPDF
   from the dependency set (it also segfaulted on import under MPI on macOS).
4. **`main_plot_utils.py`, two guards.**
   - `allow_sky_image=False` no longer raises `KeyError` when `plot_params` was
     built without the sky type in the first place.
   - The `kwargs['figure_params'][...]` write-back after `make_base_plot` is
     skipped when no `figure_params` was passed in. Injection pins the figure to
     a box on a page and needs those fed back to every reset; standalone
     generation passes none and wants a freshly randomised figure each time.
     Without the guard this raises `KeyError: 'figure_params'` on the first
     attempt and loops forever.

5. **`figure_class.py`: `reset_figure` passes `fullproc_r` to the `FigureRun`
   constructor.** Upstream it built `FigureRun()` with no arguments and patched
   attributes in afterwards, so the resources dir a caller passed arrived too
   late to affect where fonts, nouns and inline math were read from.

The shared plotting machinery (`plot_utils.py`, `data_utils.py`,
`synthetic_fig_utils.py`, ...) is copied **whole**, including the scatter, line
and histogram branches. Those branches are unreachable with the params above,
but they interleave with the contour/sky code throughout, and pruning them
line-by-line would risk more than it saves.

### Deliberately not copied

ArXiv mining (`arxiv_mining_synthetic_data/`), figure injection into paper pages
(`utils/generate_inject_utils.py`, `subfig_gen_utils.py`, `translation_utils.py`,
`annotation_utils_translate.py`, `page_coord_utils.py`), PDF mining
(`classify_pdf_figure_page_utils.py`, `figure_element_classifier.py`,
`rectangle_finding_utils.py`), all OCR engines (`ocr_helpers.py`,
`extra_ocr_helpers.py`, `{rapidocr,doctr,easyocr,kraken,chandra}_helpers.py`),
and the notebooks.

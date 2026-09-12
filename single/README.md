# single/

Single-panel-only figure generation.

`create_figures_batch.py` here is a copy of the top-level
[`../create_figures_batch.py`](../create_figures_batch.py) with the panel count
pinned to 1. It imports the same `skyfigs` package, so the data generation,
the prechecks and the accept/reject checks are all **identical** — the only
difference is that `npanels` is fixed rather than sampled.

```bash
# from the repo root
python single/create_figures_batch.py -save_dir ./figs/ -number_of_figures 20
mpirun -np 6 python single/create_figures_batch.py -save_dir ./figs/ -number_of_figures 1000 -nProcs 6
```

Output layout, flags and resume behaviour are the same as the top-level script
(see the main [README](../README.md)); re-running skips indices that already
have both an image and a JSON.

## What differs from the top-level script

| | top level | here |
|---|---|---|
| panels per figure | sampled, `-panel_min/-panel_median/-panel_max` | fixed at 1, no flags |
| `-layout_subpad_min/max` | gap between adjacent panels | not offered — meaningless with one panel |
| everything else | | identical |

`PANELS = 1` near the top of the file is the single knob. Panel count is drawn
from a `normal(median, std)` and then clamped to `[min, max]`, so pinning all
three to 1 is what forces it; every panel-grid layout style (`horizontal`,
`vertical`, `squarish`) then collapses to 1×1.

## Why this directory exists

Multi-panel figures are not currently generatable at a usable rate. Measured:

| | success rate | per figure, 1 rank |
|---|---|---|
| single-panel | ~1 in 20-40 attempts | **~1 min** |
| multi-panel | ~1 in 7000, often 0 in 600+ | **~4 h** |

The cause is the accept/reject checks, which every panel must pass
simultaneously — so the joint probability collapses as panel count rises. Two
prechecks (see [`../skyfigs/utils/prechecks.py`](../skyfigs/utils/prechecks.py))
brought `bounding boxes overlap` down from 67% of multi-panel attempts to 9%,
but `title axis off page` still rejects nearly every multi-panel attempt (~900
occurrences in 639 attempts) and is unresolved.

This directory is the reliable path while that stands. The top-level script is
unchanged and still supports multi-panel for anyone continuing that work.

## Checks that still run here

Unchanged from the top-level pipeline — all of these still apply:

- **prechecks** (`skyfigs/utils/prechecks.py`, run during generation)
  - `fit_colorbar_ticks` — caps a colorbar's tick count to what fits along it
  - `fit_panel_ticks` — the same for a panel's own x/y ticks (skipped on WCS
    axes, where wcsaxes owns the RA/DEC tick machinery)
- **accept/reject** (run after the figure is built; any failure re-randomises)
  - aspect ratio of the plot square (`check_aspect`, off by default)
  - titles / x / y labels running off the figure canvas
    (`check_labels_titles_off_page`)
  - all-pairs bounding-box overlap across squares, titles, x/y labels, tick
    labels, colorbars, colorbar labels and colorbar ticks (`collect_boxes`)
  - image re-opens cleanly after saving
  - plot area as a fraction of figure area (`check_plot_area`)

### Known caveat

`fit_colorbar_ticks` / `fit_panel_ticks` set `MaxNLocator(nbins=n)`, which caps
the number of *intervals* and still snaps to round values — so the tick count is
reduced but not strictly held to the computed capacity (a capacity of 2 gave 4
ticks in one test). It lowers collision rates substantially in practice; it is
not a hard bound.

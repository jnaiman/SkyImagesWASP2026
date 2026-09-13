# models/utils

QA-pair generation and LMM-calling helpers, copied from
`~/LLM_VQA_MultiPanel/utils`.

Restricted to the two question categories this project uses:

1. **full-figure questions** — asked of the figure as a whole
2. **contour-panel questions** — asked of an individual contour panel

Questions about histograms, line plots and scatter plots are excluded.

## What's here

| file | role |
|---|---|
| `plot_qa_utils.py` | shared base: `init_qa_pairs`, persona/context/format text builders, `get_nplots`, `get_adder`, `what_is_relationship`. Every QA module imports from it |
| `figure_level_qa_utils.py` | **full-figure questions**: panel count, plotting style, colormap, aspect ratio, plot titles, axis labels, tick labels, which plot types appear. `figure_level_qa()` runs them all |
| `general_plot_level_qa_utils.py` | plot-type-agnostic panel question: does this panel have x/y error bars. Needed by `figure_level_qa_utils` |
| `contour_plot_qa_utils.py` | **contour questions**: image-vs-lines, min/max/median/mean on x/y/color, distribution of color and x/y |
| `qa_dispatch.py` | composition layer — which questions get asked, in what order. Lifted out of `create_vqa_from_datas.ipynb`, where it was inline |
| `misc_data_utils.py` | `NumpyEncoder`, for writing the QA pairs to JSON |
| `llm_utils.py` | image encode/resize, `get_img_json_pair`, `parse_qa`, `parse_for_errors` — used by the three LMM notebooks, not by QA generation |

All of these depend only on numpy / PIL / stdlib. Nothing here pulls in
`synthetic_training_figures`, matplotlib, or the figure-generation stack.

## What was deliberately left out

| file | why |
|---|---|
| `histogram_plot_qa_utils.py` | histogram questions |
| `scatter_plot_qa_utils.py` | scatter questions |
| `linear_plot_qa_utils.py` | line-plot questions |
| `cross_panel_qa_utils.py` | **looks like a full-figure module, but isn't.** Both of its questions are scatter/line/histogram only: `calc_strongest` skips contour explicitly (`data[k]['type'] != 'contour' and ... != 'histogram'`), and `calc_strongest_stat_hists` runs only on `type == 'histogram'`. With those plot types excluded it would produce no questions |
| `figure_class.py`, `main_plot_utils.py`, `misc_utils.py`, `misc_plot_utils.py` | figure *generation*, not QA generation — and they import `synthetic_training_figures`, which in this repo is the `skyfigs` package |
| `parse_lmm_output_utils.py`, `results_plotting_utils.py` | scoring and plotting of LMM outputs — a later stage than QA generation |
| `latex_utils.py`, `replace_names_utils.py` | not reachable from the figure-level or contour question paths |

## Question levels

The QA pairs are bucketed by difficulty, following the original design:

- **Level 1** — directly readable off the figure (panel count, image vs. contour lines)
- **Level 2** — requires reading values (min/max/median/mean per axis, error bars)
- **Level 3** — requires inference (which distribution the data came from)

## Usage

```python
from utils.plot_qa_utils import init_qa_pairs
from utils.figure_level_qa_utils import figure_level_qa
from utils.qa_dispatch import plot_level_contour_qa, plot_level_general_qa
from utils.misc_data_utils import NumpyEncoder

qa_pairs = init_qa_pairs()
qa_pairs = figure_level_qa(data, qa_pairs, plot_types, verbose=False)

for iplot in range(nplots):
    if data['plot%d' % iplot]['type'] == 'contour':
        qa_pairs = plot_level_contour_qa(data, qa_pairs, iplot)
    qa_pairs = plot_level_general_qa(data, qa_pairs, iplot)

json.dump(qa_pairs, open(out_path, 'w'), cls=NumpyEncoder)
```

`data` is the per-figure dict stored in the generator's `jsons/Picture_NNNNNN.json`
(double-encoded — `json.loads(json.load(f))`).

**Note on "image of the sky" panels:** the original question set predates that
plot type, so there is no sky-specific QA module. Sky panels carry
`type == 'image of the sky'`, so `plot_level_contour_qa` will not fire on them —
only the full-figure questions will cover them. Worth deciding whether sky
panels need their own question set, or should reuse the contour ones (the
underlying data shape is the same: x, y and a color grid).

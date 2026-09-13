"""
Dispatch wrappers for QA-pair generation.

These two functions lived inline in `create_vqa_from_datas.ipynb` in
LLM_VQA_MultiPanel rather than in `utils/`.  They are the composition layer --
they decide which individual question functions get asked, in what order, and
with which arguments -- so they are pulled out here to keep the notebook thin
and to make the question set reviewable in one place.

Only two of the original dispatchers are reproduced, matching what this project
generates:

  * `figure_level_qa`  (imported from figure_level_qa_utils) -- questions asked
    of the whole figure: panel count, plotting style, colormap, aspect ratio,
    titles, axis labels, tick labels, which plot types appear.
  * `plot_level_contour_qa` (below) -- questions asked of a contour panel.
  * `plot_level_sky_qa` (below) -- questions asked of an "image of the sky"
    panel.  Adapted from the contour set rather than copied: see
    sky_plot_qa_utils.py for what differs and why.

The histogram / scatter / line dispatchers, and the cross-panel one, are
deliberately absent -- see README.md in this directory.
"""

import numpy as np

from .contour_plot_qa_utils import (q_stats_contours, q_relationship_contour,
                                    q_contour_plot_image_or_lines)
from .sky_plot_qa_utils import (q_stats_sky, q_relationship_sky,
                                q_sky_image_or_lines, SKY_LINE_LIST,
                                q_sky_epoch, q_sky_tick_unit,
                                q_sky_field_extent, q_sky_pixel_scale)
from .general_plot_level_qa_utils import q_errorbars_existance_lines


# the statistics asked about at Level 2, as used by the original notebook
STATS = {'minimum': np.min, 'maximum': np.max, 'median': np.median, 'mean': np.mean}

# distribution names offered as multiple-choice at Level 3
LINE_LIST = ['random', 'linear', 'gaussian mixture model']


def plot_level_contour_qa(data, qa_pairs, iplot, stats=None,
                          line_list=None, verbose_qa=False):
    """
    Every contour-panel question, for panel `iplot`.

    Verbatim from create_vqa_from_datas.ipynb (cell 11), except that `stats` and
    `line_list` now default to the module-level constants instead of being
    required / shadowed by a local rebind.

    Levels follow the paper's difficulty tiers:
      L1  is this panel drawn as an image, contour lines, or both
      L2  min/max/median/mean along x, y and the color axis
      L3  which distribution the color and x/y data were drawn from
    """
    if stats is None:
        stats = STATS
    if line_list is None:
        line_list = LINE_LIST

    ######### L1 #########
    qa_pairs = q_contour_plot_image_or_lines(data, qa_pairs,
                                             plot_num=iplot,
                                             verbose=verbose_qa)

    ######### L2 #########
    # stats items
    for k, v in stats.items():          # for all stats
        for axis in ['x', 'y', 'color']:
            qa_pairs = q_stats_contours(data, qa_pairs, stat={k: v},
                                        plot_num=iplot, use_words=True,
                                        verbose=verbose_qa, axis=axis)

    ######### L3 #########
    # type of distribution
    for axis in ['color', 'x/y']:
        qa_pairs = q_relationship_contour(data, qa_pairs, plot_num=iplot, axis=axis,
                                          return_qa=True, use_words=True,
                                          use_list=True,
                                          line_list=line_list,
                                          verbose=verbose_qa)

    return qa_pairs


def plot_level_general_qa(data, qa_pairs, iplot, axes=('x', 'y'), verbose_qa=False):
    """
    Plot-type-agnostic panel questions -- currently just error-bar existence.

    In the original notebook `q_errorbars_existance_lines` was called directly
    from the main loop rather than through a dispatcher; wrapped here for
    symmetry with plot_level_contour_qa.
    """
    for axis in axes:
        qa_pairs = q_errorbars_existance_lines(data, qa_pairs, axis=axis,
                                               plot_num=iplot,
                                               verbose=verbose_qa)
    return qa_pairs


def plot_level_sky_qa(data, qa_pairs, iplot, stats=None,
                      line_list=None, verbose_qa=False,
                      ask_image_or_lines=False, ask_radec=True,
                      ask_extras=True):
    """
    Every "image of the sky" question, for panel `iplot`.

    ask_image_or_lines : the image/contour/both question is near-degenerate for
        sky panels (the generator weights it 1000/1/1, so the answer is "image"
        ~99.8% of the time).  Off by default -- a near-constant answer inflates
        accuracy without measuring anything.  Set True to include it.
    ask_radec : include min/max/median/mean of RA and DEC, derived from the
        panel's WCS over the displayed region.  Automatically skipped per-panel
        when no WCS is stored.  Set False for color-only statistics.
    ask_extras : include the sky-specific questions - coordinate epoch, finest
        tick unit on each axis, angular field width/height, and pixel scale.
        Each is skipped individually when it cannot be determined.

    Levels:
      L1  (optional) image vs contour lines vs both
      L1  (extras) coordinate epoch, finest unit on the RA and DEC ticks
      L2  min/max/median/mean of the color values, and of RA/DEC in degrees;
          (extras) angular field height and width in arcmin
      L3  real image of the sky vs gaussian mixture model;
          (extras) pixel scale in arcsec
    """
    if stats is None:
        stats = STATS
    if line_list is None:
        line_list = SKY_LINE_LIST

    ######### L1 #########
    if ask_image_or_lines:
        qa_pairs = q_sky_image_or_lines(data, qa_pairs,
                                        plot_num=iplot,
                                        verbose=verbose_qa)

    ######### L2 #########
    axes = ['color'] + (['x', 'y'] if ask_radec else [])
    for k, v in stats.items():
        for axis in axes:
            qa_pairs = q_stats_sky(data, qa_pairs, stat={k: v},
                                   plot_num=iplot, use_words=True,
                                   verbose=verbose_qa, axis=axis)

    ######### L3 #########
    qa_pairs = q_relationship_sky(data, qa_pairs, plot_num=iplot,
                                  return_qa=True, use_words=True,
                                  use_list=True, line_list=line_list,
                                  verbose=verbose_qa)

    ######### sky-specific extras #########
    if ask_extras:
        # L1 -- read straight off the axes
        qa_pairs = q_sky_epoch(data, qa_pairs, plot_num=iplot, verbose=verbose_qa)
        for axis in ['x', 'y']:
            qa_pairs = q_sky_tick_unit(data, qa_pairs, plot_num=iplot, axis=axis,
                                       verbose=verbose_qa)
        # L2 -- requires reading both ends of an axis
        for extent_axis in ['height', 'width']:
            qa_pairs = q_sky_field_extent(data, qa_pairs, plot_num=iplot,
                                          axis=extent_axis, verbose=verbose_qa)
        # L3 -- extent divided by the visible grid
        qa_pairs = q_sky_pixel_scale(data, qa_pairs, plot_num=iplot, verbose=verbose_qa)
    return qa_pairs

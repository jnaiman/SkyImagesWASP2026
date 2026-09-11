"""
Holder for the plot-generation probability tables.

Ported from ArXiv_figure_injection/utils/misc_plot_utils.py, with the plot-type
set narrowed: this repo only generates "contour" and "image of the sky" panels,
so the scatter / line / histogram blocks of the original are not built.

`make_plotplotparams()` takes the baseline distributions from
`plot_parameters.py` and applies the run-time overrides (resolutions, number of
contour levels, where the astroquery tables live, ...) that the batch scripts
used, then normalises every probability.
"""

import os
from copy import deepcopy
import pandas as pd

from .utils.plot_parameters import panel_params as panel_params_orig
from .utils.plot_parameters import title_params as title_params_orig
from .utils.plot_parameters import xlabel_params as xlabel_params_orig
from .utils.plot_parameters import ylabel_params as ylabel_params_orig
from .utils.plot_parameters import colorbar_params as colorbar_params_orig

from .utils.plot_parameters import plot_types_params

from .utils.synthetic_fig_utils import normalize_params_prob

from .paths import get_resources_dir, DEFAULT_ASTROQUERY_IMG_DIR

# the only two plot types this repo generates
PLOT_TYPES = ('contour', 'image of the sky')


def make_plotplotparams(fullproc_r=None,
                        astroquery_img_dir=None,
                        plot_types=PLOT_TYPES,
                        missing_list_file=None,
                        panel_median=4, panel_max=25,
                        equation_prob=0.25, colorbar_prob=1.0,
                        contour_prob=1.0, sky_prob=1.0,
                        sky_from_astroquery_prob=1.0, sky_from_gmm_prob=1.0):
    """
    Build every probability table plot generation needs.

    fullproc_r         : resources dir (fonts.csv, object_wavelength_pairs.pickle, ...)
    astroquery_img_dir : where downloaded SkyView .fits images are cached
    plot_types         : which plot types to include; must be a subset of
                         ('contour', 'image of the sky')
    missing_list_file  : cache of (object, survey) pairs SkyView has no image
                         for.  Defaults to
                         <fullproc_r>/obj_survey_missing_files/obj_survey_missing_list.csv
    contour_prob / sky_prob
                       : relative weight of each plot type (normalised below).
                         Set one to 0 to generate only the other.
    sky_from_astroquery_prob / sky_from_gmm_prob
                       : within "image of the sky", weight of a real SkyView
                         cutout vs. a synthetic gaussian-mixture "sky".

    Returns
        plot_params_line, panel_params, title_params, xlabel_params,
        ylabel_params, colorbar_params, linestyles_hist, linestyles, font_names
    """
    unknown = [p for p in plot_types if p not in PLOT_TYPES]
    if unknown:
        raise ValueError('unsupported plot type(s) %s -- this repo only builds %s'
                         % (unknown, list(PLOT_TYPES)))
    if not plot_types:
        raise ValueError('plot_types is empty; nothing to generate')

    fullproc_r = get_resources_dir(fullproc_r)
    if astroquery_img_dir is None:
        astroquery_img_dir = DEFAULT_ASTROQUERY_IMG_DIR
    astroquery_img_dir = os.path.expanduser(astroquery_img_dir)
    if missing_list_file is None:
        missing_list_file = fullproc_r + 'obj_survey_missing_files/obj_survey_missing_list.csv'
    missing_list_file = os.path.expanduser(missing_list_file)

    ############## PLOT PARAMS ###################

    plot_params = deepcopy(plot_types_params)
    panel_params = deepcopy(panel_params_orig)
    title_params = deepcopy(title_params_orig)
    xlabel_params = deepcopy(xlabel_params_orig)
    ylabel_params = deepcopy(ylabel_params_orig)
    colorbar_params = deepcopy(colorbar_params_orig)

    # kept only so the shared plotting machinery (which still branches on line
    # style for the contour overlays) has the same subsets it always had
    linestyles = ['-', '--', ':']
    linestyles_hist = ['-']

    plot_params_line = {}

    ### Contours
    if 'contour' in plot_types:
        plot_params_line['contour'] = deepcopy(plot_params['contour'])

        plot_params_line['contour']['nlines']['min'] = 1
        plot_params_line['contour']['nlines']['max'] = 5

        # lower resolution?
        plot_params_line['contour']['npoints'] = {'nx': {'min': 10, 'max': 100},
                                                  'ny': {'min': 10, 'max': 100}}

        # prob of getting a contour plot
        plot_params_line['contour']['prob'] = contour_prob

    ### Images of the sky
    if 'image of the sky' in plot_types:
        plot_params_line['image of the sky'] = deepcopy(plot_params['image of the sky'])

        # lines if overplotting like with contours
        plot_params_line['image of the sky']['nlines']['min'] = 1
        plot_params_line['image of the sky']['nlines']['max'] = 5

        # use a real "image of the sky" from astroquery, or a GMM distribution?
        plot_params_line['image of the sky']['distribution']['gmm']['prob'] = sky_from_gmm_prob
        plot_params_line['image of the sky']['distribution']['sky']['prob'] = sky_from_astroquery_prob

        # if querying with astroquery, where are the tables (object+wavelength)
        # and the storage of already-downloaded files?
        # 1. combos of object + wavelength from our historical corpus
        plot_params_line['image of the sky']['distribution']['sky']['object wavelength table'] = \
            fullproc_r + 'object_wavelength_pairs.pickle'
        # 2. where to store images once they have been queried & downloaded
        plot_params_line['image of the sky']['distribution']['sky']['query images dir'] = astroquery_img_dir
        # 3. running cache of (object, survey) pairs SkyView has nothing for
        plot_params_line['image of the sky']['distribution']['sky']['missing obj/surveys list'] = missing_list_file

        # image or lines
        plot_params_line['image of the sky']['image or contour']['prob']['image'] = 1000

        # lower resolution?
        plot_params_line['image of the sky']['npoints'] = {'nx': {'min': 10, 'max': 100},
                                                           'ny': {'min': 10, 'max': 100}}

        # prob of getting an image of the sky
        plot_params_line['image of the sky']['prob'] = sky_prob

    ### Other params
    panel_params['number prob']['median'] = panel_median  # usually 4-ish, 1 for debugging
    panel_params['number prob']['max'] = panel_max        # 2 for debugging, 25 for a typical run

    # prob of equations
    title_params['equation']['prob'] = equation_prob   # prob any word will be an equation
    xlabel_params['equation']['prob'] = equation_prob
    ylabel_params['equation']['prob'] = equation_prob

    colorbar_params['prob'] = colorbar_prob  # prob of plot having colorbar

    ### normalize everybody
    plot_params_line, panel_params, \
        title_params, xlabel_params, \
        ylabel_params = normalize_params_prob(plot_params_line.copy(), panel_params,
                                              title_params, xlabel_params,
                                              ylabel_params, colorbar_params,
                                              verbose=False)

    #### get fonts #####
    font_names = get_font_names(fullproc_r)

    return plot_params_line, panel_params, title_params, xlabel_params, \
        ylabel_params, colorbar_params, linestyles_hist, linestyles, font_names


def get_font_names(fullproc_r=None, known_remove_fonts=('.SF Compact',)):
    """Fonts listed in fonts.csv that actually exist on this machine."""
    # imported lazily: figure_build_utils imports figure_class, which imports
    # this module, so a top-level import here would close the cycle
    from .utils.figure_build_utils import get_fonts
    return get_fonts(get_resources_dir(fullproc_r),
                     known_remove_fonts=list(known_remove_fonts))

"""
skyfigs -- synthetic astronomical figure generation, restricted to the two
plot types used for this project: "contour" and "image of the sky".

Ported from ~/ArXiv_figure_injection (see README.md for the file-by-file
provenance mapping).  The single entry point is `make_random_plot`.
"""

from .paths import get_resources_dir, check_resources  # noqa: F401

__all__ = ['make_random_plot', 'FigureRun', 'reset_figure',
           'make_plotplotparams', 'PLOT_TYPES',
           'get_resources_dir', 'check_resources']

PLOT_TYPES = ('contour', 'image of the sky')


def __getattr__(name):
    # lazy so that `import skyfigs` stays cheap (matplotlib/astropy/spacy are
    # only pulled in when you actually go to make a figure)
    if name == 'make_random_plot':
        from .main_plot_utils import make_random_plot
        return make_random_plot
    if name in ('FigureRun', 'reset_figure'):
        from . import figure_class
        return getattr(figure_class, name)
    if name == 'make_plotplotparams':
        from .plot_params_setup import make_plotplotparams
        return make_plotplotparams
    raise AttributeError(name)

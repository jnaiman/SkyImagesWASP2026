# Generate synthetic astronomical figures of type "contour" and "image of the sky".
#
# run like:
#   python create_figures_batch.py -save_dir ./synthetic_figures/ -number_of_figures 20
#   mpirun -np 4 python create_figures_batch.py -save_dir ./synthetic_figures/ -number_of_figures 700
#
# Each successful figure writes four files under -save_dir:
#   imgs/Picture_NNNNNN.jpeg     the figure
#   jsons/Picture_NNNNNN.json    every bounding box + the data behind the plot
#   pickles/Picture_NNNNNN.pickle  the same, unserialised
#   diags/Picture_NNNNNN.jpeg    the figure with the boxes drawn on it
#
# This is the standalone-generation counterpart of
# ArXiv_figure_injection/synthetic_training_figures/create_figures_batch.py,
# rebuilt on the newer `make_random_plot` / `FigureRun` architecture that lives
# inside ArXiv_figure_injection/create_inject_figures_and_PDFmine_OCR_batch.py.

import argparse
import os

parser = argparse.ArgumentParser(
    description='Generate synthetic "contour" and "image of the sky" figures.')

parser.add_argument("-save_dir", nargs='?',
                    default="~/Dropbox/wwt_image_extraction/FullProcess_resources/synthetic_figures_sky/",
                    help='where imgs/, jsons/, pickles/ and diags/ are written')
parser.add_argument("-number_of_figures", nargs='?', type=int, default=700)
parser.add_argument("-nProcs", nargs='?', type=int, default=2,
                    help='work-chunk count handed to yt parallel_objects')

# --- what to generate ---
parser.add_argument("-plot_types", nargs='?', default='contour,image of the sky',
                    help='comma-separated subset of "contour,image of the sky"')
parser.add_argument("-sky_source", nargs='?', default='both',
                    choices=['both', 'astroquery', 'gmm'],
                    help='for "image of the sky": real SkyView cutouts, a synthetic '
                         'gaussian-mixture sky, or a mix of the two')
parser.add_argument("-sky_local_only", nargs='?', type=int, default=0,
                    help='1 = never query SkyView; draw real cutouts only from the '
                         '.fits already in -astroquery_img_dir. Runs offline and much '
                         'faster, but only sees objects downloaded before')
parser.add_argument("-panel_min", nargs='?', type=int, default=1,
                    help='fewest panels per figure; 2 forces every figure multipanel')
parser.add_argument("-panel_median", nargs='?', type=int, default=4,
                    help='typical number of panels per figure')
parser.add_argument("-panel_max", nargs='?', type=int, default=25,
                    help='most panels per figure; 1 forces every figure single-panel')

# --- where the static lookup tables live ---
parser.add_argument("-resources_dir", nargs='?', default=None,
                    help='fonts.csv, data/words_cleaned.pickle, inlines*.csv, '
                         'object_wavelength_pairs.pickle. Default: $SKYFIGS_RESOURCES, '
                         'else <repo>/resources/')
parser.add_argument("-astroquery_img_dir", nargs='?',
                    default="~/Dropbox/wwt_image_extraction/FullProcess_resources/astroquery_images/",
                    help='cache of SkyView .fits downloads')

# --- run control ---
parser.add_argument("-verbose", nargs='?', type=int, default=1)
parser.add_argument("-restart", nargs='?', type=int, default=0,
                    help='1 = regenerate figures that already exist')
parser.add_argument("-time_out", nargs='?', type=float, default=5,
                    help='per-stage timeout, in minutes')
parser.add_argument("-max_tries", nargs='?', type=int, default=50,
                    help='attempts per figure before every parameter is re-randomised')
parser.add_argument("-max_resets", nargs='?', type=int, default=10,
                    help='give up on a figure after this many re-randomisations '
                         '(0 = never give up, the original behaviour). Without a '
                         'cap a hard figure retries forever')
parser.add_argument("-layout_pad_min", nargs='?', type=float, default=0.0,
                    help='tight_layout pad range, in font-size units. The default '
                         '0.0-0.1 is very tight and is why multipanel figures nearly '
                         'always fail the box-overlap check; try 0.3-1.0 for those')
parser.add_argument("-layout_pad_max", nargs='?', type=float, default=0.1)
parser.add_argument("-grace_ticks", nargs='?', type=int, default=5,
                    help='tick labels allowed to overlap before a figure is rejected')
parser.add_argument("-save_diagnostic_plot", nargs='?', type=int, default=1)
parser.add_argument("-img_format", nargs='?', default='jpeg')
parser.add_argument("-texbin", nargs='?', default='/Library/TeX/texbin',
                    help='added to $PATH so matplotlib can shell out to latex')

args = parser.parse_args()

verbose = bool(args.verbose)
restart = bool(args.restart)
save_diagnostic_plot = bool(args.save_diagnostic_plot)
img_format = [f.strip() for f in args.img_format.split(',') if f.strip()]
plot_types = tuple(p.strip() for p in args.plot_types.split(',') if p.strip())

fake_figs_dir = os.path.expanduser(args.save_dir)
if not fake_figs_dir.endswith(os.sep):
    fake_figs_dir += os.sep
astroquery_img_dir = os.path.expanduser(args.astroquery_img_dir)

# Resolve the resources dir before importing skyfigs: FigureRun() is re-built
# from scratch on every internal reset and reads it from the environment, so
# -resources_dir has to be visible there too.
if args.resources_dir is not None:
    os.environ['SKYFIGS_RESOURCES'] = os.path.expanduser(args.resources_dir)
os.environ.setdefault('SKYFIGS_ASTROQUERY_IMAGES', astroquery_img_dir)


######### IMPORTS #############

import matplotlib as mpl
mpl.use('Agg')          # non-interactive, must come before pyplot
import matplotlib.pyplot as plt

if os.path.isdir(args.texbin):
    os.environ["PATH"] += os.pathsep + args.texbin
mpl.rcParams['text.usetex'] = True
mpl.rcParams['text.latex.preamble'] = r'\usepackage{amsmath} \usepackage{amssymb}'  # for \text

import numpy as np

import warnings
warnings.filterwarnings("error")   # the generator uses warnings as control flow

from yt.enable_parallelism import turn_on_parallelism
from yt.utilities.parallel_tools.parallel_analysis_interface import parallel_objects
from yt.funcs import is_root

turn_on_parallelism()

from skyfigs.paths import get_resources_dir, check_resources
from skyfigs.plot_params_setup import make_plotplotparams
from skyfigs.main_plot_utils import make_random_plot


######### SETUP #############

if is_root():
    print('-- Start setup --')

resources_dir = get_resources_dir(args.resources_dir)
need_sky = 'image of the sky' in plot_types
if is_root():
    print('resources:', resources_dir)
    check_resources(resources_dir, need_sky=need_sky)

# output directories
for d in ['imgs', 'jsons', 'pickles'] + (['diags'] if save_diagnostic_plot else []):
    dd = fake_figs_dir + d + '/'
    if not os.path.exists(dd):
        os.makedirs(dd, exist_ok=True)
        if is_root():
            print('made:', dd)
if need_sky and not os.path.exists(astroquery_img_dir):
    os.makedirs(astroquery_img_dir, exist_ok=True)
    if is_root():
        print('made:', astroquery_img_dir)

# "image of the sky" can come from a real astroquery/SkyView cutout or from a
# synthetic gaussian-mixture sky; -sky_source picks between them
sky_from_astroquery_prob = 1.0 if args.sky_source in ('both', 'astroquery') else 0.0
sky_from_gmm_prob = 1.0 if args.sky_source in ('both', 'gmm') else 0.0
sky_local_only = bool(args.sky_local_only)
max_resets = args.max_resets if args.max_resets > 0 else None

# tight_layout spacing: the upstream default samples all three pads in 0.0-0.1,
# which crowds adjacent panels into each other's tick labels
tight_layout_params = {'prob': 1.0,
                       'pad':   {'min': args.layout_pad_min, 'max': args.layout_pad_max},
                       'w_pad': {'min': args.layout_pad_min, 'max': args.layout_pad_max},
                       'h_pad': {'min': args.layout_pad_min, 'max': args.layout_pad_max}}
if is_root() and sky_local_only and sky_from_astroquery_prob > 0:
    from skyfigs.utils.distribution_utils import list_local_sky_images
    print('sky images: local only,', len(list_local_sky_images(astroquery_img_dir)),
          'cached cutouts in', astroquery_img_dir)

plot_params, panel_params, title_params, xlabel_params, \
    ylabel_params, colorbar_params, linestyles_hist, linestyles, \
    font_names = make_plotplotparams(fullproc_r=resources_dir,
                                     astroquery_img_dir=astroquery_img_dir,
                                     plot_types=plot_types,
                                     panel_min=args.panel_min,
                                     panel_median=args.panel_median,
                                     panel_max=args.panel_max,
                                     sky_from_astroquery_prob=sky_from_astroquery_prob,
                                     sky_from_gmm_prob=sky_from_gmm_prob,
                                     sky_local_only=sky_local_only)

if is_root():
    print('plot types:', {k: round(float(v['prob']), 3) for k, v in plot_params.items()})
    print('-- Done with setup --')

# kwargs handed to make_random_plot; FigureRun keeps any of these that name one
# of its attributes, and re-applies them every time it resets itself mid-figure
figure_kwargs = dict(plot_params=plot_params,
                     panel_params=panel_params,
                     title_params=title_params,
                     xlabel_params=xlabel_params,
                     ylabel_params=ylabel_params,
                     colorbar_params=colorbar_params,
                     linestyles=linestyles,
                     linestyles_hist=linestyles_hist,
                     font_names=font_names,
                     tight_layout_params=tight_layout_params,
                     itriesMax=args.max_tries,
                     save_diagnostic_plot=save_diagnostic_plot,
                     fullproc_r=resources_dir)


###################### DO THE THING ##########################

def already_have(ifigure):
    """True if every output for this figure index is already on disk."""
    name = 'Picture_' + str(ifigure + 1).zfill(6)
    for iformat in img_format:
        if not os.path.exists(fake_figs_dir + 'imgs/' + name + '.' + iformat):
            return False
    return os.path.exists(fake_figs_dir + 'jsons/' + name + '.json')


plt.close('all')

my_storage = {}
for sto, ifigure in parallel_objects(np.arange(0, args.number_of_figures),
                                     args.nProcs, storage=my_storage):
    sto.result_id = ifigure

    print('')
    if verbose:
        print('*************** Figure', ifigure + 1, '****************')

    if already_have(ifigure) and not restart:
        if verbose:
            print('  already have:', fake_figs_dir + 'imgs/Picture_'
                  + str(ifigure + 1).zfill(6) + '.<FMT>')
        sto.result = 'skipped'
        continue

    figure_name = 'Picture_' + str(ifigure + 1).zfill(6)
    try:
        diagsout = make_random_plot(fake_figs_dir=fake_figs_dir,
                                    ifigure=ifigure,
                                    figure_name=figure_name,
                                    img_format=img_format,
                                    timeout=args.time_out,
                                    grace_ticks=args.grace_ticks,
                                    verbose=verbose,
                                    allow_sky_image=need_sky,
                                    max_resets=max_resets,
                                    **figure_kwargs)
        sto.result = 'ok' if diagsout else 'gave up'
    except Exception as e:
        print('[ERROR]: figure', ifigure + 1, 'failed --', str(e))
        sto.result = 'error: ' + str(e)
    finally:
        plt.close('all')

if is_root():
    counts = {}
    for v in my_storage.values():
        k = 'error' if (isinstance(v, str) and v.startswith('error')) else str(v)
        counts[k] = counts.get(k, 0) + 1
    print('')
    print('-- Done --', counts)
    print('figures in:', fake_figs_dir + 'imgs/')

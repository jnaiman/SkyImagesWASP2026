# Regenerate the WASP2026 dataset as one TRIPLET per index block: contour,
# synthetic (gaussian-mixture) sky, and real SkyView sky -- with the angular
# size of the sky fields CHOSEN rather than left to whatever SkyView happens to
# default to.  This is the reproducibility script for the published dataset.
#
# What differs from single/create_figures_batch.py
# ------------------------------------------------
# 1. Real-sky fields get a deliberate angular size.  The original run called
#    SkyView with `pixels=(300,300)` and no size, so each cutout came back at
#    the survey's native pixel scale and the field was whatever 300 pixels of
#    that covered -- which ranged from 0.5 arcmin to 136 degrees across the
#    dataset.  Here the size is, in order of preference:
#       (a) the object's own angular extent from SIMBAD, scaled by
#           -object_size_factor, when SIMBAD knows one (about 21% of the
#           objects with cached cutouts -- the rest are stars, which are point
#           sources and have no extent to report); otherwise
#       (b) log-uniform between -res_factor x the survey's angular RESOLUTION
#           (50x by default) and -fov_factor x the survey's default field of
#           view.  Where those cross -- a coarse beam relative to what the
#           survey hands back -- the FOV ceiling wins.
#    The existing 50-100% random display crop still applies on top, so the
#    field that ends up drawn is 50-100% of the size requested here.
#    Resolution comes from resources/skyview_survey_metadata.csv (scraped by
#    misc/fetch_skyview_survey_metadata.py); the default FOV is 300 x the
#    survey's native pixel scale, read from the local .fits cache.
#
# 2. The GMM skies are sized to MATCH the real ones.  Their scale is drawn from
#    the angular sizes the real run actually produced, so field size cannot be
#    used as a shortcut for the real-vs-synthetic question.  This is why the
#    real family must be generated FIRST -- the gmm phase reads the real jsons.
#
# 3. Contours are copied, not regenerated.  Nothing about them changes, and
#    re-rendering 667 of them costs hours.  -do_contour 1 regenerates them
#    anyway; misc/copy_contours_to_triplets.py does the copy.
#
# Index blocks, matching the published dataset:
#   Picture_000001+   contour
#   Picture_100001+   sky, gaussian mixture
#   Picture_200001+   sky, real cutout
#
# run like:
#   # 1. contours: copy rather than generate
#   python misc/copy_contours_to_triplets.py --src <old run> --dst <new run>
#   # 2. real sky FIRST -- the gmm phase is sized from its output
#   mpirun -np 6 python create_figures_triplets_batch.py -family real \
#          -save_dir ~/Downloads/tmp/waspPaper/data/full_dataset/ -number_of_figures 667
#   # 3. then the synthetic sky
#   mpirun -np 6 python create_figures_triplets_batch.py -family gmm \
#          -save_dir ~/Downloads/tmp/waspPaper/data/full_dataset/ -number_of_figures 667
#
# Each successful figure writes four files under -save_dir, exactly as before:
#   imgs/Picture_NNNNNN.jpeg / jsons/ / pickles/ / diags/

import argparse
import os
import sys

# this script lives one level down, so put the repo root on the path for
# `skyfigs` and the bundled `yt` shim
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

parser = argparse.ArgumentParser(
    description='Generate SINGLE-PANEL synthetic "contour" and '
                '"image of the sky" figures.')

parser.add_argument("-save_dir", nargs='?',
                    default="~/Dropbox/wwt_image_extraction/FullProcess_resources/synthetic_figures_sky/",
                    help='where imgs/, jsons/, pickles/ and diags/ are written')
parser.add_argument("-number_of_figures", nargs='?', type=int, default=700)
parser.add_argument("-start_index", nargs='?', type=int, default=0,
                    help='first figure index this run owns; it writes '
                         'Picture_<start_index+1> .. Picture_<start_index+number_of_figures>. '
                         'Give each plot-type batch a disjoint range so a gap left by '
                         'one is never back-filled by another with different settings')
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
parser.add_argument("-npoints_min", nargs='?', type=int, default=50,
                    help='grid every panel is drawn on: contour fields, GMM skies '
                         'and real cutouts all sample nx from this range (ny follows '
                         'the figure aspect), then quantise onto a shared odd-k '
                         'ladder so their pixelation matches')
parser.add_argument("-npoints_max", nargs='?', type=int, default=300)
parser.add_argument("-colorbar_prob", nargs='?', type=float, default=1.0,
                    help='probability a panel gets its own colorbar. At 1.0 every '
                         'panel in a multipanel figure carries one, and their tick '
                         'labels collide -- the dominant multipanel rejection')
parser.add_argument("-fontsize_min", nargs='?', type=int, default=10,
                    help='floor for shrinking fonts when boxes overlap; once hit, '
                         'the figure is abandoned and re-randomised')
# NOTE: no -panel_* flags here.  npanels is drawn from a normal(median, std) and
# clamped to [min, max]; pinning all three to 1 is what makes every figure
# single-panel, and every panel-grid layout style then collapses to 1x1.
PANELS = 1

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
                    help='tight_layout pad between the FIGURE EDGE and the subplots, '
                         'in font-size units. Keep this small (0.0-0.1) so labels can '
                         'sit right against the canvas edge -- that is deliberate')
parser.add_argument("-layout_pad_max", nargs='?', type=float, default=0.1)
parser.add_argument("-grace_ticks", nargs='?', type=int, default=5,
                    help='tick labels allowed to overlap before a figure is rejected')
parser.add_argument("-save_diagnostic_plot", nargs='?', type=int, default=1)
parser.add_argument("-img_format", nargs='?', default='jpeg')
parser.add_argument("-texbin", nargs='?', default='/Library/TeX/texbin',
                    help='added to $PATH so matplotlib can shell out to latex')


# ======================= triplet-specific options =======================
parser.add_argument("-family", nargs='?', default='real',
                    choices=('real', 'gmm', 'contour'),
                    help='which family to generate.  Run "real" BEFORE "gmm": '
                         'the gmm fields are sized from the real ones.')
parser.add_argument("-do_contour", nargs='?', type=int, default=0,
                    help='0 = refuse to generate contours (they are copied from '
                         'the previous run by misc/copy_contours_to_triplets.py). '
                         '1 = allow it, for a full from-scratch rebuild.')

# --- how a real-sky field size is chosen ---
parser.add_argument("-res_factor", nargs='?', type=float, default=50.0,
                    help='lower bound = this many times the survey resolution. '
                         'Where 50x resolution exceeds the FOV ceiling (41 of 186 '
                         'surveys), the ceiling wins and the field is set to it.')
parser.add_argument("-fov_factor", nargs='?', type=float, default=0.75,
                    help="upper bound = this fraction of the survey's default FOV")
parser.add_argument("-max_field_arcmin", nargs='?', type=float, default=300.0,
                    help='absolute ceiling on a field, in arcmin, whatever the '
                         'survey could give.  300 (5 deg) keeps a cutout reading '
                         'as an image of a region rather than an all-sky map; '
                         'without it the all-sky radio maps ask for 225 deg. '
                         'Takes priority over the resolution floor. 0 = no cap.')
parser.add_argument("-object_size_factor", nargs='?', type=float, default=3.0,
                    help="field = this many times the object's SIMBAD major axis, "
                         'so the object sits inside the frame rather than filling it')
parser.add_argument("-use_simbad_sizes", nargs='?', type=int, default=1,
                    help='0 = ignore SIMBAD and always use the survey range')
parser.add_argument("-simbad_sizes", nargs='?', default=None,
                    help='default: <repo>/resources/simbad_object_sizes.csv')
parser.add_argument("-survey_meta", nargs='?', default=None,
                    help='default: <repo>/resources/skyview_survey_metadata.csv')
parser.add_argument("-gmm_sizes_from", nargs='?', default=None,
                    help='directory of already-generated REAL jsons to take the '
                         'gmm field sizes from.  Default: <save_dir>/jsons/')
parser.add_argument("-angular_seed", nargs='?', type=int, default=20260919,
                    help='seed for the field-size draws, so a rerun reproduces them')

args = parser.parse_args()

verbose = bool(args.verbose)
restart = bool(args.restart)
save_diagnostic_plot = bool(args.save_diagnostic_plot)
img_format = [f.strip() for f in args.img_format.split(',') if f.strip()]
# ------------------------- family -------------------------
# Each family owns an index block, which is what makes the three files with the
# same offset a "triplet" and keeps the published names stable.
INDEX_BLOCK = {'contour': 0, 'gmm': 100000, 'real': 200000}
FAMILY = args.family

if FAMILY == 'contour' and not args.do_contour:
    raise SystemExit(
        'refusing to generate contours: they are unchanged by the new angular-size\n'
        'policy and are copied from the previous run instead --\n'
        '    python misc/copy_contours_to_triplets.py --src <old> --dst <new>\n'
        'pass -do_contour 1 to generate them anyway.')

if FAMILY == 'contour':
    plot_types = ('contour',)
    args.sky_source = 'gmm'          # unused, but keep the probabilities valid
else:
    plot_types = ('image of the sky',)
    args.sky_source = 'astroquery' if FAMILY == 'real' else 'gmm'

plot_types = tuple(p.strip() for p in plot_types if p.strip())

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

from skyfigs.utils.plot_parameters import fontsizes as _fontsizes
_fontsizes['fontsize min'] = args.fontsize_min   # read by main_plot_utils' checks

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

# tight_layout spacing.  pad is the gap between the FIGURE EDGE and the subplot,
# kept small on purpose so labels can sit right against the canvas edge.  w_pad
# and h_pad are the gaps between adjacent panels, so with one panel they do
# nothing; they are left at the sampled range for consistency.
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
                                     npoints_min=args.npoints_min,
                                     npoints_max=args.npoints_max,
                                     colorbar_prob=args.colorbar_prob,
                                     panel_min=PANELS,
                                     panel_median=PANELS,
                                     panel_max=PANELS,
                                     sky_from_astroquery_prob=sky_from_astroquery_prob,
                                     sky_from_gmm_prob=sky_from_gmm_prob,
                                     sky_local_only=sky_local_only)

if is_root():
    print('plot types:', {k: round(float(v['prob']), 3) for k, v in plot_params.items()})
    print('panels per figure: %d (fixed)' % PANELS)
    print('-- Done with setup --')


# ==================== ANGULAR SIZE OF THE SKY FIELDS ====================
import csv as _csv
import json as _json
import glob as _glob
from copy import deepcopy as _deepcopy

from skyfigs.utils.survey_scales import (load_survey_scales,
                                         angular_range_arcsec)

_repo = os.path.dirname(os.path.abspath(__file__))
_simbad_csv = args.simbad_sizes or os.path.join(_repo, 'resources',
                                                'simbad_object_sizes.csv')
_survey_csv = args.survey_meta or os.path.join(_repo, 'resources',
                                               'skyview_survey_metadata.csv')

SURVEY_SCALES = load_survey_scales(meta_csv=_survey_csv,
                                   cache=astroquery_img_dir)

SIMBAD_SIZES = {}
if args.use_simbad_sizes and os.path.exists(_simbad_csv):
    with open(_simbad_csv) as _f:
        for _r in _csv.DictReader(_f):
            try:
                _maj = float(_r.get('majaxis_arcmin') or '')
            except ValueError:
                continue
            if _maj > 0:
                SIMBAD_SIZES[_r['object'].strip()] = _maj

_ang_rng = np.random.default_rng(args.angular_seed)


def field_size_arcmin(survey_name, object_id):
    """
    How wide a field to ask SkyView for, in arcmin.

    SIMBAD's major axis first, scaled up so the object sits inside the frame
    rather than filling it.  Otherwise log-uniform between res_factor x the
    survey's resolution and fov_factor x its default field of view --
    log-uniform because the usable range spans two or three decades and a
    uniform draw would put almost every field at the coarse end.

    Returns None when the survey is unknown or its range is degenerate, which
    leaves SkyView to default the size exactly as the original run did.
    """
    if object_id:
        maj = SIMBAD_SIZES.get(str(object_id).strip())
        if maj:
            size = args.object_size_factor * maj
            rng_ = angular_range_arcsec(SURVEY_SCALES, survey_name,
                                        args.res_factor, args.fov_factor,
                                        args.max_field_arcmin or None)
            if rng_:                      # keep it inside what the survey can give
                size = min(max(size, rng_[0] / 60.0), rng_[1] / 60.0)
            return size

    rng_ = angular_range_arcsec(SURVEY_SCALES, survey_name,
                                args.res_factor, args.fov_factor,
                                args.max_field_arcmin or None)
    if not rng_:
        return None
    lo, hi = rng_[0] / 60.0, rng_[1] / 60.0
    return float(np.exp(_ang_rng.uniform(np.log(lo), np.log(hi))))


def realised_real_sizes(jsons_dir):
    """
    The angular widths the REAL family actually came out at, in arcmin.

    Read from the generated jsons rather than from the requested sizes: what
    matters for matching is what the figures ended up showing, after the
    display crop.
    """
    sizes = []
    for f in sorted(_glob.glob(os.path.join(jsons_dir, 'Picture_2*.json'))):
        try:
            d = _json.load(open(f))
            d = _json.loads(d) if isinstance(d, str) else d
            p0 = d.get('plot0') or {}
            if p0.get('type') != 'image of the sky':
                continue
            dp = (p0.get('data') or {}).get('data params') or {}
            if not dp.get('WCS header string'):
                continue
            xs = np.asarray(p0['data']['xs'], dtype=float)
            ys = np.asarray(p0['data']['ys'], dtype=float)
            from astropy.wcs import WCS
            w = WCS(dp['WCS header string'])
            ra, dec = w.pixel_to_world_values(
                np.array([xs.min(), xs.max()], float),
                np.array([ys.min(), ys.max()], float))
            dra = abs(float(ra[1] - ra[0]))
            if dra > 180:
                dra = 360 - dra
            width = dra * np.cos(np.radians(0.5 * (dec[0] + dec[1]))) * 60.0
            if np.isfinite(width) and width > 0:
                sizes.append(width)
        except Exception:
            continue
    return sizes


GMM_SIZE_POOL = []
if FAMILY == 'gmm':
    _src = args.gmm_sizes_from or os.path.join(fake_figs_dir, 'jsons')
    GMM_SIZE_POOL = realised_real_sizes(os.path.expanduser(_src))
    if is_root():
        if GMM_SIZE_POOL:
            _a = np.asarray(GMM_SIZE_POOL)
            print('gmm field sizes drawn from %d real figures: '
                  'min %.2f  median %.2f  max %.1f arcmin'
                  % (len(_a), _a.min(), np.median(_a), _a.max()))
        else:
            print('[WARN] no real figures found in %s -- gmm fields will use the '
                  'built-in range instead, and the two families will NOT match'
                  % _src)

if FAMILY == 'real' and is_root():
    _known = sum(1 for s in SURVEY_SCALES
                 if angular_range_arcsec(SURVEY_SCALES, s, args.res_factor,
                                         args.fov_factor,
                                         args.max_field_arcmin or None))
    print('angular-size policy: SIMBAD for %d objects, survey range for the rest'
          % len(SIMBAD_SIZES))
    print('  surveys with a usable range: %d of %d' % (_known, len(SURVEY_SCALES)))
    print('  range = [%g x resolution, %g x default FOV], capped at %g arcmin'
          % (args.res_factor, args.fov_factor, args.max_field_arcmin))

# hand the policy to the generator: get_sky_image_data reads it off plot_params
if FAMILY == 'real':
    plot_params['image of the sky']['distribution']['sky']['angular size arcmin'] = \
        field_size_arcmin

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
_first = INDEX_BLOCK[FAMILY] + args.start_index
_last = _first + args.number_of_figures
for sto, ifigure in parallel_objects(np.arange(_first, _last),
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

    # A gmm sky gets its field size from the pool the real family produced, one
    # draw per figure, so the two families end up with the same distribution of
    # angular sizes rather than merely the same bounds.
    this_kwargs = figure_kwargs
    if FAMILY == 'gmm' and GMM_SIZE_POOL:
        pick = float(_ang_rng.choice(GMM_SIZE_POOL)) * 60.0      # arcmin -> arcsec
        pp = _deepcopy(figure_kwargs['plot_params'])
        centers = pp['image of the sky']['distribution']['gmm']['centers']
        # a hair's width apart, not equal: the scale is drawn with
        # scipy's loguniform.rvs(min, max), which raises "Domain error in
        # arguments" when the two coincide.  1e-6 relative is far below any
        # visible difference and keeps the draw effectively deterministic.
        centers['center_scale']['min'] = pick
        centers['center_scale']['max'] = pick * (1.0 + 1e-6)
        this_kwargs = dict(figure_kwargs, plot_params=pp)

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
                                    **this_kwargs)
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
    print('index range: Picture_%s .. Picture_%s'
          % (str(_first + 1).zfill(6), str(_last).zfill(6)))

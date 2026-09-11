"""
Central resolution of the static lookup tables ("resources") the figure
generator needs.

Nothing here is generated at run time -- these are the corpus-derived tables
that were built once by the ArXiv mining pipeline and are simply read:

    fonts.csv                     list of system fonts to draw labels with
    data/words_cleaned.pickle     word counts -> "popular nouns" for labels
    inlines.csv / inlines_unique.csv / inlines_uniques_ignore.csv
                                  inline-math fragments for equation labels
    object_wavelength_pairs.pickle (object, wavelength, pdf) triples mined
                                  from the historical corpus; the pool that
                                  "image of the sky" draws real targets from
    obj_survey_missing_files/     accumulated cache of (object, survey) pairs
                                  SkyView has no image for, so they are not
                                  re-queried

Resolution order:
    1. explicit argument / -resources_dir on the command line
    2. $SKYFIGS_RESOURCES
    3. <repo>/resources/          (populate with fetch_resources.sh)
"""

import os

# <repo>/resources/
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLED_RESOURCES = os.path.join(REPO_ROOT, 'resources') + os.sep

# where the tables came from originally, used by fetch_resources.sh
UPSTREAM_RESOURCES = os.path.expanduser('~/ArXiv_figure_injection/resources/')

# where SkyView .fits downloads are cached between runs
DEFAULT_ASTROQUERY_IMG_DIR = os.path.expanduser(
    os.environ.get('SKYFIGS_ASTROQUERY_IMAGES',
                   '~/Dropbox/wwt_image_extraction/FullProcess_resources/astroquery_images/'))


def get_resources_dir(resources_dir=None):
    """Resolve the resources directory, always with a trailing separator."""
    if resources_dir is None:
        resources_dir = os.environ.get('SKYFIGS_RESOURCES', BUNDLED_RESOURCES)
    resources_dir = os.path.expanduser(resources_dir)
    if not resources_dir.endswith(os.sep):
        resources_dir += os.sep
    return resources_dir


def check_resources(resources_dir=None, need_sky=True, verbose=True):
    """
    Report which of the required tables are missing.  Returns the list of
    missing paths (empty list == good to go).
    """
    r = get_resources_dir(resources_dir)
    needed = ['fonts.csv', 'data/words_cleaned.pickle', 'inlines_unique.csv']
    if need_sky:
        needed.append('object_wavelength_pairs.pickle')
    missing = [r + n for n in needed if not os.path.exists(r + n)]
    if verbose and missing:
        print('[WARNING]: missing resources in', r)
        for m in missing:
            print('   ', m)
        print('  -> run ./fetch_resources.sh, or pass -resources_dir / set $SKYFIGS_RESOURCES')
    return missing

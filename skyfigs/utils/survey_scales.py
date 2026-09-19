"""
Angular scales per SkyView survey: resolution, native pixel scale, default FOV.

Why this exists
---------------
`create_figures_triplets_batch.py` picks the angular size of each real-sky
cutout instead of letting SkyView default it.  Two numbers are needed per
survey, and neither is in the FITS SkyView returns:

  * RESOLUTION -- the true resolving power (beam FWHM, seeing).  Only 6 of 186
    cached surveys record it in the header (GLEAM's BMAJ/BMIN, COBE's PIXRESOL).
    SkyView knows it for nearly all of them on its per-survey page, which
    `misc/fetch_skyview_survey_metadata.py` scrapes into
    `resources/skyview_survey_metadata.csv`.
  * DEFAULT FOV -- what a 300x300 request returns when no size is given.  Every
    cutout carries its native pixel scale as CDELT, so FOV = 300 x CDELT.  Read
    from the local .fits cache, which is exact and needs no network.

Resolution is FREE TEXT on SkyView ("6' FWHM", "Depends on plate. Typically 3\".",
"> 4' but varies with declination"), so it is parsed here rather than trusted as
a number.  32 of 186 cannot be parsed at all -- some have no unit ("0.02"), some
carry SkyView's own mojibake where a degree sign belongs ("1.2?? x 1.7??") -- and
those fall back to a multiple of the pixel scale, flagged as estimated.
"""

import csv
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_META = os.path.join(_HERE, '..', '..', 'resources',
                            'skyview_survey_metadata.csv')
DEFAULT_CACHE = '~/Dropbox/wwt_image_extraction/FullProcess_resources/astroquery_images/'

# a survey with no parseable resolution: assume the data is Nyquist-ish sampled
PIXELS_PER_RESOLUTION = 2.5
DEFAULT_PIXELS = 300          # what the generator asks SkyView for

_NUM = r'(\d+(?:\.\d+)?)'
_UNITS = [(r'(?:"|\barcsec\b|\barcseconds\b)', 1.0),
          (r"(?:'|\barcmin\b|\barcminutes\b)", 60.0),
          (r'(?:\bdeg\b|\bdegrees?\b)', 3600.0)]


def parse_angle_arcsec(text):
    """
    Free-text angle -> arcsec, or None if no unit-bearing number is present.

    Takes the LARGEST value when several appear ("26' x 42'"): those are the two
    axes of an elliptical beam, and the coarser one is what actually limits
    what can be resolved.  '??' is stripped first -- it is SkyView's mangled
    degree sign, and leaving it in would let a bare number match nothing.
    """
    if not text:
        return None
    t = text.replace('??', ' ')
    best = None
    for pattern, mult in _UNITS:
        for m in re.finditer(_NUM + r'\s*' + pattern, t, re.I):
            v = float(m.group(1)) * mult
            best = v if best is None else max(best, v)
    return best


def pixel_scales_from_cache(cache=DEFAULT_CACHE):
    """{survey: arcsec/pixel} read from one cached .fits per survey."""
    from astropy.io import fits
    d = os.path.expanduser(cache)
    if not os.path.isdir(d):
        return {}
    one = {}
    for f in os.listdir(d):
        if '_SURVEY_' in f and f.endswith('.fits'):
            one.setdefault(f.split('_SURVEY_')[-1].split('_height')[0], f)
    out = {}
    for survey, f in one.items():
        try:
            h = fits.getheader(os.path.join(d, f))
            cd = abs(float(h.get('CDELT1', 0) or 0))
            if cd > 0:
                out[survey] = cd * 3600.0
        except Exception:
            pass
    return out


def load_survey_scales(meta_csv=DEFAULT_META, cache=DEFAULT_CACHE,
                       pixels=DEFAULT_PIXELS):
    """
    {survey: {resolution_arcsec, pixel_arcsec, fov_arcsec, resolution_source}}

    fov_arcsec is what a `pixels`-square request returns with no size given --
    the natural ceiling on how wide a field to ask for, since beyond it SkyView
    is resampling coarser than the survey's own grid.
    """
    meta = {}
    path = os.path.abspath(meta_csv)
    if os.path.exists(path):
        with open(path) as f:
            for row in csv.DictReader(f):
                meta[row['survey']] = row

    pix = pixel_scales_from_cache(cache)
    out = {}
    for survey in set(meta) | set(pix):
        p = pix.get(survey)
        res = parse_angle_arcsec((meta.get(survey) or {}).get('Resolution'))
        source = 'skyview'
        if res is None:
            if p is None:
                continue
            res = PIXELS_PER_RESOLUTION * p
            source = 'estimated from pixel scale'
        out[survey] = {
            'resolution_arcsec': res,
            'pixel_arcsec': p,
            'fov_arcsec': (p * pixels) if p else None,
            'resolution_source': source,
        }
    return out


def normalise_survey(name):
    """
    A key that matches however a survey name is spelled.

    The scales are keyed off cache FILENAMES, which replace spaces with
    underscores ("DSS2_Red"), while SkyView hands back the real name
    ("DSS2 Red").  Without normalising, every multi-word survey silently missed
    and fell through to the default field size -- which is most of them.
    """
    return re.sub(r'[\s_-]+', ' ', str(name)).strip().lower()


def lookup(scales, survey):
    """The scales record for a survey, however its name is spelled."""
    if survey in scales:
        return scales[survey]
    want = normalise_survey(survey)
    for k, v in scales.items():
        if normalise_survey(k) == want:
            return v
    return None


def angular_range_arcsec(scales, survey, res_factor=50.0, fov_factor=0.75,
                         on_conflict='clamp'):
    """
    (low, high) arcsec to draw a field size from for this survey.

    low  = res_factor x resolution  -- enough beam widths across that structure
                                       is visible rather than a blur
    high = fov_factor x default FOV -- inside what the survey will give at its
                                       own pixel scale

    The two can cross, on a survey whose beam is coarse relative to what it
    hands back: at res_factor=50 that happens for 41 of 186 surveys (11 of the
    52 the dataset actually uses).  `on_conflict` decides what then:

      'clamp' (default) -- collapse to (high, high).  The FOV ceiling wins, so
                           the field stays bounded and as well resolved as the
                           survey allows.  Returning None instead would hand
                           the choice back to SkyView, whose default is the
                           unbounded behaviour this policy exists to replace.
      'none'            -- return None and let the caller decide.

    Returns None when the survey is unknown or has no FOV, either way.
    """
    s = lookup(scales, survey)
    if not s or not s.get('fov_arcsec'):
        return None
    lo = res_factor * s['resolution_arcsec']
    hi = fov_factor * s['fov_arcsec']
    if hi <= 0:
        return None
    if lo >= hi:
        return (hi, hi) if on_conflict == 'clamp' else None
    return lo, hi

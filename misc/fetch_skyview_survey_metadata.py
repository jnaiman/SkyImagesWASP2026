"""
Build a lookup table of SkyView survey metadata -- above all, ANGULAR RESOLUTION.

Why this exists
---------------
The generator asks SkyView for cutouts with `pixels=(300, 300)` and no angular
size, so every image comes back at that survey's NATIVE PIXEL SCALE and the
field of view is the derived quantity (300 x scale).  The pixel scale is in
every cutout's header as CDELT, but the pixel scale is *sampling*, not resolving
power, and the two can differ by a lot -- GLEAM samples at 56"/px with a 377"
beam, DSS2 samples at 1"/px and resolves ~3".

Only 6 of the 186 surveys in the local cache record a resolution in their FITS
header (the GLEAM beams as BMAJ/BMIN, and COBE's PIXRESOL).  SkyView itself
knows it for all of them, on its per-survey `moreinfo.pl` page, but
`astroquery.skyview` does not expose that -- its `get_images` takes pixels,
width, height, sampler, scaling, projection and radius, and nothing about
resolution.  So it is scraped once, here, into a small table.

    python misc/fetch_skyview_survey_metadata.py [--out PATH] [--surveys A,B]
                                                 [--delay 0.5] [--limit N]

Survey names come from the local astroquery cache by default (filenames encode
them with underscores for spaces), falling back to astroquery's survey_dict.
"""

import argparse
import csv
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import html as html_mod

BASE = 'https://skyview.gsfc.nasa.gov/current/cgi/moreinfo.pl?survey='
CACHE = '~/Dropbox/wwt_image_extraction/FullProcess_resources/astroquery_images/'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   '..', 'resources', 'skyview_survey_metadata.csv')

# the fields worth keeping, in output order
FIELDS = ['Regime', 'Resolution', 'PixelScale', 'PixelUnits', 'Frequency',
          'Bandpass', 'Coverage', 'CoordinateSystem', 'Projection', 'Epoch',
          'Provenance']

_PAIR = re.compile(r'<TH[^>]*>(.*?)</TH>\s*<TD[^>]*>(.*?)</TD>', re.S | re.I)
_TAG = re.compile(r'<[^>]*>')
_WS = re.compile(r'\s+')


def survey_names_from_cache(cache=CACHE):
    """Every survey the local .fits cache has an image for."""
    d = os.path.expanduser(cache)
    if not os.path.isdir(d):
        return []
    names = set()
    for f in os.listdir(d):
        if '_SURVEY_' in f and f.endswith('.fits'):
            names.add(f.split('_SURVEY_')[-1].split('_height')[0])
    return sorted(names)


def fetch(survey, timeout=30):
    """
    The raw moreinfo page for one survey.

    Decoded as ISO-8859-1, which is what the server declares.  Some values still
    contain '??' where a degree or arcmin sign belongs -- that mojibake is in
    SkyView's own data (the bytes really are 0x3f), so it is passed through
    rather than guessed at.
    """
    # cache filenames use '_' where the survey name has a space
    url = BASE + urllib.parse.quote(survey.replace('_', ' '))
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return r.read().decode('iso-8859-1')


def clean(fragment):
    """Tags out, entities in, whitespace collapsed."""
    return _WS.sub(' ', html_mod.unescape(_TAG.sub(' ', fragment))).strip()


def parse(page):
    """
    Pull the metadata out of the page's <TH>label</TH><TD>value</TD> table.

    Reading the table directly rather than scraping flattened text: with the
    markup stripped there is nothing marking where one value ends and the next
    label begins, so a resolution of "0.85 degrees" silently ran on into
    "CoordinateSystem Galactic".
    """
    out = {}
    for label, value in _PAIR.findall(page):
        key = clean(label)
        if key in FIELDS:
            out[key] = clean(value)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--surveys', default=None, help='comma-separated, else the cache')
    ap.add_argument('--delay', type=float, default=0.5, help='seconds between requests')
    ap.add_argument('--limit', type=int, default=0)
    a = ap.parse_args()

    if a.surveys:
        names = [s.strip() for s in a.surveys.split(',') if s.strip()]
    else:
        names = survey_names_from_cache()
        if not names:
            from astroquery.skyview import SkyView
            names = sorted({s for v in SkyView.survey_dict.values() for s in v})
    if a.limit:
        names = names[:a.limit]

    print('fetching %d surveys (%.1fs apart)' % (len(names), a.delay))
    rows, failed = [], []
    for i, s in enumerate(names, 1):
        try:
            rec = parse(fetch(s))
            rec['survey'] = s
            rows.append(rec)
        except Exception as e:
            failed.append((s, type(e).__name__))
        if i % 25 == 0 or i == len(names):
            print('   %d/%d' % (i, len(names)))
        time.sleep(a.delay)

    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['survey'] + FIELDS, extrasaction='ignore')
        w.writeheader()
        for r in sorted(rows, key=lambda r: r['survey']):
            w.writerow(r)

    got = sum(1 for r in rows if r.get('Resolution'))
    print()
    print('wrote %s' % out)
    print('  %d surveys, %d with a Resolution field' % (len(rows), got))
    if failed:
        print('  failed: %s' % failed[:6])


if __name__ == '__main__':
    main()

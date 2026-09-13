"""
Back-fill `sky image params` in already-generated JSONs.

Two things were missing from every JSON written before this script existed:

  * `header` was the literal string 'non serializable entry'.  NumpyEncoder's
    catch-all caught the astropy Header on its way out; the header itself was
    never lost, it is still in the matching .pickle (and in the source .fits).
  * there were no unit fields, so the physical units of the pixel values -- for
    the surveys that declare any -- were not reachable from the JSON at all.

This fills both in place.  The header is taken from the pickle when one is
present (guaranteed to be the header that produced this figure) and from the
.fits named in `sky image params['filename']` otherwise.

The JSONs are double-encoded -- json.load gives a string, which is itself JSON --
so they are rewritten the same way.

    python misc/backfill_sky_header.py <run_dir> [--dry-run] [--fits-dir DIR]

<run_dir> is the directory holding jsons/ and pickles/, e.g.
~/Downloads/tmp/test5_big.
"""

import argparse
import glob
import json
import os
import pickle
import sys
import warnings

warnings.filterwarnings('ignore')

UNIT_KEYS = (('BUNIT', 'bunit'), ('BTYPE', 'btype'), ('TELESCOP', 'telescope'),
             ('INSTRUME', 'instrument'), ('SURVEY', 'survey header'))


def header_text(h):
    try:
        return h.tostring(sep='\n', endcard=False, padding=False)
    except Exception:
        return None


def units_from(h):
    out = {}
    for fits_key, field in UNIT_KEYS:
        try:
            v = h.get(fits_key)
        except Exception:
            v = None
        if isinstance(v, str):
            v = v.strip() or None
        out[field] = v
    return out


def load_header(stem, run_dir, fits_dir):
    """(header, source) from the pickle if possible, else from the .fits."""
    pkl = os.path.join(run_dir, 'pickles', stem + '.pickle')
    if os.path.exists(pkl):
        try:
            with open(pkl, 'rb') as f:
                d = pickle.load(f)
            for k, v in d.items():
                if not k.startswith('plot'):
                    continue
                sip = ((v.get('data') or {}).get('data params') or {}).get('sky image params')
                if sip and hasattr(sip.get('header'), 'cards'):
                    return sip['header'], 'pickle'
        except Exception:
            pass
    return None, None


def load_header_from_fits(sip, fits_dir):
    fn = sip.get('filename')
    if not fn or not fits_dir:
        return None, None
    p = os.path.join(fits_dir, fn)
    if not os.path.exists(p):
        return None, None
    try:
        from astropy.io import fits
        return fits.getheader(p), 'fits'
    except Exception:
        return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run_dir')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--fits-dir', default='~/Dropbox/wwt_image_extraction/'
                                          'FullProcess_resources/astroquery_images/')
    a = ap.parse_args()
    run_dir = os.path.expanduser(a.run_dir)
    fits_dir = os.path.expanduser(a.fits_dir)

    files = sorted(glob.glob(os.path.join(run_dir, 'jsons', '*.json')))
    if not files:
        sys.exit('no jsons in ' + os.path.join(run_dir, 'jsons'))

    n = sky = patched = already = nohdr = 0
    src_count = {'pickle': 0, 'fits': 0}
    units_found = 0
    for path in files:
        n += 1
        with open(path) as f:
            outer = json.load(f)
        data = json.loads(outer) if isinstance(outer, str) else outer

        changed = False
        for k, v in data.items():
            if not k.startswith('plot'):
                continue
            sip = ((v.get('data') or {}).get('data params') or {}).get('sky image params')
            if not sip:
                continue
            sky += 1
            has_hdr = isinstance(sip.get('header'), str) and \
                'non serializable entry' not in sip['header']
            has_units = 'bunit' in sip
            if has_hdr and has_units:
                already += 1
                continue
            stem = os.path.splitext(os.path.basename(path))[0]
            h, src = load_header(stem, run_dir, fits_dir)
            if h is None:
                h, src = load_header_from_fits(sip, fits_dir)
            if h is None:
                nohdr += 1
                continue
            src_count[src] += 1
            txt = header_text(h)
            if txt:
                sip['header'] = txt
            u = units_from(h)
            sip.update(u)
            units_found += bool(u.get('bunit'))
            changed = True
        if changed:
            patched += 1
            if not a.dry_run:
                tmp = path + '.tmp'
                with open(tmp, 'w') as f:
                    json.dump(json.dumps(data), f)   # double-encoded, as written
                os.replace(tmp, path)

    print('jsons scanned          : %d' % n)
    print('  with a sky image     : %d' % sky)
    print('  already complete     : %d' % already)
    print('  patched              : %d%s' % (patched, '  (dry run, nothing written)'
                                             if a.dry_run else ''))
    print('    header from pickle : %d' % src_count['pickle'])
    print('    header from .fits  : %d' % src_count['fits'])
    print('  no header available  : %d' % nohdr)
    print('  of those patched, with a real BUNIT: %d' % units_found)


if __name__ == '__main__':
    main()

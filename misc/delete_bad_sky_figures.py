"""
Free the slots of real-sky figures that should be regenerated.

Two reasons a figure qualifies:

  --survey NAME   drawn from a survey now excluded from the pool.  TESS was
                  dropped because a third of its cutouts are unusable (see
                  EXCLUDED_SURVEYS in skyfigs/utils/distribution_utils.py);
                  leaving its figures in place would ship a survey the
                  generator claims never to draw from.

  --blank         the panel carries no signal -- all NaN, or a single constant
                  value.  These got through because the all-NaN guard used to
                  run after nan_to_num had already turned every NaN into 0.0.

THE DOWNLOAD CACHE IS NEVER TOUCHED.  Only the four per-figure outputs are
removed; the .fits cutouts stay in the astroquery cache, so the excluded
surveys' images remain available if they are ever wanted again.

    python misc/delete_bad_sky_figures.py --data_dir DIR --survey TESS --blank
    python misc/delete_bad_sky_figures.py --data_dir DIR --survey TESS --blank --apply
"""

import argparse
import json
import os
import re

import numpy as np

SUBDIRS = ('imgs', 'jsons', 'pickles', 'diags')


def classify(data_dir, block, surveys, want_blank):
    """[(stem, reason)] for every figure in `block` that should be refreshed."""
    jd = os.path.join(data_dir, 'jsons')
    pat = re.compile(r'Picture_(%s\d{5})\.json$' % block)
    out, seen = [], 0
    for f in sorted(os.listdir(jd)):
        if not pat.match(f):
            continue
        seen += 1
        try:
            d = json.load(open(os.path.join(jd, f)))
            while isinstance(d, str):
                d = json.loads(d)
            pl = d['plot0']
            sip = pl['data']['data params']['sky image params']
        except Exception:
            print('  [WARN] unreadable, leaving alone:', f)
            continue

        stem = os.path.splitext(f)[0]
        sv = sip.get('survey header')
        if surveys and sv in surveys:
            out.append((stem, 'survey=%s' % sv))
            continue
        if want_blank:
            try:
                c = np.asarray(pl['data']['colors'], dtype=float)
            except Exception:
                continue
            v = c[np.isfinite(c)]
            if v.size == 0 or np.unique(v).size <= 1:
                out.append((stem, 'blank'))
    return out, seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data_dir', required=True)
    ap.add_argument('--block', default='2',
                    help='index-block prefix: 2=real, 1=gmm, 0=contour')
    ap.add_argument('--survey', action='append', default=[],
                    help='delete figures from this survey (repeatable)')
    ap.add_argument('--blank', action='store_true',
                    help='delete figures whose panel is all-NaN or constant')
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    if not a.survey and not a.blank:
        ap.error('give --survey and/or --blank, else there is nothing to select')

    d = os.path.expanduser(a.data_dir)
    hits, seen = classify(d, a.block, set(a.survey), a.blank)
    print('figures scanned  : %d  (block %s)' % (seen, a.block))
    print('selected         : %d' % len(hits))
    by = {}
    for _, r in hits:
        by[r] = by.get(r, 0) + 1
    for r, n in sorted(by.items(), key=lambda kv: -kv[1]):
        print('    %-16s %d' % (r, n))
    if not hits:
        return

    stems = [s for s, _ in hits]
    files = []
    for s in stems:
        for sub in SUBDIRS:
            p = os.path.join(d, sub)
            if not os.path.isdir(p):
                continue
            for f in os.listdir(p):
                if os.path.splitext(f)[0] == s:
                    files.append(os.path.join(p, f))

    print('files to remove  : %d' % len(files))
    print('download cache   : NOT touched (cutouts stay available)')

    if not a.apply:
        print('\nDRY RUN -- nothing deleted.  Re-run with --apply.')
        return

    out = os.path.join(d, 'deleted_bad_sky_block%s.json' % a.block)
    json.dump({'hits': hits, 'files': files}, open(out, 'w'), indent=1)
    print('\nwrote manifest:', out)

    n = 0
    for f in files:
        try:
            os.remove(f); n += 1
        except OSError as e:
            print('  [WARN] %s: %s' % (f, e))
    print('removed %d files; %d slots free for regeneration' % (n, len(stems)))


if __name__ == '__main__':
    main()

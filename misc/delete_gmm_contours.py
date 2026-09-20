"""
Free the slots of the GMM contour figures so they can be regenerated.

Why only some of them: the contour family draws its distribution from
{random, linear, gmm}.  Only the GMM ones share the 'cluster std' policy with
the synthetic skies, and only that policy changed -- so the linear and random
contours stay exactly as they were copied from the previous run.

The generator's already-have check keys on imgs/ + jsons/, so removing a
figure's files is what marks its index for regeneration.  pickles/ and diags/
are removed too, to avoid leaving a half-figure behind.

Reversible: the originals are still in the previous run's directory, so
misc/copy_contours_to_triplets.py restores whatever this removes.

    python misc/delete_gmm_contours.py --data_dir DIR            # dry run
    python misc/delete_gmm_contours.py --data_dir DIR --apply
"""

import argparse
import json
import os
import re

SUBDIRS = ('imgs', 'jsons', 'pickles', 'diags')
CONTOUR = re.compile(r'Picture_(0\d{5})\.json$')


def gmm_contour_stems(data_dir, want='gmm'):
    """Stems of contour figures with at least one panel drawn from `want`."""
    jd = os.path.join(data_dir, 'jsons')
    hits, seen = [], 0
    for f in sorted(os.listdir(jd)):
        if not CONTOUR.match(f):
            continue
        seen += 1
        try:
            d = json.load(open(os.path.join(jd, f)))
            while isinstance(d, str):
                d = json.loads(d)
        except Exception:
            print('  [WARN] unreadable, leaving alone:', f)
            continue
        dists = {v.get('distribution') for k, v in d.items()
                 if k.startswith('plot') and isinstance(v, dict)}
        if want in dists:
            hits.append(os.path.splitext(f)[0])
    return hits, seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data_dir', required=True)
    ap.add_argument('--dist', default='gmm', choices=('gmm', 'linear', 'random'))
    ap.add_argument('--apply', action='store_true',
                    help='actually delete; without it nothing is touched')
    a = ap.parse_args()

    d = os.path.expanduser(a.data_dir)
    stems, seen = gmm_contour_stems(d, a.dist)
    print('contour figures scanned : %d' % seen)
    print('using %-18s: %d  (%.0f%%)'
          % (a.dist, len(stems), 100.0 * len(stems) / max(1, seen)))
    if not stems:
        return

    files = []
    for s in stems:
        for sub in SUBDIRS:
            p = os.path.join(d, sub)
            if not os.path.isdir(p):
                continue
            for f in os.listdir(p):
                if os.path.splitext(f)[0] == s:
                    files.append(os.path.join(p, f))

    print('files to remove         : %d' % len(files))
    print('index range             : %s .. %s' % (stems[0], stems[-1]))
    print()
    for f in files[:4]:
        print('   e.g.', f)
    print('   ...')

    if not a.apply:
        print('\nDRY RUN -- nothing deleted.  Re-run with --apply.')
        return

    out = os.path.join(d, 'deleted_%s_contours.json' % a.dist)
    json.dump({'stems': stems, 'files': files}, open(out, 'w'), indent=1)
    print('\nwrote manifest of what is being removed:', out)

    n = 0
    for f in files:
        try:
            os.remove(f); n += 1
        except OSError as e:
            print('  [WARN] %s: %s' % (f, e))
    print('removed %d files; %d contour slots now free for regeneration' % (n, len(stems)))


if __name__ == '__main__':
    main()

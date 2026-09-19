"""
Copy the contour figures from an existing run into a new dataset directory.

`create_figures_triplets_batch.py` regenerates the two SKY families with a new
angular-size policy; the contour family is unaffected by that and is reused
rather than re-rendered.  Contours live in the Picture_000001-Picture_100000
index block, so they are selected by index rather than by reading each json.

    python misc/copy_contours_to_triplets.py --src <run> --dst <run> [--dry-run]
"""

import argparse
import os
import shutil

SUBDIRS = ('imgs', 'jsons', 'pickles', 'diags')
CONTOUR_BLOCK = (1, 100000)          # Picture_NNNNNN, inclusive


def index_of(name):
    try:
        return int(os.path.splitext(name)[0].split('_')[-1])
    except (ValueError, IndexError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default='~/Downloads/tmp/waspPaper/data/astro_rescue/full_dataset')
    ap.add_argument('--dst', default='~/Downloads/tmp/waspPaper/data/full_dataset')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--overwrite', action='store_true')
    a = ap.parse_args()

    src = os.path.expanduser(a.src)
    dst = os.path.expanduser(a.dst)
    lo, hi = CONTOUR_BLOCK

    total = skipped = 0
    for sub in SUBDIRS:
        s = os.path.join(src, sub)
        if not os.path.isdir(s):
            print('[WARN] no %s in %s' % (sub, src))
            continue
        d = os.path.join(dst, sub)
        if not a.dry_run:
            os.makedirs(d, exist_ok=True)
        n = k = 0
        for name in sorted(os.listdir(s)):
            i = index_of(name)
            if i is None or not (lo <= i <= hi):
                continue
            out = os.path.join(d, name)
            if os.path.exists(out) and not a.overwrite:
                k += 1
                continue
            if not a.dry_run:
                shutil.copyfile(os.path.join(s, name), out)
            n += 1
        print('  %-8s %5d copied, %5d already there' % (sub, n, k))
        total += n
        skipped += k

    print()
    print('%d files copied%s, %d skipped' % (total,
          '  (dry run, nothing written)' if a.dry_run else '', skipped))
    print('src:', src)
    print('dst:', dst)


if __name__ == '__main__':
    main()

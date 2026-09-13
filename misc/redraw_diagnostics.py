#!/usr/bin/env python
"""
Regenerate diagnostic overlays from the saved jsons + images.

The diagnostic overlay is derived data -- everything it draws comes from the
json -- so it can be rebuilt at any time without regenerating figures.  That
matters because a bug in `add_annotations` only corrupts `diags/`, never the
training data in `jsons/` or the figures in `imgs/`.

By default only *real sky* figures are redrawn: the index bug this was written
for (nx/ny swapped in the visible-region filter) could only bite when a sky
image was non-square, so contour and GMM panels come out byte-identical.  Pass
--all to redo everything.

    python misc/redraw_diagnostics.py ~/Downloads/tmp/test5_big
    python misc/redraw_diagnostics.py <dir> --all --procs 8
"""
import argparse, json, os, sys, glob
import multiprocessing as mp

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def is_real_sky(d):
    for k in d:
        if not k.startswith('plot'):
            continue
        dp = (d[k].get('data') or {}).get('data params') or {}
        if dp.get('sky image params'):
            return True
    return False


def redraw(args):
    jf, test_dir, img_fmt = args
    import numpy as np
    from PIL import Image
    from skyfigs.utils.figure_gen_utils.misc import add_annotations_v1 as add_annotations

    name = os.path.splitext(os.path.basename(jf))[0]
    img_path = os.path.join(test_dir, 'imgs', name + '.' + img_fmt)
    if not os.path.exists(img_path):
        return (name, 'no image')
    try:
        with open(jf) as f:
            d = json.loads(json.load(f))
        img = np.array(Image.open(img_path).convert('RGB'))
        out = add_annotations(img, d, verbose=False)
        os.makedirs(os.path.join(test_dir, 'diags'), exist_ok=True)
        Image.fromarray(out).save(os.path.join(test_dir, 'diags', name + '.' + img_fmt))
        return (name, 'ok')
    except Exception as e:
        return (name, 'FAIL: %s' % e)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('test_dir')
    ap.add_argument('--all', action='store_true',
                    help='redraw every figure, not just the real-sky ones')
    ap.add_argument('--procs', type=int, default=max(1, mp.cpu_count() // 3))
    ap.add_argument('--img_format', default='jpeg')
    a = ap.parse_args()

    test_dir = os.path.expanduser(a.test_dir)
    jsons = sorted(glob.glob(os.path.join(test_dir, 'jsons', '*.json')))
    if not jsons:
        print('no jsons under', test_dir)
        return 1

    if a.all:
        todo = jsons
    else:
        todo = []
        for jf in jsons:
            try:
                with open(jf) as f:
                    if is_real_sky(json.loads(json.load(f))):
                        todo.append(jf)
            except Exception:
                pass
    print('%d figures total, redrawing %d%s  (%d procs)'
          % (len(jsons), len(todo), '' if a.all else ' real-sky', a.procs))
    if not todo:
        return 0

    work = [(jf, test_dir, a.img_format) for jf in todo]
    bad = 0
    with mp.Pool(a.procs) as pool:
        for i, (name, status) in enumerate(pool.imap_unordered(redraw, work), 1):
            if status != 'ok':
                bad += 1
                print('  %s: %s' % (name, status))
            if i % 50 == 0 or i == len(work):
                print('  %d/%d' % (i, len(work)), flush=True)
    print('done -- %d redrawn, %d failed' % (len(work) - bad, bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())

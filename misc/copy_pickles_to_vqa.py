"""
Re-issue the generator's pickles under their opaque VQA ids.

`full_dataset/pickles/Picture_NNNNNN.pickle` is the per-figure data dict the
generator wrote.  The released tree names everything by an opaque id instead --
the generator's own names encode the answer to the real-vs-synthetic question --
so this copies each pickle across under the id the lookup table assigns it:

    full_dataset/pickles/Picture_200123.pickle  ->  VQA/pickles/vqa_000456.pickle

Naming follows `VQA/imgs/` (`vqa_000456.jpeg`) rather than `VQA/qa_jsons/`
(`vqa_000456_qa.json`): these are the figure's DATA, not its questions, and
`_qa.pickle` is already what the LMM runs call their answer files
(`LMM_outputs_*/<model>/vqa_000456_qa.pickle`).  Pass --suffix _qa to use the
other convention anyway.

    python misc/copy_pickles_to_vqa.py [--dry-run] [--overwrite] [--verify N]
"""

import argparse
import hashlib
import json
import os
import shutil
import sys

DEFAULT_BASE = '~/Dropbox/WASP2026/data'


def digest(path, chunk=1 << 20):
    h = hashlib.blake2b(digest_size=16)
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(chunk), b''):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default=DEFAULT_BASE)
    ap.add_argument('--suffix', default='', help="e.g. '_qa' to match qa_jsons")
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--overwrite', action='store_true')
    ap.add_argument('--verify', type=int, default=20,
                    help='byte-compare this many copies afterwards (0 = none)')
    a = ap.parse_args()

    base = os.path.expanduser(a.base)
    src_dir = os.path.join(base, 'full_dataset', 'pickles')
    dst_dir = os.path.join(base, 'VQA', 'pickles')
    lut_path = os.path.join(base, 'VQA_private', 'vqa_lookup.json')

    for p in (src_dir, lut_path):
        if not os.path.exists(p):
            sys.exit('missing: ' + p)

    table = json.load(open(lut_path))['map']
    if not a.dry_run:
        os.makedirs(dst_dir, exist_ok=True)

    copied = skipped = missing = 0
    missing_ids = []
    pairs = []
    for vqa_id in sorted(table):
        stem = table[vqa_id]['source']
        src = os.path.join(src_dir, stem + '.pickle')
        dst = os.path.join(dst_dir, '%s%s.pickle' % (vqa_id, a.suffix))
        if not os.path.exists(src):
            missing += 1
            missing_ids.append((vqa_id, stem))
            continue
        pairs.append((src, dst))
        if os.path.exists(dst) and not a.overwrite:
            skipped += 1
            continue
        if not a.dry_run:
            # copyfile, not copy2: content only, no timestamps or flags carried
            # into the released tree
            shutil.copyfile(src, dst)
        copied += 1

    print('lookup table : %d ids' % len(table))
    print('source       : %s' % src_dir)
    print('destination  : %s' % dst_dir)
    print('naming       : <vqa_id>%s.pickle' % a.suffix)
    print()
    print('copied       : %d%s' % (copied, '  (dry run, nothing written)' if a.dry_run else ''))
    print('already there: %d' % skipped)
    print('source missing: %d' % missing)
    for vqa_id, stem in missing_ids[:5]:
        print('   %s -> %s.pickle' % (vqa_id, stem))

    if a.verify and not a.dry_run and pairs:
        step = max(1, len(pairs) // a.verify)
        checked = bad = 0
        for src, dst in pairs[::step][:a.verify]:
            if not os.path.exists(dst):
                continue
            checked += 1
            if digest(src) != digest(dst):
                bad += 1
                print('   [MISMATCH]', dst)
        print()
        print('verified     : %d copies byte-identical to their source, %d bad'
              % (checked - bad, bad))


if __name__ == '__main__':
    main()

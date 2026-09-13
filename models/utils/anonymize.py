"""
Opaque, shuffled IDs for the released VQA set.

The generator names figures in disjoint index blocks so the three categories
cannot drift during generation:

    Picture_000001+   contour
    Picture_100001+   sky / gaussian-mixture   <- "1" == synthetic
    Picture_200001+   sky / real cutout        <- "2" == real

That is convenient while generating and a problem once released: the Level 3
question is "real image of the sky, or gaussian mixture model?", and the
filename answers it.  The models themselves never see filenames -- the payloads
carry base64 pixels only -- but anything that *does* see them is affected:
human spot-checks, anything that groups or sorts by name, and the published
dataset.

This module assigns each figure an opaque id (`vqa_000001`) in shuffled order,
and keeps a PRIVATE lookup table mapping back to the source figure.  Release
`imgs/` + `qa_jsons/`; keep the lookup table.

Two properties worth relying on:

* **Deterministic** given `seed`, so a build can be reproduced.
* **Stable across re-runs.**  An existing lookup table is loaded and extended,
  never reshuffled -- otherwise re-running would silently repoint ids that had
  already been released or scored.
"""

import json
import os
import random
import shutil


LOOKUP_VERSION = 1


def _category_of(stem, blocks=None):
    """
    Best-effort category from the generator's index blocks -- recorded in the
    private table only, as a convenience for later analysis.  Never written
    anywhere released.
    """
    if blocks is None:
        blocks = [(0, 100000, 'contour'),
                  (100000, 200000, 'sky-gmm'),
                  (200000, 10 ** 9, 'sky-real')]
    try:
        i = int(stem.split('_')[-1])
    except (ValueError, IndexError):
        return 'unknown'
    for lo, hi, name in blocks:
        if lo < i <= hi:
            return name
    return 'unknown'


def load_lookup_table(path):
    """The existing table, or an empty one.  Missing file is not an error."""
    if path and os.path.exists(path):
        with open(path) as f:
            t = json.load(f)
        if t.get('version') != LOOKUP_VERSION:
            raise ValueError('lookup table %s has version %r, expected %r'
                             % (path, t.get('version'), LOOKUP_VERSION))
        return t
    return {'version': LOOKUP_VERSION, 'seed': None, 'prefix': None, 'map': {}}


def build_index_map(source_stems, lookup_path=None, seed=20260913,
                    prefix='vqa_', width=6, verbose=True):
    """
    {source_stem -> opaque_id} for every stem given.

    Stems already present in the lookup table keep their id.  Only genuinely new
    stems are shuffled and appended, so adding figures to a run never disturbs
    ids that already exist.

    Returns (forward_map, table) -- write `table` with write_lookup_table().
    """
    table = load_lookup_table(lookup_path)
    if table['seed'] is None:
        table['seed'] = seed
        table['prefix'] = prefix
    # id -> source, as stored; invert for the lookup we need here
    existing = {v['source']: k for k, v in table['map'].items()}

    new = [s for s in source_stems if s not in existing]
    if new:
        # shuffle only the new ones, deterministically, then hand out the
        # lowest unused id numbers
        rng = random.Random(table['seed'] + len(existing))
        new = sorted(new)              # sort first so input order can't matter
        rng.shuffle(new)
        used = {int(k[len(table['prefix']):]) for k in table['map']} or {0}
        nxt = max(used) + 1
        for s in new:
            vid = '%s%0*d' % (table['prefix'], width, nxt)
            table['map'][vid] = {'source': s, 'category': _category_of(s)}
            existing[s] = vid
            nxt += 1

    if verbose:
        print('index map: %d total (%d new this build), seed=%s'
              % (len(table['map']), len(new), table['seed']))
    return {s: existing[s] for s in source_stems}, table


def write_lookup_table(table, path, verbose=True):
    """Write the PRIVATE table.  Keep this out of any released directory."""
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(table, f, indent=1, sort_keys=True)
    if verbose:
        print('wrote lookup table:', path, '(%d entries -- keep private)' % len(table['map']))


def resolve(lookup_path, vqa_id=None, source_stem=None):
    """Look up either direction: id -> source stem, or source stem -> id."""
    table = load_lookup_table(lookup_path)
    if vqa_id is not None:
        e = table['map'].get(vqa_id)
        return e['source'] if e else None
    if source_stem is not None:
        for k, v in table['map'].items():
            if v['source'] == source_stem:
                return k
    return None


def copy_image_as(src_img, out_dir, vqa_id, ext=None, overwrite=False, verbose=False):
    """
    Place the figure in the released images directory under its opaque id.

    Copied rather than symlinked so the released tree stands alone and carries
    no path back to the source name.
    """
    if not os.path.exists(src_img):
        return None
    if ext is None:
        ext = os.path.splitext(src_img)[1].lstrip('.')
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, '%s.%s' % (vqa_id, ext))
    if overwrite or not os.path.exists(dst):
        shutil.copyfile(src_img, dst)      # copyfile: content only, no metadata
        if verbose:
            print('  %s -> %s' % (os.path.basename(src_img), os.path.basename(dst)))
    return dst

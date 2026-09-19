"""
Cache SIMBAD angular sizes for the objects the sky-image generator can draw.

`create_figures_triplets_batch.py` sizes each real cutout from the object's own
angular extent when SIMBAD knows one, and falls back to a survey-derived range
when it does not.  SIMBAD is queried once, here, into
`resources/simbad_object_sizes.csv`, so generation stays offline and
reproducible.

Expect most objects to have NO size: the list is dominated by stars, which are
point sources.  On a 60-name sample only 23% had `galdim_majaxis`, and the ones
that did were galaxies and extended objects.  That is not a lookup failure and
the fallback is the normal path, not the exception.

    python misc/fetch_simbad_object_sizes.py [--limit N] [--batch 400]
                                             [--out PATH] [--source cache|list]

Resumable: objects already in the output file are not re-queried, so an
interrupted run can simply be repeated.
"""

import argparse
import csv
import os
import pickle
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(_HERE, '..', 'resources', 'simbad_object_sizes.csv')
CACHE = '~/Dropbox/wwt_image_extraction/FullProcess_resources/astroquery_images/'
OBJ_LIST = os.path.join(_HERE, '..', 'resources', 'object_wavelength_pairs.pickle')
FIELDS = ['object', 'otype', 'majaxis_arcmin', 'minaxis_arcmin']


def objects_from_cache(cache=CACHE):
    """
    Objects that already have a downloaded cutout -- i.e. the ones the generator
    can actually draw.  Cache filenames replace spaces with '_', which is undone
    here so the names match what SIMBAD expects.
    """
    d = os.path.expanduser(cache)
    if not os.path.isdir(d):
        return []
    keys = set()
    for f in os.listdir(d):
        if '_OBJ_' in f and '_SURVEY_' in f:
            keys.add(f.split('_OBJ_')[1].split('_SURVEY_')[0])
    return sorted(k.replace('_', ' ').strip() for k in keys)


def objects_from_list(path=OBJ_LIST):
    with open(os.path.expanduser(path), 'rb') as f:
        return sorted({o['object'] for o in pickle.load(f)})


def load_existing(path):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return {r['object']: r for r in csv.DictReader(f)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--source', choices=('cache', 'list'), default='cache')
    ap.add_argument('--batch', type=int, default=400)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--delay', type=float, default=1.0)
    a = ap.parse_args()

    from astroquery.simbad import Simbad

    out_path = os.path.abspath(a.out)
    have = load_existing(out_path)
    names = objects_from_cache() if a.source == 'cache' else objects_from_list()
    todo = [n for n in names if n not in have]
    if a.limit:
        todo = todo[:a.limit]

    print('%d candidate objects, %d already cached, %d to query'
          % (len(names), len(have), len(todo)))
    if not todo:
        print('nothing to do')
        return

    s = Simbad()
    s.add_votable_fields('galdim_majaxis', 'galdim_minaxis', 'otype')
    s.TIMEOUT = 120

    got = 0
    for i in range(0, len(todo), a.batch):
        chunk = todo[i:i + a.batch]
        try:
            t = s.query_objects(chunk)
        except Exception as e:
            print('   [WARN] batch %d failed: %s' % (i // a.batch, type(e).__name__))
            t = None
        if t is not None:
            # query_objects returns rows in the order asked; the id column name
            # has moved around between astroquery versions, so match by position
            for name, row in zip(chunk, t):
                def val(col):
                    if col not in t.colnames:
                        return ''
                    v = row[col]
                    try:
                        return '' if v is None or v is __import__('numpy').ma.masked else str(v)
                    except Exception:
                        return ''
                rec = {'object': name, 'otype': val('otype'),
                       'majaxis_arcmin': val('galdim_majaxis'),
                       'minaxis_arcmin': val('galdim_minaxis')}
                have[name] = rec
                got += bool(rec['majaxis_arcmin'])
        # write after every batch, so an interrupted run keeps what it had
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore')
            w.writeheader()
            for k in sorted(have):
                w.writerow(have[k])
        print('   %d/%d queried, %d with a size so far'
              % (min(i + a.batch, len(todo)), len(todo), got))
        time.sleep(a.delay)

    sized = sum(1 for r in have.values() if r.get('majaxis_arcmin'))
    print()
    print('wrote', out_path)
    print('  %d objects, %d with an angular size (%.0f%%)'
          % (len(have), sized, 100.0 * sized / max(len(have), 1)))


if __name__ == '__main__':
    main()

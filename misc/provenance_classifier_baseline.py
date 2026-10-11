"""
Feature-based baseline for the sky provenance question: can a simple
classifier tell a real survey cutout from a GMM-generated sky field?

Why
---
The paper asks LMMs "What is the underlying distribution used to create the
data in this figure? [gaussian mixture model, real image of the sky]" and
they answer "real" almost regardless of the truth.  A reviewer asked for a
classifier baseline: is the question answerable from image content at all, or
are the two families indistinguishable?  An earlier draft quoted 92% (5-fold
CV) for a gradient-boosted classifier on four low-level features, but the code
behind that number was never saved.  This script recomputes it from the
released dataset so the number is reproducible.

Features (one row per sky figure, computed from the stored data array
`plot0.data.colors` and the figure's own ground-truth answers)
------------------------------------------------------------------------
  field size       log10 sqrt(field width * field height), arcmin -- the
                   angular extent the figure shows.  GMM fields are drawn to
                   the same angular-size distribution, so this one should be
                   close to uninformative; it is kept as a check on that.
  concentration    fraction of the background-subtracted signal held by the
                   brightest `--top-frac` of pixels (background = data
                   minimum).  Point-source-dominated fields score high,
                   diffuse ones low.
  colour span      log10(max - min) of the data -- the dynamic range behind
                   the colorbar.
  colour min sign  sign of the data minimum (-1, 0, +1).

Model: sklearn GradientBoostingClassifier (defaults), stratified 5-fold CV.
Reported: mean +/- std accuracy over folds; accuracy restricted to the 170
sky figures in the n255 LMM evaluation (from out-of-fold predictions, so no
figure is scored by a model that saw it); single-feature accuracies; and the
majority-class baseline.

Read-only: nothing in the dataset is modified.  `--out` writes the feature
table as CSV for inspection.

    python misc/provenance_classifier_baseline.py
    python misc/provenance_classifier_baseline.py --out provenance_features.csv
"""

import argparse
import glob
import json
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_predict

FEATURES = ['field size', 'concentration', 'colour span', 'colour min sign']


def _answers(rec):
    """Flatten every ground-truth answer in a qa json into {name: value}."""
    out = {}
    for lvl in rec['VQA'].values():
        for items in lvl.values():
            for name, e in items.items():
                # plot-level questions nest one level deeper, under 'plot0'
                entry = e if 'A' in e else e.get('plot0', {})
                a = entry.get('A')
                if isinstance(a, dict) and name in a:
                    out[name] = a[name]
    return out


def figure_features(rec, top_frac):
    """The four features for one sky figure, or None if it is not a sky panel."""
    p = rec['plot0']
    if p['type'] != 'image of the sky':
        return None
    data = np.asarray(p['data']['colors'], dtype=float)
    data = data[np.isfinite(data)]
    dmin, dmax = data.min(), data.max()

    signal = np.sort(data - dmin)[::-1]
    ntop = max(1, int(round(top_frac * signal.size)))
    total = signal.sum()
    concentration = signal[:ntop].sum() / total if total > 0 else 0.0

    ans = _answers(rec)
    width, height = float(ans['field width']), float(ans['field height'])

    return {
        'vqa_id': rec['vqa_id'],
        'label': 'gmm' if p.get('distribution') == 'gmm' else 'real',
        'field size': np.log10(np.sqrt(width * height)),
        'concentration': concentration,
        'colour span': np.log10(dmax - dmin) if dmax > dmin else -12.0,
        'colour min sign': float(np.sign(dmin)),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--qa-dir', default='~/astro_sky_image_vqa/VQA_full/qa_jsons/')
    ap.add_argument('--eval-dir', default='~/astro_sky_image_vqa/LMM_outputs_n255/gemini/',
                    help='directory of run pickles naming the LMM-evaluated figures')
    ap.add_argument('--top-frac', type=float, default=0.05,
                    help='brightest-pixel fraction used for concentration')
    ap.add_argument('--folds', type=int, default=5)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--out', default=None, help='optional CSV of the feature table')
    args = ap.parse_args()

    rows = []
    for fp in sorted(glob.glob(os.path.join(os.path.expanduser(args.qa_dir), '*_qa.json'))):
        with open(fp) as f:
            rec = json.loads(json.load(f))
        r = figure_features(rec, args.top_frac)
        if r is not None:
            rows.append(r)
    df = pd.DataFrame(rows)
    if args.out:
        df.to_csv(args.out, index=False)

    X = df[FEATURES].values
    y = (df['label'] == 'real').astype(int).values
    cv = StratifiedKFold(n_splits=args.folds, shuffle=True, random_state=args.seed)

    def oof(cols):
        clf = GradientBoostingClassifier(random_state=args.seed)
        return cross_val_predict(clf, df[cols].values, y, cv=cv)

    pred = oof(FEATURES)
    fold_acc = [np.mean(pred[te] == y[te]) for _, te in cv.split(X, y)]

    print('sky figures: %d  (real %d, gmm %d)' % (len(df), y.sum(), len(y) - y.sum()))
    print('majority-class baseline: %.1f%%' % (100 * max(y.mean(), 1 - y.mean())))
    print('gradient-boosted, %d-fold CV, all four features: %.1f%% +/- %.1f%% (fold std)'
          % (args.folds, 100 * np.mean(fold_acc), 100 * np.std(fold_acc)))
    for lab, v in (('real', 1), ('gmm', 0)):
        print('   recall on %-4s: %.1f%%' % (lab, 100 * np.mean(pred[y == v] == v)))

    evaluated = {os.path.basename(p).removesuffix('_qa.pickle')
                 for p in glob.glob(os.path.join(os.path.expanduser(args.eval_dir), '*_qa.pickle'))}
    sel = df['vqa_id'].isin(evaluated).values
    if sel.any():
        print('   on the %d sky figures in the LMM evaluation (out-of-fold): %.1f%%'
              % (sel.sum(), 100 * np.mean(pred[sel] == y[sel])))

    print('\nsingle-feature accuracy (same CV):')
    for f in FEATURES:
        print('   %-16s %.1f%%' % (f, 100 * np.mean(oof([f]) == y)))


if __name__ == '__main__':
    main()

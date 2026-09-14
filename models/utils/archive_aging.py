"""
Archive-style page aging for the VQA figures.

Applies the "archive" preset from
`models/test_models/page_aging/page_aging.ipynb` -- decades in a box, then
scanned: ink bleed and mottling, yellowed and textured paper, stains, a fold, a
page border, a little geometry and sensor noise -- and optionally drops the
result to grayscale.

Two properties the calling notebooks rely on:

* **Every figure is aged differently.**  Which effects fire, and the parameters
  each one samples, are drawn per figure.
* **But identically across models.**  The per-figure seed is derived from the
  figure's own id with a stable hash, not from the clock and not from Python's
  builtin `hash()` (which is salted per process).  So the chatgpt, claude and
  gemini runs age `vqa_000123` exactly the same way, and comparing them is not
  confounded by the aging.  Re-running months later reproduces it too.

The effects held back in the notebook (Scribbles, BookBinding, WaterMark,
Letterpress) are held back here as well: they add marks unrelated to the figure,
bend the page out of shape, or restyle the ink against the colormap.
"""

import hashlib
import json
import os

import cv2
import numpy as np

# the "archive" preset: (phase, effect name, probability it fires)
ARCHIVE_PRESET = [
    ('ink',   'InkBleed',            0.8),
    ('ink',   'BleedThrough',        0.6),
    ('ink',   'InkMottling',         0.5),
    ('paper', 'ColorPaper',          0.9),
    ('paper', 'NoiseTexturize',      0.8),
    ('paper', 'BrightnessTexturize', 0.7),
    ('paper', 'LightingGradient',    0.4),
    ('post',  'Stains',              0.8),
    ('post',  'Folding',             0.6),
    ('post',  'PageBorder',          0.5),
    ('post',  'ShadowCast',          0.4),
    ('post',  'Geometric',           0.6),
    ('post',  'SubtleNoise',         0.7),
    ('post',  'Jpeg',                0.7),
]

DEFAULT_BASE_SEED = 20260914
DEFAULT_GRAY_PROB = 0.5


def _factory(name):
    """Build one augraphy augmentation.  Imported lazily so importing this
    module does not require augraphy until it is actually used."""
    import augraphy as ag
    if name == 'Geometric':
        return ag.Geometric(rotate_range=(-3, 3), p=1)
    return getattr(ag, name)(p=1)


def image_seed(vqa_id, base_seed=DEFAULT_BASE_SEED):
    """
    A stable 32-bit seed for one figure.

    blake2b rather than hash(): the builtin is salted per interpreter, so it
    would give a different aging in every process -- and therefore a different
    aged image for each of the three model runs.
    """
    h = hashlib.blake2b(('%s|%d' % (vqa_id, base_seed)).encode(), digest_size=8)
    return int.from_bytes(h.digest(), 'big') % (2 ** 31 - 1)


def plan_for(vqa_id, base_seed=DEFAULT_BASE_SEED, gray_prob=DEFAULT_GRAY_PROB):
    """
    What will be done to this figure: which effects fire, whether it goes
    grayscale, and the seed that fixes every sampled parameter.

    Returns a plain dict -- this is what gets recorded alongside the answers.
    """
    seed = image_seed(vqa_id, base_seed)
    rng = np.random.default_rng(seed)
    effects = [(phase, name) for phase, name, prob in ARCHIVE_PRESET
               if rng.random() < prob]
    grayscale = bool(rng.random() < gray_prob)
    return {'preset': 'archive',
            'seed': int(seed),
            'base_seed': int(base_seed),
            'gray_prob': float(gray_prob),
            'grayscale': grayscale,
            'effects': [n for _, n in effects],
            'effects_by_phase': {ph: [n for p, n in effects if p == ph]
                                 for ph in ('ink', 'paper', 'post')}}


def apply_plan(img_bgr, plan):
    """Age one BGR image according to `plan`.  Returns a new BGR image."""
    from augraphy import AugraphyPipeline
    by_phase = plan['effects_by_phase']
    pipeline = AugraphyPipeline(
        ink_phase=[_factory(n) for n in by_phase.get('ink', [])],
        paper_phase=[_factory(n) for n in by_phase.get('paper', [])],
        post_phase=[_factory(n) for n in by_phase.get('post', [])],
        random_seed=plan['seed'])
    out = np.asarray(pipeline(img_bgr.copy()))
    if out.ndim == 2:
        out = cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)
    if plan['grayscale']:
        # back to 3 channels: the API payloads and everything downstream expect
        # a colour image, it just happens to have no colour left in it
        out = cv2.cvtColor(cv2.cvtColor(out, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    return out


def build_aged_images(vqa_ids, imgs_dir, aged_dir, img_format='jpeg',
                      base_seed=DEFAULT_BASE_SEED, gray_prob=DEFAULT_GRAY_PROB,
                      manifest_path=None, overwrite=False, verbose=True):
    """
    Age every figure in `vqa_ids` into `aged_dir`, and return the manifest.

    Skips a figure whose aged file already exists unless `overwrite` -- so the
    second and third model runs reuse the images the first one produced rather
    than regenerating them (they would be identical anyway; this just saves the
    time).
    """
    imgs_dir = os.path.expanduser(imgs_dir)
    aged_dir = os.path.expanduser(aged_dir)
    os.makedirs(aged_dir, exist_ok=True)

    manifest = {}
    if manifest_path and os.path.exists(manifest_path) and not overwrite:
        with open(manifest_path) as f:
            manifest = json.load(f)

    made = reused = missing = 0
    for vqa_id in vqa_ids:
        src = os.path.join(imgs_dir, '%s.%s' % (vqa_id, img_format))
        dst = os.path.join(aged_dir, '%s.%s' % (vqa_id, img_format))
        plan = plan_for(vqa_id, base_seed=base_seed, gray_prob=gray_prob)
        manifest[vqa_id] = plan
        if os.path.exists(dst) and not overwrite:
            reused += 1
            continue
        img = cv2.imread(src)
        if img is None:
            missing += 1
            if verbose:
                print('[WARN] no source image:', src)
            continue
        cv2.imwrite(dst, apply_plan(img, plan))
        made += 1

    if manifest_path:
        os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=1, sort_keys=True)

    if verbose:
        ngray = sum(1 for p in manifest.values() if p['grayscale'])
        print('aged images: %d written, %d reused, %d source images missing'
              % (made, reused, missing))
        print('  grayscale : %d of %d (%.0f%%)'
              % (ngray, len(manifest), 100.0 * ngray / max(len(manifest), 1)))
        print('  aged_dir  :', aged_dir)
        if manifest_path:
            print('  manifest  :', manifest_path)
    return manifest

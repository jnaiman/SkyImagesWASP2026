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

# The gentler counterpart, matching 'archive-light' in page_aging.ipynb: the
# same journey, every effect softened and firing less often, so the figure stays
# legible while still reading as paper.
ARCHIVE_LIGHT_PRESET = [
    ('ink',   'InkBleed-soft',            0.5),
    ('ink',   'InkMottling-soft',         0.3),
    ('paper', 'ColorPaper-soft',          0.8),
    ('paper', 'NoiseTexturize-soft',      0.5),
    ('paper', 'BrightnessTexturize-soft', 0.5),
    ('post',  'Stains-soft',              0.4),
    ('post',  'Folding',                  0.25),
    ('post',  'ShadowCast-soft',          0.25),
    ('post',  'Geometric-soft',           0.5),
    ('post',  'SubtleNoise',              0.5),
    ('post',  'Jpeg-soft',                0.6),
]

PRESETS = {'archive': ARCHIVE_PRESET, 'archive-light': ARCHIVE_LIGHT_PRESET}

DEFAULT_BASE_SEED = 20260914
DEFAULT_GRAY_PROB = 0.5
DEFAULT_PRESET = 'archive'


def use_page_background(color=(255, 255, 255)):
    """
    Make augraphy invent white paper instead of black holes.

    `Geometric`'s rotation fills the corner wedges through `rotate_image_PIL`,
    whose `background_value` defaults to (0, 0, 0) and which geometric.py calls
    WITHOUT passing one -- so the colour is not reachable through any
    augmentation parameter and has to be patched at the helper.  On a white page
    an 8 degree rotation came out 23% pure black; patched, 0%.

    Patched in every module that imported the helper by name, since
    `from ... import rotate_image_PIL` binds a separate reference in each.
    """
    import augraphy.augmentations.lib as _lib
    import augraphy.augmentations.geometric as _geo
    import augraphy.augmentations.pageborder as _pb
    import augraphy.augmentations.folding as _fold
    original = getattr(_lib, '_rotate_image_PIL_original', _lib.rotate_image_PIL)
    _lib._rotate_image_PIL_original = original

    def rotate_image_PIL(image, angle, background_value=tuple(color), expand=0):
        return original(image, angle, background_value=background_value,
                        expand=expand)

    for module in (_lib, _geo, _pb, _fold):
        module.rotate_image_PIL = rotate_image_PIL


def _factory(name, page_background=None):
    """
    Build one augraphy augmentation.  Imported lazily so importing this module
    does not require augraphy until it is actually used.

    The `-soft` variants are the same augmentations with their parameters pulled
    back; they are what 'archive-light' is made of.
    """
    import augraphy as ag
    bg = tuple(page_background) if page_background else None

    # full strength
    if name == 'Geometric':
        return ag.Geometric(rotate_range=(-3, 3), p=1)
    if name == 'Folding':
        return ag.Folding(backdrop_color=bg, p=1) if bg else ag.Folding(p=1)
    if name == 'PageBorder':
        return (ag.PageBorder(page_border_background_color=bg, p=1) if bg
                else ag.PageBorder(p=1))

    # softened
    if name == 'InkBleed-soft':
        return ag.InkBleed(intensity_range=(0.1, 0.3), severity=(0.1, 0.2), p=1)
    if name == 'InkMottling-soft':
        return ag.InkMottling(ink_mottling_alpha_range=(0.05, 0.12), p=1)
    if name == 'ColorPaper-soft':
        return ag.ColorPaper(hue_range=(28, 40), saturation_range=(3, 12), p=1)
    if name == 'NoiseTexturize-soft':
        return ag.NoiseTexturize(sigma_range=(2, 4), turbulence_range=(2, 3), p=1)
    if name == 'BrightnessTexturize-soft':
        return ag.BrightnessTexturize(texturize_range=(0.95, 0.99),
                                      deviation=0.03, p=1)
    if name == 'Stains-soft':
        return ag.Stains(stains_blend_alpha=0.18, p=1)
    if name == 'ShadowCast-soft':
        return ag.ShadowCast(shadow_opacity_range=(0.05, 0.2),
                             shadow_blur_kernel_range=(201, 401), p=1)
    if name == 'Geometric-soft':
        return ag.Geometric(rotate_range=(-1, 1), p=1)
    if name == 'Jpeg-soft':
        return ag.Jpeg(quality_range=(70, 95), p=1)

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


def plan_for(vqa_id, base_seed=DEFAULT_BASE_SEED, gray_prob=DEFAULT_GRAY_PROB,
             preset=DEFAULT_PRESET, page_background=None):
    """
    What will be done to this figure: which effects fire, whether it goes
    grayscale, and the seed that fixes every sampled parameter.

    Returns a plain dict -- this is what gets recorded alongside the answers.

    `page_background` is recorded rather than assumed so old plans stay
    reproducible: a plan written before this option existed has no such key, and
    reads back as None, which is augraphy's original black fill.
    """
    seed = image_seed(vqa_id, base_seed)
    rng = np.random.default_rng(seed)
    # one draw per effect, in preset order, then one for the grayscale coin --
    # do not reorder, it would repoint every figure's aging
    effects = [(phase, name) for phase, name, prob in PRESETS[preset]
               if rng.random() < prob]
    grayscale = bool(rng.random() < gray_prob)
    return {'preset': preset,
            'page background': list(page_background) if page_background else None,
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
    bg = plan.get('page background')
    if bg:
        use_page_background(bg)
    pipeline = AugraphyPipeline(
        ink_phase=[_factory(n, bg) for n in by_phase.get('ink', [])],
        paper_phase=[_factory(n, bg) for n in by_phase.get('paper', [])],
        post_phase=[_factory(n, bg) for n in by_phase.get('post', [])],
        random_seed=plan['seed'])
    out = np.asarray(pipeline(img_bgr.copy()))
    if out.ndim == 2:
        out = cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)
    if plan['grayscale']:
        # back to 3 channels: the API payloads and everything downstream expect
        # a colour image, it just happens to have no colour left in it
        out = cv2.cvtColor(cv2.cvtColor(out, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    return out


def _plan_key(plan):
    """The part of a plan that determines what the image looks like."""
    return (plan.get('preset'), plan.get('seed'), plan.get('grayscale'),
            tuple(plan.get('effects') or ()), tuple(plan.get('page background') or ()))


def _is_grayscale(path):
    """True if the file on disk has no colour left in it."""
    img = cv2.imread(path)
    if img is None or img.ndim != 3:
        return None
    return bool(np.array_equal(img[:, :, 0], img[:, :, 1]) and
                np.array_equal(img[:, :, 1], img[:, :, 2]))


def build_aged_images(vqa_ids, imgs_dir, aged_dir, img_format='jpeg',
                      base_seed=DEFAULT_BASE_SEED, gray_prob=DEFAULT_GRAY_PROB,
                      preset=DEFAULT_PRESET, page_background=None,
                      manifest_path=None, overwrite=False, verify=True,
                      verbose=True):
    """
    Age every figure in `vqa_ids` into `aged_dir`, and return the manifest.

    Skips a figure whose aged file already exists unless `overwrite` -- so the
    second and third model runs reuse the images the first one produced rather
    than regenerating them.

    A REUSED image keeps the plan it was actually made with.  This matters:
    recomputing the plan here would use today's `gray_prob` / `base_seed` /
    `preset`, and if any of those has changed since the images were written the
    manifest would describe an image that does not exist -- and the driver
    stamps that plan onto every answer.  When the recomputed plan disagrees with
    the stored one the difference is reported rather than silently applied; pass
    `overwrite=True` to actually regenerate with the current settings.

    `verify` additionally checks each reused file's pixels against its recorded
    grayscale flag, which catches a manifest that has drifted from the images
    for any reason at all.
    """
    imgs_dir = os.path.expanduser(imgs_dir)
    aged_dir = os.path.expanduser(aged_dir)
    os.makedirs(aged_dir, exist_ok=True)

    manifest = {}
    if manifest_path and os.path.exists(manifest_path) and not overwrite:
        with open(manifest_path) as f:
            manifest = json.load(f)

    made = reused = missing = 0
    conflicts, unrecorded, mismatched = [], [], []
    for vqa_id in vqa_ids:
        src = os.path.join(imgs_dir, '%s.%s' % (vqa_id, img_format))
        dst = os.path.join(aged_dir, '%s.%s' % (vqa_id, img_format))
        plan = plan_for(vqa_id, base_seed=base_seed, gray_prob=gray_prob,
                        preset=preset, page_background=page_background)

        if os.path.exists(dst) and not overwrite:
            stored = manifest.get(vqa_id)
            if stored is None:
                # image with no record of how it was made; the recomputed plan
                # is a guess, so say so rather than pretend
                plan['unverified'] = True
                manifest[vqa_id] = plan
                unrecorded.append(vqa_id)
            else:
                if _plan_key(stored) != _plan_key(plan):
                    conflicts.append(vqa_id)
                manifest[vqa_id] = stored          # keep what made the image
            if verify:
                on_disk = _is_grayscale(dst)
                if on_disk is not None and on_disk != manifest[vqa_id].get('grayscale'):
                    mismatched.append(vqa_id)
            reused += 1
            continue

        manifest[vqa_id] = plan
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
        print('preset     : %s%s' % (preset, '  (white page background)'
                                     if page_background else ''))
        print('aged images: %d written, %d reused, %d source images missing'
              % (made, reused, missing))
        print('  grayscale : %d of %d (%.0f%%)   [requested gray_prob=%.2f]'
              % (ngray, len(manifest), 100.0 * ngray / max(len(manifest), 1),
                 gray_prob))
        if conflicts:
            print('  [WARN] %d reused image(s) were made with DIFFERENT settings than'
                  ' the ones requested now' % len(conflicts))
            print('         (gray_prob / base_seed / preset / background changed).')
            print('         The manifest keeps the ORIGINAL plans, which describe the'
                  ' files on disk.')
            print('         Pass overwrite=True to regenerate them with the current'
                  ' settings.')
            print('         e.g.', ', '.join(conflicts[:5]),
                  '...' if len(conflicts) > 5 else '')
        if unrecorded:
            print('  [WARN] %d reused image(s) had no manifest entry; their plans are'
                  ' recomputed and marked "unverified"' % len(unrecorded))
        if mismatched:
            print('  [WARN] %d reused image(s) do not match their recorded grayscale'
                  ' flag -- the manifest has drifted from the files: %s'
                  % (len(mismatched), ', '.join(mismatched[:5])))
        print('  aged_dir  :', aged_dir)
        if manifest_path:
            print('  manifest  :', manifest_path)
    return manifest

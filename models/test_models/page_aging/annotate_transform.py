"""
Annotation boxes that survive page aging.

`add_annotations_v1` in `skyfigs/utils/figure_gen_utils/misc.py` draws the
stored bounding boxes -- plot square, title, x/y labels, colorbar -- onto a
clean figure.  It assumes the image it draws on is the image the coordinates
came from, which stops being true the moment the page is aged: `Geometric`
rotates and pads the canvas, so every stored box lands in the wrong place.

`add_annotations_transform` below is that function reworked so the annotations
are carried *through* the aging pipeline with the image.

Why corners rather than boxes
-----------------------------
Augraphy will transform either `bounding_boxes` or `keypoints` alongside the
page, but they are not equally good here.  Measured on a 20 degree rotation of a
300x200 box at (100,100):

    box    before [100, 100, 400, 300]  after [129, 265, 429, 465]
    corner before [[100,100],[400,100],[400,300],[100,300]]
           after  [[129,265],[411,163],[479,351],[197,453]]

The box came back the same size, merely translated -- augraphy tracks the
padding offset for boxes but not the rotation.  The corners came back genuinely
rotated.  So this module hands augraphy the four corners of each box as
keypoints and draws the resulting quadrilateral, which follows the page.
`quad_to_aabb` is there if an axis-aligned rectangle is wanted instead.

One gotcha: with `keypoints` or `bounding_boxes` supplied, the pipeline returns
`[image, mask, keypoints, bounding_boxes]`, not a bare image.  Calling
`np.asarray()` on that raises a confusing "inhomogeneous shape" ValueError.
"""

from copy import deepcopy

import cv2
import numpy as np

# label -> BGR, following add_annotations_v1's colour list in spirit
BOX_COLORS = {
    'square':    (0, 0, 255),
    'title':     (255, 0, 0),
    'xlabel':    (0, 200, 0),
    'ylabel':    (255, 0, 255),
    'color bar': (0, 165, 255),
}

BOX_KEYS = ('square', 'title', 'xlabel', 'ylabel', 'color bar')

_KP_LABEL = 'annotation_corners'


def collect_quads(datas_plot, img_height, keys=BOX_KEYS, flip_ycoord=True):
    """
    Every stored annotation box as (label, quad), quad being its four corners
    [[x,y] x4] in image pixels, clockwise from top-left.

    `datas_plot` is the generator's per-figure dict -- the structure
    add_annotations_v1 walks, and the one embedded in each released
    `<vqa_id>_qa.json`.  The stored coordinates use a bottom-left origin
    (matplotlib display space) and the image a top-left one, so y is flipped
    against the image height, exactly as the original function does.
    """
    out = []
    for pkey, v in datas_plot.items():
        if not pkey.startswith('plot') or not isinstance(v, dict):
            continue
        for key in keys:
            d = v.get(key)
            if not isinstance(d, dict) or 'xmin' not in d:
                continue
            x1, x2 = float(d['xmin']), float(d['xmax'])
            if flip_ycoord:
                y1, y2 = img_height - float(d['ymin']), img_height - float(d['ymax'])
            else:
                y1, y2 = float(d['ymin']), float(d['ymax'])
            xa, xb = min(x1, x2), max(x1, x2)
            ya, yb = min(y1, y2), max(y1, y2)
            quad = [[xa, ya], [xb, ya], [xb, yb], [xa, yb]]
            out.append((key, [[int(round(px)), int(round(py))] for px, py in quad]))
    return out


def quad_to_aabb(quad):
    """Axis-aligned [x1, y1, x2, y2] around a (possibly rotated) quad."""
    q = np.asarray(quad, dtype=float)
    return [int(q[:, 0].min()), int(q[:, 1].min()),
            int(q[:, 0].max()), int(q[:, 1].max())]


def draw_quads(img, labelled_quads, linethick=3, fill_blocks=False,
               label_text=False, font_scale=1.0, as_rectangles=False):
    """Draw each quad onto a copy of `img`, coloured by label."""
    canvas = deepcopy(img)
    for label, quad in labelled_quads:
        base = label.split()[-1] if label not in BOX_COLORS and ' ' in label else label
        color = BOX_COLORS.get(label, BOX_COLORS.get(base, (0, 0, 255)))
        if as_rectangles:
            x1, y1, x2, y2 = quad_to_aabb(quad)
            cv2.rectangle(canvas, (x1, y1), (x2, y2), color,
                          -1 if fill_blocks else linethick)
        else:
            pts = np.asarray(quad, dtype=np.int32).reshape(-1, 1, 2)
            if fill_blocks:
                cv2.fillPoly(canvas, [pts], color)
            else:
                cv2.polylines(canvas, [pts], True, color, linethick, cv2.LINE_AA)
        if label_text:
            x, y = quad[0]
            cv2.putText(canvas, base, (int(x), max(int(y) - 8, 14)),
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, 2, cv2.LINE_AA)
    return canvas


def _factory(name):
    """One augraphy augmentation by name.  Imported lazily."""
    import augraphy as ag
    if name == 'Geometric':
        return ag.Geometric(rotate_range=(-3, 3), p=1)
    return getattr(ag, name)(p=1)


def flatten_quads(labelled_quads):
    """
    (labels, keypoints_dict) ready to hand to AugraphyPipeline.

    All corners go into one keypoint label in order, four per box, so they can
    be regrouped afterwards without relying on dict ordering.
    """
    labels = [lab for lab, _ in labelled_quads]
    flat = [list(map(int, pt)) for _, quad in labelled_quads for pt in quad]
    return labels, {_KP_LABEL: flat}


def unpack_result(result, labels, fallback_flat, grayscale=False):
    """
    Pull the aged image and the moved corners out of a pipeline return value.

    With keypoints or bounding_boxes supplied the pipeline returns
    `[image, mask, keypoints, bounding_boxes]`; without them, a bare image.
    Handles both, so a caller does not have to care which it built.
    """
    if isinstance(result, (list, tuple)):
        aged = np.asarray(result[0])
        moved_flat = (result[2] or {}).get(_KP_LABEL, fallback_flat)
    else:
        aged, moved_flat = np.asarray(result), fallback_flat

    if aged.ndim == 2:
        aged = cv2.cvtColor(aged, cv2.COLOR_GRAY2BGR)
    if grayscale:
        aged = cv2.cvtColor(cv2.cvtColor(aged, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)

    moved = [(labels[i], [list(map(int, pt)) for pt in moved_flat[4*i:4*i + 4]])
             for i in range(len(labels))]
    return aged, moved


def age_with_quads(img, labelled_quads, effects_by_phase, seed=None,
                   grayscale=False):
    """
    Age `img` and carry the annotation corners through the same transforms.

    Builds its own pipeline from an explicit effect list.  If you already have a
    pipeline (a notebook preset, say), use flatten_quads() + unpack_result()
    instead so the preset stays the single source of truth.

    Returns (aged_image, moved_labelled_quads).
    """
    from augraphy import AugraphyPipeline

    labels, keypoints = flatten_quads(labelled_quads)
    pipeline = AugraphyPipeline(
        ink_phase=[_factory(n) for n in effects_by_phase.get('ink', [])],
        paper_phase=[_factory(n) for n in effects_by_phase.get('paper', [])],
        post_phase=[_factory(n) for n in effects_by_phase.get('post', [])],
        keypoints=keypoints,
        random_seed=seed)
    return unpack_result(pipeline(img.copy()), labels,
                         keypoints[_KP_LABEL], grayscale=grayscale)


def add_annotations_transform(img, datas_plot, effects_by_phase, seed=None,
                              grayscale=False, keys=BOX_KEYS, flip_ycoord=True,
                              linethick=3, fill_blocks=False, label_text=False,
                              as_rectangles=False):
    """
    The transform-aware counterpart of add_annotations_v1.

    Ages the figure and moves its annotation boxes by the same geometry, then
    draws them on the aged page.

    Returns a dict:
        clean            the input image
        clean_annotated  input with the stored boxes drawn on it
        aged             the aged page
        aged_annotated   aged page with the MOVED boxes drawn on it
        quads            [(label, [[x,y] x4]), ...] before
        quads_moved      the same after
    """
    quads = collect_quads(datas_plot, img.shape[0], keys=keys,
                          flip_ycoord=flip_ycoord)
    aged, moved = age_with_quads(img, quads, effects_by_phase, seed=seed,
                                 grayscale=grayscale)
    kw = dict(linethick=linethick, fill_blocks=fill_blocks,
              label_text=label_text, as_rectangles=as_rectangles)
    return {'clean': img,
            'clean_annotated': draw_quads(img, quads, **kw),
            'aged': aged,
            'aged_annotated': draw_quads(aged, moved, **kw),
            'quads': quads,
            'quads_moved': moved}

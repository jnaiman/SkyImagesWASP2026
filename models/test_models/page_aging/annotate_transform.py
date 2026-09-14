"""
Annotation boxes that survive page aging.

`add_annotations_v1` in `skyfigs/utils/figure_gen_utils/misc.py` draws the
stored bounding boxes -- plot square, title, x/y labels, tick labels, colorbar --
onto a clean figure.  It assumes the image it draws on is the image the
coordinates came from, which stops being true the moment the page is aged:
`Geometric` rotates and pads the canvas, `Squish` deletes columns, `Folding`
warps locally.  Every stored box then lands in the wrong place.

`add_annotations_transform` below is that function reworked so the annotations
are carried *through* the aging pipeline with the image.  Three things had to be
got right, each of them measured rather than assumed:

1.  **Corners, not boxes.**  Augraphy transforms `bounding_boxes` and
    `keypoints` differently.  On a 20 degree rotation of a 300x200 box at
    (100,100), the box came back *the same size, merely translated* -- augraphy
    tracks the padding offset for boxes but not the rotation -- while the
    corners came back genuinely rotated.  So annotations travel as keypoints.

2.  **One keypoint label per box.**  With every corner in a single label,
    `Squish` silently dropped points and the surviving list no longer split
    evenly into groups of four: one box absorbed another's corners and came out
    as a nonsense quadrilateral.  A label per box keeps them separate.

3.  **A dense perimeter, not four corners.**  `Squish` removes whole columns of
    the page, taking any keypoint on them with it -- a box can lose an entire
    edge, and four corners cannot survive that.  Each box is therefore sent as a
    ring of points sampled along its perimeter, and the transformed outline is
    rebuilt as the convex hull of whatever comes back.  This also tracks
    `Folding`'s local warp far better than four corners could.
"""

from copy import deepcopy

import cv2
import numpy as np

# label -> BGR
BOX_COLORS = {
    'square':          (0, 0, 255),
    'title':           (255, 0, 0),
    'xlabel':          (0, 200, 0),
    'ylabel':          (255, 0, 255),
    'color bar':       (0, 165, 255),
    'xticks':          (200, 200, 0),
    'yticks':          (200, 100, 0),
    'color bar ticks': (120, 120, 255),
}

# keys holding a single box dict
BOX_KEYS = ('square', 'title', 'xlabel', 'ylabel', 'color bar')
# keys holding a LIST of box dicts, one per tick label
LIST_KEYS = ('xticks', 'yticks', 'color bar ticks')

_KP_PREFIX = 'ann'

# Perimeter sampling.  A FIXED number of points per edge is the wrong unit: the
# plot square's long edge is ~1000 px, so eight samples sit 127 px apart, and
# although every sample lands exactly on the transformed curve, the polyline
# between them chords straight across anything narrower than that -- a fold's
# dip-and-recover shows up as a single slope down.  Sampling by DISTANCE keeps
# the resolution constant whether the box is a plot border or a tick label.
_POINT_SPACING = 10      # px between perimeter samples
_MIN_PER_EDGE = 4        # even a tiny tick-label box gets a few
_MAX_PER_EDGE = 300      # and an enormous one does not explode


def _box_to_quad(d, img_height, flip_ycoord):
    x1, x2 = float(d['xmin']), float(d['xmax'])
    if flip_ycoord:
        y1, y2 = img_height - float(d['ymin']), img_height - float(d['ymax'])
    else:
        y1, y2 = float(d['ymin']), float(d['ymax'])
    xa, xb = min(x1, x2), max(x1, x2)
    ya, yb = min(y1, y2), max(y1, y2)
    return [[int(round(xa)), int(round(ya))], [int(round(xb)), int(round(ya))],
            [int(round(xb)), int(round(yb))], [int(round(xa)), int(round(yb))]]


def collect_quads(datas_plot, img_height, keys=BOX_KEYS, list_keys=LIST_KEYS,
                  flip_ycoord=True):
    """
    Every stored annotation box as (label, quad), quad being four corners
    [[x,y] x4] in image pixels, clockwise from top-left.

    Covers both the single boxes (square, title, x/y label, colorbar) and the
    per-tick-label lists (xticks, yticks, colorbar ticks) -- the tick labels are
    stored as a LIST of box dicts, which is why walking only dict-valued keys
    misses them.

    The stored coordinates use a bottom-left origin (matplotlib display space)
    and the image a top-left one, so y is flipped against the image height,
    exactly as add_annotations_v1 does.
    """
    out = []
    for pkey, v in datas_plot.items():
        if not pkey.startswith('plot') or not isinstance(v, dict):
            continue
        for key in keys:
            d = v.get(key)
            if isinstance(d, dict) and 'xmin' in d:
                out.append((key, _box_to_quad(d, img_height, flip_ycoord)))
        for key in list_keys:
            for d in (v.get(key) or []):
                if isinstance(d, dict) and 'xmin' in d:
                    out.append((key, _box_to_quad(d, img_height, flip_ycoord)))
    return out


def quad_to_aabb(quad):
    """Axis-aligned [x1, y1, x2, y2] around a (possibly rotated) outline."""
    q = np.asarray(quad, dtype=float)
    return [int(q[:, 0].min()), int(q[:, 1].min()),
            int(q[:, 0].max()), int(q[:, 1].max())]


def _perimeter_points(quad, spacing=_POINT_SPACING):
    """
    A ring of points around `quad`, sampled every `spacing` pixels.

    Dense enough that the polyline through the transformed points follows the
    warp rather than chording across it, and dense enough that the outline
    survives an effect deleting some of the points.
    """
    q = np.asarray(quad, dtype=float)
    pts = []
    for i in range(len(q)):
        a, b = q[i], q[(i + 1) % len(q)]
        length = float(np.linalg.norm(b - a))
        n = int(np.clip(round(length / max(spacing, 1e-6)),
                        _MIN_PER_EDGE, _MAX_PER_EDGE))
        for t in np.linspace(0.0, 1.0, n + 1)[:-1]:
            pts.append(a + (b - a) * t)
    return [[int(round(p[0])), int(round(p[1]))] for p in pts]


def flatten_quads(labelled_quads, spacing=_POINT_SPACING):
    """
    (labels, keypoints_dict) ready to hand to AugraphyPipeline.

    One label per box -- see note 2 in the module docstring -- each carrying a
    perimeter ring rather than bare corners.  Ring lengths differ per box, which
    is fine: each has its own keypoint label, so nothing has to be regrouped by
    a fixed stride afterwards.
    """
    labels = [lab for lab, _ in labelled_quads]
    keypoints = {'%s%d' % (_KP_PREFIX, i): _perimeter_points(q, spacing)
                 for i, (_, q) in enumerate(labelled_quads)}
    return labels, keypoints


def _outline(points, fallback):
    """
    The transformed outline, as the surviving perimeter points in ring order.

    Kept in order rather than reduced to a convex hull: the hull would straighten
    exactly the deviations worth seeing.  Order survives augraphy's keypoint
    handling -- checked on Folding, Geometric and SectionShift, where the step
    between consecutive returned points stays near the spacing that was sent.
    Squish is the exception: it deletes the points on the columns it removes, so
    the ring acquires a gap and the outline cuts straight across it.  That is the
    honest picture -- that strip of page no longer exists.

    With fewer than three points left there is nothing to draw, so the original
    outline is returned and the caller is told it is stale.
    """
    if len(points) < 3:
        return [list(map(int, p)) for p in fallback], False
    return [[int(x), int(y)] for x, y in points], True


def unpack_result(result, labels, keypoints_sent, grayscale=False):
    """
    Pull the aged image and the moved outlines out of a pipeline return value.

    With keypoints or bounding_boxes supplied the pipeline returns
    `[image, mask, keypoints, bounding_boxes]`; without them, a bare image.

    Returns (aged_image, moved_labelled_quads, stale_labels) -- `stale_labels`
    naming any box whose points were destroyed and whose outline is therefore
    still the original one.
    """
    if isinstance(result, (list, tuple)):
        aged = np.asarray(result[0])
        moved_kp = result[2] or {}
    else:
        aged, moved_kp = np.asarray(result), {}

    if aged.ndim == 2:
        aged = cv2.cvtColor(aged, cv2.COLOR_GRAY2BGR)
    if grayscale:
        aged = cv2.cvtColor(cv2.cvtColor(aged, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)

    moved, stale = [], []
    for i, label in enumerate(labels):
        key = '%s%d' % (_KP_PREFIX, i)
        sent = keypoints_sent[key]
        got = moved_kp.get(key, sent)
        outline, ok = _outline(got, sent)
        if not ok:
            stale.append(label)
        moved.append((label, outline))
    return aged, moved, stale


def draw_quads(img, labelled_quads, linethick=3, fill_blocks=False,
               label_text=False, font_scale=1.0, warped_boxes=True):
    """
    Draw each outline onto a copy of `img`, coloured by label.

    warped_boxes : True (default) draws the full transformed outline -- the
        perimeter as the aging left it, so a fold bows the edge, a rotation
        tilts it and a squish cuts a notch out of it.  False collapses each
        outline to its axis-aligned bounding rectangle, which is what a detector
        trained on rectangles would consume, at the cost of hiding the warp.
    """
    canvas = deepcopy(img)
    for label, quad in labelled_quads:
        color = BOX_COLORS.get(label, (0, 0, 255))
        if not warped_boxes:
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
            cv2.putText(canvas, label, (int(x), max(int(y) - 8, 14)),
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, 2, cv2.LINE_AA)
    return canvas


def _factory(name):
    """One augraphy augmentation by name.  Imported lazily."""
    import augraphy as ag
    if name == 'Geometric':
        return ag.Geometric(rotate_range=(-3, 3), p=1)
    return getattr(ag, name)(p=1)


def age_with_quads(img, labelled_quads, effects_by_phase, seed=None,
                   grayscale=False, spacing=_POINT_SPACING):
    """
    Age `img` and carry the annotation outlines through the same transforms.

    Builds its own pipeline from an explicit effect list.  If you already have a
    pipeline (a notebook preset, say), use flatten_quads() + unpack_result()
    instead so the preset stays the single source of truth.

    Returns (aged_image, moved_labelled_quads, stale_labels).
    """
    from augraphy import AugraphyPipeline

    labels, keypoints = flatten_quads(labelled_quads, spacing)
    pipeline = AugraphyPipeline(
        ink_phase=[_factory(n) for n in effects_by_phase.get('ink', [])],
        paper_phase=[_factory(n) for n in effects_by_phase.get('paper', [])],
        post_phase=[_factory(n) for n in effects_by_phase.get('post', [])],
        keypoints=keypoints,
        random_seed=seed)
    return unpack_result(pipeline(img.copy()), labels, keypoints,
                         grayscale=grayscale)


def add_annotations_transform(img, datas_plot, effects_by_phase, seed=None,
                              grayscale=False, keys=BOX_KEYS,
                              list_keys=LIST_KEYS, flip_ycoord=True,
                              linethick=3, fill_blocks=False, label_text=False,
                              warped_boxes=True, spacing=_POINT_SPACING):
    """
    The transform-aware counterpart of add_annotations_v1.

    Ages the figure and moves its annotation boxes by the same geometry, then
    draws them on the aged page.

    Returns a dict:
        clean            the input image
        clean_annotated  input with the stored boxes drawn on it
        aged             the aged page
        aged_annotated   aged page with the MOVED outlines drawn on it
                         (warped outlines, or rectangles if warped_boxes=False)
        quads            [(label, [[x,y], ...]), ...] before
        quads_moved      the same after
        stale            labels whose outline could not be rebuilt
    """
    quads = collect_quads(datas_plot, img.shape[0], keys=keys,
                          list_keys=list_keys, flip_ycoord=flip_ycoord)
    aged, moved, stale = age_with_quads(img, quads, effects_by_phase, seed=seed,
                                        grayscale=grayscale, spacing=spacing)
    kw = dict(linethick=linethick, fill_blocks=fill_blocks,
              label_text=label_text, warped_boxes=warped_boxes)
    return {'clean': img,
            'clean_annotated': draw_quads(img, quads, **kw),
            'aged': aged,
            'aged_annotated': draw_quads(aged, moved, **kw),
            'quads': quads, 'quads_moved': moved, 'stale': stale}

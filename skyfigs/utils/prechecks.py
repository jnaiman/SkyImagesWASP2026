"""
Cheap geometric pre-checks, run before a figure is committed.

Background: the generator builds a figure all the way through -- data
generation, plotting, colorbars, titles, savefig -- and only then runs
`collect_boxes`, which rejects the whole thing if any two bounding boxes
overlap.  Every rejected attempt therefore pays the full cost (~2.7 s), and for
multipanel figures the rejection rate approaches 100%: measured over ~3900
rejections, 2924 were colorbar-related and 1849 of those were "colorbar ticks
overlap with each other".

The cause is not randomness, it is arithmetic.  A colorbar in a small panel is
short, matplotlib's default locator puts ~5 ticks on it regardless, and at
`fontsize_min` those labels cannot fit.  `update_fonts_boxes_overlap` responds
by shrinking the font, hits the floor, and re-randomises forever.

`fit_colorbar_ticks` below computes how many tick labels actually fit along a
colorbar and caps the locator to that number, so the collision never happens.
This keeps `colorbar_prob = 1.0` -- every panel still gets a colorbar, it just
gets a sensible number of ticks on it, which is what a person would do.
"""

import numpy as np
from matplotlib.ticker import MaxNLocator


# A tick label is about this fraction of the font size per character, and this
# fraction of the font size tall.  Rough, but only used to decide how many
# labels fit, and the safety factor absorbs the error.
_CHAR_W_PER_PT = 0.62
_LINE_H_PER_PT = 1.25


def _px_per_pt(fig):
    return fig.dpi / 72.0


def colorbar_tick_capacity(cbar, fig, orientation, fontsize,
                           safety=1.15, min_ticks=2, max_ticks=11,
                           renderer=None):
    """
    How many tick labels fit along this colorbar without colliding?

    orientation : 'vertical' (labels stack, limited by height) or
                  'horizontal' (labels sit side by side, limited by width)
    fontsize    : point size the tick labels are drawn at
    safety      : require this much more room than the bare label extent

    Returns an int in [min_ticks, max_ticks].
    """
    try:
        if renderer is None:
            renderer = fig.canvas.get_renderer()
        bbox = cbar.ax.get_window_extent(renderer)
    except Exception:
        # no renderer yet, or a wcsaxes colorbar that does not expose one --
        # fall back to the axes' figure-fraction size
        try:
            pos = cbar.ax.get_position()
            w, h = fig.get_size_inches() * fig.dpi
            span_w, span_h = pos.width * w, pos.height * h
        except Exception:
            return min_ticks
    else:
        span_w, span_h = bbox.width, bbox.height

    px_pt = _px_per_pt(fig)

    if orientation == 'vertical':
        # labels stack up the bar; each needs its own line height
        span = span_h
        per_label = fontsize * _LINE_H_PER_PT * px_pt
    else:
        # labels sit along the bar; each needs its own width.  Use the labels
        # actually on the bar when we can -- "1.5" and "-2.75e17" are very
        # different widths -- otherwise assume a middling 5 characters.
        span = span_w
        nchars = 5
        try:
            texts = [t.get_text() for t in cbar.ax.get_xticklabels()]
            texts = [t for t in texts if t]
            if texts:
                nchars = max(len(t) for t in texts)
        except Exception:
            pass
        per_label = fontsize * _CHAR_W_PER_PT * nchars * px_pt

    if per_label <= 0 or not np.isfinite(span) or span <= 0:
        return min_ticks

    n = int(span // (per_label * safety))
    return int(np.clip(n, min_ticks, max_ticks))


def fit_colorbar_ticks(cbar, fig, side, fontsize, verbose=False, **kwargs):
    """
    Cap a colorbar's tick count to what fits along it.

    Call right after the colorbar is created.  Returns the capacity used, or
    None if the colorbar could not be adjusted (a wcsaxes "colorbar" that is
    really an axes, say) -- callers should treat None as "left alone", not as
    an error.
    """
    orientation = 'horizontal' if side in ('top', 'bottom') else 'vertical'

    n = colorbar_tick_capacity(cbar, fig, orientation, fontsize, **kwargs)
    try:
        cbar.locator = MaxNLocator(nbins=n, prune=None)
        cbar.update_ticks()
    except Exception as e:
        if verbose:
            print('  [precheck] could not cap colorbar ticks:', str(e))
        return None
    if verbose:
        print('  [precheck] colorbar (%s) capped to %d ticks' % (orientation, n))
    return n


def panel_tick_capacity(ax, fig, axis, fontsize, safety=1.15,
                        min_ticks=2, max_ticks=11, renderer=None):
    """
    Same idea for a panel's own x/y tick labels: how many fit along the axis
    without running into each other.  ('x-y ticks overlap' is the largest
    non-colorbar rejection category.)
    """
    try:
        if renderer is None:
            renderer = fig.canvas.get_renderer()
        bbox = ax.get_window_extent(renderer)
        span_w, span_h = bbox.width, bbox.height
    except Exception:
        return min_ticks

    px_pt = _px_per_pt(fig)
    if axis == 'y':
        span = span_h
        per_label = fontsize * _LINE_H_PER_PT * px_pt
    else:
        span = span_w
        nchars = 5
        try:
            texts = [t.get_text() for t in ax.get_xticklabels()]
            texts = [t for t in texts if t]
            if texts:
                nchars = max(len(t) for t in texts)
        except Exception:
            pass
        per_label = fontsize * _CHAR_W_PER_PT * nchars * px_pt

    if per_label <= 0 or not np.isfinite(span) or span <= 0:
        return min_ticks
    return int(np.clip(int(span // (per_label * safety)), min_ticks, max_ticks))


def artists_outside_canvas(fig, renderer=None, tol=0.5):
    """
    Text artists (titles, axis labels, tick labels) whose bounding box crosses
    the figure edge.  Returns a list of (artist, bbox); empty means everything
    fits.
    """
    if renderer is None:
        renderer = fig.canvas.get_renderer()
    w, h = fig.get_size_inches() * fig.dpi
    out = []
    for ax in fig.axes:
        # colorbar axes carry deliberately hidden tick labels (colorbar_mods
        # blanks one axis with labelsize=-1 and labelcolor=facecolor); counting
        # those as "outside" makes every figure look broken
        # Match check_labels_titles_off_page exactly: it tests the title and the
        # x/y axis labels only.  Tick labels routinely extend a pixel past the
        # edge and are NOT rejected, so including them here would grow pad for
        # figures that the generator would have accepted -- destroying the
        # deliberate "labels right at the canvas edge" look.
        cands = [ax.title, ax.xaxis.label, ax.yaxis.label]
        for t in cands:
            if t is None or not t.get_text():
                continue
            try:
                if not t.get_visible():
                    continue
                # labelsize=-1 is how a hidden axis is marked here
                if (t.get_fontsize() or 0) <= 0:
                    continue
            except Exception:
                pass
            try:
                bb = t.get_window_extent(renderer)
            except Exception:
                continue
            if bb.width <= 0 or bb.height <= 0:
                continue
            if bb.x0 < -tol or bb.y0 < -tol or bb.x1 > w + tol or bb.y1 > h + tol:
                out.append((t, bb))
    return out


def fit_layout_to_canvas(fig, pad, w_pad, h_pad,
                         max_pad=0.8, step=0.12, tries=7, verbose=False):
    """
    Apply tight_layout, growing `pad` only as far as needed to keep every label
    inside the canvas.

    The generator samples pad in [0.0, 0.1] so that labels can sit right against
    the figure edge -- that closeness is deliberate.  But at pad ~ 0 a label
    lands fractionally *past* the edge quite often, and every edge element is
    another chance to do so, so the failure rate compounds with panel count:
    `check_labels_titles_off_page` rejected ~74% of multipanel attempts.

    Starting from the sampled pad and increasing only on demand keeps labels as
    close to the edge as they can get while still fitting, instead of throwing
    the figure away.  Returns (pad_used, fits).
    """
    pad_used = pad
    for i in range(tries):
        try:
            fig.tight_layout(pad=pad_used, w_pad=w_pad, h_pad=h_pad)
        except Exception as e:
            # "tight_layout not applied" -- more padding will not help
            if verbose:
                print('  [precheck] tight_layout failed at pad=%.2f: %s' % (pad_used, str(e)))
        try:
            fig.canvas.draw()
        except Exception:
            return pad_used, False
        bad = artists_outside_canvas(fig)
        if not bad:
            if verbose and i:
                print('  [precheck] layout fits at pad=%.2f (from %.2f)' % (pad_used, pad))
            return pad_used, True
        if pad_used >= max_pad:
            break
        pad_used = min(pad_used + step, max_pad)
    if verbose:
        print('  [precheck] %d label(s) still outside canvas at pad=%.2f'
              % (len(bad), pad_used))
    return pad_used, False


def fit_panel_ticks(ax, fig, x_fontsize, y_fontsize, verbose=False, **kwargs):
    """
    Cap a panel's own x/y tick counts to what fits along each axis -- the same
    arithmetic `fit_colorbar_ticks` applies to colorbars.

    Skipped for WCS axes (`image of the sky`), where the RA/DEC tick machinery
    is wcsaxes' own and a MaxNLocator does not apply.  Returns (nx, ny), either
    of which is None when that axis was left alone.
    """
    if hasattr(ax, 'coords'):      # wcsaxes -- leave its tick locator alone
        return None, None

    out = []
    for axis, fontsize in (('x', x_fontsize), ('y', y_fontsize)):
        n = panel_tick_capacity(ax, fig, axis, fontsize, **kwargs)
        try:
            getattr(ax, axis + 'axis').set_major_locator(MaxNLocator(nbins=n, prune=None))
            out.append(n)
        except Exception as e:
            if verbose:
                print('  [precheck] could not cap %s ticks: %s' % (axis, str(e)))
            out.append(None)
    if verbose:
        print('  [precheck] panel ticks capped to x=%s y=%s' % (out[0], out[1]))
    return out[0], out[1]

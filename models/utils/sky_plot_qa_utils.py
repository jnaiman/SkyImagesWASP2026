"""
QA pairs for "image of the sky" panels.

Adapted from `contour_plot_qa_utils.py`.  A sky panel carries the same shape of
data as a contour panel -- xs, ys and a 2-D color grid -- but three of the
contour questions do not transfer unchanged, so this is an adaptation rather
than a rename:

1. **x/y statistics.**  For a sky panel `xs`/`ys` are PIXEL INDICES (0..nx-1,
   0..ny-1) while the axes on the figure are labelled in RA/DEC.  Copying
   `q_stats_contours(axis='x')` would produce ground truth "0" for a figure
   showing "2h27m24s" -- unanswerable from the image.  `q_stats_sky` therefore
   asks in RA/DEC degrees, which is what the axes actually show.  Where those
   degrees come from depends on the distribution: a GMM sky already stores
   xs/ys in degrees, while a real cutout stores pixel indices and needs its WCS
   applied over the displayed sub-region.  Both are handled, deliberately -- if
   only real-sky panels got RA/DEC questions, the presence of the question would
   leak the answer to point 2 below.

2. **Distribution choices.**  Contour offers [random, linear, gaussian mixture
   model].  A sky panel is either a real SkyView cutout or a synthetic
   gaussian-mixture sky, so `q_relationship_sky` offers
   [gaussian mixture model, real image of the sky], and asks once about the
   image rather than once per axis -- the provenance is a property of the whole
   image, not of an axis.

3. **Image-vs-lines.**  Kept as `q_sky_image_or_lines`, but OFF by default in
   the dispatcher: the generator sets the image/contour/both weights to
   1000/1/1, so the answer is "image" about 99.8% of the time.  A question whose
   answer is near-constant inflates accuracy without measuring anything.  Turn it
   on with `ask_image_or_lines=True` if you want it.

The color-axis statistics transfer unchanged -- the colorbar is drawn on the
figure, so min/max/median/mean of the color data are legitimately readable.
"""

import numpy as np

from .plot_qa_utils import (get_nplots, persona, context_single_multi, panel_phrase,
                            how_much_data_values, get_format_adder,
                            what_is_relationship)


# what the stored `distribution` value means in words
SKY_DISTRIBUTIONS = {
    'sky': 'real image of the sky',
    'gmm': 'gaussian mixture model',
}
# the choices offered to the model
SKY_LINE_LIST = ['gaussian mixture model', 'real image of the sky']


def _displayed_pixel_limits(pdata, nx, ny):
    """
    The pixel range actually drawn, which is not always the whole array -- the
    sky path randomly zooms into 50-100% of the image.  Falls back to the full
    array when no limits were recorded.
    """
    dfp = pdata.get('data from plot') or {}
    xl = dfp.get('x pixel limits')
    yl = dfp.get('y pixel limits')
    if xl is None or yl is None:
        return (0, nx - 1), (0, ny - 1)
    return (float(xl[0]), float(xl[1])), (float(yl[0]), float(yl[1]))


def deg_to_hms(deg, seconds_decimals=2):
    """
    Right ascension in degrees -> the sexagesimal string the axis actually shows.

    The generator renders RA ticks in hours/minutes/seconds (e.g. 18h47m20s), so
    the ground truth for an RA question is given in those units rather than in
    decimal degrees -- otherwise the answer is in units that appear nowhere on
    the figure, and the model has to do a unit conversion the question never
    asked for.

    Declination is left in degrees: its ticks are degrees/arcmin/arcsec, which is
    already a degree measure, and decimal degrees is the conventional way to
    quote it.

    24h wraps to 0h, and a value that rounds up to 60 carries into the next unit,
    so 23h59m59.999s formats as 00h00m00.00s rather than 23h59m60.00s.
    """
    h_total = (float(deg) % 360.0) / 15.0
    h = int(h_total)
    m_total = (h_total - h) * 60.0
    m = int(m_total)
    s = round((m_total - m) * 60.0, seconds_decimals)
    if s >= 60.0:                     # carry, after rounding
        s -= 60.0
        m += 1
    if m >= 60:
        m -= 60
        h += 1
    if h >= 24:
        h -= 24
    return '%02dh%02dm%0*.*fs' % (h, m, seconds_decimals + 3, seconds_decimals, s)


def sky_radec_ranges(data, plot_num=0, verbose=False):
    """
    (ra_min, ra_max), (dec_min, dec_max) in DEGREES for the region displayed in
    this panel, or (None, None) if it can't be determined.

    The two sky distributions store their coordinates differently, so this has
    to branch:

      * GMM sky   -- xs/ys are ALREADY RA/DEC in degrees (the generator samples
                     the cluster centres in RA/DEC), and no WCS is written into
                     `data params`.  Read them straight off.
      * real sky  -- xs/ys are PIXEL INDICES into the cutout; the RA/DEC printed
                     on the axes comes from the stored WCS, applied over the
                     displayed sub-region.

    Getting this wrong matters beyond correctness: if RA/DEC questions were
    asked only of real-sky panels, the *presence* of the question would leak the
    answer to the Level 3 real-vs-synthetic question.

    astropy is imported lazily (real-sky branch only) so the rest of this
    package keeps its numpy/PIL/stdlib-only dependency footprint.
    """
    pdata = data['plot' + str(plot_num)]
    dparams = (pdata.get('data') or {}).get('data params') or {}
    hdr = dparams.get('WCS header string')

    # ---- GMM sky: xs/ys are already degrees ----
    if not hdr:
        if pdata.get('distribution') != 'gmm':
            if verbose:
                print('[sky qa] no WCS and not a gmm sky -- skipping RA/DEC questions')
            return None, None
        try:
            xs = np.asarray(pdata['data']['xs'], dtype=float)
            ys = np.asarray(pdata['data']['ys'], dtype=float)
            if xs.size == 0 or ys.size == 0:
                return None, None
            ra = (float(xs.min()), float(xs.max()))
            dec = (float(ys.min()), float(ys.max()))
            if ra[1] - ra[0] > 180.0:
                if verbose:
                    print('[sky qa] gmm panel straddles the RA=0 wrap -- skipping')
                return None, None
            return ra, dec
        except Exception as e:
            if verbose:
                print('[sky qa] could not read gmm RA/DEC:', e)
            return None, None

    # ---- real sky: pixel indices + WCS ----
    try:
        from astropy.wcs import WCS
    except ImportError:
        if verbose:
            print('[sky qa] astropy not available -- skipping RA/DEC questions')
        return None, None

    colors = np.asarray(pdata['data']['colors'])
    if colors.ndim != 2:
        return None, None
    ny, nx = colors.shape

    try:
        w = WCS(hdr)
        (x0, x1), (y0, y1) = _displayed_pixel_limits(pdata, nx, ny)
        # sample the four corners of the displayed box; RA/DEC are not separable
        # in general (the projection rotates), so take the extremes over corners
        xs = np.array([x0, x1, x0, x1], dtype=float)
        ys = np.array([y0, y0, y1, y1], dtype=float)
        ra, dec = w.pixel_to_world_values(xs, ys)
        ra = np.asarray(ra, dtype=float)
        dec = np.asarray(dec, dtype=float)
        if not (np.all(np.isfinite(ra)) and np.all(np.isfinite(dec))):
            return None, None
        # RA wraps at 360; if the box straddles the wrap the min/max are
        # meaningless, so bail rather than emit a wrong answer
        if ra.max() - ra.min() > 180.0:
            if verbose:
                print('[sky qa] panel straddles the RA=0 wrap -- skipping')
            return None, None
        return (float(ra.min()), float(ra.max())), (float(dec.min()), float(dec.max()))
    except Exception as e:
        if verbose:
            print('[sky qa] could not derive RA/DEC:', e)
        return None, None


def _store(qa_pairs, level, key, plot_num, payload):
    """Insert one Q/A under qa_pairs[level]['Plot-level questions'][key]."""
    bucket = qa_pairs[level]['Plot-level questions']
    if key not in bucket:
        bucket[key] = {}
    bucket[key]['plot' + str(plot_num)] = payload
    return qa_pairs


####### L1 #######
def q_sky_image_or_lines(data, qa_pairs, plot_num=0,
                         return_qa=True, verbose=True, use_words=True, use_list=True,
                         single_figure_flag=True,
                         text_persona=None, level='Level 1'):
    """
    Is the sky panel drawn as an image, contour lines, or both?

    NOTE: near-degenerate.  The generator weights image/contour/both as
    1000/1/1, so this is "image" ~99.8% of the time.  Off by default in the
    dispatcher -- see the module docstring.
    """
    big_tag = 'image or lines'
    object = 'image of the sky'

    itag = ''
    for d, v in data['plot' + str(plot_num)]['data from plot']['data'].items():
        itag += d
    if 'image' in itag and 'contour' in itag:
        ans = 'both'
    elif 'image' in itag:
        ans = 'image'
    elif 'contour' in itag:
        ans = 'contour lines'
    else:
        if verbose:
            print('[sky qa] unknown sky panel style:', itag, '-- skipping')
        return qa_pairs

    nplots = get_nplots(data)
    text_persona = persona(text=text_persona)
    text_context = context_single_multi(data, nplots, plot_num, use_words, single_figure_flag)

    adder, text_format = get_format_adder(object, big_tag,
                                          val_type='a string',
                                          nplots=nplots,
                                          use_words=use_words,
                                          use_list=use_list)
    text_question = 'What is the style of the ' + object + '?'
    if use_list:
        text_question += ' Please choose the style from the following list: [image, contour lines, both].'

    q = text_persona + " " + text_context + " " + text_question + " " + text_format
    a = {big_tag + adder: ans}
    if verbose:
        print('QUESTION:', q)
        print('ANSWER:', a)
    if return_qa:
        return _store(qa_pairs, level, big_tag + adder, plot_num,
                      {'Q': q, 'A': a, 'persona': text_persona,
                       'context': text_context, 'question': text_question,
                       'format': text_format})


####### L2 #######
def q_stats_sky(data, qa_pairs, stat={'minimum': np.min}, axis='color',
                plot_num=0, return_qa=True, use_words=True, verbose=True,
                single_figure_flag=True, text_persona=None):
    """
    min/max/median/mean for a sky panel.

    axis='color'  -> statistic of the pixel values, as read off the colorbar.
                     Transfers unchanged from the contour version.
    axis='x'/'y'  -> statistic of RA / DEC in DEGREES over the displayed region,
                     derived from the panel's WCS.  NOT the raw xs/ys, which are
                     pixel indices and do not correspond to anything printed on
                     the figure.  Skipped when the WCS is unavailable.
    """
    val_type = 'a float'
    axis = axis.lower()
    if axis not in ('x', 'y', 'color'):
        print('Axis not chosen correctly:', axis)
        return qa_pairs

    f = list(stat.values())[0]
    big_tag = list(stat.keys())[0]
    pdata = data['plot' + str(plot_num)]

    if axis == 'color':
        zs = pdata['data']['colors']
        list_stat = float(f(np.asarray(zs)))
        axis_name = 'color'
        units = ''
    else:
        ra_rng, dec_rng = sky_radec_ranges(data, plot_num=plot_num, verbose=verbose)
        if ra_rng is None:
            return qa_pairs                      # no WCS -> do not ask
        rng = ra_rng if axis == 'x' else dec_rng
        # min/max are the box edges; median/mean are its centre, since the grid
        # is regular in pixel space and (to a good approximation) in world space
        # across a single cutout
        if f is np.min:
            list_stat = float(rng[0])
        elif f is np.max:
            list_stat = float(rng[1])
        else:
            list_stat = float(0.5 * (rng[0] + rng[1]))
        axis_name = 'right ascension' if axis == 'x' else 'declination'
        if axis == 'x':
            # RA is quoted the way the axis shows it -- hours/minutes/seconds --
            # so the answer type changes from a float to a string here.
            list_stat = deg_to_hms(list_stat)
            val_type = 'a string'
            units = ' in hours, minutes and seconds (for example 18h47m20.50s)'
        else:
            units = ' in degrees'

    nplots = get_nplots(data)
    text_persona = persona(text=text_persona)
    text_context = context_single_multi(data, nplots, plot_num, use_words, single_figure_flag)

    text_question, adder, text_format = how_much_data_values(big_tag, nplots=nplots,
                                                             axis=axis_name,
                                                             val_type=val_type,
                                                             use_words=use_words,
                                                             along_an_axis=True,
                                                             for_each='')
    if units:
        text_question = text_question.rstrip() + ' Give the value' + units + '.'
        text_format = text_format.rstrip('.') + ', expressed' + units + '.'

    big_tag += ' ' + axis_name
    la = {big_tag: list_stat}
    a = {big_tag + adder: la}
    q = text_persona + " " + text_context + " " + text_question + " " + text_format

    if verbose:
        print('QUESTION:', q)
        print('ANSWER:', a)
    if return_qa:
        return _store(qa_pairs, 'Level 2', big_tag + adder, plot_num,
                      {'Q': q, 'A': a, 'persona': text_persona,
                       'context': text_context, 'question': text_question,
                       'format': text_format})


####### L3 #######
def q_relationship_sky(data, qa_pairs, plot_num=0,
                       return_qa=True, use_words=True, use_list=True,
                       line_list=None, single_figure_flag=True,
                       verbose=True, text_persona=None):
    """
    Is this a real image of the sky, or a synthetic (gaussian mixture) one?

    Differs from the contour version in two ways:
      * the choices are [gaussian mixture model, real image of the sky] rather
        than the contour list, and
      * it is asked ONCE about the image rather than once per axis -- provenance
        is a property of the whole image, not of the x/y or color axis.
    """
    if line_list is None:
        line_list = SKY_LINE_LIST

    big_tag = 'distribution'
    val_type = 'a string'

    dist = data['plot' + str(plot_num)]['distribution']
    la = SKY_DISTRIBUTIONS.get(dist, dist)
    if la not in line_list and verbose:
        print('[sky qa] WARNING: answer %r is not among the offered choices %s'
              % (la, line_list))

    nplots = get_nplots(data)
    # ask about the image as a whole -- along_an_axis=False, so no axis wording
    text_question, adder, text_format = what_is_relationship(big_tag, nplots=nplots,
                                                             val_type=val_type,
                                                             use_words=use_words,
                                                             along_an_axis=False,
                                                             for_each='')

    text_persona = persona(text=text_persona)
    text_context = context_single_multi(data, nplots, plot_num, use_words, single_figure_flag)

    if use_list:
        adder = adder.split(')')[0] + ' + list)'
        text_context += (' Please choose the ' + big_tag +
                         ' from the following list: [' + ', '.join(line_list) + '].')

    q = text_persona + " " + text_context + " " + text_question + " " + text_format
    a = {big_tag + adder: la}

    if verbose:
        print('QUESTION:', q)
        print('ANSWER:', a)
    if return_qa:
        return _store(qa_pairs, 'Level 3', big_tag + '-image' + adder, plot_num,
                      {'Q': q, 'A': a,
                       'note': 'sky panels are either a real SkyView cutout or a synthetic gaussian-mixture sky',
                       'persona': text_persona, 'context': text_context,
                       'question': text_question, 'format': text_format})


# ===================================================================
#  Additional sky-specific questions
#  All of these are answerable for BOTH a real cutout and a GMM sky --
#  see the note in sky_radec_ranges about why that symmetry matters.
# ===================================================================

import re

# RA ticks are always rendered sexagesimal, but by two different formatters:
# \mathrm{h} and \mathregular{^h}.  That difference is invisible in the image,
# so it must NOT be asked about.  What IS visible is the finest unit shown.
_RA_UNITS = [('seconds', ('mathrm{s}', 'mathregular{^s}')),
             ('minutes', ('mathrm{m}', 'mathregular{^m}')),
             ('hours',   ('mathrm{h}', 'mathregular{^h}'))]
_DEC_UNITS = [('arcseconds', ('\\prime\\prime', "''")),
              ('arcminutes', ('\\prime', "'")),
              ('degrees',    ('circ', '°'))]


def _tick_strings(data, plot_num, axis):
    key = 'xticks' if axis == 'x' else 'yticks'
    return [str(t.get('data', '')) for t in (data['plot' + str(plot_num)].get(key) or [])]


def finest_tick_unit(data, plot_num=0, axis='x'):
    """
    The smallest unit appearing on an axis' tick labels: hours/minutes/seconds
    for RA, degrees/arcminutes/arcseconds for DEC.  None if undeterminable.
    """
    ticks = _tick_strings(data, plot_num, axis)
    if not ticks:
        return None
    blob = ' '.join(ticks)
    for name, marks in (_RA_UNITS if axis == 'x' else _DEC_UNITS):
        if any(m in blob for m in marks):
            return name
    return None


def coordinate_epoch(data, plot_num=0):
    """
    The epoch stamped on the axis labels ('J2000', 'B1950', '1900', ...), or
    'none'.  The generator appends it with a random style -- 'J2000',
    '(J2000)', '(2000)', '(B2000)' -- so accept all of them.
    """
    p = data['plot' + str(plot_num)]
    lab = ((p.get('xlabel') or {}).get('words') or '') + ' ' + \
          ((p.get('ylabel') or {}).get('words') or '')
    m = re.search(r'([JB])\s?(\d{4})', lab)
    if m:
        return m.group(1) + m.group(2)
    m = re.search(r'\((\d{4})\)', lab)
    if m:
        return m.group(1)
    m = re.search(r'(?<![\d.])(1[89]\d{2}|20\d{2})(?![\d.])', lab)
    return m.group(1) if m else 'none'


def field_extent(data, plot_num=0, verbose=False):
    """
    (width_arcmin, height_arcmin) of the field drawn.

    Height is the declination span -- an angle directly.  Width is the right
    ascension span scaled by cos(dec), which is the true angle on the sky; a
    raw RA difference is not an angle away from the equator.  Returns
    (None, None) when RA/DEC can't be derived.
    """
    ra, dec = sky_radec_ranges(data, plot_num=plot_num, verbose=verbose)
    if ra is None:
        return None, None
    h = (dec[1] - dec[0]) * 60.0
    w = (ra[1] - ra[0]) * np.cos(np.radians(0.5 * (dec[0] + dec[1]))) * 60.0
    return float(abs(w)), float(abs(h))


def pixel_scale_arcsec(data, plot_num=0, verbose=False):
    """
    Approximate arcsec per image pixel, from the declination extent divided by
    the number of rows.  Uses the vertical axis so no cos(dec) factor is
    involved.  None when RA/DEC can't be derived.
    """
    _, h_arcmin = field_extent(data, plot_num=plot_num, verbose=verbose)
    if h_arcmin is None:
        return None
    colors = np.asarray(data['plot' + str(plot_num)]['data']['colors'])
    if colors.ndim != 2 or colors.shape[0] == 0:
        return None
    return float(h_arcmin * 60.0 / colors.shape[0])


def _panel(data, lead='in'):
    """panel_phrase() straight from `data` -- these questions build their text
    before _ask() computes nplots."""
    return panel_phrase(get_nplots(data), lead)


def _ask(data, qa_pairs, plot_num, level, tag, question, fmt, answer,
         use_words=True, single_figure_flag=True, text_persona=None,
         verbose=True, choices=None, return_qa=True):
    """Shared assembly for the questions below."""
    from .plot_qa_utils import get_adder
    nplots = get_nplots(data)
    adder = get_adder(nplots, use_words)
    text_persona = persona(text=text_persona)
    text_context = context_single_multi(data, nplots, plot_num, use_words, single_figure_flag)
    if choices:
        text_context += (' Please choose your answer from the following list: ['
                         + ', '.join(choices) + '].')
    q = text_persona + " " + text_context + " " + question + " " + fmt
    a = {tag + adder: answer}
    if verbose:
        print('QUESTION:', q)
        print('ANSWER:', a)
    if not return_qa:
        return qa_pairs
    return _store(qa_pairs, level, tag + adder, plot_num,
                  {'Q': q, 'A': a, 'persona': text_persona, 'context': text_context,
                   'question': question, 'format': fmt})


def q_sky_epoch(data, qa_pairs, plot_num=0, verbose=True, use_list=True, **kw):
    """(1) Which coordinate epoch is stamped on the axes, if any."""
    ans = coordinate_epoch(data, plot_num)
    tag = 'epoch'
    question = ('What coordinate epoch is given on the axis labels of ' + _panel(data)[3:] +
                '? Answer "none" if no epoch is stated.')
    fmt = ('Please format the output as a json as {"epoch":""} ' + _panel(data, 'for') +
           ', where the "epoch" value should be a string such as "J2000", "B1950" or "none".')
    return _ask(data, qa_pairs, plot_num, 'Level 1', tag, question, fmt, ans,
                verbose=verbose, **kw)


def q_sky_tick_unit(data, qa_pairs, plot_num=0, axis='x', verbose=True,
                    use_list=True, **kw):
    """
    (2) The finest unit shown on an axis.

    NOT "sexagesimal vs decimal" -- the generator always renders RA
    sexagesimally; only the LaTeX markup differs, which the image does not show.
    """
    ans = finest_tick_unit(data, plot_num, axis)
    if ans is None:
        return qa_pairs
    axis_name = 'right ascension' if axis == 'x' else 'declination'
    choices = ['hours', 'minutes', 'seconds'] if axis == 'x' \
        else ['degrees', 'arcminutes', 'arcseconds']
    tag = 'finest unit ' + axis_name
    question = ('What is the smallest unit of angle shown on the ' + axis_name +
                ' tick labels of ' + _panel(data)[3:] + '?')
    fmt = ('Please format the output as a json as {"finest unit ' + axis_name +
           '":""} ' + _panel(data, 'for') + ', where the value should be a string.')
    return _ask(data, qa_pairs, plot_num, 'Level 1', tag, question, fmt, ans,
                verbose=verbose, choices=choices if use_list else None, **kw)


def q_sky_field_extent(data, qa_pairs, plot_num=0, axis='height', verbose=True, **kw):
    """(3) Angular size of the field, in arcminutes."""
    w, h = field_extent(data, plot_num, verbose=False)
    if w is None:
        return qa_pairs
    if axis == 'height':
        ans, name, extra = h, 'height', 'the declination axis'
    else:
        ans, name, extra = w, 'width', ('the right ascension axis, as a true angle on the '
                                        'sky (i.e. including the cos(declination) factor)')
    tag = 'field ' + name
    question = ('What is the angular ' + name + ' of the sky region shown ' + _panel(data) +
                ', measured along ' + extra + '? Give the value in arcminutes.')
    fmt = ('Please format the output as a json as {"field ' + name + '":""} ' +
           _panel(data, 'for') + ', where the value should be a float, expressed in arcminutes.')
    return _ask(data, qa_pairs, plot_num, 'Level 2', tag, question, fmt, ans,
                verbose=verbose, **kw)


def q_sky_pixel_scale(data, qa_pairs, plot_num=0, verbose=True, **kw):
    """(5) Approximate angular size of one image pixel, in arcseconds."""
    ans = pixel_scale_arcsec(data, plot_num, verbose=False)
    if ans is None:
        return qa_pairs
    tag = 'pixel scale'
    question = ('Approximately what angular size does a single pixel of this sky image '
                'span? Give the value in arcseconds.')
    fmt = ('Please format the output as a json as {"pixel scale":""} ' + _panel(data, 'for') +
           ', where the value should be a float, expressed in arcseconds per pixel.')
    return _ask(data, qa_pairs, plot_num, 'Level 3', tag, question, fmt, ans,
                verbose=verbose, **kw)

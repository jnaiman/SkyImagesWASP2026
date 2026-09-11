import numpy as np
from sys import maxsize as maxint
from copy import deepcopy

from .synthetic_fig_utils import get_font_info


# based on seed, make random number generator, see: https://numpy.org/doc/2.2/reference/random/generator.html
def set_all_seeds(rng_dict = {}, rng_outer=np.random, rng=np.random, rng_titles=np.random, rng_font=np.random, rng_aspect=np.random, rng_ptype = np.random,
                  reset_outer = False, reset_inner = False, reset_titles=False, reset_fonts = False, reset_aspect = False, reset_ptype=False,
                  seeds_dict=None,
                  verbose=True):
    
    if seeds_dict is None: # fill
        seeds_dict = {}
        for v in ['outer', 'inner', 'titles', 'font', 'aspect','ptype']:
            seeds_dict[v] = None
    
    # if dictionary
    if rng_dict != {}:
        rng_outer = rng_dict['outer']
        rng = rng_dict['inner']
        rng_titles = rng_dict['titles']
        rng_font = rng_dict['font']
        rng_aspect = rng_dict['aspect']
        rng_ptype = rng_dict['ptype']

    if reset_outer:
        if seeds_dict['outer'] is None:
            seed_outer = np.random.randint(maxint)
        else:
            seed_outer = seeds_dict['outer']
        #if verbose: print('seed_outer =',seed_outer)
        rng_outer = np.random.default_rng(seed_outer)

    # "Inner" seed -- for things like distributions and whatnot
    if reset_inner:
        if seeds_dict['inner'] is None:
            seed = np.random.randint(maxint)
        else:
            seed = seeds_dict['inner'] # JPN -- bad coding!
        #if verbose: print('seed, inner = ', seed)
        rng = np.random.default_rng(seed)

    # for titles
    if reset_titles:
        if seeds_dict['titles'] is None:
            seed_titles = np.random.randint(maxint)
        else:
            seed_titles = seeds_dict['titles']
        #if verbose: print('seed_titles:', seed_titles)
        rng_titles = np.random.default_rng(seed_titles)

    # for fonts
    if reset_fonts:
        if seeds_dict['font'] is None:
            seed_font = np.random.randint(maxint)
        else:
            seed_font = seeds_dict['font']
        #if verbose: print('seed_font:', seed_font)
        rng_font = np.random.default_rng(seed_font)

    # aspect ratio
    if reset_aspect:
        if seeds_dict['aspect'] is None:
            seed_aspect = np.random.randint(maxint)
        else:
            seed_aspect = seeds_dict['aspect']
        #if verbose: print('seed_aspect:', seed_aspect)
        rng_aspect = np.random.default_rng(seed_aspect)

    # aspect ratio
    if reset_ptype:
        if seeds_dict['ptype'] is None:
            seed_ptype = np.random.randint(maxint)
        else:
            seed_ptype = seeds_dict['ptype']
        #if verbose: print('seed_ptype:', seed_ptype)
        rng_ptype = np.random.default_rng(seed_ptype)

    # full out
    if rng_dict == {}: # empty
        rng_dict['outer'] = rng_outer
        rng_dict['inner'] = rng
        rng_dict['titles'] = rng_titles
        rng_dict['font'] = rng_font
        rng_dict['aspect'] = rng_aspect
        rng_dict['ptype'] = rng_ptype

    # seeds dict
    seeds_dict = {}
    seeds_dict['outer'] = seed_outer
    seeds_dict['inner'] = seed
    seeds_dict['titles'] = seed_titles
    seeds_dict['font'] = seed_font
    seeds_dict['aspect'] = seed_aspect
    seeds_dict['ptype'] = seed_ptype

    if verbose: # print formatted seeds dict
        print('  --- seeds dictionary ---')
        print('{')
        for k,v in seeds_dict.items():
            print("'"+k+"':"+str(v)+',')
        print('}')

    return rng_dict, seeds_dict


# shorten checks
def check_aspect(datas, aspect_cut, verbose=False):
    """
    Check if the resulting aspect ratio of the figure is super small.  If so, flag to re-run stuff.
    """
    # 1. Check for square with weird aspect ratio
    success_aspect = True
    # check for thin/fat squares
    aspects = []
    aspect_errors_iplot = []
    for k,v in datas.items():
        if 'plot' in k: # a plot key
            w = v['square']['xmax']-v['square']['xmin']
            h = v['square']['ymax']-v['square']['ymin']
            aspects.append(w/h)
            if w/h > aspect_cut['max'] or w/h < aspect_cut['min']:
                success_aspect = False
                aspect_errors_iplot.append(int(k.replace('plot','')))

    if not success_aspect and verbose:
        print('[ERROR]: aspect ratio off (a = w/h = ', aspects, ')')

    return success_aspect, aspect_errors_iplot


def get_new_xylabels(xlabel_fontsize, ylabel_fontsize, rng, fontsizes, font_names, fontsize_min = 8):
    xlabel_fontsize -= 1
    ylabel_fontsize -= 1    
    err = False

    if xlabel_fontsize < fontsize_min or ylabel_fontsize < fontsize_min:
        err = True
        print("[ERROR]: can't make font size smaller, gonna grab new words for x/y axis labels and try again...")
        _, _, xlabel_fontsize, ylabel_fontsize, _, _, _, _ = get_font_info(fontsizes, font_names, rng=rng)

    return xlabel_fontsize, ylabel_fontsize, err


def get_new_title(title_fontsize, rng, fontsizes, font_names, fontsize_min=8):
    title_fontsize -= 1
    err = False

    if title_fontsize < fontsize_min:
        err = True
        print("[ERROR]: can't make font size smaller, gonna grab new words for title and try again...")
        title_fontsize, _, _, _, _, _, _, _ = get_font_info(fontsizes, font_names, rng=rng)

    return title_fontsize, err



# def check_labels_titles_off_page(datas, font_params, rng_dict, popular_nouns,xlabels_pull, ylabels_pull, titles_pull,
#                                  fontsizes, font_names,
#                                  fontsize_min = 8, verbose=True):
def check_labels_titles_off_page(datas, figure,
                                 fontsizes,
                                 fontsize_min = 8, verbose=True):
    """
    Check if any of the x-axis labels, y-axis labels, or titles is off the page of the figure.  
    If so, try to make the fontsize smaller and re-run.  If the fontsize is smaller than 
    the `fontsize_min` parameter, flag to re-pull new x/y axis labels and titles.
    """
    # check for overlaps of x/y axis labels, tickmarks or anything outside of the figbox
    success_axis_labels = True
    success_title_label = True
    width = datas['figure']['pixel width']
    height = datas['figure']['pixel height']
    xlabel_fontsize = figure.font_params['xlabel_fontsize']
    ylabel_fontsize = figure.font_params['ylabel_fontsize']
    title_fontsize = figure.font_params['title_fontsize']
    popular_nouns = figure.popular_nouns
    font_names = figure.font_names

    reset_all = False
    remake_plot = False

    for k,v in datas.items():
        if 'plot' in k: # a plot key
            # check if x is out of bounds
            for axislabel in ['xlabel', 'ylabel']:
                if v[axislabel]['xmin'] < 0 or v[axislabel]['xmax'] > width or \
                    v[axislabel]['ymin'] < 0 or v[axislabel]['ymax'] > height:
                    success_axis_labels = False
            # also title
            if 'title' in v:
                if v['title']['xmin'] < 0 or v['title']['xmax'] > width or \
                    v['title']['ymin'] < 0 or v['title']['ymax'] > height:
                    success_title_label = False

        if not success_axis_labels:
            remake_plot = True
            if verbose: 
                print('[ERROR]: x/y axis off page, making smaller...')
                # print('   x/y axis labels:', figure.xlabels_pull, figure.ylabels_pull)
            xlabel_fontsize, ylabel_fontsize, err = get_new_xylabels(xlabel_fontsize, ylabel_fontsize, 
                                                                     figure.rng_dict['titles'], fontsizes, font_names,
                                                                            fontsize_min = fontsize_min)
            # regenerate x/y titles if fontsize too small
            #success_titles = False
            if err: # fontsize too small regenerate labels
                if v['type'] != 'image of the sky':
                    figure.xlabels_pull = deepcopy(popular_nouns)
                    figure.ylabels_pull = deepcopy(popular_nouns)
                    # reset RNG for labels
                    seed_titles = np.random.randint(maxint)
                    figure.rng_dict['titles'] = np.random.default_rng(seed_titles)
                else:
                    reset_all = True
            else:
                if verbose: print('   new fontsizes (x,y):', xlabel_fontsize, ylabel_fontsize)

        if not success_axis_labels and err:
            remake_plot = True
            figure.font_params['xlabel_fontsize'] = xlabel_fontsize
            figure.font_params['ylabel_fontsize'] = ylabel_fontsize
            figure.font_params['title_fontsize'] = title_fontsize
            #return font_params, xlabels_pull, ylabels_pull, titles_pull, rng_dict, True, remake_plot
            return figure, True, remake_plot

        if reset_all:
            #return font_params, xlabels_pull, ylabels_pull, titles_pull, rng_dict, True, remake_plot
            return figure, True, remake_plot

        if not success_title_label:
            remake_plot = True
            if verbose:
                print('[ERROR]: title axis off page, making smaller...')
            title_fontsize, err = get_new_title(title_fontsize, figure.rng_dict['titles'], 
                                                fontsizes, font_names,
                                                fontsize_min=fontsize_min)
            # regenerate titles if fontsize too small
            success_titles = False
            if err:
                if v['type'] != 'image of the sky':
                    figure.titles_pull = deepcopy(popular_nouns)
                    # reset RNG for labels
                    seed_titles = np.random.randint(maxint)
                    figure.rng_dict['titles'] = np.random.default_rng(seed_titles)
                else:
                    reset_all = True
            else:
                if verbose: print('   new fontsize:', title_fontsize)

        figure.font_params['xlabel_fontsize'] = xlabel_fontsize
        figure.font_params['ylabel_fontsize'] = ylabel_fontsize
        figure.font_params['title_fontsize'] = title_fontsize

    #return font_params, xlabels_pull, ylabels_pull, titles_pull, rng_dict, reset_all, remake_plot
    return figure, reset_all, remake_plot
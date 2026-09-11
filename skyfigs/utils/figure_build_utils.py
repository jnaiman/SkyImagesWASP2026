# JPN: this will all need to be reorg'd!

from copy import deepcopy


import matplotlib.pyplot as plt
import numpy as np

def _patch_axislabels_for_astropy6():
    """
    In astropy 6.x, AxisLabels.draw() requires extra args supplied by WCSAxes.
    matplotlib's artist-walk calls draw(renderer) with no extras, raising TypeError.
    Making that call a no-op silences the error while letting the real WCSAxes call
    through.

    In astropy 6, those extras were positional; in astropy 7 they became keyword args
    (called via coord._draw_axislabels).  The guard must check both positional and
    keyword extras so the real draw call is never blocked in either version.
    """
    try:
        from astropy.visualization.wcsaxes.axislabels import AxisLabels as _AL
        _orig = _AL.draw
        def _compat(self, renderer, *args, **kwargs):
            if not args and not kwargs:
                return  # pure artist-walk call (renderer only); skip
            return _orig(self, renderer, *args, **kwargs)
        _AL.draw = _compat
    except Exception:
        pass

_patch_axislabels_for_astropy6()

def _safe_canvas_draw(fig):
    fig.canvas.draw()

def print_figure_params(figure_params):
    print('--- Figure level params ---')
    print('colormap:', figure_params['color map'])
    print('plot style:', figure_params['plot style'])
    print('aspect ratio:', figure_params['aspect ratio'])
    print('DPI:', figure_params['dpi'])
    print('# panels, # rows, # columns, panel style:', figure_params['# panels'], 
        figure_params['# rows'], figure_params['# columns'], figure_params['panel style'])





from .plot_utils import make_plot, memory_safe_plot
import time

@memory_safe_plot(max_memory_mb=15000)
def generate_data(fig, iplot, figure_params, plot_data, rng, verbose=False, 
                  linestyles = ['-', '--', ':'], 
                  linestyles_hist = ['-'], 
                  #timeout = 5, # in minutes
                  **kwargs):

    # timeout *= 60
    # start_time = time.time()
    # if time.time() - start_time > timeout:
    #     rais
    err = False
    plot_type = plot_data['plot_type']
    nrows, ncols, plot_params_here_ax, data_for_plot = figure_params['# rows'], \
                                                figure_params['# columns'], \
                                                plot_data['plot_params_here_ax'], \
                                                plot_data['data_for_plot']
    start_time = time.time()
    if plot_type != 'histogram' and plot_type != 'image of the sky':
        ax = fig.add_subplot(nrows, ncols, iplot + 1)
        data_from_plot, ax = make_plot(plot_params_here_ax[plot_type], data_for_plot, 
                                ax, plot_type=plot_type, linestyles=linestyles,
                                rng=rng, **kwargs)#, plot_style=plot_style)
    elif plot_type != 'image of the sky':
        ax = fig.add_subplot(nrows, ncols, iplot + 1)
        data_from_plot, ax = make_plot(plot_params_here_ax[plot_type], data_for_plot, 
                                ax, plot_type=plot_type, linestyles=linestyles_hist, 
                                rng=rng, **kwargs)#, plot_style=plot_style)
    elif plot_type == 'image of the sky':
        data_from_plot, ax = make_plot(plot_params_here_ax[plot_type], data_for_plot, 
                                fig, plot_type=plot_type, linestyles=linestyles, 
                                iplot=iplot, nrows=nrows, ncols=ncols, rng=rng, **kwargs)
    else:
        print('[ERROR]: no plots for plot type =', plot_type)
        import sys; sys.exit()                        
    
    end_time = time.time()
    if verbose: print('took time to generate data *from* plot:', end_time-start_time, 'seconds')

    if data_from_plot is None: # error
        return None, None, True

    plot_data = {}
    plot_data['data_from_plot'] = data_from_plot
    plot_data['ax'] = ax
    return plot_data, ax, err



from .data_utils import get_data
from .figure_gen_utils.misc import log_scale_ax

def get_plot_data(plot_params_here, rng, verbose=False, figure_params=None, 
                  limit_nlines=True, iterate_max = 100, 
                  distribution=None, plot_type=None, 
                  xmin=None, 
                  xmax=None, ymin = None, ymax = None, cmin=None, cmax=None, 
                  data_for_plot = None):
    """
    limit_nlines : if set to True, then for non-linear distributions (e.g. random, gmm), will limit number of lines to 2
    """
    # store for output
    plot_data = {}

    err = False

    # all probabilities for all types of plots
    choices = []; probs = []
    for k,v in plot_params_here.items():
        choices.append(k)
        probs.append(v['prob'])
    # double check
    probs = np.array(probs).astype('float')
    probs /= np.sum(probs)

    plot_params_here_ax = plot_params_here.copy()

    # get plot type
    start_time = time.time()
    if plot_type is None:
        plot_type = rng.choice(choices, p=probs)
    if plot_type not in choices:
        if verbose: print('[WARNING]: plot type not in list, choosing randomly')
        plot_type = rng.choice(choices, p=probs)
    if verbose: print('PLOT TYPE:', plot_type)
    plot_data['plot_type'] = plot_type

    # get distribution type, based on plot type
    dist_params = plot_params_here_ax[plot_type]['distribution'] 
    choices_d = []; probs_d = []
    for k,v in dist_params.items():
        choices_d.append(k)
        probs_d.append(v['prob'])
    # checking
    probs_d = np.array(probs_d).astype('float')
    probs_d /= np.sum(probs_d)

    if distribution is None:
        distribution_type = rng.choice(choices_d, p=probs_d)
    else:
        if distribution in choices_d:
            distribution_type = distribution
        else:
            if verbose: print('[WARNING]: distribution type not in list, choosing randomly')
            distribution_type = rng.choice(choices_d, p=probs_d)
    if verbose: print('  Distribution Type:', distribution_type)
    plot_data['distribution_type'] = distribution_type
    plot_data['dist_params'] = dist_params

    if limit_nlines and plot_type == 'line':
        if distribution_type != 'linear':
            plot_params_here_ax['line']['nlines']['max'] = 2
    
    if xmin is None or xmax is None:
        xmin,xmax = log_scale_ax()
    plot_params_here_ax[plot_type]['xmin']=xmin
    plot_params_here_ax[plot_type]['xmax']=xmax
    if plot_type == 'line' or plot_type == 'scatter' or plot_type == 'contour' or plot_type == 'image of the sky':
        if ymin is None or ymax is None:
            ymin,ymax = log_scale_ax()
        plot_params_here_ax[plot_type]['ymin']=ymin
        plot_params_here_ax[plot_type]['ymax']=ymax
    if plot_type == 'scatter' or plot_type == 'contour' or plot_type == 'image of the sky': 
        if cmin is None or cmax is None:
            cmin,cmax = log_scale_ax()
        plot_params_here_ax[plot_type]['colors']['min']=cmin
        plot_params_here_ax[plot_type]['colors']['max']=cmax

    success_get_data = False
    if data_for_plot is None:
        iloop = 0
        while not success_get_data and iloop <= iterate_max:
            iloop += 1
            #print('iloop = ', iloop)
            data_for_plot = get_data(plot_params_here_ax[plot_type],
                            plot_type=plot_type,
                                    distribution=distribution_type, 
                                    rng=rng, figure_params=figure_params)
            if len(data_for_plot['xs']) > 0 and len(data_for_plot['ys'])>0 and plot_type != 'histogram':
                success_get_data = True
            elif len(data_for_plot['xs']) > 0 and plot_type == 'histogram':
                success_get_data = True
    else:
        success_get_data = True
    if not success_get_data: # killed loop early
        return '', True
    end_time = time.time()
    if verbose: print('took time to generate data:', end_time-start_time, 'seconds')

    plot_data['data_for_plot'] = data_for_plot
    plot_data['plot_params_here_ax'] = plot_params_here_ax

    return plot_data, err


def create_data_save_dict():
    data_for_plots = []
    plot_types = []
    data_from_plots = []
    titles = []; xlabels = []; ylabels = []; 
    cbars = []; cbar_labels = []; cbar_words = []; cbar_nums = []
    distribution_types = []
    # in case axes change
    axes_save = []; cbar_axes_save = []
    data_save = {}
    data_save['data_for_plots'] = data_for_plots
    data_save['plot_types'] = plot_types
    data_save['titles'] = titles
    data_save['xlabels'] = xlabels
    data_save['ylabels'] = ylabels
    data_save['data_from_plots'] = data_from_plots
    data_save['cbars'] = cbars
    data_save['cbar_labels'] = cbar_labels
    data_save['cbar_words'] = cbar_words
    data_save['cbar_nums'] = cbar_nums
    data_save['distribution_types'] = distribution_types
    data_save['axes_save'] = axes_save
    data_save['cbar_axes_save'] = cbar_axes_save
    return data_save



###################################
########### colorbars! ############
###################################
#from .synthetic_fig_utils import add_titles_and_labels
from .synthetic_fig_utils import get_titles_or_labels

# def colorbar_mods(cbar, side, fig):
#     # axis labels slide
#     bottom = False; top = False; right = False; left = False
#     in_or_out = np.random.choice(['in','out'])

#     # is this an image of the sky colorbar?
#     if hasattr(cbar,'coords'):
#         cbar_update = cbar
#     else:
#         cbar_update = cbar.ax

#     # flip labels?
#     if side == 'top' or side == 'bottom':
#         # turn off side axis stuff
#         cbar_update.set_ylabel('')
#         cbar_update.tick_params(length=0, axis='y', labelsize=-1, color=fig.get_facecolor(), 
#                             labelcolor=fig.get_facecolor())
#         # mods for c-bar axis
#         if side == 'bottom':
#             bottom = True
#         else:
#             top = True
#         cbar_update.tick_params(axis='x',direction=in_or_out, 
#                             labelbottom=bottom, labeltop=top, 
#                             labelleft=left, labelright=right)
#     else:
#         # turn off bottom axis stuff
#         cbar_update.set_xlabel('')
#         cbar_update.tick_params(length=0, axis='x', labelsize=-1, color=fig.get_facecolor(), 
#                             labelcolor=fig.get_facecolor())

#         # mods for c-bar axis
#         if side == 'left':
#             left = True
#         else:
#             right = True
#         cbar_update.tick_params(axis='y',direction=in_or_out, 
#                             labelbottom=bottom, labeltop=top, 
#                             labelleft=left, labelright=right)
#     return cbar
def colorbar_mods(cbar, side, fig, verbose=False):
    # axis labels slide
    bottom = False; top = False; right = False; left = False
    in_or_out = np.random.choice(['in','out'])

    if verbose:
        print('----- in colorbar_mods -----')
        print('side:', side)
        print('cbar:', cbar)
        print('in or out:', in_or_out)

    # is this an image of the sky colorbar?
    if hasattr(cbar,'coords'): # image of sky colorbar
        cbar_update = cbar
    else:
        if verbose: print('USING REGULAR CBAR')
        cbar_update = cbar.ax



    # flip labels?
    if side == 'top' or side == 'bottom':
        if verbose:
            print('  I am in top!')
        # turn off side axis stuff
        cbar_update.set_ylabel('')
        cbar_update.tick_params(length=0, axis='y', labelsize=-1, color=fig.get_facecolor(), 
                            labelcolor=fig.get_facecolor())
        # mods for c-bar axis
        if side == 'bottom':
            bottom = True
        else:
            top = True
        cbar_update.tick_params(axis='x',direction=in_or_out, 
                            labelbottom=bottom, labeltop=top, 
                            labelleft=left, labelright=right)
    else:
        if verbose:
            print('  I am in right!')        # turn off bottom axis stuff
        cbar_update.set_xlabel('')
        cbar_update.tick_params(length=0, axis='x', labelsize=-1, color=fig.get_facecolor(), 
                            labelcolor=fig.get_facecolor())

        # mods for c-bar axis
        if side == 'left':
            left = True
        else:
            right = True
        cbar_update.tick_params(axis='y',direction=in_or_out, 
                            labelbottom=bottom, labeltop=top, 
                            labelleft=left, labelright=right)
    return cbar


def set_cbar_fonts(fig, cbar, colorbar_words, side, font_params, verbose=True):
    if cbar is None:
        return cbar
    if isinstance(type(colorbar_words), list):
        try:
            colorbar_words = " ".join(colorbar_words)
        except Exception as e1:
            if verbose: print('[WARNING]: set_cbar_fonts -- list of colorbarwords, ', str(e1))
            colorbar_words = None
    if colorbar_words is not None:
        try:
            cbar.set_title(colorbar_words, fontsize=font_params['colorbar_fontsize'], **font_params['csfont'])
        except Exception as e:
            try:
                cbar.set_label(colorbar_words, fontsize=font_params['colorbar_fontsize'], **font_params['csfont'])
            except Exception as e2:
                print('[ERROR]: set_cbar_fonts --', str(e), 'then', str(e2))

    if cbar is not None:
        try: # regular matplotlib
            cbar.ax.tick_params(labelsize=font_params['colorbar_ticks_fontsize']) 
        except:
            if side == 'bottom' or side == 'top': # x-axis
                visible_coords = ['b', 't']
            else: # y-axis
                visible_coords = ['l', 'r']
            ncoords = len(cbar.coords._coords)
            for icoord in range(ncoords):
                is_vis = cbar.coords[icoord]._ticklabels.get_visible_axes()
                # for specific coord, change
                for sidecoord in visible_coords:
                    if sidecoord not in is_vis or sidecoord == '#':
                        #if verbose: print('coord not visible:', sidecoord)
                        continue
                    cbar.coords[icoord].tick_params(labelsize=font_params['colorbar_ticks_fontsize'])

        # mod colorbar to turn off other axis
        cbar = colorbar_mods(cbar, side, fig)
    return cbar




# def parse_colorbar_data(plot_type, data_from_plot, fig, rng, font_params, 
#                         title_params,colorbar_params,data_for_plots,
#                         popular_nouns=None, inlines=None,
#                         colorbar_words = None, 
#                         verbose=True, norm = None, use_norm=False):
def parse_colorbar_data(figure, fig, iplot,
                        popular_nouns=None, inlines=None,
                        colorbar_words = None, 
                        verbose=True, norm = None, use_norm=False):
    """
    rng : typically rng_dict['inner']
    """

    #cbar.ax.tick_params(labelsize=10) 
    font_params = figure.font_params
    csfont = figure.font_params['csfont']
    colorbar_fontsize = figure.font_params['colorbar_fontsize']
    #colorbar_ticks_fontsize = font_params['colorbar_ticks_fontsize']
    title_params = figure.title_params
    colorbar_params = figure.colorbar_params
    if popular_nouns is None:
        popular_nouns = figure.popular_nouns
    if inlines is None:
        inlines = figure.inlines

    # check norm
    # if norm is None and use_norm:
    #     if 'data params' in data_for_plots: # has params
    #         if 'norm function' in data_for_plots['data params']:
    #             norm = data_for_plots['data params']['norm function']
    data_for_plots = figure.data_save['data_for_plots']
    if norm is None and use_norm:
        if 'data params' in data_for_plots: # has params
            if 'norm function' in data_for_plots['data params']:
                norm = data_for_plots['data params']['norm function']

    if norm is None:
        figdraw = True
    else:
        figdraw = False

    data_from_plot = figure.data_save['data_from_plots'][iplot]
    rng = figure.rng_dict['inner']
    plot_type = figure.data_save['plot_types'][iplot]
    cbar = None
    orientation = None
    if plot_type == 'scatter': 
#    if figure.data_save['plot_types'][iplot] == 'scatter': 
        if 'color bar' in data_from_plot:
            side = data_from_plot['color bar params']['side']
            if side == 'top' or side == 'bottom':
                orientation = 'horizontal'
            else:
                orientation = 'vertical'

            # else:  
            if norm is None:                            
                cbar = fig.colorbar(data_from_plot['data'], 
                        cax=data_from_plot['color bar'], 
                        orientation=orientation)
            else:
                cbar = fig.colorbar(data_from_plot['data'], 
                        cax=data_from_plot['color bar'], 
                        orientation=orientation, norm=norm)
                if figdraw: _safe_canvas_draw(fig)
            # label?
            if rng.uniform() <= data_from_plot['color bar params']['label prob']: # has label
                if colorbar_words is None:
                    
                    colorbar_words = get_titles_or_labels(popular_nouns, 
                                                          colorbar_params['capitalize'],
                                        colorbar_params['equation'], inlines,
                                        nwords=rng.integers(low=title_params['n words']['min'],
                                                                high=title_params['n words']['max']+1), 
                                                                rng=rng)
                cbar.set_label(colorbar_words, fontsize=colorbar_fontsize, **csfont)
                if figdraw: _safe_canvas_draw(fig) # not sure this actually has to be here...
            elif colorbar_words is not None:
                cbar.set_label(colorbar_words, fontsize=colorbar_fontsize, **csfont)
                if figdraw: _safe_canvas_draw(fig) # not sure this actually has to be here...

            cbar = colorbar_mods(cbar, data_from_plot['color bar params']['side'], fig)

            #cbars.append(cbar)
            #cbar_labels.append(colorbar_label)

    if plot_type == 'contour' or plot_type == 'image of the sky':
        if 'color bar' in data_from_plot:
            side = data_from_plot['color bar params']['side']
            if side == 'top' or side == 'bottom':
                orientation = 'horizontal'
            else:
                orientation = 'vertical'
    
            if 'image' in data_from_plot['data']: # select correct colorbar to use
                datac = data_from_plot['data']['image']
            else:
                datac = data_from_plot['data']['contour']

            if norm is None:                                   
                cbar = fig.colorbar(datac, 
                        cax=data_from_plot['color bar'], 
                        orientation=orientation)
            else:
                #print('*********** USING NORM ****************')
                cbar = fig.colorbar(datac, 
                        cax=data_from_plot['color bar'], 
                        orientation=orientation, norm=norm)
                if figdraw: _safe_canvas_draw(fig)
            # label?
            if rng.uniform() <= data_from_plot['color bar params']['label prob']: # has label
                if colorbar_words is None:
                    colorbar_words = get_titles_or_labels(popular_nouns, colorbar_params['capitalize'],
                                        colorbar_params['equation'], inlines,
                                        nwords=rng.integers(low=title_params['n words']['min'],
                                                                high=title_params['n words']['max']+1), 
                                                                rng=rng)
                cbar.set_label(colorbar_words, fontsize=colorbar_fontsize, **csfont)
                if figdraw: _safe_canvas_draw(fig) # not sure this actually has to be here...
            elif colorbar_words is not None:
                cbar.set_label(colorbar_words, fontsize=colorbar_fontsize, **csfont)
                if figdraw: _safe_canvas_draw(fig) # not sure this actually has to be here...
            cbar = colorbar_mods(cbar, data_from_plot['color bar params']['side'], fig)

    if cbar is not None: # and colorbar_words is not None:
        cbar = set_cbar_fonts(fig, cbar, colorbar_words, 
                              data_from_plot['color bar params']['side'], 
                              font_params)

    _safe_canvas_draw(fig)
    return cbar, colorbar_words #, orientation #, False







######################################
############ CHECKS ##################
######################################

from .synthetic_fig_utils import get_font_params
from sys import maxsize as maxint

# def update_fonts_boxes_overlap(names_overlap, success_flags, 
#                                rng_dict, seeds_dict, font_params, figure_params,
#                                popular_nouns, xlabels_pull, ylabels_pull, titles_pull,
#                                fontsizes, font_names,
#                                 fontsize_min=8, verbose=True):
def update_fonts_boxes_overlap(names_overlap, figure,
                               fontsizes,
                                fontsize_min=8, verbose=True, **kwargs):
    """
    Check if there are any overlapping bounding boxes.  If so, try to update fonts 
    if possible, and if not, flag to regenerate the figure.
    """
    # from run class
    success_flags = figure.success_flags
    font_names = figure.font_names
    rng_dict = figure.rng_dict
    seeds_dict = figure.seeds_dict
    font_params = figure.font_params
    figure_params = figure.figure_params
    popular_nouns = figure.popular_nouns
    xlabels_pull = figure.xlabels_pull
    ylabels_pull = figure.ylabels_pull
    titles_pull = figure.titles_pull
    # params
    xlabel_fontsize = font_params['xlabel_fontsize']
    xlabel_ticks_fontsize = font_params['xlabel_ticks_fontsize']
    ylabel_fontsize = font_params['ylabel_fontsize']
    ylabel_ticks_fontsize = font_params['ylabel_ticks_fontsize']
    title_fontsize = font_params['title_fontsize']
    colorbar_fontsize = font_params['colorbar_fontsize']
    colorbar_ticks_fontsize = font_params['colorbar_fontsize']
    #if verbose: print('[ERROR]: overlapping boxes!')
    # figure out what to do for each box
    # get unique overlaps
    s1 = np.unique(names_overlap, axis=0)
    # sort
    s2 = np.unique(np.sort(s1, axis=1),axis=0)

    # starter
    success_titles = success_flags['get titles']
    success_colorbar = success_flags['get colorbar fonts']

    # JPN -- this is not a great way of doing things, reorg this!
    ######## check boxes ##########
    reset_fonts = False
    for b1,b2 in s2:
        # for ticks overlapping with things
        if '-tick' in b1 and '-tick' in b2: # overlapping x/y ticks, smallen
            xlabel_ticks_fontsize -= 1
            ylabel_ticks_fontsize -= 1
            success_titles = False
            if verbose: print('  update_fonts_boxes_overlap: x-y ticks overlap')
            break
        elif ( ('-tick' in b1) and ('-tick' not in b2) and  ('xlabel' in b2) ) or ( ('-tick' in b2) and ('-tick' not in b1) and  ('xlabel' in b1) ): # xlabel cross over
            if xlabel_fontsize > xlabel_ticks_fontsize: # axis label still bigger -- JPN is this relationship correct??
                xlabel_ticks_fontsize -= 1
                ylabel_ticks_fontsize -= 1
            else:
                xlabel_fontsize -= 1
            success_titles = False
            if verbose: print('  update_fonts_boxes_overlap: x *or* y ticks overlap with xlabel')
            break            
        elif ( ('-tick' in b1) and ('-tick' not in b2) and  ('ylabel' in b2) ) or ( ('-tick' in b2) and ('-tick' not in b1) and  ('ylabel' in b1) ): # ylabel cross over
            if ylabel_fontsize > ylabel_ticks_fontsize: # axis label still bigger
                xlabel_ticks_fontsize -= 1
                ylabel_ticks_fontsize -= 1
            else:
                ylabel_fontsize -= 1
            success_titles = False
            if verbose: print('  update_fonts_boxes_overlap: x *or* y ticks overlap with ylabel')
            break   
        elif ( ('-tick' in b1) and ('-tick' not in b2) and  ('title' in b2) ) or ( ('-tick' in b2) and ('-tick' not in b1) and  ('title' in b1) ): # title cross over
            if title_fontsize > ylabel_ticks_fontsize or title_fontsize > xlabel_ticks_fontsize: # axis label still bigger
                xlabel_ticks_fontsize -= 1
                ylabel_ticks_fontsize -= 1
            else:
                title_fontsize -= 1
            success_titles = False
            if verbose: print('  update_fonts_boxes_overlap: x *or* y ticks overlap with title')
            break   
        elif ( ('xlabel' in b1) or ('xlabel' in b2) or ('ylabel' in b1) or ('ylabel' in b2) ) and (('colorbar' not in b1) and ('colorbar' not in b2)): # overlap
            ylabel_fontsize -= 1
            xlabel_fontsize -= 1
            success_titles = False
            if verbose: print('  update_fonts_boxes_overlap: xlabel/ylabel overlap with each other')
            break
        elif ('title' in b1) or ('title' in b2) and ('colorbar' not in b1) and ('colorbar' not in b2):
            title_fontsize -= 1
            success_titles = False
            if verbose: print('  update_fonts_boxes_overlap: title overlaps with *something*')
            break
        ###### colorbars #####
        elif 'colorbar tick' in b1 and 'colorbar tick' in b2: # colorbar ticks
            colorbar_ticks_fontsize -= 1
            success_colorbar = False
            if verbose: print('  update_fonts_boxes_overlap: colorbar ticks overlap with each other')
            break
        elif ('colorbar label' in b1 and 'colorbar tick' in b2) or ('colorbar label' in b2 and 'colorbar tick' in b1): # colorbar ticks overlap with colorbar label
            if colorbar_fontsize > colorbar_ticks_fontsize: # axis label still bigger
                colorbar_ticks_fontsize -= 1
            else:
                colorbar_fontsize -= 1
            success_colorbar = False
            if verbose: print('  update_fonts_boxes_overlap: colorbar ticks overlap with colorbar label')
            break
        elif (('colorbar label' in b1) or ('colorbar label' in b2)) and (('xlabel' in b1) or ('xlabel' in b2) or ('ylabel' in b1) or ('ylabel' in b2)):
            ylabel_fontsize -=1
            xlabel_fontsize -=1
            colorbar_fontsize -= 1
            success_colorbar = False
            if verbose: print('  update_fonts_boxes_overlap: colorbar label overlaps with x or y label')
            break
        elif (('colorbar label' in b1) or ('colorbar label' in b2)) and (('-tick' in b1) or ('-tick' in b2)):
            if colorbar_fontsize > xlabel_ticks_fontsize or colorbar_fontsize > ylabel_ticks_fontsize:
                xlabel_ticks_fontsize -= 1
                ylabel_ticks_fontsize -= 1
            else:
                colorbar_fontsize -= 1
            success_colorbar = False
            if verbose: print('  update_fonts_boxes_overlap: colorbar label overlaps with x or y ticks')
            break
        elif (('colorbar tick' in b1) or ('colorbar tick' in b2)) and (('xlabel' in b1) or ('xlabel' in b2) or ('ylabel' in b1) or ('ylabel' in b2)):
            if ylabel_fontsize > colorbar_ticks_fontsize or xlabel_fontsize > colorbar_ticks_fontsize:
                ylabel_fontsize -=1
                xlabel_fontsize -=1
            else:
                colorbar_ticks_fontsize -= 1
            success_colorbar = False
            if verbose: print('  update_fonts_boxes_overlap: colorbar ticks overlap with x or y label')
            break
        elif (('colorbar tick' in b1) or ('colorbar tick' in b2)) and (('-tick' in b1) or ('-tick' in b2)):
            if colorbar_ticks_fontsize > xlabel_ticks_fontsize or colorbar_ticks_fontsize > ylabel_ticks_fontsize:
                xlabel_ticks_fontsize -= 1
                ylabel_ticks_fontsize -= 1
            else:
                colorbar_ticks_fontsize -= 1
            success_colorbar = False
            if verbose: print('  update_fonts_boxes_overlap: colorbar ticks overlap with x or y ticks')
            break
        elif (('colorbar label' in b1) or ('colorbar label' in b2)) and (('title' in b1) or ('title' in b2)):
            if colorbar_fontsize > title_fontsize:
                title_fontsize -= 1
            else:
                colorbar_fontsize -= 1
            success_colorbar = False
            if verbose: print('  update_fonts_boxes_overlap: colorbar label overlaps with title')
            break
        elif (('colorbar tick' in b1) or ('colorbar tick' in b2)) and (('title' in b1) or ('title' in b2)):
            if colorbar_fontsize > title_fontsize:
                title_fontsize -= 1
            else:
                colorbar_fontsize -= 1
            success_colorbar = False
            if verbose: print('  update_fonts_boxes_overlap: colorbar ticks overlap with title')
            break

        ##### others!! #####
        else: # for 'square', 'colorbar', any of the 'offset' texts
            reset_fonts = True
            if verbose: print('  update_fonts_boxes_overlap: not sure what, but something is overlapping!')

    # full rest of fonts
    for fs in [xlabel_fontsize, ylabel_fontsize, ylabel_ticks_fontsize, xlabel_ticks_fontsize, title_fontsize, colorbar_fontsize, colorbar_ticks_fontsize]:
        if fs < fontsize_min:
            reset_fonts = True    

    if reset_fonts:
        #print('****YES: reset fonts')
        # reset titles, special
        titles_tmp = []
        for t in titles_pull:
            if t == '':
                titles_tmp.append([''])
            else:
                tt = np.array(deepcopy(popular_nouns))
                np.random.shuffle(tt)
                titles_tmp.append(tt)
        titles_pull = deepcopy(titles_tmp)
        #titles_pull = np.stack((np.array(deepcopy(popular_nouns)),) * figure_params['# panels'], axis=0)
        # reset x/y labels
        xlabels_pull = np.stack((np.array(deepcopy(popular_nouns)),) * figure_params['# panels'], axis=0)
        ylabels_pull = np.stack((np.array(deepcopy(popular_nouns)),) * figure_params['# panels'], axis=0)
        #print('*** x,y,len(t shapes):', xlabels_pull.shape, ylabels_pull.shape,len(titles_pull))
        # reset RNG for labels
        seeds_dict['title'] = np.random.randint(maxint)
        rng_dict['titles'] = np.random.default_rng(seeds_dict['title'])
        success_titles = False
        success_colorbar = False
        #from utils.synthetic_fig_utils import get_font_params
        # JPN 20251112
        font_params = get_font_params(rng_dict, fontsizes, font_names, verbose=verbose)
        # JPN 20251113
        #success_flags['get base plot'] = False
        #print('***** 0: font_params -- ', font_params)

    success_flags['get titles'] = success_titles
    success_flags['get colorbar fonts'] = success_colorbar

    if not reset_fonts:
        #print('***** NO dont reset fonts')
        font_params['xlabel_fontsize'] = xlabel_fontsize
        font_params['xlabel_ticks_fontsize'] = xlabel_ticks_fontsize
        font_params['ylabel_fontsize'] = ylabel_fontsize
        font_params['ylabel_ticks_fontsize'] = ylabel_ticks_fontsize 
        font_params['title_fontsize'] = title_fontsize
        font_params['colorbar_fontsize'] = colorbar_fontsize
        font_params['colorbar_fontsize'] = colorbar_ticks_fontsize
        #print('***** 1: font_params -- ', font_params)

    #return success_flags, rng_dict, seeds_dict, font_params, popular_nouns, xlabels_pull, ylabels_pull, titles_pull
    figure.success_flags = success_flags
    figure.rng_dict = rng_dict
    figure.seeds_dict = seeds_dict
    figure.font_params = font_params
    #print('***** 2: font_params -- ', figure.font_params)

    figure.popular_nouns = popular_nouns
    figure.xlabels_pull = xlabels_pull
    figure.ylabels_pull = ylabels_pull
    figure.titles_pull = titles_pull
    kwargs['font_params'] = font_params
    #print('***** 3: font_params -- ', font_params)


    return figure, kwargs
        
  





def create_data_save_dict():
    data_for_plots = []
    plot_types = []
    data_from_plots = []
    titles = []; xlabels = []; ylabels = []; 
    cbars = []; cbar_labels = []; cbar_words = []; cbar_nums = []
    distribution_types = []
    # in case axes change
    axes_save = []; cbar_axes_save = []
    data_save = {}
    data_save['data_for_plots'] = data_for_plots
    data_save['plot_types'] = plot_types
    data_save['titles'] = titles
    data_save['xlabels'] = xlabels
    data_save['ylabels'] = ylabels
    data_save['data_from_plots'] = data_from_plots
    data_save['cbars'] = cbars
    data_save['cbar_labels'] = cbar_labels
    data_save['cbar_words'] = cbar_words
    data_save['cbar_nums'] = cbar_nums
    data_save['distribution_types'] = distribution_types
    data_save['axes_save'] = axes_save
    data_save['cbar_axes_save'] = cbar_axes_save
    return data_save





def get_figure_pixels(fig_width_in, fig_height_in, dpi, n_panels=1):
    """
    Calculate total pixel count for a matplotlib figure.
    
    Parameters
    ----------
    fig_width_in, fig_height_in : float
        Figure dimensions in inches
    dpi : int or float
    n_panels : int
        Informational only — total canvas size doesn't change with panels,
        but useful for per-panel estimates
    
    Returns
    -------
    dict with total, per-panel, and dimension info
    """
    width_px = fig_width_in * dpi
    height_px = fig_height_in * dpi
    total_px = width_px * height_px
    
    return {
        'width_px': int(width_px),
        'height_px': int(height_px),
        'total_px': int(total_px),
        'per_panel_px': int(total_px / n_panels),
        'rgba_bytes': int(total_px * 4),   # 4 bytes per pixel (RGBA uint8)
        'rgba_gb': total_px * 4 / 1e9,
    }

# Safe threshold — tune to your machine's RAM
#MAX_PIXELS = 100_000_000  # 100 megapixels (~400 MB RGBA)

max_pixels=100e6

def safe_dpi(fig, max_pixels=max_pixels):
    """Return a DPI that keeps total pixels under max_pixels."""
    w, h = fig.get_size_inches()
    current_dpi = fig.get_dpi()
    total = w * h * current_dpi**2
    if total > max_pixels:
        safe = (max_pixels / (w * h)) ** 0.5
        return safe
    return current_dpi



def make_base_plot(figure_params, verbose=True, constrained_layout = False, use_panel_aspects=False, max_pixels=max_pixels):

    plot_style, color_map, dpi, nrows, ncols = figure_params['plot style'], figure_params['color map'], figure_params['dpi'], figure_params['# rows'], figure_params['# columns']
    aspect_fig, base, tight_layout, pad = figure_params['aspect ratio'], figure_params['base'], figure_params['tight_layout'], figure_params['layout pad']
    h_pad = figure_params['layout h_pad']
    w_pad = figure_params['layout w_pad']
    hspace = figure_params['layout hspace']
    wspace = figure_params['layout wspace']

    plt.close('all')
    plt.style.use(plot_style)
    plt.set_cmap(color_map) 
    #figsize = (base*nrows, base*aspect_fig*ncols) # w, h
    if use_panel_aspects:
        figsize = (base*ncols*aspect_fig, base*nrows) # w,h
    else:
        figsize = (base*aspect_fig, base) # w,h
    if verbose: print('figsize (w,h) =', figsize)

    # try constrained vs tight

    if tight_layout and not constrained_layout:
        if pad is None and h_pad is None and w_pad is None:
            fig = plt.figure(figsize=figsize, dpi=dpi,layout='tight')
        elif isinstance(pad,float) and isinstance(h_pad,float) and isinstance(w_pad,float):
            fig = plt.figure(figsize=figsize, dpi=dpi,layout='tight')
            fig.get_layout_engine().set(pad=pad, w_pad=w_pad, h_pad=h_pad)
    elif constrained_layout:
        if pad is None and h_pad is None and w_pad is None:
            fig = plt.figure(figsize=figsize, dpi=dpi,layout='constrained')
        elif isinstance(pad,float) and isinstance(h_pad,float) and isinstance(w_pad,float):
            fig = plt.figure(figsize=figsize, dpi=dpi,layout='constrained')
            #fig.get_layout_engine().set(pad=pad, w_pad=w_pad, h_pad=h_pad)
            #fig.set_constrained_layout_pads(hspace=hspace, w_pad=w_pad, h_pad=h_pad, wspace=wspace)
            fig.get_layout_engine().set(w_pad=w_pad, h_pad=h_pad, hspace=hspace, wspace=wspace)
    else:
        fig = plt.figure(figsize=figsize, dpi=dpi)

    # update dpi if need be
    w, h = fig.get_size_inches()
    new_dpi = fig.get_dpi()
    info = get_figure_pixels(fig_width_in=w, fig_height_in=h, dpi=new_dpi)

    if info['total_px'] > max_pixels:
        new_dpi = safe_dpi(fig)
        if verbose: print(f"Reducing DPI from {fig.get_dpi():.0f} to {new_dpi:.0f}")
        fig.set_dpi(new_dpi)

    #### create placeholder axes -- I think this is now obsoluete and should be updated (JPN)
    axes = np.empty((nrows,ncols),dtype='object')
    npanels = nrows*ncols
    
    if npanels == 1:
        axes = [axes]
        plot_inds = [(0,0)] # i,j
    else: # flatten, for now
        # create inds
        if len(axes.shape) > 1: # 2d
            ashape = np.array(axes.shape).copy()
        else:
            ashape = [nrows, ncols]
        plot_inds = np.empty(shape=(ashape[0], ashape[1],2), dtype=int)
        for i in range(ashape[0]):
            for j in range(ashape[1]):
                plot_inds[i,j][0] = i
                plot_inds[i,j][1] = j
        plot_inds = plot_inds.reshape((ashape[0]*ashape[1],-1))
        axes = axes.flatten()

    return fig, axes, plot_inds, figsize, new_dpi




def collect_saved_labels(xlabel, ylabel, title):
    err = False
    # set "pulls" to save, reset letter as needed
    xlabels_pull2 = ''; ylabels_pull2 = ''; titles_pull2 = ''
    try:
        xlabels_pull2 = xlabel.get_text()
    except:
        if type(xlabel) == type([]) or type(xlabel) == type('hi'):
            xlabels_pull2 = xlabel
        else:
            err = True
    try:
        ylabels_pull2 = ylabel.get_text()
    except:
        if type(ylabel) == type([]) or type(ylabel) == type('hi'):
            ylabels_pull2 = ylabel
        else:
            err = True
    try:
        titles_pull2 = title.get_text()
    except:
        if type(title) == type([]) or type(title) == type('hi'):
            titles_pull2 = title
        else:
            err = True

    return xlabels_pull2, ylabels_pull2, titles_pull2, err







from .synthetic_fig_utils import get_nrows_and_ncols
def set_figure_params(rng_dict, colormaps, pstyles, aspects, 
                      dpis, pparams, tparams, base, 
                      plot_flip_params, 
                      verbose=False):
    # init figure params
    figure_params = {}
    figure_params['color map'] = rng_dict['outer'].choice(colormaps)#color_maps) # choose a color map
    figure_params['plot style'] = rng_dict['outer'].choice(pstyles)#plot_styles) # choose a plotting style
    figure_params['aspect ratio'] = rng_dict['outer'].uniform(low=aspects['min'], high=aspects['max']) # aspect_fig_params
    figure_params['dpi'] = int(rng_dict['outer'].uniform(low=dpis['min'], high=dpis['max'])) # dpi_params
    figure_params['base'] = base
    npanels, panel_style, nrows, ncols = get_nrows_and_ncols(pparams, rng=rng_dict['outer'],
                                                             verbose=verbose) # panel_params
    # set
    figure_params['# panels'] = npanels
    figure_params['# rows'] = nrows
    figure_params['# columns'] = ncols
    figure_params['panel style'] = panel_style
    # also get padding params
    tight_layout = False
    if rng_dict['outer'].uniform(low=0.0, high=1.0) <= tparams['prob']: # tight_layout_params
        tight_layout = True
    # get padding
    figure_params['layout pad'] = rng_dict['outer'].uniform(low=tparams['pad']['min'], high=tparams['pad']['max'])
    figure_params['layout h_pad'] = rng_dict['outer'].uniform(low=tparams['h_pad']['min'], high=tparams['h_pad']['max'])
    figure_params['layout w_pad'] = rng_dict['outer'].uniform(low=tparams['w_pad']['min'], high=tparams['w_pad']['max'])
    figure_params['layout hspace'] = rng_dict['outer'].uniform(low=tparams['h_pad']['min'], high=tparams['h_pad']['max'])
    figure_params['layout wspace'] = rng_dict['outer'].uniform(low=tparams['w_pad']['min'], high=tparams['w_pad']['max'])
    figure_params['tight_layout'] = tight_layout

    if np.random.random() < plot_flip_params['prob']:
        figure_params['flipped font/face colors'] = True
    else:
        figure_params['flipped font/face colors'] = False


    return figure_params



from .plot_check_utils import set_all_seeds
from .plot_parameters import base

def reset_everybody(colormaps, pstyles, aspects, dpis, pparams, tparams, 
                    fontsizes, font_names, popular_nouns, success_flags,
                    plot_flip_params={'prob':0.5},
                    verbose=False):
    # reset seeds
    rng_dict, seeds_dict = set_all_seeds(reset_outer = True, 
                            reset_inner = True, 
                            reset_titles=True, 
                            reset_fonts = True, 
                            reset_aspect = True, 
                            reset_ptype=True,
                            verbose=verbose)
    
    # for ease, set a default
    if plot_flip_params is None:
        plot_flip_params = {'prob':0.5}
        
    figure_params = set_figure_params(rng_dict, colormaps, pstyles, aspects, dpis, pparams, tparams, base, plot_flip_params, verbose=verbose)

    # get all font stuffs
    font_params = get_font_params(rng_dict, fontsizes, font_names, verbose=verbose)

    # reset titles
    titles_pull = np.stack((np.array(deepcopy(popular_nouns)),) * figure_params['# panels'], axis=0)
    xlabels_pull = np.stack((np.array(deepcopy(popular_nouns)),) * figure_params['# panels'], axis=0)
    ylabels_pull = np.stack((np.array(deepcopy(popular_nouns)),) * figure_params['# panels'], axis=0)

    # for each plot, make data
    data_save = create_data_save_dict()

    # reset all flags
    success_flags_out = {}
    for k,v in success_flags.items():
        success_flags_out[k] = False
    # one specific one
    success_flags_out['get colorbar fonts'] = True

    reset_dir = {'rng_dict':rng_dict, 'seeds_dict':seeds_dict,'figure_params':figure_params,
                 'font_params':font_params, 'xlabels_pull':xlabels_pull,
                 'ylabels_pull':ylabels_pull, 'titles_pull':titles_pull,
                 'data_save':data_save, 'success_flags_out':success_flags_out}
    
    #return rng_dict, seeds_dict, figure_params, font_params, \
    #    xlabels_pull, ylabels_pull, titles_pull, data_save, success_flags_out
    return reset_dir



#def fill_datas(fig, figure_params, font_params, plot_inds):
def fill_datas(fig, figure, plot_inds):
    figure_params = figure.figure_params
    font_params = figure.font_params
    plt.set_cmap(figure_params['color map']) # do again
    # collect data
    # fig.canvas.draw()
    width, height = fig.canvas.get_width_height()
    # save data
    datas = {}
    # figure datas
    datas['figure'] = {'dpi':figure_params['dpi'], 'base':figure_params['base'], 'aspect ratio': figure_params['aspect ratio'], 
                        'nrows':figure_params['# rows'], 'ncols':figure_params['# columns'], 
                        'plot style':figure_params['plot style'], 
                        'color map':figure_params['color map'],
                        'title fontsize':font_params['title_fontsize'], 
                        'xlabel fontsize':font_params['xlabel_fontsize'],
                        'ylabel fontsize':font_params['ylabel_fontsize'], 
                        'ylabel ticks fontsize':font_params['ylabel_ticks_fontsize'], 
                        'xlabel ticks fontsize':font_params['xlabel_ticks_fontsize'], 
                    'plot indexes':plot_inds, 'pixel width':width, 'pixel height':height}
    
    return datas, width, height




def detect_cb_axes(fig, cbar_nums, flag_weird_colorbar=True, 
                   verbose=False):
    err = False
    axes_save = []; cbar_axes_save = []
    # save axes if not colorbar and image of sky
    for iaxes in range(len(fig.axes)):
        if hasattr(fig.axes[iaxes], 'coords'): # image of sky
            # colorbar?
            if fig.axes[iaxes].coords[0].coord_type == 'scalar':
                if verbose:
                    print('Probable colorbar for image of the sky axes =', iaxes)
            else:
                axes_save.append(fig.axes[iaxes])
                # does this have a colorbar?
                if iaxes in cbar_nums:
                    #print('iaxes (top)=', iaxes)
                    cbar_axes_save.append(fig.axes[iaxes+1])
                else:
                    cbar_axes_save.append([])
        else:
            # colorbar
            #fig.axes[1]._colorbar
            if hasattr(fig.axes[iaxes], '_colorbar'):
                if verbose:
                    print('Probable colorbar for regular plot axes =', iaxes)
            elif 'matplotlib.colorbar.Colorbar' in str(fig.axes[iaxes].__class__):
                if flag_weird_colorbar:
                    if verbose: print('[ERROR]: weird colorbar in detect_cb_axes!', fig.axes[iaxes])
                    return '','', True
                if verbose:
                    print('Probable colorbar (but weird!) for regular plot axes =', iaxes)
            else:
                axes_save.append(fig.axes[iaxes])
                # does this have a colorbar?
                if iaxes in cbar_nums:
                    #print('iaxes = ', iaxes)
                    cbar_axes_save.append(fig.axes[iaxes+1])
                else:
                    cbar_axes_save.append([])

    return axes_save, cbar_axes_save, err



from .plot_check_utils import check_aspect, check_labels_titles_off_page
def collect_boxes(datas, grace_ticks=5):
    """
    Collect all potential bounding boxes in a figure (can be for multi-panel figures too).
    """
    # now check overlapping boxes
    # first make boxes
    boxes_check = []
    success_boxes = True
    for k,v in datas.items():
        if 'plot' in k: # a plot key
            # square!
            boxes_check.append(([v['square']['xmin'], v['square']['ymin'], 
                                        v['square']['xmax'], v['square']['ymax']], 'square'))
            if 'title' in v:
                boxes_check.append( ([v['title']['xmin'], v['title']['ymin'], 
                                        v['title']['xmax'], v['title']['ymax']], 'title') )
            # xlabel
            boxes_check.append( ([v['xlabel']['xmin'], v['xlabel']['ymin'], 
                                        v['xlabel']['xmax'], v['xlabel']['ymax']], 'xlabel') )
            # ylabel
            boxes_check.append( ([v['ylabel']['xmin'], v['ylabel']['ymin'], 
                                        v['ylabel']['xmax'], v['ylabel']['ymax']],'ylabel')  )
            # x/yticks
            for t in ['x','y']:
                for tick in v[t+'ticks']:
                    # ignore things that are outside square
                    if tick['tx'] < v['square']['xmin']-grace_ticks or tick['tx'] > v['square']['xmax']+grace_ticks or \
                      tick['ty'] < v['square']['ymin']-grace_ticks or tick['ty'] > v['square']['ymax']+grace_ticks:
                        continue
                    boxes_check.append( ([tick['xmin'],tick['ymin'],tick['xmax'],tick['ymax']],t+'-tick labels') )
            # x/y offset labels
            for t in ['x','y']:
                if t + '-offset text' in v:
                    tick = v[t + '-offset text']
                    boxes_check.append( ([tick['xmin'],tick['ymin'],tick['xmax'],tick['ymax']],t+'-offset text') )

            # if colorbar, add this
            if 'color bar' in v:
                boxes_check.append(([v['color bar']['xmin'], v['color bar']['ymin'], 
                                        v['color bar']['xmax'], v['color bar']['ymax']],'colorbar'))
                # also check for label
                if 'label' in v['color bar']:
                    xmin = v['color bar']['label']['xmin']
                    ymin = v['color bar']['label']['ymin']
                    xmax = v['color bar']['label']['xmax']
                    ymax = v['color bar']['label']['ymax']
                    boxes_check.append(([xmin,ymin,xmax,ymax],'colorbar label'))
                # and offset text
                if 'offset text' in v['color bar']:
                    xmin = v['color bar']['offset text']['xmin']
                    ymin = v['color bar']['offset text']['ymin']
                    xmax = v['color bar']['offset text']['xmax']
                    ymax = v['color bar']['offset text']['ymax']
                    boxes_check.append(([xmin,ymin,xmax,ymax],'colorbar offset text'))
                    
            # colorbar ticks
            if 'color bar ticks' in v:
                for tick in v['color bar ticks']:
                    boxes_check.append( ([tick['xmin'],tick['ymin'],tick['xmax'],tick['ymax']], 'colorbar tick') )

    # now run and check all boxes -- look for overlap of all boxes
    names_overlap = []
    for ib1,(box1,name1) in enumerate(boxes_check):
        for ib2,(box2,name2) in enumerate(boxes_check):
            if ib1 != ib2: # ib1 < ib2?
                if isRectangleOverlap( box1, box2 ):
                    names_overlap.append( (name1, name2) )
                    success_boxes = False

    return success_boxes, boxes_check, names_overlap



import pandas as pd
def get_fonts(fullproc_r, fontfile='fonts.csv', 
                known_remove_fonts = ['.SF Compact']):
    dfont = pd.read_csv(fullproc_r + 'fonts.csv')
    # check that location is there
    drop_names = []
    for fl in dfont['font location']:
        if not os.path.exists(fl):
            drop_names.append(False)
        else:
            drop_names.append(True)

    font_names1 = dfont.loc[drop_names]['font name'].values

    # known ones to remove
    font_names = []
    for f in font_names1:
        if f in known_remove_fonts:
            pass
        else:
            font_names.append(f)
    return font_names


def close_plot_fail(fig, ifigure, fake_figs_dir, img_format, 
                remove_diags = True, verbose=True, figure_name = None):
    if figure_name is None:
        figure_name = 'Picture_' + str(ifigure+1).zfill(6)

    try:
        plt.close(fig)
    except Exception as e:
        if verbose:
            print('[WARNING]: could not close fig (' + str(e) + ')')
    try:
        os.remove(fake_figs_dir + 'jsons/' + figure_name + '.json')
    except:
        if verbose: print('-- could not remove:', fake_figs_dir + 'jsons/' + figure_name + '.json')
    loops = ['diags', 'imgs']
    if not remove_diags: loops = ['imgs']
    for d in loops:
        for iformat in img_format:
            try:
                os.remove(fake_figs_dir + d + '/' + figure_name + '.' + iformat)
            except:
                if verbose: print('-- could not remove:', fake_figs_dir + d + '/' + figure_name + '.' + iformat)
    plt.clf()            # clear current figure
    plt.cla()            # clear current axes

from .metric_utils.utilities import isRectangleOverlap
from .synthetic_fig_utils import get_font_info
from .plot_parameters import fontsizes

import os
import sys
from ..figure_class import reset_figure #, FigureRun

# def check_exceptions1(e, fontsizes, font_names, 
#                       rng_dict, seeds_dict, figure_params, font_params, 
#                       xlabels_pull, ylabels_pull, titles_pull, 
#                       data_save, success_flags,
#                       color_maps, plot_styles, 
#                     aspect_fig_params, dpi_params, panel_params, tight_layout_params,popular_nouns,
#                       verbose = True, error_front = ''):
def check_exceptions(e, figure, verbose=True, error_front = '', **kwargs):
    """
    e : this is the exception
    """
    figure.success_plot = True
    #font_names = figure.font_names
    if 'missing from font' in str(e): # missing a glph try again
        if verbose: print('[ERROR]: '+error_front+'missing font (' + str(e) + '), will try with new font')
        figure.seeds_dict['font'] = np.random.randint(maxint)
        figure.rng_dict['font'] = np.random.default_rng(figure.seeds_dict['font'])
        #font_params_save = deepcopy(figure.font_params)
        # if 'font_params' in kwargs:
        kwargs['font_params'] = deepcopy(figure.font_params)
        # else:
            # kwargs = {'font_params':deepcopy(figure.font_params)}
        try:
            _, _, _, _, _, _, _, csfont = get_font_info(fontsizes, figure.font_names, rng=figure.rng_dict['font'])
            kwargs['font_params']['csfont'] = csfont
            print("  *** new font:", kwargs['font_params']['csfont'])
        except Exception as e2:
            print('  -- tried new font, but got error', str(e2))
            pass
        figure.success_plot = False
        figure.success_flags['get titles'] = False # only reset getting titles/labels
        ##### JUST FOR NOW #####
        figure.success_plot = False
        plt.close('all')
        # ave to reset everybody
        #kwargs.font_params_save = deepcopy(font_params_save)
        figure = reset_figure(**kwargs)
        #figure.font_params = deepcopy(font_params_save)
    elif 'findfont: Font family ' in str(e) and ' not found.' in str(e):
        if verbose: print('[ERROR]: '+error_front+'font family not found (' + str(e) + '), will try with new font')
        figure.seeds_dict['font'] = np.random.randint(maxint)
        figure.rng_dict['font'] = np.random.default_rng(seeds_dict['font'])
        #font_params_save = deepcopy(figure.font_params)
        # if 'font_params' in kwargs:
        kwargs['font_params'] = deepcopy(figure.font_params)
        # else:
            # kwargs = {'font_params':deepcopy(figure.font_params)}
        try:
            _, _, _, _, _, _, _, csfont = get_font_info(fontsizes, figure.font_names, rng=figure.rng_dict['font'])
            kwargs['font_params']['csfont'] = csfont
            print("  **** new font(findfont):", kwargs['font_params']['csfont'])
        except Exception as e2:
            print('  -- tried new font, but got error', str(e2))
            pass
        figure.success_plot = False
        figure.success_flags['get titles'] = False # only reset getting titles/labels
        ##### JUST FOR NOW #####
        figure.success_plot = False
        plt.close('all')
        # have to reset everybody
        figure = reset_figure(**kwargs)
    elif 'Tight layout not applied' in str(e): # issue with tight layout, redo
        if verbose: print('[ERROR]: '+error_front+' tight layout not applied - ', str(e))
        figure.success_plot = False
        plt.close('all')
        # have to reset everybody
        figure = reset_figure(**kwargs)
    elif 'Glyph' in str(e) and 'missing' in str(e):
        if verbose: print('[ERROR]: '+error_front+'missing Glyph (' + str(e) + '), will try with new font (2)')
        figure.seeds_dict['font'] = np.random.randint(maxint)
        figure.rng_dict['font'] = np.random.default_rng(figure.seeds_dict['font'])
        # if 'font_params' in kwargs:
        kwargs['font_params'] = deepcopy(figure.font_params)
        # else:
            # kwargs = {'font_params':deepcopy(figure.font_params)}
        #font_params_save = deepcopy(figure.font_params)
        try:
            _, _, _, _, _, _, _, csfont = get_font_info(fontsizes, figure.font_names, rng=figure.rng_dict['font'])
            kwargs['font_params']['csfont'] = csfont
            print("  **** new font(Glphy):", kwargs['font_params']['csfont'])
        except Exception as e2:
            print('  -- tried new font, but got error', str(e2))
            pass
        figure.success_plot = False
        figure.success_flags['get titles'] = False # only reset getting titles/labels
        ##### JUST FOR NOW #####
        figure.success_plot = False
        plt.close('all')
        # have to reset everybody
        figure = reset_figure(**kwargs)
    elif "object has no attribute 'set_title'" in str(e):
        if verbose: print('[ERROR]:' + error_front + ' YOU NEED TO CIRCLE BACK TO FIX THIS -', str(e))
        figure.success_plot = False
        plt.close('all')
        # have to reset everybody
        figure = reset_figure(**kwargs)
    elif "index" in str(e) and "is out of bounds" in str(e):
        if verbose: print('[ERROR]:' + error_front + ' issue with indexing -', str(e))
        figure.success_plot = False
        plt.close('all')
        lskfjaslkj
        # have to reset everybody
        figure = reset_figure(**kwargs) #FigureRun()
    elif 'singular' in str(e).lower() and 'matrix' in str(e).lower():
        if verbose: print('[ERROR]:' + error_front + ' singular matrix issue -', str(e))
        figure.success_plot = False
        plt.close('all')
        # have to reset everybody
        figure = reset_figure(**kwargs)
    elif 'invalid value encountered in divide' in str(e).lower():
        if verbose: print('[ERROR]:' + error_front + ' invalid divide error -', str(e))
        figure.success_plot = False
        plt.close('all')
        # have to reset everybody
        figure = reset_figure(**kwargs) #FigureRun()
    elif 'latex was not able' in str(e).lower():
        if verbose: print('[ERROR]:' + error_front + ' latex processing issue -', str(e))
        figure.success_plot = False
        plt.close('all')
        # have to reset everybody
        figure = reset_figure(**kwargs)
    elif 'RGBA sequence should have length' in str(e):
        if verbose: print('[ERROR]:' + error_front + ' some color issue (JPN - FIX!) -', str(e))
        #figure = reset_figure(**kwargs)
    elif 'Maximum allowed dimension exceeded'.lower() in str(e).lower():
        if verbose: print('[ERROR]:' + error_front + ' max dimension? -', str(e), '- JPN -- look into this!')
    elif 'array is too big' in str(e).lower() or 'Unable to allocate'.lower() in str(e).lower():
        if verbose: print('[ERROR]:' + error_front + ' error size -', str(e))
    elif 'timed out' in str(e).lower():
        if verbose: print('[ERROR]:' + error_front + ' time out issue -', str(e))
        figure.success_plot = False
        plt.close('all')
        # have to reset everybody
        figure = reset_figure(**kwargs)
    else:
        if verbose: print('[ERROR]:' + error_front + ' other error -', str(e))
        figure.success_plot = False
        plt.close('all')
        # have to reset everybody
        figure = reset_figure(**kwargs)
        
    return figure, kwargs



    


import json
import pickle
import dill
from .data_utils import NumpyEncoder
import os

def close_plot_success(fig, datas, ifigure, fake_figs_dir, figure_params, 
                       font_params, verbose=True, use_dills = False, 
                       return_dirs = False, figure_name=None):
    if figure_name is None:
        figure_name = 'Picture_' + str(ifigure+1).zfill(6)
        # figure_name_data = 'Picture_data_' + str(ifigure+1).zfill(6)
        # figure_name_data = 'Picture_img_' + str(ifigure+1).zfill(6)
    try:
        plt.close(fig)
    except:
        if verbose:
            print('[WARNING]: could not close fig')
    # save layout
    datas['figure']['figure_params'] = figure_params
    datas['figure']['font_params'] = font_params

    dirs = {}

    # save to pickles and dills
    dumptypes = ['pickle', 'dill']
    if not use_dills:
        dumptypes = ['pickle']
    try:
        for d in dumptypes:
            with open(fake_figs_dir + d + 's/' + figure_name + '.'+d, 'wb') as f:
                #my_data = {'datas':datas, 'fig':fig}
                #my_data = sd
                if d == 'pickle':
                    #pickle.dump(my_data,f)
                    pickle.dump(datas,f)
                    dirs['pickle'] = fake_figs_dir + d + 's/' + figure_name + '.'+d
                elif d == 'dill':
                    #dill.dump(my_data,f)
                    dill.dump(datas,f)
                    dirs['dill'] = fake_figs_dir + d + 's/' + figure_name + '.'+d
        # for d in dumptypes:
        #     for s,my_data in zip(['data','fig'],[datas,fig]):
        #         with open(fake_figs_dir + d + 's/Picture_' + s + '_' + str(ifigure+1).zfill(6) + '.'+d, 'wb') as f:
        #             #my_data = {'datas':datas, 'fig':fig}
        #             #my_data = sd
        #             if d == 'pickle':
        #                 pickle.dump(my_data,f)
        #                 dirs['pickle'] = fake_figs_dir + d + 's/Picture_' + s + '_' + str(ifigure+1).zfill(6) + '.'+d
        #             elif d == 'dill':
        #                 dill.dump(my_data,f)
        #                 dirs['dill'] = fake_figs_dir + d + 's/Picture_' + s + '_' + str(ifigure+1).zfill(6) + '.'+d
    except Exception as e:
        if verbose: print('[WARNING]: could not dump pickles/dills ('+str(e) + ')')

    try:
        dumped = json.dumps(datas, cls=NumpyEncoder)
        with open(fake_figs_dir + 'jsons/' + figure_name + '.json', 'w') as f:
            json.dump(dumped, f) 
            dirs['json'] = fake_figs_dir + 'jsons/' + figure_name + '.json'
    except Exception as e:
        if verbose: print('[WARNING]: could not dump datas ('+str(e) + ')')     

    plt.clf()            # clear current figure
    plt.cla()            # clear current axes

    if verbose: print('!!!!!!!! SUCCESS !!!!!!!!!')
    if return_dirs:
        return dirs






def check_plot_area(data,cutoff=0.38):
    area_fig = data['figure']['pixel height']*data['figure']['pixel width']

    area_sqs = 0.0
    for k,v in data.items():
        if 'plot' in k:
            area_plot = (v['square']['xmax']-v['square']['xmin'])*(v['square']['ymax']-v['square']['ymin'])
            area_sqs += area_plot

    if area_sqs/area_fig > cutoff:
        return True, area_sqs/area_fig
    else: # issue
        return False, area_sqs/area_fig
    #     print(ip+1, area_sqs/area_fig)
    # else:
    #     print('***', ip+1, area_sqs/area_fig)



# def flip_colors(fig2, plottype):
#     fontcolor = fig2.axes[0].xaxis.label.get_color()
#     facecolor = fig2.get_facecolor()

#     new_facecolor = deepcopy(fontcolor)
#     new_fontcolor = deepcopy(facecolor)

#     fig2.set_facecolor(new_facecolor)

#     for axis in ['xaxis','yaxis']:
#         for iax in range(len(fig2.axes)):
#             f = getattr(fig2.axes[iax], axis)
#             f.label.set_color(new_fontcolor)

#     for axis in ['x','y']:
#         for iax in range(len(fig2.axes)):
#             # first find label color
#             for t in fig2.axes[iax].get_yticklabels():
#                 #print(t.get_color())
#                 if t.get_color() != facecolor: # not set to invisible
#                     t.set_color(new_fontcolor)
#             for t in fig2.axes[iax].get_xticklabels():
#                 #print(t.get_color())
#                 if t.get_color() != facecolor:
#                     t.set_color(new_fontcolor)

#     return fig2, new_facecolor, new_fontcolor


# def flip_colors(fig2, plottype, verbose=False):
#     fontcolor = fig2.axes[0].xaxis.label.get_color()
#     facecolor = fig2.get_facecolor()

#     new_facecolor = deepcopy(fontcolor)
#     new_fontcolor = deepcopy(facecolor)

#     if verbose:
#         print('fontcolor, facecolor', fontcolor, facecolor)
#         print('newface,newfont', new_facecolor, new_fontcolor)

#     fig2.set_facecolor(new_facecolor)

#     if plottype != 'image of the sky':
#         for axis in ['xaxis','yaxis']:
#             for iax in range(len(fig2.axes)):
#                 f = getattr(fig2.axes[iax], axis)
#                 f.label.set_color(new_fontcolor)

#         for axis in ['x','y']:
#             for iax in range(len(fig2.axes)):
#                 # first find label color
#                 for t in fig2.axes[iax].get_yticklabels():
#                     #print(t.get_color())
#                     if t.get_color() != facecolor: # not set to invisible
#                         t.set_color(new_fontcolor)
#                 for t in fig2.axes[iax].get_xticklabels():
#                     #print(t.get_color())
#                     if t.get_color() != facecolor:
#                         t.set_color(new_fontcolor)
#     else:
#         for ax in fig.axes:
#             #for i in range(len(ax.coords)):
#             for i in [0,1]:
#                 label = ax.coords[i].get_axislabel()
#                 ax.coords[i].set_axislabel(label, color=new_fontcolor)
#                 ax.coords[i].set_ticklabel(color=new_fontcolor)  # y-axis tick labels

#     return fig2, new_facecolor, new_fontcolor


#def flip_colors(fig2, data_save, figure_params, axes, verbose=False): # axes = axes_from_loop
def flip_colors(fig2, figure, axes, verbose=False): # axes = axes_from_loop

    figure_params = figure.figure_params
    data_save = figure.data_save
    cbars = data_save['cbars']
    plottypes = data_save['plot_types']

    # fontcolor = fig2.axes[0].xaxis.label.get_color()
    # facecolor = fig2.get_facecolor()
    fontcolor = figure_params['fontcolor']
    facecolor = figure_params['facecolor']

    new_facecolor = deepcopy(fontcolor)
    new_fontcolor = deepcopy(facecolor)

    if verbose:
        print('fontcolor, facecolor', fontcolor, facecolor)
        print('newfont, newface', new_fontcolor, new_facecolor)

    fig2.set_facecolor(new_facecolor)

    cbars_out = []
    # now, loop over axes
    for iax, (ax, cbar, plottype) in enumerate(zip(axes, cbars, plottypes)):

        if plottype != 'image of the sky':
            ##### ax ######
            for axis in ['xaxis','yaxis']:
                f = getattr(ax, axis)
                f.label.set_color(new_fontcolor)

            # also for title
            if hasattr(ax, 'title'):
                ax.title.set_color(new_fontcolor)

            for axis in ['x','y']:
                # first find label color
                for t in ax.get_yticklabels():
                    #print(t.get_color())
                    if t.get_color() != facecolor: # not set to invisible
                        t.set_color(new_fontcolor)
                for t in ax.get_xticklabels():
                    #print(t.get_color())
                    if t.get_color() != facecolor:
                        t.set_color(new_fontcolor)
            # spines
            for spine in ax.spines.values():
                spine.set_color(new_fontcolor)
            ax.tick_params(axis='both', colors=new_fontcolor)

            ###### cbar #####
            if cbar is None:
                cbars_out.append(None)
                continue
            else: # has cbar
                for axis in ['xaxis','yaxis']:
                    f = getattr(cbar.ax, axis)
                    f.label.set_color(new_fontcolor)      

                # also for title
                if hasattr(cbar.ax, 'title'):
                    cbar.ax.title.set_color(new_fontcolor)

                for axis in ['x','y']:
                    # first find label color
                    for t in cbar.ax.get_yticklabels():
                        #print(t.get_color())
                        if t.get_color() != facecolor: # not set to invisible
                            t.set_color(new_fontcolor)
                    for t in cbar.ax.get_xticklabels():
                        #print(t.get_color())
                        if t.get_color() != facecolor:
                            t.set_color(new_fontcolor)
                # spines
                for spine in cbar.ax.spines.values():
                    spine.set_color(new_fontcolor)
                cbar.ax.tick_params(axis='both', colors=new_fontcolor)

                cbar2 = colorbar_mods(cbar, data_save['data_from_plots'][iax]['color bar params']['side'], fig2)
                cbars_out.append(cbar2)

        else: # is image of the sky
            ###### ax ########
            for i in [0,1]:
                # also for title
                if hasattr(ax, 'title'):
                    ax.title.set_color(new_fontcolor)
                label = ax.coords[i].get_axislabel()
                ax.coords[i].set_axislabel(label, color=new_fontcolor)
                ax.coords[i].set_ticklabel(color=new_fontcolor)  # y-axis tick labels
                ax.coords[i].frame.set_color(new_fontcolor)
                ax.coords[i].set_ticks(color=new_fontcolor)

            # spines
            for spine in ax.spines.values():
                spine.set_color(new_fontcolor)
            ax.tick_params(axis='both', colors=new_fontcolor)

            ###### cbar ######
            if cbar is None:
                cbars_out.append(None)
                continue
            else:
                for i in [0,1]: 
                    label = cbar.ax.coords[i].get_axislabel()
                    cbar.ax.coords[i].set_axislabel(label, color=new_fontcolor)
                    cbar.ax.coords[i].set_ticklabel(color=new_fontcolor)  # y-axis tick labels
                    cbar.ax.coords[i].frame.set_color(new_fontcolor)
                    cbar.ax.coords[i].frame.set_color(new_fontcolor)
                    cbar.ax.coords[i].set_ticks(color=new_fontcolor)
                    # spines
                    for spine in cbar.ax.spines.values():
                        spine.set_color(new_fontcolor)
                    cbar.ax.tick_params(axis='both', colors=new_fontcolor)

                cbar2 = colorbar_mods(cbar, data_save['data_from_plots'][iax]['color bar params']['side'], fig2)
                cbars_out.append(cbar2)


    return fig2, new_facecolor, new_fontcolor, cbars_out
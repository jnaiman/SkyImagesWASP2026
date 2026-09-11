from .utils.plot_check_utils import set_all_seeds
from .utils.figure_build_utils import set_figure_params, create_data_save_dict, get_fonts
from .utils.plot_parameters import aspect_fig_params, \
    dpi_params, tight_layout_params, panel_params, base, plot_flip_params, fontsizes
from .utils.synthetic_fig_utils import get_font_params
from .utils.text_utils import get_popular_nouns, get_inline_math


import matplotlib.pyplot as plt
import os
import pandas as pd
from copy import deepcopy
import numpy as np

# for plot styles
plot_styles_checked = [
    'default',
    'Solarize_Light2',
    '_classic_test_patch',
    '_mpl-gallery',
    '_mpl-gallery-nogrid',
    'bmh',
    'classic',
    #'dark_background',
    'fast',
    'fivethirtyeight',
    'ggplot',
    'grayscale',
    #'seaborn-v0_8',
    'seaborn-v0_8-bright',
    #'seaborn-v0_8-colorblind',
    #'seaborn-v0_8-dark',
    'seaborn-v0_8-dark-palette',
    #'seaborn-v0_8-darkgrid',
    'seaborn-v0_8-deep',
    'seaborn-v0_8-muted',
    'seaborn-v0_8-notebook',
    'seaborn-v0_8-paper',
    'seaborn-v0_8-pastel',
    'seaborn-v0_8-poster',
    'seaborn-v0_8-talk',
    #'seaborn-v0_8-ticks',
    #'seaborn-v0_8-white',
    #'seaborn-v0_8-whitegrid',
    'tableau-colorblind10'
]

tight_layout_params_checked = {'prob':1.0, # prob of tight layout
                       'pad':{'min':0.0, 'max':0.1}, 
                       'w_pad':{'min':0.0, 'max':0.1}, 
                       'h_pad':{'min':0.0, 'max':0.1}
                       }# for now



# parameters for fig run
from .plot_params_setup import make_plotplotparams
from .paths import get_resources_dir




def get_words_inlines(fullproc_r, data_dir='data', verbose=False, use_uniques = True):
    # get words
    popular_nouns = get_popular_nouns(fullproc_r + data_dir+'/', verbose=verbose)
    # inline math
    inlines = get_inline_math(fullproc_r,
                            recreate_inlines=verbose,
                            use_uniques=use_uniques, verbose = verbose)
    return popular_nouns, inlines





class FigureRun():
    def __init__(self, verbose=False,
            seeds_dict=None, figure_params=None, font_params=None, 
            fullproc_r = None,  # None -> skyfigs.paths.get_resources_dir()
            color_maps = None, plot_styles=None, 
            xlabels_pull=None, ylabels_pull=None, titles_pull=None, 
            data_save=None, success_plot = False, itries=0, success_flip=False,
            success_flags = None, tight_layout_params=None, itriesMax=50, 
            font_names=None, popular_nouns=None, inlines=None, 
            plot_params = None,
            title_params = None, xlabel_params = None, 
            ylabel_params = None, colorbar_params = None, linestyles_hist=None, linestyles = None,
            rng_dict = None, save_diagnostic_plot = True,
            save_pre_check_diagnostic_plot = False,
            verbose_seeds = False, figure_name=None
            ):
        """
        Fill in class of base figure
        """
        self.save_diagnostic_plot = save_diagnostic_plot
        self.save_pre_check_diagnostic_plot = save_pre_check_diagnostic_plot
        self.seeds_dict = seeds_dict
        seeds_dict2 = seeds_dict
        if tight_layout_params is None:
            tight_layout_params = tight_layout_params_checked
        self.tight_layout_params = tight_layout_params
        fullproc_r = get_resources_dir(fullproc_r)
        self.fullproc_r = fullproc_r
        if color_maps is None: 
            color_maps = plt.colormaps()
        self.color_maps = color_maps
        if plot_styles is None:
            plot_styles = plot_styles_checked
        self.plot_styles = plot_styles
        if rng_dict is None or seeds_dict is None:
            rng_dict2, seeds_dict2 = set_all_seeds(reset_outer = True, 
                    reset_inner = True, 
                    reset_titles=True, 
                    reset_fonts = True, 
                    reset_aspect = True, 
                    reset_ptype=True, 
                    seeds_dict=seeds_dict, verbose=verbose_seeds)
        elif rng_dict is not None:
            rng_dict2 = rng_dict
        elif seeds_dict is not None:
            seeds_dict2 = seeds_dict
        self.rng_dict = rng_dict2
        self.seeds_dict = seeds_dict2
        if figure_params is None:
            figure_params = set_figure_params(self.rng_dict, 
                                            self.color_maps, self.plot_styles, 
                                                aspect_fig_params, dpi_params, 
                                                panel_params, self.tight_layout_params, 
                                                base, plot_flip_params,
                                                verbose=verbose)
        self.figure_params = figure_params

        popular_nouns2, inlines2 = get_words_inlines(fullproc_r)
        popular_nouns2 = np.array(popular_nouns2)
        inlines2 = np.array(inlines2)

        if font_names is None:
            font_names = get_fonts(fullproc_r)
        # also pull from font params, if there
        if font_params is not None:
            font_names = [font_params['csfont']['fontname']]
        self.font_names = font_names

        if font_params is None:
            font_params = get_font_params(self.rng_dict, fontsizes, self.font_names)
        self.font_params = font_params
        # if (xlabels_pull is None) or (ylabels_pull is None) or (titles_pull is None):
        #     popular_nouns2 = np.array(popular_nouns2)
        #     inlines2 = np.array(inlines)
        if popular_nouns is None:
            popular_nouns = popular_nouns2
        self.popular_nouns = popular_nouns
        if inlines is None:
            inlines = inlines2
        self.inlines = inlines
        if xlabels_pull is None:
            xlabels_pull = np.stack((np.array(deepcopy(self.popular_nouns)),) * self.figure_params['# panels'], axis=0)
        if ylabels_pull is None:
            ylabels_pull = np.stack((np.array(deepcopy(self.popular_nouns)),) * self.figure_params['# panels'], axis=0)
        if titles_pull is None:
            titles_pull = np.stack((np.array(deepcopy(self.popular_nouns)),) * self.figure_params['# panels'], axis=0)
        self.xlabels_pull = xlabels_pull; self.ylabels_pull = ylabels_pull; self.titles_pull = titles_pull

        if data_save is None:
            data_save = create_data_save_dict()
        self.data_save = data_save
        if success_flags is None:
            success_flags = {'get base plot':False, 'get data for plot':False, 
                            'get data from plot':False, 'get titles':False, 'get colorbar titles':False, 
                            'get colorbar fonts':True}
        self.success_flags = success_flags

        self.success_plot = success_plot
        self.itries = itries
        self.itriesMax = itriesMax
        self.success_flip = success_flip
        self.figure_name = figure_name

    #     if plot_params == None:
    #         # grab from creation function
    #         plot_params2, _, _, _, _, _, _, _, _ = make_plotplotparams()
    # # return plot_params_line, panel_params, title_params, xlabel_params, \
    # #     ylabel_params, colorbar_params, linestyles_hist, linestyles, font_names
    #     if plot_params is None:
    #         self.plot_params = plot_params2

        if plot_params == None or title_params == None or xlabel_params == None or \
            ylabel_params == None or colorbar_params == None or linestyles_hist==None or linestyles == None:
            # grab from creation function
            plot_params2, _, title_params2, xlabel_params2, \
                    ylabel_params2, colorbar_params2, linestyles_hist2, linestyles2, _ = \
                        make_plotplotparams(fullproc_r=fullproc_r)
        if plot_params is None:
            plot_params = plot_params2
        self.plot_params = plot_params
        if title_params is None:
            title_params = title_params2
        self.title_params = title_params
        if xlabel_params is None:
            xlabel_params = xlabel_params2
        self.xlabel_params = xlabel_params
        if ylabel_params is None:
            ylabel_params = ylabel_params2
        self.ylabel_params = ylabel_params
        if colorbar_params is None:
            colorbar_params = colorbar_params2    
        self.colorbar_params = colorbar_params   
        if linestyles_hist is None:
            linestyles_hist = linestyles_hist2
        self.linestyles_hist = linestyles_hist
        if linestyles is None:
            linestyles = linestyles2
        self.linestyles = linestyles



def reset_figure(reset_labels=True, verbose=False, itries=0, **kwargs):
    #figureout = deepcopy(figure)
    figureout = FigureRun()
    for k,v in kwargs.items():
        if k in figureout.__dict__: # in there
            if verbose:
                print('[RESET FIGURE] -- keeping kwarg:', k)
            setattr(figureout, k, v)
    figureout.itries = itries
    # reset all labels
    if reset_labels:
        xlabels_pull = np.stack((np.array(deepcopy(figureout.popular_nouns)),) * figureout.figure_params['# panels'], axis=0)
        ylabels_pull = np.stack((np.array(deepcopy(figureout.popular_nouns)),) * figureout.figure_params['# panels'], axis=0)
        titles_pull = np.stack((np.array(deepcopy(figureout.popular_nouns)),) * figureout.figure_params['# panels'], axis=0)
        figureout.xlabels_pull = xlabels_pull; figureout.ylabels_pull = ylabels_pull; figureout.titles_pull = titles_pull
    
    return figureout
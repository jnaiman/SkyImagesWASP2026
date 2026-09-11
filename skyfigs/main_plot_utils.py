import os
import matplotlib.pyplot as plt
import pandas as pd
from copy import deepcopy
import numpy as np
from PIL import Image

import warnings
warnings.filterwarnings("error")
# deprecation chatter from libraries (e.g. pyparsing's PyparsingDeprecationWarning
# raised inside matplotlib's mathtext font fallback) must not abort plot generation
warnings.filterwarnings("ignore", category=DeprecationWarning)
import time as _time

from .utils.text_utils import get_popular_nouns, get_inline_math

from .utils.plot_parameters import aspect_fig_params, dpi_params, \
    panel_params, tight_layout_params, base, plot_flip_params, fontsizes, \
        plot_types_params, colorbar_params, ylabel_params
            
from .utils.figure_gen_utils.misc import add_annotations_v1 as add_annotations

from .utils.synthetic_fig_utils import get_font_params, normalize_params_prob, add_titles_and_labels, collect_plot_data_axes

from .utils.plot_check_utils import set_all_seeds, check_aspect, check_labels_titles_off_page

from .utils.figure_build_utils import check_exceptions, make_base_plot, \
    close_plot_fail, close_plot_success, get_plot_data, \
    fill_datas, generate_data, collect_saved_labels, parse_colorbar_data, detect_cb_axes, collect_boxes, \
    update_fonts_boxes_overlap, check_plot_area, flip_colors, print_figure_params


###########################################################################
######################### MAIN PLOTTER ########################
###########################################################################

############# SMALL FUNCTIONS ##########
import signal

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Function timed out")

# memory leaks
import gc

import psutil
import os
import sys

def get_memory_mb():
    """Get current process memory in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def get_size_mb(obj):
    """Get size of an object in MB (approximate)"""
    return sys.getsizeof(obj) / 1024 / 1024

def _mrp_log_time(op, elapsed, log_file=None, rank=-1, article='', page='', fignum=''):
    if log_file is None:
        return
    import datetime as _dt, os as _os
    ts = _dt.datetime.now().isoformat(timespec='seconds')
    line = f'{ts},{rank},{_os.getpid()},{article},{page},{fignum},{op},{elapsed:.3f}\n'
    with open(log_file, 'a') as _f:
        _f.write(line)

#############################################

from .figure_class import reset_figure
def make_random_plot(figure = None, verbose=True,
                    fake_figs_dir='./', ifigure=None,
                    img_format='jpeg', figdraw=True,
                    timeout=5, aspect_cut = {'min':0.3, 'max':4.0}, grace_ticks=5, check_aspect_ratio=False,
                    timing_log=None, timing_rank=-1,
                    timing_article='', timing_page='', timing_fignum='',
                    allow_sky_image=True,
                    **kwargs):
    """
    timeout: timeout in minutes
    allow_sky_image: if False, the sky-image plot type is zeroed out.  A no-op when
                     plot_params was already built without it (see
                     skyfigs.plot_params_setup.make_plotplotparams).
    """

    #print('****kwargs at start:',kwargs)
    if figure is None: # if none, set by any kwargs
        #figure = FigureRun()
        figure = reset_figure(**kwargs)
        if not allow_sky_image and 'image of the sky' in figure.plot_params:
            figure.plot_params['image of the sky']['prob'] = 0
            kwargs['plot_params'] = figure.plot_params  # persist into kwargs so all subsequent resets inherit this

    timeout_seconds = timeout*60

    if not isinstance(img_format, list):
        img_format = [img_format]

    fig, datas, imgplot, axes_from_loop, axes_save, \
                       cbar_axes_save, cbars, plot_data_all, plot_data = [None]*9

    # ------- inner loop -------
    while figure.itries < figure.itriesMax and not figure.success_plot:
        gc.collect()
        if verbose: print(' ------ ON itries:', figure.itries, '----------')
        figure.itries += 1
        if figure.itries >= figure.itriesMax:
            figure.itries = 0
            if verbose: print('RESET EVERYBODY')
            figure.success_plot = False
            plt.close('all')
            # have to reset everybody
            figure = reset_figure(**kwargs)
            if not allow_sky_image and 'image of the sky' in figure.plot_params:
                figure.plot_params['image of the sky']['prob'] = 0
            #**HERE** only need subset of params to stay the same AND figure out
            # what to reset (if a single subfig, then need to keep same
            # colormap/font/etc)
            try:
                del fig
            except:
                pass
            try:
                del datas
            except:
                pass
            try: 
                del axes_from_loop
            except:
                pass
            try:
                del axes_save
            except:
                pass
            try:
                del cbar_axes_save
            except:
                pass
            try:
                del cbars
            except:
                pass
            try:
                del plot_data_all
            except:
                pass
            try:
                del plot_data
            except:
                pass
            gc.collect()
        try:
            fig
        except:
            fig = None

        # close figure as needed
        close_plot_fail(fig, ifigure, fake_figs_dir, img_format, remove_diags=False, 
                figure_name=figure.figure_name)
        # print('FONTS NOW:', figure.font_params)


        ################# GET BASIC FIGURE #################
        _t0_sec = _time.time()
        try:
            if not figure.success_flags['get base plot']:
                gc.collect()
                plt.close('all')
                if verbose:
                    print('  -- generating base fig')
                    print_figure_params(figure.figure_params)
                # make base fig
                fig, axes_save, plot_inds, figsize,dpi_out = make_base_plot(figure.figure_params, verbose=False)
                figure.success_flags['get base plot'] = True
                figure.data_save['figsize'] = figsize
                figure.figure_params['facecolor'] = fig.get_facecolor()
                figure.figure_params['dpi'] = dpi_out
                # the injection pipeline pins figure_params (the box the figure
                # has to fit into) and needs these fed back so every reset
                # reuses them.  Standalone generation passes no figure_params
                # and wants a freshly randomised figure on each reset.
                if kwargs.get('figure_params') is not None:
                    kwargs['figure_params']['figsize'] = figsize
                    kwargs['figure_params']['facecolor'] = fig.get_facecolor()
                    kwargs['figure_params']['dpi'] = dpi_out
                if figdraw: fig.canvas.draw() # just give it a shot here
        except Exception as e1:
            figure, kwargs = check_exceptions(e1, figure, **kwargs) 

        _mrp_log_time('mrp_get_base_plot', _time.time() - _t0_sec, log_file=timing_log, rank=timing_rank, article=timing_article, page=timing_page, fignum=timing_fignum)
        if not figure.success_flags['get base plot']: # re do the loop
            continue

        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            if figdraw:
                try:
                    fig.canvas.draw()
                except UserWarning as ew:
                    figure, kwargs = check_exceptions(ew, figure, **kwargs)

        ################### CREATE DATA, ALL AXES ############
        _t0_sec = _time.time()
        err_add = ''
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)  # e.g., 300 for 5 minutes  
        try:
            # first, get all the data for the plot
            if not figure.success_flags['get data for plot']:
                if verbose: print('  -- generating data for plot')
                plot_data_all = []
                for iplot, ax in enumerate(axes_save):
                    plot_data, err = get_plot_data(figure.plot_params, 
                        figure.rng_dict['inner'], 
                        figure_params=figure.figure_params)
                    if err:
                        del plot_data
                        break
                    plot_data_all.append(deepcopy(plot_data))
                figure.success_flags['get data for plot'] = True
        except TimeoutError as et:
            err = True
            figure, kwargs = check_exceptions(et,figure, **kwargs)
            err_add = 'Timeout error -- ' + str(et)
        except Exception as e2:
                err = True
                err_add = str(e2)
        finally:
            signal.alarm(0)

        if err: # either via exception or not
            figure.success_flags['get data for plot'] = False
            figure.success_plot = False
            plt.close('all')
            # have to reset everybody
            figure = reset_figure(itries=figure.itries, **kwargs)
            try:
                del fig
            except:
                pass
            try:
                del datas
            except:
                pass
            try: 
                del axes_from_loop
            except:
                pass
            try:
                del axes_save
            except:
                pass
            try:
                del cbar_axes_save
            except:
                pass
            try:
                del cbars
            except:
                pass
            try:
                del plot_data_all
            except:
                pass
            try:
                del plot_data
            except:
                pass
            # gc.collect()
            if verbose:
                print('[ERROR]: in getting data, will reset and try again.')  
                if len(err_add) > 0:
                        print('  -- added error:', err_add)    
        _mrp_log_time('mrp_create_data', _time.time() - _t0_sec, log_file=timing_log, rank=timing_rank, article=timing_article, page=timing_page, fignum=timing_fignum)
        gc.collect()
        if not figure.success_flags['get data for plot']:
            continue


        ############# GET DATA FROM PLOT, ALL AXES ###########
        _t0_sec = _time.time()
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)  # e.g., 300 for 5 minutes  
        err_full = False                                 
        try:
            if not figure.success_flags['get data from plot']:
                if verbose: print('  -- getting data *from* plot')
                axes_from_loop = []
                for iplot, ax in enumerate(axes_save):
                    # get data for this plot
                    plot_data = plot_data_all[iplot]
                    # create axes and plot data
                    result = generate_data(fig, iplot, figure.figure_params, plot_data, 
                                                    figure.rng_dict['inner'], verbose=False)
                    if result is not None:
                        generated_data, ax, err = result
                    else:
                        generated_data, ax, err = None, None, True
                    if err:
                        err_full = True
                        #if verbose: print('[ERROR]: "generate_data" led to memory overflow')
                        if verbose: print('[ERROR]: "generate_data" created an error')
                        break # end this loop over axes
                    # save axes
                    axes_from_loop.append(ax)
                    # save
                    figure.data_save['data_for_plots'].append(deepcopy(plot_data['data_for_plot']))
                    figure.data_save['plot_types'].append(deepcopy(plot_data['plot_type']))
                    figure.data_save['data_from_plots'].append(generated_data['data_from_plot'])                    
                    figure.data_save['distribution_types'].append(deepcopy(plot_data['distribution_type']))
            if figdraw: fig.canvas.draw() # try again here
            if not err_full:
                figure.success_flags['get data from plot'] = True
        except TimeoutError as et:
            figure, kwargs = check_exceptions(et,figure, **kwargs)         
        except Exception as e3:   
            figure, kwargs = check_exceptions(e3,figure, **kwargs)
        finally:
            signal.alarm(0)

        _mrp_log_time('mrp_get_data_from_plot', _time.time() - _t0_sec, log_file=timing_log, rank=timing_rank, article=timing_article, page=timing_page, fignum=timing_fignum)
        if not figure.success_flags['get data from plot']:
            continue


        ################# SET TITLES AND AXIS LABELS ##############
        _t0_sec = _time.time()
        try:
            if not figure.success_flags['get titles']:
                if verbose: print('  -- generating titles and axis labels')
                xp,yp,tp = [],[],[]
                xpt,ypt,tpt = [],[],[]
                for iplot, ax in enumerate(axes_from_loop):
                    # get data for this plot
                    plot_data = plot_data_all[iplot]
                    success_loop_labels = False
                    itries_labels = 0
                    while not success_loop_labels and itries_labels <= figure.itriesMax:
                        # gc.collect()
                        itries_labels +=1
                        title, xlabel, ylabel = add_titles_and_labels(figure, plot_data, ax, iplot)
            
                        xlabels_pull2, ylabels_pull2, titles_pull2, err = collect_saved_labels(xlabel, ylabel, title)

                        if err: # issue getting labels, pull again
                            del title, xlabel, ylabel
                            continue
                        xp.append(xlabels_pull2); yp.append(ylabels_pull2); tp.append(titles_pull2)
                        xpt.append(xlabel); ypt.append(ylabel); tpt.append(title)
                        success_loop_labels = True
                if not success_loop_labels or itries_labels >= figure.itriesMax:
                    figure.success_flags['get titles'] = False
                    figure.success_plot = False
                    plt.close('all')
                    # have to reset everybody
                    figure = reset_figure(itries=figure.itries, **kwargs)
                    gc.collect()
                    try:
                        del fig
                        del datas
                        del axes_from_loop
                    except:
                        pass
                else: # all is well so far!
                    try:
                        # if figdraw: fig.canvas.draw() # try again
                        if figdraw:
                            renderer = fig.canvas.get_renderer()
                            for _t in tpt + xpt + ypt:  # the actual Text objects saved above
                                _t.draw(renderer)
                            # also try for axis tick labels
                            ax.get_xticklabels()
                            ax.get_yticklabels()
                        figure.data_save['titles'] = tpt
                        figure.data_save['xlabels'] = xpt
                        figure.data_save['ylabels'] = ypt
                        fontcolor = xpt[0].get_color()
                        figure.xlabels_pull = deepcopy(xp)
                        figure.ylabels_pull = deepcopy(yp)
                        figure.titles_pull = deepcopy(tp) 
                        figure.success_flags['get titles'] = True  
                    except Exception as e44:   
                        figure, kwargs = check_exceptions(e44,figure, **kwargs)
        except Exception as e4:   
            figure, kwargs = check_exceptions(e4, figure, **kwargs)
        _mrp_log_time('mrp_titles_labels', _time.time() - _t0_sec, log_file=timing_log, rank=timing_rank, article=timing_article, page=timing_page, fignum=timing_fignum)
        gc.collect()
        if not figure.success_flags['get titles']:
            continue

        figure.figure_params['fontcolor'] = fontcolor
        
        ############# GET COLOR BARS ##############
        _t0_sec = _time.time()
        try:
            # get colorbar stuff for each plot
            if not figure.success_flags['get colorbar titles']:
                cbar_words_list = figure.popular_nouns
                cbar_inlines = figure.inlines
                cbar_nums = []; cbar_words = []; cbars = []
                for iplot, ax in enumerate(axes_from_loop):
                    cbar, colorbar_words = parse_colorbar_data(figure,fig, iplot,
                                                        popular_nouns=cbar_words_list,
                                                        inlines=cbar_inlines)
                    # fill datasave
                    cbars.append(cbar)
                    cbar_words.append(colorbar_words)
                    if cbar is not None:
                        cbar_nums.append(len(cbar_nums)) # save axis of this colorbar
                        cbar_nums.append(len(cbar_nums)) # add extra for axes for colorbar
                    else:
                        cbar_nums.append(-1)
                if figdraw: fig.canvas.draw() # with norm, now need to draw after
                figure.success_flags['get colorbar titles'] = True
                figure.data_save['cbars'] = cbars
                figure.data_save['cbar_words'] = deepcopy(cbar_words)
                figure.data_save['cbar_nums'] = deepcopy(cbar_nums)
        except Exception as ec:
            figure.success_plot = False
            figure.success_flags['get colorbar titles'] = False
            figure, kwargs = check_exceptions(ec, figure, error_front=' in parse_colorbar_data -- ', **kwargs)                  
        _mrp_log_time('mrp_colorbars', _time.time() - _t0_sec, log_file=timing_log, rank=timing_rank, article=timing_article, page=timing_page, fignum=timing_fignum)
        if not figure.success_flags['get colorbar titles']:
            continue


        ############# SET FINAL COLORS ###########
        _t0_sec = _time.time()
        plt.set_cmap(figure.figure_params['color map'])
        plt.style.use(figure.figure_params['plot style'])
        plt.rcParams['font.family'] = str(figure.font_params['csfont']['fontname'])
        f2 = fig.get_facecolor()
        figure.success_flip = False
        # flip?
        if figure.figure_params['flipped font/face colors']:
            fig, facecolor, fontcolor, cbarsout = flip_colors(fig, figure, axes_from_loop)
            figure.figure_params['fontcolor'] = fontcolor
            figure.figure_params['facecolor'] = facecolor
        else:
            cbarsout = figure.data_save['cbars']
        try:
            fig.canvas.draw()
            figure.data_save['cbars'] = cbarsout
            figure.success_flip = True
        except Exception as ec11:
            figure.success_flip = False
            figure, kwargs = check_exceptions(ec11, figure, error_front=' in flipping colors -- ', **kwargs)

        _mrp_log_time('mrp_final_colors', _time.time() - _t0_sec, log_file=timing_log, rank=timing_rank, article=timing_article, page=timing_page, fignum=timing_fignum)
        if not figure.success_flip:
            continue


        ##############################################     
        ########## END OF TRYING TO MAKE PLOT ########
        ##############################################

        ####### SAVE DATA #########
        _t0_sec = _time.time()
        # if we've made it thus far, lets collect all the data
        success_fill_data = False
        try:
            datas, width, height = fill_datas(fig, figure, plot_inds)
            success_fill_data = True
        except Exception as e_fill_data1:
            success_fill_data = False
            if 'Tight layout not applied' in str(e_fill_data1): # issue with tight layout, redo
                if verbose: print('[ERROR]: tight layout not applied, take 2 - ', str(e_fill_data1))
                plt.close('all')
                figure = reset_figure(itries=figure.itries, **kwargs)
            else:
                if verbose: print('[ERROR]: in getting data from plot - ', str(e_fill_data1))
                plt.close('all')
                figure = reset_figure(itries=figure.itries, **kwargs)
                try:
                    del fig
                    del datas
                    del axes_from_loop
                    del axes_save
                except:
                    pass
                gc.collect()
        _mrp_log_time('mrp_save_data (fill datas)', _time.time() - _t0_sec, log_file=timing_log, rank=timing_rank, article=timing_article, page=timing_page, fignum=timing_fignum)
        if not success_fill_data:
            continue

        # which are axis and which are not?
        axes_save, cbar_axes_save, err = detect_cb_axes(fig, figure.data_save['cbar_nums'])
        if err:
            plt.close('all')
            figure = reset_figure(itries=figure.itries, **kwargs)
            try:
                del fig
                del datas
                del axes_from_loop
                del plot_data
            except:
                pass
            gc.collect()
            #data_save = create_data_save_dict()
            _mrp_log_time('mrp_save_data (detect cb axes)', _time.time() - _t0_sec, log_file=timing_log, rank=timing_rank, article=timing_article, page=timing_page, fignum=timing_fignum)
            continue

        # save the fig
        success_save = False
        try:
            for iformat in img_format:
                fig.tight_layout(h_pad=figure.figure_params['layout h_pad'], w_pad=figure.figure_params['layout w_pad'], pad=figure.figure_params['layout pad'])
                figure_name = figure.figure_name
                if figure_name is None:
                    figure_name = 'Picture_' + str(ifigure+1).zfill(6)
                fig.savefig(fake_figs_dir + 'imgs/' +figure_name+ '.'+iformat, 
                            dpi=figure.figure_params['dpi'], facecolor=figure.figure_params['facecolor'])
                if verbose: print('saved:', fake_figs_dir + 'imgs/' + figure_name + '.' +iformat)
            success_save = True
        except Exception as esave:
            success_save = False
            figure, kwargs = check_exceptions(esave, figure, error_front=' saving figure failed -- ', **kwargs)
        _mrp_log_time('mrp_save_data (savefig)', _time.time() - _t0_sec, log_file=timing_log, rank=timing_rank, article=timing_article, page=timing_page, fignum=timing_fignum)
        if not success_save:
            continue

        # Save the data from the fig and for the fig
        success_fill_data = False
        try:
            err = False
            for iplot, (ax,cbar_ax) in enumerate(zip(axes_save,cbar_axes_save)): ### XYZ, only 1 axis here
                iplot_data, iplot_err = collect_plot_data_axes(ax, fig,
                                figure, iplot,
                                height, width,
                                cbar_ax=cbar_ax,
                                colorbar_verbose=False,
                                verbose=verbose)
                datas['plot' + str(iplot)] = iplot_data
                err = err or iplot_err
            # one extra
            datas['figure']['figsize'] = figure.data_save['figsize']
            datas['figure']['facecolor'] = figure.figure_params['facecolor']
            if not err: 
                success_fill_data = True
                if verbose: print('  -- filled "datas" with to/from plot')
            else: # no idea, reset everybody
                success_fill_data = False
                plt.close('all')
                # have to reset everybody
                figure = reset_figure(itries=figure.itries, **kwargs)
                try:
                    del fig
                    del datas
                    del axes_from_loop
                except:
                    pass
                gc.collect()
                #data_save = create_data_save_dict()
        except Exception as e_fill_data:
            # laskjfal
            success_fill_data = False
            font_params_save = deepcopy(figure.font_params)
            if verbose:
                print('[ERROR] 2: ' + str(e_fill_data))
            if 'Glyph' in str(e_fill_data) and 'missing' in str(e_fill_data): # missing a glyph, try different font
                _, _, _, _, _, _, csfont = get_font_info(fontsizes, figure.font_names, rng=figure.rng_dict['font'])
                font_params_save['csfont'] = csfont
                figure.success_flags['get titles'] = False
                kwargs['font_params'] = deepcopy(font_params_save)
            else: # no idea! reset everybody
                # have to reset everybody
                plt.close('all')
                figure = reset_figure(itries=figure.itries, **kwargs)
                try:
                    del fig
                    del datas
                    del axes_from_loop
                except:
                    pass
                gc.collect()
        _mrp_log_time('mrp_save_data (save data)', _time.time() - _t0_sec, log_file=timing_log, rank=timing_rank, article=timing_article, page=timing_page, fignum=timing_fignum)
        if not success_fill_data:
            figure.font_params = deepcopy(font_params_save)
            kwargs['font_params'] = deepcopy(font_params_save)
            continue

        # figure.save_pre_check_diagnostic_plot = True
        if figure.save_pre_check_diagnostic_plot:
            import pathlib as _pathlib
            _pathlib.Path(fake_figs_dir + 'diags/').mkdir(exist_ok=True, parents=True)
            img_diag = np.array(Image.open(fake_figs_dir + 'imgs/' + figure_name + '.' + img_format[0]).convert('RGB'))
            _pre_imgplot = add_annotations(img_diag, deepcopy(datas), verbose=False)
            Image.fromarray(_pre_imgplot).save(fake_figs_dir + 'diags/' + figure_name + '_pre.' + img_format[0])
            if verbose:
                print('saved pre-check diagnostic plot:', fake_figs_dir + 'diags/' + figure_name + '_pre.' + img_format[0])
            del _pre_imgplot

        ################################################################
        ########### CHECKS -- titles off, bounding boxes, etc ##########
        ################################################################
        _t0_sec = _time.time()
        if verbose: print('  -- running checks...')

        # 1. Check for square with weird aspect ratio
        if check_aspect_ratio:
            try:
                success_aspect, aspect_errors_iplot = check_aspect(datas, aspect_cut, verbose=verbose)
            except Exception as ea:
                if verbose: print('[ERROR]: in check_aspect -- ', str(ea))
                success_aspect = False
                if 'cannot unpack non-iterable' in str(ea):
                    lkfjalsj
            if not success_aspect:
                print('[UPDATE]: JPN -- should in theory just re-grab data for this index plot!!')
                plt.close('all')
                # have to reset everybody
                figure = reset_figure(itries=figure.itries, **kwargs)
                gc.collect()
                try:
                    del fig
                    del datas
                    del axes_from_loop
                except:
                    pass
                _mrp_log_time('mrp_checks', _time.time() - _t0_sec, log_file=timing_log, rank=timing_rank, article=timing_article, page=timing_page, fignum=timing_fignum)
                continue

        # 2. Check if titles or x/y axis labels are running off the page     
        try:
            figure, reset_all, remake_plot = check_labels_titles_off_page(datas, figure,
                                                                        fontsizes,
                                                                        fontsize_min = fontsizes['fontsize min'], 
                                                                        verbose=verbose)
        except Exception as er:
            if verbose:
                print('[ERROR]: in check 2 --', str(er))
            reset_all = True
        if reset_all:
            plt.close('all')
            if verbose: print('[ERROR]: in checking for titles off page')
            font_params_save = deepcopy(figure.font_params)
            # have to reset everybody
            kwargs['font_params'] = font_params_save
            figure = reset_figure(itries=figure.itries, **kwargs)
            try:
                del fig
                del datas
                del axes_from_loop
            except:
                pass
            gc.collect()
            #data_save = create_data_save_dict()
        if remake_plot:
            if verbose: print('[ERROR]: need to remake plot')
            _mrp_log_time('mrp_checks', _time.time() - _t0_sec, log_file=timing_log, rank=timing_rank, article=timing_article, page=timing_page, fignum=timing_fignum)
            continue


        # 3. Save the figure, check if issues opening it    
        # check if issue opening plot
        e = ''
        success_reopen = False
        try:
            for iformat in img_format:
                #img = np.array(Image.open(fake_figs_dir + 'imgs/Picture_' + str(ifigure+1).zfill(6) + '.' + iformat))
                img = np.array(Image.open(fake_figs_dir + 'imgs/' + figure_name + '.' + iformat))
            success_reopen = True
        except Exception as e:
            success_reopen = False
            plt.close('all')
            if verbose:
                print('[ERROR]: Issue with opening image!')
                if str(e) != '': print('Full error:', str(e))
            # have to reset everybody
            figure = reset_figure(itries=figure.itries, **kwargs)
            gc.collect()
            #data_save = create_data_save_dict()
            try:
                del fig
                del datas
                del axes_from_loop
            except:
                pass
        _mrp_log_time('mrp_checks', _time.time() - _t0_sec, log_file=timing_log, rank=timing_rank, article=timing_article, page=timing_page, fignum=timing_fignum)
        if not success_reopen:
            continue


        # 4. check if any figure boxes, title boxes, axis label boxes, etc overlap with eachother
        success_boxes, boxes_check, names_overlap = collect_boxes(datas, grace_ticks=grace_ticks)
        fignamesout = {}
        fignamesout['figure'] = fake_figs_dir + 'imgs/' + figure_name + '.' + img_format[0]
        # save diagnostics plot
        if figure.save_diagnostic_plot:
            import pathlib as _pathlib
            _pathlib.Path(fake_figs_dir + 'diags/').mkdir(exist_ok=True, parents=True)
            img_diag = np.array(Image.open(fake_figs_dir + 'imgs/' + figure_name + '.' + img_format[0]).convert('RGB'))
            imgplot = add_annotations(img_diag, deepcopy(datas), verbose=False)
            imgplot = Image.fromarray(imgplot).save(fake_figs_dir + 'diags/' + figure_name + '.' + img_format[0])
            if verbose:
                #print('saved diagnostic plot:', fake_figs_dir + 'diags/Picture_' + str(ifigure+1).zfill(6) + '.' + img_format[0])
                print('saved diagnostic plot:', fake_figs_dir + 'diags/' + figure_name + '.' + img_format[0])
            del imgplot
            fignamesout['diagnostic'] = fake_figs_dir + 'diags/' + figure_name + '.' + img_format[0]


        if not success_boxes:
            figure.success_plot = False
            if verbose:
                print('[ERROR]: bounding boxes overlap')
            # try making everything smaller
            #print('****kwargs before:', kwargs)
            figure, kwargs = update_fonts_boxes_overlap(names_overlap,figure,
                               fontsizes,
                                fontsize_min=fontsizes['fontsize min'], **kwargs)
            gc.collect()
        _mrp_log_time('mrp_checks', _time.time() - _t0_sec, log_file=timing_log, rank=timing_rank, article=timing_article, page=timing_page, fignum=timing_fignum)
        if not success_boxes:
            #print('*****kwargs after:', kwargs)
            #lskfajslj
            continue

        # 5. Check for size of plot(s) within the figure
        success_area, area = check_plot_area(datas)
        if not success_area:
            plt.close('all')
            if verbose:
                print('[ERROR]: Plot area too small (w/rt figure area), ratio =', area)
                if str(e) != '': print('Full error:', str(e))
            # have to reset everybody
            #figure = FigureRun()
            figure = reset_figure(itries=figure.itries, **kwargs)
            gc.collect()
            #data_save = create_data_save_dict()
            try:
                del fig
                del datas
                del axes_from_loop
            except:
                pass
            _mrp_log_time('mrp_checks', _time.time() - _t0_sec, log_file=timing_log, rank=timing_rank, article=timing_article, page=timing_page, fignum=timing_fignum)
            continue


        ############################################################
        ############### DONE -- SAVE EVERYTHING ####################
        ############################################################
        _t0_sec = _time.time()

        # made it to the end -- success!
        figure.success_plot = True
        #import sys; sys.exit()

        diagsout = {'success': True} # whatelse to save??

        if figure.success_plot:
            dirsout = close_plot_success(fig, datas, ifigure, fake_figs_dir, figure.figure_params, figure.font_params, 
                                        return_dirs=True, figure_name=figure.figure_name)
            for k,v in dirsout.items():
                fignamesout[k] = v
            # del fig, datas, data_save,  axes_from_loop, axes_save, \
            #             cbar_axes_save, cbars, plot_data_all, plot_data, ax
            plt.close(fig)
            try:
                del fig
            except:
                pass
            try:
                del datas
            except:
                pass
            try:
                del axes_from_loop
            except:
                pass
            try:
                del axes_save
            except:
                pass
            try:
                del cbar_axes_save
            except:
                pass
            try:
                del cbars
            except:
                pass
            try:
                del plot_data_all
            except:
                pass
            try:
                del plot_data
            except:
                pass
            try:
                del ax
            except:
                pass
            gc.collect()
            #data_save = create_data_save_dict()
            #import sys; sys.exit()
            # rng_dict, seeds_dict, figure_params, \
            #     font_params, xlabels_pull, ylabels_pull, \
            #         titles_pull, data_save, success_flags = reset_everybody(color_maps, plot_styles, 
            #                                                     aspect_fig_params, dpi_params, 
            #                                                     panel_params, tight_layout_params, 
            #                                                     fontsizes, font_names, popular_nouns, success_flags)
            #figure = FigureRun()
            figure = reset_figure(itries=figure.itries, **kwargs)

            _mrp_log_time('mrp_done', _time.time() - _t0_sec, log_file=timing_log, rank=timing_rank, article=timing_article, page=timing_page, fignum=timing_fignum)
            return diagsout

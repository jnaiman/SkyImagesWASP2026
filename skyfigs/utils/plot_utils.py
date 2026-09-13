# utilities to create plots of different kinds
import matplotlib.pyplot as plt
import matplotlib as mpl
mpl.rcParams['text.usetex'] = True
mpl.rcParams['text.latex.preamble'] = r'\usepackage{amsmath} \usepackage{amssymb}' #for \text command
from mpl_toolkits.axes_grid1 import make_axes_locatable
import numpy as np
from PIL import ImageColor

# classes
from .plot_classes_utils import Histogram, Line, Scatter, Contour

# for scatter plot markers
from matplotlib.lines import Line2D
marker_dir = Line2D.markers

# for astro coord systems
from astropy.wcs import WCS

# for astro coord systems
#from astropy.wcs import WCS

markers = []
for m,mn in marker_dir.items():
    if type(m) == str:
        if 'None' not in m.lower() and 'nothing' not in mn.lower():
            #print(m, mn)
            markers.append(m)
    else:
        #print(m,mn)
        markers.append(m)

markers = np.array(markers,dtype=object)

# for line styles
from .synthetic_fig_utils import get_line_styles
linestyles = get_line_styles()

# for colors
# how many random colors to generate?
# e.g. colors = colors_(6)
#colors_ = lambda n: list(map(lambda i: "#" + "%06x" % rng.integer(0, 0xFFFFFF),range(n)))
# JPN: should really be picked with a seed but leaving as is for now
colors_ = lambda n: list(map(lambda i: "#" + "%06x" % np.random.randint(0, 0xFFFFFF),range(n)))


# LINES PLOT
def get_line_plot(plot_params, data, ax, linestyles=linestyles, rng=np.random, **kwargs):
    """
    kwargs allows for passing of parameters to be set
    """
    line = Line()
    for k,v in kwargs.items():
        if k in line.__dict__: # in there
            setattr(line, k, v)

    datas = []
    linestyles_here = []; linethicks_here = []; markers_here = []
    marker_sizes_here = []
    xerrs = []; yerrs = []
    if line.hasMarker is None: 
        hasMarker = False
        p = rng.uniform(0,1)
        if p <= plot_params['markers']['prob']:
            hasMarker = True
    else:
        hasMarker = line.hasMarker
    colors_here = []

    if line.elinewidth is None:
        elinewidth = int(round(rng.uniform(low=plot_params['error bars']['elinewidth']['min'], 
                                            high=plot_params['error bars']['elinewidth']['max'])))
    # draw lines
    #xerrs = []; yerrs = []
    # a few tests
    for attr in ['markers', 'lthicks', 'linestyles', 'marker_sizes', 'linecolors']:
        if getattr(line, attr) is not None:
            if type(getattr(line, attr)) != type([]):
                print('type of ' + attr + ' is not correct, setting default')
                setattr(line,attr,None)
            elif len(getattr(line, attr)) != len(data['ys']):
                if len(getattr(line, attr)) > len(data['ys']):
                    print('wrong length for '+attr+', truncating')
                    setattr(line,attr, getattr(line, attr)[:len(data['ys'])])
                else:
                    print('wrong length for '+attr+', setting to default')
                    setattr(line, attr, None)


    for i in range(len(data['ys'])):
        if line.marker is None and line.markers is None:
            marker = rng.choice(markers)
        elif line.marker is not None:
            marker = line.marker
        elif line.markers is not None:
            marker = line.markers[i]

        if line.lthick is None and line.lthicks is None:
            lthick = rng.uniform(low=plot_params['line thick']['min'], 
                                   high=plot_params['line thick']['max'])
        elif line.lthick is not None:
            lthick = line.lthick
        elif line.lthicks is not None:
            lthick = line.lthicks[i]

        # choose random linestyle
        if line.linestyle is None and line.linestyles is None:
            linestyle = rng.choice(linestyles)
        elif line.linestyle is not None:
            linestyle = line.linestyle
        elif line.linestyles is not None:
            linestyle = line.linestyles[i]

        if line.linecolor is None and line.linecolors is None:
            try:
                #linecolor = ImageColor.getcolor(data_here.get_color(), "RGBA")
                linecolor = np.array(ImageColor.getcolor(colors_(1)[0], 'RGBA'))
                #cols.append(linecolor)
            except Exception as e:
                print('Issue getting line color:', str(e))
                #cols.append( (0,0,0) ) # I assume
                linecolor = (0,0,0)
            linecolor = np.array(linecolor)/255.
        elif line.linecolor is not None:
            linecolor = line.linecolor
        elif line.linecolors is not None:
            linecolor = line.linecolors[i]

        if hasMarker:
            if line.marker_size is None and line.marker_sizes is None:
                marker_size = int(round(rng.uniform(low=plot_params['markers']['size']['min'],
                                            high=plot_params['markers']['size']['min'])))
            elif line.marker_size is not None:
                marker_size = line.marker_size
            elif line.marker_sizes is not None:
                marker_size = line.marker_sizes[i]
            data_here, = ax.plot(data['xs'][i],data['ys'][i], linewidth=lthick, 
                                 linestyle = linestyle, marker=marker,
                                markersize=marker_size, color=linecolor)
        else:
            data_here, = ax.plot(data['xs'][i],data['ys'][i], linewidth=lthick, 
                                 linestyle = linestyle, color=linecolor)
            marker = ''
            marker_size = -1

        #cols = []
        plt.draw()
        #print('DRAW WAS CALLED')
        # try:
        #     cols.append(ImageColor.getcolor(data_here.get_color(), "RGBA"))
        # except:
        #     cols.append( (0,0,0) ) # I assume
        # cols = np.array(cols)/255.

        if 'xerrs' in data:# and 'yerrs' not in data: # have x-errors
            (_, caps, bars) = ax.errorbar(data['xs'][i],data['ys'][i],xerr=data['xerrs'][i],
                                         linewidth=0,elinewidth=elinewidth,
                                         markersize=0, ecolor=linecolor, zorder=0)
            xerrs.append(bars)
        if 'yerrs' in data:# and 'xerrs' not in data: # have x-errors
            (_, caps, bars) = ax.errorbar(data['xs'][i],data['ys'][i],yerr=data['yerrs'][i],
                                         linewidth=0, elinewidth=elinewidth,
                                         markersize=0, ecolor=linecolor, zorder=0)
            yerrs.append(bars)
        
        linethicks_here.append(lthick)
        linestyles_here.append(linestyle)
        markers_here.append(marker)
        datas.append(data_here)
        marker_sizes_here.append(marker_size)
        colors_here.append(linecolor)

    data_out = {'data':datas, 'plot params':{'linethick':linethicks_here, 
                                            'linestyles':linestyles_here,
                                            'markers':markers_here,
                                            'marker size':marker_sizes_here,
                                            'colors':colors_here}
               }
    # add in x/y errors, if present
    if 'xerrs' in data:
        data_out['x error bars'] = xerrs
    if 'yerrs' in data:
        data_out['y error bars'] = yerrs
    return data_out, ax




# SCATTERS: PLOTS
def get_scatter_plot(plot_params, data, ax, rng=np.random, **kwargs):
    scatter = Scatter()
    for k,v in kwargs.items():
        if k in scatter.__dict__: # in there
            setattr(scatter, k, v)

    # set choices
    for attr in ['markers', 'marker_sizes']:
        if getattr(scatter, attr) is not None:
            if type(getattr(scatter, attr)) != type([]):
                print('type of ' + attr + ' is not correct, setting default')
                setattr(scatter,attr,None)
            elif len(getattr(scatter, attr)) != len(data['ys']):
                if len(getattr(scatter, attr)) > len(data['ys']):
                    print('wrong length for '+attr+', truncating')
                    setattr(scatter,attr, getattr(scatter, attr)[:len(data['ys'])])
                else:
                    print('wrong length for '+attr+', setting to default')
                    setattr(scatter, attr, None)

    p = rng.uniform(0,1)
    cax = []; side = ''
    # choose marker
    if scatter.marker is None and scatter.markers is None:
        marker = rng.choice(markers)
    elif scatter.marker is not None:
        marker = scatter.marker
    elif scatter.markers is not None:
        marker = scatter.markers
    # choose marker size
    if scatter.marker_size is None and scatter.marker_sizes is None:
        marker_size = int(round(rng.uniform(low=plot_params['markers']['size']['min'],
                                        high=plot_params['markers']['size']['min'])))
    elif scatter.marker is not None:
        marker_size = scatter.marker_size
    elif scatter.marker_sizes is not None:
        marker = scatter.marker_sizes
    

    if not p <= plot_params['colormap scatter']['prob']: # not have color map
        data_here = ax.scatter(data['xs'],data['ys'],marker=marker, s=marker_size) 
    else:
        #print('have colormap')
        data_here = ax.scatter(data['xs'],data['ys'], 
                               c=data['colors'],marker=marker, 
                              s=marker_size) # need to add color
        divider = make_axes_locatable(ax)

        # get colorbar side/size
        if scatter.colorbar_side is None:
            probs = []; choices = []
            for k,v in plot_params['color bar']['location probs'].items():
                probs.append(v); choices.append(k)
            side = rng.choice(choices, p=probs)
        else:
            side = scatter.colorbar_side
        if scatter.colorbar_size is None:
            size = rng.uniform(low=plot_params['color bar']['size percent']['min'], 
                        high=plot_params['color bar']['size percent']['max'])
            size = str(int(round(size*100)))+'%'
        else:
            size = scatter.colorbar_size

        if scatter.colorbar_pad is None:
            pad = rng.uniform(low=plot_params['color bar']['pad']['min'], 
                                 high=plot_params['color bar']['pad']['max'])
        else:
            pad = scatter.colorbar_pad

        #print('side,size,pad', side,size,pad)

        cax = divider.append_axes(side, size=size, pad=pad)
        # the side of the axis
        if side == 'right': # this maybe should become a random selection?
            axis_side = 'right'
            cax.yaxis.set_ticks_position(axis_side)
        elif side == 'left':
            axis_side = 'left'
            cax.yaxis.set_ticks_position(axis_side)
        elif side == 'top':
            axis_side = 'top'
            cax.xaxis.set_ticks_position(axis_side)
        elif side == 'bottom':
            axis_side = 'bottom'
            cax.xaxis.set_ticks_position(axis_side)

    xerrs = []; yerrs = []
    plt.draw()
    #print('DRAW WAS CALLED 2')
    cols = data_here.get_facecolors() # color is set by data
    #print(cols)
    if scatter.elinewidth is None:
        elinewidth = int(round(rng.uniform(low=plot_params['error bars']['elinewidth']['min'], 
                                                 high=plot_params['error bars']['elinewidth']['max'])))
    else:
        elinewidth = scatter.elinewidth
    if 'xerrs' in data:# and 'yerrs' not in data: # have x-errors
        cols_scatter = cols.reshape(-1,4)#*255
        cols_scatter[cols_scatter<0] = 0
        cols_scatter[cols_scatter>1] = 1     
        cols_scatter = cols_scatter.astype('float')  
        try:
            (_, caps, bars) = ax.errorbar(data['xs'],data['ys'],xerr=data['xerrs'],
                                     linewidth=0,elinewidth=elinewidth,
                                     markersize=0, 
                                      ecolor=cols_scatter, zorder=0)

        except Exception as e:
            try:
                cols_scatter = np.clip(cols_scatter, 0, 1).astype('float')
                bars = []
                for i in range(len(data['xs'])):
                    _,c,b = ax.errorbar(data['xs'][i], data['ys'][i], 
                                xerr=data['xerrs'][i],
                                linewidth=0, elinewidth=elinewidth,
                                markersize=0,
                                ecolor=cols_scatter[i],  # now a single (r,g,b,a) tuple
                                zorder=0)
                    bars.extend(b)
            except Exception as e2:
                print('Issue with colors in xerrs (2):')
                print(e2)
                (_, caps, bars) = ax.errorbar(data['xs'],data['ys'],xerr=data['xerrs'],
                                         linewidth=0,elinewidth=elinewidth,
                                         markersize=0, zorder=0)
                print('data shape - xs,ys,xerrs:', data['xs'].shape, data['ys'].shape, 
                      data['xerrs'].shape)
                print('colors shape:', cols_scatter.shape)
                print('colors min/max:', cols_scatter.min(), cols_scatter.max())

        xerrs.append(bars)
    if 'yerrs' in data:# and 'xerrs' not in data: # have x-errors
        cols_scatter = cols.reshape(-1,4)#*255
        # make sure no min/max
        cols_scatter[cols_scatter<0] = 0
        cols_scatter[cols_scatter>1] = 1
        try:
            (_, caps, bars) = ax.errorbar(data['xs'],data['ys'],yerr=data['yerrs'],
                                     linewidth=0, elinewidth=elinewidth,
                                     markersize=0, 
                                      ecolor=cols_scatter, zorder=0)
        except Exception as e:
            try:
                cols_scatter = np.clip(cols_scatter, 0, 1).astype('float')
                
                bars = []
                for i in range(len(data['xs'])):
                    _,c,b = ax.errorbar(data['xs'][i], data['ys'][i], 
                                yerr=data['yerrs'][i],
                                linewidth=0, elinewidth=elinewidth,
                                markersize=0,
                                ecolor=cols_scatter[i],  # now a single (r,g,b,a) tuple
                                zorder=0)
                    bars.extend(b)
            except Exception as e2:
                print('Issue with colors in yerrs (2):')
                print(e2)
                (_, caps, bars) = ax.errorbar(data['xs'],data['ys'],yerr=data['yerrs'],
                                        linewidth=0, elinewidth=elinewidth,
                                        markersize=0, zorder=0)
                print('data shape - xs,ysyxerrs:', data['xs'].shape, data['ys'].shape, 
                    data['yerrs'].shape)
                print('colors shape:', cols_scatter.shape)
                print('colors min/max:', cols_scatter.min(), cols_scatter.max())
        yerrs.append(bars)
        
    # save data
    if cax != []:
        data_out = {'data':data_here, 'color bar':cax, 'marker':marker, 'marker size':marker_size,
                    'color bar params':{'side':side, 'pad':pad, 'size':size, 
                                       'axis side':axis_side, 
                                       'label prob': plot_params['color bar']['label prob']
                                       }
                   }
    else:
        data_out = {'data':data_here, 'marker':marker, 'marker size':marker_size}

    # add in x/y errors, if present
    if 'xerrs' in data:
        data_out['x error bars'] = xerrs
    if 'yerrs' in data:
        #print("YESS TO Y IN DATA")
        data_out['y error bars'] = yerrs
    if 'xerrs' in data or 'yerrs' in data:
        data_out['error bar params'] = {'elinewidth':elinewidth}
    
    return data_out, ax



def _square_bin_aspect(ax, data, verbose=False):
    """
    Make one data bin draw as a square.

    A bin is box_w/nx wide and box_h/ny tall on screen, so square bins need
    box_w/nx == box_h/ny.  The axes box is sized by the subplot layout, not by
    the grid, and the margins taken by labels and a colorbar mean its aspect
    differs from the figure's -- which is what ny was derived from.  Setting the
    axes aspect closes that gap:

        set_aspect(a),  a = sy/sx  =>  box_h/box_w = a * yrange/xrange
        square bins     <=>  box_h/box_w = ny/nx
        =>  a = (xrange/yrange) * (ny/nx)

    Sky images get this for free -- wcsaxes holds an equal aspect, so their bins
    already measure 1.00 -- this is the contour equivalent.
    """
    try:
        cols = np.asarray(data['colors'])
        if cols.ndim != 2:
            return None
        ny, nx = cols.shape
        xs, ys = np.asarray(data['xs']), np.asarray(data['ys'])
        xrange = float(xs[-1] - xs[0])
        yrange = float(ys[-1] - ys[0])
        if not np.isfinite(xrange) or not np.isfinite(yrange) or xrange == 0 or yrange == 0:
            return None
        a = abs(xrange / yrange) * (float(ny) / float(nx))
        if not np.isfinite(a) or a <= 0:
            return None
        ax.set_aspect(a, adjustable='box')
        if verbose:
            print('  [bins] aspect set to %.4g for square %dx%d bins' % (a, nx, ny))
        return a
    except Exception as e:
        if verbose:
            print('  [bins] could not set aspect:', str(e))
        return None


def get_contour_plot(plot_params, data, ax, rng=np.random, **kwargs):
    contour = Contour()
    for k,v in kwargs.items():
        if k in contour.__dict__: # in there
            setattr(contour, k, v)

    if contour.plot_type is None:
        p = rng.uniform(0,1) # probability that has a colorbar
        #pi = rng.uniform(0,1) # probability that is an image (vs a contour with lines)
        choices = []; probs = []
        for k,v in plot_params['image or contour']['prob'].items():
            choices.append(k)
            probs.append(v)
        plot_type = rng.choice(choices, p=probs)
    else:
        plot_type = contour.plot_type
    cax = []; side = ''

    if plot_type == 'contour':
        if contour.nlevels is None:
            nlevels = int(round(rng.uniform(low=plot_params['nlines']['min'],
                                              high=plot_params['nlines']['max'])))
        else:
            nlevels = contour.nlevels
        data_here2 = ax.contour(data['xs'], data['ys'], data['colors'], nlevels)
        data_here = {'contour':data_here2}
    elif plot_type == 'image':
        real_x = data['xs']
        real_y = data['ys']
        dx = (real_x[1]-real_x[0])/2.
        dy = (real_y[1]-real_y[0])/2.
        extent = [real_x[0]-dx, real_x[-1]+dx, real_y[0]-dy, real_y[-1]+dy]
        #plt.imshow(data, extent=extent)
        #print('extent', extent)
        data_here1 = ax.imshow(np.ascontiguousarray(data['colors']), extent=extent)#, aspect=100)
        data_here = {'image':data_here1}
    elif plot_type == 'both':
        if contour.grayContours is None:
            pg = rng.uniform(0,1)
            grayContours = False
            if pg <= plot_params['image or contour']['both contours']['prob gray']: # probability that contours are gray for "both" situation
                grayContours = True
        else:
            grayContours = contour.grayContours
        cmap = rng.choice(['gray', 'gray_r'])
        real_x = data['xs']
        real_y = data['ys']
        dx = (real_x[1]-real_x[0])/2.
        dy = (real_y[1]-real_y[0])/2.
        extent = [real_x[0]-dx, real_x[-1]+dx, real_y[0]-dy, real_y[-1]+dy]
        data_here1 = ax.imshow(np.ascontiguousarray(data['colors']), extent=extent)
        if contour.nlevels is None:
            nlevels = int(round(rng.uniform(low=plot_params['nlines']['min'],
                                              high=plot_params['nlines']['max'])))
        else:
            nlevels = contour.nlevels
        if not grayContours:
            data_here2 = ax.contour(data['xs'], data['ys'], data['colors'], nlevels)
        else:
            data_here2 = ax.contour(data['xs'], data['ys'], data['colors'], nlevels,
                                   cmap=cmap)

        data_here = {'image':data_here1, 'contour':data_here2}
    else:
        print('not supported plot type!')
        import sys; sys.exit()

    if not p <= plot_params['colormap contour']['prob']: # not have color map
        pass 
    else:
        divider = make_axes_locatable(ax)

        # get probs
        if contour.colorbar_side is None:
            probs = []; choices = []
            for k,v in plot_params['color bar']['location probs'].items():
                probs.append(v); choices.append(k)
            side = rng.choice(choices, p=probs)
        else:
            side = contour.colorbar_side
        if contour.colorbar_size is None:
            size = rng.uniform(low=plot_params['color bar']['size percent']['min'], 
                     high=plot_params['color bar']['size percent']['max'])
        else:
            size = contour.colorbar_size

        size = str(int(round(size*100)))+'%'
        if contour.colorbar_pad is None:
            pad = rng.uniform(low=plot_params['color bar']['pad']['min'], 
                                 high=plot_params['color bar']['pad']['max'])
        else:
            pad = contour.colorbar_pad

        cax = divider.append_axes(side, size=size, pad=pad)
        # the side of the axis
        if side == 'right': # this maybe should become a random selection?
            axis_side = 'right'
            cax.yaxis.set_ticks_position(axis_side)
        elif side == 'left':
            axis_side = 'left'
            cax.yaxis.set_ticks_position(axis_side)
        elif side == 'top':
            axis_side = 'top'
            cax.xaxis.set_ticks_position(axis_side)
        elif side == 'bottom':
            axis_side = 'bottom'
            cax.xaxis.set_ticks_position(axis_side)
    # Square bins, to match what the sky images get from wcsaxes.  Applied AFTER
    # the colorbar: make_axes_locatable places the colorbar against the axes'
    # position at append time, so shrinking the parent to satisfy an aspect
    # beforehand leaves the two mismatched and drives up overlap rejections.
    _square_bin_aspect(ax, data)

    plt.draw()
    #print('DRAW WAS CALLED 3')

    # xerrs = []; yerrs = []
    # plt.draw()
    # cols = data_here.get_facecolors()
    # elinewidth = int(round(rng.uniform(low=plot_params['error bars']['elinewidth']['min'], 
    #                                              high=plot_params['error bars']['elinewidth']['max'])))
    # if 'xerrs' in data:# and 'yerrs' not in data: # have x-errors
    #     (_, caps, bars) = ax.errorbar(data['xs'],data['ys'],xerr=data['xerrs'],
    #                                  linewidth=0,elinewidth=elinewidth,
    #                                  markersize=0, ecolor=cols, zorder=0)
    #     xerrs.append(bars)
    # if 'yerrs' in data:# and 'xerrs' not in data: # have x-errors
    #     (_, caps, bars) = ax.errorbar(data['xs'],data['ys'],yerr=data['yerrs'],
    #                                  linewidth=0, elinewidth=elinewidth,
    #                                  markersize=0, ecolor=cols, zorder=0)
    #     yerrs.append(bars)
        
    # save data
    if cax != []:
        data_out = {'data':data_here, 'color bar':cax, 
                    'color bar params':{'side':side, 'pad':pad, 'size':size, 
                                       'axis side':axis_side,
                                       'label prob': plot_params['color bar']['label prob']
                                        }#, 
                                       #'marker':marker, 'marker size':marker_size}
                   }
    else:
        data_out = {'data':data_here}

    # # add in x/y errors, if present
    # if 'xerrs' in data:
    #     data_out['x error bars'] = xerrs
    # if 'yerrs' in data:
    #     #print("YESS TO Y IN DATA")
    #     data_out['y error bars'] = yerrs
    # if 'xerrs' in data or 'yerrs' in data:
    #     data_out['error bar params'] = {'elinewidth':elinewidth}
    
    return data_out, ax









# HISTOGRAMS: PLOTS
def get_histogram_plot(plot_params, data, ax, linestyles=linestyles, rng=np.random, **kwargs):
                    #    elinewidth = None, rwidth=None, orientation=None, axis=None, 
                    #    lthick=None, linestyle=None):
    # datas = []
    # linestyles_here = []; linethicks_here = []; markers_here = []
    # marker_sizes_here = []
    # xerrs = []; yerrs = []
    """
    The "None" parameters allow for the specific setting of parameters of the plot, otherwise, they are chosen from a distribution.
    """
    hist = Histogram()
    for k,v in kwargs.items():
        if k in hist.__dict__: # in there
            setattr(hist, k, v)
    #     if 'elinewidth' in k:
    #         elinewidth = v
    # for k,v in hist.__dict__.items():
    #     if k

       

    if hist.elinewidth is None:
        hist.elinewidth = int(round(rng.uniform(low=plot_params['error bars']['elinewidth']['min'], 
                                            high=plot_params['error bars']['elinewidth']['max'])))
    #print('rwidth before', hist.rwidth)
    if hist.rwidth is None:
        hist.rwidth = rng.uniform(low=plot_params['rwidth']['min'], 
                                            high=plot_params['rwidth']['max'])
    #print('rwidth', hist.rwidth)

    if hist.orientation is None: hist.orientation='vertical' # default
    if hist.axis is None: hist.axis = 'xs'
    #err = 'xerrs'
    if len(data['xs']) == 0: # flipped!
        hist.axis = 'ys'
        #err = 'yerrs'
        hist.orientation='horizontal'


    # line boarder?
    if hist.lthick is None: 
        hist.lthick = int(round(rng.uniform(low=plot_params['line thick']['min'], 
                               high=plot_params['line thick']['max'])))
        if rng.uniform(0,1) > plot_params['line thick']['prob']:
            hist.lthick = 0

    # choose random linestyle
    if hist.linestyle is None: hist.linestyle = rng.choice(linestyles)

    # choose random color
    if hist.linecolor is None: hist.linecolor = np.array(ImageColor.getcolor(colors_(1)[0],'RGBA'))/255
    if hist.barcolor is None: hist.barcolor = np.array(ImageColor.getcolor(colors_(1)[0], 'RGBA'))/255

    # try a thing
    hist.linecolor = np.array(hist.linecolor)
    if len(hist.linecolor.shape) == 1:
        hist.linecolor = [hist.linecolor]

    # number of bins?
    if hist.nbins is None: hist.nbins = int(round(rng.uniform(low=plot_params['nbins']['min'], 
                                            high=plot_params['nbins']['max'])))

    if hist.lthick > 0:
        #try:
        # print('edgecolor=', hist.linecolor, len(hist.linecolor))
        # print('color=', hist.barcolor)
        # print('')
        try:
            data_here = ax.hist(data[hist.axis], orientation=hist.orientation, linewidth=hist.lthick, 
                                        linestyle = hist.linestyle, 
                                        edgecolor=hist.linecolor, 
                                color=hist.barcolor, 
                                rwidth=hist.rwidth, bins=hist.nbins)
        except:
            if len(hist.linecolor) == 1: # just the one color
                hist.linecolor = hist.linecolor[0]
            data_here = ax.hist(data[hist.axis], orientation=hist.orientation, linewidth=hist.lthick, 
                                        linestyle = hist.linestyle, 
                                        edgecolor=hist.linecolor, 
                                color=hist.barcolor, 
                                rwidth=hist.rwidth, bins=hist.nbins)
            
            
                    # except Exception as e:
        #     print(str(e))
        #     print('data:',data[axis])
        #     print('orientation:',orientation)
        #     print('linewidth:', lthick)
        #     print('linestyle:', linestyle)
        #     print('linecolor:', linecolor)
        #     print('rwidth:', rwidth)
        #     print('color:',barcolor)
        #     print('nbins:', nbins)
    else:
        try:
            data_here = ax.hist(data[hist.axis], orientation=hist.orientation,
                                         linestyle = hist.linestyle, edgecolor=hist.linecolor,
                                color=hist.barcolor, rwidth=hist.rwidth, bins=hist.nbins)
        except:
            if len(hist.linecolor) == 1:
                hist.linecolor = hist.linecolor[0]
            data_here = ax.hist(data[hist.axis], orientation=hist.orientation,
                                         linestyle = hist.linestyle, edgecolor=hist.linecolor,
                                color=hist.barcolor, rwidth=hist.rwidth, bins=hist.nbins)

    # add in error bars
    data_heights = data_here[0] # heights of DATA values
    bin_edges = data_here[1] # bin edges of DATA values
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    errs = []
    for b in data_heights:
        if hist.es is None:
            es = rng.uniform(low=plot_params['error bars']['x']['size']['min'], 
                                        high=plot_params['error bars']['x']['size']['max'])
        errs.append(b*es)

    if hist.hasErr is None:
        hasErr = False
        if 'xerrs' in data: # different!
            if data['xerrs']:
                hasErr = True
        elif 'yerrs' in data:
            if data['yerrs']:
                hasErr = True
        hist.hasErr = hasErr

    if hist.hasErr:
        try:
            (_, caps, bars) = ax.errorbar(bin_centers,data_heights,yerr=errs,
                                            linewidth=0,elinewidth=hist.elinewidth,
                                            markersize=0, ecolor=hist.linecolor, zorder=10) # error bars on top
        except:
            if isinstance(hist.elinewidth, list) or isinstance(hist.elinewidth, np.ndarray):
                if len(hist.elinewidth) == 1:
                    hist.elinewidth = hist.elinewidth[0]
            if isinstance(hist.linecolor, list) or isinstance(hist.linecolor, np.ndarray):
                if len(hist.linecolor) == 1:
                    hist.linecolor = hist.linecolor[0]
            (_, caps, bars) = ax.errorbar(bin_centers,data_heights,yerr=errs,
                                            linewidth=0,elinewidth=hist.elinewidth,
                                            markersize=0, ecolor=hist.linecolor, zorder=10) # error bars on top
    xerr_bars = []; yerr_bars = []
    if 'xerrs' in data and hist.hasErr:
        #if len(data['xerrs']) > 0:
        if data['xerrs']: # DIFFERENT
            data['xerrs'] = errs
            #print("YES XERR")
            xerr_bars = bars
            #xerr_bars_bars = bars
    elif 'yerrs' in data and hist.hasErr:
        #if len(data['yerrs']) > 0:
        if data['yerrs']: # DIFFERENT
            #print("YES YERR")
            yerr_bars = bars
            data['yerrs'] = errs
            #yerr_bars_bars = bars

    data_out = {'data':data_here, 'plot params':{
                                            'linethick':hist.lthick, 
                                            'linestyles':hist.linestyle,
                                             'bar color':hist.barcolor,
                                             'edge color':hist.linecolor,
                                             'orientation':hist.orientation,
                                             'rwidth':hist.rwidth,
                                             'nbins':hist.nbins
                                            }
               }
    
    # add in x/y errors, if present
    if len(xerr_bars) > 0:
        data_out['x error bars'] = [xerr_bars] # list for formatting
        #data_out['x error bars plot'] = [xerr_bars_bars] # list for formatting
        data_out['plot params']['elinewidth'] = hist.elinewidth
    if len(yerr_bars) > 0:
        data_out['y error bars'] = [yerr_bars]
        #data_out['y error bars plot'] = [yerr_bars_bars]
        data_out['plot params']['elinewidth'] = hist.elinewidth
    return data_out, ax

###############################################
############## MAIN PLOT #####################
###############################################

def make_plot(plot_params, data, ax, plot_type='line', linestyles=linestyles,
              iplot=None, nrows=None, ncols=None, rng=np.random, **kwargs):#, plot_style='default'):
    if plot_type == 'line':
        data_out, ax = get_line_plot(plot_params, data, ax, linestyles=linestyles, rng=rng, **kwargs)
        return data_out, ax
    elif plot_type == 'scatter':
        data_out, ax = get_scatter_plot(plot_params, data, ax, rng=rng, **kwargs)
        return data_out, ax
    elif plot_type == 'histogram':
        data_out, ax = get_histogram_plot(plot_params, data, ax, linestyles=linestyles, rng=rng, **kwargs)
        return data_out, ax
    elif plot_type == 'contour':
        data_out, ax = get_contour_plot(plot_params, data, ax, rng=rng, **kwargs)
        return data_out, ax
    elif plot_type == 'image of the sky':
        # note here: "ax" is really "fig"
        result = get_image_of_the_sky_plot(plot_params, data, ax, 
                                                 iplot=iplot, nrows=nrows, 
                                                 ncols=ncols, rng=rng, **kwargs)
        if result is not None:
            data_out, ax = result
        else:
            data_out, ax = None, None

        return data_out, ax
    else:
        print('not implement yet!')
        import sys; sys.exit()



def colorbar_mods(cbar, side, fig):
    # axis labels slide
    bottom = False; top = False; right = False; left = False
    in_or_out = np.random.choice(['in','out'])

    # flip labels?
    if side == 'top' or side == 'bottom':
        # turn off side axis stuff
        cbar.ax.set_ylabel('')
        cbar.ax.tick_params(length=0, axis='y', labelsize=-1, color=fig.get_facecolor(), 
                            labelcolor=fig.get_facecolor())
        # mods for c-bar axis
        if side == 'bottom':
            bottom = True
        else:
            top = True
        cbar.ax.tick_params(axis='x',direction=in_or_out, 
                            labelbottom=bottom, labeltop=top, 
                            labelleft=left, labelright=right)
    else:
        # turn off bottom axis stuff
        cbar.ax.set_xlabel('')
        cbar.ax.tick_params(length=0, axis='x', labelsize=-1, color=fig.get_facecolor(), 
                            labelcolor=fig.get_facecolor())

        # mods for c-bar axis
        if side == 'left':
            left = True
        else:
            right = True
        cbar.ax.tick_params(axis='y',direction=in_or_out, 
                            labelbottom=bottom, labeltop=top, 
                            labelleft=left, labelright=right)
    return cbar



# def make_base_plot(plot_style, color_map, dpi, nrows, ncols, aspect_fig,
#                    base=5, verbose=True, tight_layout = True):
#     plt.close('all')
#     plt.style.use(plot_style)
#     plt.set_cmap(color_map) 
#     figsize = (base*ncols*aspect_fig, base*nrows) # w,h
#     if verbose: print('figsize (w,h) =', figsize)

#     if tight_layout:
#         fig = plt.figure(figsize=figsize, dpi=dpi,layout='tight')
#     else:
#         fig = plt.figure(figsize=figsize, dpi=dpi)

#     axes = []
#     plot_inds = []
#     for i in range(nrows):
#         for j in range(ncols):
#             iplot = (i*nrows) + j
#             ax = fig.add_subplot(nrows, ncols, iplot + 1)
#             axes.append(ax)
#             plot_inds.append([i,j])

#     return fig, axes, plot_inds



from .synthetic_fig_utils import get_titles_or_labels

def make_colorbar(data_from_plot, plot_type, fig, 
                  popular_nouns, inlines, colorbar_params,
                  title_params, colorbar_fontsize, csfont,
                  rng=np.random, hasLabel=None):
    cbar = None
    colorbar_words = None
    #cbar_labels = []; cbar_words = []; cbar_nums = []
    if plot_type == 'scatter': 
        if 'color bar' in data_from_plot:
            side = data_from_plot['color bar params']['side']
            if side == 'top' or side == 'bottom':
                orientation = 'horizontal'
            else:
                orientation = 'vertical'
                              
            cbar = fig.colorbar(data_from_plot['data'], 
                        cax=data_from_plot['color bar'], 
                        orientation=orientation)
            # label?
            if type(popular_nouns) != str:
                colorbar_words = get_titles_or_labels(popular_nouns, 
                                                    colorbar_params['capitalize'],
                                        colorbar_params['equation'], inlines,
                                        nwords=rng.integers(low=title_params['n words']['min'],
                                                                high=title_params['n words']['max']+1), 
                                                                rng=rng)
            else:
                colorbar_words = popular_nouns
                hasLabel = True

            if hasLabel is None and (hasLabel is not False):
                if rng.uniform() <= data_from_plot['color bar params']['label prob']: # has label
                    cbar.set_label(colorbar_words, fontsize=colorbar_fontsize, **csfont)
            elif hasLabel:
                cbar.set_label(colorbar_words, fontsize=colorbar_fontsize, **csfont)

            # fig.canvas.draw() # not sure this actually has to be here...

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
                                                         
            cbar = fig.colorbar(datac, 
                        cax=data_from_plot['color bar'], 
                        orientation=orientation)
            # label?
            if type(popular_nouns) != str:
                colorbar_words = get_titles_or_labels(popular_nouns, 
                                                    colorbar_params['capitalize'],
                                        colorbar_params['equation'], inlines,
                                        nwords=rng.integers(low=title_params['n words']['min'],
                                                                high=title_params['n words']['max']+1), 
                                                                rng=rng)
            else:
                colorbar_words = popular_nouns
                hasLabel = True

            if hasLabel is None and (hasLabel is not False):
                if rng.uniform() <= data_from_plot['color bar params']['label prob']: # has label
                    cbar.set_label(colorbar_words, fontsize=colorbar_fontsize, **csfont)
            elif hasLabel:
                cbar.set_label(colorbar_words, fontsize=colorbar_fontsize, **csfont)

            cbar = colorbar_mods(cbar, data_from_plot['color bar params']['side'], fig)

            # # save for each
            # cbar_labels.append(cbar)
            # cbar_words.append(colorbar_words)
            # if cbar is not None:
            #     cbar_nums.append(len(cbar_nums)) # save axis of this colorbar
            #     cbar_nums.append(len(cbar_nums)) # add extra for axes for colorbar
            # else:
            #     cbar_nums.append(-1)
    #fig.canvas.draw()
    return cbar, colorbar_words


            # # label?
            # #colorbar_label = None
            # if rng.uniform() <= data_from_plot['color bar params']['label prob']: # has label
            #     colorbar_words = get_titles_or_labels(popular_nouns, colorbar_params['capitalize'],
            #                             colorbar_params['equation'], inlines,
            #                             nwords=rng.integers(low=title_params['n words']['min'],
            #                                                     high=title_params['n words']['max']+1), 
            #                                                     rng=rng)
            #     cbar.set_label(colorbar_words, fontsize=colorbar_fontsize, **csfont)
                #fig.canvas.draw() # not sure this actually has to be here...

            #cbar = colorbar_mods(cbar, data_from_plot['color bar params']['side'], fig)
                # if orientation == 'horizontal':
                #     colorbar_label = cbar.ax.xaxis.label
                # else:
                #     colorbar_label = cbar.ax.yaxis.label
                # print('colorbar_label, contour:', colorbar_label)
                #import sys; sys.exit()
            #cbars.append(cbar) # do we need this here?...


    # if plot_type == 'scatter': 
    #     if 'color bar' in data_from_plot:
    #         side = data_from_plot['color bar params']['side']
    #         if side == 'top' or side == 'bottom':
    #             orientation = 'horizontal'
    #         else:
    #             orientation = 'vertical'

    #         cbar = fig.colorbar(data_from_plot['data'], 
    #                         cax=data_from_plot['color bar'], 
    #                         orientation=orientation)
    #         #cbars.append(cbar)

    # if plot_type == 'contour':
    #     if 'color bar' in data_from_plot:
    #         side = data_from_plot['color bar params']['side']
    #         if side == 'top' or side == 'bottom':
    #             orientation = 'horizontal'
    #         else:
    #             orientation = 'vertical'
    
    #         if 'image' in data_from_plot['data']: # select correct colorbar to use
    #             datac = data_from_plot['data']['image']
    #         else:
    #             datac = data_from_plot['data']['contour']
                            
    #         cbar = fig.colorbar(datac, 
    #                         cax=data_from_plot['color bar'], 
    #                         orientation=orientation)
    #         #cbars.append(cbar)
    # return cbar


def create_sky_projection(xmin, ymin, xmax, ymax, nx, ny, rng=np.random):
    CRVAL1 = xmax # RA at pixel 1 -- NOTE: RA decreases along x typically!
    CRVAL2 = ymin # DEC at pixel 1

    # deg per pixel
    CDELT1 = (xmin - xmax)/nx # should be < 0
    CDELT2 = (ymax - ymin)/ny

    # number pixels
    NAXIS1 = nx
    NAXIS2 = ny

    wcs_input_dict = {
        'CTYPE1': 'RA---TAN', 
        'CUNIT1': 'deg', 
        'CDELT1': CDELT1, #-0.0002777777778, 
        'CRPIX1': 1, 
        'CRVAL1': CRVAL1, #337.5202808, 
        'NAXIS1': NAXIS1, #1024,
        'CTYPE2': 'DEC--TAN', 
        'CUNIT2': 'deg', 
        'CDELT2': CDELT2, #0.0002777777778, 
        'CRPIX2': 1, 
        'CRVAL2': CRVAL2, #-20.833333059999998, 
        'NAXIS2': NAXIS2 #1024
    }
    wcs_helix_dict = WCS(wcs_input_dict)
    return wcs_helix_dict


# def update_projection(ax, projection='3d', fig=None):
#     if fig is None:
#         fig = plt.gcf()
#     rows, cols, start, stop = ax.get_subplotspec().get_geometry()
#     ax.remove()
#     ax = fig.add_subplot(rows, cols, start+1, projection=projection)
#     return ax

# claude suggested
import psutil
import gc
import traceback
def memory_safe_plot(max_memory_mb=4000, skip_on_excess=True):
    """Wrapper to skip plotting if memory exceeds threshold"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            process = psutil.Process()
            current_mb = process.memory_info().rss / 1024 / 1024
            
            if current_mb > max_memory_mb:
                if skip_on_excess:
                    print(f"Skipping plot - memory at {current_mb:.0f}MB")
                    gc.collect()
                    return None
                else:
                    # Try aggressive cleanup first
                    gc.collect()
                    plt.close('all')
                    current_mb = process.memory_info().rss / 1024 / 1024
                    if current_mb > max_memory_mb:
                        print(f"Still high memory ({current_mb:.0f}MB), skipping")
                        return None
            
            try:
                result = func(*args, **kwargs)
                return result
            except MemoryError:
                print(f"MemoryError in {func.__name__}, skipping")
                plt.close('all')
                gc.collect()
                return None
            except Exception as e:
                print(f"Error in {func.__name__}: {e}")
                traceback.print_exc()
                plt.close('all')
                return None
        return wrapper
    return decorator

# # Usage:
# @memory_safe_plot(max_memory_mb=3500)
# def make_plot(img_data, filename):
#     fig, ax = plt.subplots()
#     ax.imshow(img_data, interpolation='none')
#     ax.contour(img_data[::4, ::4], levels=5)
#     plt.savefig(filename)
#     plt.close(fig)
#     return filename

# # In your loop:
# for i, data in enumerate(files):
#     result = make_plot(data, f'plot_{i}.png')
#     if result is None:
#         print(f"Skipped plot {i}")
#     # Force cleanup periodically
#     if i % 10 == 0:
#         gc.collect()

from .plot_classes_utils import ImageOfSky 

@memory_safe_plot(max_memory_mb=10000)
def get_image_of_the_sky_plot(plot_params, data, fig,
                              iplot=None, nrows=None, ncols=None, 
                              rng=np.random, figdraw=True, **kwargs):
    
    imgOfSky = ImageOfSky()
    for k,v in kwargs.items():
        if k in imgOfSky.__dict__: # in there
            setattr(imgOfSky, k, v)

    if iplot == None:
        print('[ERROR]: need to specify iplot for "image of the sky" plots')
        import sys; sys.exit()
    if nrows == None:
        print('[ERROR]: need to specify nrows for "image of the sky" plots')
        import sys; sys.exit()
    if ncols == None:
        print('[ERROR]: need to specify ncols for "image of the sky" plots')
        import sys; sys.exit()

    p = rng.uniform(0,1) # probability that has a colorbar
    #pi = rng.uniform(0,1) # probability that is an image (vs a contour with lines)
    choices = []; probs = []
    for k,v in plot_params['image or contour']['prob'].items():
        choices.append(k)
        probs.append(v)
    # double check
    probs = np.array(probs).astype('float')
    probs /= np.sum(probs)
    if imgOfSky.image_or_contour is None:
        plot_type = rng.choice(choices, p=probs)
    elif imgOfSky.image_or_contour not in choices:
        plot_type = rng.choice(choices, p=probs)
    else:
        plot_type = imgOfSky.image_or_contour
    cax = []; side = ''

    ### HERE -- flag for if distribution is "sky" or "gmm"
    # create projection for GMM distributions
    real_img_of_sky = False
    if 'WCS' in data['data params']: # have "real" image of sky
        # check for saved
        wcs_helix = data['data params']['WCS']
        real_img_of_sky = True
        try:
            if 'non serializable entry' not in wcs_helix:
                # grab x/y ranges
                res_dict = plot_params['distribution']['sky']['resolution']
                # ONE factor for both axes.  Drawing xres and yres independently
                # makes the displayed sub-region a different shape from the pixel
                # grid, which stretches every bin on screen (measured up to 1.3x).
                xres = rng.uniform(low=res_dict['min'], high=res_dict['max'])
                yres = xres
                dx = int(round(data['data params']['sky image params']['original img size'][1]*(1-xres)/2.))
                dy = int(round(data['data params']['sky image params']['original img size'][0]*(1-yres)/2.))
                dx = max(0,dx); dy = max(0,dy)
            else: # is a saved WCS
                wcs_helix = WCS(data['data params']['WCS header string'])
                # calc from here
                # real_x = data['data']['xs']
                # real_y = data['data']['ys']
                real_x = data['xs']
                real_y = data['ys']
                dx = (real_x[1]-real_x[0])/2.
                dy = (real_y[1]-real_y[0])/2.
        except Exception as esky:
            if "'WCS' is not iterable" in str(esky): # assume wcs
                # grab x/y ranges
                res_dict = plot_params['distribution']['sky']['resolution']
                # ONE factor for both axes.  Drawing xres and yres independently
                # makes the displayed sub-region a different shape from the pixel
                # grid, which stretches every bin on screen (measured up to 1.3x).
                xres = rng.uniform(low=res_dict['min'], high=res_dict['max'])
                yres = xres
                dx = int(round(data['data params']['sky image params']['original img size'][1]*(1-xres)/2.))
                dy = int(round(data['data params']['sky image params']['original img size'][0]*(1-yres)/2.))
                dx = max(0,dx); dy = max(0,dy)
            else:
                print('NOOOOO IDEA')
                lsfjaslkj

        xrange_plot = (dx,data['data params']['sky image params']['original img size'][1]-dx)
        yrange_plot = (dy,data['data params']['sky image params']['original img size'][0]-dy)
    else:
        wcs_helix = create_sky_projection(np.array(data['xs']).min(), 
                                          np.array(data['ys']).min(), 
                                      np.array(data['xs']).max(), 
                                      np.array(data['ys']).max(), 
                                      len(data['xs']), len(data['ys']))
    
    # create ax with this projection
    ax = fig.add_subplot(nrows, ncols, iplot + 1, projection=wcs_helix)
    # get renorm function
    #norm = data['data params']['norm function']

    # Guard against zero/near-zero size arrays that cause segfaults in image_resample
    _colors = np.asarray(data['colors'])
    if _colors.ndim < 2 or _colors.shape[0] < 2 or _colors.shape[1] < 2:
        raise ValueError(f'image data too small for sky plot: shape={_colors.shape}')
    _bbox = ax.get_position()
    if _bbox.width < 1e-3 or _bbox.height < 1e-3:
        raise ValueError(f'axes too small for sky plot: {_bbox.width:.4f} x {_bbox.height:.4f}')

    if plot_type == 'contour':
        nlevels = int(round(rng.uniform(low=plot_params['nlines']['min'],
                                              high=plot_params['nlines']['max'])))
        #ax = update_projection(ax, projection=wcs_helix)
        data_here2 = ax.contour(data['xs'], data['ys'], data['colors'], nlevels)
        if real_img_of_sky:
            ax.set_xlim(xrange_plot)
            ax.set_ylim(yrange_plot)
        data_here = {'contour':data_here2}
    elif plot_type == 'image':
        real_x = data['xs']
        real_y = data['ys']
        dx = (real_x[1]-real_x[0])/2.
        dy = (real_y[1]-real_y[0])/2.
        #extent = [real_x[0]-dx, real_x[-1]+dx, real_y[0]-dy, real_y[-1]+dy]
        #plt.imshow(data, extent=extent)
        #ax = update_projection(ax, projection=wcs_helix)
        data_here1 = ax.imshow(np.ascontiguousarray(data['colors']), interpolation='none')#, norm=norm) #, extent=extent)
        if real_img_of_sky:
            ax.set_xlim(xrange_plot)
            ax.set_ylim(yrange_plot)
        data_here = {'image':data_here1}
    elif plot_type == 'both':
        pg = rng.uniform(0,1)
        grayContours = False
        if pg <= plot_params['image or contour']['both contours']['prob gray']: # probability that contours are gray for "both" situation
            grayContours = True
        cmap = rng.choice(['gray', 'gray_r'])
        real_x = data['xs']
        real_y = data['ys']
        dx = (real_x[1]-real_x[0])/2.
        dy = (real_y[1]-real_y[0])/2.
        #extent = [real_x[0]-dx, real_x[-1]+dx, real_y[0]-dy, real_y[-1]+dy]
        #ax = update_projection(ax, projection=wcs_helix)
        data_here1 = ax.imshow(np.ascontiguousarray(data['colors']), interpolation='none')#, norm=norm)#, extent=extent)
        nlevels = int(round(rng.uniform(low=plot_params['nlines']['min'],
                                              high=plot_params['nlines']['max'])))
        if not grayContours:
            data_here2 = ax.contour(data['xs'], data['ys'], data['colors'], nlevels)
        else:
            data_here2 = ax.contour(data['xs'], data['ys'], data['colors'], nlevels,
                                   cmap=cmap)
        if real_img_of_sky:
            ax.set_xlim(xrange_plot)
            ax.set_ylim(yrange_plot)

        data_here = {'image':data_here1, 'contour':data_here2}
    else:
        print('not supported plot type!')
        import sys; sys.exit()

    if not p <= plot_params['colormap contour']['prob']: # not have color map
        pass 
    else:
        divider = make_axes_locatable(ax)
        #print('divider:', divider)

        # get probs
        probs = []; choices = []
        for k,v in plot_params['color bar']['location probs'].items():
            probs.append(v); choices.append(k)
        if imgOfSky.colorbar_side is None:
            side = rng.choice(choices, p=probs)
        else:
            side = imgOfSky.colorbar_side
        if imgOfSky.colorbar_size is None:  
            size = rng.uniform(low=plot_params['color bar']['size percent']['min'], 
                     high=plot_params['color bar']['size percent']['max'])
            size = str(int(round(size*100)))+'%'
        else:
            size = imgOfSky.colorbar_size
        if imgOfSky.colorbar_pad is None:
            pad = rng.uniform(low=plot_params['color bar']['pad']['min'], 
                                 high=plot_params['color bar']['pad']['max'])
        else:
            pad = imgOfSky.colorbar_pad
        
        #print('side, size, pad', side, size, pad)

        cax = divider.append_axes(side, size=size, pad=pad)
        # the side of the axis
        if side == 'right': # this maybe should become a random selection?
            axis_side = 'right'
            cax.yaxis.set_ticks_position(axis_side)
        elif side == 'left':
            axis_side = 'left'
            cax.yaxis.set_ticks_position(axis_side)
        elif side == 'top':
            axis_side = 'top'
            cax.xaxis.set_ticks_position(axis_side)
        elif side == 'bottom':
            axis_side = 'bottom'
            cax.xaxis.set_ticks_position(axis_side)
    import warnings as _warnings
    with _warnings.catch_warnings():
        _warnings.filterwarnings("ignore", message="Tight layout not applied")
        plt.draw()
    #print('DRAW WAS CALLED 3')
    #if figdraw: fig.canvas.draw()

    xerrs = []; yerrs = []
        
    # save data
    if cax != []:
        data_out = {'data':data_here, 'color bar':cax, 
                    'color bar params':{'side':side, 'pad':pad, 'size':size, 
                                       'axis side':axis_side,
                                       'label prob': plot_params['color bar']['label prob']
                        } 
                                       #'marker':marker, 'marker size':marker_size}
                   }
    else:
        data_out = {'data':data_here}

    # save x/y limits if real image of sky
    if real_img_of_sky:
        data_out['x pixel limits'] = xrange_plot
        data_out['y pixel limits'] = yrange_plot

    # add in x/y errors, if present
    if 'xerrs' in data:
        data_out['x error bars'] = xerrs
    if 'yerrs' in data:
        #print("YESS TO Y IN DATA")
        data_out['y error bars'] = yerrs
    # if 'xerrs' in data or 'yerrs' in data:
    #     data_out['error bar params']:{'elinewidth':elinewidth}
    
    return data_out, ax

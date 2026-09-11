import numpy as np
import cv2 as cv

def log_scale_ax(scale_exp = {'min':0.01, 'max':5.0}, 
                 scale_factor = {'min':0.1, 'max':10}, 
                 npoints=1,
                 verbose=False):
    """
    npoints : how many objects do we want?  only 1 is implemented right now
    """
    if npoints != 1:
        print('only npoints=1 is implemented!')
        import sys; sys.exit()
    scale_input = np.random.uniform(low=scale_exp['min'], high=scale_exp['max'])
    n = np.random.exponential(scale_input)
    scale = 10**n
    scale_factor_low = np.random.uniform(low=scale_factor['min'], high=scale_factor['max'])
    xmin = scale - scale_factor_low*scale
    scale_factor_high = np.random.uniform(low=scale_factor['min'], high=scale_factor['max'])
    xmax = scale + scale_factor_high*scale
    if verbose: print(scale_input, n, scale, xmin,xmax)
    return xmin,xmax


# claude
def remap_box(box, old_canvas, new_canvas):
    """
    Remap a box from old canvas coordinates to new canvas coordinates.
    
    Parameters
    ----------
    box : tuple
        (xmin, ymin, xmax, ymax) in old canvas coordinates
    old_canvas : tuple
        (xmin, ymin, xmax, ymax) of the old canvas
    new_canvas : tuple
        (xmin, ymin, xmax, ymax) of the new canvas
    
    Returns
    -------
    tuple
        New (xmin, ymin, xmax, ymax) in new canvas coordinates
    """
    xmin, ymin, xmax, ymax = box
    old_xmin, old_ymin, old_xmax, old_ymax = old_canvas
    new_xmin, new_ymin, new_xmax, new_ymax = new_canvas
    
    # Get old canvas dimensions
    old_width = old_xmax - old_xmin
    old_height = old_ymax - old_ymin
    
    # Get new canvas dimensions
    new_width = new_xmax - new_xmin
    new_height = new_ymax - new_ymin
    
    # Convert box to normalized coordinates [0, 1]
    norm_xmin = (xmin - old_xmin) / old_width
    norm_ymin = (ymin - old_ymin) / old_height
    norm_xmax = (xmax - old_xmin) / old_width
    norm_ymax = (ymax - old_ymin) / old_height
    
    # Map to new canvas
    new_box_xmin = new_xmin + norm_xmin * new_width
    new_box_ymin = new_ymin + norm_ymin * new_height
    new_box_xmax = new_xmin + norm_xmax * new_width
    new_box_ymax = new_ymin + norm_ymax * new_height
    
    return (new_box_xmin, new_box_ymin, new_box_xmax, new_box_ymax)


def remap_point(point, old_canvas, new_canvas):
    """
    Remap a point from old canvas coordinates to new canvas coordinates.
    
    Parameters
    ----------
    point : tuple
        (x, y) in old canvas coordinates
    old_canvas : tuple
        (xmin, ymin, xmax, ymax) of the old canvas
    new_canvas : tuple
        (xmin, ymin, xmax, ymax) of the new canvas
    
    Returns
    -------
    tuple
        New (x, y) in new canvas coordinates
    """
    x, y = point
    old_xmin, old_ymin, old_xmax, old_ymax = old_canvas
    new_xmin, new_ymin, new_xmax, new_ymax = new_canvas
    
    # Get canvas dimensions
    old_width = old_xmax - old_xmin
    old_height = old_ymax - old_ymin
    new_width = new_xmax - new_xmin
    new_height = new_ymax - new_ymin
    
    # Normalize to [0, 1]
    norm_x = (x - old_xmin) / old_width
    norm_y = (y - old_ymin) / old_height
    
    # Map to new canvas
    new_x = new_xmin + norm_x * new_width
    new_y = new_ymin + norm_y * new_height
    
    return (new_x, new_y)

    #   d = v['square']
    #   xmin,ymin = int(d['xmin']),int(img.shape[0]-d['ymin'])
    #   xmax,ymax = int(d['xmax']),int(img.shape[0]-d['ymax'])


def rescale_xymin(d, img_shape, new_canvas = None, new_img_shape=None,
        no_subtract = False, roundit=False, add_canvas_delta=True):
    if new_img_shape is None:
        new_img_shape = img_shape
    """
    new_canvas : (xmin,ymin,xmax,ymax)
    """
    # translate to new place
    xmin,ymin = d['xmin'],d['ymin']
    xmax,ymax = d['xmax'],d['ymax'] 
    # flip   
    #xmin,ymin = d['xmin'],d['ymax']
    #xmax,ymax = d['xmax'],d['ymin'] 
    # if not no_subtract:
    #     ymin = img_shape[0]-d['ymin']
    #     ymax = img_shape[0]-d['ymax']
    if new_canvas is not None:
        old_canvas = (0,0,img_shape[1],img_shape[0])
        xmin,ymin,xmax,ymax = remap_box((xmin,ymin,xmax,ymax), 
            old_canvas, new_canvas) 
        # add canvas delta back in
        if add_canvas_delta:
            delta = new_canvas[-1]-img_shape[0]
            ymax -= delta
            ymin -= delta
    if not no_subtract:
        # ymin = img_shape[0]-d['ymin']
        # ymax = img_shape[0]-d['ymax']        
        ymin = new_img_shape[0]-ymin
        ymax = new_img_shape[0]-ymax
    if roundit:
        xmin,ymin = int(round(xmin)),int(round(ymin))
        xmax,ymax = int(round(xmax)),int(round(ymax))                        
    return xmin,ymin,xmax,ymax
    # flip
    #return xmin,ymax,xmax,ymin

def translate_xsys(xs,ys, img_shape, new_canvas=None, no_subtract=False):
    if not no_subtract:
        ys = img_shape[0]-ys
    if new_canvas is not None:
        old_canvas = (0,0,img_shape[1],img_shape[0])
        xs,ys = remap_point((xs,ys), old_canvas, new_canvas)
    xs,ys = int(round(xs)),int(round(ys))
    return xs,ys


def plot_color_bar(v,img,imgplot, color=(255,0,0), lthick=3, verbose=True, xmin_all=0, ymin_all=0, csize=5, 
                new_canvas=None):
    # format
    xmin_all = int(round(xmin_all))
    ymin_all = int(round(ymin_all))
    # colormap
    # xmin,ymin = int(round(v['color bar']['xmin'])), int(round(img.shape[0]-v['color bar']['ymin']))
    # xmax,ymax = int(round(v['color bar']['xmax'])), int(round(img.shape[0]-v['color bar']['ymax']))
    xmin,ymin,xmax,ymax = rescale_xymin(v['color bar'], img.shape, new_canvas = new_canvas, roundit=True)
    #print(xmin,ymin,xmax,ymax, xmin_all,ymin_all)
    cv.rectangle(imgplot, (xmin+xmin_all,ymin+ymin_all), (xmax+xmin_all,ymax+ymin_all), color, lthick)
    # colormap ticks
    if 'color bar ticks' in v:
        for d in v['color bar ticks']:
            #xmin,ymin,xmax,ymax = int(d['xmin']),int(img.shape[0]-d['ymin']),int(d['xmax']),int(img.shape[0]-d['ymax'])
            xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape, new_canvas = new_canvas, roundit=True)
            # check if we should have it or not
            xs,ys = translate_xsys(d['tx'],d['ty'], img.shape, new_canvas=new_canvas)#,roundit=True)
            if v['color bar']['params']['side'] == 'bottom' or v['color bar']['params']['side'] == 'top':
                if d['tx']>=v['color bar']['xmin'] and d['tx']<=v['color bar']['xmax']:
                    cv.rectangle(imgplot, (xmin+xmin_all,ymin+ymin_all), (xmax+xmin_all,ymax+ymin_all), color, lthick)
                    #cv.circle(imgplot, (int(d['tx'])+xmin_all, int(img.shape[0]-d['ty'])+ymin_all), csize, color, -1)
                    cv.circle(imgplot, (xs+xmin_all, ys+ymin_all), csize, color, -1)
            else: # side
                if d['ty']>=v['color bar']['ymin'] and d['ty']<=v['color bar']['ymax']:
                    cv.rectangle(imgplot, (xmin+xmin_all,ymin+ymin_all), (xmax+xmin_all,ymax+ymin_all), color, lthick)
                    #cv.circle(imgplot, (int(d['tx'])+xmin_all, int(img.shape[0]-d['ty'])+ymin_all), csize, color, -1)
                    cv.circle(imgplot, (xs+xmin_all, ys+ymin_all), csize, color, -1)
    # check for label
    if 'label' in v['color bar']:
        # xmin = int(round(v['color bar']['label']['xmin']))
        # xmax = int(round(v['color bar']['label']['xmax']))
        # ymin = img.shape[0]-int(round(v['color bar']['label']['ymin']))
        # ymax = img.shape[0]-int(round(v['color bar']['label']['ymax']))
        xmin,ymin,xmax,ymax = rescale_xymin(v['color bar']['label'], img.shape, new_canvas = new_canvas,roundit=True)
        #ymin = int(round(v['color bar']['label']['ymin']))
        #ymax = int(round(v['color bar']['label']['ymax']))
        cv.rectangle(imgplot, (xmin+xmin_all,ymin+ymin_all), (xmax+xmin_all,ymax+ymin_all), color, lthick)
        # print("I AM IN PLOT COLOR BAR")
        # print(xmin,ymin,xmax,ymax)
    # check for offset text
    if 'offset text' in v['color bar']:
        # xmin = int(round(v['color bar']['offset text']['xmin']))
        # xmax = int(round(v['color bar']['offset text']['xmax']))
        # ymin = img.shape[0]-int(round(v['color bar']['offset text']['ymin']))
        # ymax = img.shape[0]-int(round(v['color bar']['offset text']['ymax']))
        xmin,ymin,xmax,ymax = rescale_xymin(v['color bar']['offset text'], img.shape, new_canvas = new_canvas, roundit=True)        
        cv.rectangle(imgplot, (xmin+xmin_all,ymin+ymin_all), (xmax+xmin_all,ymax+ymin_all), color, lthick)
    return imgplot

# # claude
# def rescale_translate_box(box, new_center, scale_x=1.0, scale_y=1.0):
#     """
#     Rescale and translate a bounding box.
    
#     Parameters
#     ----------
#     box : tuple
#         (xmin, ymin, xmax, ymax)
#     new_center : tuple
#         (center_x, center_y) for the rescaled box
#     scale_x : float
#         Scale factor for width (default 1.0)
#     scale_y : float
#         Scale factor for height (default 1.0)
    
#     Returns
#     -------
#     tuple
#         New (xmin, ymin, xmax, ymax)
#     """
#     xmin, ymin, xmax, ymax = box
    
#     # Get current dimensions
#     width = xmax - xmin
#     height = ymax - ymin
    
#     # Apply scaling
#     new_width = width * scale_x
#     new_height = height * scale_y
    
#     # Center around new_center
#     cx, cy = new_center
#     new_xmin = cx - new_width / 2
#     new_xmax = cx + new_width / 2
#     new_ymin = cy - new_height / 2
#     new_ymax = cy + new_height / 2
    
#     return (new_xmin, new_ymin, new_xmax, new_ymax)





from copy import deepcopy
def add_annotations_v1(imgplot, datas_plot, verbose = True, csize = 5, img = None,
                    color_annotations = [(255,0,0),(255,0,125),(0,255,0),(0,255,255)], 
                    fill_blocks = False, linethick=3, fraction_tick = 0.1, 
                    flip_ycoord = True):
    """
    imgplot : image to plot on
    img : orig image (if None, just a copy)

    linethick : thickness of lines
    
    fill_blocks : if true, fill in everything with a color

    fraction_tick : if not None, then looks for ticks within a range after squares (default None for images of the sky)

    new_canvas : (xmin,ymin,xmax,ymax) of new canvas to place image in

    returns : image with annotations plotted in "color_annotations", or other colors
    """
    if img is None:
        img = deepcopy(imgplot)
    # checks
    if color_annotations is None or len(color_annotations) == 0:
        color_annotations = [(255,0,0)]
    while len(color_annotations) < 4:
        csave = deepcopy(color_annotations[-1])
        color_annotations.append( csave )

    color1 = color_annotations[0]
    color2 = color_annotations[1]
    color3 = color_annotations[2]
    color4 = color_annotations[3]

    facecolor = datas_plot['figure']['facecolor']

    iplot_count = 0
    for p,v in datas_plot.items():
        iplot_count += 1
        if 'plot' in p: # not figure stuffs... just yet
            out_string = ' ------ Plot #' + str(p.split('plot')[-1]) + ' ------ \n'
            out_string += 'Plot type:' + v['type'] + '\n'
            out_string += 'Distribution:' + v['distribution'] + '\n'
            if 'data params' in v['data']:
                if 'nclusters' in v['data']['data params']:
                    out_string += '  n_clusters = ' + str(v['data']['data params']['nclusters']) + '\n'
                if 'm1' in v['data']['data params']:
                    out_string += 'm_1 * x + b_1: m_1 & b_1 = ' + str(v['data']['data params']['m1']) + \
                      ' & ' + str(v['data']['data params']['a1']) + '\n'
                if 'm2' in v['data']['data params']:
                    out_string += 'm_2 * y + b_2: m_2 & b_2 = ' + str(v['data']['data params']['m2']) + \
                      ' & ' + str(v['data']['data params']['a2']) + '\n'
                if 'm' in v['data']['data params'] and 'a' in v['data']['data params']:
                    out_string += 'm * x + b: m & b = ' + str(v['data']['data params']['m']) + \
                      ' & ' + str(v['data']['data params']['a']) + '\n'
            if verbose: print(out_string)
            
            # square
            #print(v)
            d = v['square']
            # print('here square:',d)
            # print('here img shape:', img.shape)
            if flip_ycoord:
                xmin,ymin = int(d['xmin']),int(img.shape[0]-d['ymin'])
                xmax,ymax = int(d['xmax']),int(img.shape[0]-d['ymax'])
            else:
                xmin,ymin = int(d['xmin']),int(img.shape[0]-d['ymin'])
                xmax,ymax = int(d['xmax']),int(img.shape[0]-d['ymax'])
            #print('xmin,ymin,xmax,ymax:', xmin,ymin,xmax,ymax)
            #xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape, new_canvas = new_canvas)
            if fill_blocks:
                cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, -1)
            else:
                cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, linethick)
            # title bounding box
            if 'title' in v: # has a title?
                d = v['title']
                xmin,ymin = int(d['xmin']),int(img.shape[0]-d['ymin'])
                xmax,ymax = int(d['xmax']),int(img.shape[0]-d['ymax'])
                #xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape, new_canvas = new_canvas)
                if fill_blocks:
                    cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, -1)
                else:
                    cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, linethick)
            # xlabel bounding box
            d = v['xlabel']
            xmin,ymin = int(d['xmin']),int(img.shape[0]-d['ymin'])
            xmax,ymax = int(d['xmax']),int(img.shape[0]-d['ymax'])
            #xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape, new_canvas = new_canvas)
            if fill_blocks:
                cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, -1)
            else:
                cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, linethick)
            # ylabel bounding box
            d = v['ylabel']
            xmin,ymin = int(d['xmin']),int(img.shape[0]-d['ymin'])
            xmax,ymax = int(d['xmax']),int(img.shape[0]-d['ymax'])
            #xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape, new_canvas = new_canvas)
            if fill_blocks:
                cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, -1)
            else:
                cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, linethick)
    
            #print('PLOT:', p)
            if v['type'] == 'line':
                xs = v['data pixels']['xs']
                ys = v['data pixels']['ys']
                for xx,yy in zip(xs,ys):
                    for x,y in zip(xx,yy):
                        #x,y = translate_xsys(x,y, img.shape, new_canvas=new_canvas, no_subtract = True)
                        cv.circle(imgplot, (int(x), int(y)), csize, color1, -1)
                        #cv.circle(imgplot, (x, y), csize, color1, -1)
            elif v['type'] == 'scatter':
                xs = v['data pixels']['xs']
                ys = v['data pixels']['ys']
                for x,y in zip(xs,ys):
                    #x,y = translate_xsys(x,y, img.shape, new_canvas=new_canvas, no_subtract = True)
                    cv.circle(imgplot, (int(x), int(y)), csize, color1, -1)
                    #cv.circle(imgplot, (x,y), csize, color1, -1)
                # colorbar
                if 'color bar' in v:
                    imgplot = plot_color_bar(v,img,imgplot, lthick=linethick, csize=csize)#, new_canvas=new_canvas)
            elif v['type'] == 'histogram':
                # middle of bar
                xs = np.array(v['data pixels']['xs'])
                ys = np.array(v['data pixels']['ys'])
                for x,y in zip(xs,ys): # middle
                    #x,y = translate_xsys(x,y, img.shape, new_canvas=new_canvas, no_subtract = True)                    
                    cv.circle(imgplot, (int(x), int(y)), csize, color1, -1)
                    #cv.circle(imgplot, (x,y), csize, color1, -1)
                # right
                xsr = np.array(v['data pixels']['xs_right'])
                ysr = np.array(v['data pixels']['ys_right'])
                for x,y in zip(xsr,ysr): # right
                    #x,y = translate_xsys(x,y, img.shape, new_canvas=new_canvas, no_subtract = True)                    
                    cv.circle(imgplot, (int(x), int(y)), csize, color1, -1)
                    #cv.circle(imgplot, (x,y), csize, color1, -1)
                # left
                xsl = np.array(v['data pixels']['xs_left'])
                ysl = np.array(v['data pixels']['ys_left'])
                for x,y in zip(xsl,ysl): # left
                    #x,y = translate_xsys(x,y, img.shape, new_canvas=new_canvas, no_subtract = True)                    
                    cv.circle(imgplot, (int(x), int(y)), csize, color2, -1)
                    #cv.circle(imgplot, (x,y), csize, color2, -1)
            elif v['type'] == 'contour':
                if v['data pixels']['image'] != {}:
                    xs = v['data pixels']['image']['xsc']
                    ys = v['data pixels']['image']['ysc']
                    for x,y in zip(xs,ys):
                        #x,y = translate_xsys(x,y, img.shape, new_canvas=new_canvas, no_subtract = True)                    
                        cv.circle(imgplot, (int(x), int(y)), csize, color3, -1)
                        #cv.circle(imgplot, (x,y), csize, color3, -1)
                if v['data pixels']['contour'] != {}:
                    xs = v['data pixels']['contour']['xs']
                    ys = v['data pixels']['contour']['ys']
                    for x,y in zip(xs,ys):
                        #x,y = translate_xsys(x,y, img.shape, new_canvas=new_canvas, no_subtract = True)                    
                        cv.circle(imgplot, (int(x), int(y)), csize, color4, -1)
                        #cv.circle(imgplot, (x,y), csize, color4, -1)
                if 'color bar' in v:
                    imgplot = plot_color_bar(v,img,imgplot, lthick=linethick, csize=csize)#, new_canvas=new_canvas)
            elif v['type'] == 'image of the sky':
                # get mods
                if 'sky image params' in v['data']['data params']:
                    ymod = v['data']['data params']['sky image params']['original img size'][1]
                    xmod = v['data']['data params']['sky image params']['original img size'][0]
                    #xmod, ymod = translate_xsys(xmod,ymod, img.shape, new_canvas=new_canvas, no_subtract = True) 
                    mx = 1 # should this be 1 or 0?
                if v['data pixels']['image'] != {}:
                    xs = v['data pixels']['image']['xsc']
                    ys = v['data pixels']['image']['ysc']
                    if 'x pixel limits' not in v['data from plot']: # no limits
                        for ixy,(x,y) in enumerate(zip(xs,ys)):
                            #x,y = translate_xsys(x,y, img.shape, new_canvas=new_canvas, no_subtract = True)                    
                            cv.circle(imgplot, (int(x), int(y)), csize, color3, -1)
                            #cv.circle(imgplot, (x,y), csize, color3, -1)
                    else:
                        for ixy,(x,y) in enumerate(zip(xs,ys)):
                            # check limits
                            # JPN -- not sure about the -1!
                            if (ixy-mx)//xmod > v['data from plot']['x pixel limits'][0] and \
                                (ixy-mx)//xmod < v['data from plot']['x pixel limits'][1] and \
                                    ixy%ymod > v['data from plot']['y pixel limits'][0] and \
                                        ixy%ymod < v['data from plot']['y pixel limits'][1]:
                                #x,y = translate_xsys(x,y, img.shape, new_canvas=new_canvas, no_subtract = True)                    
                                cv.circle(imgplot, (int(x), int(y)), csize, color3, -1)                                
                                #cv.circle(imgplot, (x,y), csize, color3, -1)                                
                if v['data pixels']['contour'] != {}:
                    xs = v['data pixels']['contour']['xs']
                    ys = v['data pixels']['contour']['ys']
                    if 'x pixel limits' not in v['data from plot']: # no limits
                        for x,y in zip(xs,ys):
                            #x,y = translate_xsys(x,y, img.shape, new_canvas=new_canvas, no_subtract = True)                    
                            cv.circle(imgplot, (int(x), int(y)), csize, color4, -1)
                            #cv.circle(imgplot, (x,y), csize, color4, -1)
                    else:
                        for ixy,(x,y) in enumerate(zip(xs,ys)):
                            # check limits
                            # JPN -- not sure about the -1!
                            if (ixy-mx)//xmod > v['data from plot']['x pixel limits'][0] and \
                                (ixy-mx)//xmod < v['data from plot']['x pixel limits'][1] and \
                                    ixy%ymod > v['data from plot']['y pixel limits'][0] and \
                                        ixy%ymod < v['data from plot']['y pixel limits'][1]:
                                #x,y = translate_xsys(x,y, img.shape, new_canvas=new_canvas, no_subtract = True)                    
                                cv.circle(imgplot, (int(x), int(y)), csize, color4, -1)    
                                #cv.circle(imgplot, (x,y), csize, color4, -1)    
                if 'color bar' in v:
                    imgplot = plot_color_bar(v,img,imgplot, lthick=linethick, csize=csize)#,new_canvas=new_canvas, no_subtract = True)                
            else:
                print('no idea how to deal with this plot type! Plot type = ', v['type'])
                import sys; sys.exit()
    
            # these are things for every plot
            # get dx
            if fraction_tick is not None and v['type'] != 'image of the sky':
                xts = []
                for d in v['xticks']:
                    xts.append(d['tx'])
                dx = np.mean((np.roll(xts,-1)-np.array(xts))[:-1])*fraction_tick
                if verbose:
                    print(' -- with fraction_tick =', fraction_tick, 
                        ', dx =', dx)
            else:
                dx = 0.0
            for d in v['xticks']: # draw x-ticks
                #xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape, new_canvas = new_canvas)
                xmin,ymin,xmax,ymax = int(d['xmin']),int(img.shape[0]-d['ymin']),int(d['xmax']),int(img.shape[0]-d['ymax'])
                if d['tx']+dx>=v['square']['xmin'] and d['tx']-dx<=v['square']['xmax']:
                    if fill_blocks:
                        cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, -1)
                    else:
                        cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, linethick)
                # also ticks
                if d['tx']>=v['square']['xmin']-dx and d['tx']<=v['square']['xmax']+dx:
                    #x,y = translate_xsys(d['tx'],d['ty'], img.shape, new_canvas=new_canvas)                    
                    cv.circle(imgplot, (int(d['tx']), int(img.shape[0]-d['ty'])), csize, color1, -1)
                    #cv.circle(imgplot, (x,y), csize, color1, -1)
            # get dy
            if fraction_tick is not None and v['type'] != 'image of the sky':
                yts = []
                for d in v['yticks']:
                    yts.append(d['ty'])
                dy = np.mean((np.roll(yts,-1)-np.array(yts))[:-1])*fraction_tick
                if verbose:
                    print(' -- with fraction_tick =', fraction_tick, 
                        ', dy =', dy)
            else:
                dy = 0.0
            for d in v['yticks']: # draw y-ticks
                xmin,ymin,xmax,ymax = int(d['xmin']),int(img.shape[0]-d['ymin']),int(d['xmax']),int(img.shape[0]-d['ymax'])
                #xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape, new_canvas = new_canvas)
                if d['ty']+dy>=v['square']['ymin'] and d['ty']-dy<=v['square']['ymax']:
                    if fill_blocks:
                        cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, -1)
                    else:
                        cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, linethick)
                if d['ty']>=v['square']['ymin']-dy and d['ty']<=v['square']['ymax']+dy:
                    #x,y = translate_xsys(d['tx'],d['ty'], img.shape, new_canvas=new_canvas)                    
                    cv.circle(imgplot, (int(d['tx']), int(img.shape[0]-d['ty'])), csize, color1, -1)
                    #cv.circle(imgplot, (x,y), csize, color1, -1)
            # any offset labels?
            for t in ['x','y']:
                if t + '-offset text' in v:
                    xmin = int(round(v[t + '-offset text']['xmin']))
                    ymin = img.shape[0]-int(round(v[t + '-offset text']['ymin']))
                    xmax = int(round(v[t + '-offset text']['xmax']))
                    ymax = img.shape[0]-int(round(v[t + '-offset text']['ymax']))
                    #xmin,ymin,xmax,ymax = rescale_xymin(v[t + '-offset text'], img.shape, new_canvas = new_canvas)
                    if fill_blocks:
                        cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, -1)
                    else:
                        cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, linethick)

            if v['type'] == 'line':
                if 'x error bars' in v['data pixels']:
                    for il,l in enumerate(v['data pixels']['x error bars']):
                        for ie,(xmin,ymin,xmax,ymax) in enumerate(l):
                            xmin,ymin = int(round(xmin)),int(round(img.shape[0]-ymin))
                            xmax,ymax = int(round(xmax)),int(round(img.shape[0]-ymax))
                            # only take parts within square
                            xmin = max(xmin,int(round(v['square']['xmin'])))
                            xmax = min(xmax,int(round(v['square']['xmax'])))
                            ymin = max(ymin,int(round(img.shape[0]-v['square']['ymax'])))
                            ymax = min(ymax,int(round(img.shape[0]-v['square']['ymin'])))
                            #d = {'xmin':xmin,'ymin':ymin+img.shape[0], 'xmax':xmax, 'ymax':ymax+img.shape[0]}
                            #xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape, new_canvas = new_canvas)
                            cv.line(imgplot, (xmin,ymin),(xmax,ymax), color1, 2)
                if 'y error bars' in v['data pixels']:
                    for l in v['data pixels']['y error bars']:
                        for xmin,ymin,xmax,ymax in l:
                            xmin,ymin = int(round(xmin)),int(round(img.shape[0]-ymin))
                            xmax,ymax = int(round(xmax)),int(round(img.shape[0]-ymax))
                            # only take parts within square
                            xmin = max(xmin,int(round(v['square']['xmin'])))
                            xmax = min(xmax,int(round(v['square']['xmax'])))
                            ymin = max(ymin,int(round(img.shape[0]-v['square']['ymax'])))
                            ymax = min(ymax,int(round(img.shape[0]-v['square']['ymin'])))
                            #d = {'xmin':xmin,'ymin':ymin+img.shape[0], 'xmax':xmax, 'ymax':ymax+img.shape[0]}
                            #xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape, new_canvas = new_canvas)
                            cv.line(imgplot, (xmin,ymin),(xmax,ymax), color1, 2)
            elif v['type'] == 'scatter' or v['type'] == 'histogram':
                if 'x error bars' in v['data pixels']:
                    for xmin,ymin,xmax,ymax in v['data pixels']['x error bars']:
                        xmin,ymin = int(round(xmin)),int(round(img.shape[0]-ymin))
                        xmax,ymax = int(round(xmax)),int(round(img.shape[0]-ymax))
                        # only take parts within square
                        xmin = max(xmin,int(round(v['square']['xmin'])))
                        xmax = min(xmax,int(round(v['square']['xmax'])))
                        ymin = max(ymin,int(round(img.shape[0]-v['square']['ymax'])))
                        ymax = min(ymax,int(round(img.shape[0]-v['square']['ymin'])))
                        #d = {'xmin':xmin,'ymin':ymin+img.shape[0], 'xmax':xmax, 'ymax':ymax+img.shape[0]}
                        #xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape, new_canvas = new_canvas)
                        cv.line(imgplot, (xmin,ymin),(xmax,ymax), color1, 2)
                if 'y error bars' in v['data pixels']:
                    for xmin,ymin,xmax,ymax in v['data pixels']['y error bars']:
                        #print(ymin,ymax)
                        xmin,ymin = int(round(xmin)),int(round(img.shape[0]-ymin))
                        xmax,ymax = int(round(xmax)),int(round(img.shape[0]-ymax))
                        xmin = max(xmin,int(round(v['square']['xmin'])))
                        xmax = min(xmax,int(round(v['square']['xmax'])))
                        ymin = max(ymin,int(round(img.shape[0]-v['square']['ymax'])))
                        ymax = min(ymax,int(round(img.shape[0]-v['square']['ymin'])))
                        #d = {'xmin':xmin,'ymin':ymin+img.shape[0], 'xmax':xmax, 'ymax':ymax+img.shape[0]}
                        #xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape, new_canvas = new_canvas)
                        cv.line(imgplot, (xmin,ymin),(xmax,ymax), color1, 2)

    return imgplot


def add_annotations_OLD(imgplot, datas_plot, verbose = True, csize = 5, img = None,
                    color_annotations = [(255,0,0),(255,0,125),(0,255,0),(0,255,255)], 
                    fill_blocks = False, linethick=3, fraction_tick = 0.1,
                    new_canvas = None):
    """
    imgplot : image to plot on
    img : orig image (if None, just a copy)

    linethick : thickness of lines
    
    fill_blocks : if true, fill in everything with a color

    fraction_tick : if not None, then looks for ticks within a range after squares (default None for images of the sky)

    new_canvas : (xmin,ymin,xmax,ymax) of new canvas to place image in

    returns : image with annotations plotted in "color_annotations", or other colors
    """
    if img is None:
        img = deepcopy(imgplot)
    # checks
    if color_annotations is None or len(color_annotations) == 0:
        color_annotations = [(255,0,0)]
    while len(color_annotations) < 4:
        csave = deepcopy(color_annotations[-1])
        color_annotations.append( csave )

    color1 = color_annotations[0]
    color2 = color_annotations[1]
    color3 = color_annotations[2]
    color4 = color_annotations[3]

    facecolor = datas_plot['figure']['facecolor']

    iplot_count = 0
    for p,v in datas_plot.items():
        iplot_count += 1
        if 'plot' in p: # not figure stuffs... just yet
            out_string = ' ------ Plot #' + str(p.split('plot')[-1]) + ' ------ \n'
            out_string += 'Plot type:' + v['type'] + '\n'
            out_string += 'Distribution:' + v['distribution'] + '\n'
            if 'data params' in v['data']:
                if 'nclusters' in v['data']['data params']:
                    out_string += '  n_clusters = ' + str(v['data']['data params']['nclusters']) + '\n'
                if 'm1' in v['data']['data params']:
                    out_string += 'm_1 * x + b_1: m_1 & b_1 = ' + str(v['data']['data params']['m1']) + \
                      ' & ' + str(v['data']['data params']['a1']) + '\n'
                if 'm2' in v['data']['data params']:
                    out_string += 'm_2 * y + b_2: m_2 & b_2 = ' + str(v['data']['data params']['m2']) + \
                      ' & ' + str(v['data']['data params']['a2']) + '\n'
                if 'm' in v['data']['data params'] and 'a' in v['data']['data params']:
                    out_string += 'm * x + b: m & b = ' + str(v['data']['data params']['m']) + \
                      ' & ' + str(v['data']['data params']['a']) + '\n'
            if verbose: print(out_string)
            
            # square
            #print(v)
            d = v['square']
            # xmin,ymin = int(d['xmin']),int(img.shape[0]-d['ymin'])
            # xmax,ymax = int(d['xmax']),int(img.shape[0]-d['ymax'])
            #xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape)
            xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape, new_canvas = new_canvas)
            if fill_blocks:
                cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, -1)
            else:
                cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, linethick)
            # title bounding box
            if 'title' in v: # has a title?
                d = v['title']
                # xmin,ymin = int(d['xmin']),int(img.shape[0]-d['ymin'])
                # xmax,ymax = int(d['xmax']),int(img.shape[0]-d['ymax'])
                # xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape)
                xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape, new_canvas = new_canvas)
                if fill_blocks:
                    cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, -1)
                else:
                    cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, linethick)
            # xlabel bounding box
            d = v['xlabel']
            # xmin,ymin = int(d['xmin']),int(img.shape[0]-d['ymin'])
            # xmax,ymax = int(d['xmax']),int(img.shape[0]-d['ymax'])
            # xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape)
            xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape, new_canvas = new_canvas)
            if fill_blocks:
                cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, -1)
            else:
                cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, linethick)
            # ylabel bounding box
            d = v['ylabel']
            # xmin,ymin = int(d['xmin']),int(img.shape[0]-d['ymin'])
            # xmax,ymax = int(d['xmax']),int(img.shape[0]-d['ymax'])
            xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape, new_canvas = new_canvas)
            if fill_blocks:
                cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, -1)
            else:
                cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, linethick)
    
            #print('PLOT:', p)
            if v['type'] == 'line':
                xs = v['data pixels']['xs']
                ys = v['data pixels']['ys']
                for xx,yy in zip(xs,ys):
                    for x,y in zip(xx,yy):
                        x,y = translate_xsys(x,y, img.shape, new_canvas=new_canvas, no_subtract = True)
                        #cv.circle(imgplot, (int(x), int(y)), csize, color1, -1)
                        cv.circle(imgplot, (x, y), csize, color1, -1)
            elif v['type'] == 'scatter':
                xs = v['data pixels']['xs']
                ys = v['data pixels']['ys']
                for x,y in zip(xs,ys):
                    x,y = translate_xsys(x,y, img.shape, new_canvas=new_canvas, no_subtract = True)
                    #cv.circle(imgplot, (int(x), int(y)), csize, color1, -1)
                    cv.circle(imgplot, (x,y), csize, color1, -1)
                # colorbar
                if 'color bar' in v:
                    imgplot = plot_color_bar(v,img,imgplot, lthick=linethick, csize=csize)#, new_canvas=new_canvas)
            elif v['type'] == 'histogram':
                # middle of bar
                xs = np.array(v['data pixels']['xs'])
                ys = np.array(v['data pixels']['ys'])
                for x,y in zip(xs,ys): # middle
                    x,y = translate_xsys(x,y, img.shape, new_canvas=new_canvas, no_subtract = True)                    
                    #cv.circle(imgplot, (int(x), int(y)), csize, color1, -1)
                    cv.circle(imgplot, (x,y), csize, color1, -1)
                # right
                xsr = np.array(v['data pixels']['xs_right'])
                ysr = np.array(v['data pixels']['ys_right'])
                for x,y in zip(xsr,ysr): # right
                    x,y = translate_xsys(x,y, img.shape, new_canvas=new_canvas, no_subtract = True)                    
                    #cv.circle(imgplot, (int(x), int(y)), csize, color1, -1)
                    cv.circle(imgplot, (x,y), csize, color1, -1)
                # left
                xsl = np.array(v['data pixels']['xs_left'])
                ysl = np.array(v['data pixels']['ys_left'])
                for x,y in zip(xsl,ysl): # left
                    x,y = translate_xsys(x,y, img.shape, new_canvas=new_canvas, no_subtract = True)                    
                    #cv.circle(imgplot, (int(x), int(y)), csize, color2, -1)
                    cv.circle(imgplot, (x,y), csize, color2, -1)
            elif v['type'] == 'contour':
                #xs = np.array
                #xs = []; ys = []
                #if 'image' in v['data pixels']:
                if v['data pixels']['image'] != {}:
                    xs = v['data pixels']['image']['xsc']
                    ys = v['data pixels']['image']['ysc']
                    #print('image')
                    #print(xs[:10], ys[:10])
                    for x,y in zip(xs,ys):
                        #print(x,y)
                        x,y = translate_xsys(x,y, img.shape, new_canvas=new_canvas, no_subtract = True)                    
                        #cv.circle(imgplot, (int(x), int(y)), csize, color3, -1)
                        cv.circle(imgplot, (x,y), csize, color3, -1)
                #if 'contour' in v['data pixels']:
                if v['data pixels']['contour'] != {}:
                    xs = v['data pixels']['contour']['xs']
                    ys = v['data pixels']['contour']['ys']
                    #print('contour')
                    #print(xs[:10], ys[:10])
                    for x,y in zip(xs,ys):
                        #print(x,y)
                        x,y = translate_xsys(x,y, img.shape, new_canvas=new_canvas, no_subtract = True)                    
                        #cv.circle(imgplot, (int(x), int(y)), csize, color4, -1)
                        cv.circle(imgplot, (x,y), csize, color4, -1)
                if 'color bar' in v:
                    #print('ding')
                    imgplot = plot_color_bar(v,img,imgplot, lthick=linethick, csize=csize)#, new_canvas=new_canvas)
            elif v['type'] == 'image of the sky':
                # get mods
                if 'sky image params' in v['data']['data params']:
                    ymod = v['data']['data params']['sky image params']['original img size'][1]
                    xmod = v['data']['data params']['sky image params']['original img size'][0]
                    xmod, ymod = translate_xsys(xmod,ymod, img.shape, new_canvas=new_canvas, no_subtract = True) 
                    mx = 1 # should this be 1 or 0?
                    #print('have xy mod:', xmod, ymod)
                if v['data pixels']['image'] != {}:
                    xs = v['data pixels']['image']['xsc']
                    ys = v['data pixels']['image']['ysc']
                    #print('len xs, ys:', len(xs), len(ys))
                    if 'x pixel limits' not in v['data from plot']: # no limits
                        for ixy,(x,y) in enumerate(zip(xs,ys)):
                            x,y = translate_xsys(x,y, img.shape, new_canvas=new_canvas, no_subtract = True)                    
                            #cv.circle(imgplot, (int(x), int(y)), csize, color3, -1)
                            cv.circle(imgplot, (x,y), csize, color3, -1)
                    else:
                        #print('checking limits')
                        for ixy,(x,y) in enumerate(zip(xs,ys)):
                            # check limits
                            # JPN -- not sure about the -1!
                            if (ixy-mx)//xmod > v['data from plot']['x pixel limits'][0] and \
                                (ixy-mx)//xmod < v['data from plot']['x pixel limits'][1] and \
                                    ixy%ymod > v['data from plot']['y pixel limits'][0] and \
                                        ixy%ymod < v['data from plot']['y pixel limits'][1]:
                                x,y = translate_xsys(x,y, img.shape, new_canvas=new_canvas, no_subtract = True)                    
                                #cv.circle(imgplot, (int(x), int(y)), csize, color3, -1)                                
                                cv.circle(imgplot, (x,y), csize, color3, -1)                                
                if v['data pixels']['contour'] != {}:
                    xs = v['data pixels']['contour']['xs']
                    ys = v['data pixels']['contour']['ys']
                    if 'x pixel limits' not in v['data from plot']: # no limits
                        for x,y in zip(xs,ys):
                            x,y = translate_xsys(x,y, img.shape, new_canvas=new_canvas, no_subtract = True)                    
                            #cv.circle(imgplot, (int(x), int(y)), csize, color4, -1)
                            cv.circle(imgplot, (x,y), csize, color4, -1)
                    else:
                        for ixy,(x,y) in enumerate(zip(xs,ys)):
                            # check limits
                            # JPN -- not sure about the -1!
                            if (ixy-mx)//xmod > v['data from plot']['x pixel limits'][0] and \
                                (ixy-mx)//xmod < v['data from plot']['x pixel limits'][1] and \
                                    ixy%ymod > v['data from plot']['y pixel limits'][0] and \
                                        ixy%ymod < v['data from plot']['y pixel limits'][1]:
                                x,y = translate_xsys(x,y, img.shape, new_canvas=new_canvas, no_subtract = True)                    
                                #cv.circle(imgplot, (int(x), int(y)), csize, color4, -1)    
                                cv.circle(imgplot, (x,y), csize, color4, -1)    
                if 'color bar' in v:
                    imgplot = plot_color_bar(v,img,imgplot, lthick=linethick, csize=csize)#,new_canvas=new_canvas, no_subtract = True)                
            else:
                print('no idea how to deal with this plot type! Plot type = ', v['type'])
                import sys; sys.exit()
    
            # these are things for every plot
            # get dx
            if fraction_tick is not None and v['type'] != 'image of the sky':
                xts = []
                for d in v['xticks']:
                    xts.append(d['tx'])
                dx = np.mean((np.roll(xts,-1)-np.array(xts))[:-1])*fraction_tick
                if verbose:
                    print(' -- with fraction_tick =', fraction_tick, 
                        ', dx =', dx)
            else:
                dx = 0.0
            for d in v['xticks']: # draw x-ticks
                xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape, new_canvas = new_canvas)
                #xmin,ymin,xmax,ymax = int(d['xmin']),int(img.shape[0]-d['ymin']),int(d['xmax']),int(img.shape[0]-d['ymax'])
                if d['tx']+dx>=v['square']['xmin'] and d['tx']-dx<=v['square']['xmax']:
                    if fill_blocks:
                        cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, -1)
                    else:
                        cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, linethick)
                # also ticks
                if d['tx']>=v['square']['xmin']-dx and d['tx']<=v['square']['xmax']+dx:
                    x,y = translate_xsys(d['tx'],d['ty'], img.shape, new_canvas=new_canvas)                    
                    #cv.circle(imgplot, (int(d['tx']), int(img.shape[0]-d['ty'])), csize, color1, -1)
                    cv.circle(imgplot, (x,y), csize, color1, -1)
                    #cv.circle(imgplot, (x,y), 50, color1, -1)
            # get dy
            if fraction_tick is not None and v['type'] != 'image of the sky':
                yts = []
                for d in v['yticks']:
                    yts.append(d['ty'])
                dy = np.mean((np.roll(yts,-1)-np.array(yts))[:-1])*fraction_tick
                if verbose:
                    print(' -- with fraction_tick =', fraction_tick, 
                        ', dy =', dy)
            else:
                dy = 0.0
            for d in v['yticks']: # draw y-ticks
#                xmin,ymin,xmax,ymax = int(d['xmin']),int(img.shape[0]-d['ymin']),int(d['xmax']),int(img.shape[0]-d['ymax'])
                xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape, new_canvas = new_canvas)
                if d['ty']+dy>=v['square']['ymin'] and d['ty']-dy<=v['square']['ymax']:
                    if fill_blocks:
                        cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, -1)
                    else:
                        cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, linethick)
                if d['ty']>=v['square']['ymin']-dy and d['ty']<=v['square']['ymax']+dy:
                    x,y = translate_xsys(d['tx'],d['ty'], img.shape, new_canvas=new_canvas)                    
                    #cv.circle(imgplot, (int(d['tx']), int(img.shape[0]-d['ty'])), csize, color1, -1)
                    cv.circle(imgplot, (x,y), csize, color1, -1)
            # any offset labels?
            for t in ['x','y']:
                if t + '-offset text' in v:
                    # xmin = int(round(v[t + '-offset text']['xmin']))
                    # ymin = img.shape[0]-int(round(v[t + '-offset text']['ymin']))
                    # xmax = int(round(v[t + '-offset text']['xmax']))
                    # ymax = img.shape[0]-int(round(v[t + '-offset text']['ymax']))
                    xmin,ymin,xmax,ymax = rescale_xymin(v[t + '-offset text'], img.shape, new_canvas = new_canvas)
                    if fill_blocks:
                        cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, -1)
                    else:
                        cv.rectangle(imgplot, (xmin,ymin), (xmax,ymax), color1, linethick)

            if v['type'] == 'line':
                if 'x error bars' in v['data pixels']:
                    for il,l in enumerate(v['data pixels']['x error bars']):
                        for ie,(xmin,ymin,xmax,ymax) in enumerate(l):
                            xmin,ymin = int(round(xmin)),int(round(img.shape[0]-ymin))
                            xmax,ymax = int(round(xmax)),int(round(img.shape[0]-ymax))
                            # only take parts within square
                            xmin = max(xmin,int(round(v['square']['xmin'])))
                            xmax = min(xmax,int(round(v['square']['xmax'])))
                            ymin = max(ymin,int(round(img.shape[0]-v['square']['ymax'])))
                            ymax = min(ymax,int(round(img.shape[0]-v['square']['ymin'])))
                            d = {'xmin':xmin,'ymin':ymin+img.shape[0], 'xmax':xmax, 'ymax':ymax+img.shape[0]}
                            xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape, new_canvas = new_canvas)
                            cv.line(imgplot, (xmin,ymin),(xmax,ymax), color1, 2)
                if 'y error bars' in v['data pixels']:
                    for l in v['data pixels']['y error bars']:
                        for xmin,ymin,xmax,ymax in l:
                            xmin,ymin = int(round(xmin)),int(round(img.shape[0]-ymin))
                            xmax,ymax = int(round(xmax)),int(round(img.shape[0]-ymax))
                            # only take parts within square
                            xmin = max(xmin,int(round(v['square']['xmin'])))
                            xmax = min(xmax,int(round(v['square']['xmax'])))
                            ymin = max(ymin,int(round(img.shape[0]-v['square']['ymax'])))
                            ymax = min(ymax,int(round(img.shape[0]-v['square']['ymin'])))
                            d = {'xmin':xmin,'ymin':ymin+img.shape[0], 'xmax':xmax, 'ymax':ymax+img.shape[0]}
                            xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape, new_canvas = new_canvas)
                            cv.line(imgplot, (xmin,ymin),(xmax,ymax), color1, 2)
            elif v['type'] == 'scatter' or v['type'] == 'histogram':
                if 'x error bars' in v['data pixels']:
                    for xmin,ymin,xmax,ymax in v['data pixels']['x error bars']:
                        xmin,ymin = int(round(xmin)),int(round(img.shape[0]-ymin))
                        xmax,ymax = int(round(xmax)),int(round(img.shape[0]-ymax))
                        # only take parts within square
                        xmin = max(xmin,int(round(v['square']['xmin'])))
                        xmax = min(xmax,int(round(v['square']['xmax'])))
                        ymin = max(ymin,int(round(img.shape[0]-v['square']['ymax'])))
                        ymax = min(ymax,int(round(img.shape[0]-v['square']['ymin'])))
                        d = {'xmin':xmin,'ymin':ymin+img.shape[0], 'xmax':xmax, 'ymax':ymax+img.shape[0]}
                        xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape, new_canvas = new_canvas)
                        cv.line(imgplot, (xmin,ymin),(xmax,ymax), color1, 2)
                if 'y error bars' in v['data pixels']:
                    for xmin,ymin,xmax,ymax in v['data pixels']['y error bars']:
                        #print(ymin,ymax)
                        xmin,ymin = int(round(xmin)),int(round(img.shape[0]-ymin))
                        xmax,ymax = int(round(xmax)),int(round(img.shape[0]-ymax))
                        xmin = max(xmin,int(round(v['square']['xmin'])))
                        xmax = min(xmax,int(round(v['square']['xmax'])))
                        ymin = max(ymin,int(round(img.shape[0]-v['square']['ymax'])))
                        ymax = min(ymax,int(round(img.shape[0]-v['square']['ymin'])))
                        d = {'xmin':xmin,'ymin':ymin+img.shape[0], 'xmax':xmax, 'ymax':ymax+img.shape[0]}
                        xmin,ymin,xmax,ymax = rescale_xymin(d, img.shape, new_canvas = new_canvas)
                        cv.line(imgplot, (xmin,ymin),(xmax,ymax), color1, 2)

    return imgplot
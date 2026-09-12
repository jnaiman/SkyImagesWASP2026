import numpy as np
import json
from scipy.stats import loguniform

from .distribution_utils import get_random_data, \
   get_linear_data, get_gmm_data, get_sky_image_data


# for saving numpy arrays
# https://stackoverflow.com/questions/26646362/numpy-array-is-not-json-serializable
class NumpyEncoder(json.JSONEncoder):
    """ Special json encoder for numpy types """
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return 'non serializable entry'
        return json.JSONEncoder.default(self, obj)

# NOTE: the upstream copy of this file also defined FitzNumpyEncoder and
# fitz_object_hook here, for serialising PyMuPDF geometry produced by the PDF
# mining half of the ArXiv_figure_injection pipeline.  Nothing in synthetic
# figure generation emits fitz objects, so they are dropped here and PyMuPDF
# is not a dependency of this repo.

##########################################
############## CONTOUR DATA ###############
##########################################
from .plot_classes_utils import Contour

def get_contour_data(plot_params, distribution = 'random',
                     verbose=True, rng=np.random, figure_params=None, 
                     iterate_max_aspect = 50, verbose_level=1,
                     **kwargs):
    """
    plot_params : directory with plot params
    """
    #print('here1')
    contour = Contour()
    for k,v in kwargs.items():
        if k in contour.__dict__: # in there
            setattr(contour, k, v)

    data_params = {}
    #print('contour', contour.__dict__)
    if contour.nx is None:
        nx = int(round(rng.uniform(low=plot_params['npoints']['nx']['min'], 
                                          high=plot_params['npoints']['nx']['max'])))
    else:
        nx = contour.nx
    if contour.ny is None:
        ny = int(round(rng.uniform(low=plot_params['npoints']['ny']['min'], 
                                          high=plot_params['npoints']['ny']['max'])))
    else:
        ny = contour.ny

    # also add in for figure params?
    if figure_params is not None and contour.ny is None:
        ny = int(round(nx/figure_params['aspect ratio']))

    #print('here2')
    
    xmin_base,xmax_base = plot_params['xmin'],plot_params['xmax']
    ymin_base,ymax_base = plot_params['ymin'],plot_params['ymax']
    if contour.aspect_ratio_limit is None:
        aspect_ratio_limit = plot_params['aspect ratio limit']
    else:
        aspect_ratio_limit = contour.aspect_ratio_limit

    # start
    aspect_ratio = aspect_ratio_limit + 1.0

    #print('here3')
    #print('aspect ratio:', aspect_ratio, 'aspect_ratio_limit:', aspect_ratio_limit)
    iloop = 0
    while ((aspect_ratio > aspect_ratio_limit) or (1./aspect_ratio > aspect_ratio_limit)) and (iloop<=iterate_max_aspect):
        x1 = rng.uniform(low=xmin_base, high=xmax_base)
        x2 = rng.uniform(low=xmin_base, high=xmax_base)
        if x1<x2:
            xmin = x1; xmax = x2
        else:
            xmin=x2; xmax=x1
        y1 = rng.uniform(low=ymin_base, high=ymax_base)
        y2 = rng.uniform(low=ymin_base, high=ymax_base)
        if y1<y2:
            ymin = y1; ymax = y2
        else:
            ymin=y2; ymax=y1

        if np.abs((ymax-ymin)) > 0: # make sure division will work
            aspect_ratio = np.abs((xmax-xmin)/(ymax-ymin))
            #print('aspect ratio OK:', aspect_ratio)
        else:
            aspect_ratio = aspect_ratio_limit + 1.0
            #print('aspect ratio not ok:', aspect_ratio)
        if aspect_ratio == 0:
            #print('aspect ratio 0:', aspect_ratio)
            aspect_ratio = aspect_ratio_limit + 1.0

        iloop+=1
        if iloop >= iterate_max_aspect: # try again
            if verbose and verbose_level>1:
                print("Issue with aspect ratio that can't be overcome, resetting min/max x/y...")
            # xmin_base,xmax_base = plot_params['xmin'],plot_params['xmax']
            # ymin_base,ymax_base = plot_params['ymin'],plot_params['ymax']
            xmax_base = np.abs(xmin_base) + 10*np.abs(xmin_base)
            ymax_base = np.abs(ymin_base) + 10*np.abs(ymin_base)

        #print(aspect_ratio)

    #print('here4')

    c1 = rng.uniform(low=plot_params['colors']['min'], 
                           high=plot_params['colors']['max'])
    c2 = rng.uniform(low=plot_params['colors']['min'], 
                           high=plot_params['colors']['max'])
    if c1<c2:
        cmin = c1; cmax = c2
    else:
        cmin=c2; cmax=c1

    # replace with inputs if requested
    if contour.xmin is not None:
        xmin = contour.xmin
    if contour.ymin is not None:
        ymin = contour.ymin
    if contour.xmax is not None:
        xmax = contour.xmax
    if contour.ymax is not None:
        ymax = contour.ymax
    if contour.cmin is not None:
        cmin = contour.cmin
    if contour.cmax is not None:
        cmax = contour.cmax

    # if verbose:
    #     print('Start pull data for contour plots...')
    #     print('  distribution = ', distribution)
    if distribution == 'random':
        #print(xmin,xmax)
        xs,ys,colors = get_random_data('contour',xmin,xmax,ymin,ymax,
                                  npoints=(nx,ny),
                                  zmin=cmin, zmax=cmax, rng=rng) 
    elif distribution == 'linear':
        xs,ys,colors, data_params = get_linear_data('contour',plot_params['distribution'][distribution],
                                                    xmin,xmax,ymin,ymax,
                                  npoints=(nx,ny), rng=rng)#,
                                  #zmin=cmin, zmax=cmax) 
    elif distribution == 'gmm':
        xs,ys,colors, data_params = get_gmm_data('contour',
                                                 plot_params['distribution'][distribution],
                                                    xmin,xmax,ymin,ymax,
                                  npoints=(nx,ny),
                                  #zmin=cmin, zmax=cmax) 
                                  cmin=cmin, cmax=cmax, rng=rng, function=rng.uniform) 

    # do we have x/y error bars?
    hasXErr = False; hasYErr = False
    xerr,yerr = [],[] # x/y error maybe later

    return xs, ys, colors, xerr, yerr, data_params

####################################################
############## IMAGE OF THE SKY DATA ###############
####################################################

from .plot_classes_utils import ImageOfSky 

def get_min_max_imgOfSky(imgOfSky, plot_params, rng, distribution):
    dirout = {}
    if distribution == 'gmm':
        xmins = ['xmin', 'ymin', 'cmin']
        xmaxs = ['xmax', 'ymax', 'cmax']
    elif distribution == 'sky':
        xmins = ['cmin']
        xmaxs = ['cmax']
    else:
        print('not sure what this distribution is!!')
        print(distribution)
        import sys; sys.exit()

    for mins,maxs in zip(xmins, xmaxs):
        if getattr(imgOfSky,mins) is None:
            if mins in plot_params:
                xmin = plot_params[mins]
            else:
                print("ERROR in min for Img of sky!")
                print('mins:', mins)
                import sys; sys.exit()
        else:
            xmin = getattr(imgOfSky,mins)
        if getattr(imgOfSky,maxs) is None:
            if maxs in plot_params:
                xmax = plot_params[maxs]
            else:
                print("ERROR in max for Img of sky!")
                import sys; sys.exit()
        else:
            xmax = getattr(imgOfSky,maxs)

        if getattr(imgOfSky,maxs) is None and getattr(imgOfSky, mins) is None:
            x1 = rng.uniform(low=xmin, high=xmax)
            x2 = rng.uniform(low=xmin, high=xmax)
            if x1<x2:
                xmin = x1; xmax = x2
            else:
                xmin=x2; xmax=x1  
        else:
            pass
        dirout[mins] = xmin
        dirout[maxs] = xmax
    return dirout


from astropy.visualization import simple_norm
def get_image_of_the_sky_data(plot_params, distribution = 'random',
                     verbose=True, rng=np.random, warning_verbose=False,
                     figure_params=None, image_renorm = 'log', **kwargs):
    """
    plot_params : directory with plot params
    """

    imgOfSky = ImageOfSky()
    for k,v in kwargs.items():
        if k in imgOfSky.__dict__: # in there
            setattr(imgOfSky, k, v)

    data_params = {}
    if imgOfSky.nx is None:
        nx = int(round(rng.uniform(low=plot_params['npoints']['nx']['min'], 
                                          high=plot_params['npoints']['nx']['max'])))
    else:
        nx = imgOfSky.nx

    if imgOfSky.ny is None:
        ny = int(round(rng.uniform(low=plot_params['npoints']['ny']['min'], 
                                          high=plot_params['npoints']['ny']['max'])))
    else:
        ny = imgOfSky.ny

    # in case you want to resize for the aspect ratio of the plot
    if figure_params is not None and imgOfSky.ny is None:
        ny = int(round(nx/figure_params['aspect ratio']))

    if imgOfSky.distribution is not None:
        distribution = imgOfSky.distribution

    # light reformat
    plot_params_mod = {}
    for k in ['xmin', 'xmax', 'ymin', 'ymax']:
        plot_params_mod[k] = plot_params[k]
    for kin, kout in zip(['min', 'max'], ['cmin', 'cmax']):
        plot_params_mod[kout] = plot_params['colors'][kin]
    dirminsmaxs = get_min_max_imgOfSky(imgOfSky, plot_params_mod, rng, distribution)


    if distribution == 'gmm':
        xy_params = plot_params['distribution'][distribution]['centers']

        # gmm-params
        if imgOfSky.gmm_center_scale is None:
            xy_scale = xy_params['center_scale']['scale']
        else:
            xy_scale = imgOfSky.gmm_center_scale
        if imgOfSky.gmm_scale_min is None:
            xy_scale_min = xy_params['center_scale']['min']
        else:
            xy_scale_min = imgOfSky.gmm_scale_min
        if imgOfSky.gmm_scale_max is None:
            xy_scale_max = xy_params['center_scale']['max']
        else:
            xy_scale_max = imgOfSky.gmm_scale_max

        if verbose and warning_verbose:
           print('image of sky w/GMM, overwriting xmin/xmax/ymin/ymax')

        #print(xy_params)
        if xy_scale != 'log':
            print('[ERROR]: in data_utils -- wrong scale selected:', xy_params['scale']) 
        else:
            scale = loguniform.rvs(xy_scale_min, 
                                   xy_scale_max, size=1, 
                                   random_state=rng)[0] # in arcsec
            # to deg (ra/dec in deg)
            scale /= 60*60

        # pick x/y center
        if imgOfSky.gmm_center_ra is None:
            x_center = rng.uniform(low=xy_params['center_ra']['min'], high=xy_params['center_ra']['max'])
        else:
            x_center = imgOfSky.gmm_center_ra
        if imgOfSky.gmm_center_dec is None:
            y_center = rng.uniform(low=xy_params['center_dec']['min'], high=xy_params['center_dec']['max'])
        else:
            y_center = imgOfSky.gmm_center_dec

        xmin = x_center-scale*0.5; xmax = x_center + scale*0.5
        ymin = y_center -scale*0.5; ymax = y_center +scale*0.5

        # checks for in bounds
        dx = xmax-xmin; dy = ymax-ymin
        if xmin < xy_params['center_ra']['min']: # shift
            xmin = xy_params['center_ra']['min']
            xmax = xmin + dx
        if xmax > xy_params['center_ra']['max']:
            xmax = xy_params['center_ra']['max']
            xmin = xmax - dx
        if ymin < xy_params['center_dec']['min']:
            ymin = xy_params['center_dec']['min']
            ymax = ymin + dy
        if ymax > xy_params['center_dec']['max']:
            ymax = xy_params['center_dec']['max']
            ymin = ymax - dy

        if verbose and warning_verbose:
            print('[WARNING]: for gmm image of sky, assume same scale in x/y')
            print('   x (RA):', xmin, xmax)
            print('   y (DEC):', ymin, ymax)

        distparams = plot_params['distribution']['gmm'] # use GMM params for creation

        xs,ys,colors, data_params = get_gmm_data('contour', # using contour for this
                                        distparams,
                                        xmin,xmax,ymin,ymax,
                        npoints=(nx,ny),
                        #zmin=cmin, zmax=cmax) 
                        cmin=dirminsmaxs['cmin'], 
                        cmax=dirminsmaxs['cmax'], 
                        rng=rng, function=rng.uniform) 

        if verbose and warning_verbose:
            print('[WARNING]: RA/DEC both in deg')

        #import sys; sys.exit()
    elif distribution == 'sky':
        #print('[ERROR]: not implemented yet!', distribution)
        #distparams = plot_params['distribution']['sky'] # sky image info
        #distparams['xy labels ra/dec'] = plot_params['xy labels ra/dec'] # pass RA/DEC formats
        # nx/ny were sampled above for both distributions; pass them through so a
        # real cutout ends up on the same grid a GMM sky would have used,
        # instead of always coming back as the fetched 300x300
        xs,ys,colors, data_params = get_sky_image_data(plot_params,
                        cmin=dirminsmaxs['cmin'], 
                        cmax=dirminsmaxs['cmax'], 
                        nx=nx, ny=ny,
                        rng=rng, verbose=verbose, **kwargs)
        # to avoid FITS memory issues with stretch, take out outliers
        norm = simple_norm(colors, image_renorm, percent=99)
        im_stretch = norm(colors)
        norm2 = simple_norm(colors, image_renorm, percent=99) # might not need it 2x?
        colors = norm2.inverse(im_stretch)
    else:
        print('[ERROR]: in data_utils (get_image_of_the_sky_data), no such distribution -', distribution)

    # do we have x/y error bars?
    hasXErr = False; hasYErr = False
    xerr,yerr = [],[] # x/y error maybe later

    # if imgOfSky.image_renorm is None and (image_renorm_gmm is None or distribution=='sky'):
    #     # pick randomly
    #     renorms = plot_params['image renorm']['prob']
    #     choices, probs = [],[]
    #     for k,v in renorms.items():
    #         choices.append(k)
    #         probs.append(v)
    #     # renorm
    #     probs = np.array(probs)/np.sum(probs)
    #     image_renorm = rng.choice(choices, p=probs)
    # elif image_renorm_gmm is not None and distribution == 'gmm':
    #     image_renorm = image_renorm_gmm
    # else:
    #     image_renorm = imgOfSky.image_renorm
    # add a few things for data params for rescaling
    # get renorm

    # renomre to t
    #norm = simple_norm(colors, image_renorm, percent=99)

    # data_params['norm type'] = image_renorm
    # data_params['norm function'] = norm

    return xs, ys, colors, xerr, yerr, data_params



############################################################
######################## LINES DATA ########################
############################################################

from .plot_classes_utils import Line

def get_line_data(plot_params, npoints,nlines,xmin=0, xmax=1, ymin=0, ymax=1, 
                  #prob_same_x=0.1,
                  xordered=True, verbose=True,
                 pick_xrange=True, pick_yrange=True,
                 distribution='random', rng=np.random, **kwargs):
    """
    ymin/ymax : can be a number of a list, if list, needs to be matched up with number of nlines
    xordered : do we want to put the x-points in a monotonic order?
    """
    line = Line()
    for k,v in kwargs.items():
        if k in line.__dict__: # in there
            setattr(line, k, v)

    if line.prob_same_x is None:
        prob_same_x = plot_params['prob same x']
    else:
        prob_same_x = line.prob_same_x

    data_params = {}
    if (type(ymin) not in [list, np.ndarray]) and (type(ymax) not in [list, np.ndarray]):
        pass
    elif ((type(ymin) not in [list, np.ndarray]) and (type(ymax) in [list, np.ndarray])):
        if verbose: print('type of ymin and ymax must be the same!  Will fall back on ints')
        ymax = ymax[0]
    elif ((type(ymin) in [list, np.ndarray]) and (type(ymax) not in [list, np.ndarray])):
        if verbose: print('type of ymin and ymax must be the same!  Will fall back on ints')
        ymin = ymin[0]
    elif len(ymin) != nlines or len(ymax) != nlines:
        if verbose: print('length of ymax, ymin not the same as "nlines", falling back on ints')
        ymin = ymin[0]; ymax = ymax[0]

    nlines = int(round(rng.uniform(low=nlines['min'], high=nlines['max'])))
    npoints = int(round(rng.uniform(low=npoints['min'], high=npoints['max'])))

    # pick randomly
    if pick_xrange:
        x1 = rng.uniform(low=xmin, high=xmax)
        x2 = rng.uniform(low=xmin, high=xmax)
        if x1<x2:
            xmin = x1; xmax = x2
        else:
            xmin=x2; xmax=x1
    if pick_yrange:
        y1 = rng.uniform(low=ymin, high=ymax)
        y2 = rng.uniform(low=ymin, high=ymax)
        if y1<y2:
            ymin = y1; ymax = y2
        else:
            ymin=y2; ymax=y1

    # into arrays
    if (type(ymin) not in [list, np.ndarray]) and (type(ymax) not in [list, np.ndarray]):
        ymin = np.repeat(ymin,nlines)
        ymax = np.repeat(ymax,nlines)

    if distribution == 'random':
        xs,ys = get_random_data('line',xmin,xmax,ymin,ymax,
                    prob_same_x=prob_same_x, 
                            nlines=nlines, npoints=npoints, rng=rng)
    elif distribution == 'linear':
        #print("HI IN GET LINE DATA")
        xs,ys,data_params = get_linear_data('line', plot_params['distribution'][distribution],
                                xmin,xmax,ymin,ymax,
                    prob_same_x=prob_same_x, 
                            nlines=nlines, npoints=npoints, rng=rng)
    elif distribution == 'gmm': # gaussian mixture model
        xs,ys,data_params = get_gmm_data('line', plot_params['distribution'][distribution],
                                xmin,xmax,ymin,ymax,
                    prob_same_x=prob_same_x, 
                            nlines=nlines, npoints=npoints, rng=rng, function=rng.uniform)
        # have to update for binning
        npoints = len(xs[0])
    else:
        print("don't know how to deal with this line distribution!")
        import sys; sys.exit()

    # do we have x/y error bars?
    hasXErr = False; hasYErr = False
    xerrs,yerrs = [],[]

    # for error rate
    #scale = 
    if rng.uniform(0,1) <= plot_params['error bars']['x']['prob']: # yes
        hasXErr = True
        scale = np.max(xmax)-np.min(xmin)
        for i in range(nlines):
            xerr = rng.uniform(low=plot_params['error bars']['x']['size']['min']*scale, 
                                 high=plot_params['error bars']['x']['size']['max']*scale,
                                 size=len(xs[i]))
            xerrs.append(xerr)
    if rng.uniform(0,1) <= plot_params['error bars']['y']['prob']: # yes
        hasYErr = True
        scale = np.max(ymax)-np.min(ymin)
        for i in range(nlines):
            yerr = rng.uniform(low=plot_params['error bars']['y']['size']['min']*scale, 
                                 high=plot_params['error bars']['y']['size']['max']*scale,
                                 size=len(xs[i]))
            yerrs.append(yerr)
    
    return xs, ys, xerrs, yerrs, data_params


############################################################
######################## SCATTER DATA ########################
############################################################

def get_scatter_data(plot_params, distribution = 'random',
                     verbose=True, rng=np.random):
    """
    plot_params : directory with plot params
    """

    data_params = {}
    npoints = int(round(rng.uniform(low=plot_params['npoints']['min'], 
                                          high=plot_params['npoints']['max'])))
    #print('npoints here:', npoints)
    
    xmin,xmax = plot_params['xmin'],plot_params['xmax']
    ymin,ymax = plot_params['ymin'],plot_params['ymax']


    x1 = rng.uniform(low=xmin, high=xmax)
    x2 = rng.uniform(low=xmin, high=xmax)
    if x1<x2:
        xmin = x1; xmax = x2
    else:
        xmin=x2; xmax=x1
    y1 = rng.uniform(low=ymin, high=ymax)
    y2 = rng.uniform(low=ymin, high=ymax)
    if y1<y2:
        ymin = y1; ymax = y2
    else:
        ymin=y2; ymax=y1
    c1 = rng.uniform(low=plot_params['colors']['min'], 
                           high=plot_params['colors']['max'])
    c2 = rng.uniform(low=plot_params['colors']['min'], 
                           high=plot_params['colors']['max'])
    if c1<c2:
        cmin = c1; cmax = c2
    else:
        cmin=c2; cmax=c1

    if distribution == 'random':
        xs,ys,colors = get_random_data('scatter',xmin,xmax,ymin,ymax,
                                  npoints=npoints,
                                  cmin=cmin, cmax=cmax, rng=rng)
    elif distribution == 'linear':
        xs,ys,colors,data_params = get_linear_data('scatter', 
                                    plot_params['distribution'][distribution],
                                    xmin,xmax,ymin,ymax,
                                    cmin=cmin,cmax=cmax,
                                    npoints=npoints, rng=rng)
    elif distribution == 'gmm':
        xs,ys,colors,data_params = get_gmm_data('scatter', 
                                    plot_params['distribution'][distribution],
                                    xmin,xmax,ymin,ymax,
                                    cmin=cmin,cmax=cmax,
                                    npoints=npoints, rng=rng, function=rng.uniform)
        # have to update npoints based on how things where sampled??
        npoints = len(xs)
    else:
        print('no such distribution in "get_scatter_data"!')
        import sys; sys.exit()


    # do we have x/y error bars?
    hasXErr = False; hasYErr = False
    xerr,yerr = [],[]

    if rng.uniform(0,1) <= plot_params['error bars']['x']['prob']: # yes
        hasXErr = True
        scale = xmax-xmin
        xerr = rng.uniform(low=plot_params['error bars']['x']['size']['min']*scale, 
                                 high=plot_params['error bars']['x']['size']['max']*scale,
                                 size=len(xs))
    if rng.uniform(0,1) <= plot_params['error bars']['y']['prob']: # yes
        hasYErr = True
        scale = ymax-ymin
        yerr = rng.uniform(low=plot_params['error bars']['y']['size']['min']*scale, 
                                 high=plot_params['error bars']['y']['size']['max']*scale,
                                 size=len(xs))

    #print(xerr)
    #print(yerr)
    #if data_params == {}:
    #    print('missing data params!!!!!!!')
    return xs, ys, colors, xerr, yerr, data_params



################################################
############ HISTOGRAM PLOTS: PLOT ############
################################################

def get_histogram_data(plot_params, distribution = 'random',
                     verbose=True, rng=np.random):
    """
    plot_params : plot parameters
    """

    data_params = {}
    npoints = int(round(rng.uniform(low=plot_params['npoints']['min'], 
                                          high=plot_params['npoints']['max'])))
    
    xmin,xmax = plot_params['xmin'],plot_params['xmax']

    x1 = rng.uniform(low=xmin, high=xmax)
    x2 = rng.uniform(low=xmin, high=xmax)
    if x1<x2:
        xmin = x1; xmax = x2
    else:
        xmin=x2; xmax=x1

    ys = []
    if distribution == 'random':
        xs = get_random_data('histogram',xmin,xmax,
                                  npoints=npoints, rng=rng)
    elif distribution == 'linear':
        xs, data_params = get_linear_data('histogram',plot_params['distribution'][distribution],
                                          xmin,xmax,
                                  npoints=npoints, rng=rng)
    elif distribution == 'gmm':
        xs, data_params = get_gmm_data('histogram',plot_params['distribution'][distribution],
                                          xmin,xmax,
                                  npoints=npoints, rng=rng, function=rng.uniform)
    else:
        print('no distribution in "get_histogram_data"!')
        import sys; sys.exit()
    
    # do we have x/y error bars?
    hasXErr = False; hasYErr = False
    # xerr,yerr = [],[]

    if rng.uniform(0,1) <= plot_params['error bars']['x']['prob']: # yes
        hasXErr = True
    #     #scale = xmax-xmin
    #     scale = xs
    #     xerr = rng.uniform(low=plot_params['error bars']['x']['size']['min'], 
    #                              high=plot_params['error bars']['x']['size']['max'],
    #                              size=npoints)*scale
        
    if rng.uniform(0,1) < plot_params['horizontal prob']: # probability that we have a horizontal bar plot
        # flip
        ys = xs.copy()
        #yerr = xerr.copy()
        #xs = []; ys = []
        hasYErr = True
        hasXErr = False

    return xs, ys, hasXErr, hasYErr, data_params # this is different than other plots!



###########################################################################
######################## MAIN GET DATA #######################
###########################################################################

##### GENERIC DATA AND PLOTS #####
def get_data(plot_params, plot_type='line', distribution='random', #npoints = 100, xmin=0, xmax=1, ymin=0, ymax=1, 
             #xordered=True, nlines=1, # line params
             verbose=True, xordered=True, # general params
             rng=None, # random number generation
             figure_params = None, # in case you need to pas info about the figure
             **kwargs
            ):
    if rng is None:
        rng = np.random
    if plot_type == 'line':
        xs, ys, xerrs,yerrs, data_params = get_line_data(plot_params,  
                                            plot_params['npoints'], # this bad coding, should just pass plot_params
                              plot_params['nlines'],
                              xmin=plot_params['xmin'], 
                              xmax=plot_params['xmax'], 
                              ymin=plot_params['ymin'], 
                              ymax=plot_params['ymax'], 
                              #prob_same_x=plot_params['prob same x'],
                              xordered=xordered, 
                              verbose=verbose, 
                                            distribution=distribution,
                                            rng=rng, **kwargs)
        data = {'xs':xs, 'ys':ys}
        if len(xerrs) > 0:
            data['xerrs'] = xerrs
        if len(yerrs) > 0:
            data['yerrs'] = yerrs
        if data_params != {}:
            data['data params'] = data_params
        return data
    elif plot_type == 'scatter':
        xs, ys, colors_scatter,xerr,yerr, data_params = get_scatter_data(plot_params,
                                                           distribution=distribution, 
                                                           rng=rng,
                                                           verbose=verbose)
        data = {'xs':xs, 'ys':ys, 'colors':colors_scatter}
        if len(xerr) > 0:
            data['xerrs'] = xerr
        if len(yerr) > 0:
            data['yerrs'] = yerr
        if data_params != {}:
            data['data params'] = data_params
        else:
            pass
            #print('in get_data --- NO DATA PARAMS')
        return data
    elif plot_type == 'histogram':
        xs,ys,hasXErr,hasYErr, data_params = get_histogram_data(plot_params,
                                                   distribution=distribution,
                                                   rng=rng,
                                                           verbose=verbose)
        data = {'xs':xs, 'ys':ys}
        #if len(xerr) > 0:
        if hasXErr:
            data['xerrs'] = hasXErr # different!
        #if len(yerr) > 0:
        if hasYErr:
            data['yerrs'] = hasYErr # different!
        if data_params != {}:
            data['data params'] = data_params
        return data
    elif plot_type == 'contour':
        xs, ys, color_grid,xerr,yerr, data_params = get_contour_data(plot_params,
                                                       distribution=distribution, 
                                                       rng=rng,
                                                           verbose=verbose, 
                                                           **kwargs)
        data = {'xs':xs, 'ys': ys, 'colors':color_grid}
        if len(xerr) > 0:
            data['xerrs'] = xerr
        if len(yerr) > 0:
            data['yerrs'] = yerr
        if data_params != {}:
            data['data params'] = data_params
        return data
    elif plot_type == 'image of the sky':
        xs, ys, color_grid,xerr,yerr, data_params = get_image_of_the_sky_data(plot_params,
                                                       distribution=distribution, rng=rng,
                                                           verbose=verbose, 
                                                           figure_params=figure_params,
                                                           **kwargs)
        data = {'xs':xs, 'ys': ys, 'colors':color_grid}
        if len(xerr) > 0:
            data['xerrs'] = xerr
        if len(yerr) > 0:
            data['yerrs'] = yerr
        if data_params != {}:
            data['data params'] = data_params
        return data
    else:
        print('not implement for this plot type!', 'Plot type:', plot_type)
        import sys; sys.exit()




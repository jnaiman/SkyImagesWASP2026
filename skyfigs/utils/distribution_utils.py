import numpy as np

######### "RAW" DISTRIBUTIONS ##########

def get_random(xmin,xmax,ymin=0,ymax=0, zmin=0,zmax=1,hmin=0,hmax=1,
               ndims=1,
               npoints=10,grid=False,
              function=np.random.uniform): #, rng=np.random):
    """
    Generic random distribution
    ndims : 1-3, how many dimensions for the data
    xmin/xmax : ranges for dimension 1
    ymin/ymax : ranges for dimension 2
    zmin/zmax : ranges for dimension 3
    hmin/hmax : ranges for dimension 3, grid=True (3d "heatmap")
    npoints : number of random points (can be a tuple for different values)
    function : how to generate the random numbers
    grid : if ndim>1 and grid is set to True instead of individual points, 
           you will get a data on a uniform grid
    """
    if ndims == 1:
        #print(xmin)
        #print(xmax)
        #print(npoints)
        return function(low=xmin, high=xmax, size=npoints)
    elif ndims == 2:
        if not grid:
            return function(low=np.array([xmin,ymin]),
                            high=np.array([xmax,ymax]), size=[npoints,2])
        else:
            x = np.linspace(xmin,xmax,npoints[0])
            y = np.linspace(ymin,ymax,npoints[1])
            #grid = function(low=zmin,high=zmax,size=(npoints,npoints))
            grid = function(low=zmin,high=zmax,size=npoints) # npoints is a tuple (nx,ny)
            return {'x':x, 'y':y, 'z':grid.T} # .T for right shape
    elif ndims == 3:
        if not grid:
            return function(low=np.array([xmin,ymin,zmin]),
                            high=np.array([xmax,ymax,zmax]), size=[npoints,3])
        else:
            x = np.linspace(xmin,xmax,npoints[0])
            y = np.linspace(ymin,ymax,npoints[1])
            z = np.linspace(zmin,zmax,npoints[2])
            #grid = function(low=hmin,high=hmax,size=(npoints,npoints,npoints))
            grid = function(low=hmin,high=hmax,size=npoints) # tuple (nx,ny,nz)
            return {'x':x, 'y':y, 'z':z, 'h':grid.T} # .T for right shape

    else:
        print('ndims=', ndims, 'not supported for "get_random" function!')
        import sys; sys.exit()
        


##### SPECIFIC DISTRIBUTIONS #######
def get_random_data(plot_type,xmin,xmax,ymin=0,ymax=1,zmin=0,zmax=0,
                    prob_same_x=0.5, nlines=1, npoints=1,
                   cmin=0, cmax=1, rng=np.random):
    """
    npoints : can be tuple if multi dimension
    """
    # do we have all the same x for all points?
    if plot_type == 'line':
        p = rng.uniform(0,1)
        xs = []
        if p <= prob_same_x: # same x for all y
            x = get_random(xmin,xmax,ndims=1,npoints=npoints, 
                           function=rng.uniform)#, rng=rng)
            x = np.sort(x)
            # repeat for all
            for i in range(nlines):
                xs.append(x)
        else: # different
            for i in range(nlines):
                x = get_random(xmin,xmax,ndims=1,npoints=npoints, function=rng.uniform)#, rng=rng)
                x = np.sort(x)
                xs.append(x)
            
        ys = []
        for i in range(nlines):
            y = get_random(ymin[i],ymax[i],ndims=1,npoints=npoints, function=rng.uniform)#, rng=rng)
            ys.append(y)
        return xs,ys
    elif plot_type == 'scatter':
        xs = get_random(xmin,xmax,ndims=1,npoints=npoints, function=rng.uniform)#, rng=rng)
        ys = get_random(ymin,ymax,ndims=1,npoints=npoints, function=rng.uniform)#, rng=rng)
        colors = get_random(cmin,cmax,ndims=1,npoints=npoints, function=rng.uniform)#, rng=rng)
        return xs,ys,colors
    elif plot_type == 'histogram':
        x = get_random(xmin,xmax,ndims=1,npoints=npoints, function=rng.uniform)#, rng=rng)
        return x
    elif plot_type == 'contour':
        data = get_random(xmin,xmax,ymin=ymin,ymax=ymax, ndims=2, grid=True, 
                         npoints=npoints, zmin=zmin,zmax=zmax, function=rng.uniform)#, rng=rng) # {'x':x, 'y':y, 'z':grid}
        xs = data['x']; ys = data['y']
        colors = data['z']
        return xs,ys,colors


########################################################################
############################# LINEAR ############################
#######################################################################


def get_linear(x,y=[],z=[],h=[],
               ndims=1,
                    a1=(-1,1), a2=(-1,1), a3=(-1,1), a4=(-1,1), # mx + a
                    m1=(-1,1), m2=(-1,1), m3=(-1,1), m4=(-1,1), # mx + a
                    noise1=(0,1), noise2=None,noise3=None, noise4=None,
               npoints=10,grid=False,
              function=np.random.uniform, rng=np.random):
    """
    a1-a4 : the "a's" in mx + a, will be randomly selected from range
    m1-m4 : the "m's" in mx + a, will be randomly selected from range
    noise1-noise4 : noise as a % of calculated "y", will be randomly selected from range
    """
    if ndims == 1:
        a = function(a1[0],a1[1])
        m = function(m1[0],m1[1])
        y = m*x + a
        # now add noise --> I think maybe multiply?
        noise_level = function(noise1[0],noise1[1])
        noise = rng.normal(0,1,npoints)*noise_level
        y = y*(1+noise)
        data = {'m':m, 'a':a, 'noise level':noise_level}
        return y, data
    if ndims == 2:
        if not grid:
            a11 = function(a1[0],a1[1])
            m11 = function(m1[0],m1[1])
            a22 = function(a2[0],a2[1])
            m22 = function(m2[0],m2[1])
            #noise_level1 = function(noise1[0],noise1[1])
#            if len(x.shape)>1 and len(y.shape)>1: # have 2d x/y
            noise_level1 = function(noise1[0],noise1[1])
            #print('noise level shape', noise_level1)
#            elif len(x) == len(y):
#                noise_level1 = 
                
            noise1 = rng.normal(0,1,npoints[0])*noise_level1
            #print('noise1 shape', noise1.shape)
            if noise2 is not None: # different noise in different directions
                noise_level2 = function(noise2[0],noise2[1])
                noise2 = rng.normal(0,1,npoints[1])*noise_level2
                z = (m11*x + a11)*(1+noise1) + (m22*y + a22)*(1+noise2)
            else:
                if len(x) == len(y):
                    noise1 = rng.normal(0,1,npoints[0])*noise_level1
                else:
                    noise1 = rng.normal(0,1,npoints)*noise_level1
                    
                #print('noise1 shape here', noise1.shape)
                z = (m11*x + a11 + m22*y + a22)*(1+noise1)

            #print('z shape', z.shape)
                
            data = {'m1':m11, 'a1':a11, 
                    'm2':m22, 'a2':a22, 
                   'noise level 1':noise_level1}
            if noise2 is not None: 
                data['noise level 2'] = noise_level2
            return z, data
        else:
            a11 = function(a1[0],a1[1])
            m11 = function(m1[0],m1[1])
            a22 = function(a2[0],a2[1])
            m22 = function(m2[0],m2[1])
            noise_level1 = function(noise1[0],noise1[1],len(x))
            grid = np.zeros([len(x),len(y)])
            # repeat x/y
            xr = np.repeat(x[:,np.newaxis], len(y), axis=1).T
            yr = np.repeat(y[:,np.newaxis], len(x), axis=1)
            if noise2 is not None:
                noise_level2 = function(noise2[0],noise2[1],len(y))
                nxr = np.repeat(noise_level1[:,np.newaxis], len(y), axis=1).T
                nyr = np.repeat(noise_level2[:,np.newaxis], len(x), axis=1)
                grid = (m11*xr + a11)*(1+nxr) + (m22*yr + a22)*(1+nyr)
            else:
                noise_level1 = function(noise1[0],noise1[1],npoints)
                #print('shape1:', noise_level1.shape)
                noise1 = rng.normal(0,1,npoints)*noise_level1
                grid = (m11*xr + a11 + m22*yr + a22)*(1+noise1.T)
                
            data = {'m1':m11, 'a1':a11, 
                    'm2':m22, 'a2':a22, 
                   'noise level 1':noise_level1}
            if noise2 is not None:
                   data['noise level 2'] = noise_level2
            zout = {'x':x, 'y':y, 'z':grid}
            return zout, data



def get_linear_data(plot_type, dist_params, 
                    xmin,xmax,ymin=0,ymax=1,zmin=0,zmax=0,
                    prob_same_x=0.5, nlines=1, npoints=1,
                   cmin=0, cmax=1, 
                   function=np.random.uniform, rng=np.random):

    """
    npoints : can be tuple if multi dimension
    """
    #print('in get_linear_data:', dist_params)
    # do we have all the same x for all points?
    if plot_type == 'line':
        p = rng.uniform(0,1)
        xs = []
        if p <= prob_same_x: # same x for all y
            x = function(low=xmin, high=xmax, size=npoints) # x-values
            x = np.sort(x)
            # repeat for all
            for i in range(nlines):
                xs.append(x)
        else: # different
            for i in range(nlines):
                x = function(low=xmin, high=xmax, size=npoints) # x-values
                x = np.sort(x)
                xs.append(x)
            
        ys = []
        data_line = {}
        for i in range(nlines):
            #y = get_random(ymin[i],ymax[i],ndims=1,npoints=npoints)
            y, data = get_linear(xs[i],ndims=1,npoints=npoints,
                          a1=dist_params['intersect'],
                          m1=dist_params['slope'],
                          noise1=dist_params['noise'], function=rng.uniform)
            ##y = data['y']
            ys.append(y)
            data_line['line'+str(i)] = data.copy()
        return xs,ys, data_line
    elif plot_type == 'scatter':
        # x/y
        xs = get_random(xmin,xmax,ndims=1,npoints=npoints, function=rng.uniform)#, rng=rng) # this will be random still
        ys, data_points = get_linear(xs,ndims=1,npoints=npoints,
                      a1=dist_params['intersect'],
                      m1=dist_params['slope'],
                      noise1=dist_params['noise'], function=rng.uniform)    
        # colors linear?
        if rng.uniform(0,1) <= dist_params['color noise prob']:
            colors, data_color = get_linear(xs,ys,ndims=2, 
                               npoints=(npoints,npoints),
                      a1=dist_params['intersect'],
                      m1=dist_params['slope'],
                      noise1=dist_params['noise'], rng=rng, function=rng.uniform)#,  
                      # a2=dist_params['intersect'],
                      # m2=dist_params['slope'],
                      # noise2=dist_params['noise'])  
            # colors is now 2D at each combo of x/y
            data_color['type'] = 'linear'
        else:
            colors = get_random(cmin,cmax,ndims=1,npoints=npoints, function=rng.uniform)#, rng=rng)
            data_color = {'type':'random'}

        #ys = get_random(ymin,ymax,ndims=1,npoints=npoints)
        #colors = get_random(cmin,cmax,ndims=1,npoints=npoints)
        # is color linear?
        data = {'points':data_points, 'colors':data_color}
        return xs,ys,colors, data
    elif plot_type == 'histogram': # I feel like this doesn't make too 
                                   # much sense for histograms, but lets just do it
        x = get_random(xmin,xmax,ndims=1,npoints=npoints, function=rng.uniform)#, rng=rng) 
        y, data = get_linear(x,ndims=1,npoints=npoints,
                      a1=dist_params['intersect'],
                      m1=dist_params['slope'],
                      noise1=dist_params['noise'], rng=rng, function=rng.uniform)
        return y, data
    elif plot_type == 'contour':
        xs = get_random(xmin,xmax,ndims=1,npoints=npoints[0], function=rng.uniform)#, rng=rng) # this will be random still
        xs = np.sort(xs)
        ys = get_random(xmin,xmax,ndims=1,npoints=npoints[1], function=rng.uniform)#, rng=rng) # this will be random still
        ys = np.sort(ys)
        data, data_params = get_linear(xs,ys,ndims=2, 
                               npoints=npoints,
                      a1=dist_params['intersect'],
                      m1=dist_params['slope'],
                      noise1=dist_params['noise'],  
                      # a2=dist_params['intersect'],
                      # m2=dist_params['slope'],
                      # noise2=dist_params['noise'],
                                      grid=True, rng=rng, function=rng.uniform)

        xs = data['x']; ys = data['y']
        colors = data['z']
        return xs,ys,colors,data_params



########################################################################
############################# GMM (in progress!) ############################
#######################################################################


# nclusters = 3
# cluster_std = ([1,0.05],
#                [1,1],
#                [2,2])
# nsamples = 500

from sklearn.datasets import make_blobs
from scipy.stats import binned_statistic_2d

def get_gmm(xmin,xmax,ymin=0,ymax=1,zmin=0,zmax=1,
            cmin=0,cmax=1, ndims=1, 
            nclusters = {'min':1,'max':10}, 
            cluster_std = {'min':0.01, 'max':1.0},
            nsamples = {'min':10,'max':1000},
            noise = {'min':0, 'max':1.0},
            grid=False,
           function=np.random.uniform, 
           small_data_params = True, 
           down_sample_max=None, fit_to_bounds = True,
            min_points=5, iloop_max = 8, max_sample_size = 1000000, 
            seed = None, verbose=False, rng=np.random):

    """
    small_data_params : won't save X array and y_true for contour plots (big stuffs)
    seed : set seed to a number to keep things consitent for debugging
    """

    #seed = 42
    #rng.seed(seed=seed)

    if type(nsamples) == type({}): # will pull randomly
        if nsamples['min'] == nsamples['max']:
            nsamples1 = nsamples['min']
        elif rng == np.random:
            nsamples1 = rng.randint(nsamples['min'],nsamples['max'])
        else:
            nsamples1 = rng.integers(nsamples['min'],nsamples['max'])
        nsamples_min = min(nsamples['min'],min_points)
    elif type(nsamples) == type([]) or type(nsamples) == type(()):
        nsamples1 = nsamples[0]
        nsamples_min=min(nsamples[0],min_points)
    else:
        nsamples1 = nsamples # if fixed
        nsamples_min = min(nsamples,min_points)
    # number of clusters
    if nclusters['min'] != nclusters['max']:
        if rng == np.random:
            nclusters1 = rng.randint(nclusters['min'],nclusters['max'])
        else:
            nclusters1 = rng.integers(nclusters['min'],nclusters['max'])
    else: # same
        nclusters1 = nclusters['min']
    if ndims > 1:
        cluster_std1 = rng.uniform(cluster_std['min'],cluster_std['max'], (nclusters1,ndims))
        # power
        #print('power:', cluster_std1)
        cluster_std1 = np.power(10,cluster_std1)
        #print('after power:', cluster_std1)
        #cluster_std1 *= (xmax-xmin)
    else:
        #print('ding ding!')
        cluster_std1 = rng.uniform(cluster_std['min'],cluster_std['max'], nclusters1)
        cluster_std1 = np.power(10,cluster_std1)
        cluster_std1 *= (xmax-xmin)

    #print(cluster_std1)
    #print('nsamples:', nsamples1)
        
    data_params = {'nsamples':nsamples1, 'nclusters':nclusters1}#,
                  #'cluster_std':cluster_std1}
    # moving for consistancy?
    centers = np.zeros((nclusters1,ndims))
    noise_level = function(noise['min'],noise['max'])

    # n_features = n_dim
    # centers : int or array-like of shape (n_centers, n_features), default=None
    #    The number of centers to generate, or the fixed center locations.
    # center_box : tuple of float (min, max), default=(-10.0, 10.0)
    if ndims == 1: # along a line 
        #print('xmin,xmax', xmin,xmax)
        #print('nclusters1', nclusters1)
        #centers_x = rng.uniform(xmin,xmax,(nclusters1,2))
        centers_x = rng.uniform(xmin,xmax,nclusters1).reshape(-1, 1)
        # for reproducable random state
        random_state = rng.bit_generator.state['state']['state']%(2**32 - 1)
        #print('random state 1:', random_state)
        X, y_true,centers_ret = make_blobs(n_samples=nsamples1, n_features=1,
                               cluster_std=cluster_std1, centers=centers_x,
                              center_box=(xmin,xmax),
                                      return_centers=True, 
                                      random_state=random_state)
        #**HERE** maybe we need an upsampling factor again
        # collapse
        #X = np.sum(X, axis=1)
        # labeling starts at 0
        y_true += 1
        
        #noise1 = rng.normal(0,1,nsamples1)*noise_level*(xmax-xmin)
        #print('distribution utils - noise_level, nsamples, ndims', noise_level, nsamples,ndims)
        noise1 = rng.normal(loc=0,
                                scale=noise_level/2, # the 1/2 is just a sort of random scalier
                                size=(nsamples1,ndims))#*noise_level  
        shifts = noise1*(xmax-xmin)
        Xout = X.flatten() + shifts.flatten()  
        # print('Xflatten =', X.shape)
        # print('shifts', shifts.shape) 
        # print('Xout:', Xout.shape)
        # print('xmin,xmax', xmin,xmax)
        #noise1[noise1<0] = 0.0 # allow for negatives
        # multiply
        #Xout = X.flatten()*(1+noise1.flatten())
        #shifts = noise1*(ma-mi)
        #Xout = X.flatten() + noise1
        # drop outside
        if fit_to_bounds:
            mask = (Xout > xmax) | (Xout < xmin)
            #print('mask', mask.shape)
            #print('x,y before:', Xout.shape, y_true.shape)
            y_true_out = y_true.copy()[~mask]
            Xout = Xout[~mask]
            #print('x,y after:', Xout.shape, y_true.shape)

        if not small_data_params:
            data_params['X'] = X
            data_params['Xout'] = Xout
            data_params['labels'] = y_true
        data_params['centers'] = centers_x
        data_params['cluster_std'] = cluster_std1
        data_params['noise level'] = noise_level
        
        return Xout, data_params 
    elif ndims > 1: # multi-d
        if ndims > 1: # 2
            #mi = np.min([xmin,ymin])
            mi = np.array([xmin,ymin])
            #ma = np.max([xmax,ymax])
            ma = np.array([xmax,ymax])
        if ndims > 2:
            #mi = np.min([mi,zmin])
            #ma = np.max([ma,zmax])
            #pass
            mi = np.array([xmin,ymin,zmin])
            ma = np.array([xmax,ymax,zmax])
        if ndims > 3:
            print('ndims > 3 not supported!')
            import sys; sys.exit()

        #print('mi,ma:', mi,ma)
        #print('xmin,xmax,ymin,ymax:',xmin,xmax, ymin,ymax)
        y_true_out = []
        isamples_mul = 0
        maxReached = True
        #print('HERE gmm_data 3')
        #print(nsamples_min, iloop_max, max_sample_size, nsamples1)
        if nsamples1 > max_sample_size:
            nsamples1 = max_sample_size
        # y_true_out 
        #print('nsamples_min', nsamples_min)
        #print('nsamples1', nsamples1)
        #print('max sample size', max_sample_size)
        while (len(y_true_out) < nsamples_min) or ((isamples_mul<=iloop_max) and (nsamples1 <= max_sample_size)): # loop until we get something
            #print("HERE")
            if isamples_mul > 1: # we are on a new loop
                if verbose: print('    on loop:', isamples_mul, nsamples1, len(y_true_out))
            isamples_mul += 1
            nsamples1 *= isamples_mul
            centers_x = rng.uniform(xmin,xmax,nclusters1)
            centers_y = rng.uniform(ymin,ymax,nclusters1)
            #centers = np.zeros((nclusters1,ndims))
            centers[:,0] = centers_x
            centers[:,1] = centers_y
            if ndims > 2:
                centers_z = rng.uniform(zmin,zmax,nclusters1)
                centers[:,2] = centers_z
            # print('centers',centers)
            # print("ma,mi", ma,mi)
            # print('std',cluster_std1*(ma-mi))
            random_state = rng.bit_generator.state['state']['state']%(2**32 - 1)
            #print('random state 2:', random_state)
            # print('nsamles1:', nsamples1)
            # print('nfeatures', ndims)
            # print('cluster std min/max', cluster_std1.min(), cluster_std1.max())
            # print('ma,mi', ma,mi)
            # print('centers min/max:', centers.min(), centers.max())
            X, y_true,centers_ret = make_blobs(n_samples=nsamples1, n_features=ndims,
                                   cluster_std=cluster_std1*(ma-mi), centers=centers,
                                  center_box=(mi,ma),
                                          return_centers=True, 
                                          random_state=random_state)
            #print('xmin/max', X.min(), X.max())
            
            noise_level = function(noise['min'],noise['max'])
            #print('noise_level:', noise_level)
            #noise1 = rng.normal(0,1,(nsamples1,ndims))*noise_level
            noise1 = rng.normal(loc=0,
                          scale=noise_level/2, # the 1/2 is just a scaler
                          size=(nsamples1,ndims))
            # starts at 0
            y_true += 1
                                        
            # multiply
            #Xout = X*(1+noise1)
            #**HERE** -- small shift?
            shifts = noise1*(ma-mi)
            Xout = X + shifts
            #print('xmin,ymin,xmax,ymax:', xmin,ymin,xmax,ymax)
            # drop outside
            #print('X:', X)
            #print('Xout:', Xout)
            mask = (Xout[:,0] > xmax) | (Xout[:,0] < xmin) | (Xout[:,1] > ymax) | (Xout[:,1] < ymin)
            Xout = Xout[~mask]
            y_true_out = y_true.copy()[~mask]
            mask = (X[:,0] > xmax) | (X[:,0] < xmin) | (X[:,1] > ymax) | (X[:,1] < ymin)
            #print('X before:', X.shape)
            X = X[~mask]
            #print('X after:', X.shape)
            y_true = y_true[~mask]
            if len(y_true_out) >= nsamples_min: maxReached = False
            # print('y_true, 1:', y_true)
            # print('y_true_out:', y_true_out)

        #print('len ytrue', len(y_true_out))
        #print('HERE gmm_data 4')
        if not maxReached: # we have maxed out! drop condition
            if verbose: print('    maxed out!')
            centers_x = rng.uniform(xmin,xmax,nclusters1)
            centers_y = rng.uniform(ymin,ymax,nclusters1)
            centers = np.zeros((nclusters1,ndims))
            centers[:,0] = centers_x
            centers[:,1] = centers_y
            if ndims > 2:
                centers_z = rng.uniform(zmin,zmax,nclusters1)
                centers[:,2] = centers_z
            #print('centers',centers)
            #print("ma,mi", ma,mi)
            #print('std',cluster_std1*(ma-mi))
            random_state = rng.bit_generator.state['state']['state']%(2**32 - 1)
            #print('random state 3:', random_state)
            #print('function:', function)
            #print('rng:', rng)
            X, y_true,centers_ret = make_blobs(n_samples=nsamples1, n_features=ndims,
                                   cluster_std=cluster_std1*(ma-mi), centers=centers,
                                  center_box=(mi,ma),
                                          return_centers=True, 
                                          random_state=random_state)
            
            noise_level = function(noise['min'],noise['max'])
            noise1 = rng.normal(0,1,(nsamples1,ndims))*noise_level
            # starts at 0
            y_true += 1
                                        
            # multiply
            Xout = X*(1+noise1)
            y_true_out = y_true.copy()#[~mask]


        #print('HERE gmm_data 5')
        if not small_data_params:
            data_params['X'] = X
            #data_params['Xout'] = Xout
            #data_params['y_true_out'] = y_true_out
            data_params['labels'] = y_true
        data_params['centers'] = centers
        data_params['cluster_std'] = cluster_std1
        data_params['noise level'] = noise_level
        #print('HERE gmm_data 6')

        if not grid:
            # colors
            #print(nclusters1)
            #print(y_true_out)
            
            if nclusters1 > 1 and np.max(y_true_out) != np.min(y_true_out):
                colors = (y_true_out-np.min(y_true_out))/(np.max(y_true_out)-np.min(y_true_out))*(cmax-cmin)+cmin
            else:
                colors = (y_true_out)*(cmax-cmin)+cmin # ytrue = 1 now
            # noise here as well
            noise2 = rng.normal(0,1,len(y_true_out))*noise_level
            colors = colors*(1+noise2)

            # downsample if needed
            if down_sample_max is not None:
                if len(colors) > down_sample_max:
                    ints = rng.choice(np.arange(0,len(colors)),
                                            size=down_sample_max,
                                            replace=False)
                    Xout = Xout[ints,:]
                    colors = colors[ints]
            return Xout, colors, data_params
        else: # we have more work to do (contours)
            #print('HERE gmm_data 7')
            # just the shape
            #y_true[y_true>0] = 1
            y_true[:] = 1
            #print('HERE gmm_data 7.1')
            #y_true = y_true[~mask]
            nbinsx,nbinsy = nsamples[1],nsamples[2]
            
            binx = np.linspace(xmin,xmax, nbinsx)
            biny = np.linspace(ymin,ymax, nbinsy)

            #print("HERE gmm_data 7.1.1")
            #print('y_true:', y_true)
                
            ret = binned_statistic_2d(X[:,1], X[:,0], y_true, 
                                    'sum', bins=[biny,binx], 
                expand_binnumbers=True)
            #print("HERE gmm_data 7.2")
            
            colors = ret.statistic
            # renorm
            if np.max(colors) != np.min(colors):
                div1 = np.max(colors)-np.min(colors)
            else:
                div1 = 1
            colors = (colors-np.min(colors))/div1*(cmax-cmin)+cmin
            # noise here as well
            noise2 = rng.normal(0,1,colors.shape)*noise_level
            colors = colors*(1+noise2)

            xs = (binx[:-1] + binx[1:]) / 2
            ys = (biny[:-1] + biny[1:]) / 2
            #print("HERE gmm_data 8")
            # print('xs:',xs)
            # print('ys:',ys)
            # print('colors:', colors)
            # print('data_params:', data_params)
            #print('shape(xs):', xs.shape, 'shape(colors):', colors.shape)

            return xs,ys, colors, data_params


def get_gmm_data(plot_type, dist_params,
                 xmin,xmax,ymin=0,ymax=1,zmin=0,zmax=0,
                    prob_same_x=0.5, nlines=1, npoints=1,
                   cmin=0, cmax=1, 
                   function=np.random.uniform, small_data_params = True, 
                   seed = None, verbose=False, rng=np.random):
    """
    npoints : can be tuple if multi dimension
    seed : set seed to number for randomization
    """

    #seed = 42
    #rng.seed(seed)
    #print('npoints here in get_gmm_data', npoints)
        
    if plot_type == 'line':
        p = rng.uniform(0,1)
        xs = []
        isSameX = False
        if p <= prob_same_x: # same x for all y
            x = function(low=xmin, high=xmax, size=npoints) # x-values
            x = np.sort(x)
            # repeat for all
            for i in range(nlines):
                xs.append(x)
            isSameX = True
        else: # different
            for i in range(nlines):
                x = function(low=xmin, high=xmax, size=npoints) # x-values
                x = np.sort(x)
                xs.append(x)

        # histograms actually but as line plot?
        isHisto = False
        if rng.uniform(0,1) <= dist_params['histogram as line']['prob']:
            isHisto = True
        ys = []
        data_params = {}
        for i in range(nlines):
            if not isHisto:
                y, data_params1 = get_gmm(ymin[i],ymax[i],
                                         ndims=1,
                                         #npoints=npoints,
                              nclusters=dist_params['nclusters'],
                              nsamples=len(xs[i]), # keep same # of x values
                              cluster_std=dist_params['cluster std'],
                                        noise=dist_params['noise'],
                                        function=function,
                                         small_data_params = small_data_params,
                                         fit_to_bounds = not isSameX, 
                                         verbose=verbose, rng=rng)
                #print('isSameX', isSameX)
                if not isSameX and len(y) != len(xs[i]):
                    #print('hey')
                    inds = rng.choice(np.arange(0,len(xs[i])),len(y),replace=False)
                    inds = np.sort(inds)
                    xs[i] = xs[i][inds]
            else:
                ypoints, data_params1 = get_gmm(np.min(xs[i]),np.max(xs[i]),
                                             ndims=1,
                                  nclusters=dist_params['nclusters'],
                                  nsamples=len(xs[i])*dist_params['histogram as line']['factor'],
                                  cluster_std=dist_params['cluster std'],
                                            noise=dist_params['noise'],
                                            function=function,
                                         small_data_params = small_data_params,
                                         verbose=verbose, rng=rng)
                # repeat from centers to edges
                #bins = xs[i].copy()
                #rol
                y,bin_edges = np.histogram(ypoints, bins=xs[i]) 
                xs[i] = (bin_edges[:-1] + bin_edges[1:]) / 2 # update bins
                # rescale
                y = y.astype('float')
                #print('ymin,ymax, ymin[i],ymax[i]', np.min(y), np.max(y), ymax[i], ymin[i])
                y = (y-np.min(y))/(np.max(y)-np.min(y))*(float(ymax[i])-float(ymin[i]))+ymin[i]
                #print((float(ymax[i])-float(ymin[i]))+ymin[i])

            ys.append(y)
            data_params['line'+str(i)] = data_params1.copy()
        return xs,ys, data_params
    elif plot_type == 'scatter':
        # x/y
        npoints = rng.uniform(dist_params['upsample factor log']['min'], 
                                    dist_params['upsample factor log']['max'])
        npoints = int(np.max(npoints+1)*round(np.power(10,npoints)))
        #print('now npoints=',npoints)

        data_params_out = {'points':"","colors":''}
        X, colors_dist, data_params = get_gmm(xmin,xmax,ymin=ymin,ymax=ymax,
                                     ndims=2,
                          nclusters=dist_params['nclusters'],
                          nsamples=npoints,#dist_params['nsamples'], # keep same # of x values
                          cluster_std=dist_params['cluster std'],
                                    noise=dist_params['noise'],
                                    function=function,
                                                 cmin=cmin,
                                                 cmax=cmax,
                                             down_sample_max=dist_params['max points'],
                                         small_data_params = small_data_params,
                                         verbose=verbose, rng=rng, 
                                         iloop_max = -1 # this one is so that it doesn't loop a ton
                                         )  
        xs = X[:,0]
        ys = X[:,1]
        # colors linear?
        if rng.uniform(0,1) <= dist_params['color noise prob']: 
            colors = colors_dist
            data_params_out['colors'] = {'type':'gmm, by cluster'}
        else: #otherwise, make random
            colors = get_random(cmin,cmax,ndims=1,npoints=len(colors_dist), function=rng.uniform)#, rng=rng)
            data_params_out['colors'] = {'type':'gmm, random'}

        data_params_out['points'] = data_params.copy()

        return xs,ys,colors, data_params_out
    elif plot_type == 'histogram': # I feel like this doesn't make too 
                                   # much sense for histograms, but lets just do it
        y, data_params = get_gmm(xmin,xmax,
                                     ndims=1,
                          nclusters=dist_params['nclusters'],
                          nsamples=dist_params['nsamples'], # keep same # of x values
                          cluster_std=dist_params['cluster std'],
                                    noise=dist_params['noise'],
                                    function=function,
                                         small_data_params = small_data_params,verbose=verbose,
                                         rng=rng)

        return y, data_params
    elif plot_type == 'contour':
        # upsample the number of points per grid
        nx = npoints[0] # silly reformatting stuffs
        ny = npoints[1]
        npoints = rng.uniform(dist_params['upsample factor log']['min'], 
                                    dist_params['upsample factor log']['max'])
        npoints = int(np.max(npoints+1)*round(np.power(10,npoints)))

        xs,ys, colors, data_params = get_gmm(xmin,xmax,ymin=ymin,ymax=ymax,
                                     ndims=2,
                          nclusters=dist_params['nclusters'],
                          nsamples=(npoints,nx,ny), # keep same # of x values
                          cluster_std=dist_params['cluster std'],
                                    noise=dist_params['noise'],
                                    function=function,
                                                 cmin=cmin,
                                                 cmax=cmax, 
                                        grid=True,
                                         small_data_params = small_data_params, 
                                         seed = seed, verbose=verbose, rng=rng)  

        return xs,ys,colors,data_params
    else:
        print('[ERROR]: No such plot type for:', plot_type)
        
        return xs,ys,colors,data_params


##########################################
########## Image of the Sky ##############
###### (right now only for contours!) ####
##########################################
# JPN -- support for scatters too?
# JPN -- what about histograms?

# xs,ys,colors, data_params = get_sky_image_data(npoints=(nx,ny),
#                         cmin=cmin, cmax=cmax, rng=rng)

#from glob import glob
import pickle
import time
#import numpy as np
#from copy import deepcopy
#import matplotlib.pyplot as plt
import operator

# for parsing
#from astroquery.simbad import Simbad
import time
from astroquery.skyview import SkyView
import os

from astropy.wcs import WCS
from astropy.io import fits
from astropy.utils.data import get_pkg_data_filename

import pandas as pd

# best guesses for how surveys match up with wavelength tags
surveys_by_wl = {'O':['Optical:SDSS', 'OtherOptical', 'Optical:DSS class=', 'Allbands:GOODS/HDF/CDF'], 
                 # repeat IR for other far ir/near ir/etc
                 'I':['IR:IRAS', 'IR:2MASS class=', 'IR:UKIDSS class=', 'IR:WISE class=', 'IR:AKARI class=', 'IR:Planck', 'IR:WMAP&COBE'], 
                 'F':['IR:IRAS', 'IR:2MASS class=', 'IR:UKIDSS class=', 'IR:WISE class=', 'IR:AKARI class=', 'IR:Planck', 'IR:WMAP&COBE'], 
                 'M':['IR:IRAS', 'IR:2MASS class=', 'IR:UKIDSS class=', 'IR:WISE class=', 'IR:AKARI class=', 'IR:Planck', 'IR:WMAP&COBE'], 
                 'N':['IR:IRAS', 'IR:2MASS class=', 'IR:UKIDSS class=', 'IR:WISE class=', 'IR:AKARI class=', 'IR:Planck', 'IR:WMAP&COBE'], 
                 # out of IR repeats
                 'X':['HardX-ray', 'X-ray:SwiftBAT',  'SoftX-ray class=', 'ROSATw/sources class=', 'ROSATDiffuse class='],
                 'G':['GammaRay'],
                 'R':['Radio:GHz', 'Radio:MHz class=', 'Radio:GLEAM class='],
                 'U':['UV', 'SwiftUVOT'],
                 # repeats for "m" and "s"
                 'm':['Radio:GHz', 'Radio:MHz class=', 'Radio:GLEAM class='],
                 's':['IR:IRAS', 'IR:2MASS class=', 'IR:UKIDSS class=', 'IR:WISE class=', 'IR:AKARI class=', 'IR:Planck', 'IR:WMAP&COBE'] 
                 }

# other guesses
# 'F' 'G' 'I' 'M' 'N' 'O' 'R' 'U' 'X' 'm' 's'

# from docs above
# survey_keys = {'R':['Radio:GHz', 'Radio:MHz', 'Radio:GLEAM'], 
#                'I':['IR:IRAS', 'IR:2MASS', 'IR:UKIDSS', 'IR:WISE', 'IR:AKARI', 'IR:Planck', 'IR:WMAP&COBE'], 
#                'V':['Optical:DSS', 'Optical:SDSS'], 
#                'U':['UV', 'SwiftUVOT'], 
#                'X':['HardX-ray', 'X-ray:SwiftBAT', 'SoftX-ray class', 'ROSATw/sources','ROSATDiffuse'], 
#                'G':['GammaRay']
#                }

## 'F' 'G' 'I' 'M' 'N' 'O' 'R' 'U' 'X' 'm' 's'
# I think "F" means Far IR -- get some IRAS
# I think "M" means Mid-IR -- IRAS again
# N I think means near-IR (RAFGL)
# m -- maybe millimeter (like Radio)
# s -- TeV? actually might be submillimeter, like Far IR and Microwave bands

from .plot_classes_utils import ImageOfSky
import gc

# try to fix headers
def fix_headers(img):
    #try:
    header = img.header
    new_cards = []
    for card in header.cards:
        # Clean the value
        value = card.value
        if isinstance(value, str):
            value = value.replace('\t', '')
        
        # Clean the comment
        comment = card.comment
        if comment:
            comment = comment.replace('\t', '')
        
        # Create a new card with cleaned values
        new_cards.append(fits.Card(card.keyword, value, comment))
    img.header.clear()
    for card in new_cards:
        img.header.append(card)
    #img.header = header 
    return img


import warnings
import logging
# Suppress only the download progress messages
logging.getLogger('astropy.utils.data').setLevel('ERROR')
from astropy.utils.data import conf
import time
conf.show_progress = False  # This should disable the download progress messages
from sys import path
from ..paths import REPO_ROOT
if REPO_ROOT not in path:
    path.append(REPO_ROOT)  # to get the bundled yt/ shim, whatever the cwd is
from yt.utilities.parallel_tools.parallel_analysis_interface import communication_system

_object_wavelengths_cache = {}
_missing_list_cache = {}

def get_images_survey(surveys_wl, object_id, save_img_dir, pdfname, missing_list,
                      missing_list_file,
                      verbose=True, sleep_time = 2, overwrite = False, 
                      pick_random_survey = True, rng=np.random, 
                      height=300, width=300, debug=False, showProgress=False, 
                      running_in_parallel=False, comm=None):
    pdfs = []; objs = []; surveys = []; reasons = []
    err = False
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=ResourceWarning)
        for s in surveys_wl:
            if verbose: print('  Main survey:', s)
            try:
                sub_surveys_wl = SkyView.survey_dict[s]
            except Exception as e:
                if verbose:
                    print(str(e))
                    print('survey tried:', s)
                return None, err
            if pick_random_survey:
                sub_surveys_wl = [rng.choice(sub_surveys_wl)]
            # get all images associated with this survey
            filenames = []
            for ss in sub_surveys_wl:
                subdf = missing_list[(missing_list['object']==object_id) & (missing_list['survey']==ss) & (missing_list['pdf']==pdfname) ]
                if len(subdf) > 0:
                    if verbose: print('   missing, skipping:', ss)
                    continue
                if verbose: print('    sub survey:', ss)
                try:
                    img_list = SkyView.get_images(position=object_id, survey = ss, 
                                                pixels=(width,height), show_progress=showProgress)
                except:
                    if verbose: print('      no survey for:', ss)
                    # add to list
                    img_list = []
                    pdfs.append(pdfname); objs.append(object_id); surveys.append(ss)
                    reasons.append('no survey')
                    continue
                if len(img_list) == 0:
                    if verbose:
                        print('      no images')
                    pdfs.append(pdfname); objs.append(object_id); surveys.append(ss)
                    reasons.append('no images')
                alreadyHave = False
                for iimg, img in enumerate(img_list):
                    filename = 'image_' + pdfname + '_OBJ_' + object_id.replace(' ', '_').replace('/','-') + \
                                    '_SURVEY_' + str(ss).replace(' ','_').replace('/','-') + \
                                    '_height' + str(height) + '_width' + str(width) + \
                                        '_NUM_' + str(iimg).zfill(4) + '.fits'
                    filenames.append(filename)
                    if os.path.exists(save_img_dir + filename) and not overwrite:
                        if verbose:
                            print('already have:', filename)
                        alreadyHave = True
                        img.close()  # Claude -- ADD THIS - close even if skipping
                        del img
                        continue
                    if verbose: print('      on image number:', iimg)
                    try:
                        img.writeto(save_img_dir + filename)
                        img.close()  # Claude -- ADD THIS - close after successful write
                    except Exception as e:
                        if 'Unprintable string'.lower() in str(e).lower():
                            # try to fix header
                            try:
                                imgOut = fix_headers(img[0])
                                imgOut.writeto(save_img_dir + filename)
                                imgOut.close()  # Claude -- ADD THIS
                                del imgOut
                                gc.collect()
                            except Exception as e2:
                                pdfs.append(pdfname); objs.append(object_id); surveys.append(ss)
                                reasons.append('exception')
                                if verbose:
                                    print('          cannot write image (2):', filename)
                                    print('          ' + str(e2))
                                if debug:
                                    err = True
                                    img.close()  # Claude -- ADD THIS - close before returning
                                    del img
                                    del img_list
                                    return img, err
                        else:
                            pdfs.append(pdfname); objs.append(object_id); surveys.append(ss)
                            reasons.append('exception')
                            if verbose:
                                print('          cannot write image:', filename)
                                print('          ' + str(e))
                        img.close()  # Claude -- ADD THIS - close after exception
                        del img
                if not alreadyHave: time.sleep(sleep_time)

        # if running_in_parallel:
        #     print('IN PAR 2')
        if len(pdfs) > 0: # update list
            missing_addon = pd.DataFrame({'object':objs,
                                          'survey':surveys,
                                          'pdf':pdfs, 'reason':reasons})
            if not running_in_parallel:
                #print('[WARNING]: writing of missing list is not parallizable!!')
                missing_out = pd.concat([missing_list,missing_addon],ignore_index=True)
                missing_out.to_csv(missing_list_file, index=False)
            else: # in parallel
                #print('IN PARALLEL SAVE IMG')
                #missing_file_dir = "/".join(missing_list_file.split('/')[:-1]) + '/' # get dir
                missing_list_file_out = missing_list_file.removesuffix('.csv')
                missing_out = pd.concat([missing_list,missing_addon],ignore_index=True)
                # write other to file with timestamp
                t = str(round(time.time()*1e5)) + '_c' + str(comm.rank)
                missing_addon.to_csv(missing_list_file_out + t + '.csv', index=False)
            # update in-memory cache so future calls skip re-reading disk
            _missing_list_cache[missing_list_file] = missing_out
    
        del img_list
        gc.collect()
        # choose an image
        if len(filenames) > 0:
            img_pick = rng.choice(filenames)
            return img_pick, err
        else:
            return None, err
        

from copy import deepcopy


def survey_keys_test(survey_keys, surveys_by_wl, verbose=False):
    # test for survey keys
    if survey_keys is not None:
        if survey_keys['key'] is not None:
            surveys = surveys_by_wl[survey_keys['key']]
        else:
            if verbose: print('survey_keys["key"] should come from:', list(surveys_by_wl.keys()))
            survey_keys = None
            return survey_keys
        
        if survey_keys['survey'] is not None:
            if survey_keys['survey'] in surveys:
                # final check
                return {'key':survey_keys['key'], 'survey':[survey_keys['survey']]}
            else: # not right survey
                return {'key':survey_keys['key'], 'survey':surveys_by_wl['key']}
        else:
            return {'key':survey_keys['key'], 'survey':surveys_by_wl['key']}
    else:
        return survey_keys




def find_obj(imgOfSky,object_wavelengths,surveys_by_wl,
             rng=np.random,
             verbose=False, survey_keys={'key':None, 'survey':None}):
    use_random_obj = False
    obj = {}
    # if none, then use random obj!
    if imgOfSky.obj is None:
        use_random_obj = True
        if verbose: print('  -- will use randomly selected sky image')
        return use_random_obj, obj
    
    # then, need to check for all params -- some OK to have, others no
    if not isinstance(imgOfSky.obj,dict):
        if verbose: print('  -- imgOfSky.obj is not directory, using randomly selected sky image')
        return True, obj
    
    all_objs = deepcopy(object_wavelengths)
    for k,v in imgOfSky.obj.items():
        if 'object' in k and v is not None: # subset to objects
            ao_tmp = []
            for o in all_objs:
                if v.replace(' ', '').lower() in o['object'].replace(' ', '').lower():
                    ao_tmp.append(o)
            all_objs = deepcopy(ao_tmp)
        elif 'wavelength' in k and v is not None: # subset to wavelengths
            ao_tmp = []
            for o in all_objs:
                if str(v) in str(o['wavelength']):
                    ao_tmp.append(o)
            all_objs = deepcopy(ao_tmp)
        elif 'pdf' in k and v is not None: # subset to pdf
            ao_tmp = []
            for o in all_objs:
                if str(v).lower().replace('.','').replace('_', '') in str(o['pdf'].replace('_','').lower()):
                    ao_tmp.append(o)
            all_objs = deepcopy(ao_tmp)
        elif 'itable' in k and v is not None: # subest to tables, probably generally don't want to do this
            ao_tmp = []
            for o in all_objs:
                if int(v) == int(o['itable']):
                    ao_tmp.append(o)
            all_objs = deepcopy(ao_tmp)

    # get survey keys
    survey_keys = survey_keys_test(survey_keys, 
                                   surveys_by_wl, 
                                   verbose=verbose)
    if survey_keys is None:
        pass
        # moving on!
    else:
        # see if we have this particular wavelength
        ao_tmp = []
        for o in all_objs:
            for sk in survey_keys['key']:
                if str(sk) in o['wavelength']:
                    if o not in ao_tmp:
                        ao_tmp.append(o)
        if len(ao_tmp) > 0:
            all_objs = deepcopy(ao_tmp)
        # also, update survey keys
        survey_keys = survey_keys['survey']

    if len(all_objs) == 0: # nothing!
        if verbose: print('  -- imgOfSky.obj has no exact match to input dir:', imgOfSky.obj, ', using random image of sky')
        return True, obj
    elif len(all_objs) != 1:
        if verbose: print('  -- selected object has multiples ('+str(len(all_objs))+' in number), will select from here')
        obj = rng.choice(all_objs)
        if isinstance(obj, list):
            obj = obj[0]
        return False, obj
    
    obj = all_objs[0]
    del all_objs
    gc.collect()
        
    return use_random_obj, obj, survey_keys


import gc
from glob import glob
from mpi4py import MPI
# JPN -- here you want function as rng.uniform when
_local_sky_files_cache = {}


def list_local_sky_images(query_imgs_dir, verbose=False):
    """
    Every .fits already downloaded into the astroquery cache.  Listed once per
    process -- the cache holds ~1e5 files, so this is not something to redo on
    every figure.
    """
    query_imgs_dir = os.path.expanduser(query_imgs_dir)
    if query_imgs_dir not in _local_sky_files_cache:
        try:
            files = [f for f in os.listdir(query_imgs_dir) if f.endswith('.fits')]
        except FileNotFoundError:
            files = []
        _local_sky_files_cache[query_imgs_dir] = np.array(sorted(files))
        if verbose:
            print('    local sky image cache:', len(files), 'files in', query_imgs_dir)
    return _local_sky_files_cache[query_imgs_dir]


def parse_sky_image_filename(filename):
    """
    Recover (pdf, object, survey) from a cached cutout's name, which
    get_images_survey built as

        image_<pdf>_OBJ_<object>_SURVEY_<survey>_height<H>_width<W>_NUM_<N>.fits

    The object and survey were written with ' ' -> '_' and '/' -> '-', so what
    comes back is the flattened form, not necessarily the original string.
    """
    stem = filename.removeprefix('image_').removesuffix('.fits')
    pdf, _, rest = stem.partition('_OBJ_')
    obj, _, rest = rest.partition('_SURVEY_')
    survey = rest.partition('_height')[0]
    return pdf, obj, survey


def pick_local_sky_image(query_imgs_dir, rng=np.random, verbose=False):
    """
    Choose a random already-downloaded cutout instead of querying SkyView.
    Returns (filename, obj, survey) shaped like the query path's results, so
    the metadata written into the figure json keeps the same fields.
    """
    files = list_local_sky_images(query_imgs_dir, verbose=verbose)
    if len(files) == 0:
        raise FileNotFoundError(
            'no .fits files in ' + str(query_imgs_dir) + ' -- "local only" needs a '
            'populated astroquery image cache (drop the flag to query SkyView)')
    filename = str(rng.choice(files))
    pdf, obj_name, survey = parse_sky_image_filename(filename)
    return filename, {'object': obj_name, 'pdf': pdf, 'wavelength': ''}, [survey]


def get_sky_image_data(plot_params,
                   cmin=0, cmax=1, 
                   verbose=False, rng=np.random, timer_pause=1.0, 
                   overwrite = False, pick_random_survey = False, 
                   height=300, width=300, warning_verbose=False, 
                   verbose_get_images = False,
                   **kwargs):
    """
    npoints : can be tuple if multi dimension
    timer_pause : if pulling from astroquery, how much of a pause to take
    height/width : the default resolution of the images returned (astroquery default is 300x300)
    """

    imgOfSky = ImageOfSky()
    for k,v in kwargs.items():
        if k in imgOfSky.__dict__: # in there
            setattr(imgOfSky, k, v)

    # get sky images list
    if verbose and warning_verbose:
        print("[WARNING]: loading of sky images not optimized! (distribution_utils/get_sky_image_data)")
    if imgOfSky.output_dir is None:
        output_dir = plot_params['distribution']['sky']['object wavelength table']
    else:
        output_dir = imgOfSky.output_dir
    #print(output_dir)
    if output_dir not in _object_wavelengths_cache:
        with open(output_dir,'rb') as f:
            _object_wavelengths_cache[output_dir] = pickle.load(f)
    object_wavelengths = _object_wavelengths_cache[output_dir]

    # test for parallel or serial
    comm = None
    comm = MPI.COMM_WORLD #communication_system.communicators[-1]
    running_in_parallel = False
    # Check if parallel
    if comm.size > 1:
        running_in_parallel = True
    # print('***** COMM INFO:')
    # print(comm)
    # print(comm.size)


    # # Check MPI directly
    # mpi_comm = MPI.COMM_WORLD
    # print('MPI COMM: mpi_comm', mpi_comm.size)

    # missing obj/surveys
    if imgOfSky.missing_list_file is None:
        missing_list_file = plot_params['distribution']['sky']['missing obj/surveys list']
        missing_list_file = os.path.expanduser(missing_list_file)
    else:
        missing_list_file = imgOfSky.missing_list_file

    if missing_list_file not in _missing_list_cache:
        if not running_in_parallel:
            #print("****** FLAGGED AS NOT IN PARALLEL")
            if not os.path.exists(missing_list_file): # make new one
                _missing_list_cache[missing_list_file] = pd.DataFrame({'object':[], 'survey':[], 'pdf':[], 'reason':[]})
                if verbose:
                    print('writing missing items file:', missing_list_file)
            else:
                try:
                    _missing_list_cache[missing_list_file] = pd.read_csv(missing_list_file)
                except Exception as e:
                    print('[ERROR]: opening missing_list file in distribution_utils/get_sky_image_data')
                    print(str(e))
                    import sys; sys.exit()
        else: # in parallel
            #print("******HERE 2 IN PARALLEL")
            if '.csv' in missing_list_file or '.json' in missing_list_file: # is a file type, let's not
                missing_file_dir = "/".join(missing_list_file.split('/')[:-1]) + '/'
                missing_files = glob(missing_file_dir + '*.csv')
                missing_list_loaded = pd.DataFrame({'object':[], 'survey':[], 'pdf':[], 'reason':[]})
                for mfile in missing_files:
                    mf1 = pd.read_csv(mfile)
                    missing_list_loaded = pd.concat([missing_list_loaded, mf1], ignore_index=True)
                _missing_list_cache[missing_list_file] = missing_list_loaded
    missing_list = _missing_list_cache[missing_list_file]                    

    # get image height/width
    if imgOfSky.height is None:
        height = plot_params['distribution']['sky']['image height']
    else:
        height = imgOfSky.height
    if imgOfSky.width is None:
        width = plot_params['distribution']['sky']['image width']
    else:
        width = imgOfSky.width

    if imgOfSky.survey is not None:
        survey_keys = imgOfSky.survey
    else:
        survey_keys = None
    if imgOfSky.obj is not None:
        use_random_obj, obj, survey_keys = find_obj(imgOfSky,
                                       object_wavelengths, surveys_by_wl,
             rng=np.random,
             verbose=verbose, survey_keys = survey_keys)
    else:
        use_random_obj = True
        
    if imgOfSky.query_images_dir is None:
        query_imgs_dir = plot_params['distribution']['sky']['query images dir']
    else:
        query_imgs_dir = imgOfSky.query_images_dir 

    # restrict to images already sitting in the astroquery cache?
    local_only = plot_params['distribution']['sky'].get('local only', False)
    if imgOfSky.local_only is not None:
        local_only = imgOfSky.local_only

    filename = None
    while filename is None:
        if local_only:
            # no network: pick one of the cutouts already on disk
            filename, obj, survey = pick_local_sky_image(query_imgs_dir, rng=rng,
                                                         verbose=verbose)
            if verbose:
                print('    object, survey, pdf (local):', obj['object'], survey, obj['pdf'])
        else:
            # grab random object
            # object, wavelength(s), pdf, itable
            if use_random_obj: # if not already selected, select it!
                obj = rng.choice(object_wavelengths)

            # if only wavelength is emtpy, just guess optical
            if obj['wavelength'] == '':
                survey_keys = ['Optical:DSS class='] #surveys_by_wl['O']
                if verbose_get_images:
                    print('No wavelength, picking optical ( wavelength empty )')
            else:
                if survey_keys is None:
                    survey_keys = surveys_by_wl[obj['wavelength']]

            # pick random survey
            if not pick_random_survey:
                survey = [rng.choice(survey_keys)]
                if verbose_get_images: print('picking random survey:', survey)
            else:
                survey = survey_keys

            if verbose:
                print('    object, survey, pdf:', obj['object'], survey, obj['pdf'])

            # try all surveys
            isurvey = 0
            n_surveys = len(survey_keys)
            while filename is None and isurvey < n_surveys:
                if verbose_get_images: print(' on survey', survey, '(', isurvey+1, 'of', n_surveys, ')')
                filename, err = get_images_survey(survey, obj['object'], 
                                query_imgs_dir, 
                                obj['pdf'], missing_list, missing_list_file,
                            verbose=verbose_get_images, sleep_time = timer_pause, overwrite = overwrite, 
                            pick_random_survey = pick_random_survey, rng=rng, 
                            height=height, width=width, running_in_parallel=running_in_parallel, 
                            comm=comm)
                # try different survey if no file
                if filename is None:
                    survey = [survey_keys[isurvey]]
                    isurvey += 1

        # try to open
        if filename is not None:
            try:
                if verbose:
                    print('    will try to load fits file:', query_imgs_dir+filename)
                filename2 = query_imgs_dir+filename
                # add a with?
                with open(filename2,'rb') as ff:
                    hdu = fits.open(ff, output_verify='fix')[0]
                    #hdu = fits.open(ff, output_verify='fix', verify='fix')[0]
                    wcs = WCS(hdu.header)
                    img_data = hdu.data
                    # apply some "fixes" for large images/out of bounds data
                    img_data = np.nan_to_num(img_data, nan=0.0, posinf=0.0, neginf=0.0)
                    # downsample if need to
                    if img_data.shape[0] > 4000 or img_data.shape[1] > 4000:
                        # Quick downsample by binning
                        factor = 2
                        img_data = img_data[::factor, ::factor]
                        if verbose: print('    had to downsample image, new size=', img_data.shape)
            except Exception as e:
                if verbose:
                    print('[ERROR]: Issue opening fits file - ', str(e))
                filename = None

        # also check if only NaN's
        if filename is not None:
            if len(img_data[~np.isnan(img_data)]) == 0:
                if verbose:
                    print('[WARNING]: img_data is all NaNs for file:', filename)
                filename = None

    # # get renorm
    # norm = simple_norm(img_data, image_renorm, percent=99)

    data_params = {}
    data_params['WCS'] = wcs
    # also save simple string version
    data_params['WCS header string'] = wcs.to_header_string()
    data_params['sky image params'] = {'filename':filename, 
                                       'header':hdu.header,
                                       'object':obj['object'], 
                                       'pdf':obj['pdf'],
                                       'survey':survey, 
                                       'original img size':img_data.shape}

    # xs,ys are just the pixel coords
    xs = np.arange(0,img_data.shape[1])
    ys = np.arange(0,img_data.shape[0])

    del hdu, imgOfSky
    gc.collect()

    #return xs,ys,colors,data_params
    return xs, ys, img_data, data_params
        
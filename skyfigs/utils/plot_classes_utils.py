class Histogram():
    def __init__(self):
        self.rwidth = None
        self.elinewidth = None
        self.orientation = None
        self.axis = None
        self.lthick = None
        self.linestyle = None
        self.linecolor = None
        self.barcolor = None
        self.nbins = None
        self.es = None
        self.hasErr = None

class Line():
    def __init__(self):
        self.hasMarker = None
        self.elinewidth = None
        self.marker = None
        self.markers = None
        self.lthick = None
        self.lthicks = None
        self.linestyle = None
        self.linestyles = None
        self.marker_size = None
        self.marker_sizes = None
        self.linecolor = None
        self.linecolors = None
        # plots
        self.prob_same_x = None


class Scatter():
    def __init__(self):
        self.marker = None
        self.markers = None
        self.marker_size = None
        self.marker_sizes = None
        self.colorbar_side = None
        self.colorbar_size = None
        self.colorbar_pad = None
        self.elinewidth = None

class Contour():
    def __init__(self):
        self.nx = None
        self.ny = None
        self.plot_type = None
        self.nlevels = None
        self.grayContours = None
        self.colorbar_side = None
        self.colorbar_size = None
        self.colorbar_pad = None
        self.xmin = None
        self.ymin = None
        self.xmax = None
        self.ymax = None
        self.cmin = None
        self.cmax = None
        self.aspect_ratio_limit = None



class ImageOfSky():
    def __init__(self):
        self.nx = None
        self.ny = None
        self.xmin = None
        self.ymin = None
        self.xmax = None
        self.ymax = None
        self.cmin = None
        self.cmax = None
        self.distribution = None
        # gmm-speciifc params
        self.gmm_center_scale = None
        self.gmm_scale_min = None
        self.gmm_scale_max = None
        self.gmm_center_ra = None
        self.gmm_center_dec = None
        # real image-of-sky specific params
        self.output_dir = None
        self.missing_list_file = None
        self.height = None
        self.width = None
        self.obj = None
        self.survey = None # e.g., {'key':'O', 'survey':'Optical:SDSS'}
        self.query_images_dir = None
        self.image_or_contour = None
        # colorbar
        self.colorbar_side = None
        self.colorbar_size = None
        self.colorbar_pad = None
        self.image_renorm = None


        # self.plot_type = None
        # self.nlevels = None
        # self.grayContours = None
        # self.colorbar_side = None
        # self.colorbar_size = None
        # self.colorbar_pad = None

        # self.aspect_ratio_limit = None
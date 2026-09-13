import json
import numpy as np

# # for saving numpy arrays
# # https://stackoverflow.com/questions/26646362/numpy-array-is-not-json-serializable
# class NumpyEncoder(json.JSONEncoder):
#     """ Special json encoder for numpy types """
#     def __init__(self,*args, verbose=False, **kwargs):
#         self.verbose = verbose
#         super().__init__(*args, **kwargs)

#     def default(self, obj):
#         if isinstance(obj, np.integer):
#             return int(obj)
#         elif isinstance(obj, np.floating):
#             return float(obj)
#         elif isinstance(obj, np.ndarray):
#             return obj.tolist()
#         else:
#             if self.verbose:
#                 print('type of object is not serializable:', type(obj))
#             return 'non serializable entry'
#         return json.JSONEncoder.default(self, obj)

class NumpyEncoder(json.JSONEncoder):
    """ Special json encoder for numpy types """
    def __init__(self, *args, verbose=False, **kwargs):
        self.verbose = verbose
        super().__init__(*args, **kwargs)

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            if self.verbose:
                print('type of object is not serializable:', type(obj))
            return 'non serializable entry'
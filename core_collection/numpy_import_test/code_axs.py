#!/usr/bin/env python3

import numpy as np
import scipy

def deps_versions():
    """Reports the versions of currently used python dependencies.
    """
    return f"numpy=={np.__version__}, scipy=={scipy.__version__}"


def multiply(a, b, c, d, e, f):
    """Example of importing a python package dependency.

Usage examples :
                axs byname numpy_import_test , multiply 1 2 3 4 5 6
    """
    mat = np.array([[a, b], [c, d]])
    vec = np.array([e, f])

    return np.dot(mat, vec).tolist()

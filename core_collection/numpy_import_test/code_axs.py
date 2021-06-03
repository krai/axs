#!/usr/bin/env python3

import numpy as np
import scipy

def multiply(a, b, c, d, e, f):
    """Example of importing a python package dependency.

Usage examples :
                axs byname pip , install numpy 1.16.4                   # manual installation of NumPy
                axs byname numpy_import_test , multiply 1 2 3 4 5 6     # test use case
    """
    print(f"NumPy's version is {np.__version__}")
    print(f"NumPy's location is {np.__file__}")
    print(f"SciPy's version is {scipy.__version__}")
    print(f"SciPy's location is {scipy.__file__}")

    mat = np.array([[a, b], [c, d]])
    vec = np.array([e, f])

    return np.dot(mat, vec).tolist()

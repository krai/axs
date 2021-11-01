#!/usr/bin/env python3

"""An example of a script that can automatically import its documented dependencies before execution.

Usage examples:
    # without any dependency modifications:
                axs byname numpy_import_test , deps_versions
                axs byname numpy_import_test , multiply 1 2 3 4 5 6

    # an extra condition is dynamically added during script's loading:
                axs byname numpy_import_test , deps_versions --pillow_query+=,package_version=8.1.2     # string extension syntax
                axs byname numpy_import_test , deps_versions --pillow_query+,=package_version=8.2.0     # list extension syntax
"""

import numpy as np
import PIL

def deps_versions():
    """Reports the versions of currently used python dependencies.
    """
    return f"numpy=={np.__version__}, pillow=={PIL.__version__}"


def multiply(a, b, c, d, e, f):
    """Example of importing a python package dependency.

Usage examples :
                axs byname numpy_import_test , multiply 1 2 3 4 5 6
    """
    mat = np.array([[a, b], [c, d]])
    vec = np.array([e, f])

    return np.dot(mat, vec).tolist()

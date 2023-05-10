#!/usr/bin/env python3

"""Example "axs-native" code that can automatically import its documented dependencies before execution.

Usage examples:
    # without any dependency modifications:
                axs byname numpy_import_test , deps_versions
                axs byname numpy_import_test , multiply 1 2 3 4 5 6

    # an extra condition is dynamically added during script's loading:
                axs byname numpy_import_test , deps_versions --pillow_query+=,package_version=8.1.2     # string extension syntax
                axs byname numpy_import_test , deps_versions --pillow_query+,=package_version=8.2.0     # list extension syntax
"""

import sys
import numpy as np
import PIL
import local_import     # testing an import inside the entry


def kernel_python_major_dot_minor():
    """Reports the major.minor version of the currently running Python
    """
    major_version, minor_version = sys.version_info[0:2]

    return f"{major_version}.{minor_version}"


def deps_versions():
    """Reports the versions of currently used python dependencies.
    """
    return local_import.external_deps_versions()


def multiply(a, b, c, d, e, f):
    """Example of importing a python package dependency.

Usage examples :
                axs byname numpy_import_test , multiply 1 2 3 4 5 6
    """
    mat = np.array([[a, b], [c, d]])
    vec = np.array([e, f])

    return np.dot(mat, vec).tolist()

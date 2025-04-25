#!/usr/bin/env python3

import sys

def version(__version__):
    """Get the current kernel version

Usage examples :
                axs version
    """
    return __version__


def python_path():
    """Get the path to the Python executable that is used by the kernel itself

Usage examples :
                axs python_path
    """
    return sys.executable


def kernel_python_major_dot_minor():
    """Get the major.minor version of the Python executable that is used by the kernel itself

Usage examples :
                axs kernel_python_major_dot_minor
    """
    major_version, minor_version = sys.version_info[0:2]

    return f"{major_version}.{minor_version}"


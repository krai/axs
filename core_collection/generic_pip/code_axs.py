#!/usr/bin/env python3

""" This entry knows how to manipulate Python's module path to jump the queue.
"""

import sys


def use(__entry__):
    """Make an entry that contains an installed pip package the preferred location to import the package from.

Usage examples :
                axs np: byname numpy_1.16.4_pip , use , get np , ask_package_location
    """
    package_install_path = __entry__.get_path( __entry__['rel_packages_dir'] )
    sys.path.insert(0, package_install_path)
    return package_install_path


def ask_package_version(package_name):
    """Ask the pip package that is currently the preferred one for its version.
        This could work both with a use'd or the one importable by default.

Usage examples :
                axs np: byname numpy_1.16.4_pip , use , get np , ask_package_version
                
                axs byname generic_pip , ask_package_version numpy
    """
    module = __import__(package_name)
    return getattr(module, '__version__')


def ask_package_location(package_name):
    """Ask the pip package that is currently the preferred one for its file location.
        This could work both with a use'd or the one importable by default.

Usage examples :
                axs np: byname numpy_1.16.4_pip , use , get np , ask_package_location

                axs byname generic_pip , ask_package_location numpy
    """
    module = __import__(package_name)
    return getattr(module, '__file__')

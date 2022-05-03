#!/usr/bin/env python3

"""This entry knows how to run a Python script in an external Python interpreter.
    It inherits the main run() function from the shell entry.

Usage examples:
                axs byname python_script , run --abs_script_path=./barebones_resnet50.py --python_deps/:=^:byquery:python_package,package_name=torchvision,package_version=0.8.1
"""

import os

def ext_use_python_deps(python_deps=None):
    """Build PYTHONPATH from a list of resolved Python dependencies.
    """
    new_env    = {}

    if 'SYSTEMROOT' in os.environ:
        new_env['SYSTEMROOT']   = os.environ['SYSTEMROOT']

    if python_deps:
        new_env['PYTHONPATH']   = ':'.join( [ dep['abs_packages_dir'] for dep in python_deps ] )

    new_env['LD_LIBRARY_PATH']  = os.environ['LD_LIBRARY_PATH']

    return new_env

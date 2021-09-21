#!/usr/bin/env python3

"""This entry knows how to run a Python script in an external Python interpreter.
    It inherits the main run() function from the shell entry.

Usage examples:
                axs byname python_script , run --abs_script_path=./barebones_resnet50.py --python_deps/:=^:byquery:python_package,package_name=torchvision,package_version=0.8.1
"""

def ext_use_python_deps(python_deps=None):
    """Build PYTHONPATH from a list of resolved Python dependencies.
    """
    return { 'PYTHONPATH': ':'.join( [ dep['abs_packages_dir'] for dep in python_deps ] ) } if python_deps else {}

#!/usr/bin/env python3

"""This entry knows how to run a Python script in an external Python interpreter.
    It inherits the main run() function from the shell entry.

Usage examples:
                axs byname python_script , run --abs_script_path=./pytorch_classify.py --python_deps/:=^:byquery:python_package,package_name=torchvision,package_version=0.8.1
"""

import os

def ext_use_python_deps(python_deps=None, inherit_env_keys=None):
    """Build PYTHONPATH from a list of resolved Python dependencies.
    """
    new_env    = {}

    for env_key in (inherit_env_keys or []):
        if env_key in os.environ:
            new_env[env_key]    = os.environ[env_key]

    if python_deps:     # Note the OS-independent way of joining individual paths
        new_env['PYTHONPATH']   = os.pathsep.join( [ dep.get('abs_packages_dir') or dep.get_path(dep.get('file_name')) for dep in python_deps ] )

    if os.getenv('LD_LIBRARY_PATH') is not None:
        new_env['LD_LIBRARY_PATH']  = os.environ['LD_LIBRARY_PATH']

    return new_env

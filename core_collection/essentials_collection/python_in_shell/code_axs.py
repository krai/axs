#!/usr/bin/env python3

"""This entry knows how to run a Python script in an external Python interpreter.
    It inherits the main run() function from the shell entry.

Usage examples:
                axs byname python_script , run --abs_script_path=./pytorch_classify.py --python_deps/:=^:byquery:python_package,package_name=torchvision,package_version=0.8.1
"""

import os

def ext_use_python_deps(python_deps=None, inherit_env_keys=None, extra_env=None):
    """Build PYTHONPATH from a list of resolved Python dependencies.
    """
    new_env    = {}

    for env_key in (inherit_env_keys or []):
        if env_key in os.environ:
            new_env[env_key]    = os.environ[env_key]

    if extra_env:   # FIXME: may need extra provision for interplay between inherited and extra environments
        new_env.update( extra_env )

    if python_deps:     # Note the OS-independent way of joining individual paths
        all_abs_packages_dirs = []
        for dep in python_deps:
            if type(dep)==str:
                all_abs_packages_dirs.append( dep )     # the easiest way is to simply provide an absolute path
            else:
                abs_packages_dirs = dep.get('abs_packages_dirs')
                if abs_packages_dirs:
                    all_abs_packages_dirs.extend( abs_packages_dirs )   # there may be multiple, or none
                else:
                    all_abs_packages_dirs.append( dep.get_path(dep.get('file_name')) )  # if everything else failed, assume the entry contains python code directly

        new_env['PYTHONPATH']   = os.pathsep.join( all_abs_packages_dirs )

        path_parts  = []
        for dep in python_deps:
            if dep and type(dep)!=str and dep.get('abs_bin_dir'):
                path_parts.append( dep.get('abs_bin_dir') )

        if new_env.get('PATH'):
            path_parts.append( new_env.get('PATH') )

        new_env['PATH'] = os.pathsep.join( path_parts )

    return new_env

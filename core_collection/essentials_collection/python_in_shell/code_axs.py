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
        new_env['PYTHONPATH']   = os.pathsep.join( [ dep if type(dep)==str else ( dep.get('abs_packages_dir') or dep.get_path(dep.get('file_name')) ) for dep in python_deps ] )

        path_parts  = [ new_env.get('PATH') ] if new_env.get('PATH') else []
        for dep in python_deps:
            if dep and type(dep)!=str and dep.get('abs_bin_dir'):
                path_parts.append( dep.get('abs_bin_dir') )
        new_env['PATH'] = os.pathsep.join( path_parts )

    return new_env


def python_sync_pip_package(package_query, python_tool_entry):
    """A helper function to synchronize installed pip packages with the "workflow python" version.

Usage examples:
                axs bypath want_a_pip_sync_package , get python_deps --scipy_pip_query+=,no_deps --desired_python_version=3.9
    """
    if type(package_query)!=list:
        package_query = package_query.split(',')

    return python_tool_entry.get_kernel().byquery( package_query + [[ "desired_python_version", python_tool_entry["desired_python_version"] ]] )

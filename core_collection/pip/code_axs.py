#!/usr/bin/env python3

""" This entry knows how to install pip packages into generated entries.
"""

import logging
import os
import sys
import ufun


# Please note: some of the parameters below, although not directly used by the method,
#   must still be present in order to be automatically recorded via __record_entry__ mechanism.
#
def install(package_name, pip_options=None, installable=None, python_tool_entry=None, pip_entry_name=None, rel_install_dir=None, rel_packages_dir=None, python_major_dot_minor=None, tags=None,  __record_entry__=None):
    """Install a pip package into a separate entry, so that it could be easily use'd.

Usage examples :
                axs byname pip , install numpy 1.16.4

                axs byname pip , install numpy

                axs byname pip , install scipy 1.5.1 --pip_options,=no-deps --tags,=python_package,no_deps

                axs byname pip , install --package_name=torchvision --package_version=0.11.1+cu113 --pip_options="torch==1.10.0+cu113 -f https://download.pytorch.org/whl/cu113/torch_stable.html"

            # installing from a wheel file:
                axs byname pip , install mlperf_loadgen 1.1 --installable=$HOME/work_collection/mlperf_inference_git/loadgen/dist/mlperf_loadgen-1.1-cp36-cp36m-macosx_10_9_x86_64.whl
    """

    __record_entry__.pluck("pip_entry_name")

    __record_entry__["tags"]                = tags or ["python_package"]
    __record_entry__["_parent_entries"]     = [ [ "^", "byname", "base_pip_package" ] ]
    __record_entry__.parent_objects         = None      # reload parents
    __record_entry__.save( pip_entry_name )

    abs_install_dir   = __record_entry__["abs_install_dir"]
    os.makedirs( os.path.join(abs_install_dir, 'lib') )
    os.symlink( 'lib', os.path.join(abs_install_dir, 'lib64') )

    if pip_options:
        if type(pip_options)==dict:
            pip_options = [ k+'='+pip_options[k] for k in pip_options ]

        if type(pip_options)==list:
            pip_options = ' '.join( [ e if e.startswith('-') else '--'+e for e in pip_options ] )

    else:
        pip_options=''

    python_tool_entry.call('run', [], {
        "shell_cmd": [ "^^", "substitute", "#{tool_path}#"+f" -m pip install {installable} --prefix={abs_install_dir} --ignore-installed {pip_options}" ],
        "capture_output": False,
        "errorize_output": True,
    } )

    return __record_entry__


def available_versions(package_name, python_tool_entry):

    output_string = python_tool_entry.call('run', [], {
        "shell_cmd": [ "^^", "substitute", "#{tool_path}#"+f" -m pip install {package_name}==99.99.99 --user" ],
        "capture_output": False,
        "capture_stderr": True,
    } )

    versions_list = ufun.rematch(output_string, '\(from versions:\s(.*?)\)').split(', ')

    return versions_list

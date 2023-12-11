#!/usr/bin/env python3

""" This entry knows how to install pip packages into generated entries.

Usage examples :

    # install a given pip package:
            axs byname pip , install numpy

    # install a specific version of the given pip package:
            axs byname pip , install numpy 1.16.4

    # check available versions for a specific package (optionally from a specific index)
            axs byname pip , get available_package_versions --package_name=tensorrt --pip_options="--extra-index-url https://pypi.nvidia.com"
"""

import logging
import os
import sys
import ufun


def flatten_options(pip_options):
    if pip_options:
        if type(pip_options)==dict:
            flattened_options = ' '.join( [ k+' '+pip_options[k] for k in pip_options ] )

        elif type(pip_options)==list:
            flattened_options = ' '.join( [ e if e.startswith('-') else '--'+e for e in pip_options ] )

        else:
            flattened_options = pip_options

    else:
        flattened_options = ''

    return flattened_options


def install(package_name, flattened_options=None, installable=None, abs_install_dir=None, newborn_entry=None, __entry__=None):
    """Install a pip package into a separate entry, so that it could be easily use'd.

Usage examples :

    # install a given pip package:
            axs .pip.install numpy

    # install a specific version of the given pip package:
            axs .pip.install numpy 1.16.4

    # only install the specific package, without dependencies:
            axs byname pip , install scipy 1.5.1 --pip_options,=no-deps --tags,=python_package,no_deps

    # install a specific package with a specific version with a specific dependency version, given a "links file" :
            axs byname pip , install --package_name=torchvision --package_version=0.11.1+cu113 --pip_options="torch==1.10.0+cu113 -f https://download.pytorch.org/whl/cu113/torch_stable.html"

    # install a package from a given wheel file:
            axs byname pip , install mlperf_loadgen 1.1 --installable=$HOME/work_collection/mlperf_inference_git/loadgen/dist/mlperf_loadgen-1.1-cp36-cp36m-macosx_10_9_x86_64.whl
    """

    os.makedirs( abs_install_dir )
#    os.makedirs( os.path.join(abs_install_dir, 'lib') )
#    os.symlink( 'lib', os.path.join(abs_install_dir, 'lib64') )

    return_code = __entry__.call('get', 'install_package', {
        "installable": installable,
        "abs_install_dir": abs_install_dir,
        "flattened_options": flattened_options,
    } )
    if return_code:
        logging.error(f"A problem occured when trying to install {installable}, bailing out")
        newborn_entry.remove()
        return None
    else:
        return newborn_entry


def available_versions(package_name, force_binary=False, __entry__=None):
    """Install a pip package into a separate entry, so that it could be easily use'd.

Usage examples :

    # return the list of available versions for a specific package:
            axs .pip.available_versions --package_name=scipy
    """
    versions_list = __entry__.call('get', 'available_package_versions', {
        'package_name': package_name,
        'force_binary': force_binary,
    } )

    return versions_list

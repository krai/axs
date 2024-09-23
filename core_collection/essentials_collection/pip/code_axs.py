#!/usr/bin/env python3

""" This entry knows how to install pip packages into generated entries.

Usage examples :

    # install a given pip package:
            axs byname pip , install numpy

    # install a specific version of the given pip package:
            axs byname pip , install numpy 1.16.4

    # check available versions for a specific package (optionally from a specific index)
            axs byname pip , get available_package_versions --package_name=tensorrt --pip_options="--extra-index-url https://pypi.nvidia.com"

    # get an attribute from a specific package:
            axs byquery python_package,package_name=numpy , use , , attr numpy.pi

    # run a function from a specific package:
            axs byquery python_package,package_name=numpy , use , , func numpy.log 10
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


def install(installable, install_package, newborn_entry=None, patch_tool_entry=None, abs_patch_path=None):
    """Install a pip package into a separate entry, so that it could be easily use'd.
    Technically this is a function wrapper around a recorded expression "available_package_versions".

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

    # install a package using a rule:
            axs byquery python_package,package_name=numpy

    # install a package with a given version & without dependencies, using a rule:
            axs byquery python_package,package_name=scipy,package_version=1.2.1,no_deps

    # install all dependencies for project_A from its requirements.txt file, using a rule (note the correct quotes and their escaping) :
            axs byquery 'python_package,package_name=deps_for_project_A,installable="-r path/to/project_A/requirements.txt"'
    """

    if install_package:     # the non-zero (shell) return value of a recorded expression indicates an error:
        logging.error(f"A problem occured when trying to install {installable}, bailing out")
        newborn_entry.remove()
        return None

    elif patch_tool_entry:
        newborn_entry.parent_objects = None
        abs_packages_dir = newborn_entry["abs_packages_dir"]

        logging.warning(f"The resolved patch_tool_entry '{patch_tool_entry.get_name()}' located at '{patch_tool_entry.get_path()}' uses the shell tool '{patch_tool_entry['tool_path']}'")

        retval = patch_tool_entry.call('run', [], { 'entry_path': abs_packages_dir, 'abs_patch_path': abs_patch_path} )
        if retval != 0:
            logging.error(f"could not patch \"{abs_packages_dir}\" with \"{abs_patch_path}\", bailing out")
            newborn_entry.remove()
            return None

    return newborn_entry


def available_versions(available_package_versions):
    """Find which versions of a given package are available.
    Technically this is a function wrapper around a recorded expression "available_package_versions".

Usage examples :

    # return the list of available versions for a specific package:
            axs byname pip , available_versions --package_name=numpy

    # return the list of available versions for a specific package , specifically requiring only binary/precompiled packages:
            axs byname pip , available_versions --package_name=numpy --force_binary+
    """

    return available_package_versions

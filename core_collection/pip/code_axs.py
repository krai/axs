#!/usr/bin/env python3

""" This entry knows how to install pip packages into generated entries.
"""

import os
import sys


def install(package_name, package_version=None, pip_options=None, tags=None, __entry__=None):
    """Install a pip package into a separate entry, so that it could be easily use'd.

Usage examples :
                axs byname pip , install numpy 1.16.4

                axs byname pip , install numpy

                axs byname pip , install scipy 1.5.1 --pip_options,=no-deps --tags,=python_package,no_deps
    """
    assert __entry__ != None, "__entry__ should be defined"

    pip_entry_name = '_'.join( [package_name, package_version, 'pip'] ) if package_version else '_'.join( [package_name, 'pip'] )
    rel_install_dir         = 'install'

    result_data = {
        "_parent_entries":  [ [ "^", "byname", "generic_pip" ] ],
        "rel_packages_dir": os.path.join( rel_install_dir, 'lib', f"python{sys.version_info.major}.{sys.version_info.minor}", 'site-packages' ),
        "package_name":     package_name,
        "package_version":  package_version if package_version is not None else 'UNKNOWN',
        "tags":             tags or [ "python_package" ],
    }

    result_entry    = __entry__.get_kernel().work_collection().call('attached_entry', deterministic=False).own_data( result_data ).save( pip_entry_name )

    extra_python_site_dir   = result_entry.get_path( rel_install_dir )
    os.makedirs( os.path.join(extra_python_site_dir, 'lib') )
    os.symlink( 'lib', os.path.join(extra_python_site_dir, 'lib64') )

    version_suffix  = '=='+package_version if package_version!=None else ''
    if pip_options:
        if type(pip_options)==dict:
            pip_options = [ k+'='+pip_options[k] for k in pip_options ]

        if type(pip_options)==list:
            pip_options = ' '.join( [ e if e.startswith('-') else '--'+e for e in pip_options ] )

    else:
        pip_options=''

    __entry__.call('run',  f"python3 -m pip install {package_name}{version_suffix} --prefix={extra_python_site_dir} --ignore-installed {pip_options}" )

    return result_entry

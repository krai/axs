#!/usr/bin/env python3

""" This entry knows how to install pip packages into generated entries.
"""

import logging
import os
import sys


def install(package_name, package_version=None, pip_options=None, tool_entry=None, tags=None, entry_name=None, __record_entry__=None):
    """Install a pip package into a separate entry, so that it could be easily use'd.

Usage examples :
                axs byname pip , install numpy 1.16.4

                axs byname pip , install numpy

                axs byname pip , install scipy 1.5.1 --pip_options,=no-deps --tags,=python_package,no_deps

                axs byname pip , install --package_name=torchvision --package_version=0.11.1+cu113 --pip_options="torch==1.10.0+cu113 -f https://download.pytorch.org/whl/cu113/torch_stable.html"
    """

    rel_install_dir = 'install'
    logging.warning(f"The resolved tool_entry '{tool_entry.get_name()}' located at '{tool_entry.get_path()}' uses the shell tool '{tool_entry['tool_path']}'")

    if sys.platform.startswith('win'):
        rel_packages_dir    = os.path.join( rel_install_dir, 'lib', 'site-packages' )
    else:
        version_label       = tool_entry.call('run', [], { "shell_cmd": [ "^^", "substitute", "#{tool_path}# -c \"import sys;print(f'python{sys.version_info.major}.{sys.version_info.minor}')\""], "capture_output": True } )
        rel_packages_dir    = os.path.join( rel_install_dir, 'lib', version_label, 'site-packages' )

    if not entry_name:
        entry_name = '_'.join( [package_name, package_version, 'pip'] ) if package_version else '_'.join( [package_name, 'pip'] )

    __record_entry__.pluck("entry_name")

    __record_entry__["tags"]                = tags or ["python_package"]
    __record_entry__["_parent_entries"].insert(0, [ "^", "byname", "generic_pip" ] )
    __record_entry__.parent_objects         = None      # reload parents

    __record_entry__["rel_packages_dir"]    = rel_packages_dir
    __record_entry__.save( entry_name )

    extra_python_site_dir   = __record_entry__.get_path( rel_install_dir )
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

    tool_entry.call('run', [], {
        "shell_cmd": [ "^^", "substitute", "#{tool_path}#"+f" -m pip install {package_name}{version_suffix} --prefix={extra_python_site_dir} --ignore-installed {pip_options}" ],
        "capture_output": False,
        "errorize_output": True,
    } )

    # Recovering package_version from metadata and adding it to the Entry:
    __record_entry__.parent_objects = None
    version_from_metadata = __record_entry__.call('get_metadata', [], {'header_name': 'Version'})[0]
    __record_entry__["package_version"] = version_from_metadata
    __record_entry__.save( entry_name )

    return __record_entry__

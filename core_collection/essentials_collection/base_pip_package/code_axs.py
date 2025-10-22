#!/usr/bin/env python3

""" This entry knows how to manipulate Python's module path to jump the queue.
"""

import sys


def use(abs_packages_dirs):
    """Make an entry that contains an installed pip package the preferred location to import the package from.

Usage examples :
                axs byname numpy_1.16.4_pip_package , use , , python_api 'import numpy\nprint(numpy.__version__)'
                axs np: byname numpy_1.16.4_pip_package , use , , get np , ask_package_location
    """
    sys.path[0:0] = abs_packages_dirs
    return abs_packages_dirs


def get_metadata_path(abs_packages_dir, package_name, metadata_filename='METADATA'):
    """Locate the METADATA file that gets installed alongside the pip package, see
        https://packaging.python.org/specifications/recording-installed-packages/

Usage examples:
                axs byname base_pip_package , get_metadata_path $HOME/CK-TOOLS/lib-python-onnx-compiler.python-3.6.8-precompiled-macos-64/build onnx
    """
    import re
    import os.path
    from glob import glob

    distinfo_path_pattern   = os.path.join( abs_packages_dir, '*.dist-info' )
    for distinfo_path in glob( distinfo_path_pattern ):
        distinfo_name = os.path.basename( distinfo_path ).split( '-', 1 )[0]
        normalized_distinfo_name = re.sub(r"[-_.]+", "-", distinfo_name).lower()
        toplevel_path = os.path.join( distinfo_path, 'top_level.txt' )
        if os.path.isfile( toplevel_path ):
            with open( toplevel_path, 'r' ) as toplevel_fp:
                toplevel = toplevel_fp.readline().rstrip().lower()
        else:
            toplevel = normalized_distinfo_name

        if package_name.lower() in (toplevel, normalized_distinfo_name):
            return os.path.join( distinfo_path, metadata_filename )

    assert False, f"Could not find METADATA for package={package_name} when abs_packages_dir={abs_packages_dir}"
    return None


def get_metadata(abs_packages_dir, package_name, header_name=None, full=False):
    """Parse the METADATA file that gets installed alongside the pip package using email header parser, see
        https://packaging.python.org/specifications/core-metadata/

        Returns either all header names (if --header_name is not specified)
        or a list of values corresponding to the specified --header_name

Usage examples:
                axs byname base_pip_package , get_metadata $HOME/CK-TOOLS/lib-python-onnx-compiler.python-3.6.8-precompiled-macos-64/build onnx Version
                axs byname numpy_1.16.4_pip_package , get_metadata
                axs byname numpy_1.16.4_pip_package , get_metadata --header_name=Platform
    """
    from email.parser import BytesHeaderParser
    from email.policy import default

    metadata_path = get_metadata_path(abs_packages_dir, package_name)

    with open(metadata_path, 'rb') as metadata_fp:
        headers = BytesHeaderParser(policy=default).parse(metadata_fp)

    if full:
        metadata_dict = {}
        for k, v in headers.items():
            if k in metadata_dict:
                metadata_dict[k].append(v)
            else:
                metadata_dict[k] = [ v ]
        return metadata_dict
    elif header_name:
        return [ v for k, v in headers.items() if k==header_name ]
    else:
        return headers.keys()


def get_deps(abs_packages_dir, package_name):
    """Parse the METADATA file that gets installed alongside the pip package using email header parser
        and return the list of package dependencies, see:
        https://packaging.python.org/specifications/core-metadata/#requires-dist-multiple-use

Usage examples:
                axs byname base_pip_package , get_deps $HOME/CK-TOOLS/lib-python-onnx-compiler.python-3.6.8-precompiled-macos-64/build onnx
                axs byname numpy_1.16.4_pip_package , get_deps
    """
    return get_metadata( abs_packages_dir, package_name, 'Requires-Dist' )


def ask_package_version(package_name):
    """Ask the pip package that is currently the preferred one for its version.
        This could work both with a use'd or the one importable by default.

Usage examples :
                axs np: byname numpy_1.16.4_pip_package , use , , get np , ask_package_version

                axs gen: byname base_pip_package , use $HOME/CK-TOOLS/lib-python-onnx-compiler.python-3.6.8-precompiled-macos-64/build , , get gen , ask_package_version onnx
                
                axs byname base_pip_package , ask_package_version numpy
    """
    module = __import__(package_name)
    return getattr(module, '__version__')


def ask_package_location(package_name):
    """Ask the pip package that is currently the preferred one for its file location.
        This could work both with a use'd or the one importable by default.

Usage examples :
                axs np: byname numpy_1.16.4_pip_package , use , , get np , ask_package_location

                axs byname base_pip_package , ask_package_location numpy
    """
    module = __import__(package_name)
    return getattr(module, '__file__')


def get_abs_packages_dirs(rel_packages_dirs, merge=False, __entry__=None):

    abs_packages_dirs = []

    for rel_packages_dir in rel_packages_dirs:
        abs_packages_dir = __entry__.get_path( rel_packages_dir )
        if abs_packages_dir:
            abs_packages_dirs.append( abs_packages_dir )

    if merge and len(abs_packages_dirs)==2:
        import os.path
        import shutil

        src_dir, dst_dir = sorted( abs_packages_dirs, key=len, reverse=True )
        for src_item in os.listdir(src_dir):
            src_full_path = os.path.join( src_dir, src_item )
            shutil.move( src_full_path, dst_dir )
        abs_packages_dirs = [ dst_dir ]

    return abs_packages_dirs

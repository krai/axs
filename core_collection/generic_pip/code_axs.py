#!/usr/bin/env python3

""" This entry knows how to manipulate Python's module path to jump the queue.
"""

import sys


def use(abs_packages_dir):
    """Make an entry that contains an installed pip package the preferred location to import the package from.

Usage examples :
                axs np: byname numpy_1.16.4_pip , use , get np , ask_package_location
    """
    sys.path.insert(0, abs_packages_dir)
    return abs_packages_dir


def get_metadata_path(abs_packages_dir, package_name, metadata_filename='METADATA'):
    """Locate the METADATA file that gets installed alongside the pip package, see
        https://packaging.python.org/specifications/recording-installed-packages/

Usage examples:
                axs byname generic_pip , get_metadata_path $HOME/CK-TOOLS/lib-python-onnx-compiler.python-3.6.8-precompiled-macos-64/build onnx
    """
    import os.path
    from glob import glob

    distinfo_path_pattern   = os.path.join( abs_packages_dir, '*.dist-info' )
    for distinfo_path in glob( distinfo_path_pattern ):
        distinfo_name = os.path.basename( distinfo_path ).split( '-', 1 )[0]
        toplevel_path = os.path.join( distinfo_path, 'top_level.txt' )
        if os.path.isfile( toplevel_path ):
            with open( toplevel_path, 'r' ) as toplevel_fp:
                toplevel = toplevel_fp.readline().rstrip()
        else:
            toplevel = distinfo_name

        if package_name.lower() in (toplevel.lower(), distinfo_name.lower()):
            return os.path.join( distinfo_path, metadata_filename )

    assert False, f"Could not find METADATA for package {package_name}"
    return None


def get_metadata(abs_packages_dir, package_name, header_name=None):
    """Parse the METADATA file that gets installed alongside the pip package using email header parser, see
        https://packaging.python.org/specifications/core-metadata/

        Returns either all header names (if --header_name is not specified)
        or a list of values corresponding to the specified --header_name

Usage examples:
                axs byname generic_pip , get_metadata $HOME/CK-TOOLS/lib-python-onnx-compiler.python-3.6.8-precompiled-macos-64/build onnx Version
                axs byname numpy_1.16.4_pip , get_metadata
                axs byname numpy_1.16.4_pip , get_metadata --header_name=Platform
    """
    from email.parser import BytesHeaderParser
    from email.policy import default

    metadata_path = get_metadata_path(abs_packages_dir, package_name)

    with open(metadata_path, 'rb') as metadata_fp:
        headers = BytesHeaderParser(policy=default).parse(metadata_fp)

    if header_name:
        return [ v for k, v in headers.items() if k==header_name ]
    else:
        return headers.keys()


def get_deps(abs_packages_dir, package_name):
    """Parse the METADATA file that gets installed alongside the pip package using email header parser
        and return the list of package dependencies, see:
        https://packaging.python.org/specifications/core-metadata/#requires-dist-multiple-use

Usage examples:
                axs byname generic_pip , get_deps $HOME/CK-TOOLS/lib-python-onnx-compiler.python-3.6.8-precompiled-macos-64/build onnx
                axs byname numpy_1.16.4_pip , get_deps
    """
    return get_metadata( abs_packages_dir, package_name, 'Requires-Dist' )


def ask_package_version(package_name):
    """Ask the pip package that is currently the preferred one for its version.
        This could work both with a use'd or the one importable by default.

Usage examples :
                axs np: byname numpy_1.16.4_pip , use , get np , ask_package_version

                axs gen: byname generic_pip , use $HOME/CK-TOOLS/lib-python-onnx-compiler.python-3.6.8-precompiled-macos-64/build , get gen , ask_package_version onnx
                
                axs byname generic_pip , ask_package_version numpy
    """
    module = __import__(package_name)
    return getattr(module, '__version__')


def ask_package_location(package_name):
    """Ask the pip package that is currently the preferred one for its file location.
        This could work both with a use'd or the one importable by default.

Usage examples :
                axs np: byname numpy_1.16.4_pip , use , get np , ask_package_location

                axs byname generic_pip , ask_package_location numpy
    """
    module = __import__(package_name)
    return getattr(module, '__file__')

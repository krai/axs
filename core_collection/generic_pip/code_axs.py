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


def get_metadata_path(abs_packages_dir, package_name):
    """Locate the METADATA file that gets installed alongside the pip package, see
        https://packaging.python.org/specifications/recording-installed-packages/

Usage examples:
                axs byname generic_pip , get_metadata_path $HOME/CK-TOOLS/lib-python-onnx-compiler.python-3.6.8-precompiled-macos-64/build onnx
    """
    import os.path
    from glob import glob

    metadata_path_pattern   = os.path.join( abs_packages_dir, package_name+'-*.dist-info', 'METADATA' )
    metadata_path_matches   = glob( metadata_path_pattern )
    assert len(metadata_path_matches)==1, f"The package {package_name} does not have a METADATA matching {metadata_path_pattern}"

    return metadata_path_matches[0]


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

    with open(metadata_path, 'rb') as fp:
        headers = BytesHeaderParser(policy=default).parse(fp)

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

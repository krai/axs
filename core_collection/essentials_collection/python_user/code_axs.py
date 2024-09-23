#!/usr/bin/env python3

"""This entry knows how to require Python packages version-synchronized with the executing Python

"""

def python_sync_pip_package(package_query, python_tool_entry):
    """A helper function to synchronize installed pip packages with the "workflow python" version.

Usage examples:
                axs bypath want_a_pip_sync_package , get python_deps --scipy_pip_query+=,no_deps --desired_python_version=3.9
    """
    if type(package_query)!=list:
        package_query = package_query.split(',')

    return python_tool_entry.get_kernel().byquery( package_query + [[ "desired_python_version", python_tool_entry["desired_python_version"] ]] )

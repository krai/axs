"""
    A package for installing a precompiled python3 binary into a separate axs entry.

    Usage examples :

        # get version:
            axs byquery extracted,precompiled_python,minor_version=14 , subst_run "#{exe_path}# --version"

        # get help:
            axs byquery extracted,precompiled_python,minor_version=13 , subst_run "#{exe_path}# --help"

        # any other command - just roll it yourself from the template above
"""

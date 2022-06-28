#!/usr/bin/env python3

"""An example of some code that can be imported into code_axs.py
    if it simply lives in the same directory.
"""

import numpy as np
import PIL

def external_deps_versions():
    """Reports the versions of currently used python dependencies.
    """
    return f"numpy=={np.__version__}, pillow=={PIL.__version__}"

if __name__ == '__main__':
    print( 'Standalone: '+external_deps_versions() )

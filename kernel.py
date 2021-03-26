#!/usr/bin/env python3

"""
# Accessing the kernel via API (default and non-default)

if condition:
    from kernel import MicroKernel
    ak = MicroKernel(name='SpecialKernel')
else:
    from kernel import default as ak
"""

__version__ = '0.2.2'   # TODO: update with every kernel change

import logging
import os
from runnable import Runnable
from stored_entry import Entry


class MicroKernel(Runnable):
    def __init__(self, entry_cache=None, **kwargs):
        self.entry_cache    = entry_cache or {}
        super().__init__(**kwargs)
        logging.debug(f"[{self.name}] Initializing the MicroKernel with entry_cache={self.entry_cache}")


    def version(self):
        """ Get the current kernel version
        """
        return __version__


    def kernel_path(self, entry_path=None):
        """ Get the path where the kernel is currently installed
        """
        kernel_dir_path = os.path.dirname( os.path.realpath(__file__) )
        if entry_path:
            return os.path.join(kernel_dir_path, entry_path)
        else:
            return kernel_dir_path


    def introduce(self):
        print(f"I am {self.name} version={self.version()} kernel_path={self.kernel_path()}")


    def bypath(self, entry_path):
        """ Fetch an entry by its path, cached by the path
        """
        cache_hit = self.entry_cache.get(entry_path)

        if cache_hit:
            logging.debug(f"[{self.name}] bypath: cache HIT for entry_path={entry_path}")
        else:
            logging.debug(f"[{self.name}] bypath: cache MISS for entry_path={entry_path}")
            cache_hit = self.entry_cache[entry_path] = Entry(entry_path=entry_path, kernel=self)

        return cache_hit


    def core_collection(self):
        """ Fetch the core_collection entry
        """
        return self.bypath( self.kernel_path( 'core_collection' ) )


    def byname(self, entry_name):
        """ Fetch an entry by its name (delegated to core_collection)
        """
        logging.debug(f"[{self.name}] byname({entry_name})")
        return self.core_collection().call('byname', [entry_name])



#logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(funcName)s %(message)s")

default_kernel = MicroKernel(name="DefaultKernel")

if __name__ == '__main__':

    ak = default_kernel # just a rename for brevity

    ak.introduce()

    result      = ak.byname('be_like').call('meme', ['does not instagram her food', 'considerate'], {'person': 'Mary'})
    print( result )

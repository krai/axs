#!/usr/bin/env python3

__version__ = '0.2.0'   # TODO: update with every kernel change

import logging
from stored_entry import Entry


class MicroKernel:
    def __init__(self, entry_cache=None, name="DefaultKernel"):
        self.entry_cache    = entry_cache or {}
        self.name           = name
        logging.debug(f"[{self.name}] Initializing the MicroKernel with entry_cache={self.entry_cache}")

    def version(self):
        return __version__

    def introduce(self):
        print(f"I am {self.name} version {self.version()}")


    def bypath(self, entry_path):
        cache_hit = self.entry_cache.get(entry_path)

        if cache_hit:
            logging.debug(f"[{self.name}] bypath: cache HIT for entry_path={entry_path}")
        else:
            logging.debug(f"[{self.name}] bypath: cache MISS for entry_path={entry_path}")
            cache_hit = self.entry_cache[entry_path] = Entry(entry_path=entry_path, kernel=self)

        return cache_hit

#logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(funcName)s %(message)s")

default_kernel = MicroKernel()

if __name__ == '__main__':

    ak = default_kernel # just a rename for brevity

    ak.introduce()

    entry_bl    = ak.bypath('be_like')
    result      = entry_bl.call('meme', ['does not instagram her food', 'considerate'], {'person': 'Mary'})
    print( result )

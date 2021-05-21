#!/usr/bin/env python3

"""
# Accessing the kernel via API (default and non-default)

if condition:
    from kernel import MicroKernel
    ak = MicroKernel(name='SpecialKernel')
else:
    from kernel import default as ak
"""

__version__ = '0.2.67'   # TODO: update with every kernel change

import logging
import os
from runnable import Runnable
from stored_entry import Entry


class MicroKernel(Runnable):
    """One central place to create and cache Entries, and to execute pipelines

Usage examples :
                axs version
                axs kernel_path
                axs help help
    """

    def __init__(self, entry_cache=None, **kwargs):
        self.entry_cache    = entry_cache or {}
        super().__init__(kernel=self, **kwargs)
        logging.debug(f"[{self.name}] Initializing the MicroKernel with entry_cache={self.entry_cache}")


    def version(self):
        """Get the current kernel version
        """
        return __version__


    def kernel_path(self, entry_path=None):
        """Get the path where the kernel is currently installed
        """
        kernel_dir_path = os.path.dirname( os.path.realpath(__file__) )
        if entry_path:
            return os.path.join(kernel_dir_path, entry_path)
        else:
            return kernel_dir_path


    def introduce(self):
        print(f"I am {self.name} version={self.version()} kernel_path={self.kernel_path()}")


    def bypath(self, path, name=None, container=None, own_data=None):
        """Fetch an entry by its path, cached by the path
            Ad-hoc entries built either form a data file (.json) or functions' file (.py) can also be created.

Usage examples :
                axs bypath core_collection/counting_collection/germanic/dutch , dig number_mapping.5
                axs bypath xyz/boo.json , substitute "Hello, #{boo}#"
                axs bypath pqr/iterative.py , factorial 6
        """
        path = os.path.realpath( path )

        cache_hit = self.entry_cache.get(path)

        if cache_hit:
            logging.debug(f"[{self.name}] bypath: cache HIT for path={path}")
        else:
            logging.debug(f"[{self.name}] bypath: cache MISS for path={path}")
            if path.endswith('.json'):
                name = name or "AdHoc_data"
                cache_hit = self.entry_cache[path] = Entry(name=name, parameters_path=path, own_functions=False, kernel=self)
            elif path.endswith('.py'):
                module_name = path[:-len('.py')]
                name = name or "AdHoc_functions"
                cache_hit = self.entry_cache[path] = Entry(name=name, own_data={}, entry_path='.', module_name=module_name, parent_objects=[], kernel=self)
            else:
                cache_hit = self.entry_cache[path] = Entry(name=name, entry_path=path, own_data=own_data, kernel=self, container=container)
            logging.debug(f"[{self.name}] bypath: successfully CACHED {cache_hit.get_name()} under path={path}")

        return cache_hit


    def core_collection(self):
        """Fetch the core_collection entry
        """
        return self.bypath( self.kernel_path( 'core_collection' ) )


    def work_collection(self):
        """Fetch the work_collection entry
        """
        work_collection_path = os.getenv('AXS_WORK_COLLECTION') or os.path.join(os.getenv('HOME'), 'work_collection')
        if not os.path.exists(work_collection_path):
            print(f"Creating new empty work_collection at {work_collection_path}...")
            work_collection_data = {
                "parent_entries^": [ "^core_collection" ],
            }
            work_collection_object = Entry(name="work_collection", entry_path=work_collection_path, own_data=work_collection_data, kernel=self)
            work_collection_object.call('add_entry_path', [ self.kernel_path( 'core_collection' ) ] )
        return self.bypath( work_collection_path )


    def byname(self, entry_name):
        """Fetch an entry by its name (delegated to core_collection)
        """
        logging.debug(f"[{self.name}] byname({entry_name})")
        return self.work_collection().call('byname', [entry_name])


    def byquery(self, query):
        """Fetch an entry by a query over its tags (delegated to core_collection)
        """
        logging.debug(f"[{self.name}] byquery({query})")
        return self.work_collection().call('byquery', [query])


#logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(funcName)s %(message)s")

default_kernel = MicroKernel(name="DefaultKernel")

if __name__ == '__main__':

    ak = default_kernel # just a rename for brevity

    ak.introduce()

    result = ak.execute([
                ('byname', ['be_like'], {}),
                ('meme', ['does not instagram her food', 'considerate'], {'person': 'Mary'}),
    ])
    print( result )

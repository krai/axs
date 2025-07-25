#!/usr/bin/env python3

"""
# Accessing the kernel via API (default and non-default)

if condition:
    from kernel import MicroKernel
    ak = MicroKernel(name='SpecialKernel')
else:
    from kernel import default as ak
"""

__version__ = '0.2.439'     # TODO: update with every kernel change

import logging
import os
import sys

import ufun

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
        self.entry_cache            = entry_cache or {}
        self.record_container_value = None
        super().__init__(kernel=self, **kwargs)
        logging.debug(f"[{self.get_name()}] Initializing the MicroKernel with entry_cache={self.entry_cache}")


    def version(self):
        """Get the current kernel version

Usage examples :
                axs version
        """
        return __version__


    def kernel_path(self, rel_file_path=None):
        """Get the path where the kernel is currently installed

Usage examples :
                axs kernel_path
                axs kernel_path core_collection
        """
        kernel_dir_path = os.path.dirname( os.path.realpath(__file__) )
        if rel_file_path:
            return os.path.join(kernel_dir_path, rel_file_path)
        else:
            return kernel_dir_path


    def python_path(self):
        """Get the path to the Python executable that is used by the kernel itself

Usage examples :
                axs python_path
        """
        return sys.executable


    def kernel_python_major_dot_minor(self):
        """Get the major.minor version of the Python executable that is used by the kernel itself

Usage examples :
                axs kernel_python_major_dot_minor
        """
        major_version, minor_version = sys.version_info[0:2]

        return f"{major_version}.{minor_version}"


    def introduce(self):
        print(f"I am {self.get_name()} version={self.version()} kernel_path={self.kernel_path()} interpreted by python_path={self.python_path()}")


    def fresh_entry(self, entry_path=None, own_data=None, container=None, name=None, generated_name_prefix=None):
        """Constructor for a fresh unstored Entry (optional data, no code, no filesystem path),
            which is not attached to any container (collection).
            It can be gradually populated with (more) data and stored later.

Usage examples :
                axs fresh_entry coordinates , plant x 10 y -5 , save
                axs fresh_entry , plant message "Hello, world" , save hello
                axs fresh_entry ---own_data='{"greeting":"Hello", "name":"world", "_parent_entries":[["AS^IS", "^","byname","shell"]]}' , run ---='[["^^","substitute","echo #{greeting}#, #{name}#"]]'
        """

        if own_data is None:    # sic: retain the same empty dictionary if given
            own_data = {}
        return Entry(entry_path=entry_path, own_data=own_data, own_functions=False, container=container, name=name, generated_name_prefix=generated_name_prefix, is_stored=False, kernel=self)


    def uncache(self, old_path):
        if old_path and old_path in self.entry_cache:
            del self.entry_cache[ old_path ]
            logging.debug(f"[{self.get_name()}] Uncaching from under {old_path}")


    def encache(self, new_path, entry):
        new_path = os.path.realpath( new_path )
        self.entry_cache[ new_path ] = entry
        logging.debug(f"[{self.get_name()}] Caching under {new_path}")

        return entry


    def bypath(self, path, name=None, container=None, own_data=None, parent_objects=None):
        """Fetch an entry by its path, cached by the path
            Ad-hoc entries built either form a data file (.json) or functions' file (.py) can also be created, and even manually stacked

Usage examples :
                axs bypath counting_collection/germanic/dutch , dig number_mapping.5
                axs bypath only_data/oxygen.json , substitute "Element #{name}# has symbol #{symbol}#, atomic number #{number}# and weight #{weight}#"
                axs bypath only_code/iterative.py , factorial 6
                axs elem: bypath only_data/carbon.json , get_kernel , code: bypath only_code/iterative.py --parent_objects,:=^:get:elem , factorial --:=^^:get:number
                axs elem: bypath only_data/oxygen.json , get_kernel , lat: bypath latin --parent_objects,:=^:get:elem , get weight
        """
        path = os.path.realpath( path )

        cache_hit = self.entry_cache.get(path)

        if cache_hit:
            logging.debug(f"[{self.get_name()}] bypath: cache HIT for path={path}")
        else:
            logging.debug(f"[{self.get_name()}] bypath: cache MISS for path={path}")

            if path.endswith('.json'):      # ad-hoc data entry from a .json file
                entry_object = Entry(name=name, parameters_path=path, own_functions=False, parent_objects=parent_objects or [], is_stored=True, kernel=self)
            elif path.endswith('.py'):      # ad-hoc functions entry from a .py file
                module_name = path[:-len('.py')]
                entry_object = Entry(name=name, entry_path=path, own_data={}, module_name=module_name, parent_objects=parent_objects or [], is_stored=True, kernel=self)
            else:
                entry_object = Entry(name=name, entry_path=path, own_data=own_data, container=container, parent_objects=parent_objects or None, kernel=self)

            cache_hit = self.encache( path, entry_object )
            logging.debug(f"[{self.get_name()}] bypath: successfully CACHED {cache_hit.get_name()} under path={path}")

        return cache_hit


    def core_collection(self):
        """Fetch the core_collection entry

Usage examples :
                axs core_collection , help
                axs core_collection , entry_path: get_path , , byname shell , run --shell_cmd_with_subs='ls -1 #{entry_path}#'
        """
        return self.bypath( self.kernel_path( 'core_collection' ) )


    def record_container(self, *given_values):
        if len(given_values):
            self.record_container_value = given_values[0]
        return self.record_container_value


    def work_collection(self):
        """Fetch the work_collection entry

Usage examples :
                axs work_collection , get_path
                AXS_WORK_COLLECTION=~/alt_wc axs work_collection , get_path
                axs work_collection , entry_path: get_path , , byname shell , run --shell_cmd_with_subs='ls -1 #{entry_path}#'
        """
        work_collection_path = os.getenv('AXS_WORK_COLLECTION') or os.path.join(os.path.expanduser('~'), 'work_collection')
        if os.path.exists(work_collection_path):
            work_collection_object = self.bypath( work_collection_path )
        else:
            logging.warning(f"[{self.get_name()}] Creating new empty work_collection at {work_collection_path}...")
            work_collection_data = {
                self.PARAMNAME_parent_entries: [[ "^", "core_collection" ]],
                "tags": [ "collection" ],
                "contained_entries": {
                    "core_collection": [ "^", "execute", [[
                        [ "core_collection" ],
                        [ "get_path" ]
                    ]] ]
                }
            }
            work_collection_object = self.bypath(work_collection_path, name="work_collection", own_data=work_collection_data)
            work_collection_object.save( completed=ufun.generate_current_timestamp() )

        self.record_container( work_collection_object )     # to avoid infinite recursion
        return work_collection_object


    def byname(self, entry_name, skip_entry_names=None):
        """Fetch an entry by its name (delegated to work_collection)

Usage examples :
                axs byname pip , help
        """
        logging.debug(f"[{self.get_name()}] byname({entry_name, skip_entry_names})")
        return self.work_collection().call('byname', [entry_name, skip_entry_names])


    def all_byquery(self, query, pipeline=None, template=None, parent_recursion=False, skip_entry_names=None):
        """Returns a list of ALL entries matching the query.
            Empty list if nothing matched.

Usage examples :
                axs all_byquery onnx_model
                axs all_byquery python_package,package_name=pillow
                axs all_byquery onnx_model --template="#{model_name}# : #{file_name}#"
                axs all_byquery python_package --template="python_#{python_version}# package #{package_name}#"
                axs all_byquery tags. --template="tags=#{tags}#"
                axs all_byquery deleteme+ ---='[["remove"]]'
                axs all_byquery git_repo ---='[["pull"]]'
        """
        logging.debug(f"[{self.get_name()}] all_byquery({query}, {pipeline}, {template}, {parent_recursion}, {skip_entry_names})")
        return self.work_collection().call('all_byquery', [query, pipeline, template, parent_recursion, skip_entry_names])


    def show_matching_rules(self, query):
        """Find and show all the rules (and their advertising entries) that match the given query.

Usage examples :
                axs show_matching_rules shell_tool,can_download_url_from_zenodo
        """
        logging.debug(f"[{self.get_name()}] show_matching_rules({query})")
        return self.work_collection().call('show_matching_rules', [query])


    def byquery(self, query, produce_if_not_found=True, parent_recursion=False, skip_entry_names=None):
        """Fetch an entry by a query over its tags (delegated to work_collection)
            Note parent_recursion is False by default, but can be switched on manually (beware of the avalanche though!).

Usage examples :
                axs byquery person.,be!=Be
                axs byquery person.,be!=Be --parent_recursion+ , get_path
        """
        logging.debug(f"[{self.get_name()}] byquery({query}, {produce_if_not_found}, {parent_recursion}, {skip_entry_names})")
        return self.work_collection().call('byquery', [query, produce_if_not_found, parent_recursion, skip_entry_names])


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

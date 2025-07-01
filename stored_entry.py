#!/usr/bin/env python3

import importlib.util
import logging
import os
import sys
import uuid

import ufun
from runnable import Runnable


class Entry(Runnable):
    "An Entry is a Runnable stored in the file system"

    FILENAME_parameters     = 'data_axs.json'
    MODULENAME_functions    = 'code_axs'     # the actual filename ends in .py
    PREFIX_gen_entryname    = 'generated_entry_'

    def __init__(self, entry_path=None, parameters_path=None, module_name=None, container=None, generated_name_prefix=None, is_stored=None, **kwargs):
        "Accept setting entry_path in addition to parent's parameters"

        self.generated_name_prefix  = generated_name_prefix or self.PREFIX_gen_entryname
        self.container_object       = container

        if entry_path:
            self.set_path(entry_path)
        else:
            self.entry_path         = None  # an obligatory placeholder

        self.parameters_path        = parameters_path
        self.module_name            = module_name or self.MODULENAME_functions
        self.is_stored              = is_stored if type(is_stored)==bool else os.path.exists(entry_path)

        super().__init__(**kwargs)

        logging.debug(f"[{self.get_name()}] Initializing the Entry with entry_path={self.entry_path}, parameters_path={self.parameters_path}, module_name={self.module_name}, generated_name_prefix={self.generated_name_prefix}")


    def generate_name(self, prefix=''):
        """Generates a unique name with a given prefix

Usage examples :
                axs generate_name
                axs generate_name unnamed_entry_
        """
        return prefix + uuid.uuid4().hex


    def set_path(self, new_path):
        """Sets the path of the given Entry

            Please note that the output of this method is the Entry itself, not the new_path
        """

        new_path = new_path or self.name or self.generate_name( self.generated_name_prefix )

        if os.path.isabs( new_path ):           # absolute path
            self.entry_path = new_path

        elif self.container_object:             # relative to container
            self.entry_path = os.path.join( self.container_object.get_path( new_path ) )

        else:                                   # relative to cwd
            self.entry_path = os.path.realpath( new_path )

        self.parameters_path    = None
        self.name               = None

        return self


    def get_path(self, file_name=None):
        """The directory path of the stored Entry, optionally joined with a given relative name.

Usage examples :
                axs byname base_map , get_path
                axs byname derived_map , get_path README.md
        """
        def ensure_path():

            if self.entry_path is None:
                self.set_path(None)

            return self.entry_path

        if file_name:
            if type(file_name)==list:
                file_name = os.path.sep.join( file_name )

            if os.path.isabs( file_name ):
                return file_name
            else:
                return os.path.join(ensure_path(), file_name)
        else:
            return ensure_path()


    def get_path_from(self, key_path):
        """A frequently needed combination of fetching a relative path from an Entry's data
            and getting an absolute file path from that relative path.

Usage examples :
                axs byquery package_name=numpy , get_path_from rel_packages_dir
        """
        rel_path = self.dig(key_path)

        return self.get_path(rel_path) if rel_path is not None else None


    def get_path_of(self, resource_name, strict=True):
        """Assuming the entry has contained_files{} dictionary defined,
            given the resource_name maps it to the absolute path of this resource.
            Also optionally checks if the path exists, raising FileNotFoundError if not.

Usage examples :
                axs byquery git_repo,repo_name=mlperf_inference_git , get_path_of bert_code_root
        """
        abs_path = self.get_path(self.dig(["contained_files", resource_name], safe=not strict))
        if strict and not os.path.exists( abs_path ):
            raise FileNotFoundError( abs_path )

        return abs_path


    def trim_path(self, input_path):
        """Transform path to relative-to-entry if inside entry, or absolute if outside
        """
        if os.path.isabs( input_path ):                             # given as absolute
            real_input_path     = os.path.realpath( input_path )
            real_entry_path_tr  = os.path.realpath( self.entry_path ) + os.path.sep

            if real_input_path.startswith( real_entry_path_tr ):    # absolute and inside => trim
                return real_input_path[ len(real_entry_path_tr): ]
            else:                                                   # absolute, but outside => keep
                return input_path
        else:                                                       # relative, assume inside => keep
            return input_path


    def find_file(self, regex, looking_for_dir=False, return_full=False, topdown=True, abs_paths=False, return_all=False):
        """Find a file with the given regex inside current entry and return its relative or absolute path.
Note: it must be Python's regex, not Shell's!

Usage examples :
                axs byname numpy_package_for_python3.6 , find_file 'poly.*' --return_full+ --return_all+
        """
        candidates = ufun.fs_find(self.get_path(''), regex, looking_for_dir=looking_for_dir, return_full=return_full, topdown=topdown)

        if not abs_paths:
            candidates = [ self.trim_path(c).split( os.path.sep ) for c in candidates ]     # each trimmed path is a list in our internal "portable relative path format"

        if return_all:
            return candidates
        elif len(candidates):
            return candidates[0]
        else:
            return None


    def get_name(self):
        return self.name or (self.entry_path and os.path.basename(self.entry_path))


    def get_parameters_path(self):
        """Return the path to a json file that is supposed to contain loadable parameters
        """
        return self.parameters_path or self.get_path( self.FILENAME_parameters )


    def get_module_name(self):
        return self.module_name


    def get_container(self):
        return self.container_object


    def bypath(self, path, name=None):
        """A parameterization of MicroKernel.bypath() that is always relative to the "current" entry,
            mainly used by collections.
        """
        return self.get_kernel().bypath(self.get_path(path), name, container=self)


    def attach(self, container=None):
        """Dispatch the request to register an entry in a container to the container.

Usage examples :
                axs fresh_entry dynamically_attached , plant apple tree , attach --:=^:work_collection , save

                axs byname mlperf_inference_git_recipe , attach --:=^:work_collection , save another_git_recipe
        """
        if container:
            self.container_object = container
        else:
            container = self.get_container()

        if container:
            container.call('add_entry_path', [self.get_path(''), self.get_name()] )

        return self


    def detach(self):
        """Dispatch the request to de-register an entry from a container to the container.
        """
        container = self.get_container()
        if container:
            container.call("remove_entry_name", self.get_name() )
            self.container_object = None
        else:
            logging.warning(f"[{self.get_name()}] was not attached to a container")

        return self


    def pure_data_loader(self):
        "Returns the dictionary loaded or the (stringifiable) exception object"

        parameters_path = self.get_parameters_path()
        try:
            return ufun.load_json( parameters_path )
        except OSError as e:
            return e


    def own_functions(self):
        """Lazy-load and cache functions from the file system

            Note the convention:
                stored None means "not loaded yet", as in "cached value missing"
                whereas stored False means "this object has no code to load", "nothing to see here".

Usage examples :
                axs byname be_like , own_functions
                axs byname dont_be_like , own_functions
        """
        if self.own_functions_cache==None:    # lazy-loading condition
            entry_path = self.get_path()
            if entry_path:
                module_name = self.get_module_name()

                file_path = os.path.join( entry_path , module_name+'.py' )
                if os.path.exists( file_path ):
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    self.own_functions_cache = False    # to avoid infinite recursion
                    self.touch('_BEFORE_CODE_LOADING')
                    self.own_functions_cache = importlib.util.module_from_spec(spec)
                    sys.path.insert( 0, entry_path )    # allow (and prefer) code imports local to the entry
                    spec.loader.exec_module( self.own_functions_cache )
                    sys.path.pop( 0 )                   # /allow (and prefer) code imports local to the entry

                else:
                    self.own_functions_cache = False

            else:
                logging.debug(f"[{self.get_name()}] The entry does not have a path, so no functions either")
                self.own_functions_cache = False

        return self.own_functions_cache


    def reload(self):
        """Triggers reloading data, code and clears call cache.

            Useful when another axs process is allowed to update entries and we need to pick up the changes.
        """
        self.own_data_cache         = None
        self.call_cache             = {}
        self.own_functions_cache    = None

        return self


    def pickle_one(self):
        """Return a command that would (hopefully) load *this* entry at a later time. Used recursively by pickle_struct()
        """

        if self.parameters_path:
            return [ "^", "bypath", self.parameters_path ]
        elif self.entry_path:
            if self.get_container():
                return [ "^", "byname", self.get_name()]
            else:
                return [ "^", "bypath", self.get_path()]
        else:
            fresh_entry_opt_args = { "own_data": self.pickle_struct(self.own_data()) }
            if self.container_object:
                fresh_entry_opt_args["container"] = self.container_object.pickle_one()
            return [ "^", "fresh_entry", [], fresh_entry_opt_args ]


    def save(self, new_path=None, on_collision="force", completed=None):    # FIXME: "force" mimics old behaviour. To benefit from the change we need to switch to "raise"
        """Store [updated] own_data of the entry
            Note1: the entry didn't have to have existed prior to saving
            Note2: only parameters get stored

Usage examples :
                axs fresh_entry coordinates , plant x 10 y -5 , save
                axs fresh_entry , plant contained_entries '---={}' _parent_entries --,:=AS^IS:^:core_collection , save new_collection
        """

        if new_path:
            self.set_path( new_path )
            self.is_stored = False
        else:
            new_path = self.get_path()

        own_data = self.own_data()

        if ("__completed" in own_data) or ("__query" in own_data) or (completed is not None):
            self["__completed"] = completed or False

        parameters_path        = self.get_parameters_path()
        parameters_dirname, parameters_basename = os.path.split( parameters_path )

        if parameters_dirname and not self.is_stored:   # directory needs to be created
            if os.path.exists( parameters_dirname ):    # unexpected collision

                if on_collision in ("force", "ignore"):
                    logging.warning(f"[{self.get_name()}] Saving into existing directory {parameters_dirname} in --on_collision=force mode")

                elif on_collision=="timestamp":
                    prev_parameters_dirname = parameters_dirname
                    parameters_dirname += '_' + ufun.generate_current_timestamp(fs_safe=True)
                    logging.warning(f"[{self.get_name()}] Collision when saving into existing directory {prev_parameters_dirname}, switching to {parameters_dirname} in --on_collision=timestamp mode")

                    if self.parameters_path:
                        parameters_path = os.path.join( parameters_dirname, parameters_basename)
                    else:
                        self.name       = os.path.basename(parameters_dirname)
                        self.entry_path = None
                        parameters_path = self.get_parameters_path()
                        parameters_dirname, parameters_basename = os.path.split( parameters_path )

                    if os.path.exists(parameters_dirname):  # still a collision?
                        raise FileExistsError( f"Cannot save to {prev_parameters_dirname} or {parameters_dirname} as both directories exist. Please investigate or use --on_collision=force to override" )
                    else:
                        os.makedirs( parameters_dirname )

                else: # elif on_collision=="raise":
                    raise FileExistsError( f"Cannot save to {parameters_dirname} as the directory exists. Use --on_collision=force to override" )

            else:
                os.makedirs( parameters_dirname )

        json_string = ufun.save_json( self.pickle_struct(own_data), parameters_path, indent=4 )

        logging.info(f"[{self.get_name()}] parameters {json_string} saved to '{parameters_path}'")

        self.call('attach')

        ak = self.get_kernel()
        if ak:
            ak.encache( new_path, self )
        self.is_stored  = True

        return self


    def remove(self):
        """Delete the entry from the file system (keeping the memory shadow)

Usage examples :
                axs byname hebrew_letters , remove
        """
        self.call('detach')

        if self.is_stored:
            entry_path = self.parameters_path or self.entry_path
            ufun.rmdir( entry_path )
            logging.info(f"[{self.get_name()}] {entry_path} removed from the filesystem")

            ak = self.get_kernel()
            if ak:
                ak.uncache( entry_path )
            self.is_stored  = False
        else:
            logging.warning(f"[{self.get_name()}] was not stored in the file system, so cannot be removed")

        return self


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(funcName)s %(message)s")

    print('-'*40 + ' Entry direct creation and storing: ' + '-'*40)

    base_ordinals = Entry(entry_path='base_ordinals', own_data={
        "0": "zero",
        "1": "one",
        "2": "two",
        "3": "three",
    })
    assert base_ordinals[2]=="two", "Accessing own parameter of an unstored object"

    derived_ordinals = Entry(entry_path='derived_ordinals', own_data={
        "5": "five",
        "6": "six",
        "7": "seven",
        "8": "eight",
    }, parent_objects=[base_ordinals]).save()

    assert derived_ordinals["7"]=="seven", "Accessing own parameter of a stored object"
    assert derived_ordinals[3]=="three", "Accessing inherited (unstored) parameter of a stored object"
    base_ordinals.save()
    assert derived_ordinals["1"]=="one", "Accessing inherited (stored) parameter of a stored object"

    base_ordinals[4]="four"
    base_ordinals.save()
    assert base_ordinals["4"]=="four", "Accessing inherited (added) parameter of a stored object"

    # FIXME: add examples entries with code, and call that code

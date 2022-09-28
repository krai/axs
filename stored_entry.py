#!/usr/bin/env python3

import imp
import json
import logging
import os
import shutil
import sys
import uuid

import ufun
from runnable import Runnable


class Entry(Runnable):
    "An Entry is a Runnable stored in the file system"

    FILENAME_parameters     = 'data_axs.json'
    MODULENAME_functions    = 'code_axs'     # the actual filename ends in .py
    PREFIX_gen_entryname    = 'generated_entry_'

    def __init__(self, entry_path=None, parameters_path=None, module_name=None, container=None, generated_name_prefix=None, **kwargs):
        "Accept setting entry_path in addition to parent's parameters"

        self.generated_name_prefix  = generated_name_prefix or self.PREFIX_gen_entryname
        self.container_object       = container

        if entry_path:
            self.set_path(entry_path)
        else:
            self.entry_path         = None  # an obligatory placeholder

        self.parameters_path        = parameters_path
        self.module_name            = module_name or self.MODULENAME_functions

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

        if new_path.startswith(os.path.sep):    # absolute path
            self.entry_path = new_path

        elif self.container_object:             # relative to container
            self.entry_path = os.path.join( self.container_object.get_path( new_path ) )

        else:                                   # relative to cwd
            self.entry_path = os.path.realpath( new_path )

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
                file_name = os.path.sep.join(file_name)

            if file_name.startswith(os.path.sep):
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
        return self.get_path(self.dig(key_path))


    def trim_path(self, input_path):
        """Transform path to relative-to-entry if inside entry, or absolute if outside
        """
        if input_path.startswith( os.path.sep ):                    # given as absolute
            real_input_path     = os.path.realpath( input_path )
            real_entry_path_tr  = os.path.realpath( self.entry_path ) + os.path.sep

            if real_input_path.startswith( real_entry_path_tr ):    # absolute and inside => trim
                return real_input_path[ len(real_entry_path_tr): ]
            else:                                                   # absolute, but outside => keep
                return input_path
        else:                                                       # relative, assume inside => keep
            return input_path


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


    def own_data(self, data_dict=None):
        """Lazy-load, cache and return own data from the file system

Usage examples :
                axs byname base_map , own_data
                axs byname derived_map , own_data
        """

        if data_dict is not None:
            self.own_data_cache = data_dict
            self.parent_objects = None  # magic request to reload the parents
            return self

        elif self.own_data_cache is None:   # lazy-loading condition
            parameters_path = self.get_parameters_path()
            if os.path.isfile( parameters_path ):
                self.own_data_cache = ufun.load_json( parameters_path )
                self.touch('_AFTER_DATA_LOADING')
            else:
                logging.warning(f"[{self.get_name()}] parameters file {parameters_path} did not exist, initializing to empty parameters")
                self.own_data_cache = {}

        return self.own_data_cache


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

                try:
                    (open_file_descriptor, path_to_module, module_description) = imp.find_module( module_name, [entry_path] )
                except ImportError as e:
                    self.own_functions_cache = False
                else:
                    self.own_functions_cache = False    # to avoid infinite recursion
                    self.touch('_BEFORE_CODE_LOADING')
                    sys.path.insert( 0, entry_path )    # allow (and prefer) code imports local to the entry
                    self.own_functions_cache = imp.load_module(path_to_module, open_file_descriptor, path_to_module, module_description) or False
                    sys.path.pop( 0 )                   # /allow (and prefer) code imports local to the entry

            else:
                logging.debug(f"[{self.get_name()}] The entry does not have a path, so no functions either")
                self.own_functions_cache = False

        return self.own_functions_cache


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


    def save(self, new_path=None):
        """Store [updated] own_data of the entry
            Note1: the entry didn't have to have existed prior to saving
            Note2: only parameters get stored

Usage examples :
                axs fresh_entry coordinates , plant x 10 y -5 , save
                axs fresh_entry , plant contained_entries '---={}' _parent_entries --,:=AS^IS:^:core_collection , save new_collection
        """

        # FIXME: cache_replace() should be called even if new_path not defined, but it's the first time the entry is saved
        if new_path:
            self.get_kernel().cache_replace(self.parameters_path or self.entry_path, new_path, self)

            self.set_path( new_path )
            self.parameters_path    = None
            self.name               = None

        parameters_full_path        = self.get_parameters_path()

        # Autovivify the directories in between if necessary:
        parameters_dirname      = os.path.dirname( parameters_full_path )
        if parameters_dirname and not os.path.exists(parameters_dirname):
            os.makedirs(parameters_dirname)

        json_data   = json.dumps( self.pickle_struct(self.own_data()) , indent=4)
        with open(parameters_full_path, "w") as json_fd:
            json_fd.write( json_data+"\n" )

        logging.warning(f"[{self.get_name()}] parameters {json_data} saved to '{parameters_full_path}'")

        self.call('attach')

        return self


    def remove(self):
        """Delete the entry from the file system (keeping the memory shadow)

Usage examples :
                axs byname hebrew_letters , remove
        """
        self.call('detach')

        entry_path = self.get_path('')
        if entry_path:
            shutil.rmtree(entry_path)
            logging.warning(f"[{self.get_name()}] {entry_path} removed from the filesystem")
        else:
            logging.warning(f"[{self.get_name()}] was not saved to the file system, so cannot be removed")

        self.entry_path     = None

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

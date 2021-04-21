#!/usr/bin/env python3

import imp
import json
import logging
import os
import shutil

from runnable import Runnable

class Entry(Runnable):
    "An Entry is a Runnable stored in the file system"

    FILENAME_parameters     = 'parameters.json'
    MODULENAME_functions    = 'python_code'     # the actual filename ends in .py

    def __init__(self, entry_path=None, parameters_path=None, module_name=None, container=None, **kwargs):
        "Accept setting entry_path in addition to parent's parameters"

        self.entry_path         = entry_path
        self.parameters_path    = parameters_path
        self.module_name        = module_name
        self.container_object   = container
        super().__init__(**kwargs)
        logging.debug(f"[{self.get_name()}] Initializing the Entry with entry_path={self.entry_path}, parameters_path={self.parameters_path}, module_name={self.module_name}")


    def get_path(self, file_name=None):
        """The directory path of the stored Entry, optionally joined with a given relative name.

Usage examples :
                axs byname base_map , get_path
                axs byname derived_map , get_path README.md
        """
        if file_name:
            if file_name.startswith(os.path.sep):
                return file_name
            else:
                return os.path.join(self.entry_path, file_name)
        else:
            return self.entry_path


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
        return self.module_name or self.MODULENAME_functions


    def get_container(self):
        return self.container_object


    def parameters_loaded(self):
        """Lazy-load, cache and return own parameters from the file system

Usage examples :
                axs byname base_map , parameters_loaded
                axs byname derived_map , parameters_loaded
        """

        if self.own_parameters==None:   # lazy-loading condition
            parameters_path = self.get_parameters_path()
            if os.path.isfile( parameters_path ):
                with open( parameters_path ) as json_fd:
                    self.own_parameters = json.load(json_fd)
            else:
                logging.warning(f"[{self.get_name()}] parameters file {parameters_path} did not exist, initializing to empty parameters")
                self.own_parameters = {}

        return self.own_parameters


    def functions_loaded(self):
        """Lazy-load and cache functions from the file system

            Note the convention:
                stored None means "not loaded yet", as in "cached value missing"
                whereas stored False means "this object has no code to load", "nothing to see here".

Usage examples :
                axs byname be_like , functions_loaded
                axs byname dont_be_like , functions_loaded
        """
        if self.module_object==None:    # lazy-loading condition
            entry_path = self.get_path()
            if entry_path:
                module_name = self.get_module_name()
                try:
                    (open_file_descriptor, path_to_module, module_description) = imp.find_module( module_name, [entry_path] )

                    self.module_object = imp.load_module(path_to_module, open_file_descriptor, path_to_module, module_description) or False
                except ImportError as e:
                    self.module_object = False
            else:
                logging.debug(f"[{self.get_name()}] The entry does not have a path, so no functions either")
                self.module_object = False

        return self.module_object


    def save(self):
        """Store [updated] own_parameters of the entry
            Note1: the entry didn't have to have existed prior to saving
            Note2: only parameters get stored

Usage examples :
                axs bypath foo_entry , save --x=new_x_value --y=new_y_value
                axs bypath new_collection , save ---contained_entries='{}' --parent_entries^,=^core_collection
        """

        parameters_full_path    = self.get_parameters_path()

        # Autovivify the directories in between if necessary:
        parameters_dirname      = os.path.dirname( parameters_full_path )
        if parameters_dirname and not os.path.exists(parameters_dirname):
            os.makedirs(parameters_dirname)

        # Store the [potentially updated] own_parameters:
        own_parameters          = self.parameters_loaded()
        json_data               = json.dumps(own_parameters, indent=4)
        with open(parameters_full_path, "w") as json_fd:
            json_fd.write( json_data+"\n" )

        logging.warning(f"[{self.get_name()}] parameters {json_data} saved to '{parameters_full_path}'")

        return self


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(funcName)s %(message)s")

    print('-'*40 + ' Entry direct creation and storing: ' + '-'*40)

    base_ordinals = Entry(entry_path='base_ordinals', own_parameters={
        "0": "zero",
        "1": "one",
        "2": "two",
        "3": "three",
    })
    assert base_ordinals[2]=="two", "Accessing own parameter of an unstored object"

    derived_ordinals = Entry(entry_path='derived_ordinals', own_parameters={
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

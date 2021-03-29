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
    PARAMNAME_parent_path   = 'parent_path'

    def __init__(self, entry_path=None, kernel=None, **kwargs):
        "Accept setting entry_path in addition to parent's parameters"

        self.entry_path = entry_path
        self.kernel     = kernel
        super().__init__(**kwargs)
        logging.debug(f"[{self.get_name()}] Initializing the Entry with entry_path={self.entry_path} and kernel={self.kernel}")


    def get_path(self, file_name=None):
        """The directory path of the stored Entry, optionally joined with a given relative name.

Usage examples :
                axs byname base_map , get_path
                axs byname derived_map , get_path README.md
        """
        if file_name:
            if file_name.startswith('/'):
                return file_name
            else:
                return os.path.join(self.entry_path, file_name)
        else:
            return self.entry_path


    def get_kernel(self):
        return self.kernel


    def get_name(self):
        return self.entry_path and os.path.basename(self.entry_path)


    def parameters_loaded(self):
        """Lazy-load, cache and return own parameters from the file system

Usage examples :
                axs byname base_map , parameters_loaded
                axs byname derived_map , parameters_loaded
        """

        if self.own_parameters==None:   # lazy-loading condition
            parameters_full_path = self.get_path( self.FILENAME_parameters )
            if os.path.isfile( parameters_full_path ):
                with open( parameters_full_path ) as json_fd:
                    self.own_parameters = json.load(json_fd)
            else:
                self.own_parameters = {}

        return self.own_parameters


    def functions_loaded(self, module_name=MODULENAME_functions):
        """Lazy-load and cache functions from the file system

            Note the convention:
                stored None means "not loaded yet", as in "cached value missing"
                whereas stored False means "this object has no code to load", "nothing to see here".

Usage examples :
                axs byname be_like , functions_loaded
                axs byname dont_be_like , functions_loaded
                axs byname dont_be_like , functions_loaded alt_python_code
        """
        if self.module_object==None:    # lazy-loading condition
            try:
                (open_file_descriptor, path_to_module, module_description) = imp.find_module( module_name, [self.get_path()] )

                self.module_object = imp.load_module(path_to_module, open_file_descriptor, path_to_module, module_description) or False
            except ImportError as e:
                self.module_object = False

        return self.module_object


    def parent_loaded(self):
        if self.parent_object==None:     # lazy-loading condition
            parent_path = self.parameters_loaded().get( self.PARAMNAME_parent_path )    # only look into own_parameters to avoid infinite recursion
            if parent_path:
                full_parent_path    = self.get_path(parent_path)    # extend the relative path, but preserve absolute one
                ak                  = self.get_kernel()             # go through the kernel, if available:
                self.parent_object  = ak.bypath(entry_path=full_parent_path) if ak else Entry(entry_path=full_parent_path)
            else:
                self.parent_object  = False

        return self.parent_object


    def save(self, update=None, new_path=None):
        """Store [updated] own_parameters of the entry back or to a new location.
            Note: only parameters get stored.

Usage examples :
                axs byname derived_map , save --new_path=derived_map_copy
        """
        own_parameters = self.parameters_loaded()   # Note the order!
        if update:
            own_parameters.update( update )

        if new_path:
            if not os.path.exists(new_path):    # Autovivify the directories in between if necessary
                os.makedirs(new_path)

            self.entry_path = new_path

        parameters_full_path = self.get_path( self.FILENAME_parameters )
        with open(parameters_full_path, "w") as json_fd:
            json_fd.write( json.dumps(own_parameters, indent=4)+'\n' )

        logging.debug(f"[{self.get_name()}] parameters saved")

        return own_parameters


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(funcName)s %(message)s")

    print('-'*40 + ' Entry direct loading and access: ' + '-'*40)

    base_map = Entry(entry_path='./base_map')
    print(f"base_map.get_path()={base_map.get_path()}")
    print(f"base_map['first']={base_map['first']}")
    print(f"base_map.get('fourth')={base_map.get('fourth')}")
    print("")

    derived_map = Entry(entry_path='./derived_map')
    print(f"derived_map.get_path()={derived_map.get_path()}")
    print(f"derived_map['fourth']={derived_map['fourth']}")
    print(f"derived_map['second']={derived_map['second']}")
    print("")

    base_map.save( new_path='copy_base_map' )
    print("")

    derived_map.save( update={'sixth':'sechste'}, new_path='extended_derived_map' )
    print("")

    dont_be_like    = Entry(entry_path='./dont_be_like')
    print(f"dont_be_like.call('meme',['wrote an OS that everybody hates'],{{'quality':'selfish'}})={dont_be_like.call('meme',['wrote an OS that everybody hates'],{'quality':'selfish','person2':'everybody'})}")


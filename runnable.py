#!/usr/bin/env python3

import logging

import function_access
from param_source import ParamSource

class Runnable(ParamSource):
    """ An object of Runnable class is a non-persistent container of parameters (inherited) and code (own)
        that may optionally also have a parent object of the same class.

        It can run a method of its own or inherited using own or inherited parameters.
    """

    def __init__(self, module_object=None, **kwargs):
        "Accept setting module_object in addition to parent's parameters"

        self.module_object  = module_object
        super().__init__(**kwargs)
        logging.debug(f"[{self.get_name()}] Initializing the Runnable with {repr(self.module_object)+' as module_object' if self.module_object else 'no module_object'}")


    def module_loaded(self):
        """ Placeholder for lazy-loading code in subclasses that support it.

            Note the convention:
                stored None means "not loaded yet", as in "cached value missing"
                whereas stored False means "this object has no code to load", "nothing to see here".
        """

        return self.module_object or False


    def reach_method(self, function_name, _ancestry_path=None):
        "Recursively find a method for the given entry - either its own or belonging to one of its parents."

        if _ancestry_path == None:
            _ancestry_path = []

        _ancestry_path += [ self.get_name() ]
        try:
            module_object   = self.module_loaded()
            function_object = getattr(module_object, function_name)
        except (ImportError, AttributeError) as e:
            if self.parent_loaded():
                return self.parent_object.reach_method(function_name, _ancestry_path)
            else:
                raise NameError( "could not find the method '{}' along the ancestry path '{}'".format(function_name, ' --> '.join(_ancestry_path) ) )

        return function_object


    def help(self, method_name=None):
        """ Recursively reach for the method and examine its DocString and calling signature.

            Usage example:
                clic additive help
                clic additive help inc
        """
        print( "Entry:         {}".format( self.get_name() ) )

        if method_name:
            print( "Method:        {}".format( method_name ) )
            try:
                ancestry_path   = []
                function_object = self.reach_method(method_name, _ancestry_path=ancestry_path) # the method may not be reachable

                required_arg_names, optional_arg_names, method_defaults, varargs, varkw = function_access.expected_call_structure(function_object)

                signature = ', '.join(required_arg_names + [optional_arg_names[i]+'='+str(method_defaults[i]) for i in range(len(optional_arg_names))] )

                if varargs or varkw:
                    print( """NB: this method cannot be called via our calling mechanism,
                              because it makes use of variable arguments (*) or variable keywords (**)""" )

                print( "MethodPath:    {}".format( function_object.__module__ ))
                print( "Ancestry path: {}".format( ' --> '.join(ancestry_path) ))
                print( "Signature:     {}({})".format( method_name, signature ))
                print( "DocString:    {}".format( function_object.__doc__ ))
            except Exception as e:
                logging.error( str(e) )
        else:
            try:
                module_object   = self.module_loaded()      # the entry may not contain any code...
                doc_string      = module_object.__doc__     # the module may not contain any DocString...
                print( "DocString:    {}".format(doc_string))
            except ImportError:
                parent_may_know = ", but you may want to check its parent: "+self.parent_object.get_name() if self.parent_loaded() else ""
                print("This entry has no code of its own" + parent_may_know)
            except Exception as e:
                logging.error( str(e) )


    def call(self, function_name, pos_params=None, override_dict=None):
        """ Call a given method of a given entry and feed it
            with arguments from the current object optionally overridden by a given dictionary.

            The function can have a mix of positional args and named args with optional defaults.
        """

        runnable = Runnable(name="override", own_parameters=override_dict, parent_object=self) if override_dict else self

        try:
            pos_params          = pos_params or []
            function_object     = self.reach_method(function_name)

            """
            merged_params.update( {             # These special parameters are non-overridable at the moment. Should they be?
                '__kernel__'    : self.kernel,
                '__entry__'     : self,
            } )
            """

            result = function_access.feed_a_function(function_object, pos_params, runnable)
        except NameError as method_not_found_e:
            try:
                entry_method_object = getattr(runnable, function_name)
                result = function_access.feed_a_function(entry_method_object, pos_params, runnable, class_method=True)
            except AttributeError:
                raise method_not_found_e

        return result


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(funcName)s %(message)s")

    print('-'*40 + ' Creating a hierarchy of Runnables: ' + '-'*40)

    from argparse import Namespace

    def plus_one(number):
        "Adds 1 to the argument"
        return number+1

    def trice(number):
        "Multiplies the argument by 3"
        return number*3

    granddad    = Runnable(name='granddad', module_object=Namespace( add_one=plus_one, subtract_one=(lambda x: x-1)  ) )
    dad         = Runnable(name='dad',      module_object=Namespace( double=(lambda x: x*2), triple=trice                   ), parent_object=granddad)
    child       = Runnable(name='child',    module_object=Namespace( square=(lambda x: x*x)                                 ), parent_object=dad)


    print('-'*40 + ' Testing reach_method(): ' + '-'*40)

    path_to_method = []
    result = child.reach_method('square', path_to_method)(12)
    print(f"square(12)={result}, path to the method: {path_to_method}")

    path_to_method = []
    result = child.reach_method('add_one', path_to_method)(12)
    print(f"add_one(12)={result}, path to the method: {path_to_method}")

    path_to_method = []
    result = child.reach_method('double', path_to_method)(12)
    print(f"double(12)={result}, path to the method: {path_to_method}")


    print('-'*40 + ' Testing help(): ' + '-'*40)

    child.help(method_name='triple')
    print("")
    child.help(method_name='add_one')


    print('-'*40 + ' Testing call(): ' + '-'*40)

    print(f"child.call('double', [20])={child.call('double', [20])}\n")
    print(f"child.call('triple', override_dict=dict('number': 11))={child.call('triple', override_dict={'number': 11} )}\n")

    dad['x']=100
    print(f"child.call('subtract_one')={child.call('subtract_one')}\n")
    print(f"child.call('square')={child.call('square')}\n")

    print(f"child.call('get', ['x'])={child.call('get', ['x'])}\n")

    try:
        print(f"child.call('nonexistent')={child.call('nonexistent')}\n")
    except NameError as e:
        print(e)

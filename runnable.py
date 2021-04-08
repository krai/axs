#!/usr/bin/env python3

import logging

import function_access
from param_source import ParamSource
from copy import copy

class Runnable(ParamSource):
    """An object of Runnable class is a non-persistent container of parameters (inherited) and code (own)
        that may optionally also have a parent object of the same class.

        It can run an own or inherited action using own or inherited parameters.
    """

    def __init__(self, module_object=None, kernel=None, **kwargs):
        "Accept setting module_object and kernel in addition to parent's parameters"

        self.module_object  = module_object
        self.kernel         = kernel
        super().__init__(**kwargs)
        logging.debug(f"[{self.get_name()}] Initializing the Runnable with {repr(self.module_object)+' as module_object' if self.module_object else 'no module_object'} and kernel={self.kernel}")


    def get_kernel(self):
        return self.kernel


    def functions_loaded(self):
        """Placeholder for lazy-loading code in subclasses that support it.

            Note the convention:
                stored None means "not loaded yet", as in "cached value missing"
                whereas stored False means "this object has no code to load", "nothing to see here".
        """

        return self.module_object or False


    def list_own_functions(self):
        """A lightweight method to list all own methods of an entry

Usage examples :
                axs byname be_like , list_own_functions
                axs byname shell , list_own_functions
        """
        module_object = self.functions_loaded()
        return function_access.list_function_names(module_object) if module_object else []


    def reach_function(self, function_name, _ancestry_path):
        "Recursively find a Runnable's function - either its own or belonging to the nearest parent."

        _ancestry_path.append( self.get_name() )

        module_object   = self.functions_loaded()

        if hasattr(module_object, function_name):
            return getattr(module_object, function_name)
        else:
            found_function = None
            for parent_object in self.parents_loaded():
                found_function = parent_object.reach_function(function_name, _ancestry_path)
                if found_function:
                    break
                else:
                    _ancestry_path.pop()

            return found_function


    def reach_action(self, action_name, _ancestry_path=None):
        "First try to reach for a Runnable's function (externally loaded code), if unavailable - try Runnable's method instead."

        if _ancestry_path == None:  # if we have to initialize it internally, the value will be lost to the caller
            _ancestry_path = []

        function_object = self.reach_function( action_name, _ancestry_path )
        if function_object:
            return function_object
        elif hasattr(self, action_name):
            _ancestry_path.clear()  # empty the specific list given to us - a form of feedback
            return getattr(self, action_name)
        else:
            raise NameError( "could not find the action '{}' neither along the ancestry path '{}' nor in the {} class".
                              format(action_name, ' --> '.join(_ancestry_path),  self.__class__.__name__) )


    def help(self, action_name=None):
        """Reach for a Runnable's function or method and examine its DocString and calling signature.

Usage examples :
                axs help
                axs help help
                axs help substitute
                axs byname be_like , help
                axs byname dont_be_like , help meme
                axs byname dont_be_like , help get
        """

        common_format = "{:15s}: {}"
        entry_class = self.__class__

        print( common_format.format( entry_class.__name__+' class', entry_class.__doc__ ))
        print( common_format.format( 'Class methods', function_access.list_function_names(entry_class) ))

        print('')
        print( common_format.format( 'Specific '+entry_class.__name__, self.get_name() ))

        if action_name:
            try:
                ancestry_path   = []
                action_object   = self.reach_action(action_name, _ancestry_path=ancestry_path)

                required_arg_names, optional_arg_names, action_defaults, varargs, varkw = function_access.expected_call_structure( action_object )

                signature = ', '.join(required_arg_names + [optional_arg_names[i]+'='+str(action_defaults[i]) for i in range(len(optional_arg_names))] )

                if varargs or varkw:
                    print( """NB: this action cannot be called via our calling mechanism,
                              because it makes use of variable arguments (*) or variable keywords (**)""" )

                if ancestry_path:
                    print( common_format.format('Function', action_name ))
                    print( common_format.format('Ancestry path', ' --> '.join(ancestry_path) ))
                else:
                    print( common_format.format( 'Method', action_name ))
                    print( common_format.format( 'Declared in', action_object.__module__+'.py' ))

                print( common_format.format( 'Signature', action_name+'('+signature+')' ))
                print( common_format.format( 'DocString', action_object.__doc__ ))
            except Exception as e:
                logging.error( str(e) )
        else:
            module_object   = self.functions_loaded()     # the entry may not contain any code...
            if module_object:
                doc_string      = module_object.__doc__     # the module may not contain any DocString...
                print( common_format.format('Description', doc_string))
                print( common_format.format('OwnFunctions', self.list_own_functions()))
            else:
                parents_names   = self.get_parents_names()
                parents_may_know = ", but you may want to check its parents: "+parents_names if parents_names else ""
                print("This Runnable has no loadable functions" + parents_may_know)


    def call(self, action_name, pos_params=None, override_dict=None, pos_preps=None):
        """Call a given function or method of a given entry and feed it
            with arguments from the current object optionally overridden by a given dictionary.

            The action can have a mix of positional args and named args with optional defaults.
        """

        if override_dict:
            self.parameters_loaded().update( override_dict )

        pos_params = pos_params or []

        # deferred substitution/execution of positional arguments
        if pos_preps:
            for idx in range(len(pos_params)):
                prep = pos_preps[idx]
                if prep in ('#', '*'):
                    if prep=='*':   # The order is important for nested executions that may want to perform their own substitutions
                        pos_params[idx] = self.execute( pos_params[idx] )
                    pos_params[idx] = self.substitute( pos_params[idx] )


        action_object   = self.reach_action(action_name)
        result          = function_access.feed(action_object, pos_params, self)

        return result


    def execute(self, pipeline):
        """Execute a parsed pipeline (a chain of calls that starts from the kernel object)
        """

        results = self.get_kernel()
        for call_params in pipeline:
            results = results.call(*call_params)
        return results


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

    granddad    = Runnable(name='granddad', module_object=Namespace( add_one=plus_one, subtract_one=(lambda x: x-1)         ) )
    dad         = Runnable(name='dad',      module_object=Namespace( double=(lambda x: x*2), triple=trice                   ), parent_objects=[granddad])
    mum         = Runnable(name='mum',      module_object=Namespace( cube=(lambda x: x*x*x)                                 ) )
    child       = Runnable(name='child',    module_object=Namespace( square=(lambda x: x*x)                                 ), parent_objects=[dad, mum])


    print(f"granddad can run: {granddad.list_own_functions()}")
    print(f"dad can run: {dad.list_own_functions()}")
    print(f"mum can run: {mum.list_own_functions()}")
    print(f"child can run: {child.list_own_functions()}")

    print('-'*40 + ' Testing reach_action(): ' + '-'*40)

    path_to_function = []
    result = child.reach_action('square', path_to_function)(12)
    print(f"square(12)={result}, path to the function: {path_to_function}")

    path_to_function = []
    result = child.reach_action('add_one', path_to_function)(12)
    print(f"add_one(12)={result}, path to the function: {path_to_function}")

    path_to_function = []
    result = child.reach_action('double', path_to_function)(12)
    print(f"double(12)={result}, path to the function: {path_to_function}")

    path_to_function = []
    result = child.reach_action('cube', path_to_function)(12)
    print(f"cube(12)={result}, path to the function: {path_to_function}")


    print('-'*40 + ' Testing help(): ' + '-'*40)

    child.help('triple')
    print("")
    child.help('add_one')


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

#!/usr/bin/env python3

import logging
import re

import function_access
from param_source import ParamSource
from copy import deepcopy

class Runnable(ParamSource):
    """An object of Runnable class is a non-persistent container of parameters (inherited) and code (own)
        that may optionally also have a parent object of the same class.

        It can run an own or inherited action using own or inherited parameters.
    """

    ESCAPE_do_not_process           = 'AS^IS'

    def __init__(self, own_functions=None, kernel=None, **kwargs):
        "Accept setting own_functions and kernel in addition to parent's parameters"

        self.own_functions_cache    = own_functions
        self.kernel                 = kernel
        self.call_cache             = {}

        super().__init__(**kwargs)
        logging.debug(f"[{self.get_name()}] Initializing the Runnable with {self.list_own_functions() if self.own_functions_cache else 'no'} pre-loaded functions and kernel={self.kernel}")


    def get_kernel(self):
        return self.kernel


    def own_functions(self):
        """Placeholder for lazy-loading code in subclasses that support it.

            Note the convention:
                stored None means "not loaded yet", as in "cached value missing"
                whereas stored False means "this object has no code to load", "nothing to see here".
        """

        return self.own_functions_cache or False


    def list_own_functions(self):
        """A lightweight method to list all own methods of an entry

Usage examples :
                axs byname be_like , list_own_functions
                axs byname shell , list_own_functions
        """
        own_functions = self.own_functions()
        return function_access.list_function_names(own_functions) if own_functions else []


    def reach_function(self, function_name, _ancestry_path):
        "Recursively find a Runnable's function - either its own or belonging to the nearest parent."

        _ancestry_path.append( self.get_name() )

        own_functions   = self.own_functions()

        if hasattr(own_functions, function_name):
            return getattr(own_functions, function_name)
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

        logging.debug(f"[{self.get_name()}] reach_action({action_name}) ...")
        if _ancestry_path == None:  # if we have to initialize it internally, the value will be lost to the caller
            _ancestry_path = []

        function_object = self.reach_function( action_name, _ancestry_path )
        if function_object:
            logging.debug(f"[{self.get_name()}] reach_action({action_name}) was found as a function")

            return function_object
        elif hasattr(self, action_name):
            logging.debug(f"[{self.get_name()}] reach_action({action_name}) was found as a class method")

            _ancestry_path.clear()  # empty the specific list given to us - a form of feedback
            return getattr(self, action_name)
        else:
            raise NameError( "could not find the action '{}' neither along the ancestry path '{}' nor in the {} class".
                              format(action_name, ' --> '.join(_ancestry_path),  self.__class__.__name__) )


    def can(self, action_name):
        "Returns whether object has such an action or not (a boolean)"

        try:
            self.reach_action(action_name)
            return True
        except NameError:
            return False


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
        help_buffer = []
        common_format = "{:15s}: {}"
        entry_class = self.__class__

        help_buffer.append( common_format.format( entry_class.__name__+' class', entry_class.__doc__ ))
        help_buffer.append( common_format.format( 'Class methods', function_access.list_function_names(entry_class) ))

        help_buffer.append('')
        help_buffer.append( common_format.format( 'Specific '+entry_class.__name__, self.get_name() ))

        if action_name:
            try:
                ancestry_path   = []
                action_object   = self.reach_action(action_name, _ancestry_path=ancestry_path)

                required_arg_names, optional_arg_names, action_defaults, varargs, varkw = function_access.expected_call_structure( action_object )

                if varargs:
                    required_arg_names.append( '*'+varargs )

                signature = ', '.join(required_arg_names + [optional_arg_names[i]+'='+str(action_defaults[i]) for i in range(len(optional_arg_names))] )

                if varkw:
                    help_buffer.append( """NB: this action cannot be called via our calling mechanism,
                              because it makes use of variable keywords (**)""" )

                if ancestry_path:
                    help_buffer.append( common_format.format('Function', action_name ))
                    help_buffer.append( common_format.format('Ancestry path', ' --> '.join(ancestry_path) ))
                else:
                    help_buffer.append( common_format.format( 'Method', action_name ))
                    help_buffer.append( common_format.format( 'Declared in', action_object.__module__+'.py' ))

                help_buffer.append( common_format.format( 'Signature', action_name+'('+signature+')' ))
                help_buffer.append( common_format.format( 'DocString', action_object.__doc__ ))
            except Exception as e:
                logging.error( str(e) )
        else:
            own_functions   = self.own_functions()     # the entry may not contain any code...
            if own_functions:
                doc_string      = own_functions.__doc__     # the module may not contain any DocString...
                help_buffer.append( common_format.format('Description', doc_string))
                help_buffer.append( common_format.format('OwnFunctions', self.list_own_functions()))
            else:
                parents_names   = self.get_parents_names()
                parents_may_know = ", but you may want to check its parents: "+parents_names if parents_names else ""
                help_buffer.append("This Runnable has no loadable functions" + parents_may_know)

        return '\n'.join(help_buffer)


    def __getitem__(self, param_name, parent_recursion=None):
        """Lazy parameter access: returns the parameter value from self or the closest parent,
            automatically executing nested_calls on the result.
        """
        if param_name=='__entry__':
            return self
        elif param_name=='__record_entry__':
            return True     # a placeholder to be substituted later

        try:
            getitem_gen         = self.getitem_generator( str(param_name), parent_recursion )
            unprocessed_value   = next(getitem_gen)

        except StopIteration:
            logging.debug(f"[{self.get_name()}]  I don't have parameter '{param_name}', and neither do the parents - raising KeyError")
            raise KeyError(param_name)

        param_value = self.nested_calls(unprocessed_value)
        logging.debug(f"[{self.get_name()}]  Got {param_name}={param_value}")

        return param_value


    def call(self, action_name, pos_params=None, override_dict=None, deterministic=True, call_record_entry_ptr=None):
        """Call a given function or method of a given entry and feed it
            with arguments from the current object optionally overridden by a given dictionary.

            The action can have a mix of positional args and named args with optional defaults.

            Currently all calls are assumed to be deterministic, and their results are cached (subject to context):
                axs mi: fresh_entry , plant alpha 10  beta 20  formula --:='AS^IS:^^:substitute:#{alpha}#-#{beta}#' , get formula
                axs mi: fresh_entry , plant alpha 10  beta 20  formula --:='AS^IS:^^:substitute:#{alpha}#-#{beta}#' , get formula , get mi , get formula
                axs mi: fresh_entry , plant alpha 10  beta 20  formula --:='AS^IS:^^:substitute:#{alpha}#-#{beta}#' , get formula , get mi , get formula --alpha=100
        """

        def unidict(d):
            "Unique dictionary representation, used for hashing"

            return '{'+(','.join([ repr(k)+':'+repr(d[k]) for k in sorted(d.keys()) ]))+'}' if type(d)==dict else repr(d)


        logging.debug(f'[{self.get_name()}]  calling action {action_name} with pos_params={pos_params} and override_dict={override_dict} ...')

        cache_tail = '+'.join([unidict(s.own_data()) for s in self.runtime_stack()]) + '+' + unidict(override_dict)
        cache_key = action_name + str(pos_params) + cache_tail

        if deterministic and (cache_key in self.call_cache):
            cached_value = self.call_cache[cache_key]
            logging.debug(f"[{self.get_name()}]  Call '{cache_key}' is FOUND IN CACHE, returning {cached_value}")
            return cached_value
        else:
            logging.debug(f"[{self.get_name()}]  Call '{cache_key}' NOT TAKEN from cache, have to run...")

        if not pos_params:
            pos_params = []                                 # allow pos_params to be missing
        elif type(pos_params)==list:
            pos_params = self.nested_calls(pos_params)      # perform all nested calls if there are any
        else:
            pos_params = [ pos_params ]                     # simplified syntax for single positional parameter actions

        rt_call_specific    = ParamSource(name='rt_call_specific', own_data=override_dict or {})   # FIXME: overlapping entry names are not unique
        self.runtime_stack().append( rt_call_specific )

        action_object       = self.reach_action(action_name)
        captured_mapping    = {}    # retain the pointer to perform modifications later
        action_object, joint_arg_tuple, optional_arg_dict   = function_access.prep(action_object, pos_params, self, captured_mapping)

        ak = self.get_kernel()
        if ak:
            call_record_entry   = ak.fresh_entry(container=ak.record_container(), own_data=captured_mapping, generated_name_prefix=f"generated_by_{action_name}_")

            call_record_entry["_parent_entries"] = [ self ]

            if call_record_entry.get("action_name") != action_name:
                call_record_entry["action_name"] = action_name

            if call_record_entry_ptr is not None:   # making it available to the pipeline
                call_record_entry_ptr.append( call_record_entry )

            if '__record_entry__' in optional_arg_dict:     # it's a placeholder which we have to substitute
                if captured_mapping:
                    for a in ('__entry__', '__record_entry__'):
                        if a in captured_mapping:
                            del captured_mapping[a]

                optional_arg_dict['__record_entry__'] = call_record_entry

        result          = function_access.feed(action_object, joint_arg_tuple, optional_arg_dict)

        self.runtime_stack().pop()

        if ak:
            call_record_entry['__result__'] = result    # only visible if save()d after execution (not all application cases)

        logging.debug(f'[{self.get_name()}]  called action {action_name} with "{pos_params}", got "{result}"')
        self.call_cache[cache_key] = result

        return result


    def nested_calls(self, unprocessed_struct):
        """Walk over the structure and perform any nested calls found in it.
            Can be quite expensive for large structures, but ok for a prototype.

Usage examples :
                axs noop  --:='^^:substitute:#{alpha}#-#{beta}#' --alpha=11 --beta=22
                axs noop  --:='AS^IS:^^:substitute:#{alpha}#-#{beta}#'
                axs nested_calls  --:='AS^IS:^^:substitute:#{alpha}#-#{beta}#' --alpha=11 --beta=22
        """

        side_effects_count = 0

        def nested_calls_rec(input_structure):
            nonlocal side_effects_count

            if type(input_structure)==list and len(input_structure):
                head = input_structure[0]
                if head=='^^':
                    side_effects_count += 1
                    return self.call( *input_structure[1:] )
                elif head=='^':
                    side_effects_count += 1
                    return self.get_kernel().call( *input_structure[1:] )
                elif head==self.ESCAPE_do_not_process:
                    side_effects_count += 1                                                         # it is only a "side effect" for the purposes of our GC-facilitating decision making below
                    return deepcopy( input_structure[1:] )                                          # drop the escape symbol, keeping the rest of the substructure intact
                else:
                    return [ nested_calls_rec(elem) for elem in input_structure ]                   # list elements are substituted
            elif type(input_structure)==dict:
                if self.ESCAPE_do_not_process in input_structure:
                    side_effects_count += 1                                                         # it is only a "side effect" for the purposes of our GC-facilitating decision making below
                    return deepcopy( input_structure[self.ESCAPE_do_not_process] )                  # follow just this one key (keeping the value intact), NB: all other keys of the dict are ignored
                else:
                    return { k : nested_calls_rec(input_structure[k]) for k in input_structure }    # only values are substituted
            else:
                return input_structure

        processed_struct = nested_calls_rec(unprocessed_struct)

        return processed_struct if side_effects_count else unprocessed_struct                   # keeping the original if unchanged should help with GC


    def execute(self, pipeline):
        """Execute a parsed pipeline (a chain of calls that starts from the kernel object).
            Whenever a result returned by a function is NOT an Runnable, the execution resets back to the kernel object.

Usage examples :
                axs si: byname sysinfo , substitute '#{os}#--#{ar}#' --os:=^^:dig:si.osname --ar:=^^:dig:si.arch
                axs si: byname sysinfo , os: dig si.osname , ar: dig si.arch , substitute '#{os}#--#{ar}#'
                axs si: byname sysinfo , os: dig si.osname , ar: dig si.arch , rt_pipeline_entry , save
                axs rt_pipeline_entry , old_dir: cd , si: byname sysinfo , os: dig si.osname , ar: dig si.arch , get si , run 'echo "Hello, world!" >README.txt' , rt_pipeline_entry , save
                axs bypath only_code/iterative.py , :rec: factorial 5 , get rec , save factorial_of_5

            # Record a call:
                axs bypath only_code/iterative.py , :rec: factorial 5 , get rec , save factorial_of_5
            # Replay:
                axs bypath factorial_of_5 , call
        """
        ak = self.get_kernel()
        rt_pipeline_wide = ak.bypath(path='rt_pipeline_wide', own_data={})

        result = self
        for call_params in pipeline:
            entry = result if hasattr(result, 'call') else self

            entry.runtime_stack().append( rt_pipeline_wide )

            output_label    = call_params.pop(3) if len(call_params)>3 else None    # NB: the order is important!
            input_label     = call_params.pop(3) if len(call_params)>3 else None

            call_record_entry_ptr = []  # the value of call_record_entry is returned via appending to this empty list
            result = entry.call(*call_params, call_record_entry_ptr=call_record_entry_ptr)

            entry.runtime_stack().pop()

            if input_label:
                rt_pipeline_wide[input_label] = call_record_entry_ptr[0]

            if output_label:
                rt_pipeline_wide[output_label] = result

        return result


    def python_api(self, src_text, line_sep='\\n'):
        """Execute the given string as piece of Python code in the current Python interpreter and its environment.
            You can have multiple semicolon-separated commands on a line by using a non-default line separator.
            A value can be returned (and properly integrated into the pipeline) by assigning it to _ variable.

Careful with that axe, Eugene: a potential security risk.

Usage examples :
                axs python_api 'print( len([10, 20, 30]) )''
                axs python_api '_= self.version().split('.')''
                axs byquery package_name=scipy , python_api 'import scipy\nfrom scipy.special import exp10\n_=exp10([1,2,5,10])'
                axs byquery package_name=numpy , python_api 'syll=self["abs_packages_dir"].split("/"); _=syll[-1]' '; '
        """
        exec( src_text.replace(line_sep, '\n') )       # working around newline encoding in shells
        return locals().get('_')


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

    granddad    = Runnable(name='granddad', own_functions=Namespace( add_one=plus_one, subtract_one=(lambda x: x-1)         ) )
    dad         = Runnable(name='dad',      own_functions=Namespace( double=(lambda x: x*2), triple=trice                   ), parent_objects=[granddad])
    mum         = Runnable(name='mum',      own_functions=Namespace( cube=(lambda x: x*x*x)                                 ) )
    child       = Runnable(name='child',    own_functions=Namespace( square=(lambda x: x*x)                                 ), parent_objects=[dad, mum])

    assert sorted(granddad.list_own_functions())==['add_one', 'subtract_one'], "granddad's own functions"
    assert sorted(dad.list_own_functions())==['double', 'triple'], "dad's own functions"

    print('-'*40 + ' Testing reach_action(): ' + '-'*40)

    assert sorted(mum.reach_action('list_own_functions')())==['cube'], "mum's own functions listed via reach_action"
    assert sorted(child.reach_action('list_own_functions')())==['square'], "child's own functionss listed via reach_action"

    input_arg = 12
    func_applied_to_input_arg = {
        "square": ("child", 144),
        "add_one": ("granddad", 13),
        "double": ("dad", 24),
        "cube": ("mum", 1728)
    }
    for func_name in func_applied_to_input_arg:
        owner_entry_name, func_value = func_applied_to_input_arg[func_name]
        path_to_function = []
        assert child.reach_action(func_name, path_to_function)(input_arg)==func_value, f"{owner_entry_name}'s function '{func_name}'"

    print('-'*40 + ' Testing help(): ' + '-'*40)

    child.help('triple')
    print("")
    child.help('add_one')

    print('-'*40 + ' Testing call(): ' + '-'*40)

    assert child.call('double', [20])==40, "call() for dad's function, positional args"
    assert child.call('triple', override_dict={'number': 11})==33, "call() for dad's function, named args"

    dad['x']=100

    assert child.call('subtract_one')==99, "call() for granddad's function, inherit arg from dad"
    assert child.call('square')==10000, "call() for child's function, inherit arg from dad"
    assert child.call('get', ['x'])==100, "call() for class method, inherit arg from dad"

    try:
        print(f"child.call('nonexistent')={child.call('nonexistent')}\n")
    except NameError as e:
        assert str(e)=="could not find the action 'nonexistent' neither along the ancestry path 'child' nor in the Runnable class"

#!/usr/bin/env python3

import inspect
import logging
import re
import sys
from copy import deepcopy

import function_access
import ufun
from param_source import ParamSource


class Runnable(ParamSource):
    """An object of Runnable class is a non-persistent container of parameters (inherited) and code (own)
        that may optionally also have a parent object of the same class.

        It can run an own or inherited action using own or inherited parameters.
    """

    pipeline_counter                = 0
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


    def reach_function(self, function_name):
        "Find a Runnable's function through the inheritance hierarchy"

        ancestor_name_order = []
        for parent_obj, ancestry_path in self.parent_generator():
            own_functions   = parent_obj.own_functions()

            if hasattr(own_functions, function_name):
                found_function = getattr(own_functions, function_name)
                if inspect.isfunction(found_function):
                    return found_function, ancestry_path
            else:
                ancestor_name_order += [ parent_obj.get_name() ]

        return None, ancestor_name_order


    def reach_action(self, action_name, _ancestry_path=None):
        "First try to reach for a Runnable's function (externally loaded code), if unavailable - try Runnable's method instead."

        logging.debug(f"[{self.get_name()}] reach_action({action_name}) ...")
        if _ancestry_path == None:  # if we have to initialize it internally, the value will be lost to the caller
            _ancestry_path = []

        function_object, ancestry_path = self.reach_function( action_name )
        if function_object:
            logging.debug(f"[{self.get_name()}] reach_action({action_name}) was found as a function")

            _ancestry_path.extend( ancestry_path )
            return function_object

        elif hasattr(self, action_name):
            logging.debug(f"[{self.get_name()}] reach_action({action_name}) was found as a class method")

            return getattr(self, action_name)
        else:
            raise NameError( "could not find the action '{}' neither among the ancestors ({}) nor in the {} class".
                              format(action_name, ', '.join(ancestry_path),  self.__class__.__name__) )


    def can(self, action_name):
        "Returns whether object has such an action or not (a boolean)"

        try:
            self.reach_action(action_name)
            return True
        except NameError:
            return False


    def possible_actions(self):
        """Support for bash autocompletion.

# Add this to your .bash_profile (or .bash_login , or .bashrc) :
# ------------------------------- >8 >8 >8 -----------------------------
_axs_comp()
{
    cur="${COMP_WORDS[COMP_CWORD]}"     # the so-far-typed part of the (first) action
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    if [[ $COMP_CWORD -eq 1 ]] ; then   # if we just started, it should be the kernel
        COMPREPLY=($(compgen -W "$(axs possible_actions ,0 func ufun.join_with)" -- "$cur" ))
    elif [[ "$prev" == "byname" ]] ; then
        COMPREPLY=($(compgen -W "$(axs work_collection , get contained_entries , keys ,0 func ufun.join_with)" -- "$cur" ))
    elif [[ "$prev" == "," ]] ; then    # hoping this assumption is more frequently right than wrong!
        COMPREPLY=($(compgen -W "$(axs fresh_entry , possible_actions ,0 func ufun.join_with)" -- "$cur" ))
    else
        COMPREPLY=()
    fi
}
complete -o bashdefault -o default -F _axs_comp axs
# ------------------------------- 8< 8< 8< -----------------------------

Usage examples :
                axs byname extractor , possible_actions
                axs <tab><tab>
                axs fresh_entry , <tab><tab>

        """
        return function_access.list_function_names( self.__class__ ) + self.list_own_functions()


    def help(self, *arguments):
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

        if arguments:
            action_name = arguments[0]
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


    def __getitem__(self, param_name, parent_recursion=None, perform_nested_calls=True):
        """Lazy parameter access: returns the parameter value from self or the closest parent,
            automatically executing nested_calls on the result.
        """
        logging.debug(f"[{self.get_name()}]  Looking for [{param_name}]...")

        if param_name=='__entry__':
            return self

        try:
            getitem_gen                             = self.getitem_generator( str(param_name), parent_recursion )
            value_source_entry, unprocessed_value   = next(getitem_gen)

        except StopIteration:
            logging.debug(f"[{self.get_name()}]  I don't have parameter '{param_name}', and neither do the parents - raising KeyError")
            raise KeyError(param_name)

        if perform_nested_calls:
            if param_name not in value_source_entry.blocked_param_set:
                value_source_entry.blocked_param_set[param_name] = set()

            value_source_entry.blocked_param_set[param_name].add(self.get_name())

            logging.debug(f"[{self.get_name()}]  BLOCKING '{param_name}' in order to compute nested_calls on {unprocessed_value} ...")
            try:
                param_value = self.nested_calls(unprocessed_value)
            except Exception as e:
                logging.debug(f"[{self.get_name()}]  unBLOCKING '{param_name}' after attempt to compute nested_calls on {unprocessed_value} ...")
                del value_source_entry.blocked_param_set[param_name]
                raise e
            logging.debug(f"[{self.get_name()}]  unBLOCKING '{param_name}' after computing nested_calls on {unprocessed_value} ...")

            value_source_entry.blocked_param_set[param_name].remove(self.get_name())
        else:
            param_value = unprocessed_value

        logging.debug(f"[{self.get_name()}]  Got {param_name}={param_value}")

        return param_value


    def call(self, action_path, *the_pos_rest, **the_named_rest):
        """Dispatch qualified calls via dig() and local calls via local_call()

Usage examples :
                axs version
                axs .pip.available_versions numpy

        """
        if '.' in action_path:
            action_parts = action_path.split('.')
            action_entry = self.dig( action_parts[:-1] )    # starting from an empty string will trigger byname() inside dig()

            # TODO: checking for ..method_name or .fully.qualified..method_name is better be done here,
            #       and possibly also creation of the temp_entry for ad-hoc editing of parameters, to offload the actual call()

            action_name = action_parts[-1]
            return action_entry.local_call( action_name, *the_pos_rest, **the_named_rest )
        else:
            return self.local_call( action_path, *the_pos_rest, **the_named_rest )


    def local_call(self, action_name, pos_params=None, edit_dict=None, export_params=None, deterministic=True, call_record_entry_ptr=None, nested_context=None, slice_relative_to=None):
        """Call a given function or method of a given entry and feed it
            with arguments from the current object optionally overridden by a given edit_dict

            The action can have a mix of positional args and named args with optional defaults.

            Currently all calls are assumed to be deterministic, and their results are cached (subject to context):
                axs mi: fresh_entry , plant alpha 10  beta 20  formula --:='AS^IS:^^:substitute:#{alpha}#-#{beta}#' , get formula
                axs mi: fresh_entry , plant alpha 10  beta 20  formula --:='AS^IS:^^:substitute:#{alpha}#-#{beta}#' , get formula , get mi , get formula
                axs mi: fresh_entry , plant alpha 10  beta 20  formula --:='AS^IS:^^:substitute:#{alpha}#-#{beta}#' , get formula , get mi , get formula --alpha=100
        """

        logging.debug(f'[{self.get_name()}]  calling action "{action_name}" with pos_params={pos_params} and edit_dict={edit_dict} ...')

        cache_tail = '\n\t+'.join([repr(s) for s in self.runtime_stack()])
        cache_key = f"{action_name}.{pos_params}/{ufun.repr_dict(edit_dict)}\n\t+{cache_tail}"

        if deterministic and (cache_key in self.call_cache):
            cached_value = self.call_cache[cache_key]
            logging.debug(f"[{self.get_name()}]  Call '{cache_key}' is FOUND IN CACHE, returning {cached_value}")
            return cached_value
        else:
            logging.debug(f"[{self.get_name()}]  Call '{cache_key}' NOT TAKEN from cache, have to run...")


        ak = self.get_kernel()

        imported_slice = slice_relative_to.slice( *export_params ) if (export_params and slice_relative_to) else {}

        rt_call_specific = Runnable(name='rt_call_specific_'+action_name+'/'+str(pos_params), own_data=imported_slice, parent_objects = [ self ], kernel=ak)     # FIXME: overlapping entry names are not unique

        local_edits  = {}
        for one_edit in edit_dict or {}:
            if one_edit.startswith('.'):    # remote edits of a named entry
                _, remote_entry_name, remote_edit = one_edit.split('.', 2)
                print(f"THIS IS A REMOTE EDIT: {remote_entry_name} :: {remote_edit} -> {edit_dict[one_edit]}")

                remote_entry = ak.byname( remote_entry_name )
                remote_entry.set_own_data( { remote_edit: edit_dict[one_edit] }, topup=True )   # FIXME: we are editing LIVE entries, DO NOT SAVE!
            else:
                local_edits.update( { one_edit: edit_dict[one_edit] } )

        rt_call_specific.set_own_data( local_edits, topup=True)   # topping up with all the local edits


        self.runtime_stack().append( rt_call_specific )     # FIXME: lots of collisions related to this

        if nested_context:
            rt_call_specific.runtime_stack( nested_context )

        # FIXME: this is a candidate for deletion. Be sure to seriously test the hell out of it
        rt_call_specific.own_data( self.nested_calls( rt_call_specific.own_data() ) )   # perform the delayed interpretation of expressions

        if ak:
            call_record_entry   = ak.fresh_entry(container=ak.record_container(), generated_name_prefix=f"generated_by_{self.get_name()}_on_{action_name}_")
            captured_mapping    = call_record_entry.own_data()  # retain the pointer to perform modifications later
        else:
            captured_mapping    = None  # request not to capture the mapping
            call_record_entry   = None  # to please a testing edge case

        if pos_params is None:
            pos_params = []                                 # allow pos_params to be missing
        elif type(pos_params)==list:
            pos_params = self.nested_calls(pos_params)      # perform all nested calls if there are any

        if type(pos_params)!=list:
            pos_params = [ pos_params ]                     # simplified syntax for single positional parameter actions


        action_object       = self.reach_action(action_name)

        if action_name=='func':         # at least propagate edit_dict.  FIXME: maybe rely on func's signature if available?
            joint_arg_tuple     = pos_params
            optional_arg_dict   = rt_call_specific.own_data()
        else:
            rt_call_specific['__record_entry__'] = call_record_entry    # the order is important: first nested_calls() (potentially blocked by {"AS^IS": {}}  then add __record_entry__
            action_object, joint_arg_tuple, optional_arg_dict   = function_access.prep(action_object, pos_params, self, captured_mapping)


        if ak:
            # adding all key-value pairs that were mentioned in the edit_dict, but not needed by the call(), to make sure they also get recorded
            missing_filter_keys = set(rt_call_specific.own_data()) - set(captured_mapping.keys())
            for mfk in missing_filter_keys:
                call_record_entry[mfk] = rt_call_specific[mfk]

            for a in ('__entry__', '__record_entry__'):
                if a in captured_mapping:
                    del captured_mapping[a]

            call_record_entry["_replay"] = [ "^^", "execute", [
                [ [ "get_kernel" ] ] +
                ( [ self.pickle_one()[1:] ] if hasattr(self, 'pickle_one') else [] ) +
                [ [ action_name ] ]     # assuming all parameters have been properly recorded (scattered around) call_record_entry and are thus available
            ] ]

            if call_record_entry_ptr is not None:           # making it available to the pipeline
                call_record_entry_ptr.append( call_record_entry )


        result          = function_access.feed(action_object, joint_arg_tuple, optional_arg_dict)

        self.runtime_stack().pop()

        if ak and result!=call_record_entry :
            call_record_entry['__result__'] = result    # only visible if save()d after execution (not all application cases)

        logging.debug(f'[{self.get_name()}]  called action "{action_name}" with {pos_params}, got {result}')
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
                    try:
                        return self.call( *input_structure[1:], slice_relative_to=self )
                    except Exception as e:
                        as_part = f"\nas part of\n\t{unprocessed_struct}" if input_structure!=unprocessed_struct else ""
                        logging.error(f"[{self.get_name()}] While computing\n\t{input_structure}{as_part}\nthe following exception was raised:\n\t{e.__class__.__name__}({e})\n"+ ("="*120) )
                        raise e
                elif head=='^':
                    side_effects_count += 1
                    try:
                        return self.get_kernel().call( *input_structure[1:], slice_relative_to=self )
                    except Exception as e:
                        as_part = f" as part of {unprocessed_struct}" if input_structure!=unprocessed_struct else ""
                        print("-"*120 + f"\n[{self.get_name()}] While computing {input_structure}{as_part} the following exception was raised:\n\t{e.__class__.__name__}({e})\n"+ "="*120, file=sys.stderr)
                        raise e
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


    def execute(self, pipeline, pipeline_wide_data=None):
        """Execute a parsed pipeline (a chain of calls that starts from the kernel object).
            Whenever a result returned by a function is NOT an Runnable, the execution resets back to the kernel object.

Usage examples :
                axs si: byname sysinfo , substitute '#{os}#--#{ar}#' --os:=^^:dig:si.osname --ar:=^^:dig:si.arch
                axs si: byname sysinfo , os: dig si.osname , , ar: dig si.arch , , substitute 'OS=#{os}#, Arch=#{ar}#'
                axs bypath only_code/iterative.py , :rec: factorial 5 , get rec , save factorial_of_5

                axs version , split . , __getitem__ 2
                axs core_collection , get_path , split /axs/ , __getitem__ 0

                axs noop --,=alpha,beta ,0 enumerate existing values
                axs noop --,=alpha,beta ,1 enumerate existing values
                axs noop --,=alpha,beta ,2 enumerate existing values

                axs noop 12 ,0 func runnable.plus_one
                axs noop 12.345 ,0 func format 10.4f
                axs core_collection , get contained_entries , keys ,0 func list
                axs byname downloader , own_data ,0 func pprint.pformat --width=120
                axs byname downloader , own_data ,0 func json.dumps --indent=4

            # Record a call:
                axs bypath only_code/iterative.py , :rec: factorial 5 , get rec , save factorial_of_5
            # Replay:
                axs bypath factorial_of_5 , get _replay

            # Record a command's output:
                axs work_collection , attached_entry ls_output_entry , plant file_name ls_output.txt , save , target_path: get_path , , byname shell , run --shell_cmd_with_subs='ls -l > #{target_path}#'
                axs byname ls_output_entry , entry_dir:  get_path '' , , byname shell , run --shell_cmd_with_subs='ls -l #{entry_dir}#'
                axs byname ls_output_entry , out_file_path: get_path , , byname shell , run --shell_cmd_with_subs='cat #{out_file_path}#'
        """
        max_call_params     = 3     # action, pos_params, edit_dict
        pipeline_wide_data  = pipeline_wide_data or {}
#        rt_pipeline_wide    = self.get_kernel().bypath(path=f'rt_pipeline_wide_{Runnable.pipeline_counter}', own_data=pipeline_wide_data)  # the "service" pipeline-wide entry
        rt_pipeline_wide    = Runnable(name=f'rt_pipeline_wide_{Runnable.pipeline_counter}', own_data=pipeline_wide_data, kernel=self.get_kernel()) # the "service" pipeline-wide entry
        Runnable.pipeline_counter += 1

        local_context       = [ rt_pipeline_wide ]
        result              = entry = self
        passing_param       = None

        for call_idx, call_params in enumerate(pipeline):

            if type(call_params) in (int, str): # a number is a signal to insert the previous result into the pos_params of the next call,
                                                # a string param name is a signal to add the previous result into edit_dict of the next call
                protected_result = { self.ESCAPE_do_not_process : result } if type(result) in (dict, list) else result
                passing_param = (call_params, protected_result)
                entry = self

            elif call_params == []:         # an empty list is a signal to start again from self
                entry = self

            else:
                output_label    = call_params.pop(max_call_params) if len(call_params)>max_call_params else None    # NB: the order is important!
                input_label     = call_params.pop(max_call_params) if len(call_params)>max_call_params else None

                call_record_entry_ptr = []  # the value of call_record_entry is returned via appending to this empty list

                call_params_iter    = iter(call_params)
                action_name         = next(call_params_iter)
                pos_params          = next(call_params_iter, [])
                edit_dict           = { **pipeline_wide_data, **next(call_params_iter, {}) }    # shallow dictionary merge
                export_params       = next(call_params_iter, None)

                if type(pos_params)!=list:      # first ensure pos_params is a list
                    pos_params = [ pos_params ]     # simplified syntax for single positional parameter actions

                if passing_param:
                    param_position_or_name, param_value = passing_param
                    if type(param_position_or_name) == int:     # insert the previous call's result into pos_params of the current call
                        insert_position_offset = 1 if action_name=='func' else 0
                        pos_params = pos_params[:]      # make a shallow copy to avoid editing original entry data
                        pos_params.insert( param_position_or_name+insert_position_offset, param_value )
                    elif type(param_position_or_name) == str:   # add the previous call's result to the edit_dict of the current call
                        edit_dict[param_position_or_name] = param_value

                    passing_param = None     # empty it after use


                if hasattr(entry, 'call'):                                  # an Entry-specific or Runnable-generic method ("func" called on an Entry will fire here)
                    # print(f"Before call({action_name}, {pos_params}, {edit_dict}, export:{export_params}, rel:+++{self}---)")
                    result = entry.call(action_name, pos_params, edit_dict, export_params, slice_relative_to=self, call_record_entry_ptr=call_record_entry_ptr, nested_context=local_context)
                elif hasattr(entry, action_name):                           # a non-axs Object method
                    action_object   = getattr(entry, action_name)
                    pos_params      = rt_pipeline_wide.nested_calls(pos_params)              # perform all nested calls if there are any
                    result          = function_access.feed(action_object, pos_params, edit_dict)
                elif action_name[0]=='.':   # presumably a qualified action_name, let's start from self
                    result = self.call(action_name, pos_params, edit_dict, export_params, slice_relative_to=self, call_record_entry_ptr=call_record_entry_ptr, nested_context=local_context)
                else:
                    display_pipeline = "\n\t".join([str(step) for step in ["["]+pipeline]) + "\n]"
                    raise RuntimeError( f'In pipeline {display_pipeline} step {pipeline[call_idx]} cannot be executed on value ({entry}) produced by {pipeline[call_idx-1]}' )

                if input_label:
                    rt_pipeline_wide[input_label] = call_record_entry_ptr[0]

                if output_label:
                    rt_pipeline_wide[output_label] = function_access.to_num_or_not_to_num( result )

                entry = result

        return result


    def attr(self, attr_name, default_attr_value=None):
        """Access an arbitrary Python's attribute that is a member of a reachable module (or self).

Usage examples :
                axs attr json.__file__
                axs byquery python_package,package_name=numpy , use , attr numpy.__version__
                axs fresh_entry alpha , attr .entry_path
        """
        attr_object = None

        for i, syll in enumerate( attr_name.split('.') ):
            if i==0 and syll=="":
                attr_object = self
            else:
                try:
                    if attr_object:
                        attr_object = getattr(attr_object, syll)
                    else:
                        attr_object =  __import__(syll)
                except Exception:
                    attr_object = default_attr_value
        return attr_object


    def func(self, func_name, *func_pos_params, **func_opt_params):
        """Run an arbitrary Python's function - either a built-in or member of a reachable module.

            NB: Currently doesn't pick up parameters from the containing object.

Usage examples :
                axs func runnable.plus_one 12                                                                   # internal to AXS
                axs func len abcde                                                                              # built-in
                axs func os.path.join alpha beta gamma                                                          # part of Python's core library
                axs func numpy.arange 15                                                                        # if numpy is already installed in PYTHONPATH
                axs byquery python_package,package_name=numpy , use , func numpy.arange 7                       # if we need our own specific numpy
                axs byquery python_package,package_name=numpy , use , func numpy.exp2 --,=0,1,2,3,4,5,6,7,8     # same, passing a list
        """
        if '.' in func_name:                                            # an imported "dotted" function (can be several dots deep)
            func_object = self.attr(func_name)
        else:                                                           # a built-in function
            func_object = __builtins__[func_name]

        if func_object:
            return function_access.feed(func_object, func_pos_params, func_opt_params)
        else:
            raise NameError( f"could not find the function '{func_name}'" )


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


    def pickle_struct(self, input_structure):
        """Recursively pickle a data structure that may have some Entry objects as leaves. Used by save()
        """
        if type(input_structure)==list:
            return [self.pickle_struct(e) for e in input_structure]                         # all list elements are pickled
        elif type(input_structure)==dict:
            return { k : self.pickle_struct(input_structure[k]) for k in input_structure }  # only values are pickled
        elif hasattr(input_structure, 'pickle_one'):
            return input_structure.pickle_one()                                             # ground step
        else:
            return input_structure                                                          # basement step

    def throw(self, error_message, exception_class="Exception"): # TODO: Is it possible to find out the field name? E.g. "v"
        """Throw an error
Usage examples :
                "x": [ "^^", "throw", "Override this" ]
                "y": [ "^^", "throw", "Override this", "FileNotFoundError" ]
        """
        logging.error(f"Raising exception: {exception_class}({error_message})")
        exception_class = eval(exception_class)
        raise exception_class(error_message)

def plus_one(number):
    "Adds 1 to the argument"
    return number+1


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(funcName)s %(message)s")

    print('-'*40 + ' Creating a hierarchy of Runnables: ' + '-'*40)

    from argparse import Namespace

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
    assert child.call('triple', [], {'number': 11})==33, "call() for dad's function, named args"

    dad['x']=100

    assert child.call('subtract_one')==99, "call() for granddad's function, inherit arg from dad"
    assert child.call('square')==10000, "call() for child's function, inherit arg from dad"
    assert child.call('get', ['x'])==100, "call() for class method, inherit arg from dad"

    try:
        print(f"child.call('nonexistent')={child.call('nonexistent')}\n")
    except NameError as e:
        assert str(e)=="could not find the action 'nonexistent' neither among the ancestors (child, dad, granddad, mum) nor in the Runnable class"

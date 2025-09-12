#!/usr/bin/env python3

from copy import deepcopy
import logging
import pprint
import re
from types import MethodType, FunctionType
import sys

import ufun


class ParamSource:
    """ An object of ParamSource class is a non-persistent container of parameters
        that may optionally also have a list of parent objects of ParamSource class.

        It can return the value of a known parameter or delegate the request for an unknown parameter to its parent(s).
    """

    PARAMNAME_parent_entries        = '_parent_entries'
    ESCAPE_do_not_process           = 'AS^IS'

    def __init__(self, name=None, own_data=None, parent_objects=None, own_functions=None):
        "A trivial constructor"

        self.name               = name
        self.parent_objects     = parent_objects    # sic! The order of initializations is important; data-defined parents have a higher priority than code-assigned ones
        self.own_functions_ns   = own_functions

        self.set_own_data( own_data )


    def is_overrider(self):
        return False


    def get_name(self):
        "Read-only access to the name"

        return self.name


    def own_functions(self):
        """Placeholder for lazy-loading code in subclasses that support it.

            Note the convention:
                stored None means "not loaded yet", as in "cached value missing"
                whereas stored False means "this object has no code to load", "nothing to see here".
        """

        return self.own_functions_ns or False


    def list_own_functions(self):
        """A lightweight method to list all own methods of an entry

Usage examples :
                axs byname be_like , list_own_functions
                axs byname shell , list_own_functions
        """
        from runnable import list_function_names

        own_functions = self.base_entry().own_functions()
        return list_function_names(own_functions) if own_functions else []


    def set_own_data(self, own_data=None):

        self.unprocessed_data = own_data

        if type(own_data)==dict and self.PARAMNAME_parent_entries in own_data:
            self.parent_objects = None      # trigger lazy-reloading of parents

        return self.unprocessed_data


    def pure_data_loader(self):
        """Placeholder for lazy-loading data in subclasses that support it."""

        return {}


    def own_data(self, data_dict=None):
        """Lazy-load, cache and return own data from the file system

Usage examples :
                axs byname base_map , own_data
                axs byname derived_map , own_data
        """
        if data_dict is not None:           # setter mode, so returns self. FIXME: we need a language feature to reset back to self
            self.set_own_data( data_dict )
            return self

        elif self.unprocessed_data is None:   # getter in lazy-loading mode
            loaded_data = self.pure_data_loader()
            if type(loaded_data)==dict:
                self.set_own_data( loaded_data )
#                self.touch('_AFTER_DATA_LOADING')      # FIXME - temporarily turned off, put it back ASAP
            else:
                logging.warning(f"[{self.get_name()}] {loaded_data}, initializing to empty parameters (unstored)")
                self.set_own_data( {} )

        return self.unprocessed_data          # any getter returns here


    def parents_loaded(self):
        if self.parent_objects==None:     # lazy-loading condition
            logging.debug(f"[{self.get_name()} {self} ] Lazy-loading the parents...")
            self.parent_objects = self.get(self.PARAMNAME_parent_entries, [], compute_expressions=True) # FIXME: would be great to go via self.call("get"...) , but causes an infinite loop

            for i, parent_object in enumerate(self.parent_objects):
                if parent_object is None:
                    raise RuntimeError( f"Entry {self.get_name()}'s parent number {i} could not be loaded (is None) ." ) # NB: part of the message should stay verbatim!
                elif type(parent_object)==list:
                    raise RuntimeError( f"Entry {self.get_name()}'s parent number {i} could not be loaded (is {parent_object}) ." )

            # broken_parent_indices = [i for i, parent_object in enumerate(self.parent_objects) if parent_object is None]
            # if None in self.parent_objects:
            #     raise RuntimeError( f"Entry {self.get_name()}'s parent(s) number {broken_parent_indices} could not be loaded." ) # NB: part of the message should stay verbatim!

            logging.debug(f"[{self.get_name()}] Parents loaded and cached.")
        else:
            logging.debug(f"[{self.get_name()}] Parents have already been cached")

        return self.parent_objects


    def pp_data(self):
        return pprint.PrettyPrinter(indent=4).pformat(self.own_data())


    def display_header(self):
        return f"{type(self).__name__}/{id(self)} {self.get_name()} {id(self.own_data())}"


    def data_tree(self, prefix="", is_last=True):

        data_lines = (self.display_header() + '=' + self.pp_data()).split("\n")
        parents_loaded = self.parents_loaded()
        
        # Print the first line with connector and Entry name
        print(f"{prefix}+-- {data_lines[0]}")
        
        # Print remaining data lines with offset
        parent_prefix = prefix + ("    " if is_last else "|   ")
        for line in data_lines[1:]:
            print(f"{parent_prefix}({line}")
        
        # Draw parents
        for i, parent_entry in enumerate(parents_loaded):
            is_last_parent = i == len(parents_loaded) - 1
            parent_entry.data_tree(parent_prefix, is_last_parent)


    def base_entry(self):
        if self.is_overrider():
            return self.parents_loaded()[0].base_entry()
        else:
            return self


    def entry_data(self):
        return self.base_entry().own_data()


    def hierarchy_generator(self, parent_recursion, include_self):
        "Yields the entry and its' parents in order"

        logging.debug(f"[{self.get_name()} {self.__class__.__name__} {id(self)}]")

        if include_self:   # skipping self is useful when augmenting parents' value
            yield self
        else:
            logging.debug(f"[{self.get_name()}]  No self included in hierarchy generation, skipping further")

        if (parent_recursion=='deep') or (parent_recursion=='shallow' and self.is_overrider()):
            for parent_idx, parent_object in enumerate( self.parents_loaded() ):
                if parent_object is not None:
                    if type(parent_object)==list:
                        print("BUGBUGBUGBUG:", parent_object)

                    yield from parent_object.hierarchy_generator(parent_recursion=parent_recursion, include_self=True)
                else:
                    raise RuntimeError( f"Parent #{parent_idx+1} of entry {self.get_name()} could not be loaded." )     # TODO: check error message filtering rule
        else:
            logging.debug(f"[{self.get_name()}]  Parent recursion in hierarchy generation was set to '{parent_recursion}', skipping further")


    def find_in_hierarchy_generator(self, finder_method_name, name_to_find, parent_recursion, include_self):
        "Walk the potential sources of the parameter (own_data and the parents recursively)"

        logging.debug(f"[{self.get_name()} {self.__class__.__name__} {id(self)}] Attempt to {finder_method_name} for '{name_to_find}'...")

        for hierarchy_object in self.hierarchy_generator(parent_recursion=parent_recursion, include_self=include_self):
            try:
                finder_method = getattr(hierarchy_object, finder_method_name)
                yield from finder_method(name_to_find)
            except StopIteration:
                pass


    def find_own_value_generator(self, param_name):
        "Specific finder method for finding a parameter value - augmented or not"

        own_data = self.own_data()
        for augmented_or_not_param_name, param_name_is_augmented in ((param_name,False), (param_name+'+',True)):
            if augmented_or_not_param_name in own_data:
                param_value = own_data[augmented_or_not_param_name]
                logging.debug(f"[{self.get_name()}]  parameter '{augmented_or_not_param_name}' is contained here, returning '{param_value}'")
                yield (self, param_value, param_name_is_augmented)
                break   # this implements the "exclusive or" logic: an entry is expected to either contain an augmentation or a fixed value, not both


    def find_action_generator(self, action_name):
        "Specific finder method for finding a generalized action"
    
        for expected_type, actions_namespace in ( (FunctionType, self.own_functions()), (MethodType, self) ):
            if actions_namespace and hasattr(actions_namespace, action_name):
                found_action = getattr(actions_namespace, action_name)
                if type(found_action)==expected_type:
                    yield (self, found_action, expected_type==FunctionType)


    def __getitem__(self, param_name, parent_recursion=None, include_self=True, compute_expressions=True):
        "Lazy parameter access: returns the parameter value from self or the closest parent"

        param_name = str(param_name)

        if parent_recursion is None:
            parent_recursion = 'shallow' if param_name[0]=='_' else 'deep'
        elif type(parent_recursion)==bool:
            parent_recursion = 'deep' if parent_recursion else 'shallow'

        try:
            param_entry, param_value, param_name_is_augmented = next( self.find_in_hierarchy_generator( "find_own_value_generator", param_name, parent_recursion=parent_recursion, include_self=include_self) )
            if param_name_is_augmented:
                base_param_value = param_entry.__getitem__(param_name, parent_recursion=parent_recursion, include_self=False)
                param_value = ufun.augment(base_param_value, param_value)

            if compute_expressions:
                return self.nested_calls( param_value )
            else:
                return param_value

        except StopIteration:
            logging.debug(f"[{self.get_name()}]  I don't have parameter '{param_name}', and neither do the parents - raising KeyError")
            raise KeyError(param_name)


    def noop(self, arg):
        "Returns its own single argument"

        return arg


    def enumerate(self, *args):
        "Enumerates its arguments in a dictionary"

        return dict(enumerate(args))


    def dig(self, key_path, safe=False, parent_recursion=None, safe_value=None):
        """Traverse the given path of keys into a parameter's internal structure.
            --safe allows it not to fail when the path is not traversable

Usage examples :
                axs dig greek.2 --greek,=alpha,beta,gamma,delta
                axs dig greek.4 --greek,=alpha,beta,gamma,delta --safe
                axs byname counting_collection , byname french , dig --key_path,=number_mapping,7
                axs byname counting_collection , byname dutch , dig number_mapping.6
                axs dig .unzip_tool.tool_path
        """
        if type(key_path)!=list:
            key_path = key_path.split('.')

        key_syllable_iter   = iter(key_path)
        param_name          = next(key_syllable_iter)

        try:
            if not param_name:                                      # path that starts from an empty syllable indicates we want to start form the "root", or the kernel
                entry_name  = next(key_syllable_iter)
                start_entry = self.get_kernel().byname(entry_name)
                param_name  = next(key_syllable_iter, None)         # protect with None to avoid exhausting the iterator too soon
            else:
                start_entry = self

            if param_name is not None:
                struct_ptr  = start_entry.__getitem__(param_name, parent_recursion=parent_recursion)
                struct_ptr  = self.nested_calls( struct_ptr )
#                struct_ptr  = start_entry.call("__getitem__", [], { "param_name": param_name, "parent_recursion": parent_recursion})
            else:
                struct_ptr  = start_entry

            for key_syllable in key_syllable_iter:
                if type(struct_ptr)==list:  # descend into lists with numeric indices
                    key_syllable = int(key_syllable)
                struct_ptr = struct_ptr[key_syllable]   # iterative descent
            return struct_ptr
        except (KeyError, IndexError, ValueError) as e:
            if safe:
                return safe_value
            else:
                raise e


    def slice(self, *param_names, safe=False, plantable=False, skip_missing=False):
        """Produces a slice of a dictionary, with optional remapping

Usage examples :
                axs bypath 3d_point , slice x y z w --safe
                axs bypath 3d_point , slice x y z w --skip_missing
                axs bypath 3d_point , slice x y --,::=another_y:y,another_z:z z
        """
        slice_dict = {}
        for param_name in param_names:
            mapping = param_name if type(param_name)==dict else { param_name: param_name }  # perform optional remapping

            for k in mapping.keys():
                try:
                    slice_dict[k] = self.dig(mapping[k], safe=safe)
                except (KeyError, IndexError, ValueError) as e:
                    if skip_missing:
                        pass
                    else:
                        raise e

        if plantable:
            import itertools

            return list(itertools.chain(*zip(slice_dict.keys(), slice_dict.values())))      # flattened list of key-value pairs
        else:
            return slice_dict


    def substitute(self, input_structure, times=1):
        """Perform single-level parameter substitutions in the given structure

Usage examples :
                axs substitute "Hello, #{mate}#!" --mate=world
                axs byname base_map , substitute '#{first}# und #{second}#'
                axs byname derived_map , substitute '#{first}#, #{third}# und #{fifth}#' --first=Erste
                axs byname counting_collection , byname castellano , substitute '#{number_mapping.3}# + #{number_mapping.5}# = #{number_mapping.8}#'
        """
        pre_pattern     = '{}([\\w\\.]+){}'.format(re.escape('#{'), re.escape('}#'))
        full_pattern    = re.compile(     pre_pattern+'$' )
        sub_pattern     = re.compile( '('+pre_pattern+')' )

        def scalar_substitute(input_template):

            full_match = re.match(full_pattern, input_template)
            if full_match:                          # input_template is made of exactly one anchor
                key_path = full_match.group(1)
                return self.dig( key_path, safe=True )         # output type is determined by the value
            else:
                output_string = input_template

                for sub_match in re.finditer(sub_pattern, input_template):  # input_template may contain 0 or more anchors
                    expression, key_path = sub_match.group(1), sub_match.group(2)
                    param_value  = self.dig( key_path, safe=True )
                    output_string = output_string.replace(expression, str(param_value) )    # fit the output into a string

                return output_string

        def substitute_once(input_structure):
            # Structural recursion:
            if type(input_structure)==list:
                if len(input_structure)==2 and input_structure[0]=="AS#IS":
                    return input_structure[1]
                else:
                    return [substitute_once(e) for e in input_structure]                                        # all list elements are substituted
            elif type(input_structure)==dict:
                return { substitute_once(k) : substitute_once(input_structure[k]) for k in input_structure }    # both keys and values are substituted
            elif type(input_structure)==str:
                return scalar_substitute(input_structure)                                                       # ground step
            else:
                return input_structure                                                                          # basement step

        substituted_structure = input_structure
        for _ in range(times):
            substituted_structure = substitute_once(substituted_structure)

        return substituted_structure


    def get(self, param_name, default_value=None, parent_recursion=None, compute_expressions=True):
        """A safe wrapper around __getitem__() - returns the default_value if missing

Usage examples :
                axs get bar --foo=42 --bar,=gold,silver,chocolate
                axs byname base_map , get fourth Vierte
                axs byname derived_map , get fifth
        """
        try:
            return self.__getitem__(param_name, parent_recursion=parent_recursion, compute_expressions=compute_expressions)
        except KeyError:
            logging.debug(f"[{self.get_name()}] caught KeyError: parameter '{param_name}' is missing, returning the default value '{default_value}'")
            return default_value


    def touch(self, param_name):
        """[Compute and] print the value of a [non-inherited] parameter and carry on - useful for debugging and hooking
        """
        param_value = self.get(param_name, None)
        if param_value!=None:
            logging.info(f"[{self.get_name()}] touch {param_name}={param_value}")
        return param_value


    def __setitem__(self, param_name, param_value):
        "A simple setter method. We always set the value at the top"

        param_name = str(param_name)
        self.own_data()[param_name] = param_value

        if param_name==self.PARAMNAME_parent_entries:   # magic request to reload the parents
            self.parent_objects = None

        return self


    def plant(self, *keypath_value_pairs, pluck=False):
        """Traverse the given path of keys into a parameter's internal structure
            and change/add a value there.
            Fairly tolerant to short lists & missing values.

Usage examples :
                axs fresh_entry , plant num.tens --,=10,20,30 num.doubles --,=2,4,6,8 , own_data
                axs fresh_entry , plant _parent_entries --,:=AS^IS:^:byname:shell , run 'echo hello, world'
                axs bypath only_data/carbon.json , plant weight+ 0.5 , own_data
                axs bypath only_data/carbon.json , plant isotopes+ 15 , own_data
                axs bypath only_data/carbon.json , plant isotopes+ --,=15,16 , own_data
                axs bypath only_data/carbon.json , plant iso_dict --,::=medium:13.5,superheavy:15.5 , own_data
        """

        kvp_length  = len(keypath_value_pairs)
        loop_step   = 1 if pluck else 2

        if int(kvp_length/loop_step)*loop_step != kvp_length:
            raise AssertionError(f"keypath_value_pairs should contain an whole number of {loop_step}-tuples")

        for i in range(0, kvp_length, loop_step):
            key_path    = keypath_value_pairs[i]
            value       = None if pluck else keypath_value_pairs[i+1]

            if type(key_path)!=list:
                key_path = key_path.split('.')

            if key_path[-1].endswith('+'):
                key_path[-1] = key_path[-1][:-1]    # trim off that '+'
                edit_mode = 'AUGMENT'
            elif pluck:
                edit_mode = 'PLUCK'
            else:
                edit_mode = 'ASSIGN'

            # pre-clone if necessary:
            if (len(key_path)>1 or edit_mode == 'AUGMENT') and (key_path[0] not in self.own_data()):
                top_key = key_path[0]
                self.__setitem__( top_key, deepcopy( self.__getitem__(top_key, perform_nested_calls=True) ) )   # FIXME: perform_nested_calls is not defined (probably needs redesign anyway)

            if (edit_mode == 'AUGMENT') and hasattr(self, "nested_calls"):
                value = self.nested_calls( value )

            ufun.edit_structure(self.entry_data(), key_path, value, edit_mode)

            if key_path == [ self.PARAMNAME_parent_entries ]:   # magic request to reload the parents
                self.parent_objects = None

        return self


    def pluck(self, *key_paths):
        """Traverse the given path of keys into a parameter's internal structure
            and remove a key-value pair from there.

Usage examples :
                axs bypath foo , pluck foo.bar.baz , save
        """
        return self.plant(*key_paths, pluck=True)


    def case(self, question, *answer_value_pairs, default_value=None, execute_value=False):
        """An ordered key-to-value mapper, used for decision-making.

Usage examples :
                axs plant number 20 , case --,=^^,get,number 10 ten 20 twenty 30 thirty
                axs plant number 15 , case --,=^^,get,number 0 zero --,=1,2,3,4,5,6,7,8,9 single_digit --,=10,20,30,40,50,60,70,80,90 tens --default_value=anything_else
        """

        avp_length  = len(answer_value_pairs)
        final_value = [] if (default_value is None and execute_value) else default_value
        for i in range(0, avp_length, 2):
            answer  = answer_value_pairs[i]
            value   = answer_value_pairs[i+1]

            if (type(question)==type(answer) and question==answer) or (type(answer)==list and ufun.is_in(question,answer) ):
                final_value = value
                break

        return self.execute( final_value ) if execute_value else final_value


    def call(self, action, pos_params=None, own_data=None):

        from runnable import Runnable

        runnable = Runnable(action, name=self.get_name(), pos_params=pos_params, own_data=own_data, parent_entry=self)
        result = runnable()

        if result == runnable:
            result = self

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
                if head==self.ESCAPE_do_not_process:
                    side_effects_count += 1                                                         # it is only a "side effect" for the purposes of our GC-facilitating decision making below
                    return deepcopy( input_structure[1:] )                                          # drop the escape symbol, keeping the rest of the substructure intact
                else:
                    input_structure = [ nested_calls_rec(elem) for elem in input_structure ]

                    if head=='^^':
                        side_effects_count += 1
                        try:
                            return self.call( *input_structure[1:] )
                        except Exception as e:
                            as_part = f"\nas part of\n\t{unprocessed_struct}" if input_structure!=unprocessed_struct else ""
                            logging.error(f"[{self.get_name()}] While computing\n\t{input_structure}{as_part}\nthe following exception was raised:\n\t{e.__class__.__name__}({e})\n"+ ("="*120) )
                            raise e
                    elif head=='^':
                        side_effects_count += 1
                        try:
                            from stored_entry import Entry
                            return Entry.get_kernel().call( *input_structure[1:] )
                        except Exception as e:
                            as_part = f" as part of {unprocessed_struct}" if input_structure!=unprocessed_struct else ""
                            print("-"*120 + f"\n[{self.get_name()}] While computing {input_structure}{as_part} the following exception was raised:\n\t{e.__class__.__name__}({e})\n"+ "="*120, file=sys.stderr)
                            raise e
                    else:
                        return input_structure
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
                axs work_collection , attached_entry ls_output_entry , plant file_name ls_output.txt , save , target_path: get_path , , byname shell , run --shell_cmd_with_subs='ls -l > #{tar
get_path}#'
                axs byname ls_output_entry , entry_dir:  get_path '' , , byname shell , run --shell_cmd_with_subs='ls -l #{entry_dir}#'
                axs byname ls_output_entry , out_file_path: get_path , , byname shell , run --shell_cmd_with_subs='cat #{out_file_path}#'
        """
        max_call_params     = 3     # action, pos_params, edit_dict
        result              = entry_or_object = self
        passing_param       = None

        for call_idx, call_params in enumerate(pipeline):

            if type(call_params) in (int, str): # a number is a signal to insert the previous result into the pos_params of the next call,
                                                # a string param name is a signal to add the previous result into edit_dict of the next call
                protected_result = { self.ESCAPE_do_not_process : result } if type(result) in (dict, list) else result
                passing_param = (call_params, protected_result)
                entry_or_object = self

            elif call_params == []:         # an empty list is a signal to start again from self
                entry_or_object = self

            else:
                output_label    = call_params.pop(max_call_params) if len(call_params)>max_call_params else None    # NB: the order is important!
                input_label     = call_params.pop(max_call_params) if len(call_params)>max_call_params else None

                call_record_entry_ptr = []  # the value of call_record_entry is returned via appending to this empty list

                call_params_iter    = iter(call_params)
                action_name         = next(call_params_iter)
                pos_params          = next(call_params_iter, [])
                edit_dict           = next(call_params_iter, {})
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


                if hasattr(entry_or_object, 'call'):                                  # an Entry-specific or Runnable-generic method ("func" called on an Entry will fire here)
#                    result = entry_or_object.call(action_name, pos_params, edit_dict, export_params)
                    result = entry_or_object.call(action_name, pos_params, edit_dict)

                elif hasattr(entry_or_object, action_name):                           # a non-axs Object method
                    from runnable import feed

                    action_object   = getattr(entry_or_object, action_name)
                    pos_params      = self.nested_calls(pos_params)              # perform all nested calls if there are any
                    result          = feed(action_object, pos_params, edit_dict)
#                elif action_name[0]=='.':   # presumably a qualified action_name, let's start from self
#                    result = self.call(action_name, pos_params, edit_dict, export_params, pipeline_wide_entry=self, slice_relative_to=self, call_record_entry_ptr=call_record_entry_ptr)
                else:
                    display_pipeline = "\n\t".join([str(step) for step in ["["]+pipeline]) + "\n]"
                    raise RuntimeError( f'In pipeline {display_pipeline} step {pipeline[call_idx]} cannot be executed on value ({entry_or_object}) produced by {pipeline[call_idx-1]}' )

                if input_label:
                    self[input_label] = call_record_entry_ptr[0]

                if output_label:
                    self[output_label] = ufun.to_num_or_not_to_num( result )

                entry_or_object = result

        return result


    def attr(self, attr_name, default_attr_value=None):
        """Access an arbitrary Python's attribute that is a member of a reachable module (or self).

Usage examples :
                axs attr json.__file__
                axs byquery python_package,package_name=numpy , use , , attr numpy.__version__
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
                axs byquery python_package,package_name=numpy , use , , func numpy.arange 7                     # if we need our own specific numpy
                axs byquery python_package,package_name=numpy , use , , func numpy.exp2 --,=0,1,2,3,4,5,6,7,8   # same, passing a list
        """
        if '.' in func_name:                                            # an imported "dotted" function (can be several dots deep)
            func_object = self.attr(func_name)
        else:                                                           # a built-in function
            func_object = __builtins__[func_name]

        if func_object:
            from runnable import feed

            return feed(func_object, func_pos_params, func_opt_params)
        else:
            raise NameError( f"could not find the function '{func_name}'" )



# TESTING:
if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(funcName)s %(message)s")

    print('-'*20 + ' Dictionary-like data access: ' + '-'*20)

    noname      = ParamSource(own_data={"alpha": 10, "beta": -3})

    assert noname['alpha']+noname['beta']+noname.get('gamma', 1)==8, "Accessing own data"

    print('-'*20 + ' Access request delegation down the ParamSource hierarchy: ' + '-'*20)

    granddad    = ParamSource(name='granddad',  own_data={"seventh":"seitsmes", "nineth":"yheksas", "extlist":[10, 20, 30], "extlist+":[11, 22, 33] })
    dad         = ParamSource(name='dad',       own_data={"third":"kolmas",     "fifth":"viies"},   parent_objects=[granddad])

    grandma     = ParamSource(name='grandma',   own_data={"eighth":"kaheksas", "tenth":"kymnes"})
    mum         = ParamSource(name='mum',       own_data={"fourth":"neljas",   "sixth":"kuues"},    parent_objects=[grandma])

    child       = ParamSource(name='child',     own_data={"first":"esimene",   "second":"teine", "extlist+":[40, 50]},   parent_objects=[dad, mum])

    assert child['first']=='esimene', "Getting own data"
    assert child['third']=='kolmas', "Inheriting dad's data"
    assert child['seventh']=='seitsmes', "Inheriting granddad's data"

    assert child['fourth']=='neljas', "Inheriting mum's data"
    assert child['eighth']=='kaheksas', "Inheriting grandma's data"

    assert child['extlist']==[10, 20, 30, 40, 50], "Augmenting a list"

    assert child.substitute("#{second}#, #{fifth}#, #{sixth}#, #{nineth}# ja #{tenth}#")=="teine, viies, kuues, yheksas ja kymnes", "Substitution of data of mixed inheritance"

    try:
        missing = child['missing1']
    except KeyError as e:
        assert str(e)=="'missing1'", "Parameter 'missing1' is correctly missing"

    assert child.get('missing2', 'MISSING')=='MISSING', "Missing data substituted with default value"

    dad['third']        = 'KOLMAS'
    dad['seventh']      = 'SEITSMES'
    grandma['missing']  = 'PUUDU'

    child.data_tree()

    assert grandma.own_data()=={"eighth":"kaheksas", "tenth":"kymnes", "missing":"PUUDU"}, "Modified grandma's data"
    assert dad.own_data()=={"third":"KOLMAS", "fifth":"viies", "seventh":"SEITSMES"}, "Modified dad's data"
    assert child.own_data()=={'first': 'esimene', 'second': 'teine', "extlist+":[40, 50]}, "Unmodified child's data"

    from runnable import feed, prep, four_param_example_func

    print('-'*40 + ' feed() calls: ' + '-'*40)

    foo_param_parent = ParamSource(name='foo_param_parent', own_data={"alpha": 100, "beta": 200, "delta": 400, "epsilon": 600})
    foo_param_child  = ParamSource(name='foo_param_child',  own_data={"alpha": 10, "lambda": 7777},            parent_objects=[foo_param_parent])

    assert feed(*prep(four_param_example_func, (), foo_param_child))==(10, 200, 333, 400), "feed() call with all parameters coming from ParamSource object"

    bar_params = ParamSource(name='bar_params', own_data={"mate": "world", "deep": {"hole": [10,20,30], "sea": "Red"} })

    assert feed(*prep(bar_params.substitute, ("Hello, #{mate}#!",), bar_params))=="Hello, world!", "feed() call with both positional and optional parameters #1"

    assert feed(*prep(bar_params.dig, ("deep.hole.2",), bar_params))==30, "feed() call with both positional and optional parameters #2"

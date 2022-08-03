#!/usr/bin/env python3

import logging
import re

class ParamSource:
    """ An object of ParamSource class is a non-persistent container of parameters
        that may optionally also have a parent object of the same class.

        It can return the value of a known parameter or delegate the request for an unknown parameter to its parent.
    """

    PARAMNAME_parent_entries        = '_parent_entries'

    def __init__(self, name=None, own_data=None, parent_objects=None):
        "A trivial constructor"

        self.name                   = name
        self.own_data_cache         = own_data
        self.parent_objects         = parent_objects
        self.runtime_stack_cache    = []
        self.blocked_param_set      = set()

        logging.debug(f"[{self.get_name()}] Initializing the ParamSource with own_data={self.own_data_cache}, inheriting from {'some parents' or 'no parents'}")
# FIXME: The following would cause infinite recursion (expecting cached entries before they actually end up in cache)
#        logging.debug(f"[{self.get_name()}] Initializing the ParamSource with own_data={self.own_data_cache}, inheriting from {self.get_parents_names() or 'no parents'}")


    def __repr__(self):
        "Not callable via commandline (FIXME)"

        own_data = self.own_data()
        return (self.get_name() or 'Anonymous') + '{'+(','.join([ repr(k)+':'+('self' if own_data[k]==self else repr(own_data[k])) for k in sorted(own_data.keys()) ]))+'}'


    def get_name(self):
        "Read-only access to the name"

        return self.name


    def own_data(self, data_dict=None):
        "Placeholder for lazy-loading parameters in subclasses that support it"

        if data_dict is not None:
            self.own_data_cache = data_dict
            return self

        elif self.own_data_cache is None:
            self.own_data_cache = {}

        return self.own_data_cache


    def parents_loaded(self):
        if self.parent_objects==None:     # lazy-loading condition
            logging.debug(f"[{self.get_name()}] Lazy-loading the parents...")
            self.parent_objects = self.get(self.PARAMNAME_parent_entries, [])
            logging.debug(f"[{self.get_name()}] Parents loaded and cached.")
        else:
            logging.debug(f"[{self.get_name()}] Parents have already been cached")

        return self.parent_objects


    def get_parents_names(self):
        "Returns a string representation of the name list"

        parent_objects = self.parents_loaded()
        return repr([parent_object.get_name() for parent_object in parent_objects]) if parent_objects else ""


    def noop(self, arg):
        "Returns its own single argument"

        return arg


    def enumerate(self, *args):
        "Enumerates its arguments in a dictionary"

        return dict(enumerate(args))


    def slice(self, *param_names):
        """Produces a slice of a dictionary, with optional remapping

Usage examples :
                axs bypath 3d_point , slice x y --,::=another_y:y,another_z:z z
        """
        slice_dict = {}
        for param_name in param_names:
            if type(param_name)==dict:      # perform optional remapping
                for k in param_name.keys():
                    slice_dict[k] = self[param_name[k]]
            else:
                slice_dict[param_name] = self[param_name]

        return slice_dict


    def runtime_stack(self):
        "A list of entries to query for parameters before own_data during [] parameter access"

        return self.runtime_stack_cache


    def rt_pipeline_entry(self):
        "Returns the entry that persists through the pipeline's execution"

        return self.runtime_stack_cache[0]


    def get_own_value_generator(self, param_name):
        "Common part of accessing a parameter"

        own_data = self.own_data()
        if param_name in own_data and param_name not in self.blocked_param_set:
            param_value = own_data[param_name]
            logging.debug(f"[{self.get_name()}]  {self.get_name()} has parameter '{param_name}', returning '{param_value}'")
            yield (self, param_value)
        else:
            logging.debug(f"[{self.get_name()}]  {self.get_name()} does not have parameter '{param_name}', skipping further")


    def getitem_generator(self, param_name, parent_recursion=None):
        "Walk the potential sources of the parameter (runtime, own_data and the parents recursively)"

        logging.debug(f"[{self.get_name()}] Attempt to access parameter '{param_name}'...")

        for runtime_entry in self.runtime_stack():
            yield from runtime_entry.get_own_value_generator( param_name )

        yield from self.get_own_value_generator( param_name )

        # trust the boolean value if it was defined,
        # otherwise the parameter's inheritability is encoded in its name:
        if parent_recursion if parent_recursion is not None else param_name[0]!='_':
            for parent_object in self.parents_loaded():
                logging.debug(f"[{self.get_name()}]  I don't have parameter '{param_name}', fallback to the parent '{parent_object.get_name()}'")
                try:
                    yield from parent_object.getitem_generator(param_name)
                except StopIteration:
                    logging.debug(f"[{self.get_name()}]  My parent '{parent_object.get_name()}'' did not know about '{param_name}'")
                    pass
        else:
            logging.debug(f"[{self.get_name()}]  No parent recursion for '{param_name}', skipping further")


    def get_data_pile(self, param_name):
        """Get all values of the same parameter in the order of their inheritance, top first.

Usage examples :
                axs byname dont_be_like , get_data_pile be
        """
        return [ value for source, value in self.getitem_generator( str(param_name) ) ]


    def __getitem__(self, param_name, parent_recursion=None):
        "Lazy parameter access: returns the parameter value from self or the closest parent"

        try:
            return next( self.getitem_generator( str(param_name), parent_recursion ) )[1]
        except StopIteration:
            logging.debug(f"[{self.get_name()}]  I don't have parameter '{param_name}', and neither do the parents - raising KeyError")
            raise KeyError(param_name)


    def dig(self, key_path, safe=False, parent_recursion=None):
        """Traverse the given path of keys into a parameter's internal structure.
            --safe allows it not to fail when the path is not traversable

Usage examples :
                axs dig greek.2 --greek,=alpha,beta,gamma,delta
                axs dig greek.4 --greek,=alpha,beta,gamma,delta --safe
                axs byname counting_collection , byname french , dig --key_path,=number_mapping,7
                axs byname counting_collection , byname dutch , dig number_mapping.6
        """
        if type(key_path)!=list:
            key_path = key_path.split('.')

        param_name = key_path[0]

        try:
            struct_ptr  = self.__getitem__(param_name, parent_recursion)

            for key_syllable in key_path[1:]:
                if type(struct_ptr)==list:  # descend into lists with numeric indices
                    key_syllable = int(key_syllable)
                struct_ptr = struct_ptr[key_syllable]   # iterative descent
            return struct_ptr
        except (KeyError, IndexError, ValueError) as e:
            if safe:
                return None
            else:
                raise e


    def substitute(self, input_structure):
        """Perform single-level parameter substitutions in the given structure

Usage examples :
                axs substitute "Hello, #{mate}#!" --mate=world
                axs byname base_map , substitute '#{first}# und #{second}#'
                axs byname derived_map , substitute '#{first}#, #{third}# und #{fifth}#' --first=Erste
                axs byname counting_collection , byname castellano , substitute '#{number_mapping.3}# + #{number_mapping.5}# = #{number_mapping.8}#'
        """
        pre_pattern     = '{}([\w\.]+){}'.format(re.escape('#{'), re.escape('}#'))
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

        # Structural recursion:
        if type(input_structure)==list:
            return [self.substitute(e) for e in input_structure]                            # all list elements are substituted
        elif type(input_structure)==dict:
            return { k : self.substitute(input_structure[k]) for k in input_structure }     # only values are substituted
        elif type(input_structure)==str:
            return scalar_substitute(input_structure)                                       # ground step
        else:
            return input_structure                                                          # basement step


    def get(self, param_name, default_value=None):
        """A safe wrapper around __getitem__() - returns the default_value if missing

Usage examples :
                axs get bar --foo=42 --bar,=gold,silver,chocolate
                axs byname base_map , get fourth Vierte
                axs byname derived_map , get fifth
        """
        try:
            return self.__getitem__(param_name)
        except KeyError:
            logging.debug(f"[{self.get_name()}] caught KeyError: parameter '{param_name}' is missing, returning the default value '{default_value}'")
            return default_value


    def touch(self, param_name):
        """[Compute and] print the value of a [non-inherited] parameter and carry on - useful for debugging and hooking
        """
        param_value = self.get(param_name, None)
        if param_value!=None:
            logging.warning(f"[{self.get_name()}] touch {param_name}={param_value}")
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

            struct_ptr = self.own_data()

            last_idx = len(key_path)-1
            for key_idx, key_syllable in enumerate(key_path):
                augment = key_syllable.endswith('+')
                if augment:
                    key_syllable = key_syllable[:-1]

                if type(struct_ptr)==list:  # descend into lists with numeric indices
                    key_syllable = int(key_syllable)
                    padding_size = key_syllable-len(struct_ptr)+1
                    struct_ptr.extend([None]*(padding_size-1))  # explicit list vivification
                    if padding_size>0:
                        struct_ptr.append({})
                elif key_syllable not in struct_ptr:
                    struct_ptr[key_syllable] = {}               # explicit dict vivification

                if key_idx<last_idx:
                    struct_ptr = struct_ptr[key_syllable]       # iterative descent
                elif pluck:
                    struct_ptr.pop(key_syllable)
                elif augment:
                    orig_value = struct_ptr[key_syllable]

                    if type(orig_value)==dict:
                        struct_ptr[key_syllable].update(value)
                    elif type(orig_value)==list and type(value)!=list:
                        struct_ptr[key_syllable] += [ value ]
                    else:
                        struct_ptr[key_syllable] += value
                else:
                    struct_ptr[key_syllable] = value


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


    def case(self, question, *answer_value_pairs, default_value=None):
        """An ordered key-to-value mapper, used for decision-making.

Usage examples :
                axs plant number 20 , case --,=^^,get,number 10 ten 20 twenty 30 thirty
                axs plant number 15 , case --,=^^,get,number 0 zero --,=1,2,3,4,5,6,7,8,9 single_digit --,=10,20,30,40,50,60,70,80,90 tens --default_value=anything_else
        """

        avp_length  = len(answer_value_pairs)
        for i in range(0, avp_length, 2):
            answer  = answer_value_pairs[i]
            value   = answer_value_pairs[i+1]

            if (type(question)==type(answer) and question==answer) or (type(answer)==list and question in answer):
                    return value

        return default_value


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(funcName)s %(message)s")

    print('-'*20 + ' Dictionary-like data access: ' + '-'*20)

    noname      = ParamSource(own_data={"alpha": 10, "beta": -3})

    assert noname['alpha']+noname['beta']+noname.get('gamma', 1)==8, "Accessing own data"

    print('-'*20 + ' Access request delegation down the ParamSource hierarchy: ' + '-'*20)

    granddad    = ParamSource(name='granddad',  own_data={"seventh":"seitsmes", "nineth":"yheksas"})
    dad         = ParamSource(name='dad',       own_data={"third":"kolmas",     "fifth":"viies"},   parent_objects=[granddad])

    grandma     = ParamSource(name='grandma',   own_data={"eighth":"kaheksas", "tenth":"kymnes"})
    mum         = ParamSource(name='mum',       own_data={"fourth":"neljas",   "sixth":"kuues"},    parent_objects=[grandma])

    child       = ParamSource(name='child',     own_data={"first":"esimene",   "second":"teine"},   parent_objects=[dad, mum])

    assert child['first']=='esimene', "Getting own data"
    assert child['third']=='kolmas', "Inheriting dad's data"
    assert child['seventh']=='seitsmes', "Inheriting granddad's data"

    assert child['fourth']=='neljas', "Inheriting mum's data"
    assert child['eighth']=='kaheksas', "Inheriting grandma's data"

    assert child.substitute("#{second}#, #{fifth}#, #{sixth}#, #{nineth}# ja #{tenth}#")=="teine, viies, kuues, yheksas ja kymnes", "Substitution of data of mixed inheritance"

    try:
        missing = child['missing1']
    except KeyError as e:
        assert str(e)=="'missing1'", "Parameter 'missing1' is correctly missing"

    assert child.get('missing2', 'MISSING')=='MISSING', "Missing data substituted with default value"

    dad['third']        = 'KOLMAS'
    dad['seventh']      = 'SEITSMES'
    granddad['missing'] = 'PUUDU'

    assert granddad.own_data()=={"seventh":"seitsmes", "nineth":"yheksas", "missing":"PUUDU"}, "Modified granddad's data"
    assert dad.own_data()=={"third":"KOLMAS", "fifth":"viies", "seventh":"SEITSMES"}, "Modified dad's data"
    assert child.own_data()=={'first': 'esimene', 'second': 'teine'}, "Unmodified child's data"

    from function_access import feed, prep, four_param_example_func

    print('-'*40 + ' feed() calls: ' + '-'*40)

    foo_param_parent = ParamSource(name='foo_param_parent', own_data={"alpha": 100, "beta": 200, "delta": 400, "epsilon": 600})
    foo_param_child  = ParamSource(name='foo_param_child',  own_data={"alpha": 10, "lambda": 7777},            parent_objects=[foo_param_parent])

    assert feed(*prep(four_param_example_func, (), foo_param_child))==(10, 200, 333, 400), "feed() call with all parameters coming from ParamSource object"

    bar_params = ParamSource(name='bar_params', own_data={"mate": "world", "deep": {"hole": [10,20,30], "sea": "Red"} })

    assert feed(*prep(bar_params.substitute, ("Hello, #{mate}#!",), bar_params))=="Hello, world!", "feed() call with both positional and optional parameters #1"

    assert feed(*prep(bar_params.dig, ("deep.hole.2",), bar_params))==30, "feed() call with both positional and optional parameters #2"

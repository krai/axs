#!/usr/bin/env python3

import logging
import re

class ParamSource:
    """ An object of ParamSource class is a non-persistent container of parameters
        that may optionally also have a parent object of the same class.

        It can return the value of a known parameter or delegate the request for an unknown parameter to its parent.
    """

    PARAMNAME_parent_entry  = 'parent_entry'

    def __init__(self, name=None, own_parameters=None, parent_object=None):
        "A trivial constructor"

        self.name           = name
        self.own_parameters = own_parameters
        self.parent_object  = parent_object
        logging.debug(f"[{self.get_name()}] Initializing the ParamSource with own_parameters={self.own_parameters} and {self.parent_object.get_name()+' as parent' if self.parent_object else 'no parent'}")


    def get_name(self):
        "Read-only access to the name"

        return self.name


    def parameters_loaded(self):
        "Placeholder for lazy-loading parameters in subclasses that support it"

        if self.own_parameters == None:
            self.own_parameters = {}

        return self.own_parameters


    def parent_loaded(self):
        if self.parent_object==None:     # lazy-loading condition
            self.parent_object  = self.get( self.PARAMNAME_parent_entry, parent_recursion=False ) or False

        return self.parent_object


    def __getitem__(self, param_name, calling_top_context=None, parent_recursion=True):
        "Lazy parameter access: returns the parameter value from self or the closest parent"

        calling_top_context = calling_top_context or self

        logging.debug(f"[{self.get_name()}] Attempt to access parameter '{param_name}'...")
        if param_name=='__entry__':
            return self

        own_parameters = self.parameters_loaded()
        if param_name in own_parameters:
            param_value = own_parameters[param_name]
            logging.debug(f'[{self.get_name()}]  I have parameter "{param_name}", returning "{param_value}"')
            return param_value
        else:
            for prefix in ('#', '*'):
                prefixed_param_name = prefix+param_name
                if prefixed_param_name in own_parameters:
                    unsubstituted_structure = own_parameters[prefixed_param_name]
                    logging.debug(f'[{self.get_name()}]  I have parameter "{prefixed_param_name}", the value is "{unsubstituted_structure}"')
                    substituted_structure = calling_top_context.substitute( unsubstituted_structure )
                    logging.debug(f'[{self.get_name()}]  Substituting "{unsubstituted_structure}", returning "{substituted_structure}"')
                    if prefix=='#':
                        return substituted_structure
                    elif prefix=='*':
                        logging.debug(f'[{self.get_name()}]  About to execute the pipeline: "{substituted_structure}"')
                        pipeline_result = calling_top_context.execute( substituted_structure )
                        logging.debug(f'[{self.get_name()}]  Executed "{substituted_structure}", returning "{pipeline_result}"')
                        return pipeline_result

            if parent_recursion:
                parent_object = self.parent_loaded()
                if parent_object:
                    logging.debug(f"[{self.get_name()}]  I don't have parameter '{param_name}', fallback to the parent")
                    return parent_object.__getitem__(param_name, calling_top_context=calling_top_context)

            logging.debug(f"[{self.get_name()}]  I don't have parameter '{param_name}', and no parent either - raising KeyError")
            raise KeyError(param_name)


    def dig(self, key_path, safe=False, parent_recursion=True):
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
            struct_ptr  = self.__getitem__(param_name, parent_recursion=parent_recursion)

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
                return self.dig( key_path )         # output type is determined by the value
            else:
                output_string = input_template

                for sub_match in re.finditer(sub_pattern, input_template):  # input_template may contain 0 or more anchors
                    expression, key_path = sub_match.group(1), sub_match.group(2)
                    param_value  = self.dig( key_path )
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


    def get(self, param_name, default_value=None, calling_top_context=None, parent_recursion=True):
        """A safe wrapper around __getitem__() - returns the default_value if missing

Usage examples :
                axs get bar --foo=42 --bar,=gold,silver,chocolate
                axs byname base_map , get fourth Vierte
                axs byname derived_map , get fifth
        """
        try:
            return self.__getitem__(param_name, calling_top_context=calling_top_context, parent_recursion=parent_recursion)
        except KeyError:
            logging.debug(f"[{self.get_name()}] caught KeyError: parameter '{param_name}' is missing, returning the default value '{default_value}'")
            return default_value


    def __setitem__(self, param_name, param_value):
        "A simple setter method. We always set the value at the top"

        self.parameters_loaded()[param_name] = param_value


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(funcName)s %(message)s")

    print('-'*20 + ' Access request delegation down the ParamSource hierarchy: ' + '-'*20)

    granddad    = ParamSource(name='granddad',  own_parameters={"fifth":"viies", "sixth":"kuues"} )
    dad         = ParamSource(name='dad',       own_parameters={"third":"kolmas", "fourth":"neljas"},   parent_object=granddad)
    child       = ParamSource(name='child',     own_parameters={"first":"esimene", "second":"teine"},   parent_object=dad)

    assert child['first']=='esimene', "Getting own data"
    assert child['third']=='kolmas', "Inheriting dad's data"
    assert child['fifth']=='viies', "Inheriting granddad's data"
    assert child.substitute("#{second}#, #{third}# ja #{fifth}#")=="teine, kolmas ja viies", "Substitution of data of mixed inheritance"

    try:
        missing = child['seventh']
    except KeyError as e:
        print(f"\tParameter {e} is correctly missing\n")

    assert child.get('ninth', 'MISSING')=='MISSING', "Missing data substituted with default value"

    dad['second']       = 'TEINE'
    dad['third']        = 'KOLMAS'
    granddad['seventh'] = 'SEITSMES'

    assert granddad.parameters_loaded()=={'fifth': 'viies', 'sixth': 'kuues', 'seventh': 'SEITSMES'}, "Modified granddad's data"
    assert dad.parameters_loaded()=={'third': 'KOLMAS', 'fourth': 'neljas', 'second': 'TEINE'}, "Modified dad's data"
    assert child.parameters_loaded()=={'first': 'esimene', 'second': 'teine'}, "Unmodified child's data"

    from function_access import feed, four_param_example_func

    print('-'*40 + ' feed() calls: ' + '-'*40)

    foo_param_parent = ParamSource(name='foo_param_parent', own_parameters={"alpha": 100, "beta": 200, "delta": 400, "epsilon": 600})
    foo_param_child  = ParamSource(name='foo_param_child',  own_parameters={"alpha": 10, "lambda": 7777},            parent_object=foo_param_parent)

    assert feed(four_param_example_func, (), foo_param_child)==(10, 200, 333, 400), "feed() call with all parameters coming from ParamSource object"

    bar_params = ParamSource(name='bar_params', own_parameters={"mate": "world", "deep": {"hole": [10,20,30], "sea": "Red"} })

    assert feed(bar_params.substitute, ("Hello, #{mate}#!",), bar_params)=="Hello, world!", "feed() call with both positional and optional parameters #1"

    assert feed(bar_params.dig, ("deep.hole.2",), bar_params)==30, "feed() call with both positional and optional parameters #2"

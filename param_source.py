#!/usr/bin/env python3

import re

class ParamSource:
    """ An object of ParamSource class is a non-persistent container of parameters
        that may optionally also have a parent object of the same class.

        It can return the value of a known parameter or delegate the request for an unknown parameter to its parent.
    """

    def __init__(self, name=None, own_parameters=None, parent_object=None):
        "A trivial constructor"

        self.name = name
        self.own_parameters = own_parameters
        self.parent_object  = parent_object
        print(f"[{self.get_name()}] Initializing the ParamSource with {self.own_parameters} and {self.parent_object.get_name()+' as parent' if self.parent_object else 'no parent'}")


    def get_name(self):
        "Read-only access to the name"

        return self.name


    def parameters_loaded(self):
        "Placeholder for lazy-loading parameters in subclasses that support it"

        if self.own_parameters == None:
            self.own_parameters = {}

        return self.own_parameters


    def parent_loaded(self):
        "Placeholder for lazy-loading the parent in subclasses that support it"

        return self.parent_object


    def __getitem__(self, param_name, calling_top_context=None):
        "Lazy parameter access: returns the parameter value from self or the closest parent"

        calling_top_context = calling_top_context or self

        print(f"[{self.get_name()}] Attempt to access parameter '{param_name}'...")
        own_parameters = self.parameters_loaded()
        hash_param_name = '#'+param_name
        if param_name in own_parameters:
            param_value = own_parameters[param_name]
            print(f'[{self.get_name()}]  I have parameter "{param_name}", returning "{param_value}"')
            return param_value
        elif hash_param_name in own_parameters:
            unsubstituted_expression = own_parameters[hash_param_name]
            print(f'[{self.get_name()}]  I have parameter "{hash_param_name}", the value is "{unsubstituted_expression}"')
            substituted_value = calling_top_context.substitute( unsubstituted_expression )
            print(f'[{self.get_name()}]  Substituting "{unsubstituted_expression}", returning "{substituted_value}"')
            return substituted_value
        else:
            parent_object = self.parent_loaded()
            if parent_object:
                print(f"[{self.get_name()}]  I don't have parameter '{param_name}', fallback to the parent")
                return parent_object.__getitem__(param_name, calling_top_context)
            else:
                print(f"[{self.get_name()}]  I don't have parameter '{param_name}', and no parent either - raising KeyError")
                raise KeyError(param_name)


    def substitute(self, input_string):
        """ Perform single-level parameter substitutions in the given string

            Usage examples:
                clic base_map substitute '#{first}# und #{second}#'
                clic derived_map substitute '#{first}#, #{third}# und #{fifth}#' --first=Erste
        """
        pattern         = re.compile( '({}(\w+){})'.format(re.escape('#{'), re.escape('}#')) )
        output_string   = input_string

        for match in re.finditer(pattern, input_string):
            expression, param_name = match.group(1), match.group(2)
            param_value = self[param_name]
            output_string = output_string.replace(expression, param_value)

        return output_string


    def get(self, param_name, default_value=None):
        """ A safe wrapper around __getitem__() - returns the default_value if missing

            Usage examples:
                clic base_map get fourth Vierte
                clic derived_map get fifth
        """
        try:
            return self[param_name]
        except KeyError:
            return default_value


    def __setitem__(self, param_name, param_value):
        "A simple setter method. We always set the value at the top"

        self.parameters_loaded()[param_name] = param_value


if __name__ == '__main__':

    print('-'*40 + ' Access request delegation down the ParamSource hierarchy: ' + '-'*40)

    granddad    = ParamSource(name='granddad',  own_parameters={"fifth":"viies", "sixth":"kuues"} )
    dad         = ParamSource(name='dad',       own_parameters={"third":"kolmas", "fourth":"neljas"},   parent_object=granddad)
    child       = ParamSource(name='child',     own_parameters={"first":"esimene", "second":"teine"},   parent_object=dad)

    print(f"\tchild['first']={child['first']}\n")
    print(f"\tchild['third']={child['third']}\n")
    print(f"\tchild['fifth']={child['fifth']}\n")
    try:
        print(f"\tchild['seventh']={child['seventh']}\n")
    except KeyError as e:
        print(f"\tMissing parameter: {e}\n")

    print(f"\tAnother missing value: child.get('ninth')={child.get('ninth', 'MISSING')}\n")

    dad['second']       = 'TEINE'
    dad['third']        = 'KOLMAS'
    granddad['seventh'] = 'SEITSMES'

    print(f"granddad.parameters_loaded()={granddad.parameters_loaded()}")
    print(f"dad.parameters_loaded()={dad.parameters_loaded()}")
    print(f"child.parameters_loaded()={child.parameters_loaded()}\n")

    from function_access import feed_a_function, four_param_example_func

    print('-'*40 + ' Access call: ' + '-'*40)

    foo_param_parent = ParamSource('foo_param_parent',  {"alpha": 100, "beta": 200, "delta": 400, "epsilon": 600})
    foo_param_child  = ParamSource('foo_param_child',   {"alpha": 10, "lambda": 7777},                              foo_param_parent)

    param_tuple = ()
    param_dict = foo_param_child
    print(f"feed_a_function(four_param_example_func, {param_tuple}, {param_dict} -->")
    output_tuple = feed_a_function( four_param_example_func, param_tuple, param_dict )
    print(f"--> {output_tuple}\n")


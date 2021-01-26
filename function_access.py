#!/usr/bin/env python3

#   Accessing almost any python function in CK way (feed it with parameters from a dictionary-like object)
#
#   Thanks for this SO entry for inspiration:
#       https://stackoverflow.com/questions/196960/can-you-list-the-keyword-arguments-a-python-function-receives

import sys          # to obtain Python's version
import inspect      # to obtain a random function's signature


def expected_call_structure(function_object, class_method=False):
    """ Get the expected parameters of a function and their default values.
    """

    if sys.version_info[0] < 3:
        supported_arg_names, varargs, varkw, defaults = inspect.getargspec(function_object)
    else:
        supported_arg_names, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations = inspect.getfullargspec(function_object)

    defaults = defaults or tuple()

    if class_method:
        supported_arg_names.pop(0)

    num_required        = len(supported_arg_names) - len(defaults)
    required_arg_names  = supported_arg_names[:num_required]
    optional_arg_names  = supported_arg_names[num_required:]

    return required_arg_names, optional_arg_names, defaults, varargs, varkw


def feed_a_function(function_object, given_arg_list, dict_like_object, class_method=False):
    """ Call a given function_object and feed it with arguments from given list and dictionary-like object (must support []).

        The function can be declared as having named args and defaults.
        Neither *varargs or **kwargs are supported.
    """

    required_arg_names, optional_arg_names, defaults, varargs, varkw = expected_call_structure(function_object, class_method)

    # Topping up the list of required positional arguments, or detecting missing ones:
    num_given                       = len(given_arg_list)
    num_required                    = len(required_arg_names)
    if num_given<num_required:  # some that are required have not been given
        non_listed_required_arg_names   = required_arg_names[num_given:]
    else:                       # all required have been given, the rest are encroaching into optionals
        non_listed_required_arg_names   = []
        optional_arg_names              = optional_arg_names[num_given-num_required:]

    missing_arg_names = []
    non_listed_required_arg_values  = []
    for arg_name in non_listed_required_arg_names:  # topping up from the "dictionary"
        try:
            non_listed_required_arg_values.append( dict_like_object[arg_name] )
        except KeyError as e:
            missing_arg_names.append( arg_name )

    if missing_arg_names:
        raise TypeError( 'The "{}" function is missing required positional arguments: {}'
                        .format(function_object.__name__, missing_arg_names)
        )

    else:
        # Forming the list of values of optional arguments (taking either a provided value or a default in each case) :
        optional_arg_values = []
        for opt_idx, arg_name in enumerate(optional_arg_names):
            try:
                optional_arg_values.append( dict_like_object[arg_name] )
            except KeyError:
                optional_arg_values.append( defaults[opt_idx] )

        #print(f"feed_a_function: About to call `{function_object.__name__}` with {*given_arg_list, *non_listed_required_arg_values, *optional_arg_values}")
        ret_values = function_object(*given_arg_list, *non_listed_required_arg_values, *optional_arg_values)
        return ret_values


def four_param_example_func(alpha, beta, gamma=333, delta=4444):
    print(f'\t[four_param_example_func] alpha = {alpha}, beta = {beta}, gamma = {gamma}, delta = {delta}')
    return alpha, beta, gamma, delta


if __name__ == '__main__':

    print('-'*40 + ' Direct calls: ' + '-'*40)

    param_tuple = (10, 20)
    print(f"four_param_example_func{param_tuple} --> ")
    output_tuple = four_param_example_func(*param_tuple)
    print(f"--> {output_tuple}\n")

    param_tuple = (100, 200, 300)
    print(f"four_param_example_func{param_tuple} --> ")
    output_tuple = four_param_example_func(*param_tuple)
    print(f"--> {output_tuple}\n")


    print('-'*40 + ' Access calls: ' + '-'*40)

    param_tuple = (50, 60)
    param_dict  = {'delta':80}
    print(f"feed_a_function(four_param_example_func, {param_tuple}, {param_dict} -->")
    output_tuple = feed_a_function( four_param_example_func, param_tuple, param_dict )
    print(f"--> {output_tuple}\n")

    param_tuple = (500,)
    param_dict  = {'beta':600, 'gamma':700}
    print(f"feed_a_function(four_param_example_func, {param_tuple}, {param_dict} -->")
    output_tuple = feed_a_function( four_param_example_func, param_tuple, param_dict )
    print(f"--> {output_tuple}\n")

    param_tuple = ()
    param_dict  = {'alpha':5000, 'beta':6000, 'delta':8000}
    print(f"feed_a_function(four_param_example_func, {param_tuple}, {param_dict} -->")
    output_tuple = feed_a_function( four_param_example_func, param_tuple, param_dict )
    print(f"--> {output_tuple}\n")


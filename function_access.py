#!/usr/bin/env python3

#   Accessing almost any python function or method (collectively called an "action") in CK way
#   by feeding it parameters from a list and a dictionary-like object.
#
#   Thanks for this SO entry for inspiration:
#       https://stackoverflow.com/questions/196960/can-you-list-the-keyword-arguments-a-python-function-receives

import inspect      # to obtain a random function's signature
import logging      # for non-obtrusive logging
import sys          # to obtain Python's version


def list_function_names(module_like_object):
    """Return the list of functions of a given Module/Class/Namespace
    """
    function_names = [name for name, function_object in inspect.getmembers(module_like_object, inspect.isfunction)]
    logging.debug(f"Module/Class/Namespace {module_like_object.__name__ if hasattr(module_like_object, '__name__') else ''} contains the following functions: {function_names}")
    return function_names


def expected_call_structure(action_object):
    """Get the expected parameters of a function and their default values.
    """

    if sys.version_info[0] < 3:
        supported_arg_names, varargs, varkw, defaults = inspect.getargspec(action_object)
        kwonlyargs = tuple()
        kwonlydefaults = {}
    else:
        supported_arg_names, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations = inspect.getfullargspec(action_object)

    defaults = defaults or tuple()
    if varargs:
        supported_arg_names += kwonlyargs
        defaults += tuple(kwonlydefaults.values() if kwonlydefaults else [])

    if inspect.ismethod(action_object):
        supported_arg_names.pop(0)

    num_required        = len(supported_arg_names) - len(defaults)
    required_arg_names  = supported_arg_names[:num_required]
    optional_arg_names  = supported_arg_names[num_required:]

    logging.debug(f"{action_object.__name__}() required={required_arg_names}, optional={optional_arg_names}, defaults={defaults}, varargs={varargs}, varkw={varkw}")
    return required_arg_names, optional_arg_names, defaults, varargs, varkw


def feed(action_object, given_arg_list, dict_like_object):
    """Call a given action_object and feed it with arguments from given list and dictionary-like object (must support []).

        The function can be declared as having named args and defaults.
        *varargs are supported while **kwargs are not.
    """

    required_arg_names, optional_arg_names, defaults, varargs, varkw = expected_call_structure(action_object)

    # Topping up the list of required positional arguments, or detecting missing ones:
    num_given                       = len(given_arg_list)
    num_required                    = len(required_arg_names)
    if num_given<num_required:  # some that are required have not been given
        non_listed_required_arg_names   = required_arg_names[num_given:]
    else:
        non_listed_required_arg_names   = []    # all required have been given
        if not varargs:
            optional_arg_names          = optional_arg_names[num_given-num_required:]   # the rest are encroaching into optionals

    missing_arg_names = []
    non_listed_required_arg_values  = []
    for arg_name in non_listed_required_arg_names:  # topping up from the "dictionary"
        try:
            non_listed_required_arg_values.append( dict_like_object[arg_name] )
        except KeyError as e:
            missing_arg_names.append( arg_name )

    if missing_arg_names:
        raise TypeError( 'The "{}" function is missing required positional arguments: {}'
                        .format(action_object.__name__, missing_arg_names)
        )

    else:
        # Forming the dictionary of values of optional arguments (taking either a provided value or a default in each case) :
        optional_arg_dict   = {}
        for opt_idx, arg_name in enumerate(optional_arg_names):
            try:
                optional_arg_dict[arg_name] = dict_like_object[arg_name]
            except KeyError:
                optional_arg_dict[arg_name] = defaults[opt_idx]

        logging.debug(f"About to call `{action_object.__name__}` with list={*given_arg_list, *non_listed_required_arg_values}, dict={optional_arg_dict}")
        ret_values = action_object(*given_arg_list, *non_listed_required_arg_values, **optional_arg_dict)

        return ret_values


def four_param_example_func(alpha, beta, gamma=333, delta=4444):
    "Just an example function for testing purposes"

    logging.debug(f'alpha = {alpha}, beta = {beta}, gamma = {gamma}, delta = {delta}')
    return alpha, beta, gamma, delta


def to_num_or_not_to_num(x):
    "Convert the parameter to a number if it looks like it"

    try:
        x_int = int(x)
        if type(x_int)==int:
            logging.debug(f"converting {repr(x)} to int")
            return x_int
    except:
        try:
            x_float = float(x)
            if type(x_float)==float:
                logging.debug(f"converting {repr(x)} to float")
                return x_float
        except:
            logging.debug(f"keeping {repr(x)} as it was")
            pass

    return x


if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(funcName)s: %(message)s")

    print('-'*40 + ' four_param_example_func() calls: ' + '-'*40)

    assert four_param_example_func(10, 20)==(10, 20, 333, 4444), "Direct call with only positional args"

    assert four_param_example_func(100, 200, 300)==(100, 200, 300, 4444), "Direct call with all positional and some optional-as-positional args"

    assert four_param_example_func(1000, 2000, delta=4000)==(1000, 2000, 333, 4000), "Direct call with all positional and some optional args"

    print('-'*40 + ' feed() calls: ' + '-'*40)

    assert feed(four_param_example_func, (21, 43, 65, 87), None)==(21, 43, 65, 87), "Feed() call with all positional and all optional pretending to be optional"

    assert feed(four_param_example_func, (50, 60), {'delta':80})==(50, 60, 333, 80), "Feed() call with all positional and some optional args"

    assert feed(four_param_example_func, (500,), {'beta':600, 'gamma':700})==(500, 600, 700, 4444), "Feed() call with some positional, some named-positional and some optional args"

    assert feed(four_param_example_func, (), {'alpha':5000, 'beta':6000, 'delta':8000})==(5000, 6000, 333, 8000), "Feed() call with all args posing as optional"

    print('-'*40 + ' to_num_or_not_to_num() calls: ' + '-'*40)

    assert to_num_or_not_to_num("100")==100, "Converting string into int"

    assert to_num_or_not_to_num("100.52")==100.52, "Converting string into float"

    assert to_num_or_not_to_num("abcde")=="abcde", "Not converting into num #1"

    assert to_num_or_not_to_num("100.52x")=="100.52x", "Not converting into num #2"

    print('-'*40 + ' expected_call_structure() calls: ' + '-'*40)

    assert expected_call_structure(four_param_example_func)==(['alpha', 'beta'], ['gamma', 'delta'], (333, 4444), None, None)

    print('-'*40 + ' list_function_names() calls: ' + '-'*40)

    assert sorted(list_function_names(sys.modules[__name__]))==['expected_call_structure', 'feed', 'four_param_example_func', 'list_function_names', 'to_num_or_not_to_num'], "Functions defined in this module"

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


def prep(action_object, given_arg_list, dict_like_object, mapping_used=None):
    """Prepare to call a given action_object and feed it with arguments from given list and dictionary-like object (must support []).

        The function can be declared as having named args and defaults.
        *varargs are supported while **kwargs are not.
    """

    required_arg_names, optional_arg_names, defaults, varargs, varkw = expected_call_structure(action_object)

    # Topping up the list of required positional arguments, or detecting missing ones:
    num_given                       = len(given_arg_list)
    num_required                    = len(required_arg_names)
    listed_optional_names           = []
    if num_given<num_required:  # some that are required have not been given
        non_listed_required_arg_names   = required_arg_names[num_given:]
        if varargs:
            listed_vararg_values        = tuple()   # just not enough
    else:
        non_listed_required_arg_names   = []        # all required have been given
        if varargs:
            listed_vararg_values        = given_arg_list[num_required:]
        else:
            encroached_number           = num_given-num_required
            listed_optional_names       = optional_arg_names[:encroached_number]    # these are encroaching into optionals
            defaults                    = defaults[encroached_number:]
            optional_arg_names          = optional_arg_names[encroached_number:]    # the rest, still to be taken from the dict-like

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

        joint_arg_tuple = (*given_arg_list, *non_listed_required_arg_values)

        if mapping_used is not None:

            mapping_used.update( dict(zip( (*required_arg_names, *listed_optional_names), joint_arg_tuple)) )
            mapping_used.update( optional_arg_dict )
            if varargs:
                mapping_used[varargs] = listed_vararg_values

        logging.debug(f"Prepared to call `{action_object.__name__}` with tuple={joint_arg_tuple}, dict={optional_arg_dict}")

        return action_object, joint_arg_tuple, optional_arg_dict


def feed(action_object, joint_arg_tuple, optional_arg_dict):

    logging.debug(f"Feeding {getattr(action_object, '__name__', 'Unknown')} with {joint_arg_tuple} and {optional_arg_dict} ...")
    ret_values = action_object(*joint_arg_tuple, **optional_arg_dict)
    logging.debug(f"Just fed {getattr(action_object, '__name__', 'Unknown')} , ret_values = {ret_values}")

    return ret_values


def four_param_example_func(alpha, beta, gamma=333, delta=4444):
    "Just an example function for testing purposes"

    logging.debug(f'alpha = {alpha}, beta = {beta}, gamma = {gamma}, delta = {delta}')
    return alpha, beta, gamma, delta


def vararg_supporting_example_func(alpha, beta, *others, gamma=333, delta=4444):
    "Another example function for testing purposes"

    logging.debug(f'alpha = {alpha}, beta = {beta}, others = {others}, gamma = {gamma}, delta = {delta}')
    return alpha, beta, others, gamma, delta



def to_num_or_not_to_num(x):
    "Convert the parameter to a number if it looks like it"

    if isinstance(x, str) and len(x)>1 and x.startswith('"') and x.endswith('"'):
        return x[1:-1]

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

    mapping_used = {}
    assert feed(*prep(four_param_example_func, (10, 20, 30), {}, mapping_used))==(10, 20, 30, 4444), "feed() call with some optionals fed from positionals"
    assert mapping_used=={'alpha': 10, 'beta': 20, 'gamma': 30, 'delta': 4444}, "checking the corresponding mapping used"

    mapping_used = {}
    assert feed(*prep(four_param_example_func, (21, 43, 65, 87), None, mapping_used))==(21, 43, 65, 87), "feed() call with all positional and all optional pretending to be optional"
    assert mapping_used=={'alpha': 21, 'beta': 43, 'gamma': 65, 'delta': 87}, "checking the corresponding mapping used"

    mapping_used = {}
    assert feed(*prep(four_param_example_func, (50, 60), {'delta':80}, mapping_used))==(50, 60, 333, 80), "feed() call with all positional and some optional args"
    assert mapping_used=={'alpha': 50, 'beta': 60, 'gamma': 333, 'delta': 80}, "checking the corresponding mapping used"

    mapping_used = {}
    assert feed(*prep(four_param_example_func, (500,), {'beta':600, 'gamma':700}, mapping_used))==(500, 600, 700, 4444), "feed() call with some positional, some named-positional and some optional args"
    assert mapping_used=={'alpha': 500, 'beta': 600, 'gamma': 700, 'delta': 4444}, "checking the corresponding mapping used"

    mapping_used = {}
    assert feed(*prep(four_param_example_func, (), {'alpha':5000, 'beta':6000, 'delta':8000}, mapping_used))==(5000, 6000, 333, 8000), "feed() call with all args posing as optional"
    assert mapping_used=={'alpha': 5000, 'beta': 6000, 'gamma': 333, 'delta': 8000}, "checking the corresponding mapping used"

    print('-'*40 + ' feed() calls with a *vararg-supporting function: ' + '-'*40)

    mapping_used = {}
    assert feed(*prep(vararg_supporting_example_func, (21, 43, 65, 87), {}, mapping_used))==(21, 43, (65, 87), 333, 4444), "feed()ing a vararg func with an actual overflow"
    assert mapping_used=={'alpha': 21, 'beta': 43, 'gamma': 333, 'delta': 4444, 'others': (65, 87)}, "checking the corresponding mapping used"

    mapping_used = {}
    assert feed(*prep(vararg_supporting_example_func, (21, 43, 65, 87), { 'delta': 800 }, mapping_used))==(21, 43, (65, 87), 333, 800), "feed()ing a vararg func with overflow and a dict"
    assert mapping_used=={'alpha': 21, 'beta': 43, 'gamma': 333, 'delta': 800, 'others': (65, 87)}, "checking the corresponding mapping used"

    mapping_used = {}
    assert feed(*prep(vararg_supporting_example_func, (21, 43), { 'alpha': 210, 'gamma': 70 }, mapping_used))==(21, 43, (), 70, 4444), "feed()ing a vararg func flush"
    assert mapping_used=={'alpha': 21, 'beta': 43, 'gamma': 70, 'delta': 4444, 'others': ()}, "checking the corresponding mapping used"

    mapping_used = {}
    assert feed(*prep(vararg_supporting_example_func, (), { 'alpha': 2100, 'beta': 4300, 'delta': 8000 }, mapping_used))==(2100, 4300, (), 333, 8000), "feed()ing a vararg func with not enough list, compensated from a dict"
    assert mapping_used=={'alpha': 2100, 'beta': 4300, 'gamma': 333, 'delta': 8000, 'others': ()}, "checking the corresponding mapping used"


    print('-'*40 + ' to_num_or_not_to_num() calls: ' + '-'*40)

    assert to_num_or_not_to_num("100")==100, "Converting string into int"

    assert to_num_or_not_to_num("100.52")==100.52, "Converting string into float"

    assert to_num_or_not_to_num("abcde")=="abcde", "Not converting into num #1"

    assert to_num_or_not_to_num("100.52x")=="100.52x", "Not converting into num #2"

    print('-'*40 + ' expected_call_structure() calls: ' + '-'*40)

    assert expected_call_structure(four_param_example_func)==(['alpha', 'beta'], ['gamma', 'delta'], (333, 4444), None, None)

    print('-'*40 + ' list_function_names() calls: ' + '-'*40)

    assert sorted(list_function_names(sys.modules[__name__]))==['expected_call_structure', 'feed', 'four_param_example_func', 'list_function_names', 'prep', 'to_num_or_not_to_num', 'vararg_supporting_example_func'], "Functions defined in this module"

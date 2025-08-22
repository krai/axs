#!/usr/bin/env python3

import inspect
import logging
import sys

from param_source import ParamSource

logger = logging.getLogger(__name__)

def list_function_names(module_like_object):
    """Return the list of functions of a given Module/Class/Namespace
    """
    function_names = [name for name, function_object in inspect.getmembers(module_like_object, inspect.isfunction)]
    logging.debug(f"Module/Class/Namespace {module_like_object.__name__ if hasattr(module_like_object, '__name__') else ''} contains the following functions: {function_names}")
    return function_names


def expected_call_structure(action_object):
    """Get the expected parameters of a function and their default values.
    """

    try:
        supported_arg_names, varargs, varkw, defaults, kwonlyargs, kwonlydefaults, annotations = inspect.getfullargspec(action_object)
    except TypeError:
        return [],{},[],'varargs',None

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
 

class Runnable(ParamSource):

    def __init__(self, action, pos_params=None, parent_entry=None, own_data=None, **kwargs):

        if pos_params is None:
            self.pos_params = []                                 # allow pos_params to be missing
        elif type(pos_params)!=list:
            self.pos_params = [ pos_params ]                     # simplified syntax for single positional parameter actions
        else:
            self.pos_params = pos_params

        self.param_value_cache  = parent_entry.param_value_cache if parent_entry.__class__==Runnable and not own_data else {}

        if parent_entry:
            kwargs['parent_objects'] = [ parent_entry ]

        if own_data:
            kwargs['own_data'] = own_data
        super().__init__(**kwargs)  # own_data will hopefully be defined there

        if type(action)==str:
            self.action_name = action
            try:
                _, self.action_object, _ = next( self.find_in_hierarchy_generator( "find_action_generator", self.action_name, parent_recursion='deep', include_self=True) )
            except StopIteration:
#                logging.debug(f"[{self.get_name()}]  I don't have action '{self.action_name}', and neither do the parents - raising NameError")
                raise NameError(self.action_name)

        else:
            self.action_object, self.action_name = action, "Unnamed_Function"

        logging.debug(f"[***] Initializing Runnable(action={self.action_name}, pos_params={self.pos_params} and parent_objects={self.parent_objects}")


    def __call__(self, captured_mapping=None):

        # FIXME: prep() call cannot move to __init__ as it needs a pre-initialized self object, but maybe at least expected_call_structure() could be called inside __init__ ?
        action_object, joint_arg_tuple, optional_arg_dict   = prep(self.action_object, self.pos_params, self, captured_mapping)

        result  = feed(action_object, joint_arg_tuple, optional_arg_dict)

        return result


    def display_header(self):
        return f"{type(self).__name__}/{id(self)} {self.action_name}({self.pos_params}, {id(self.own_data())}"


    def is_overrider(self):
        return True


    def __getitem__(self, param_name, parent_recursion=None, include_self=True):

        if param_name=='__entry__':
            return self.base_entry()

        elif param_name in self.param_value_cache:
            param_value = self.param_value_cache[param_name]
            logging.info(f"[{self.display_header()}]  FOUND IN CACHE [{param_name}] -> {param_value}")

        else:
            param_value = super().__getitem__(param_name, parent_recursion=parent_recursion, include_self=include_self)

            logging.info(f"[{self.display_header()}]  NOT YET IN CACHE [{param_name}] , the hierarchy (parent_recursion={parent_recursion}, include_self={include_self}) -> {param_value}")

            computed_expr_value = self.nested_calls( param_value )

            logging.info(f"[{self.display_header()}]  Running a sub-call to __getitem__({param_name}, {parent_recursion}, {include_self}) : {param_value} ---> {computed_expr_value}")
            param_value = computed_expr_value

            logging.info(f"[{self.display_header()}]  CACHING [{param_name}] := {param_value}")
            self.param_value_cache[param_name] = param_value

        return param_value


def four_param_example_func(alpha, beta, gamma=333, delta=4444):
    "Just an example function for testing purposes"

    logging.debug(f'alpha = {alpha}, beta = {beta}, gamma = {gamma}, delta = {delta}')
    return alpha, beta, gamma, delta


def vararg_supporting_example_func(alpha, beta, *others, gamma=333, delta=4444):
    "Another example function for testing purposes"

    logging.debug(f'alpha = {alpha}, beta = {beta}, others = {others}, gamma = {gamma}, delta = {delta}')
    return alpha, beta, others, gamma, delta


def plus_one(x):
    "Adds 1 to the argument"
    return x+1





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


    print('-'*40 + ' expected_call_structure() calls: ' + '-'*40)

    assert expected_call_structure(four_param_example_func)==(['alpha', 'beta'], ['gamma', 'delta'], (333, 4444), None, None)

    # Existing python functions
    hexer1 = Runnable( hex, pos_params=[255] )
    print("hex(255)=", hexer1())

    hexer2 = Runnable( hex, own_data={'number':31} )
    print("hex(31)=", hexer2())

    printer = Runnable( print, pos_params=['Hello', 'world!'] )
    print( "print('Hello','world')=", printer())


    # ad hoc lambda function, without a parent_entry (pure Runnable functionality)
    ad_hoc_sum1 = Runnable(lambda x, y, z: x+y+z, pos_params=[11, 22], own_data={'z':44})()
    print("X+Y+Z=", ad_hoc_sum1)

    # same function, but with a base_entry
    base_entry = ParamSource(name='base_entry', own_data={'x':10, 'y':30})
    override_entry = Runnable( lambda x, y, z: x+y+z , name='override_entry', own_data={'x':200,'z':4}, parent_entry=base_entry )
    print( "x+y+z=", override_entry() )

    from argparse import Namespace

    def trice(number):
        "Multiplies the argument by 3"
        return number*3

    granddad    = ParamSource(name='granddad', own_data={'x': 10, 'y': 20, 'one': 1}, own_functions=Namespace( add_one=plus_one, subtract_one=(lambda x: x-1)         ) )
    dad         = ParamSource(name='dad',      own_data={'number':37, 't': ["^^", "triple", [], {} ]}, own_functions=Namespace( double=(lambda x: x*2), triple=trice ), parent_objects=[granddad])
    mum         = ParamSource(name='mum',      own_functions=Namespace( cube=(lambda x: x*x*x)                                 ) )
    child       = ParamSource(name='child',    own_functions=Namespace( square=(lambda x: x*x)                                 ), parent_objects=[dad, mum])

    call_1      = Runnable('add_one', parent_entry=child)()
    print(call_1)
    call_2      = Runnable('subtract_one', parent_entry=child, own_data={'x':100})()
    print(call_2)

    call_3      = Runnable('substitute', pos_params=["Y=#{y}#, T=#{t}#, Y=#{y}#"], parent_entry=child)()
    print(call_3)


    pre_call_4  = Runnable('noop', pos_params=['abc'], parent_entry=child)
    call_4 = pre_call_4()
    print(call_4)

    from stored_entry import Entry
    e2 = Entry(entry_path="/Users/lg4/tmp/robin/point_2d")
    print(e2.own_data())
    print(e2["report"])
    norm1 = Runnable("get_norm", own_data={'y':4}, parent_entry=e2)()
    print(f"norm1={norm1}")

    print( "Child is overrider:", child, child.is_overrider() )
    print( "pre-Call4 is overrider:", pre_call_4, pre_call_4.is_overrider() )
    print( "Child's base entry:", child.base_entry(), child.base_entry().get_name() )
    print( "pre-Call4's base entry':", pre_call_4.base_entry(), pre_call_4.base_entry().get_name() )

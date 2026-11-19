#!/usr/bin/env python3

"""axs04: a ParamSource that can also find and call actions.

Running this file as a script runs the tests of its Python API.
"""

import inspect
import sys

from param_source import ParamSource


def prep(action_object, pos_params, named_params, param_source):
    """Work out the arguments that action_object should be called with, without calling it.
        Each parameter of the function gets the first value found in this order: the given positional parameters,
        the named_params dictionary, the parameters of param_source (including inherited ones), the function's own default.
        Positional parameters beyond the function's named ones go into its *args, if it has any.
        Its **kwargs, if it has them, receive those entries of named_params that match none of its named parameters
        (never values from param_source); without **kwargs such entries do not reach the function.
        Raises TypeError if there are too many positional parameters or if a required parameter has no value.
        Returns a tuple (action_object, args, kwargs) that can be passed to feed().
    """
    signature   = inspect.signature(action_object)
    bound       = signature.bind_partial(*pos_params)
    missing     = []

    for param_name, param in signature.parameters.items():
        if param_name in bound.arguments or param.kind is param.VAR_POSITIONAL:
            continue
        if param.kind is param.VAR_KEYWORD:
            bound.arguments[param_name] = { k: v for k, v in named_params.items()
                                            if k not in signature.parameters or signature.parameters[k].kind is param.POSITIONAL_ONLY }
            continue
        if param_name in named_params:
            bound.arguments[param_name] = named_params[param_name]
        else:
            try:
                bound.arguments[param_name] = param_source[param_name]
            except KeyError:
                if param.default is param.empty:
                    missing.append(param_name)

    if missing:
        raise TypeError(f"{getattr(action_object, '__name__', action_object)}() has no value for required parameters {missing}")

    bound.apply_defaults()
    return action_object, bound.args, bound.kwargs


def feed(action_object, args, kwargs):
    """Call action_object with the positional args and keyword kwargs (as prepared by prep()) and return the result.
    """
    return action_object(*args, **kwargs)


class ActionSource(ParamSource):
    """An object of ActionSource class is a ParamSource that can also find and call actions.

        An action is either a function from the own_functions namespace of an object in the hierarchy,
        or a public method of the object itself (such as get() or plant()).
        When an action is called, its parameters are looked up starting from the object it was called on,
        even if the function itself was found in a parent.
    """

    def __init__(self, name=None, own_data=None, parent_objects=None, own_functions=None):
        """Create a container with an optional name, an optional dictionary of own data, an optional list of parent objects
            and an optional namespace of own functions (any object whose attributes are functions, such as a module).
        """
        super().__init__(name=name, own_data=own_data, parent_objects=parent_objects)
        self.own_functions_cache = own_functions


    def own_functions(self):
        """Return this object's namespace of own functions, or None if it has none.
        """
        return self.own_functions_cache


    def find_action(self, action_name):
        """Return the callable that implements the named action.
            Own functions are searched first, through the hierarchy in depth-first order (see hierarchy_generator()),
            skipping parents that have no functions. Only if no own function is found, a public method of this object is used,
            so that an object's code can redefine a built-in method for itself and all its descendants.
            Raises NameError if there is no such action.
        """
        for source_object in self.hierarchy_generator():
            functions_ns = source_object.own_functions() if isinstance(source_object, ActionSource) else None
            found_function = getattr(functions_ns, action_name, None)
            if inspect.isfunction(found_function):
                return found_function

        if not action_name.startswith('_') and inspect.ismethod( getattr(self, action_name, None) ):
            return getattr(self, action_name)

        raise NameError(f"[{self.get_name()}] has no action '{action_name}': neither a function in the hierarchy nor a public method")


    def call(self, action_name, pos_params=None, named_params=None):
        """Find the named action, fill its parameters (see prep()) using this object as the source of parameters, and run it.
            Returns whatever the action returns. The call itself changes neither this object nor its parents.
        """
        action_object = self.find_action(action_name)
        return feed( *prep(action_object, pos_params or [], named_params or {}, self) )


if __name__ == '__main__' or 'unittest' in sys.modules:    # run as a script, or collected by unittest/pytest (which have already loaded unittest)

    import unittest
    from types import SimpleNamespace

    class TestActionSource(unittest.TestCase):

        def setUp(self):
            """A parent with functions and data, a child with data only, and a parent that is a plain ParamSource.
            """
            self.funcs = SimpleNamespace(
                add3        = lambda a, b, c=0: a + b + c,
                collect     = lambda first, *rest, label='L': (first, rest, label),
                kw_only     = lambda a, *, k: (a, k),
                with_kwargs = lambda a, **extra: (a, extra),
                explode     = lambda a: 1/0,
                get_name    = lambda: 'redefined by code',
            )
            self.base   = ActionSource('base',  { 'a': 1, 'b': 2 }, own_functions=self.funcs)
            self.child  = ActionSource('child', { 'b': 20 }, [self.base])
            self.mixed  = ActionSource('mixed', {}, [ParamSource('plain', { 'a': 1, 'b': 2 })], own_functions=self.funcs)

        def test_fill_from_hierarchy(self):         self.assertEqual( self.child.call('add3'), 21 )     # a inherited, b own, c default
        def test_params_from_asking_object(self):   self.assertEqual( (self.base.call('add3'), self.child.call('add3')), (3, 21) )
        def test_positional_wins(self):             self.assertEqual( self.child.call('add3', [100]), 120 )
        def test_named_beats_data_and_default(self): self.assertEqual( self.child.call('add3', named_params={'a': 7, 'c': 5}), 32 )
        def test_unmatched_named_ignored(self):     self.assertEqual( self.child.call('add3', named_params={'zzz': 1}), 21 )
        def test_varargs(self):                     self.assertEqual( (self.child.call('collect', [1, 2, 3]), self.child.call('collect', named_params={'first': 0})), ((1, (2, 3), 'L'), (0, (), 'L')) )
        def test_kwargs_get_unmatched_named(self):  self.assertEqual( self.child.call('with_kwargs', named_params={'a': 7, 'zzz': 1}), (7, {'zzz': 1}) )   # 'b' from data never reaches **extra
        def test_keyword_only(self):                self.assertEqual( self.child.call('kw_only', named_params={'k': 9}), (1, 9) )
        def test_missing_required_raises(self):     self.assertRaises( TypeError, ActionSource('lonely', own_functions=self.funcs).call, 'add3' )
        def test_too_many_positionals_raise(self):  self.assertRaises( TypeError, self.child.call, 'add3', [1, 2, 3, 4] )
        def test_method_as_action(self):            self.assertEqual( (self.child.call('get', ['a']), self.child.call('own_data')), (1, {'b': 20}) )
        def test_code_redefines_method(self):       self.assertEqual( (self.child.call('get_name'), self.child.get_name()), ('redefined by code', 'child') )
        def test_private_method_not_an_action(self): self.assertRaises( NameError, self.child.call, '__getitem__', ['a'] )
        def test_unknown_action_raises(self):       self.assertRaises( NameError, self.child.call, 'no_such_action' )
        def test_plain_param_source_parent(self):   self.assertEqual( self.mixed.call('add3'), 3 )
        def test_own_function_shadows_parents(self):
            self.assertEqual( ActionSource('shadow', {}, [self.base], own_functions=SimpleNamespace(add3=lambda a: -a)).call('add3'), -1 )
        def test_prep_does_not_run(self):
            self.assertEqual( prep(self.funcs.explode, [], {}, self.child), (self.funcs.explode, (1,), {}) ); self.assertRaises( ZeroDivisionError, self.child.call, 'explode' )
        def test_prep_reports_arguments(self):      self.assertEqual( prep(self.funcs.add3, [], {'c': 5}, self.child), (self.funcs.add3, (1, 20, 5), {}) )
        def test_call_has_no_side_effects(self):
            self.child.call('add3', named_params={'a': 7, 'c': 5}); self.assertEqual( (self.child.own_data(), self.base.own_data()), ({'b': 20}, {'a': 1, 'b': 2}) )

    if __name__ == '__main__':
        unittest.main(verbosity=2)

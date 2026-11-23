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

        Each call creates an override (see ParamSource) holding the call's named parameters, on top of the object called,
        and the action runs on it: a method of the object is bound to the override, and a function that declares the parameter
        __entry__ receives the override (or, declaring __real_entry__, the real object underneath). So lookups and nested calls
        see the call's named parameters, while edits and questions of identity concern the real object (see ParamSource.on_real_entry()).
    """

    def __init__(self, name=None, own_data=None, parent_objects=None, own_functions=None, is_override=False):
        """Create a container with an optional name, an optional dictionary of own data, an optional list of parent objects
            and an optional namespace of own functions (any object whose attributes are functions, such as a module).
            With is_override set, the object becomes an override (see ParamSource).
        """
        super().__init__(name=name, own_data=own_data, parent_objects=parent_objects, is_override=is_override)
        self.own_functions_cache = own_functions


    def own_functions(self):
        """Return this object's namespace of own functions, or None if it has none.
        """
        return self.own_functions_cache


    def __getitem__(self, param_name):
        """Return the value of a parameter as ParamSource does, except for two special names:
            __entry__ gives this object itself, and __real_entry__ the real object underneath it (see ParamSource.real_entry()).
        """
        if str(param_name)=='__entry__':
            return self
        if str(param_name)=='__real_entry__':
            return self.real_entry()
        return super().__getitem__(param_name)


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


    def can(self, action_name):
        """Return whether this object has the named action (see find_action()).
        """
        try:
            self.find_action(action_name)
            return True
        except NameError:
            return False


    def call(self, action_name, pos_params=None, named_params=None):
        """Create an override (of the same class) holding named_params on top of this object, find the named action on it,
            fill its parameters from it (see prep()), and run it. Methods found as actions are therefore bound to the override.
            Returns whatever the action returns. The call itself changes neither this object nor its parents.
        """
        pos_params      = pos_params or []
        named_params    = named_params or {}
        call_override   = type(self)(own_data=dict(named_params), parent_objects=[self], is_override=True)
        action_object   = call_override.find_action(action_name)
        return feed( *prep(action_object, pos_params, named_params, call_override) )


    def execute(self, pipeline):
        """Run a pipeline of calls starting from this object (the originator), and return the result of the last call.
            Each step is a list [action_name], [action_name, pos_params] or [action_name, pos_params, named_params];
            pos_params that is not a list is a single positional parameter. Each step is called on the result of the previous one:
            an ActionSource through call(), any other object by calling its method of that name directly.
            Markers between steps change what the next step is called on:
                []      (" , , " on the command line)   the originator again;
                "-"     (" ,- " on the command line)    the object the previous step was called on, discarding that step's result.
            A trailing marker makes the pipeline return that object. An empty pipeline returns the originator.
        """
        result = current_object = previous_object = self

        for step in pipeline:
            if step == []:
                current_object = self
                continue
            if step == '-':
                result = current_object = previous_object
                continue
            if len(step) > 3:
                raise ValueError(f"[{self.get_name()}] a pipeline step has at most 3 elements (action_name, pos_params, named_params), got {step}")

            action_name     = step[0]
            pos_params      = step[1] if len(step) > 1 else []
            named_params    = step[2] if len(step) > 2 else {}
            if type(pos_params) != list:
                pos_params = [ pos_params ]

            previous_object = current_object
            if isinstance(current_object, ActionSource):
                result = current_object.call(action_name, pos_params, named_params)
            else:
                result = getattr(current_object, action_name)(*pos_params, **named_params)
            current_object = result

        return result


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
                peek        = lambda __entry__: __entry__['b'],
                outer       = lambda __entry__: __entry__.call('add3'),
                bump        = lambda __entry__: __entry__.plant('counter+', 1),
                who         = lambda __entry__: (__entry__.is_override(), __entry__.real_entry().get_name()),
                real_name   = lambda __real_entry__: (__real_entry__.is_override(), __real_entry__.get_name()),
                promote_deeper = lambda __entry__: __entry__.call('promote', [], {'y': 2}),
            )
            self.peer   = ActionSource('peer',  { 'a': 100, 'b': 200 }, own_functions=self.funcs)
            self.base   = ActionSource('base',  { 'a': 1, 'b': 2 }, own_functions=self.funcs)
            self.child  = ActionSource('child', { 'b': 20 }, [self.base])
            self.mixed  = ActionSource('mixed', {}, [ParamSource('plain', { 'a': 1, 'b': 2 })], own_functions=self.funcs)
            self.start  = ActionSource('start', { 'peer': self.peer, 'words': 'alpha-beta-gamma' }, [self.child])    # where the pipeline tests start

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
        def test_method_as_action(self):            self.assertEqual( (self.child.call('get', ['a']), self.child.call('entry_data')), (1, {'b': 20}) )
        def test_code_redefines_method(self):       self.assertEqual( (self.child.call('get_name'), self.child.get_name()), ('redefined by code', 'child') )
        def test_private_method_not_an_action(self): self.assertRaises( NameError, self.child.call, '__getitem__', ['a'] )
        def test_can(self):                         self.assertEqual( (self.child.can('add3'), self.child.can('get'), self.child.can('no_such_action')), (True, True, False) )
        def test_unknown_action_raises(self):       self.assertRaises( NameError, self.child.call, 'no_such_action' )
        def test_plain_param_source_parent(self):   self.assertEqual( self.mixed.call('add3'), 3 )
        def test_own_function_shadows_parents(self):
            self.assertEqual( ActionSource('shadow', {}, [self.base], own_functions=SimpleNamespace(add3=lambda a: -a)).call('add3'), -1 )
        def test_prep_does_not_run(self):
            self.assertEqual( prep(self.funcs.explode, [], {}, self.child), (self.funcs.explode, (1,), {}) ); self.assertRaises( ZeroDivisionError, self.child.call, 'explode' )
        def test_prep_reports_arguments(self):      self.assertEqual( prep(self.funcs.add3, [], {'c': 5}, self.child), (self.funcs.add3, (1, 20, 5), {}) )
        def test_call_has_no_side_effects(self):
            self.child.call('add3', named_params={'a': 7, 'c': 5}); self.assertEqual( (self.child.own_data(), self.base.own_data()), ({'b': 20}, {'a': 1, 'b': 2}) )

        def test_named_reach_lookups_inside(self):  self.assertEqual( (self.child.call('peek', named_params={'b': 99}), self.child.call('peek')), (99, 20) )
        def test_named_reach_nested_calls(self):    self.assertEqual( self.child.call('outer', named_params={'c': 5}), 26 )
        def test_entry_is_the_override(self):       self.assertEqual( self.child.call('who'), (True, 'child') )
        def test_entry_outside_a_call(self):        self.assertIs( self.child['__entry__'], self.child )
        def test_edits_through_entry_persist(self):
            self.child.call('bump'); self.child.call('bump'); self.assertEqual( (self.child['counter'], 'counter' in self.base.own_data()), (2, False) )
        def test_method_action_edits_object(self):
            self.child.call('plant', ['counter', 5]); self.assertEqual( self.child.own_data(), {'b': 20, 'counter': 5} )
        def test_nested_call_has_no_side_effects(self):
            self.child.call('outer', named_params={'a': 7, 'c': 5}); self.assertEqual( (self.child.own_data(), self.base.own_data()), ({'b': 20}, {'a': 1, 'b': 2}) )

        def test_execute_one_step(self):            self.assertEqual( self.start.execute([ ['add3', [], {'c': 5}] ]), 26 )
        def test_execute_chains_on_result(self):    self.assertEqual( self.start.execute([ ['get', ['peer']], ['add3'] ]), 300 )
        def test_execute_plain_object_methods(self): self.assertEqual( self.start.execute([ ['get', 'words'], ['split', '-'], ['__getitem__', 1] ]), 'beta' )
        def test_execute_back_to_originator(self):  self.assertEqual( self.start.execute([ ['get', ['peer']], [], ['add3'] ]), 21 )
        def test_execute_previous_object_marker(self): self.assertEqual( self.start.execute([ ['get', 'peer'], ['add3'], '-', ['get', 'a'] ]), 100 )   # continue from peer, not from 300
        def test_execute_trailing_marker_returns_object(self): self.assertIs( self.start.execute([ ['get', 'peer'], ['add3'], '-' ]), self.peer )
        def test_execute_marker_after_side_effect(self):    # dict.update() returns None, so only ,- lets the chain carry on from the dict
            self.assertEqual( self.start.execute([ ['get', 'peer'], ['own_data'], ['update', {'note': 'set'}], '-', ['pop', 'note'] ]), 'set' )
        def test_execute_empty_pipeline(self):      self.assertIs( self.start.execute([]), self.start )
        def test_execute_as_an_action(self):        self.assertEqual( self.start.call('execute', [[ ['get', 'peer'], ['get', 'b'] ]]), 200 )
        def test_execute_step_too_long(self):       self.assertRaises( ValueError, self.child.execute, [ ['add3', [], {}, 'label'] ] )
        def test_execute_has_no_side_effects(self):
            self.start.execute([ ['add3', [], {'a': 7}], [], ['get', 'peer'], ['add3', [], {'c': 1}] ]); self.assertEqual( (self.start.own_data(), self.child.own_data(), self.peer.own_data()), ({'peer': self.peer, 'words': 'alpha-beta-gamma'}, {'b': 20}, {'a': 100, 'b': 200}) )

        def test_methods_see_call_params(self):     self.assertEqual( self.child.call('get', ['xyz'], {'xyz': 123}), 123 )
        def test_own_data_is_the_calls(self):       self.assertEqual( (self.child.call('own_data', [], {'q': 1}), self.child.call('entry_data', [], {'q': 1})), ({'q': 1}, {'b': 20}) )
        def test_identity_through_call(self):       self.assertEqual( ActionSource('plain', {'b': 1}).call('get_name', [], {'q': 1}), 'plain' )   # an object whose hierarchy does not redefine get_name
        def test_edits_return_real_object(self):    self.assertIs( self.child.call('plant', ['k', 1]), self.child )
        def test_real_entry_parameter(self):        self.assertEqual( self.child.call('real_name', [], {'q': 1}), (False, 'child') )
        def test_promote_through_call(self):
            promoted = self.child.call('promote', [], {'x': 1}); self.assertEqual( (promoted.own_data(), promoted['b'], promoted.is_override()), ({'x': 1}, 20, False) )
        def test_promote_flattens_nested_calls(self):
            self.assertEqual( self.child.call('promote_deeper', [], {'x': 1}).own_data(), {'x': 1, 'y': 2} )

    if __name__ == '__main__':
        unittest.main(verbosity=2)

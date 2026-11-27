#!/usr/bin/env python3

"""axs04: a ParamSource that can also find and call actions.

Running this file as a script runs the tests of its Python API.
"""

import builtins
import difflib
import importlib
import inspect
import sys
import textwrap
from copy import deepcopy

from param_source import ParamSource, split_key_path, FIRING_STACK, versioned, dependencies_still_hold


def prep(action_object, pos_params, named_params, param_source):
    """Work out the arguments that action_object should be called with, without calling it.
        Each parameter of the function gets the first value found in this order: the given positional parameters,
        the named_params dictionary, the parameters of param_source (including inherited ones), the function's own default.
        Positional parameters beyond the function's named ones go into its *args, if it has any.
        Its **kwargs, if it has them, receive those entries of named_params that match none of its named parameters
        (never values from param_source); without **kwargs such entries do not reach the function.
        A callable without an inspectable signature (such as Python's max) receives only pos_params and named_params, as they are.
        Raises TypeError if there are too many positional parameters or if a required parameter has no value.
        Returns a tuple (action_object, args, kwargs) that can be passed to feed().
    """
    try:
        signature   = inspect.signature(action_object)
    except ValueError:
        return action_object, list(pos_params), dict(named_params)
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


PYTHON_SCHEME = 'py:'

def reach_python_callable(python_name):
    """Return the Python callable that python_name names, written exactly as in Python: a built-in (len, max),
        or a dotted path whose longest importable prefix is a module and whose rest are attributes (os.path.join, operator.mul),
        or attributes of a built-in (str.upper). Raises NameError if there is no such callable.
    """
    name_parts = python_name.split('.')
    for split_at in range(len(name_parts)-1, -1, -1):
        try:
            current_object = importlib.import_module('.'.join(name_parts[:split_at])) if split_at else builtins
        except ImportError:
            continue
        try:
            for attribute_name in name_parts[split_at:]:
                current_object = getattr(current_object, attribute_name)
        except AttributeError:
            break
        if callable(current_object):
            return current_object
        break
    raise NameError(f"there is no Python callable '{python_name}'")


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


    def fire_inert_expression(self, param_name, inert_expression, holding_object):
        """Compute a parameter from its inert expression [action_name], [action_name, pos_params] or [action_name, pos_params, named_params]
            (pos_params that is not a list is a single positional parameter), by calling the named action on this object, the asking one,
            whichever object holds the expression. So the expression's positional parameters bind the action's arguments directly,
            its named parameters form the top layer of the call, and everything else comes from where the lookup started.
            The value is cached together with every lookup made while computing it (see ParamSource), and reused while all those
            lookups would still find the same providers unchanged. It is cached in this object, or, if this object is an override
            with no data of its own, in the first object beneath it that has some (see cache_owner()): an empty override cannot change
            what any lookup finds, so computations through any number of them can share one result.
            Raises ValueError for a cycle: the same expression needed again for the same cache owner while it is being computed,
            which would only repeat the same computation; a recursion that brings new parameters each time is fine.
        """
        if type(inert_expression)!=list or not 1 <= len(inert_expression) <= 3 or type(inert_expression[0])!=str:
            raise ValueError(f"[{holding_object.get_name()}] '@{param_name}' should be [action_name], [action_name, pos_params] or [action_name, pos_params, named_params], got {inert_expression!r}")

        cache_owner = self.cache_owner()
        cached      = cache_owner.computed_values.get(param_name)
        if cached and dependencies_still_hold(cached[1]):
            value, dependencies = cached
        else:
            firing_key = ( id(holding_object), param_name )
            if any( frame[0]==firing_key and frame[1] is cache_owner for frame in FIRING_STACK ):
                raise ValueError(f"[{holding_object.get_name()}] '@{param_name}' needs its own value to be computed (a cycle)")

            action_name     = inert_expression[0]
            pos_params      = inert_expression[1] if len(inert_expression) > 1 and inert_expression[1] is not None else []
            named_params    = inert_expression[2] if len(inert_expression) > 2 and inert_expression[2] is not None else {}
            FIRING_STACK.append( [ firing_key, cache_owner, [ (self, param_name, versioned(holding_object)) ] ] )
            try:
                value = self.call(action_name, pos_params if type(pos_params)==list else [ pos_params ], named_params)
            finally:
                dependencies = FIRING_STACK.pop()[2]
            cache_owner.computed_values[param_name] = ( value, dependencies )

        if FIRING_STACK:
            FIRING_STACK[-1][2].extend(dependencies)     # whatever needed this value depends on what it depends on
        return value


    def cache_owner(self):
        """Return the object whose cache serves this one (see fire_inert_expression()): this object itself,
            unless it is an override with no data of its own, in which case the first object beneath it that has some data, or is real.
        """
        owner = self
        while owner.is_override() and not owner.own_data():
            owner = owner.parent_objects()[0]
        return owner


    def find_action(self, action_name):
        """Return the callable that implements the named action.
            Own functions are searched first, through the hierarchy in depth-first order (see hierarchy_generator()),
            skipping parents that have no functions. Only if no own function is found, a public method of this object is used,
            so that an object's code can redefine a built-in method for itself and all its descendants.
            A name starting with 'py:' is any Python callable, written after it exactly as in Python (see reach_python_callable()):
            it becomes the action itself, so its parameters are filled like any action's, including by name from the call's context.
            Raises NameError if there is no such action.

            Usage examples:
                axs py:len abcde                                                         # => 5
                axs py:os.path.join alpha beta                                           # => alpha/beta
                axs py:str.upper hello                                                   # => HELLO
                axs py:operator.mul --a=6 --b=7                                          # => 42
                axs py:max 3 7 5                                                         # => 7
                axs noop --,=alpha,beta ,0 py:len                                        # => 2
                axs byname pyramid , py:operator.mul --b=10                              # => 30
        """
        if action_name.startswith(PYTHON_SCHEME):
            return reach_python_callable( action_name[len(PYTHON_SCHEME):] )

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

            Usage examples:
                axs byname baz , can get                                                 # => True
                axs can fly                                                              # => False
        """
        try:
            self.find_action(action_name)
            return True
        except NameError:
            return False


    def call(self, action_name, pos_params=None, named_params=None):
        """Create an override (of the same class) holding named_params on top of this object, find the named action on it,
            fill its parameters from it (see prep()), and run it. Methods found as actions are therefore bound to the override.
            A named parameter whose key contains a dot or ends in '+' edits the value the call sees instead of replacing it:
            the whole inherited value is first copied into the override (unless the call gives that parameter itself),
            then the edit is planted into the copy (see ParamSource.plant()), in the order given, after the plain parameters.
            Such edits never match a function's parameters or reach its **kwargs: their effect reaches functions through the override.
            Neither do inert expressions given as '@name': they become part of the call's layer, so they fire when anything
            during the call (including other expressions fired during it) asks for 'name'.
            Returns whatever the action returns. The call itself changes neither this object nor its parents.

            Usage examples:
                axs byname baz , call get --,=greeting                                   # => hello from baz
                axs noop --arg.colour.green=255                                          # => {'colour': {'green': 255}}
                axs dig greek.2 --greek,=alpha,beta --greek+=gamma                       # => gamma
                axs byname foo , get greeting --greeting+=_and_more                      # => hello from foo_and_more
        """
        pos_params      = pos_params or []
        named_params    = named_params or {}
        plain_params    = { key: value for key, value in named_params.items() if not is_edit_key(key) }     # including '@name' expressions
        override_data   = dict(plain_params)

        edits = [ (key, value) for key, value in named_params.items() if is_edit_key(key) ]
        if edits:
            edited_layer = ParamSource(own_data=override_data)      # plants straight into override_data
            for key_path, value in edits:
                top_name = split_key_path(key_path)[0].rstrip('+')
                if top_name not in override_data and self.get(top_name) is not None:
                    override_data[top_name] = deepcopy( self.get(top_name) )     # copy-on-write: never edit what lies beneath
                edited_layer.plant(key_path, value)

        call_override   = type(self)(own_data=override_data, parent_objects=[self], is_override=True)
        action_object   = call_override.find_action(action_name)
        argument_params = { key: value for key, value in plain_params.items() if not key.startswith('@') }
        return feed( *prep(action_object, pos_params, argument_params, call_override) )


    def help(self, action_name: str = None) -> str:
        """Describe this object, or one of its actions, using its DocStrings and the action's signature.
            Without an action name: the object's identity, the module DocString of its code, and every action available to it
            with the first sentence of its DocString, grouped by where the action comes from (own code, each ancestor's code, built-in methods).
            With an action name: where the action comes from, its signature (with any declared types), each parameter with its kind,
            declared type, default and where its value would come from in this very call, and the full DocString.

            Usage examples:
                axs help
                axs help help
                axs byname baz , help
                axs byname baz , help get
                axs byname baz , help get --greeting=hi
                axs help bypath
                axs help py:math.hypot
        """
        return self._describe_action(action_name) if action_name else self._describe_object()


    def _describe_object(self):
        """Return the text of help() for the object itself (see help()).
        """
        real_entry  = self.real_entry()
        lines       = []
        add         = lambda label, value: lines.append( help_line(label, value) )

        add( type(real_entry).__name__, real_entry.get_name() or '(anonymous)' )
        add( 'Class', first_line(type(real_entry).__doc__) )
        if getattr(real_entry, 'storage_key', None) and real_entry.storage_key():
            add( 'Stored as', real_entry.storage_key() + '  (by ' + str(real_entry.storage_backend().get_name()) + ')' )
        if getattr(real_entry, 'get_containing_collection', None) and real_entry.get_containing_collection():
            add( 'In collection', real_entry.get_containing_collection().get_name() )
        parents = real_entry.parent_objects()
        add( 'Parents', ', '.join( str(parent.get_name()) for parent in parents ) if parents else '(none)' )

        own_functions = real_entry.own_functions() if isinstance(real_entry, ActionSource) else None
        if inspect.getdoc(own_functions) and inspect.ismodule(own_functions):
            add( 'Description', inspect.getdoc(own_functions) )

        seen_actions = set()
        for source_object, functions in functions_by_source(real_entry):
            lines.append('')
            lines.append( ('Own functions' if source_object is real_entry else f"Functions inherited from {source_object.get_name()}") + ':' )
            for function_name, function_object in functions:
                note = '  [shadowed by an earlier definition]' if function_name in seen_actions else ''
                lines.append( help_line('    '+function_name, first_line(function_object.__doc__) + note) )
                seen_actions.add(function_name)

        lines.append('')
        lines.append( f"Built-in methods of {type(real_entry).__name__}:" )
        for method_name in builtin_method_names(real_entry):
            note = '  [redefined by code above]' if method_name in seen_actions else ''
            lines.append( help_line('    '+method_name, first_line(getattr(type(real_entry), method_name).__doc__) + note) )

        return '\n'.join(lines)


    def _describe_action(self, action_name):
        """Return the text of help() for one action (see help()).
        """
        real_entry  = self.real_entry()
        lines       = []
        add         = lambda label, value: lines.append( help_line(label, value) )

        try:
            action_object = self.find_action(action_name)
        except NameError:
            candidates  = [ name for _, functions in functions_by_source(real_entry) for name, _ in functions ] + builtin_method_names(real_entry)
            suggestions = difflib.get_close_matches(action_name, candidates)
            return f"[{real_entry.get_name()}] has no action '{action_name}'" + ( f". Did you mean: {', '.join(suggestions)}?" if suggestions else '' )

        add( 'Action', action_name )
        if action_name.startswith(PYTHON_SCHEME):
            add( 'Kind', f"Python callable from module {getattr(action_object, '__module__', None) or 'builtins'}" )
        elif inspect.ismethod(action_object):
            defining_class = action_object.__func__.__qualname__.split('.')[0]
            add( 'Kind', f"built-in method of the {defining_class} class, declared in {action_object.__func__.__module__}.py" )
        else:
            defining_source = next( source for source, functions in functions_by_source(real_entry) if any(name==action_name for name, _ in functions) )
            add( 'Kind', f"function in the code of {defining_source.get_name()}" + ( ' (redefining a built-in method)' if action_name in builtin_method_names(real_entry) else '' ) )
            ancestry_path = [ str(source.get_name()) for source in unique_hierarchy(real_entry) ]
            add( 'Ancestry path', ' --> '.join( ancestry_path[:ancestry_path.index(str(defining_source.get_name()))+1] ) )

        try:
            signature = inspect.signature(action_object)
        except ValueError:      # some built-in callables have no inspectable signature
            add( 'Signature', '(not inspectable)' )
        else:
            add( 'Signature', action_name + str(signature) )
            if signature.parameters:
                lines.append( 'Parameters:' )
                for param in signature.parameters.values():
                    lines.append( help_line( '    '+param.name, describe_parameter(param, self) ) )

        add( 'DocString', inspect.cleandoc(action_object.__doc__) if action_object.__doc__ else '(none)' )
        return '\n'.join(lines)


    def case(self, question):
        """Return the outcome given with this call under the name that question prints as (see printed_form()),
            for example "False", "None", "10" or "zip"; if there is none, the default_value given with this call (which may be null).
            If there is neither, the answer was not foreseen, so LookupError is raised rather than a value made up.
            Only what is given with this very call is consulted, never values found further down, so that a case
            fired by another case, or run on an Entry that happens to have such parameters, cannot pick up their outcomes or default.
            An outcome given as an inert expression ("@False": [...]) is computed only if it is chosen; so is "@default_value".
            Several answers can share one outcome by referring to it: "@True": ["get", "1"].

            Consulted only when needed (named parameters, not in the signature):
                <the question's printed form>   the outcome for that answer, plainly or as an inert expression
                default_value                   the outcome when no answer matches, plainly or as an inert expression

            Usage examples:
                axs case 20 --10=ten --20=twenty --30=thirty                             # => twenty
                axs case 40 --10=ten --20=twenty --default_value=other                   # => other
                axs py:os.path.isfile /no/such/file ,question case --True=file --False=absent     # => absent
                axs byname factorial , get factorial                                     # => 120
                axs byname factorial , get factorial --n=10                              # => 3628800
        """
        this_call_data = self.own_data()
        for name in ( printed_form(question), 'default_value' ):
            if name in this_call_data or '@'+name in this_call_data:
                return self[name]       # an inert expression fires only now

        outcome_names = sorted( name.lstrip('@') for name in this_call_data if name.lstrip('@')!='question' )
        raise LookupError(f"[{self.get_name()}] case() has no outcome for '{printed_form(question)}' (outcomes given: {outcome_names}) and no default_value")


    def execute(self, pipeline):
        """Run a pipeline of calls starting from this object (the originator), and return the result of the last call.
            Each step is a list [action_name], [action_name, pos_params] or [action_name, pos_params, named_params];
            pos_params that is not a list is a single positional parameter. Each step is called on the result of the previous one:
            an ActionSource through call(), any other object by calling its method of that name directly.
            Markers between steps change how the next step is made:
                []      (" , , " on the command line)   it is called on the originator again;
                "-"     (" ,- " on the command line)    it is called on the object the previous step was called on,
                                                        discarding that step's result;
                N       (" ,N " on the command line)    the previous result is inserted at position N of its positional parameters,
                                                        and it is called on the originator;
                "name"  (" ,name " on the command line) the previous result becomes its named parameter "name",
                                                        and it is called on the originator.
            A passing marker followed by "-" makes the call on the previous step's object instead ("this is how a result gets stored
            back into the Entry that produced it"); "-" followed by a passing marker passes the previous step's object itself.
            A trailing "-" or [] makes the pipeline return that object. An empty pipeline returns the originator.
            The steps themselves are never changed, so a pipeline can be run again.

            Usage examples:
                axs execute ---='[["byname", "baz"], ["get", "greeting"]]'               # => hello from baz
                axs execute ---='[["noop", "x"], 0, ["noop"]]'                           # => x
                axs noop greek.1 ,0 dig --greek,=alpha,beta                              # => beta
                axs noop hello ,arg noop                                                 # => hello
                axs byname foo , get greeting ,1 ,- plant copy , get copy                # => hello from foo
                axs byname baz , get_name ,- ,0 noop                                     # => axs byname baz
        """
        result = current_object = previous_object = self
        passing = None      # (position or name, value) to pass into the next call

        for step in pipeline:
            if step == []:
                current_object = self
                continue
            if step == '-':
                result = current_object = previous_object
                continue
            if type(step) in (int, str):
                passing = (step, result)
                current_object = self
                continue
            if len(step) > 3:
                raise ValueError(f"[{self.get_name()}] a pipeline step has at most 3 elements (action_name, pos_params, named_params), got {step}")

            action_name     = step[0]
            pos_params      = step[1] if len(step) > 1 else []
            named_params    = step[2] if len(step) > 2 else {}
            if type(pos_params) != list:
                pos_params = [ pos_params ]

            if passing is not None:
                position_or_name, passed_value = passing
                if type(position_or_name) == int:
                    pos_params = pos_params[:position_or_name] + [ passed_value ] + pos_params[position_or_name:]
                else:
                    named_params = { **named_params, position_or_name: passed_value }
                passing = None

            previous_object = current_object
            if isinstance(current_object, ActionSource):
                result = current_object.call(action_name, pos_params, named_params)
            else:
                result = getattr(current_object, action_name)(*pos_params, **named_params)
            current_object = result

        return result


def is_edit_key(key):
    """Return whether a named parameter's key edits a value (contains a dot, or ends in '+') rather than replacing it.
    """
    return '.' in key or key.endswith('+')


def printed_form(value):
    """Return the text the command line prints for a value: an Entry as the command line that loads it (see Entry.pickle_one()),
        anything else as Python's str() does (so True, None, 10 and "zip" print as True, None, 10 and zip).
    """
    return value.pickle_one() if hasattr(value, 'pickle_one') and not isinstance(value, type) else str(value)


HELP_LABEL_WIDTH = 30

def help_line(label, value):
    """Format one line of help(): the label in a column of fixed width, then the value, with any further lines indented under it.
    """
    value_lines = str(value).split('\n')
    return '\n'.join( [ f"{label:{HELP_LABEL_WIDTH}s}: {value_lines[0]}" ] + [ ' ' * (HELP_LABEL_WIDTH+2) + line for line in value_lines[1:] ] )


def first_line(doc_string):
    """Return the first sentence of a DocString's first paragraph (shortened if very long), or '(no DocString)'.
    """
    if not doc_string:
        return '(no DocString)'
    first_paragraph = ' '.join( inspect.cleandoc(doc_string).split('\n\n')[0].split() )
    sentence_end    = first_paragraph.find('. ')
    first_sentence  = first_paragraph[:sentence_end+1] if sentence_end>=0 else first_paragraph
    return textwrap.shorten(first_sentence, 120, placeholder=' ...')


def unique_hierarchy(source_object):
    """Return the objects of hierarchy_generator() in order, each only once.
    """
    seen = []
    for ancestor in source_object.hierarchy_generator():
        if not any(ancestor is known for known in seen):
            seen.append(ancestor)
    return seen


def functions_by_source(source_object):
    """Return (ancestor, [(function_name, function_object), ...]) for every ancestor whose code defines functions, in lookup order.
        Functions merely imported into a code module (defined in another module) are left out.
    """
    groups = []
    for ancestor in unique_hierarchy(source_object):
        functions_ns = ancestor.own_functions() if isinstance(ancestor, ActionSource) else None
        if functions_ns:
            functions = [ (name, function_object) for name, function_object in inspect.getmembers(functions_ns, inspect.isfunction)
                          if not inspect.ismodule(functions_ns) or function_object.__module__==functions_ns.__name__ ]
            if functions:
                groups.append( (ancestor, functions) )
    return groups


def builtin_method_names(source_object):
    """Return the names of the public methods of the object's class, which are its built-in actions.
    """
    return [ name for name, _ in inspect.getmembers(type(source_object), inspect.isfunction) if not name.startswith('_') ]


def describe_parameter(param, context_object):
    """Describe one parameter of an action for help(): its kind, declared type, default, and where its value would come from
        if the action were called on context_object (an override carrying the parameters given to help() itself, if any).
    """
    parts = []
    if param.kind is param.VAR_POSITIONAL:
        parts.append('*args: takes any further positional arguments')
    elif param.kind is param.VAR_KEYWORD:
        parts.append("**kwargs: receives the call's named parameters that match no other parameter")
    elif param.kind is param.KEYWORD_ONLY:
        parts.append('keyword-only')
    if param.annotation is not param.empty:
        parts.append( 'type ' + inspect.formatannotation(param.annotation) )
    if param.default is not param.empty:
        parts.append( 'default ' + repr(param.default) )

    if param.name=='__entry__':
        parts.append("special: receives the call's override")
    elif param.name=='__real_entry__':
        parts.append('special: receives the real entry')
    elif param.kind not in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
        layers = context_object.override_chain_generator() if param.name.startswith('_') else context_object.hierarchy_generator()
        provider = next( (layer for layer in layers if param.name in layer.own_data() or '@'+param.name in layer.own_data()), None )
        if provider is not None and '@'+param.name in provider.own_data():
            source = 'this call' if provider.is_override() else str(provider.get_name())
            parts.append( f"now: computed by @{param.name} = {textwrap.shorten(repr(provider.own_data()['@'+param.name]), 50)} (from {source})" )
        elif provider is not None:
            value = repr( provider.own_data()[param.name] )
            source = 'this call' if provider.is_override() else str(provider.get_name())
            parts.append( f"now: {textwrap.shorten(value, 40)} (from {source})" )
        elif param.default is param.empty:
            parts.append( f"required: give it positionally or as --{param.name}=..." )
    return ', '.join(parts)


if __name__ == '__main__' or 'unittest' in sys.modules:    # run as a script, or collected by unittest/pytest (which have already loaded unittest)

    import unittest
    from types import SimpleNamespace

    class TestActionSource(unittest.TestCase):

        def setUp(self):
            """A parent with functions and data, a child with data only, and a parent that is a plain ParamSource.
            """
            def typed(count: int, label: str = 'item') -> list:
                """Make a list
                    of labels. Each label is the same.

                    A second paragraph that summaries leave out.
                """
                return [label] * count
            self.funcs = SimpleNamespace(
                typed       = typed,
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
                nested_colour = lambda __entry__: __entry__.call('get', ['colour']),
                double      = lambda x: 2 * x,
                counted_double = lambda x, extra=0: ( self.firings.append(x), 2 * x + extra )[1],
                fact        = lambda n, __entry__: 1 if n <= 1 else n * __entry__.call('get', ['factorial'], {'n': n-1}),
                twice_c     = lambda __entry__: ( __entry__['c'], __entry__['c'] ),
                plus_one_real = lambda __real_entry__: __real_entry__['c'] + 1,
                pair        = lambda first, second: (first, second),
                branch_run  = lambda label: ( self.firings.append(label), label )[1],
                sum3        = lambda a, b, c: a + b + c,
                prod2       = lambda a, b=2: a * b,
            )
            self.peer   = ActionSource('peer',  { 'a': 100, 'b': 200 }, own_functions=self.funcs)
            self.base   = ActionSource('base',  { 'a': 1, 'b': 2 }, own_functions=self.funcs)
            self.child  = ActionSource('child', { 'b': 20 }, [self.base])
            self.mixed  = ActionSource('mixed', {}, [ParamSource('plain', { 'a': 1, 'b': 2 })], own_functions=self.funcs)
            self.palette = ActionSource('palette', { 'colour': {'red': 1, 'green': 2}, 'greek': ['alpha'] }, [self.base])
            self.kid    = ActionSource('kid', {}, [self.palette])
            self.calc   = ActionSource('calc', { 'x': 2, '@doubled': ['double', [], {}], '@of_three': ['double', [3]], '@of_four': ['double', [], {'x': 4}] }, [self.base])
            self.calc_kid = ActionSource('calc_kid', { 'x': 5 }, [self.calc])
            self.firings  = []
            self.counter  = ActionSource('counter', { 'x': 2, '@c': ['counted_double'], '@first': ['get', ['c']], '@second': ['get', ['c']], '@pair_of_c': ['pair'] }, [self.base])
            self.counter_kid = ActionSource('counter_kid', {}, [self.counter])
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
        def test_entry_parents_through_call(self):  self.assertEqual( (self.child.call('entry_parents', [], {'q': 1}), self.child.call('parent_objects', [], {'q': 1})[0] is self.child), ([self.base], True) )
        def test_identity_through_call(self):       self.assertEqual( ActionSource('plain', {'b': 1}).call('get_name', [], {'q': 1}), 'plain' )   # an object whose hierarchy does not redefine get_name
        def test_edits_return_real_object(self):    self.assertIs( self.child.call('plant', ['k', 1]), self.child )
        def test_real_entry_parameter(self):        self.assertEqual( self.child.call('real_name', [], {'q': 1}), (False, 'child') )
        def test_promote_through_call(self):
            promoted = self.child.call('promote', [], {'x': 1}); self.assertEqual( (promoted.own_data(), promoted['b'], promoted.is_override()), ({'x': 1}, 20, False) )
        def test_promote_flattens_nested_calls(self):
            self.assertEqual( self.child.call('promote_deeper', [], {'x': 1}).own_data(), {'x': 1, 'y': 2} )

        def test_help_object_groups(self):
            text = ActionSource('shadow', {}, [self.child], own_functions=SimpleNamespace(add3=lambda a: -a)).help(); self.assertEqual( [line in text for line in ('Own functions:', 'Functions inherited from base:', 'Built-in methods of ActionSource:')], [True, True, True] )
        def test_help_object_marks_shadowing(self):
            text = ActionSource('shadow', {}, [self.child], own_functions=SimpleNamespace(add3=lambda a: -a)).help(); self.assertEqual( (text.count('[shadowed by an earlier definition]'), 'redefined by code above' in text), (1, True) )
        def test_help_summary_is_first_sentence(self): self.assertIn( ': Make a list of labels.\n', self.child.help() )
        def test_help_action_kind_and_path(self):
            text = self.child.help('add3'); self.assertEqual( ('function in the code of base' in text, 'child --> base' in text), (True, True) )
        def test_help_parameter_sources(self):
            text = self.child.call('help', ['add3'], {'c': 5}); self.assertEqual( [s in text for s in ('now: 1 (from base)', 'now: 20 (from child)', 'default 0, now: 5 (from this call)')], [True, True, True] )
        def test_help_declared_types(self):
            text = self.child.help('typed'); self.assertEqual( [s in text for s in ('typed(count: int, label: str = ', ') -> list', 'type int, required', "type str, default 'item'")], [True, True, True, True] )
        def test_help_method_kind(self):            self.assertIn( 'built-in method of the ParamSource class, declared in param_source.py', self.child.help('get') )
        def test_help_special_parameters(self):     self.assertIn( "special: receives the call's override", self.child.help('peek') )
        def test_help_suggests_names(self):         self.assertEqual( self.child.help('ad3'), "[child] has no action 'ad3'. Did you mean: add3?" )

        def test_edit_at_path(self):
            self.assertEqual( (self.palette.call('get', ['colour'], {'colour.green': 20}), self.palette['colour']), ({'red': 1, 'green': 20}, {'red': 1, 'green': 2}) )
        def test_edit_by_augmenting(self):
            self.assertEqual( (self.palette.call('get', ['greek'], {'greek+': 'beta'}), self.palette['greek']), (['alpha', 'beta'], ['alpha']) )
        def test_edit_inherited_value(self):
            self.assertEqual( (self.kid.call('get', ['colour'], {'colour.red': 9}), self.palette['colour'], self.kid.own_data()), ({'red': 9, 'green': 2}, {'red': 1, 'green': 2}, {}) )
        def test_edit_creates_missing_levels(self): self.assertEqual( self.palette.call('get', ['fresh'], {'fresh.deep': 1}), {'deep': 1} )
        def test_edits_follow_plain_params(self):   self.assertEqual( self.palette.call('get', ['colour'], {'colour.green': 4, 'colour': {'blue': 3}}), {'blue': 3, 'green': 4} )
        def test_edits_reach_nested_calls(self):    self.assertEqual( self.palette.call('nested_colour', [], {'colour.green': 7}), {'red': 1, 'green': 7} )
        def test_edits_reach_function_arguments(self): self.assertEqual( self.child.call('add3', [], {'a+': 10}), 31 )     # a: inherited 1, augmented by 10
        def test_edits_never_reach_kwargs(self):    self.assertEqual( self.child.call('with_kwargs', [], {'a': 7, 'x.y': 1, 'z+': 2, 'w': 3}), (7, {'w': 3}) )
        def test_edit_keys(self):                   self.assertEqual( [is_edit_key(k) for k in ('plain', 'a.b', 'greek+', 'a.b+')], [False, True, True, True] )

        def test_execute_passes_by_position(self):  self.assertEqual( self.start.execute([ ['noop', 100], 0, ['add3'] ]), 120 )      # a=100, b=20 from child
        def test_execute_passes_into_the_middle(self): self.assertEqual( self.start.execute([ ['noop', 5], 1, ['add3', [100]] ]), 105 )
        def test_execute_passes_by_name(self):      self.assertEqual( self.start.execute([ ['noop', 7], 'c', ['add3'] ]), 28 )
        def test_execute_passing_calls_originator(self): self.assertIs( self.start.execute([ ['get', 'peer'], 0, ['noop'] ]), self.peer )
        def test_execute_pass_then_previous_object(self):
            self.assertIs( self.start.execute([ ['get', 'peer'], ['get', 'a'], 1, '-', ['plant', ['copy']] ]), self.peer ); self.assertEqual( self.peer['copy'], 100 )
        def test_execute_previous_object_then_pass(self): self.assertIs( self.start.execute([ ['get', 'peer'], ['get', 'a'], '-', 0, ['noop'] ]), self.peer )
        def test_execute_passes_only_once(self):    self.assertEqual( self.start.execute([ ['noop', 7], 'c', ['add3'], [], ['add3'] ]), 21 )   # the second add3 gets no c
        def test_execute_leaves_steps_unchanged(self):
            pipeline = [ ['noop', 7], 'c', ['add3', [], {'b': 1}], [], ['noop', 2], 0, ['add3', [5]] ]; self.start.execute(pipeline); self.assertEqual( pipeline, [ ['noop', 7], 'c', ['add3', [], {'b': 1}], [], ['noop', 2], 0, ['add3', [5]] ] )

        def test_inert_fires(self):                 self.assertEqual( self.calc['doubled'], 4 )
        def test_inert_fires_on_asking_object(self): self.assertEqual( self.calc_kid['doubled'], 10 )            # the expression is calc's, x is calc_kid's
        def test_inert_plain_value_above_wins(self): self.assertEqual( self.calc.call('get', ['doubled'], {'doubled': 99}), 99 )
        def test_inert_context_reaches_it(self):    self.assertEqual( self.calc.call('get', ['doubled'], {'x': 100}), 200 )
        def test_inert_positionals_bind(self):      self.assertEqual( self.calc.call('get', ['of_three'], {'x': 100}), 6 )
        def test_inert_named_bind(self):            self.assertEqual( self.calc.call('get', ['of_four'], {'x': 100}), 8 )
        def test_inert_raw_expression(self):        self.assertEqual( self.calc['@of_three'], ['double', [3]] )
        def test_inert_both_forms_rejected(self):   self.assertRaises( ValueError, ActionSource(own_data={'x': 1, '@x': ['noop', 1]}).__getitem__, 'x' )
        def test_inert_malformed_rejected(self):    self.assertRaises( ValueError, ActionSource(own_data={'@x': 'noop'}).__getitem__, 'x' )
        def test_inert_cycle_detected(self):        self.assertRaises( ValueError, ActionSource(own_data={'@loop': ['get', ['loop']]}).__getitem__, 'loop' )
        def test_inert_needs_action_source(self):   self.assertRaises( TypeError, ParamSource(own_data={'@y': ['noop', 1]}).__getitem__, 'y' )
        def test_inert_set_by_call(self):           self.assertEqual( self.calc.call('get', ['tripled'], {'@tripled': ['double', [], {'x': 1.5}]}), 3.0 )
        def test_inert_edited_by_call(self):
            self.assertEqual( (self.calc.call('get', ['doubled'], {'@doubled.named_params.x': 7}), self.calc['@doubled']), (14, ['double', [], {}]) )
        def test_inert_part_aliases(self):          self.assertEqual( [split_key_path('@e.' + part + '.k') for part in ('action_name', 'pos_params', 'named_params')], [['@e', '0', 'k'], ['@e', '1', 'k'], ['@e', '2', 'k']] )
        def test_inert_edit_one_element_expression(self):
            self.assertEqual( ActionSource('short', {'@e': ['double']}, [self.base]).call('get', ['e'], {'@e.named_params.x': 5}), 10 )
        def test_inert_none_slots_are_empty(self):  self.assertEqual( ActionSource('short', {'@e': ['double', None, {'x': 3}]}, [self.base])['e'], 6 )
        def test_inert_inspect_edited_unfired(self):
            self.assertEqual( ActionSource('short', {'@e': ['no_such_action']}).call('dig', ['@e.named_params'], {'@e.named_params.x': 5}), {'x': 5} )
        def test_help_shows_computed_parameter(self): self.assertIn( "now: computed by @x = ['double', [], {}] (from this call)", self.calc.call('help', ['double'], {'@x': ['double', [], {}]}) )

        def test_cache_computes_once(self):         self.assertEqual( ([self.counter['c'], self.counter['c']], self.firings), ([4, 4], [2]) )
        def test_cache_invalidated_by_own_edit(self):
            self.counter['c']; self.counter['x'] = 10; self.assertEqual( (self.counter['c'], self.firings), (20, [2, 10]) )
        def test_cache_invalidated_by_parent_edit(self):
            self.counter_kid['c']; self.counter.plant('x', 7); self.assertEqual( (self.counter_kid['c'], self.firings), (14, [2, 7]) )
        def test_cache_invalidated_by_shadowing(self):
            self.counter_kid['c']; self.counter_kid['x'] = 3; self.assertEqual( (self.counter_kid['c'], self.counter['c'], self.firings), (6, 4, [2, 3, 2]) )
        def test_cache_invalidated_by_missing_appearing(self):
            self.counter_kid['c']; self.counter_kid['extra'] = 1; self.assertEqual( (self.counter_kid['c'], self.firings), (5, [2, 2]) )   # extra appears outside the holder of @c
        def test_cache_invalidated_by_new_expression_above(self):
            self.counter_kid['c']; self.counter_kid['@c'] = ['double', [], {'x': 50}]; self.assertEqual( (self.counter_kid['c'], self.firings), (100, [2]) )
        def test_cache_invalidated_by_expression_edit(self):
            self.counter['c']; self.counter.plant('@c.named_params.x', 9); self.assertEqual( (self.counter['c'], self.firings), (18, [2, 9]) )
        def test_cache_per_asking_object(self):     self.assertEqual( (self.counter['c'], self.counter_kid['c'], self.counter['c'], self.firings), (4, 4, 4, [2, 2]) )
        def test_cache_within_one_call(self):       self.assertEqual( (self.counter.call('twice_c', [], {'x': 6}), self.firings), ((12, 12), [6]) )
        def test_cache_separate_calls(self):        self.assertEqual( (self.counter.call('get', ['c'], {'x': 6}), self.counter.call('get', ['c'], {'x': 7}), self.firings), (12, 14, [6, 7]) )
        def test_cache_reuse_passes_dependencies_on(self):    # c is reused while computing e, and c depends on x held by another object
            x_source = ActionSource('x_source', {'x': 2}, [self.base]); kid = ActionSource('kid', {'@e': ['plus_one_real']}, [ActionSource('c_holder', {'@c': ['counted_double']}, [x_source])]); kid['c']; kid['e']; x_source['x'] = 10; self.assertEqual( (kid['e'], self.firings), (21, [2, 10]) )
        def test_recursion_with_new_parameters(self): self.assertEqual( ActionSource('fact', {'n': 5, '@factorial': ['fact']}, [self.base])['factorial'], 120 )

        def test_cache_shared_through_empty_overrides(self): self.assertEqual( (self.counter.call('get', ['pair_of_c'], {'x': 6}), self.firings), ((12, 12), [6]) )   # two expressions need c
        def test_cache_owner(self):                 self.assertEqual( (ActionSource(None, {}, [ActionSource(None, {'q': 1}, [self.counter], is_override=True)], is_override=True).cache_owner().own_data(), ActionSource(None, {}, [self.counter], is_override=True).cache_owner() is self.counter), ({'q': 1}, True) )
        def test_substitute_computes_once(self):    self.assertEqual( (self.counter.call('substitute', ['#{c}# #{c}# #{c}# #{c}#'], {'x': 6}), self.firings), ('12 12 12 12', [6]) )

        def test_py_builtin_and_dotted(self):       self.assertEqual( [self.child.call('py:len', ['abcde']), self.child.call('py:os.path.join', ['a', 'b']), self.child.call('py:str.upper', ['hi'])], [5, 'a/b', 'HI'] )
        def test_py_fills_from_context(self):       self.assertEqual( self.child.call('py:operator.mul', [], {'@a': ['get', ['b']], 'b': 7}), 49 )   # b is 7 here, a computed from it
        def test_py_fills_from_hierarchy(self):     self.assertEqual( self.child.call('py:operator.mul', [], {'a': 3}), 60 )                         # b=20 inherited from child
        def test_py_without_signature(self):        self.assertEqual( self.child.call('py:max', [3, 7, 5]), 7 )
        def test_py_unknown(self):                  self.assertEqual( (self.child.can('py:len'), self.child.can('py:no_such_module.nothing'), self.child.can('py:os.sep')), (True, False, False) )
        def test_py_in_pipeline(self):              self.assertEqual( self.start.execute([ ['noop', [['a', 'b', 'c']]], 0, ['py:len'] ]), 3 )
        def test_py_in_inert_expression(self):      self.assertEqual( ActionSource('calc_py', {'@total': ['py:sum', [[1, 2, 3]]]})['total'], 6 )
        def test_help_python_callable(self):        self.assertEqual( [s in self.child.help('py:operator.mul') for s in ('Python callable from module _operator', 'py:operator.mul(a, b, /)', 'now: 20 (from child)')], [True, True, True] )
        def test_prep_without_signature(self):      self.assertEqual( prep(max, [3, 9], {}, self.child), (max, [3, 9], {}) )
        def test_inert_keys_never_reach_kwargs(self): self.assertEqual( self.child.call('with_kwargs', [], {'a': 7, '@k': ['noop', [1]], 'w': 3}), (7, {'w': 3}) )
        def test_inert_in_named_params_chain(self): self.assertEqual( ActionSource('chain', {'@r': ['sum3', [], {'@b': ['prod2', [], {'@a': ['get', ['d']], 'b': 5}]}]}, [self.base]).call('get', ['r'], {'a': 1, 'c': 1, 'd': 10}), 52 )

        def test_case_chooses(self):                self.assertEqual( self.child.call('case', [20], {'10': 'ten', '20': 'twenty'}), 'twenty' )
        def test_case_printed_forms(self):          self.assertEqual( [ self.child.call('case', [q], {'False': 'f', 'None': 'n', '10': 't', 'zip': 'z'}) for q in (False, None, 10, 'zip') ], ['f', 'n', 't', 'z'] )
        def test_case_default(self):                self.assertEqual( (self.child.call('case', [3], {'1': 'one', 'default_value': 'other'}), self.child.call('case', [3], {'1': 'one', 'default_value': None})), ('other', None) )
        def test_case_unforeseen_answer(self):      self.assertRaises( LookupError, self.child.call, 'case', [3], {'1': 'one'} )
        def test_case_error_not_masked_by_get(self): self.assertRaises( LookupError, ActionSource('wrapper', {'@x': ['case', [3], {'1': 'one'}]}, [self.child]).get, 'x', 'masked' )
        def test_case_only_this_call(self):         self.assertRaises( LookupError, ActionSource('leaky', {'b': 'from entry', 'default_value': 'from entry'}, [self.child]).call, 'case', ['b'] )
        def test_case_nested_no_leak(self):         self.assertRaises( LookupError, self.child.call, 'case', ['x'], {'default_value': 'outer', '@x': ['case', ['nothing']]} )
        def test_case_lazy_outcomes(self):
            self.assertEqual( (self.child.call('case', [2], {'@1': ['branch_run', ['one']], '@2': ['branch_run', ['two']], '@default_value': ['branch_run', ['default']]}), self.firings), ('two', ['two']) )
        def test_case_lazy_default(self):           self.assertEqual( (self.child.call('case', [9], {'@1': ['branch_run', ['one']], '@default_value': ['branch_run', ['default']]}), self.firings), ('default', ['default']) )
        def test_case_shared_outcome(self):         self.assertEqual( [ self.child.call('case', [q], {'1': 'yes', '@True': ['get', ['1']]}) for q in (1, True) ], ['yes', 'yes'] )
        def test_case_question_by_name(self):       self.assertEqual( self.child.call('case', [], {'@question': ['get', ['b']], '20': 'b is twenty'}), 'b is twenty' )
        def test_printed_form(self):                self.assertEqual( [printed_form(v) for v in (True, None, 10, 'zip', [1, 'a'])], ['True', 'None', '10', 'zip', "[1, 'a']"] )

    if __name__ == '__main__':
        unittest.main(verbosity=2)

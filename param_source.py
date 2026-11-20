#!/usr/bin/env python3

"""axs04: a minimal, non-persistent container of parameters.

Running this file as a script runs the tests of its Python API.
"""

__version__ = "0.4.6"

import sys
from copy import deepcopy


def split_key_path(key_path):
    """Turn a key path given as a dot-separated string or as a list into a new list of keys.
    """
    return key_path.split('.') if type(key_path)==str else list(key_path)


def index_into(struct_ptr, key_syllable, vivify=False):
    """Return the index under which key_syllable addresses struct_ptr: an integer for lists, a string otherwise
        (dictionary keys are strings, in line with parameter names). With vivify set, a list that is too short
        for the index is padded with None.
    """
    if type(struct_ptr)!=list:
        return str(key_syllable)
    index = int(key_syllable)
    if vivify and index >= len(struct_ptr):
        struct_ptr.extend( [None] * (index - len(struct_ptr) + 1) )
    return index


def augment_value(orig_value, diff):
    """Return a new value combining orig_value with diff, leaving both unchanged:
        a dictionary is topped up with another dictionary, a list gets a non-list element appended
        or another list concatenated, strings are concatenated and numbers are added.
        A missing original (None) is simply replaced by diff.
    """
    if orig_value is None:
        return diff
    elif type(orig_value)==dict and type(diff)==dict:
        return { **orig_value, **diff }
    elif type(orig_value)==list:
        return orig_value + (diff if type(diff)==list else [ diff ])
    try:
        return orig_value + diff
    except TypeError:
        raise TypeError(f"Cannot augment a {type(orig_value).__name__} with a {type(diff).__name__}") from None


class ParamSource:
    """An object of ParamSource class is a non-persistent container of parameters with an ordered list of parent objects.

        A parameter missing from an object's own data is looked up in its ancestors (see hierarchy_generator()),
        except for parameters whose names start with '_', which are never inherited.
        Writing (__setitem__(), plant(), pluck()) always targets the object's own data at the top level,
        so a value set on a child shadows the inherited one without changing the parent.

        Explicit edits of an inherited parameter (plant() or pluck() below its top level, augmenting it with '+',
        or dig() with vivify) first store a deep copy of the whole parameter in own data (see own_value()),
        so they never change the parent.

        An override (created with is_override=True) is a transient layer on top of exactly one parent, used to hold
        the parameters of a call. Its data is fixed when it is created: all edits made through it (__setitem__(), plant(),
        pluck(), own_value(), dig() with vivify) go to the nearest non-override object underneath (see base_object()),
        although within the override that object's edited parameter stays shadowed by the override's own value.
        Parameters whose names start with '_' are looked up through overrides, down to and including that object.

        BEWARE: values are returned by reference, and edits made directly on them are not tracked. Appending to
        or otherwise changing a value obtained from __getitem__(), get() or dig() changes it wherever it lives:
        if it was inherited, the change is seen by the parent and all its other descendants. To edit such a value
        for this object only, take a private copy first:
            obj.own_value('greek').append('beta')

        There are no expressions and no persistence yet.
    """

    def __init__(self, name=None, own_data=None, parent_objects=None, is_override=False):
        """Create a container with an optional name, an optional dictionary of own data and an optional list of parent objects.
            An object without a name is anonymous; an object without data starts empty; an object without parents has none.
            With is_override set, the object becomes an override, which must have exactly one parent.
        """
        self.name = name
        self.is_override_flag = False
        self.set_own_data( own_data )
        parent_objects = list(parent_objects or [])
        for parent_object in parent_objects:
            if not isinstance(parent_object, ParamSource):
                raise TypeError(f"[{name}] parent objects should be ParamSource objects, got {type(parent_object).__name__}")
        if is_override and len(parent_objects)!=1:
            raise ValueError(f"[{name}] an override must have exactly one parent, got {len(parent_objects)}")
        self.parent_objects_cache = parent_objects
        self.is_override_flag = bool(is_override)


    def get_name(self):
        """Read-only access to the name. Anonymous objects return None.
        """
        return self.name


    def set_own_data(self, own_data=None):
        """Replace this object's own data with the given dictionary, or with an empty one if None is given.
            The dictionary is held by reference, not copied. The data of an override cannot be replaced after its creation.
            Returns the object itself, so that calls can be chained.
        """
        if self.is_override():
            raise TypeError(f"[{self.get_name()}] the data of an override cannot be replaced after its creation")
        if own_data is None:
            own_data = {}
        elif type(own_data)!=dict:
            raise TypeError(f"[{self.get_name()}] own_data should be a dictionary, got {type(own_data).__name__}")

        self.own_data_cache = own_data
        return self


    def own_data(self):
        """Return the dictionary of this object's own data, by reference.
        """
        return self.own_data_cache


    def parent_objects(self):
        """Return the list of this object's parent objects, in order of priority.
        """
        return self.parent_objects_cache


    def is_override(self):
        """Return whether this object is an override (a transient layer holding a call's parameters).
        """
        return self.is_override_flag


    def override_chain_generator(self):
        """Yield this object and, while the yielded object is an override, the one parent underneath it,
            ending with the first object that is not an override (see base_object()).
        """
        source_object = self
        yield source_object
        while source_object.is_override():
            source_object = source_object.parent_objects()[0]
            yield source_object


    def base_object(self):
        """Return the nearest object that is not an override: this object itself, unless it is an override.
        """
        for source_object in self.override_chain_generator():
            pass
        return source_object


    def hierarchy_generator(self):
        """Yield this object followed by its ancestors, in depth-first, left-to-right order.
            An ancestor reachable through several parents is visited more than once, which is harmless
            for lookups, as they stop at the first object that has the parameter.
        """
        # DESIGN DECISION: depth-first order, as in axs 0.2. It differs from C3 (Python's own method resolution order)
        #   only for diamonds: with D(B, C), B(A) and C(A), depth-first visits A before C, so a parameter defined
        #   in both A and C is taken from A. C3 would give D, B, C, A; it is short to implement, but refuses some
        #   hierarchies and needs a cached order (which brings invalidation problems once parents can change).
        #   This order will also apply to methods once Entries have code. test_depth_first_order_in_diamond pins it.
        yield self
        for parent_object in self.parent_objects():
            yield from parent_object.hierarchy_generator()


    def own_value(self, param_name):
        """Make sure a parameter lives in own data before it is edited in place: if it is only inherited,
            store a deep copy of the inherited value in own data.
            Returns the parameter's value from own data, by reference and safe to edit in place,
            or None if the parameter is missing everywhere. On an override, this is done in base_object() instead.
        """
        if self.is_override():
            return self.base_object().own_value(param_name)
        param_name = str(param_name)
        own_data = self.own_data()
        if param_name not in own_data:
            try:
                own_data[param_name] = deepcopy( self.__getitem__(param_name) )
            except KeyError:
                return None
        return own_data[param_name]


    def __getitem__(self, param_name):
        """Return the value of a parameter, by reference, from the first object in the hierarchy that has it.
            Parameters whose names start with '_' are only looked up in this object's own data, and through overrides
            (see override_chain_generator()). Parameter names are converted to strings. Raises KeyError if the parameter is missing.
        """
        param_name = str(param_name)
        for source_object in ( self.override_chain_generator() if param_name.startswith('_') else self.hierarchy_generator() ):
            source_data = source_object.own_data()
            if param_name in source_data:
                return source_data[param_name]

        raise KeyError(param_name)


    def get(self, param_name, default_value=None):
        """A safe wrapper around __getitem__(): returns default_value if the parameter is missing.
        """
        try:
            return self.__getitem__(param_name)
        except KeyError:
            return default_value


    def __setitem__(self, param_name, param_value):
        """Set a parameter's value in this object's own data, shadowing any inherited value (on an override, in base_object() instead).
            Parameter names are converted to strings.
        """
        self.base_object().own_data()[ str(param_name) ] = param_value


    def dig(self, key_path, safe=False, safe_value=None, vivify=False):
        """Traverse a path of keys into a parameter's internal structure and return what is found there, by reference.
            The path is a dot-separated string or a list of keys; its first key names the parameter, which may be inherited.
            Numeric keys index into lists.
            If the path cannot be traversed, raises the underlying error, or returns safe_value when safe is set.
            With vivify set, the path is created as it is traversed: missing dictionary levels and None placeholders
            become empty dictionaries, and lists that are too short are padded with None; an inherited parameter
            is first copied into own data (see own_value()). On an override, a vivifying dig() is done in base_object() instead.
        """
        if vivify and self.is_override():
            return self.base_object().dig(key_path, safe=safe, safe_value=safe_value, vivify=True)
        key_path = split_key_path(key_path)
        try:
            if vivify:
                if self.own_value( key_path[0] ) is None:     # a vivifying walk is an edit, so it must only ever reach own data
                    self.__setitem__( key_path[0], {} )
            struct_ptr = self.__getitem__( key_path[0] )
            for key_syllable in key_path[1:]:
                index = index_into(struct_ptr, key_syllable, vivify)
                if vivify and ((type(struct_ptr)==dict and index not in struct_ptr) or struct_ptr[index] is None):
                    struct_ptr[index] = {}
                struct_ptr = struct_ptr[index]
            return struct_ptr
        except (KeyError, IndexError, ValueError, TypeError):
            if safe:
                return safe_value
            raise


    def plant(self, *keypath_value_pairs):
        """Assign values at the ends of key paths in this object's own data, creating missing structure on the way (see dig() with vivify).
            Takes alternating key paths and values. A path whose last key ends in '+' augments the existing value
            instead of replacing it (see augment_value()); a missing or None value is simply assigned.
            Editing below the top level of an inherited parameter, or augmenting it, first copies it into own data
            (see own_value()), so the parent is never changed. On an override, the planting is done in base_object() instead.
            Returns the object itself, so that calls can be chained.
        """
        if self.is_override():
            self.base_object().plant(*keypath_value_pairs)
            return self
        if len(keypath_value_pairs) % 2:
            raise ValueError(f"[{self.get_name()}] plant() expects alternating key paths and values, got an odd number of arguments")

        for key_path, value in zip(keypath_value_pairs[0::2], keypath_value_pairs[1::2]):
            key_path = split_key_path(key_path)
            augment_mode = type(key_path[-1])==str and key_path[-1].endswith('+')
            if augment_mode:
                key_path[-1] = key_path[-1][:-1]

            if augment_mode and len(key_path)==1:
                self.own_value( key_path[0] )       # for longer paths dig(vivify=True) does this
            struct_parent_ptr = self.dig(key_path[:-1], vivify=True) if len(key_path)>1 else self.own_data()
            index = index_into(struct_parent_ptr, key_path[-1], vivify=True)
            if augment_mode:
                value = augment_value( struct_parent_ptr.get(index) if type(struct_parent_ptr)==dict else struct_parent_ptr[index], value )
            struct_parent_ptr[index] = value

        return self


    def pluck(self, *key_paths):
        """Remove the values at the ends of the given key paths from this object's own data.
            Plucking a top-level parameter lets an inherited value of the same name show through again;
            plucking an inherited top-level parameter raises KeyError. Below the top level, an inherited
            parameter is first copied into own data (see own_value()), so the parent is never changed.
            Raises the underlying error if a path does not exist; nothing is created on the way.
            On an override, the plucking is done in base_object() instead. Returns the object itself, so that calls can be chained.
        """
        if self.is_override():
            self.base_object().pluck(*key_paths)
            return self
        for key_path in key_paths:
            key_path = split_key_path(key_path)
            if len(key_path)>1:
                self.dig(key_path)                      # raises if the path does not exist, before anything is copied
                self.own_value( key_path[0] )
            struct_parent_ptr = self.dig(key_path[:-1]) if len(key_path)>1 else self.own_data()
            del struct_parent_ptr[ index_into(struct_parent_ptr, key_path[-1]) ]

        return self


if __name__ == '__main__' or 'unittest' in sys.modules:    # run as a script, or collected by unittest/pytest (which have already loaded unittest)

    import unittest

    class TestParamSource(unittest.TestCase):

        def setUp(self):
            """One object with deliberately awkward data (falsy values, a stored None, a numeric-string key, a mutable list, a nested dict), edited in several ways.
            """
            self.data = { 'zero': 0, 'none': None, '7': 'seven', 'greek': ['alpha'], 'colour': {'red': 128} }
            self.ps, self.blank = ParamSource(name='alpha', own_data=self.data), ParamSource()
            self.data['late'] = 2                   # the dictionary is held by reference...
            self.ps['greek'].append('beta')         # ...and values are returned by reference
            self.ps[8] = 'eight'                    # numeric names are stringified on the way in
            self.ps['added'] = 1
            self.ps['added'] = 2                    # overwriting
            ParamSource()['leak'] = 1               # must not leak into other default-constructed objects
            self.ps.plant('colour.green', 255, 'deep.er.est', 1, 'greek.3', 'delta', 'greek.5.x', 'vivified', 'greek.2.y', 'filled')
            # A diamond: child(left, right), left(base), right(base)
            self.base   = ParamSource('base',  { 'x': 'base', 'w': 'base', 'greek': ['alpha'], 'colour': {'red': 0}, 'nested': {'inner': {'a': 1}}, '_private': 'base' })
            self.left   = ParamSource('left',  { 'x': 'left' }, [self.base])
            self.right  = ParamSource('right', { 'x': 'right', 'y': 'right', 'w': 'right' }, [self.base])
            self.child  = ParamSource('child', { 'z': 'child' }, [self.left, self.right])
            # Two overrides stacked on top of child
            self.over       = ParamSource(own_data={ 'x': 'over', '_flag': 'over' }, parent_objects=[self.child], is_override=True)
            self.over_over  = ParamSource(own_data={ 'y': 'over2' }, parent_objects=[self.over], is_override=True)

        def test_name(self):                        self.assertEqual( self.ps.get_name(), 'alpha' )
        def test_anonymous(self):                   self.assertIsNone( self.blank.get_name() )
        def test_empty_and_unshared_default(self):  self.assertEqual( self.blank.own_data(), {} )
        def test_numeric_name_read(self):           self.assertEqual( self.ps[7], 'seven' )
        def test_falsy_value_is_not_default(self):  self.assertEqual( self.ps.get('zero', 42), 0 )
        def test_stored_none_is_not_default(self):  self.assertIsNone( self.ps.get('none', 42) )
        def test_missing_gives_default(self):       self.assertEqual( (self.ps.get('missing'), self.ps.get('missing', 42)), (None, 42) )
        def test_missing_raises(self):              self.assertRaises( KeyError, self.ps.__getitem__, 'missing' )
        def test_non_dict_rejected_at_init(self):   self.assertRaises( TypeError, ParamSource, own_data=[1] )
        def test_set_own_data_resets(self):         self.assertEqual( self.ps.set_own_data().own_data(), {} )
        def test_version_format(self):              self.assertRegex( __version__, r'^\d+\.\d+\.\d+$' )
        def test_all_edits_landed(self):
            self.assertEqual( self.ps.own_data(), { 'zero': 0, 'none': None, '7': 'seven', 'late': 2, '8': 'eight', 'added': 2, 'greek': ['alpha', 'beta', {'y': 'filled'}, 'delta', None, {'x': 'vivified'}], 'colour': {'red': 128, 'green': 255}, 'deep': {'er': {'est': 1}} } )
        def test_rejection_keeps_data(self):
            self.assertRaises( TypeError, self.ps.set_own_data, 'x' ); self.assertEqual( self.ps['7'], 'seven' )
        def test_set_own_data_replaces_and_chains(self):
            self.assertIs( self.blank.set_own_data({'only': 1}), self.blank ); self.assertEqual( self.blank.own_data(), {'only': 1} )

        def test_dig(self):                         self.assertEqual( (self.ps.dig('colour.green'), self.ps.dig('greek.5.x'), self.ps.dig(['greek', 2, 'y'])), (255, 'vivified', 'filled') )
        def test_dig_safe(self):                    self.assertEqual( (self.ps.dig('greek.9', safe=True), self.ps.dig('colour.blue', safe=True, safe_value=0)), (None, 0) )
        def test_dig_vivify(self):                  self.assertEqual( (self.ps.dig('fresh.path', vivify=True), self.ps['fresh']), ({}, {'path': {}}) )
        def test_dig_by_reference(self):            self.assertIs( self.ps.dig('colour'), self.ps['colour'] )
        def test_plant_list_paths(self):
            self.ps.plant(['greek', 3], 'DELTA', ['colour', 7], 'seven'); self.assertEqual( (self.ps.dig('greek.3'), self.ps.dig('colour.7')), ('DELTA', 'seven') )
        def test_plant_chains(self):                self.assertIs( self.ps.plant('flat', 0), self.ps )
        def test_plant_into_scalar_fails(self):     self.assertRaises( TypeError, self.ps.plant, 'colour.red.deeper', 1 )
        def test_plant_odd_arguments(self):         self.assertRaises( ValueError, self.ps.plant, 'colour.blue' )
        def test_pluck_missing_raises(self):        self.assertRaises( KeyError, self.ps.pluck, 'colour.blue' )
        def test_dig_failures(self):
            for bad_path in ('missing', 'colour.blue', 'greek.9', 'greek.one', 'colour.red.deeper'): self.assertRaises( (KeyError, IndexError, ValueError, TypeError), self.ps.dig, bad_path )
        def test_pluck(self):
            self.assertIs( self.ps.pluck('colour.red', 'greek.0', 'zero'), self.ps ); self.assertEqual( (self.ps['colour'], self.ps.dig('greek.0'), self.ps.get('zero')), ({'green': 255}, 'beta', None) )
        def test_failed_pluck_creates_nothing(self):
            self.assertRaises( KeyError, self.ps.pluck, 'nowhere.deep' ); self.assertNotIn( 'nowhere', self.ps.own_data() )
        def test_plus_is_literal_elsewhere(self):
            self.ps.plant('odd+.key', 1); self.assertEqual( (self.ps.dig('odd+.key'), self.ps.pluck('odd+').get('odd+')), (1, None) )
        def test_augment_scalars_and_dicts(self):
            self.ps.plant('deep.er+', {'more': 2}, 'zero+', 5, '7+', 'teen', 'greek.1+', '!'); self.assertEqual( [self.ps.dig(p) for p in ('deep.er', 'zero', '7', 'greek.1')], [{'est': 1, 'more': 2}, 5, 'seventeen', 'beta!'] )
        def test_augment_lists(self):
            self.ps.plant('greek+', 'omega', 'greek+', ['psi', 'chi']); self.assertEqual( self.ps['greek'][-3:], ['omega', 'psi', 'chi'] )
        def test_augment_missing_or_none_assigns(self):
            self.ps.plant('fresh.list+', [1], 'none+', 'x', 'greek.4+', 'four'); self.assertEqual( (self.ps.dig('fresh.list'), self.ps['none'], self.ps.dig('greek.4')), ([1], 'x', 'four') )
        def test_augment_type_mismatch(self):
            for path, value in (('colour+', 'not a dict'), ('7+', 1), ('zero+', 'one')): self.assertRaises( TypeError, self.ps.plant, path, value )
        def test_augment_makes_a_new_value(self):
            colour_before = self.ps['colour']; self.ps.plant('colour+', {'blue': 0}); self.assertEqual( colour_before, {'red': 128, 'green': 255} )

        def test_inherited_lookup(self):            self.assertEqual( [self.child[p] for p in ('z', 'x', 'y', 'greek')], ['child', 'left', 'right', ['alpha']] )
        def test_depth_first_order_in_diamond(self): self.assertEqual( self.child['w'], 'base' )      # C3 would give 'right': see hierarchy_generator()
        def test_hierarchy_order(self):             self.assertEqual( [o.get_name() for o in self.child.hierarchy_generator()], ['child', 'left', 'base', 'right', 'base'] )
        def test_underscore_not_inherited(self):    self.assertEqual( (self.base['_private'], self.child.get('_private')), ('base', None) )
        def test_missing_in_hierarchy_raises(self): self.assertRaises( KeyError, self.child.__getitem__, 'missing' )
        def test_parents_must_be_param_sources(self): self.assertRaises( TypeError, ParamSource, 'bad', {}, [{'x': 1}] )
        def test_dig_through_inheritance(self):     self.assertEqual( self.child.dig('colour.red'), 0 )
        def test_setitem_shadows(self):
            self.child['x'] = 'own'; self.assertEqual( (self.child['x'], self.left['x']), ('own', 'left') )
        def test_pluck_reveals_inherited(self):
            self.child['x'] = 'own'; self.child.pluck('x'); self.assertEqual( self.child['x'], 'left' )
        def test_pluck_inherited_raises(self):      self.assertRaises( KeyError, self.child.pluck, 'x' )
        def test_augment_inherited_top_level(self):
            self.child.plant('greek+', 'beta'); self.assertEqual( (self.child['greek'], self.base['greek']), (['alpha', 'beta'], ['alpha']) )
        def test_nested_plant_copies_on_write(self):
            self.child.plant('colour.green', 255, 'colour.red+', 1); self.assertEqual( (self.child['colour'], self.base['colour']), ({'red': 1, 'green': 255}, {'red': 0}) )
        def test_own_value_is_deep(self):
            self.child.plant('nested+', {'b': 2}, 'nested.inner.c', 3); self.assertEqual( self.base['nested'], {'inner': {'a': 1}} )
        def test_nested_pluck_copies_on_write(self):
            self.child.pluck('colour.red'); self.assertEqual( (self.child['colour'], self.base['colour']), ({}, {'red': 0}) )
        def test_failed_nested_pluck_copies_nothing(self):
            self.assertRaises( KeyError, self.child.pluck, 'colour.blue' ); self.assertNotIn( 'colour', self.child.own_data() )
        def test_own_value_missing(self):           self.assertEqual( (self.child.own_value('missing'), 'missing' in self.child.own_data()), (None, False) )
        def test_dig_vivify_copies_on_write(self):
            self.child.dig('colour.shade', vivify=True); self.assertEqual( (self.child['colour'], self.base['colour']), ({'red': 0, 'shade': {}}, {'red': 0}) )
        def test_explicit_own_value(self):      # the snippet from the class DocString
            self.child.own_value('greek').append('beta'); self.assertEqual( (self.child['greek'], self.base['greek']), (['alpha', 'beta'], ['alpha']) )
        def test_returned_reference_edits_parent(self):   # documented hazard, see the class DocString
            self.child['greek'].append('beta'); self.assertEqual( self.base['greek'], ['alpha', 'beta'] )

        def test_override_needs_one_parent(self):
            for parents in ([], [self.left, self.right]): self.assertRaises( ValueError, ParamSource, None, {}, parents, True )
        def test_base_object(self):                 self.assertEqual( [o.base_object().get_name() for o in (self.over_over, self.over, self.child)], ['child', 'child', 'child'] )
        def test_override_lookup(self):             self.assertEqual( [self.over_over[p] for p in ('y', 'x', 'z', 'greek', '_flag')], ['over2', 'over', 'child', ['alpha'], 'over'] )
        def test_underscore_through_overrides(self):
            self.assertEqual( (ParamSource(None, {}, [ParamSource(None, {}, [self.base], True)], True).get('_private'), self.over.get('_private')), ('base', None) )
        def test_override_data_is_fixed(self):      self.assertRaises( TypeError, self.over.set_own_data, {} )
        def test_plant_through_override(self):
            self.assertIs( self.over_over.plant('new', 1, 'colour.green', 2), self.over_over ); self.assertEqual( (self.child['new'], self.child['colour'], self.base['colour']), (1, {'red': 0, 'green': 2}, {'red': 0}) )
        def test_other_edits_through_override(self):
            self.over['k'] = 1; self.over.pluck('z'); self.over.own_value('greek').append('beta'); self.assertEqual( self.child.own_data(), {'k': 1, 'greek': ['alpha', 'beta']} )
        def test_dig_vivify_through_override(self):
            ov = ParamSource(own_data={'colour': {'blue': 9}}, parent_objects=[self.child], is_override=True); ov.dig('colour.shade', vivify=True); self.assertEqual( (ov.own_data(), self.child['colour'], self.base['colour']), ({'colour': {'blue': 9}}, {'red': 0, 'shade': {}}, {'red': 0}) )
        def test_overrides_unchanged_by_edits(self):
            self.over_over.plant('x', 'stored', 'y+', '!'); self.assertEqual( (self.over.own_data(), self.over_over.own_data()), ({'x': 'over', '_flag': 'over'}, {'y': 'over2'}) )
        def test_override_still_shadows_edit(self):
            self.over.plant('x', 'stored'); self.assertEqual( (self.child['x'], self.over['x']), ('stored', 'over') )

    if __name__ == '__main__':
        unittest.main(verbosity=2)

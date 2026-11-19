#!/usr/bin/env python3

"""axs04: a minimal, non-persistent container of parameters.

Running this file as a script runs the tests of its Python API.
"""

__version__ = "0.4.3"

import sys


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
    """An object of ParamSource class is a non-persistent container of parameters.

        At this stage it holds only its own data: there is no inheritance, no overriding,
        no expressions and no persistence yet.
    """

    def __init__(self, name=None, own_data=None):
        """Create a container with an optional name and an optional dictionary of own data.
            An object without a name is anonymous; an object without data starts empty.
        """
        self.name = name
        self.set_own_data( own_data )


    def get_name(self):
        """Read-only access to the name. Anonymous objects return None.
        """
        return self.name


    def set_own_data(self, own_data=None):
        """Replace this object's own data with the given dictionary, or with an empty one if None is given.
            The dictionary is held by reference, not copied.
            Returns the object itself, so that calls can be chained.
        """
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


    def __getitem__(self, param_name):
        """Return the value of a parameter, by reference. Parameter names are converted to strings.
            Raises KeyError if the parameter is missing.
        """
        return self.own_data()[ str(param_name) ]


    def get(self, param_name, default_value=None):
        """A safe wrapper around __getitem__(): returns default_value if the parameter is missing.
        """
        try:
            return self.__getitem__(param_name)
        except KeyError:
            return default_value


    def __setitem__(self, param_name, param_value):
        """Set a parameter's value in this object's own data. Parameter names are converted to strings.
        """
        self.own_data()[ str(param_name) ] = param_value


    def dig(self, key_path, safe=False, safe_value=None, vivify=False):
        """Traverse a path of keys into a parameter's internal structure and return what is found there, by reference.
            The path is a dot-separated string or a list of keys; its first key names the parameter, numeric keys index into lists.
            If the path cannot be traversed, raises the underlying error, or returns safe_value when safe is set.
            With vivify set, the path is created as it is traversed: missing dictionary levels and None placeholders
            become empty dictionaries, and lists that are too short are padded with None.
        """
        key_path = split_key_path(key_path)
        try:
            if vivify and self.get( key_path[0] ) is None:
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
            Returns the object itself, so that calls can be chained.
        """
        if len(keypath_value_pairs) % 2:
            raise ValueError(f"[{self.get_name()}] plant() expects alternating key paths and values, got an odd number of arguments")

        for key_path, value in zip(keypath_value_pairs[0::2], keypath_value_pairs[1::2]):
            key_path = split_key_path(key_path)
            augment_mode = type(key_path[-1])==str and key_path[-1].endswith('+')
            if augment_mode:
                key_path[-1] = key_path[-1][:-1]

            # NB: once parents exist, planting below the top level of an inherited parameter
            #     will first have to copy that parameter into own data (copy-on-write).
            struct_parent_ptr = self.dig(key_path[:-1], vivify=True) if len(key_path)>1 else self.own_data()
            index = index_into(struct_parent_ptr, key_path[-1], vivify=True)
            if augment_mode:
                value = augment_value( struct_parent_ptr.get(index) if type(struct_parent_ptr)==dict else struct_parent_ptr[index], value )
            struct_parent_ptr[index] = value

        return self


    def pluck(self, *key_paths):
        """Remove the values at the ends of the given key paths from this object's own data.
            Raises the underlying error if a path does not exist; nothing is created on the way.
            Returns the object itself, so that calls can be chained.
        """
        for key_path in key_paths:
            key_path = split_key_path(key_path)
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

    if __name__ == '__main__':
        unittest.main(verbosity=2)

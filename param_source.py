#!/usr/bin/env python3

"""axs04: a minimal, non-persistent container of parameters.

Running this file as a script runs the tests of its Python API.
"""

__version__ = "0.4.1"

import sys


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


if __name__ == '__main__' or 'unittest' in sys.modules:    # run as a script, or collected by unittest/pytest (which have already loaded unittest)

    import unittest

    class TestParamSource(unittest.TestCase):

        def setUp(self):
            """One object with deliberately awkward data (falsy values, a stored None, a numeric-string key, a mutable list), edited in several ways.
            """
            self.data = { 'zero': 0, 'none': None, '7': 'seven', 'greek': ['alpha'] }
            self.ps, self.blank = ParamSource(name='alpha', own_data=self.data), ParamSource()
            self.data['late'] = 2                   # the dictionary is held by reference...
            self.ps['greek'].append('beta')         # ...and values are returned by reference
            self.ps[8] = 'eight'                    # numeric names are stringified on the way in
            self.ps['added'] = 1
            self.ps['added'] = 2                    # overwriting
            ParamSource()['leak'] = 1               # must not leak into other default-constructed objects

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
            self.assertEqual( self.ps.own_data(), { 'zero': 0, 'none': None, '7': 'seven', 'greek': ['alpha', 'beta'], 'late': 2, '8': 'eight', 'added': 2 } )
        def test_rejection_keeps_data(self):
            self.assertRaises( TypeError, self.ps.set_own_data, 'x' ); self.assertEqual( self.ps['7'], 'seven' )
        def test_set_own_data_replaces_and_chains(self):
            self.assertIs( self.blank.set_own_data({'only': 1}), self.blank ); self.assertEqual( self.blank.own_data(), {'only': 1} )

    if __name__ == '__main__':
        unittest.main(verbosity=2)

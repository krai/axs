#!/usr/bin/env python3

"""axs04: an ActionSource that can be stored by a storage backend.

Running this file as a script runs the tests of its Python API.
"""

import sys
from types import SimpleNamespace

from action_source import ActionSource
import filesystem_storage_backend


def loaded_entries(storage_backend):
    """Return the dictionary of the Entries a storage backend has loaded or saved, keyed by their canonical storage keys.
        It is kept on the real backend object (never on an override of it), and created when first needed.
    """
    storage_backend = storage_backend.base_object()
    if not hasattr(storage_backend, 'loaded_entries_by_key'):
        storage_backend.loaded_entries_by_key = {}
    return storage_backend.loaded_entries_by_key


def bykey(storage_key, __entry__):
    """The generic lookup action of every storage backend: return the one Entry object for the key,
        loading it (lazily, see Entry) and remembering it the first time, so that later lookups of the same key,
        however it is spelled, return the same object.
    """
    storage_backend = __entry__.base_object()
    storage_key     = storage_backend.call('canonical_key', [storage_key])
    entries         = loaded_entries(storage_backend)
    if storage_key not in entries:
        entries[storage_key] = Entry(storage_backend=storage_backend, storage_key=storage_key)
    return entries[storage_key]


class Entry(ActionSource):
    """An object of Entry class is an ActionSource that can be stored by a storage backend.

        A storage backend is an Entry with the actions canonical_key, load_data, save_data and remove, optionally load_functions,
        which inherits the generic lookup action bykey() from BASE_STORAGE_BACKEND. The filesystem storage backend is built
        by the kernel; any other one lives in an Entry. An Entry's identity is the pair (storage_backend(), storage_key());
        an Entry without a storage key is not stored (yet).

        Each storage backend keeps one Entry object per key (see loaded_entries()): bykey() returns it, save() puts an Entry there,
        remove() takes it out. Creating an Entry directly with a storage key bypasses this, giving an independent object
        (which tests use to see what is really in storage); if such an Entry is saved, it becomes the one kept for its key.

        A stored Entry loads its data, and its code, only when they are first needed. Only the filesystem storage backend
        provides code: Entries stored elsewhere get their behaviour by inheriting from Entries that have code.
        Parents are not stored yet: they can only be given as objects.
    """

    def __init__(self, name=None, own_data=None, parent_objects=None, own_functions=None, is_override=False, storage_backend=None, storage_key=None):
        """Create an Entry. Without a storage key, it is an unsaved Entry built from the given data, parents and functions.
            With a storage key, its data and code are loaded lazily from the storage backend (by default, the filesystem one),
            unless own_data or own_functions are given explicitly.
        """
        super().__init__(name=name, own_data=own_data, parent_objects=parent_objects, own_functions=own_functions, is_override=is_override)
        if storage_key is not None and storage_backend is None:
            storage_backend = FILESYSTEM_STORAGE_BACKEND
        self.assigned_storage_backend   = storage_backend
        self.assigned_storage_key       = None if storage_key is None else storage_backend.call('canonical_key', [storage_key])
        self.data_loaded                = own_data is not None or storage_key is None


    def storage_backend(self):
        """Return the storage backend of this Entry, or None if it has never been given one.
        """
        return self.assigned_storage_backend


    def storage_key(self):
        """Return the key under which the storage backend keeps this Entry (in canonical form), or None if it is not stored.
        """
        return self.assigned_storage_key


    def set_own_data(self, own_data=None):
        """Replace this Entry's own data, as ParamSource does; the Entry no longer needs to load its data from storage.
        """
        super().set_own_data(own_data)
        self.data_loaded = True
        return self


    def own_data(self):
        """Return the dictionary of this Entry's own data, by reference, loading it from storage the first time if necessary.
        """
        if not self.data_loaded:
            self.own_data_cache = self.storage_backend().call('load_data', [self.storage_key()])
            self.data_loaded    = True
        return self.own_data_cache


    def own_functions(self):
        """Return this Entry's namespace of own functions, loading it from storage the first time if necessary.
            Returns False if the Entry is stored by a storage backend that provides no code, or if it has no code.
        """
        if self.own_functions_cache is None and self.storage_key() is not None:
            storage_backend = self.storage_backend()
            try:
                storage_backend.find_action('load_functions')
            except NameError:
                self.own_functions_cache = False    # storage backends other than the filesystem one provide no code
            else:
                self.own_functions_cache = storage_backend.call('load_functions', [self.storage_key()])
        return self.own_functions_cache


    def save(self, storage_key=None):
        """Store this Entry's own data, under its current storage key or under the given one ("save as").
            Saving under a new key keeps the old copy in storage; the Entry then refers to the new one.
            The saved Entry becomes the one its storage backend keeps for its key (see loaded_entries()).
            Only data is written, never code. On an override, base_object() is saved instead.
            Returns the Entry itself, so that calls can be chained.
        """
        if self.is_override():
            self.base_object().save(storage_key)
            return self

        if storage_key is not None:
            self.own_data()                     # load data and code from the old location (if any) before leaving it
            self.own_functions()
            self.forget_storage_key()
            if self.storage_backend() is None:
                self.assigned_storage_backend = FILESYSTEM_STORAGE_BACKEND
            self.assigned_storage_key = self.storage_backend().call('canonical_key', [storage_key])
        elif self.storage_key() is None:
            raise ValueError(f"[{self.get_name()}] an Entry that has never been stored needs a storage key to be saved")

        self.assigned_storage_key = self.storage_backend().call('save_data', [self.storage_key(), self.own_data()])
        loaded_entries( self.storage_backend() )[ self.storage_key() ] = self
        return self


    def remove(self):
        """Remove this Entry from storage, and from the Entries its storage backend keeps (see loaded_entries()).
            The Entry stays usable in memory, as an Entry that is not stored.
            On an override, base_object() is removed instead. Returns the Entry itself, so that calls can be chained.
        """
        if self.is_override():
            self.base_object().remove()
            return self

        if self.storage_key() is None:
            raise ValueError(f"[{self.get_name()}] an Entry that is not stored cannot be removed")
        self.own_data()                         # keep the in-memory Entry complete once its storage is gone
        self.own_functions()
        self.storage_backend().call('remove', [self.storage_key()])
        self.forget_storage_key()
        return self


    def forget_storage_key(self):
        """Stop being the Entry its storage backend keeps for the current key (if it is), and have no storage key any more.
        """
        if self.storage_key() is not None:
            entries = loaded_entries( self.storage_backend() )
            if entries.get( self.storage_key() ) is self:
                del entries[ self.storage_key() ]
        self.assigned_storage_key = None


# The parent of every storage backend, providing the generic lookup action bykey().
BASE_STORAGE_BACKEND = Entry('base_storage_backend', own_functions=SimpleNamespace(bykey=bykey))

# The one storage backend that is part of the kernel: its actions are the functions of the filesystem_storage_backend module,
# and its own data are the parameters those functions use.
FILESYSTEM_STORAGE_BACKEND = Entry('filesystem_storage_backend', own_functions=filesystem_storage_backend, parent_objects=[BASE_STORAGE_BACKEND],
                                   own_data={ 'data_file_name': 'data_axs.json', 'code_file_name': 'code_axs.py' })


if __name__ == '__main__' or 'unittest' in sys.modules:    # run as a script, or collected by unittest/pytest (which have already loaded unittest)

    import os
    import tempfile
    import unittest
    from copy import deepcopy

    def write_file(path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(text)

    class TestEntry(unittest.TestCase):

        def setUp(self):
            """A stored base Entry with data and code, an unsaved child, and an in-memory storage backend with no code.
            """
            temp_dir = tempfile.TemporaryDirectory(); self.addCleanup(temp_dir.cleanup)
            self.root       = temp_dir.name
            self.base_path  = os.path.join(self.root, 'base')
            write_file(os.path.join(self.base_path, 'data_axs.json'), '{"a": 1, "b": 2}')
            write_file(os.path.join(self.base_path, 'code_axs.py'), 'def add3(a, b, c=0):\n    return a + b + c\n\n'
                                                                    'def remember(__entry__, value):\n    return __entry__.plant("memo", value).save()\n')
            self.base   = Entry(storage_key=self.base_path)
            self.child  = Entry('child', own_data={'b': 20}, parent_objects=[self.base])
            self.store  = {}
            self.fs     = self.new_filesystem_backend()       # a private cache for each test
            self.memory = Entry('memory_storage_backend', parent_objects=[BASE_STORAGE_BACKEND], own_functions=SimpleNamespace(
                canonical_key   = lambda storage_key: storage_key,
                load_data       = lambda storage_key: deepcopy(self.store[storage_key]),
                save_data       = lambda storage_key, own_data: self.store.update({storage_key: deepcopy(own_data)}) or storage_key,
                remove          = lambda storage_key: self.store.pop(storage_key) and None,
            ))

        def new_filesystem_backend(self, **own_data):
            """A variant of the filesystem backend: a child Entry with its own cache, overriding parameters if given.
            """
            return Entry('variant_filesystem_backend', own_data=own_data, parent_objects=[FILESYSTEM_STORAGE_BACKEND])

        def reload(self, path):
            return Entry(storage_key=path).own_data()

        def bypath(self, path, storage_backend=None):
            return (storage_backend or self.fs).call('bypath', [path])

        def test_data_and_code_from_storage(self):  self.assertEqual( (self.base['a'], self.base.call('add3')), (1, 3) )
        def test_code_inherited_by_unsaved(self):   self.assertEqual( self.child.call('add3'), 21 )
        def test_storage_key_is_canonical(self):    self.assertEqual( Entry(storage_key=os.path.join(self.root, 'x', '..', 'base')).storage_key(), os.path.realpath(self.base_path) )
        def test_unsaved_has_no_key(self):          self.assertEqual( (self.child.storage_key(), self.child.storage_backend()), (None, None) )
        def test_unsaved_cannot_save(self):         self.assertRaises( ValueError, self.child.save )
        def test_unsaved_cannot_remove(self):       self.assertRaises( ValueError, self.child.remove )
        def test_no_code_file(self):                self.assertIs( self.child.save(os.path.join(self.root, 'child')).own_functions(), False )
        def test_data_loaded_lazily(self):
            write_file(os.path.join(self.base_path, 'data_axs.json'), '{"a": 100}'); self.assertEqual( self.base['a'], 100 )   # changed after creation, before first use
        def test_save_as_and_reload(self):
            self.child.save(os.path.join(self.root, 'child')); self.assertEqual( self.reload(os.path.join(self.root, 'child')), {'b': 20} )
        def test_edit_and_save(self):
            self.base.plant('c', 3).save(); self.assertEqual( self.reload(self.base_path), {'a': 1, 'b': 2, 'c': 3} )
        def test_save_untouched_keeps_data(self):
            Entry(storage_key=self.base_path).save(); self.assertEqual( self.reload(self.base_path), {'a': 1, 'b': 2} )   # loads before writing
        def test_save_as_keeps_old_copy_and_code(self):
            self.base.save(os.path.join(self.root, 'copy')); self.assertEqual( (self.reload(self.base_path), self.base.call('add3'), self.base.storage_key()), ({'a': 1, 'b': 2}, 3, os.path.realpath(os.path.join(self.root, 'copy'))) )
        def test_remove(self):
            self.base.remove(); self.assertEqual( (os.path.exists(self.base_path), self.base.storage_key(), self.base['a'], self.base.call('add3')), (False, None, 1, 3) )
        def test_save_through_override(self):       # an override's own data (the call's 'value') is never stored
            self.base.call('remember', named_params={'value': 5}); self.assertEqual( self.reload(self.base_path), {'a': 1, 'b': 2, 'memo': 5} )
        def test_memory_backend_round_trip(self):
            Entry(own_data={'x': 1}, storage_backend=self.memory, storage_key='m').save(); self.assertEqual( Entry(storage_backend=self.memory, storage_key='m')['x'], 1 )
        def test_memory_backend_code_by_inheritance(self):
            self.store['m'] = {'b': 20}; self.assertEqual( Entry(storage_backend=self.memory, storage_key='m', parent_objects=[self.base]).call('add3'), 21 )
        def test_memory_backend_provides_no_code(self):
            self.store['m'] = {}; self.assertIs( Entry(storage_backend=self.memory, storage_key='m').own_functions(), False )
        def test_memory_backend_remove(self):
            self.store['m'] = {'x': 1}; Entry(storage_backend=self.memory, storage_key='m').remove(); self.assertEqual( self.store, {} )

        def test_backend_is_unsaved_entry(self):    self.assertEqual( (isinstance(FILESYSTEM_STORAGE_BACKEND, Entry), FILESYSTEM_STORAGE_BACKEND.storage_key()), (True, None) )
        def test_backends_inherit_bykey(self):      self.assertEqual( (FILESYSTEM_STORAGE_BACKEND.find_action('bykey') is bykey, hasattr(filesystem_storage_backend, 'bykey')), (True, False) )
        def test_variant_backend_file_names(self):  # a variant backend is just a child Entry overriding a parameter
            Entry(own_data={'v': 1}, storage_backend=self.new_filesystem_backend(data_file_name='params.json')).save(os.path.join(self.root, 'v')); self.assertEqual( os.listdir(os.path.join(self.root, 'v')), ['params.json'] )
        def test_bykey_gives_one_object(self):      self.assertIs( self.bypath(self.base_path), self.fs.call('bykey', [os.path.join(self.root, 'x', '..', 'base')]) )
        def test_cache_kept_on_real_backend(self):  # bykey() runs on the call's override, but the map must be on the backend itself
            self.bypath(self.base_path); self.assertEqual( list(self.fs.loaded_entries_by_key), [os.path.realpath(self.base_path)] )
        def test_backends_cache_separately(self):   self.assertIsNot( self.bypath(self.base_path), self.bypath(self.base_path, self.new_filesystem_backend()) )
        def test_direct_construction_uncached(self): self.assertIsNot( Entry(storage_backend=self.fs, storage_key=self.base_path), self.bypath(self.base_path) )
        def test_memory_backend_bykey(self):
            self.store['m'] = {'x': 1}; self.assertIs( self.memory.call('bykey', ['m']), self.memory.call('bykey', ['m']) )
        def test_cached_entry_shares_edits(self):
            self.bypath(self.base_path).plant('x', 2); self.assertEqual( self.bypath(os.path.join(self.base_path, '.'))['x'], 2 )
        def test_save_registers(self):
            new_entry = Entry(own_data={'n': 1}, storage_backend=self.fs).save(os.path.join(self.root, 'new')); self.assertIs( self.bypath(os.path.join(self.root, 'new')), new_entry )
        def test_save_as_moves_in_cache(self):
            moved = self.bypath(self.base_path).save(os.path.join(self.root, 'copy')); self.assertEqual( (self.bypath(os.path.join(self.root, 'copy')) is moved, self.bypath(self.base_path) is moved), (True, False) )
        def test_remove_unregisters(self):
            removed = self.bypath(self.base_path).remove(); self.assertEqual( (removed.storage_key(), self.bypath(self.base_path) is removed), (None, False) )
        def test_save_as_of_uncached_keeps_cached(self):
            cached = self.bypath(self.base_path); Entry(storage_backend=self.fs, storage_key=self.base_path).save(os.path.join(self.root, 'copy')); self.assertIs( self.bypath(self.base_path), cached )
        def test_saved_direct_entry_replaces_cached(self):
            direct = Entry(storage_backend=self.fs, storage_key=self.base_path).save(); self.assertIs( self.bypath(self.base_path), direct )

    if __name__ == '__main__':
        unittest.main(verbosity=2)

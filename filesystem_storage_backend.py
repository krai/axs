#!/usr/bin/env python3

"""axs04: the filesystem storage backend, the only storage backend that is part of the kernel itself.

Every other storage backend lives in an Entry, which is ultimately loaded through this one.
Its module-level functions are the backend's actions, just as the functions of an Entry's code_axs.py are its actions.
A storage key is the absolute real path of an Entry's directory, which holds the Entry's data in data_axs.json
and, optionally, its code in code_axs.py.

Running this file as a script runs the tests of its Python API.
"""

import importlib.util
import json
import os
import shutil
import sys

DATA_FILE_NAME  = 'data_axs.json'
CODE_FILE_NAME  = 'code_axs.py'


def canonical_key(storage_key):
    """Return the canonical form of a storage key: the absolute real path, so that different spellings of a path give one key.
    """
    return os.path.realpath(storage_key)


def load_data(storage_key):
    """Return the data stored under the key, or an empty dictionary if the Entry's directory has no data file.
    """
    data_path = os.path.join(storage_key, DATA_FILE_NAME)
    if not os.path.exists(data_path):
        return {}
    with open(data_path) as data_file:
        return json.load(data_file)


def save_data(storage_key, own_data):
    """Write the data under the key, creating the Entry's directory if necessary, and return the key.
        The data file is replaced in one step, so an interrupted save never leaves a half-written file behind.
        Only the data file is written: any code or other files in the directory are left untouched.
    """
    os.makedirs(storage_key, exist_ok=True)
    data_path       = os.path.join(storage_key, DATA_FILE_NAME)
    temp_data_path  = data_path + '.tmp'
    with open(temp_data_path, 'w') as data_file:
        json.dump(own_data, data_file, indent=4)
        data_file.write('\n')
    os.replace(temp_data_path, data_path)
    return storage_key


def remove(storage_key):
    """Remove the Entry's whole directory, including its code and any other files in it.
    """
    shutil.rmtree(storage_key)


def load_functions(storage_key):
    """Load the Entry's code as a module and return it, or return False if the Entry's directory has no code file.
        The module is not registered in sys.modules, so Entries with code in different directories never clash.
    """
    code_path = os.path.join(storage_key, CODE_FILE_NAME)
    if not os.path.exists(code_path):
        return False
    spec    = importlib.util.spec_from_file_location(f"code_axs[{storage_key}]", code_path)
    module  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == '__main__' or 'unittest' in sys.modules:    # run as a script, or collected by unittest/pytest (which have already loaded unittest)

    import tempfile
    import unittest

    class TestFilesystemStorageBackend(unittest.TestCase):

        def setUp(self):
            """A temporary directory with one Entry directory that has both data and code.
            """
            temp_dir = tempfile.TemporaryDirectory(); self.addCleanup(temp_dir.cleanup)
            self.root, self.key = temp_dir.name, os.path.join(temp_dir.name, 'entry')
            save_data(self.key, {"a": 1})
            with open(os.path.join(self.key, CODE_FILE_NAME), 'w') as code_file: code_file.write('def double(a):\n    return 2*a\n')

        def test_round_trip(self):                  self.assertEqual( load_data(self.key), {'a': 1} )
        def test_missing_data_is_empty(self):       self.assertEqual( load_data(self.root), {} )
        def test_missing_code_is_false(self):       self.assertIs( load_functions(self.root), False )
        def test_code_loaded(self):                 self.assertEqual( load_functions(self.key).double(21), 42 )
        def test_canonical_key(self):               self.assertEqual( canonical_key(os.path.join(self.key, '..', 'entry')), os.path.realpath(self.key) )
        def test_save_data_keeps_code_and_no_temp(self):
            save_data(self.key, {'b': 2}); self.assertEqual( sorted(os.listdir(self.key)), [CODE_FILE_NAME, DATA_FILE_NAME] )
        def test_file_is_readable_json(self):
            with open(os.path.join(self.key, DATA_FILE_NAME)) as f: self.assertEqual( f.read(), '{\n    "a": 1\n}\n' )
        def test_remove(self):
            remove(self.key); self.assertFalse( os.path.exists(self.key) )

    if __name__ == '__main__':
        unittest.main(verbosity=2)

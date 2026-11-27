"""axs04: the code of the base storage backend, the parent of every storage backend, beside core_collection in the kernel Entry's directory.

It holds what all storage backends share, whatever they store in: one object per storage key (loaded_entries(), bykey()),
and defaults for optional actions. The kernel's bootstrap loads it through the filesystem storage backend.
"""

def loaded_entries(__real_entry__):
    """Return the dictionary of the Entries this storage backend has loaded or saved, keyed by their canonical storage keys.
        It is kept on the backend Entry itself (never on an override of it), and created when first needed.

        Usage examples:
            axs storage_backend , loaded_entries
    """
    if not hasattr(__real_entry__, 'loaded_entries_by_key'):
        __real_entry__.loaded_entries_by_key = {}
    return __real_entry__.loaded_entries_by_key


def bykey(storage_key, __real_entry__):
    """Return the one Entry object for the key, loading it (lazily) and remembering it the first time,
        so that later lookups of the same key, however it is spelled, return the same object.

        Usage examples:
            axs storage_backend , bykey "$(axs byname foo , storage_key)" , get greeting  # => hello from foo
    """
    storage_key = __real_entry__.call('canonical_key', [storage_key])
    entries     = __real_entry__.call('loaded_entries')
    if storage_key not in entries:
        entries[storage_key] = type(__real_entry__)(storage_backend=__real_entry__, storage_key=storage_key)     # the backend is an Entry itself
    return entries[storage_key]


def load_functions(storage_key):
    """Return False: by default a storage backend provides no code, and the Entries it stores get their behaviour
        by inheriting from Entries that have code. The filesystem storage backend redefines this.
    """
    return False

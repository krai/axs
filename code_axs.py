"""axs04: the code of the kernel Entry, the starting point for finding everything else.

The kernel Entry inherits core_collection's code (byname() and others) and redefines only walk(),
so that every such function searches the collections of collection_search_path, in order.
"""


def version(__version__):
    """Return the version of axs, kept in the kernel Entry's own data.
    """
    return __version__


def core_collection(core_collection_path, __entry__):
    """Return core_collection, found at core_collection_path relative to the kernel Entry.
    """
    kernel_entry    = __entry__.base_object()
    storage_backend = kernel_entry.storage_backend()
    return storage_backend.call('bykey', [ storage_backend.call('resolve_key', [kernel_entry.storage_key(), core_collection_path]) ])


def walk(collection_search_path, __entry__):
    """Yield the Entries of each collection in collection_search_path in turn, where each element names a kernel action
        that returns a collection. Each collection is walked by its own walk(), so the first match of a name wins.
    """
    for collection_action_name in collection_search_path:
        yield from __entry__.call(collection_action_name).call('walk')


def bypath(path, __entry__):
    """Return the one Entry object stored at the path, through the kernel Entry's own storage backend.
    """
    return __entry__.base_object().storage_backend().call('bykey', [path])


def fresh_entry(entry_path=None, own_data=None, name=None, __entry__=None):
    """Return a new Entry that is not stored yet: with optional data, no code, and an optional path under which save() will store it.
        Without a name, an Entry with a path is named after it.
    """
    kernel_entry    = __entry__.base_object()
    entry_class     = type(kernel_entry)        # the kernel Entry is an Entry itself, so no import is needed
    return entry_class(name=name, own_data=own_data if own_data is not None else {}, own_functions=False,
                       storage_backend=None if entry_path is None else kernel_entry.storage_backend(), storage_key=entry_path)

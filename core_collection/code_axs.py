"""axs04: the code of core_collection, inherited by every collection.

A collection is an Entry with _contained_entries in its own data: a dictionary mapping the names of the Entries
it contains to their keys relative to its own (for the filesystem storage backend, relative paths).
The leading underscore keeps contents from being inherited: a collection's descendants do not appear to contain its Entries.
"""


def walk(__entry__):
    """Yield the collection itself, then the Entries it contains, in order, walking into contained collections depth-first.
        Contained collections are recognised by _contained_entries in their own data, and walked by this very function,
        so they need no code of their own. Each Entry is found through the collection's storage backend, so it is the cached one.
    """
    collection      = __entry__.base_object()
    storage_backend = collection.storage_backend()
    yield collection

    for entry_name, relative_key in collection['_contained_entries'].items():
        contained_entry = storage_backend.call('bykey', [ storage_backend.call('resolve_key', [collection.storage_key(), relative_key]) ])
        contained_entry.set_containing_collection(collection)
        if '_contained_entries' in contained_entry.own_data():
            yield from walk(contained_entry)
        else:
            yield contained_entry


def byname(entry_name, __entry__):
    """Return the first Entry named entry_name found by walk(), or None if there is none.
    """
    for candidate_entry in walk(__entry__):
        if candidate_entry.get_name()==entry_name:
            return candidate_entry
    return None

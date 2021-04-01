#!/usr/bin/env python3

""" This entry knows how to make other entries.
"""

def walk(__entry__):
    """An internal recursive generator not to be called directly
    """

    assert __entry__ != None, "__entry__ should be defined"
    ak = __entry__.get_kernel()
    assert ak != None, "__entry__'s kernel should be defined"
    collection_own_name = __entry__.get_name()


    print(f"collection({collection_own_name}).walk(): trying the collection itself")
    yield __entry__

    print(f"collection({collection_own_name}).walk(): walking contained_entries:")
    contained_entries = __entry__.get('contained_entries')
    for entry_name in contained_entries:
        if type(contained_entries)==dict:
            relative_entry_path = contained_entries[entry_name]
            print(f"collection({collection_own_name}).walk(): mapping {entry_name} to relative_entry_path={relative_entry_path}")
        else:
            relative_entry_path = entry_name
            print(f"collection({collection_own_name}).walk(): using relative_entry_path={entry_name}")
        yield ak.bypath(path=__entry__.get_path(relative_entry_path), name=entry_name)

    print(f"collection({collection_own_name}).walk(): recursing into contained_collections:")
    contained_collections = __entry__.get('contained_collections')
    for collection_name in contained_collections:
        print(f"collection({collection_own_name}).walk() checking in {collection_name}...")

        if type(contained_collections)==dict:
            relative_collection_path = contained_collections[collection_name]
            print(f"collection({collection_own_name}).walk(): mapping {collection_name} to relative_collection_path={relative_collection_path}")
        else:
            relative_collection_path = collection_name
            print(f"collection({collection_own_name}).walk(): using relative_collection_path={relative_collection_path}")

        collection_object   = ak.bypath(path=__entry__.get_path(relative_collection_path), name=collection_name)

        yield from walk(collection_object)


def byname(entry_name, __entry__=None):
    """Fetch an entry by name
    """

    for candidate_entry in walk(__entry__):
        if candidate_entry.get_name() == entry_name:
            return candidate_entry
    return None


def byquery(query,  __entry__=None):
    """Fetch an entry by query
    """

    positive_tags_set   = set()
    negative_tags_set   = set()
    for posi_nega_tag in query.split(','):
        if posi_nega_tag.startswith('-'):
            negative_tags_set.add( posi_nega_tag[1:] )
        else:
            positive_tags_set.add( posi_nega_tag )

    for candidate_entry in walk(__entry__):
        candidate_tags_set  = set(candidate_entry.get('tags') or [])

        if (positive_tags_set <= candidate_tags_set) and negative_tags_set.isdisjoint(candidate_tags_set):
            return candidate_entry
    return None


if __name__ == '__main__':

    print("Unfortunately this entry cannot be tested separately from the framework")


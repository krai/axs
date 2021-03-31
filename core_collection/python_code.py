#!/usr/bin/env python3

""" This entry knows how to make other entries.
"""

def byname(entry_name, contained_entries, contained_collections=None, __entry__=None):

    assert __entry__ != None, "__entry__ should be defined"
    ak = __entry__.get_kernel()
    assert ak != None, "__entry__'s kernel should be defined"

    if entry_name == __entry__.get_name():
        print(f"collection.byname({entry_name}): found the collection itself")
        return __entry__
    elif entry_name in contained_entries:
        if type(contained_entries)==dict:
            relative_entry_path = contained_entries[entry_name]
            print(f"collection.byname({entry_name}): mapping to relative_entry_path={relative_entry_path}")
        else:
            relative_entry_path = entry_name
            print(f"collection.byname({entry_name}): using relative_entry_path={entry_name}")
        return ak.bypath(path=__entry__.get_path(relative_entry_path))

    elif contained_collections:
        print(f"collection.byname({entry_name}) recursing into contained_collections...")

        for collection_name in contained_collections:
            print(f"collection.byname({entry_name}) checking in {collection_name}...")

            if type(contained_collections)==dict:
                relative_collection_path = contained_collections[collection_name]
                print(f"collection.byname({entry_name}): mapping to relative_collection_path={relative_collection_path}")
            else:
                relative_collection_path = collection_name
                print(f"collection.byname({entry_name}): using relative_collection_path={relative_collection_path}")

            collection_object   = ak.bypath(path=__entry__.get_path(relative_collection_path))
            found_object        = collection_object.call("byname", [ entry_name ])
            if found_object:
                print(f"collection.byname({entry_name}): found in collection {collection_name}")
                return found_object
    
    return None


if __name__ == '__main__':

    print("Unfortunately this entry cannot be tested separately from the framework")


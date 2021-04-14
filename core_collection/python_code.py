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


    print(f"collection({collection_own_name}).walk(): yielding the collection itself")
    yield __entry__

    print(f"collection({collection_own_name}).walk(): walking contained_entries:")
    contained_entries = __entry__.get('contained_entries',[])
    for entry_name in contained_entries:
        relative_entry_path = contained_entries[entry_name]
        print(f"collection({collection_own_name}).walk(): mapping {entry_name} to relative_entry_path={relative_entry_path}")

        contained_entry = ak.bypath(path=__entry__.get_path(relative_entry_path), name=entry_name, container=__entry__)
        if contained_entry.can( 'walk' ):
            print(f"collection({collection_own_name}).walk(): recursively walking collection {entry_name}...")
            yield from walk(contained_entry)
        else:
            print(f"collection({collection_own_name}).walk(): yielding non-collection {entry_name}")
            yield contained_entry


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

    def create_filter(key_path, fun, against=None):
        """ Finally, a useful real-life example of closures:
            captures both *fun* and *against* in the internal function.
        """
        split_key_path = key_path.split('.')    # computed only once during closure creation

        def filter_closure(entry):
            return fun(entry.dig(split_key_path, safe=True, parent_recursion=False), against)   # computed every time during filter application

        return filter_closure


    import re
    from function_access import to_num_or_not_to_num

    positive_tags_set   = set()
    negative_tags_set   = set()
    conditions          = query.split(',')
    filter_list         = []

    # parsing the query:
    for condition in conditions:
        binary_op_match = re.match('([\w\.]*\w)(=|==|!=|<>|<|>|<=|>=|:|!:)(-?[\w\.]+)$', condition)
        if binary_op_match:
            key_path    = binary_op_match.group(1)
            binary_op   = binary_op_match.group(2)
            test_val    = to_num_or_not_to_num(binary_op_match.group(3))
            if binary_op in ('=', '=='):
                filter_list.append( create_filter(key_path, lambda x, y : x==y, test_val) )
            elif binary_op in ('!=', '<>'):
                filter_list.append( create_filter(key_path, lambda x, y : x!=y, test_val) )
            elif binary_op=='<':
                filter_list.append( create_filter(key_path, lambda x, y : x!=None and x<y, test_val) )
            elif binary_op=='>':
                filter_list.append( create_filter(key_path, lambda x, y : x!=None and x>y, test_val) )
            elif binary_op=='<=':
                filter_list.append( create_filter(key_path, lambda x, y : x!=None and x<=y, test_val) )
            elif binary_op=='>=':
                filter_list.append( create_filter(key_path, lambda x, y : x!=None and x>=y, test_val) )
            elif binary_op==':':
                filter_list.append( create_filter(key_path, lambda x, y : type(x)==list and y in x, test_val) )
            elif binary_op=='!:':
                filter_list.append( create_filter(key_path, lambda x, y : type(x)==list and y not in x, test_val) )
        else:
            unary_op_match = re.match('([\w\.]*\w)(\.|\?)$', condition)
            if unary_op_match:
                key_path    = unary_op_match.group(1)
                unary_op    = unary_op_match.group(2)
                if unary_op=='.':
                    filter_list.append( create_filter(key_path, lambda x, y: x!=None) )
                elif unary_op=='?':
                    filter_list.append( create_filter(key_path, lambda x, y: bool(x)) )
            else:
                tag_match = re.match('([!^-])?(\w+)$', condition)
                if tag_match:
                    if tag_match.group(1):
                        negative_tags_set.add( tag_match.group(2) )
                    else:
                        positive_tags_set.add( tag_match.group(2) )
                else:
                    raise(SyntaxError("Could not parse the condition '{}'".format(condition)))


    # applying the query as a filter:
    for candidate_entry in walk(__entry__):
        candidate_tags_set  = set(candidate_entry.get('tags') or [])

        if (positive_tags_set <= candidate_tags_set) and negative_tags_set.isdisjoint(candidate_tags_set):
            candidate_still_ok = True
            for filter_function in filter_list:
                if not filter_function(candidate_entry):
                    candidate_still_ok = False
                    break
            if candidate_still_ok:
                return candidate_entry
    return None


if __name__ == '__main__':

    print("Unfortunately this entry cannot be tested separately from the framework")


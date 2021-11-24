#!/usr/bin/env python3

""" This entry knows how to make other entries.
"""

from copy import deepcopy
import logging
import os

def walk(__entry__):
    """An internal recursive generator not to be called directly
    """

    ak = __entry__.get_kernel()
    assert ak != None, "__entry__'s kernel should be defined"
    collection_own_name = __entry__.get_name()


    logging.debug(f"collection({collection_own_name}): yielding the collection itself")
    yield __entry__

    logging.debug(f"collection({collection_own_name}): walking contained_entries:")
    contained_entries = __entry__.get('contained_entries', {})
    for entry_name in contained_entries:
        relative_entry_path = contained_entries[entry_name]
        logging.debug(f"collection({collection_own_name}): mapping {entry_name} to relative_entry_path={relative_entry_path}")

        contained_entry = ak.bypath(path=__entry__.get_path(relative_entry_path), name=entry_name, container=__entry__)

        # Have to resort to duck typing to avoid triggering dependencies by testing if contained_entry.can('walk'):
        if 'contained_entries' in contained_entry.own_data():
            logging.debug(f"collection({collection_own_name}): recursively walking collection {entry_name}...")
            yield from walk(contained_entry)
        else:
            logging.debug(f"collection({collection_own_name}): yielding non-collection {entry_name}")
            yield contained_entry


def attached_entry(entry_path=None, own_data=None, generated_name_prefix=None, __entry__=None):
    """Create a new entry with the given name and attach it to this collection

Usage examples :
                axs work_collection , attached_entry ultimate_answer ---='{"answer":42}' , save
    """

    return __entry__.get_kernel().fresh_entry(container=__entry__, entry_path=entry_path, own_data=own_data, generated_name_prefix=generated_name_prefix)


def byname(entry_name, __entry__):
    """Fetch an entry by name
    """

    for candidate_entry in walk(__entry__):
        if candidate_entry.get_name() == entry_name:
            return candidate_entry
    return None


def byquery(query, produce_if_not_found=True, parent_recursion=False, __entry__=None):
    """Fetch an entry by query.
        If the query returns nothing on the first pass, but matching _producer_rules are defined,
        apply the matching producer_rule and return its output.

Usage examples :
                axs byquery python_package,package_name=numpy , get_path
                axs byquery python_package,package_name=numpy,package_version=1.16.4 , get_metadata --header_name=Version
                axs byquery shell_tool,tool_name=wget
            # the query given as an explicit list of query_conditions
                axs byquery axs byquery --:=count:romance:^french
                axs byquery "--,=count,romance,language!=French"
    """
    assert __entry__ != None, "__entry__ should be defined"

    import re
    from function_access import to_num_or_not_to_num

    def parse_condition(condition, context):

        binary_op_match = re.match('([\w\.]*\w)(==|=|!=|<>|<=|>=|<|>|:|!:)(.+)$', condition)
        if binary_op_match:
            key_path    = binary_op_match.group(1)
            op          = binary_op_match.group(2)
            val         = to_num_or_not_to_num(binary_op_match.group(3))

            if op in ('=', '=='):
                op = '='
                comparison_lambda   = lambda x, y : x==y
            elif op in ('!=', '<>'):
                comparison_lambda   = lambda x, y : x!=y
            elif op=='<':
                comparison_lambda   = lambda x, y : x!=None and x<y
            elif op=='>':
                comparison_lambda   = lambda x, y : x!=None and x>y
            elif op=='<=':
                comparison_lambda   = lambda x, y : x!=None and x<=y
            elif op=='>=':
                comparison_lambda   = lambda x, y : x!=None and x>=y
            elif op==':':
                comparison_lambda   = lambda x, y : type(x)==list and y in x
            elif op=='!:':
                comparison_lambda   = lambda x, y : type(x)==list and y not in x
            else:
                raise SyntaxError(f"Could not parse the condition '{condition}' in {context}")
        else:
            unary_op_match = re.match('([\w\.]*\w)(\.|\?|\+|-)$', condition)
            if unary_op_match:
                key_path    = unary_op_match.group(1)
                op          = unary_op_match.group(2)
                val         = None
                if op=='.':               # path exists
                    comparison_lambda   = lambda x, y: x!=None
                elif op in ('?', '+'):    # computes to True
                    comparison_lambda   = lambda x, y: bool(x)
                elif op=='-':             # computes to False
                    comparison_lambda   = lambda x, y: not bool(x)
                else:
                    raise SyntaxError(f"Could not parse the condition '{condition}' in {context}")
            else:
                tag_match = re.match('([!^-])?(\w+)$', condition)
                if tag_match:
                    key_path    = 'tags'
                    val         = tag_match.group(2)
                    if tag_match.group(1):
                        op = "tag-"
                        comparison_lambda   = lambda x, y : type(x)!=list or y not in x
                    else:
                        op = "tag+"
                        comparison_lambda   = lambda x, y : type(x)==list and y in x
                else:
                    raise SyntaxError(f"Could not parse the condition '{condition}' in {context}")

        return key_path, op, val, comparison_lambda


    query_conditions    = query if type(query)==list else query.split(',')
    query_posi_tag_set  = set()
    query_posi_val_dict = {}
    query_mentioned_set = set()
    query_filter_list   = []

    # parsing the Query:
    for condition in query_conditions:
        key_path, op, val, query_comparison_lambda = parse_condition( condition, "Query" )
        query_mentioned_set.add( key_path )

        if op=='=':
            query_posi_val_dict[key_path] = val
        elif op=='tag+':
            query_posi_tag_set.add( val )

        query_filter_list.append( (key_path, op, val, query_comparison_lambda, key_path.split('.')) )

    # trying to match the Query in turn against each existing and walkable entry:
    for candidate_entry in walk(__entry__):
        candidate_still_ok = True
        for key_path, op, val, query_comparison_lambda, split_key_path in query_filter_list:
            if not query_comparison_lambda( candidate_entry.dig(split_key_path, safe=True, parent_recursion=parent_recursion), val ):
                candidate_still_ok = False
                break
        if candidate_still_ok:
            return candidate_entry

    # if a matching entry does not exist, see if we can produce it with a matching Rule
    if produce_if_not_found and len(query_posi_tag_set):
        logging.warning(f"[{__entry__.get_name()}] byquery({query}) did not find anything, but there are tags: {query_posi_tag_set} , trying to find a producer...")

        for advertising_entry in walk(__entry__):
            for rule_index, unprocessed_rule in enumerate( advertising_entry.own_data().get('_producer_rules', []) ):   # block processing some params until they are really needed
                rule_conditions = unprocessed_rule[0]

                rule_posi_tag_set   = set()
                rule_posi_val_dict  = {}
                rule_filter_list    = []

                # parsing the Rule
                for condition in rule_conditions:
                    key_path, op, val, rule_comparison_lambda = parse_condition( condition, f"Entry: {advertising_entry.get_name()}" )

                    if op=='=':
                        rule_posi_val_dict[key_path] = val
                    elif op=='tag+':
                        rule_posi_tag_set.add( val )

                    rule_filter_list.append( (key_path, op, val, rule_comparison_lambda) )

                if rule_posi_tag_set.issubset(query_posi_tag_set):  # FIXME:  rule_posi_tag_set should include it
                    qr_conditions_ok  = True

                    # first matching rule's conditions against query's values:
                    for key_path, op, rule_val, rule_comparison_lambda in rule_filter_list:

                        if op=='tag+': continue     # we have matched them directly above

                        # we allow (only) equalities on the rule side not to have a match on the query side
                        qr_conditions_ok = rule_comparison_lambda( query_posi_val_dict[key_path], rule_val ) if (key_path in query_posi_val_dict) else ((op=='=') and (key_path in query_mentioned_set))
                        if not qr_conditions_ok: break

                    if qr_conditions_ok:
                        # then matching query's conditions against rule's values:
                        for key_path, op, query_val, query_comparison_lambda, split_key_path in query_filter_list:

                            if op=='tag+': continue     # we have matched them directly above

                            # we allow (only) equalities on the query side not to have a match on the rule side
                            qr_conditions_ok = query_comparison_lambda( rule_posi_val_dict[key_path], query_val ) if (key_path in rule_posi_val_dict) else (op=='=')
                            if not qr_conditions_ok: break

                    if qr_conditions_ok:
                        all_processed_rules = advertising_entry.get('_producer_rules')
                        if type(all_processed_rules)!=list:
                            raise(KeyError(f"{advertising_entry.get_name()}'s _producer_rules[] is incomplete, please check all substitutions work"))

                        _, producer_entry, producer_method, extra_params = all_processed_rules[rule_index]
                        #extra_params    = advertising_entry.nested_calls( unprocessed_rule[3] )

                        logging.warning(f"Entry '{advertising_entry.get_name()}' advertises producer '{producer_entry.get_name()}' with action {producer_method}({extra_params}) and matching tags {rule_posi_tag_set} that may work with {query_posi_val_dict}")
                        cumulative_params = deepcopy( extra_params )    # defaults first
                        cumulative_params.update( rule_posi_val_dict )  # rules on top (may override some defaults)
                        cumulative_params.update( query_posi_val_dict ) # query on top (may override some defaults)
                        cumulative_params["tags"] = list(query_posi_tag_set)    # FIXME:  rule_posi_tag_set should include it
                        producer_entry.runtime_stack().append( advertising_entry )
                        new_entry = producer_entry.call(producer_method, [], {'AS^IS':cumulative_params})
                        producer_entry.runtime_stack().pop()
                        if new_entry:
                            logging.warning("The rule selected produced an entry.")
                            return new_entry
                        else:
                            logging.warning("The rule selected didn't produce an entry, but maybe there is a better rule...")

    else:
        logging.debug(f"[{__entry__.get_name()}] byquery({query}) did not find anything, and no matching _producer_rules => returning None")
        return None


def add_entry_path(new_entry_path, new_entry_name=None, __entry__=None):
    """Add a new entry to the collection given the path
    """
    assert __entry__ != None, "__entry__ should be defined"

    trimmed_new_entry_path  = __entry__.trim_path( new_entry_path )
    new_entry_name          = new_entry_name or os.path.basename( trimmed_new_entry_path )
    existing_rel_path       = __entry__.dig(['contained_entries', new_entry_name], safe=True)

    if existing_rel_path:
        if existing_rel_path == trimmed_new_entry_path:
            logging.warning(f"The entry {existing_rel_path} has already been attached to the {__entry__.get_name()} collection, skipping")
        else:
            raise(KeyError(f"There was already another entry named {new_entry_name} with path {existing_rel_path}, remove it first"))
    else:
        __entry__.plant(['contained_entries', new_entry_name], trimmed_new_entry_path)
        return __entry__.save()


def remove_entry_name(old_entry_name, __entry__):

    contained_entries       = __entry__.pluck(['contained_entries', old_entry_name])
    return __entry__.save()



if __name__ == '__main__':

    print("Unfortunately this entry cannot be tested separately from the framework")


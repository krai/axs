#!/usr/bin/env python3

""" This entry knows how to make other entries.
"""

from copy import deepcopy
import logging
import os
import ufun

def walk(__entry__, skip_entry_names=None):
    """An internal recursive generator not to be called directly
    """
    ak = __entry__.get_kernel()
    assert ak != None, "__entry__'s kernel should be defined"
    collection_own_name = __entry__.get_name()

    seen_entry_names = set()
    try:
        logging.debug(f"collection({collection_own_name}): yielding the collection itself")
        yield __entry__

        logging.debug(f"collection({collection_own_name}): walking contained_entries:")
        contained_entries = __entry__.get('contained_entries', {})
        for entry_name in contained_entries:
            if skip_entry_names and (entry_name in skip_entry_names):
                logging.debug(f"collection({collection_own_name}): skipping {entry_name}")
                continue

            entry_value = contained_entries[entry_name]

            if type(entry_value)==str:
                relative_entry_path = entry_value
                logging.debug(f"collection({collection_own_name}): mapping {entry_name} to relative_entry_path={relative_entry_path}")

                contained_entry = ak.bypath(path=__entry__.get_path(relative_entry_path), name=entry_name, container=__entry__)

                # Have to resort to duck typing to avoid triggering dependencies by testing if contained_entry.can('walk'):
                if 'contained_entries' in contained_entry.own_data():
                    logging.debug(f"collection({collection_own_name}): recursively walking collection {entry_name}...")
                    yield from walk(contained_entry)
                    contained_entry.touch('_BEFORE_CODE_LOADING')
                else:
                    logging.debug(f"collection({collection_own_name}): yielding non-collection {entry_name}")
                    yield contained_entry
            else:
                logging.debug(f"collection({collection_own_name}): yielding non-filesystem entry {entry_name}")
                yield entry_value

            seen_entry_names.add( entry_name )

    except RuntimeError as e:
        if str(e)=="dictionary changed size during iteration":
            print(f"Collection {__entry__.get_name()} modified under iteration, checking the new ones")
            yield from walk(__entry__, seen_entry_names)
        else:
            raise e

def attached_entry(entry_path=None, own_data=None, generated_name_prefix=None, __entry__=None):
    """Create a new entry with the given name and attach it to this collection

Usage examples :
                axs work_collection , attached_entry ultimate_answer ---='{"answer":42}' , save
    """
    return __entry__.get_kernel().fresh_entry(container=__entry__, entry_path=entry_path, own_data=own_data, generated_name_prefix=generated_name_prefix)


def byname(entry_name, skip_entry_names=None, __entry__=None):
    """Fetch an entry by name
    """
    for candidate_entry in walk(__entry__, skip_entry_names):
        if candidate_entry.get_name() == entry_name:
            return candidate_entry
    return None



class FilterPile:

    def __init__(self, conditions, context):

        import re

        def parse_condition(condition, context):

            if type(condition)==list and len(condition)==2:   # pre-parsed equality
                key_path, val = condition
                op = '='
                comparison_lambda   = lambda x: x==val

            else:   # a pre-parsed binary op list or string that needs to be parsed (even if a tag)
                from function_access import to_num_or_not_to_num

                if type(condition)==list and len(condition)==3:
                    key_path, op, val = condition
                    pre_val = str(val)
                    binary_op_match = True
                else:
                    binary_op_match = re.match('([\\w\\.\\-]*\\w)(:=|\\?=|===|==|=|!==|!=|<>|<=|>=|<|>|:|!:)(.*)$', condition)
                    if binary_op_match:
                        key_path    = binary_op_match.group(1)
                        op          = binary_op_match.group(2)
                        pre_val     = binary_op_match.group(3)
                        val         = to_num_or_not_to_num(pre_val)

                if binary_op_match:
                    if op in (':=',):           # auto-split
                        op = '='
                        pre_val = pre_val.split(':')
                        val     = [ to_num_or_not_to_num(x) for x in pre_val ]
                        comparison_lambda   = lambda x: x==val
                    elif op in ('?=',):         # optional/selective match
                        comparison_lambda   = lambda x: x==val
                    elif op in ('=', '=='):     # with auto-conversion to numbers
                        op = '='
                        comparison_lambda   = lambda x: x==val
                    elif op in ('===',):        # no auto-conversion
                        op = '='
                        comparison_lambda   = lambda x: x==pre_val
                        val                 = pre_val
                    elif op in ('<>', '!='):    # with auto-conversion to numbers
                        comparison_lambda   = lambda x: x!=val
                    elif op in ('!==',):        # no auto-conversion
                        comparison_lambda   = lambda x: x!=pre_val
                        val                 = pre_val
                    elif op=='<' and len(pre_val)>0:
                        comparison_lambda   = lambda x: x!=None and x<val
                    elif op=='>' and len(pre_val)>0:
                        comparison_lambda   = lambda x: x!=None and x>val
                    elif op=='<=' and len(pre_val)>0:
                        comparison_lambda   = lambda x: x!=None and x<=val
                    elif op=='>=' and len(pre_val)>0:
                        comparison_lambda   = lambda x: x!=None and x>=val
                    elif op==':' and len(pre_val)>0:
                        comparison_lambda   = lambda x: type(x)==list and val in x
                    elif op=='!:' and len(pre_val)>0:
                        comparison_lambda   = lambda x: type(x)==list and val not in x
                    else:
                        raise SyntaxError(f"Could not parse the condition '{condition}' in {context}")
                else:
                    unary_op_match = re.match('([\\w\\.]*\\w)(\\.|!\\.|\\?|\\+|-)$', condition)
                    if unary_op_match:
                        key_path    = unary_op_match.group(1)
                        op          = unary_op_match.group(2)
                        val         = None
                        if op=='.':               # path exists
                            comparison_lambda   = lambda x: x is not None
                        elif op=='!.':            # path does not exist
                            comparison_lambda   = lambda x: x is None
                        elif op=='+':             # computes to True
                            op, val = '=', True
                            comparison_lambda   = lambda x: bool(x)
                        elif op=='-':             # computes to False
                            op, val = '=', False
                            comparison_lambda   = lambda x: not bool(x)
                        else:
                            raise SyntaxError(f"Could not parse the condition '{condition}' in {context}")
                    else:
                        tag_match = re.match('([!^-])?(\\w+)$', condition)
                        if tag_match:
                            key_path    = 'tags'
                            val         = tag_match.group(2)
                            if tag_match.group(1):
                                op = "tag-"
                                comparison_lambda   = lambda x: type(x)!=list or val not in x
                            else:
                                op = "tag+"
                                comparison_lambda   = lambda x: type(x)==list and val in x
                        else:
                            raise SyntaxError(f"Could not parse the condition '{condition}' in {context}")

            return key_path, op, val, comparison_lambda


        self.conditions    = conditions if type(conditions)==list else re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', conditions)
        self.context       = context
        self.posi_tag_set  = set()
        self.posi_val_dict = {}
        self.opti_val_dict = {}
        self.mentioned_set = set()
        self.filter_list   = []

        # parsing the Query:
        for condition in self.conditions:
            if condition in (None, ""): continue

            key_path, op, val, comparison_lambda = parse_condition( condition, self.context )
            self.mentioned_set.add( key_path )

            if op=='=':
                self.posi_val_dict[key_path] = val
            elif op=='?=':
                self.opti_val_dict[key_path] = val
            elif op=='tag+':
                self.posi_tag_set.add( val )

            self.filter_list.append( (key_path, op, val, comparison_lambda, key_path.split('.')) )


    def matches_entry(self, candidate_entry, parent_recursion):

        candidate_still_ok = True
        for key_path, op, val, query_comparison_lambda, split_key_path in self.filter_list:
            try:
                if not query_comparison_lambda( candidate_entry.dig(split_key_path, safe=True, parent_recursion=parent_recursion) ):
                    candidate_still_ok = False
                    break
            except RuntimeError as e:
                if parent_recursion and ("could not be loaded" in str(e)) :
                    logging.warning( str(e) )
                    candidate_still_ok = False
                    break
                else:
                    raise(e)
        return candidate_still_ok


def all_byquery(query, pipeline=None, template=None, parent_recursion=False, skip_entry_names=None, __entry__=None):
    """Returns a list of ALL entries matching the query.
        Empty list if nothing matched.

Usage examples :
                axs all_byquery onnx_model
                axs all_byquery python_package,package_name=pillow
                axs all_byquery onnx_model --template="#{model_name}# : #{file_name}#"
                axs all_byquery python_package --template="python_#{python_version}# package #{package_name}#"
                axs all_byquery tags. --template="tags=#{tags}#"
                axs all_byquery deleteme+ ---='[["remove"]]'
    """
    assert __entry__ != None, "__entry__ should be defined"

    parsed_query        = FilterPile( query, "Query" )

    # trying to match the Query in turn against each existing and walkable entry, gathering them all:
    result_list = []
    for candidate_entry in walk(__entry__, skip_entry_names):
        if parsed_query.matches_entry( candidate_entry, parent_recursion ):
            if pipeline:
                single_result = candidate_entry.execute(pipeline)
            elif template is not None:
                single_result = str(candidate_entry.substitute(template))
            else:
                single_result = candidate_entry

            result_list.append( single_result )

    if template is not None:
        return "\n".join( result_list )
    else:
        return result_list


def find_matching_rules(parsed_query, __entry__):
    """An internal method for finding matching rules given a query, not to be called directly
    """
    matching_rules = []
    for advertising_entry in walk(__entry__):
        for unprocessed_rule in advertising_entry.own_data().get('_producer_rules', []):        # block processing some params until they are really needed
            parsed_rule     = FilterPile( advertising_entry.nested_calls( unprocessed_rule[0] ), f"Entry: {advertising_entry.get_name()}" )

            if parsed_rule.posi_tag_set.issubset(parsed_query.posi_tag_set):  # FIXME:  parsed_rule.posi_tag_set should include it
                qr_conditions_ok  = True

                # first matching rule's conditions against query's values:
                for key_path, op, rule_val, rule_comparison_lambda, _ in parsed_rule.filter_list:

                    if op=='tag+': continue     # we have matched them directly above

                    if op=='tag-':  # rule doesn't want the query to contain a certain tag
                        qr_conditions_ok = rule_val not in parsed_query.posi_tag_set
                        break

                    # we allow (only) equalities on the rule side not to have a match on the query side
                    elif (key_path in parsed_query.posi_val_dict):    # does the query contain a specific value for this rule condition's key_path?
                        qr_conditions_ok = rule_comparison_lambda( parsed_query.posi_val_dict[key_path] )       # if so, use this value in evaluating this rule condition
                    else:
                        qr_conditions_ok = (((op=='?=') and (key_path not in parsed_query.mentioned_set)) or    # ignore optional(selective) matches
                                            ((op=='!.') and (key_path not in parsed_query.mentioned_set)) or
                                            ((op=='=') and (key_path in parsed_query.mentioned_set)))           # otherwise if this rule condition sets a value, the query should have a corresponding condition to check (later)

                    if not qr_conditions_ok: break

                if qr_conditions_ok:
                    # then matching query's conditions against rule's values:
                    for key_path, op, query_val, query_comparison_lambda, _ in parsed_query.filter_list:

                        if op=='tag+': continue     # we have matched them directly above

                        if op=='tag-':  # query doesn't want the rule to contain a certain tag
                            qr_conditions_ok = query_val not in parsed_rule.posi_tag_set
                            break

                        # we allow (only) equalities on the query side not to have a match on the rule side
                        elif (key_path in parsed_rule.posi_val_dict): # does the rule contain a specific value for this query condition's key_path?
                            qr_conditions_ok = query_comparison_lambda( parsed_rule.posi_val_dict[key_path] )   # if so, use this value in evaluating this query condition
                        else:
                            qr_conditions_ok = (op=='=')                                                        # otherwise this query condition must set a value

                        if not qr_conditions_ok: break

                if qr_conditions_ok:
                    matching_rules.append( (advertising_entry, unprocessed_rule, parsed_rule) )

    return sorted( matching_rules, key = lambda x: len(x[1][0]), reverse=True)


def show_matching_rules(query, __entry__):
    """Find and show all the rules (and their advertising entries) that match the given query.

Usage examples :
                axs show_matching_rules shell_tool,can_download_url_from_zenodo
    """
    parsed_query        = FilterPile( query, "Query" )

    matching_rules = find_matching_rules(parsed_query, __entry__)

    for advertising_entry, unprocessed_rule, parsed_rule in matching_rules:
        print( f"{advertising_entry.get_path()}:\n\t{str(unprocessed_rule)}\n")

    return len(matching_rules)


def byquery(query, produce_if_not_found=True, parent_recursion=False, skip_entry_names=None, __entry__=None):
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

    parsed_query        = FilterPile( query, "Query" )
    if not parsed_query.filter_list:
        logging.debug(f"[{__entry__.get_name()}] the query was empty => returning None")
        return None

    # trying to match the Query in turn against each existing and walkable entry, first match returns:
    for candidate_entry in walk(__entry__, skip_entry_names):
        if parsed_query.matches_entry( candidate_entry, parent_recursion ):
            if candidate_entry.get('__completed', True):    # either explicitly completed, or not carrying this attribute at all, probably a static Entry
                return candidate_entry
            else:
                logging.info(f"[{__entry__.get_name()}] byquery({query}) found incomplete Entry {candidate_entry.get_name()} in {candidate_entry.get_path()} , which may either be in progress or dead - PLEASE INVESTIGATE")
                return None     # FIXME: we cannot yet distinguish between a botched installation and a still-running one

    # if a matching entry does not exist, see if we can produce it with a matching Rule
    if produce_if_not_found and len(parsed_query.posi_tag_set):
        logging.info(f"[{__entry__.get_name()}] byquery({query}) did not find anything, but there are tags: {parsed_query.posi_tag_set} , trying to find a producer...")

        matching_rules = find_matching_rules(parsed_query, __entry__)
        logging.info(f"[{__entry__.get_name()}] A total of {len(matching_rules)} matched rules found.\n")

        match_idx = 0
        for advertising_entry, unprocessed_rule, parsed_rule in matching_rules:
            match_idx += 1  # matches are 1-based
            logging.info(f"Matched Rule #{match_idx}/{len(matching_rules)}: {unprocessed_rule[0]} from Entry '{advertising_entry.get_name()}'...")

            rule_vector         = advertising_entry.nested_calls(unprocessed_rule)
            producer_pipeline   = rule_vector[1]
            extra_params        = rule_vector[2] if len(rule_vector)>2 else {}
            export_params       = rule_vector[3] if len(rule_vector)>3 else []

            cumulative_params = advertising_entry.slice( *export_params )   # default slice
            cumulative_params["__query"] = query                            # NB: unparsed query in its original format, DANGER!
            cumulative_params.update( parsed_rule.opti_val_dict )           # optional matches on top (may override some defaults)
            cumulative_params.update( deepcopy( extra_params ) )            # extra_params on top (may override some defaults)
            cumulative_params.update( parsed_rule.posi_val_dict )           # rules on top (may override some defaults)
            cumulative_params.update( parsed_query.posi_val_dict )          # query on top (may override some defaults)
            cumulative_params["tags"] = list(parsed_query.posi_tag_set)     # FIXME:  parsed_rule.posi_tag_set should include it
            if type(produce_if_not_found)==dict:
                cumulative_params.update( produce_if_not_found )            # highest priority override only in case there was no match and we are generating
            cumulative_params["__cumulative_param_names"] = list( cumulative_params.keys() )
            logging.info(f"Pipeline: {producer_pipeline}, Cumulative params: {cumulative_params}")

            if type(producer_pipeline[0])==list:
                new_entry = advertising_entry.execute(producer_pipeline, cumulative_params)
            elif len(producer_pipeline)<3:
                producer_call_params_iter   = iter(producer_pipeline)
                producer_action_name        = next(producer_call_params_iter)
                producer_pos_params         = next(producer_call_params_iter, [])
                new_entry                   = advertising_entry.call( producer_action_name, producer_pos_params, cumulative_params )
            else:
                raise SyntaxError(f"Rule parsing error: a single-call action with its own named parameters is ambiguous: {producer_pipeline}")

            if new_entry:
                if not isinstance(new_entry, type(__entry__)):
                    raise RuntimeError( f"Matched Rule #{match_idx}/{len(matching_rules)} produced something ( {repr(new_entry)} ), which is not an Entry - PLEASE INVESTIGATE" )
                elif parsed_query.matches_entry( new_entry, parent_recursion ):
                    logging.info(f"Matched Rule #{match_idx}/{len(matching_rules)} produced an entry, which matches the original query, finalizing...\n")
                    if not new_entry.get("__completed", True):
                        new_entry.save( on_collision="force", completed=ufun.generate_current_timestamp() )   # we expect a collision
                    return new_entry
                else:
                    raise RuntimeError( f"Matched Rule #{match_idx}/{len(matching_rules)} produced an entry, but it failed to match the original query {query} - PLEASE INVESTIGATE" )
            else:
                logging.info(f"Matched Rule #{match_idx}/{len(matching_rules)} didn't produce a result, {len(matching_rules)-match_idx} more matched rules to try...\n")

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
        return __entry__.save( on_collision="force", completed=ufun.generate_current_timestamp() )   # we expect a collision


def remove_entry_name(old_entry_name, __entry__):

    contained_entries       = __entry__.pluck(['contained_entries', old_entry_name])
    return __entry__.save( on_collision="force", completed=ufun.generate_current_timestamp() )   # we expect a collision


if __name__ == '__main__':

    print("Unfortunately this entry cannot be tested separately from the framework")


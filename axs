#!/usr/bin/env python3

""" A simple CommandLine API for this framework.
"""

import getpass
import json
import logging
import os
import re
import socket
import sys

log_indocker = 'inDocker:' if os.path.exists('/.dockerenv') else ''
log_username = getpass.getuser()
log_hostname = socket.gethostname()

logging.basicConfig(level=logging.INFO, format=f"%(levelname)s:{log_indocker}{log_username}@{log_hostname} %(filename)s:%(funcName)s:%(lineno)s %(message)s")
#logging.basicConfig(level=logging.DEBUG, format=f"%(levelname)s:{log_username}@{log_hostname} %(filename)s:%(funcName)s:%(lineno)s %(message)s") # put this BEFORE IMPORTING the kernel to see logging from the kernel

from function_access import to_num_or_not_to_num
from kernel import default_kernel as ak

def cli_parse(arglist):
    """Parse the command pipeline representing a chain of calls

    The expected format is:
        [<label>:] <action_name> [<pos_param>]* [<opt_param>]* [, <action_name> [<pos_param>]* [<opt_param>]*]*

        Positional parameters can have the following formats:
            ---='{"hello": "world"}'        # parsed JSON
            --,=abc,123,def                 # comma-separated list ["abc", 123, "def"]
            --,                             # empty list
            free_word                       # string or number

        Optional parameters can have the following formats:
            --alpha                         # boolean True
            --beta-                         # boolean False
            --gamma=                        # scalar empty string
            --delta=1234                    # scalar number
            --epsilon=hello                 # scalar string
            --zeta,=tag1,tag2,tag3          # 1D list (can be split on a comma, a colon: or a space )
            --zeta_2d,:=x:10,y:20,z:30      # 2D list (first delimiter between 1D lists, second delimiter within 1D lists)
            --zeta_dict,::=x:10,y:20,z:30   # full dictionary (first delimiter between pairs, second delimiter between a key and a value)
            --eta.theta                     # dictionary boolean True value
            --iota.kappa-                   # dictionary boolean False value
            --lambda.mu=                    # dictionary empty string value
            --nu.xi=omicron                 # dictionary scalar value (number or string)
            --pi.rho,=tag1,tag2,tag3        # dictionary that contains a list
            ---xyz='[{"pq":"rs"},123]'      # parsed JSON

        Named parameters (using the syntax for optional) can be "augmented" in different ways, depending on the type of original data:
            --alpha+=10                     # numeric: addition; list: append
            --beta.gamma+,=20,30            # list: extend
            --delta.epsilon+,::=x:40,y:50   # dictionary: merge
    """


    pipeline = []
    i = 0

    while i<len(arglist):

        if arglist[i]==',':     # just skip the pipeline link separator
            i += 1
        elif arglist[i].startswith(','):
            insert_position = to_num_or_not_to_num(arglist[i][1:])
            pipeline.append( insert_position )
            i += 1

        call_params     = {}
        call_pos_params = []
        curr_link       = []
        pipeline.append( curr_link )

        ## Going through the arguments
        while i<len(arglist) and not arglist[i].startswith(','):
            if not arglist[i].startswith('--'):
                matched = re.match(r'^(\^{1,2})(\w+)(([:,\ /;=]).*)?$', arglist[i])   # a nested action
                if matched:
                    delimiter = matched.group(4)
                    call_pos_params.append( [ matched.group(1), matched.group(2), [to_num_or_not_to_num(el) for el in matched.group(3).split(delimiter)[1:] ] if delimiter else [] ] )

                    if len(curr_link)==0:          # no action has been parsed yet
                        curr_link.extend( [ 'noop', call_pos_params, call_params ] )
                elif len(curr_link)==0:
                    if re.match(r'^(\w*):(?:(\w*):)?$', arglist[i]):                # input and/or output label(s)
                        matched = re.match(r'^(\w*):(?:(\w*):)?$', arglist[i])
                        curr_link.extend( [ None, call_pos_params, call_params, matched.group(1), matched.group(2) ] )
                    elif re.match(r'^(?:\.[\w\-]*\.)?(?:\w+\.)*\w+$', arglist[i]):                      # a normal action (qualified or local)
                        curr_link.extend( [ arglist[i], call_pos_params, call_params ] )
                    else:
                        raise(Exception("Parsing error - cannot understand non-option '{}' before an action".format(arglist[i])))
                elif curr_link[0] is None and re.match(r'^(?:\.[\w\-]*\.)?(?:\w+\.)*\w+$', arglist[i]): # a normal action (qualified or local) after input/output label(s)
                    curr_link[0] = arglist[i]
                else:
                    call_pos_params.append( to_num_or_not_to_num(arglist[i]) )      # a positional argument

            else:
                matched = re.match(r'^---(([\w\.]*\+?)((\^{1,2})(\w+))?)=(.*)$', arglist[i])                    # verbatim JSON value
                if matched:
                    call_param_json     = matched.group(6)
                    call_param_value    = json.loads( call_param_json )
                else:
                    matched = re.match(r'^--(([\w\.]*\+?)((\^{1,2})(\w+))?)([\ ,;:/]{0,3})(#?)=(.*)$', arglist[i])  # scalar value, list, list-of-lists or dictionary
                    if matched:
                        delimiters          = list(matched.group(6))
                        substitute_first    = matched.group(7)
                        call_param_value    = matched.group(8)

                        if substitute_first:
                            call_param_value    = [ '^^', 'substitute', call_param_value ]
                        elif len(delimiters)==3 and delimiters[1]==delimiters[2]:     # a dictionary
                            call_param_value    = dict([ [ to_num_or_not_to_num(elem) for elem in group.split(delimiters[1]) ] for group in call_param_value.split(delimiters[0]) ])
                        elif len(delimiters)==2:                                    # a 2D list
                            call_param_value    = [ [ to_num_or_not_to_num(elem) for elem in group.split(delimiters[1]) ] for group in call_param_value.split(delimiters[0]) ]
                        elif len(delimiters)==1:                                    # a 1D list
                            call_param_value    =   [ to_num_or_not_to_num(elem) for elem in call_param_value.split(delimiters[0]) ]
                        else:                                                       # a scalar
                            call_param_value    =     to_num_or_not_to_num(call_param_value)
                    else:
                        matched = re.match(r'^--(([\w\.]*)((\^{1,2})(\w+))?)([,+-]?)$', arglist[i])     # empty list or bool value
                        if matched:
                            if matched.group(6) == ',':
                                call_param_value    = []                        # the way to express an empty list
                            else:
                                call_param_value    = matched.group(6) != '-'   # boolean True or False

                if matched:
                    if matched.group(3):    # if there was a nested action
                        call_param_value = [ matched.group(4), matched.group(5), call_param_value ]

                    if matched.group(2):    # if option name was present
                        call_params[matched.group(2)] = call_param_value
                    else:
                        call_pos_params.append( call_param_value )

                else:
                    raise(Exception("Parsing error - cannot understand option '{}'".format(arglist[i])))
            i += 1

    return pipeline


def main():
    pipeline = cli_parse(sys.argv[1:])
#    from pprint import pprint
#    pprint(pipeline)
    try:
        return ak.execute(pipeline)
    except RuntimeError as e:
        logging.error(f"RuntimeError: {e}")

if __name__ == '__main__':
    print(ak.pickle_struct(main()))

#!/usr/bin/env python3

""" A simple CommandLine API for this framework.
"""

import json
import logging
import re
import sys

from function_access import to_num_or_not_to_num

def cli_parse(arglist):
    """Parse the command pipeline representing a chain of calls

    The expected format is:
        <action_name> [<pos_param>]* [<opt_param>]* [, <action_name> [<pos_param>]* [<opt_param>]*]*

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
            --zeta,=tag1,tag2,tag3          # list (can be split on a comma, a colon: or a space )
            --eta.theta                     # dictionary boolean True value
            --iota.kappa-                   # dictionary boolean False value
            --lambda.mu=                    # dictionary empty string value
            --nu.xi=omicron                 # dictionary scalar value (number or string)
            --pi.rho,=tag1,tag2,tag3        # dictionary that contains a list
            ---xyz='[{"pq":"rs"},123]'      # parsed JSON
    """


    pipeline = []
    i = 0

    while i<len(arglist):

        if arglist[i]==',':     # just skip the pipeline link separator
            i += 1

        call_params     = {}
        call_pos_params = []
        call_pos_preps  = []
        curr_link = [ None, call_pos_params, call_params, call_pos_preps ]
        pipeline.append( curr_link )

        ## Going through the parameters
        while i<len(arglist) and not arglist[i].startswith(','):
            call_param_prep = ''

            if not arglist[i].startswith('--'):
                if curr_link[0]==None:  # no action has been parsed yet
                    if re.match(r'^\w+$', arglist[i]):  # normal action
                        curr_link[0] = arglist[i]
                    else:                               # a "guess me" action
                        curr_link[0] = 'noop'
                        call_pos_preps.append( arglist[i][0] )
                        call_pos_params.append( arglist[i][1:] )
                else:   # a regular positional param
                    call_pos_preps.append( call_param_prep )
                    call_pos_params.append( to_num_or_not_to_num(arglist[i]) )
            else:
                call_param_key  = None

                matched_json_param = re.match('^---(([\w\.]*)(\^{1,2}\w+)?)=(.*)$', arglist[i])
                if matched_json_param:
                    if matched_json_param.group(2):
                        call_param_key      = matched_json_param.group(1)
                    else:
                        call_param_prep     = matched_json_param.group(3)

                    call_param_json     = matched_json_param.group(4)
                    call_param_value    = json.loads( call_param_json )
                else:
                    matched_parampair = re.match('^--(([\w\.]*)(\^{1,2}\w+)?)([\ ,;:]?)=(.*)$', arglist[i])
                    if matched_parampair:
                        if matched_parampair.group(2):
                            call_param_key  = matched_parampair.group(1)
                        else:
                            call_param_prep = matched_parampair.group(3)

                        delimiter           = matched_parampair.group(4)
                        call_param_value    = matched_parampair.group(5)

                        if delimiter:
                            call_param_value    = [to_num_or_not_to_num(el) for el in call_param_value.split(delimiter)]
                        else:
                            call_param_value    = to_num_or_not_to_num(call_param_value)
                    else:
                        matched_paramsingle = re.match('^--(([\w\.]*)(\^{1,2}\w+)?)([,+-]?)$', arglist[i])
                        if matched_paramsingle:
                            if matched_paramsingle.group(2):
                                call_param_key  = matched_paramsingle.group(1)
                            else:
                                call_param_prep = matched_paramsingle.group(3)

                            if matched_paramsingle.group(4) == ',':
                                call_param_value    = []                                    # the way to express an empty list
                            else:
                                call_param_value    = matched_paramsingle.group(4) != '-'   # boolean True or False

                if call_param_key:
                    call_params[call_param_key] = call_param_value
                elif call_param_prep:
                    call_pos_preps.append( call_param_prep )
                    call_pos_params.append( call_param_value )
                else:
                    raise(Exception("Parsing error - cannot understand '{}'".format(arglist[i])))
            i += 1

    return pipeline


def main():
    #logging.basicConfig(level=logging.DEBUG, format="%(levelname)s:%(funcName)s %(message)s")   # put this BEFORE IMPORTING the kernel to see logging from the kernel

    from kernel import default_kernel as ak

    pipeline = cli_parse(sys.argv[1:])
    return ak.execute(pipeline)

if __name__ == '__main__':
    print(main())

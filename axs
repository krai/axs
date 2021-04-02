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

        You can use as many positional params as possible while their values are scalars.
        However as soon as you need to define a structure, a switch to optional param syntax will be necessary.

        Optional params can represent a lot of things:
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

        call_params = {}
        call_pos_params = []
        curr_link = ( arglist[i], call_pos_params, call_params )
        i += 1
        pipeline.append( curr_link )

        ## Going through the parameters
        while i<len(arglist) and not arglist[i].startswith(','):
            if not arglist[i].startswith('--'):
                call_pos_params.append( to_num_or_not_to_num(arglist[i]) )
            else:
                call_param_key = None

                matched_json_param = re.match('^---([\*#]?\w+)=(.*)$', arglist[i])
                if matched_json_param:
                    call_param_key      = matched_json_param.group(1)
                    call_param_json     = matched_json_param.group(2)
                    call_param_value    = json.loads( call_param_json )
                else:
                    matched_parampair = re.match('^--(#?[\w\.]+)([\ ,;:]?)=(.*)$', arglist[i])
                    if matched_parampair:
                        call_param_key      = matched_parampair.group(1)
                        delimiter           = matched_parampair.group(2)
                        call_param_value    = matched_parampair.group(3)
                        if delimiter:
                            call_param_value    = [to_num_or_not_to_num(el) for el in call_param_value.split(delimiter)]
                        else:
                            call_param_value    = to_num_or_not_to_num(call_param_value)
                    else:
                        matched_paramsingle = re.match('^--([\w\.]+)([,-]?)$', arglist[i])
                        if matched_paramsingle:
                            call_param_key      = matched_paramsingle.group(1)
                            if matched_paramsingle.group(2) == ',':
                                call_param_value    = []                                    # the way to express an empty list
                            else:
                                call_param_value    = matched_paramsingle.group(2) != '-'   # either boolean True or False

                if call_param_key:
                    call_params[call_param_key] = call_param_value
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

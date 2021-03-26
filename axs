#!/usr/bin/env python3

""" A simple, one-call CommandLine API for this framework.
"""

import logging
import re
import sys

def cli_parse(arglist):
    """Parse the command line representing a single call:

    The expected format is:
        <entry_name> <action_name> [<pos_param>]* [<opt_param>]*

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
    """

    def to_num_or_not_to_num(x):
        "Convert the parameter to a number if it looks like it"

        try:
            x_int = int(x)
            if type(x_int)==int:
                return x_int
        except:
            try:
                x_float = float(x)
                if type(x_float)==float:
                    return x_float
            except:
                pass

        return x


    def traverset(dictionary, key_path, value):
        last_syllable = key_path.pop()          # in the edge case of one element, the list becomes empty after popping

        dict_ptr = dictionary
        for key_syllable in key_path:
            if key_syllable not in dict_ptr:    # explicit path vivification
                dict_ptr[key_syllable] = {}
            dict_ptr = dict_ptr[key_syllable]   # iterative descent

        dict_ptr[last_syllable] = value



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

                matched_parampair = re.match('^--([\w\.]+)([\ ,;:]?)=(.*)$', arglist[i])
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

    pipeline    = cli_parse(sys.argv[1:])
    results     = ak    # start from the kernel, continue with other entries
    for link_id, kernel_link in enumerate(pipeline):
        results = results.call(*kernel_link)

    return results


if __name__ == '__main__':
    print(main())

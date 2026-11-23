#!/usr/bin/env python3

"""axs04: the command line interface.

Parses the command line into a pipeline of calls, executes it starting from the kernel Entry (see execute()),
and prints the result, with every Entry shown as the command line that would load it again (see pickle_struct()).

    axs <action> [<argument>]* [, <action> [<argument>]*]*

Arguments:
    free_word                       a positional argument: a number if it looks like one, otherwise a string ("42" stays a string)
    ---=JSON                        a positional argument given as JSON
    --,=a,b,c                       a positional list (the delimiter can be any of: , : ; / or a space)
    --,                             a positional empty list
    --name=value  --name=           a named argument: a number or a string (here, empty)
    --name  --name+  /  --name-     a named boolean: True / False
    ---name=JSON                    a named argument given as JSON (---name=null gives None)
    --name,=a,b,c                   a named list (any of the delimiters above)
    --name,                         a named empty list
    --name,:=x:10,y:20              a named 2D list (the first delimiter separates the rows, the second their elements)
    --name,::=x:10,y:20             a named dictionary (the first delimiter separates the pairs, the second each key from its value)

Named arguments can also edit, instead of replacing, the value the call sees (see ActionSource.call()):
    --colour.green=255              plant a value at a path inside it (with any of the value forms above)
    --greek+=gamma  --greek+,=a,b   augment it (append to a list, top up a dictionary, add to a number or a string)

Between the calls of a pipeline:
    ,                               the next call is made on the result of the previous one
    , ,                             the next call is made on the kernel Entry again
    ,-                              the next call is made on the object of the previous call, discarding its result
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))     # the kernel's Python files live next to this script

from stored_entry import kernel, pickle_struct


def to_num_or_not_to_num(text):
    """Convert a string into an int or a float if it looks like one. A string in double quotes stays a string, without the quotes.
    """
    if len(text)>1 and text.startswith('"') and text.endswith('"'):
        return text[1:-1]
    for number_type in (int, float):
        try:
            return number_type(text)
        except ValueError:
            pass
    return text


def parse_delimited(delimiters, text):
    """Parse the text of an argument according to the delimiters that preceded its '=':
        none: a scalar; one: a list; two: a 2D list; three with the last two equal: a dictionary.
    """
    if len(delimiters)==0:
        return to_num_or_not_to_num(text)
    elif len(delimiters)==1:
        return [ to_num_or_not_to_num(element) for element in text.split(delimiters[0]) ]
    elif len(delimiters)==2:
        return [ [ to_num_or_not_to_num(element) for element in row.split(delimiters[1]) ] for row in text.split(delimiters[0]) ]
    elif len(delimiters)==3 and delimiters[1]==delimiters[2]:
        return dict( [ to_num_or_not_to_num(element) for element in pair.split(delimiters[1], 1) ] for pair in text.split(delimiters[0]) )
    raise ValueError(f"Cannot understand the delimiters '{delimiters}'")


def parse_call(tokens):
    """Parse the tokens of one call into [action_name, pos_params, named_params].
    """
    action_name = tokens[0]
    if not re.match(r'^\w+$', action_name):
        raise ValueError(f"Cannot understand '{action_name}' as an action name")
    pos_params, named_params = [], {}

    for token in tokens[1:]:
        if not token.startswith('--'):
            name, value = None, to_num_or_not_to_num(token)
        elif re.match(r'^---([\w.]*\+?)=(.*)$', token, re.DOTALL):
            matched = re.match(r'^---([\w.]*\+?)=(.*)$', token, re.DOTALL)
            name, value = matched.group(1), json.loads(matched.group(2))
        elif re.match(r'^--([\w.]*\+?)([ ,;:/]{0,3})=(.*)$', token, re.DOTALL):
            matched = re.match(r'^--([\w.]*\+?)([ ,;:/]{0,3})=(.*)$', token, re.DOTALL)
            name, value = matched.group(1), parse_delimited(matched.group(2), matched.group(3))
        elif re.match(r'^--([\w.]*)([,+-]?)$', token):
            matched = re.match(r'^--([\w.]*)([,+-]?)$', token)
            name, value = matched.group(1), ([] if matched.group(2)==',' else matched.group(2)!='-')
        else:
            raise ValueError(f"Cannot understand the option '{token}'")

        if name:
            named_params[name] = value
        else:
            pos_params.append(value)

    return [ action_name, pos_params, named_params ]


def cli_parse(arglist):
    """Parse a command line (as a list of arguments) into a pipeline for execute().
    """
    pipeline, call_tokens = [], []

    for token in arglist:
        if token in (',', ',-'):
            if call_tokens:
                pipeline.append( parse_call(call_tokens) )
                call_tokens = []
            elif token==',' and pipeline and pipeline[-1]!='-':
                pipeline.append( [] )       # " , , ": an empty call between two separators means "back to the kernel Entry"
            if token==',-':
                pipeline.append( '-' )
        else:
            call_tokens.append(token)

    if call_tokens:
        pipeline.append( parse_call(call_tokens) )
    return pipeline


def main():
    result = pickle_struct( kernel().execute( cli_parse(sys.argv[1:]) ) )
    try:
        print( result )
        sys.stdout.flush()
    except BrokenPipeError:     # the reader (say, head) stopped early: not an error worth a traceback
        os.dup2( os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno() )


if __name__ == '__main__':
    main()

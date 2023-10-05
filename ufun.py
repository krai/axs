#!/usr/bin/env python3

"A collection of utility functions"

import errno
import json
import os
import re
import shutil
import stat
import sys

def load_json(json_file_path):
    """Load a data structure from given JSON file.

Usage examples :
                axs func ufun.load_json ab.json , keys ,0 func list
                axs byquery program_output,task=object_detection,framework=onnxrt,model_name=ssd_resnet34,num_of_images=5 , get_path_from output_file_name ,0 func ufun.load_json
    """
    with open( json_file_path, encoding='utf-8' ) as json_fd:
        try:
            data_structure = json.load(json_fd)
        except json.decoder.JSONDecodeError as e:
            print(f'Error parsing "{json_file_path}" : {e}', file=sys.stderr)
            data_structure = {}

        return data_structure


def save_json(data_structure, json_file_path, indent=None):
    """Store a data structure in a JSON file.

Usage examples :
                axs func ufun.save_json ---='{"hello":"world"}' hello.json
                axs work_collection , get contained_entries , keys ,0 func list ,0 func ufun.save_json work_entries.json
    """
    json_string   = json.dumps( data_structure , indent=indent)

    with open(json_file_path, "w") as json_fd:
        json_fd.write( json_string+"\n" )

    return json_string


def rematch(input_string, regex, group=1):
    """Find a substring matching a given regular expression and return it

Usage examples :
                axs byname kernel_python_tool , run ,0 func ufun.rematch '^Python\s((\d+)\.(\d+))\.\d+'    # parse the major.minor version from Python
    """
    searchObj = re.search(regex, input_string, re.MULTILINE)
    if searchObj:
        if group>0:
            return searchObj.group(group)
        else:
            return True
    else:
        print(f'Failed to match "{input_string}" against "{regex}"', file=sys.stderr)
        return False


def fs_find(top_dir, regex, looking_for_dir=False, return_full=False, topdown=True):
    """Find a file or directory by regex in top_dir, return the list of all matches. Note: it must be Python's regex, not Shell's!

Usage examples :
                axs byquery extracted,imagenet , get_path ,0 func ufun.fs_find 'ILSVRC2012_val_\d+.JPEG' , __getitem__ 0
    """
    containing_subdirs = []
    for dirpath,dirnames,filenames in os.walk(top_dir, topdown=topdown):
        candidate_list = dirnames if looking_for_dir else filenames
        for candidate_name in candidate_list:
            if re.match(regex, candidate_name):
                containing_subdirs.append( os.path.join(dirpath, candidate_name) if return_full else dirpath )
                break

    return containing_subdirs


def join_with(things, separator=' '):
    """Reverse the order of arguments for String.join() to simplify its use in pipelines

Usage examples :
                axs work_collection , get contained_entries , keys ,0 func ufun.join_with
                axs noop --,=ab,cd,ef ,0 func ufun.join_with $'\n'      # note Bash-specific syntax for passing a carriage return
    """
    return separator.join(things)


def rmdir(dir_path):
    """Recursively remove a non-empty directory

Usage examples :
                axs func ufun.rmdir path/to/remove
    """
    #   Thanks for this SO entry:
    #       https://stackoverflow.com/questions/1213706/what-user-do-python-scripts-run-as-in-windows
    #
    def handleRemoveReadonly(func, path, exc):
        if func in (os.rmdir, os.remove) and exc[1].errno == errno.EACCES:
            os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO) # 0777
            func(path)
        else:
            raise

    shutil.rmtree(dir_path, ignore_errors=False, onerror=handleRemoveReadonly)


def is_in(candidate, iterable):
    """Check if element is TRULY contained in the iterable.

Note that the following are true in Python:
    1==True
    0==False
    True in [1]
    1 in [True]
    False in [0]
    0 in [False]

So to account for the difference between (1 and True) and between (0 and False), we employ or own containment check.

Usage examples :
                axs func ufun.is_in 0 ---='[false,2,4]'
                axs func ufun.is_in --- ---='[false,2,4]'
                axs func ufun.is_in 1 ---='[0,true,4]'
                axs func ufun.is_in --+ ---='[0,true,4]'
    """
    for element in iterable:
        if candidate is element:
            return True
    return False


def augment(orig_structure, diff):
    """Apply a simple 1-arg editing uperation to a data structure

Usage examples :
                axs func ufun.augment 100 -23                   # add two numbers
                axs func ufun.augment abcd efg                  # concatenate two strings
                axs func ufun.augment --,=10,20,30 40           # add an element to the list
                axs func ufun.augment --,=10,20,30 --,=40,50    # concatenate two lists
    """

    if type(orig_structure)==dict:
        return {**orig_structure, **diff}                   # dictionary top-up
    elif type(orig_structure)==list and type(diff)!=list:
        return orig_structure + [ diff ]                    # list top-up with an element
    else:
        return orig_structure + diff                        # list top-up with another list  OR  string concatenation  OR  adding numbers


def repr_dict(d, exception_pairs=None):
    """A safer way to print a dictionary that may contain 1st-level references to self or self-containing objects.
        Note exception_pairs has to be a list of pairs.
    """
    exception_pairs = exception_pairs or []

    def safe_value(v):
        for (exception_v, safe_v) in exception_pairs:
            if v==exception_v:
                return safe_v
        return repr(v)

    return ('{' + (','.join([ repr(k)+':'+safe_value(d[k]) for k in sorted(d.keys()) ])) + '}') if type(d)==dict else repr(d)

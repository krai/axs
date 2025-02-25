#!/usr/bin/env python3

"A collection of utility functions"

import datetime
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


def rematch(input_string, regex, grab=1):
    """Find a substring matching a given regular expression and return it

Usage examples :
                axs byname kernel_python_tool , run ,0 func ufun.rematch '^Python\s((\d+)\.(\d+))\.\d+'     # parse the major.minor version from Python

                axs func ufun.rematch A2B34C56 'A(\d)B(\d\d)C(\d)' --,=alpha,beta,gamma                     # parse multiple fields into a dictionary
    """
    searchObj = re.search(regex, input_string, re.MULTILINE)
    if searchObj:
        if not grab:
            return True
        elif type(grab)==list:
            return { grab[i] : searchObj.group(i+1) for i in range(len(grab)) }
        else:
            return searchObj.group(grab)

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


def generate_index(collection_path=".", is_work_collection=False):
    """Find a non-recursive list of directories that are contained in a given directory
        and turn it into an index structure compatible with "contained_entries"

Usage examples :
                axs func ufun.generate_index $HOME/work_collection --+ ,0 func json.dumps --indent=8
    """

    contained_entry_names = []
    for entry_name in os.listdir( collection_path ):
        if os.path.isdir( os.path.join(collection_path, entry_name)) and not entry_name.startswith('.'):
            contained_entry_names.append( entry_name )

    generated_index = { "core_collection": [ "^", "execute", [[ [ "core_collection" ], [ "get_path" ] ]] ] } if is_work_collection else {}

    generated_index.update( { entry_name: entry_name for entry_name in contained_entry_names } )

    return generated_index


def join_with(things, separator=' '):
    """Reverse the order of arguments for String.join() to simplify its use in pipelines

Usage examples :
                axs work_collection , get contained_entries , keys ,0 func ufun.join_with
                axs noop --,=ab,cd,ef ,0 func ufun.join_with $'\n'      # note Bash-specific syntax for passing a carriage return
    """
    return separator.join( [ str(thing) for thing in things ] )


def rmdir(dir_path):
    """Recursively remove a non-empty directory or file

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

    if os.path.isdir( dir_path ):
        shutil.rmtree(dir_path, ignore_errors=False, onerror=handleRemoveReadonly)
    else:
        os.remove( dir_path )


def move_dir_contents_from_to(source_dir, dest_dir):

    all_filenames = os.listdir(source_dir)

    for filename in all_filenames:
        source_path = os.path.join(source_dir, filename)
        dest_path   = os.path.join(dest_dir, filename)
        shutil.move(source_path, dest_path)


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
    candidate_type = type(candidate)
    for element in iterable:
        if candidate_type==type(element) and candidate==element:
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


def edit_structure(struct_ptr, key_path, value=None, edit_mode='ASSIGN'):

    last_idx = len(key_path)-1
    for key_idx, key_syllable in enumerate(key_path):

        if type(struct_ptr)==list:  # descend into lists with numeric indices
            key_syllable = int(key_syllable)
            padding_size = key_syllable-len(struct_ptr)+1
            struct_ptr.extend([None]*(padding_size-1))  # explicit list vivification
            if padding_size>0:
                struct_ptr.append({})
        elif key_syllable not in struct_ptr:
            struct_ptr[key_syllable] = {}               # explicit dict vivification

        if key_idx<last_idx:
            struct_ptr = struct_ptr[key_syllable]       # iterative descent
        elif edit_mode == 'PLUCK':
            struct_ptr.pop(key_syllable)
        elif edit_mode == 'AUGMENT':
            prev_value = struct_ptr[key_syllable]
            struct_ptr[key_syllable] = augment( prev_value, value )
        elif edit_mode == 'ASSIGN':
            struct_ptr[key_syllable] = value

    return struct_ptr


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


def generate_current_timestamp(time_format=None, fs_safe=True):
    """Generate the current timestamp in a readable format

Usage examples :
                axs func ufun.generate_current_timestamp                # safe to use in a filename by default
                axs func ufun.generate_current_timestamp --fs_safe-     # colon as time separator is more readable, but not suitable for filenames
                axs func ufun.generate_current_timestamp "%Y.%m.%d"     # an arbitrary timestamp format
    """
    time_format = time_format or ("%Y.%m.%d_%Hh%Mm%Ss" if fs_safe else "%Y.%m.%d_%H:%M:%S")

    return datetime.datetime.now().strftime( time_format )

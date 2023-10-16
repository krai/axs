#!/usr/bin/env python3

""" This entry knows how to download git repositories.
    They may either become collections or regular entries.
"""

import os
import logging

import ufun


def propose_checkout(current_checkout):
    """Cannot use "case" in data_axs.json due to the current bug (clash of nested "case"-s), so implementing in code_axs.py :
    """
    if current_checkout.startswith("mlperf_"):
        return current_checkout
    else:
        return None


def url_2_repo_name(url=None):
    """Cut the repo_name out of the URL, if given.

Usage examples :
                axs byname git , get repo_name --url=https://hello.world/repo/long_name.git
                axs byname git , get url --repo_name=short_name
    """
    if url:
        repo_name = os.path.basename( url )
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]          # trim it off

        return repo_name
    else:
        return None


def clone(repo_name=None, url=None, rel_clone_dir=None, generated_entry=None, move_on_up=True, git_tool_entry=None, checkout=None, submodules=False, abs_patch_path=None, patch=None, tags=None, contained_files=None, __entry__=None):
    """Clone a git repository into an Entry,

Usage examples :
                axs byname git , clone --repo_name=counting_collection
            # or
                axs byname git , clone --url=https://github.com/ens-lg4/counting_collection
            # or
                axs byquery git_repo,collection,repo_name=axs2mlperf                                                    # default url_prefix
            # or
                axs byquery git_repo,collection,repo_name=counting_collection,url_prefix=https://github.com/ens-lg4     # specific url_prefix

Clean-up:
                axs byname counting_collection , remove
    """

    assert __entry__ != None, "__entry__ should be defined"

    generated_entry_path    = generated_entry.get_path( "" )
    tool_path               = git_tool_entry["tool_path"]

    logging.warning(f"The resolved git_tool_entry '{git_tool_entry.get_name()}' located at '{git_tool_entry.get_path()}' uses the shell tool '{tool_path}'")

    retval = git_tool_entry.call('run', f"\"{tool_path}\" -C \"{generated_entry_path}\" clone {url} {rel_clone_dir}", {"capture_output": False} )
    if retval == 0:

        abs_clone_dir = os.path.join(generated_entry_path, rel_clone_dir)

        if checkout:
            git_tool_entry.call('run', f"\"{tool_path}\" -C \"{abs_clone_dir}\" checkout \"{checkout}\"" )

        if submodules:
            git_tool_entry.call('run', f"\"{tool_path}\" -C \"{abs_clone_dir}\" submodule init" )
            git_tool_entry.call('run', f"\"{tool_path}\" -C \"{abs_clone_dir}\" submodule update" )

        if abs_patch_path:
            patch_tool_entry = __entry__['patch_tool_entry']
            logging.warning(f"The resolved patch_tool_entry '{patch_tool_entry.get_name()}' located at '{patch_tool_entry.get_path()}' uses the shell tool '{patch_tool_entry['tool_path']}'")

            retval = patch_tool_entry.call('run', [], { 'entry_path': abs_clone_dir, 'abs_patch_path': abs_patch_path} )
            if retval != 0:
                logging.error(f"could not patch \"{abs_clone_dir}\" with \"{abs_patch_path}\", bailing out")
                return None

        if move_on_up:
            ufun.move_dir_contents_from_to( abs_clone_dir, generated_entry_path )
            ufun.rmdir( abs_clone_dir )
        else:
            generated_entry['file_name'] = rel_clone_dir
            generated_entry.save()

        return generated_entry

    else:
        logging.error(f"A problem (retval={retval}) occured when trying to clone '{repo_name}' at {url} , bailing out")
        return None


def pull(repo_path, git_tool_entry, __entry__=None):
    """Pull the repository contained in an entry.

Usage examples :
                axs byname counting_collection , pull

                axs byname git , pull `axs core_collection , get_path`
    """
    tool_path       = git_tool_entry["tool_path"]
    git_tool_entry.call('run', f"\"{tool_path}\" -C \"{repo_path}\" pull --ff-only" )

    return __entry__

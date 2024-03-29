#!/usr/bin/env python3

""" This entry knows how to download and query git repositories.
    They may either become collections or regular entries.

Usage examples :
    # obtain the URL of the kernel's repository:
            axs byname git , get git_url

    # obtain the URL of a given repository:
            axs byname axs2mlperf , get git_url

    # obtain the URL of a given repository using query:
            axs byquery git_repo,collection,repo_name=axs2mlperf , get git_url

    # obtain the checkout (branch or tag) of the kernel's repository:
            axs byname git , get current_checkout

    # obtain the checkout (branch or tag) of a given repository:
            axs byname axs2mlperf , get current_checkout

    # obtain the checkout (branch or tag) of a given repository using query:
            axs byquery git_repo,collection,repo_name=axs2mlperf , get current_checkout
"""

import os
import logging

import ufun


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


def clone(repo_name=None, url=None, rel_clone_dir=None, newborn_entry=None, newborn_entry_path=None, move_on_up=True, checkout=None, submodules=False, abs_patch_path=None, patch=None, clone_options="", tags=None, contained_files=None, __entry__=None):
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

    retval = __entry__.call('run', [], { "cmd_key": "clone", "container_path": newborn_entry_path, "url": url, "clone_subdir": rel_clone_dir, "clone_options": clone_options, "capture_output": False } )
    if retval == 0:

        abs_clone_dir = os.path.join(newborn_entry_path, rel_clone_dir)

        if checkout:
            __entry__.call('run', [], { "cmd_key": "checkout", "repo_path": abs_clone_dir, "checkout": checkout } )

        if submodules:
            __entry__.call('run', [], { "cmd_key": "submodules_1", "repo_path": abs_clone_dir } )
            __entry__.call('run', [], { "cmd_key": "submodules_2", "repo_path": abs_clone_dir } )

        if abs_patch_path:
            patch_tool_entry = __entry__['patch_tool_entry']
            logging.warning(f"The resolved patch_tool_entry '{patch_tool_entry.get_name()}' located at '{patch_tool_entry.get_path()}' uses the shell tool '{patch_tool_entry['tool_path']}'")

            retval = patch_tool_entry.call('run', [], { 'entry_path': abs_clone_dir, 'abs_patch_path': abs_patch_path} )
            if retval != 0:
                logging.error(f"could not patch \"{abs_clone_dir}\" with \"{abs_patch_path}\", bailing out")
                return None

        if move_on_up:
            ufun.move_dir_contents_from_to( abs_clone_dir, newborn_entry_path )
            ufun.rmdir( abs_clone_dir )
        else:
            newborn_entry['file_name'] = rel_clone_dir
            if tags and 'collection' in tags:
                newborn_entry['contained_entries'] = { rel_clone_dir: rel_clone_dir }
            newborn_entry.save()

        return newborn_entry

    else:
        logging.error(f"A problem (retval={retval}) occured when trying to clone '{repo_name}' at {url} , bailing out")
        newborn_entry.remove()
        return None


def pull(repo_path,  __entry__=None):
    """Pull the repository contained in an entry.

Usage examples :
                axs byname counting_collection , pull

                axs byname git , pull `axs core_collection , get_path`
    """
#    __entry__.call('subst_run', "\"#{tool_path}#\" -C \"#{repo_path}#\" pull --ff-only", { 'repo_path': repo_path} )
    __entry__.call('run', [], { "cmd_key": "pull", "repo_path": repo_path} )

    return __entry__

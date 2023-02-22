#!/usr/bin/env python3

""" This entry knows how to download git repositories.
    They may either become collections or regular entries.
"""

import os
import logging


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


def clone(repo_name=None, url=None, repo_dir_name=None, git_tool_entry=None, container_entry=None, checkout=None, submodules=False, tags=None, __entry__=None):
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
    ak = __entry__.get_kernel()
    assert ak != None, "__entry__'s kernel should be defined"

    container_path  = container_entry.get_path('')
    entry_path      = container_entry.get_path( repo_dir_name )
    tool_path       = git_tool_entry["tool_path"]
    retval = git_tool_entry.call('run', f"\"{tool_path}\" -C \"{container_path}\" clone {url} {repo_dir_name}", {"capture_output": False} )
    if retval == 0:
        if checkout:
            git_tool_entry.call('run', f"\"{tool_path}\" -C \"{entry_path}\" checkout \"{checkout}\"" )

        if submodules:
            git_tool_entry.call('run', f"\"{tool_path}\" -C \"{entry_path}\" submodule init" )
            git_tool_entry.call('run', f"\"{tool_path}\" -C \"{entry_path}\" submodule update" )

        result_entry                = ak.bypath( entry_path )   # "discover" the Entry after cloning, then either create or augment the data
        result_entry['repo_name']   = repo_name
        result_entry['tags']        = tags or [ 'git_repo' ]
        if checkout:
            result_entry['checkout']    = checkout
        result_entry.attach( container_entry ).save()

        return result_entry

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

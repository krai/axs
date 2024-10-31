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


def clone(repo_name=None, url=None, env=None, rel_clone_dir=None, abs_result_path=None, cloned_axs_data_path=None, newborn_entry=None, newborn_entry_path=None, move_on_up=True, checkout=None, submodules=False, abs_patch_path=None, git_tool_entry=None, patch_tool_entry=None, clone_options="", tags=None, contained_files=None):
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

    assert git_tool_entry != None, "git_tool_entry should be defined"

    retval = git_tool_entry.call('run', [], { "cmd_key": "clone", "container_path": newborn_entry_path, "url": url, "env": env, "clone_subdir": rel_clone_dir, "clone_options": clone_options, "capture_output": False } )
    if retval == 0:

        if checkout:
            git_tool_entry.call('run', [], { "cmd_key": "checkout", "repo_path": abs_result_path, "checkout": checkout } )

        if submodules:
            git_tool_entry.call('run', [], { "cmd_key": "submodules_1", "repo_path": abs_result_path } )
            git_tool_entry.call('run', [], { "cmd_key": "submodules_2", "repo_path": abs_result_path } )

        if patch_tool_entry:
            logging.warning(f"The resolved patch_tool_entry '{patch_tool_entry.get_name()}' located at '{patch_tool_entry.get_path()}' uses the shell tool '{patch_tool_entry['tool_path']}'")

            retval = patch_tool_entry.call('run', [], { 'entry_path': abs_result_path, 'abs_patch_path': abs_patch_path} )
            if retval != 0:
                logging.error(f"could not patch \"{abs_result_path}\" with \"{abs_patch_path}\", bailing out")
                return None

        if os.path.exists( cloned_axs_data_path ):
            newborn_entry["contained_entries"] = ufun.load_json( cloned_axs_data_path )["contained_entries"]

        if move_on_up:
            ufun.move_dir_contents_from_to( abs_result_path, newborn_entry_path )
            ufun.rmdir( abs_result_path )
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


def pull(repo_path,  git_tool_entry, __entry__):
    """Pull the repository contained in an entry.

Usage examples :
                axs byname counting_collection , pull

                axs byname git , pull `axs core_collection , get_path`
    """
    retval = git_tool_entry.call('run', [], { "cmd_key": "pull", "repo_path": repo_path} )
    if retval == 0:
        return __entry__
    else:
        logging.error(f"could not pull {repo_path} ; return value = {retval}, bailing out")
        return None


def git(rest_of_cmd, env, repo_path, git_tool_entry, __entry__):
    """Run an arbitrary git command in a git_repo

Usage examples :
                axs byname axs2mlperf , git branch
    """
    retval = git_tool_entry.call('run', [], { "cmd_key": "generic", "rest_of_cmd": rest_of_cmd, "env": env, "repo_path": repo_path, "capture_output": False} )
    if retval == 0:
        return __entry__
    else:
        logging.error(f"could not run:\n\tgit {rest_of_cmd}\nreturn value = {retval}, bailing out")
        return None


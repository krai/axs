#!/usr/bin/env python3

""" This entry knows how to detect and set up shell tools

Usage examples :
    # show the detected tool's name:
            axs byquery shell_tool,can_download_url , get tool_name

    # show the detected tool's path:
            axs byquery shell_tool,can_download_url , get tool_path

    # show the command template:
            axs byquery shell_tool,can_download_url , get shell_cmd_with_subs

    # show the substituted downloading command:
            axs byquery shell_tool,can_download_url , get shell_cmd  --url=http://example.com/ --target_path=example.html

    # run the substituted downloading command:
            axs byquery shell_tool,can_download_url , run  --url=http://example.com/ --target_path=example.html
"""

import logging
import os
import sys


def which(tool_name, exec_suffixes=None, env=None):
    """OS-independent routine to search for an executable in the OS's executable path.

Usage examples :
    # detect the executable by searching through the active exec_path
            axs byname tool_detector , which wget
    """
    exec_dirs   = os.get_exec_path(env)

    for exec_dir in exec_dirs:
        for suffix in exec_suffixes:
            candidate_full_path = os.path.join(exec_dir, tool_name + suffix)
            if os.access(candidate_full_path, os.X_OK):
                return candidate_full_path
    return None


def detect(tool_name=None, tool_path=None, newborn_entry=None):
    """Detect/select an installed shell tool and create an entry to point at it

Usage examples :
    # detect wget by providing all the parameters from the command line:
            axs byname tool_detector , detect wget --tags,=shell_tool,can_download_url '--shell_cmd:=AS^IS:^^:substitute:#{tool_path}# -O #{target_path}# #{url}#'

    # detect curl by providing all the parameters from the command line:
            axs byname tool_detector , detect curl --tags,=shell_tool,can_download_url '--shell_cmd:=AS^IS:^^:substitute:#{tool_path}# -L -o #{target_path}# #{url}#'

    # select kernel_python by default:
            axs byquery shell_tool,can_python

    # detect a custom tool_name:
            axs byquery shell_tool,can_python,tool_name=python3.8

    # run the substituted downloading command:
            axs byquery shell_tool,can_download_url , run --url=https://example.com/ --target_path=example.html
    """

    if tool_path:
        return newborn_entry.save()
    else:
        logging.warning(f"Could not detect the tool '{tool_name}'")
        return None

#!/usr/bin/env python3

""" This entry knows how to run an arbitrary shell command in a given environment
    and optionally capture the output.
"""

import logging
import subprocess
import sys

def run(shell_cmd, env=None, capture_output=False, errorize_output=False, split_to_lines=False):
    """Run the given shell command in the given environment

Usage examples:
            axs byname shell , run 'echo This is a test.'

    # dynamically create a tool and use it:
            axs fresh_entry , plant _parent_entries --,:=AS^IS:^:byname:shell , plant tool_path --:=^^:which:wget , plant shell_cmd '--:=AS^IS:^^:substitute:#{tool_path}# -O #{target_path}# #{url}#' , run --url=https://example.com --target_path=example.html

    # first create a downloading tool, then use it:
            axs fresh_entry ---own_data='{"_parent_entries":[["AS^IS","^","byname","shell"]]}' , plant tool_name wget tool_path --:=^^:which:wget shell_cmd '--:=AS^IS:^^:substitute:#{tool_path}# -O #{target_path}# #{url}#' tags --,=shell_tool,can_download_url , save wget_tool
            axs bypath wget_tool , run --url=https://example.com --target_path=example.html

    """
    env = env or {}
    if env:
        shell_cmd = 'env ' + ' '.join([ f"{k}={env[k]}" for k in env]) + ' ' + shell_cmd

    if type(shell_cmd)==list:   # making sure all components are strings
        shell_cmd = [str(x) for x in shell_cmd]

    logging.warning(f"shell.run() about to execute:\n\t{shell_cmd}\n" + (' '*8 + '^'*len(shell_cmd)) )

    if capture_output:
        stdout_target = subprocess.PIPE
    elif errorize_output:
        stdout_target = sys.stderr.buffer
    else:
        stdout_target = None

    completed_process = subprocess.run(shell_cmd, shell = (type(shell_cmd)!=list), stdout=stdout_target)
    if capture_output:
        output  = completed_process.stdout.decode('utf-8').rstrip()

        if split_to_lines:
            output = output.split('\n')

        return output
    else:
        return completed_process.returncode


if __name__ == '__main__':

    # When the entry's code is run as a script, perform local tests:
    #
    return_code = run( "echo Hello, world!" )
    print(f"ReturnCode = {return_code}\n")

    return_code = run( shell_cmd='env', env={'FOO':12345, 'BAR':23456, 'BAZ':34567} )
    print(f"ReturnCode = {return_code}\n")

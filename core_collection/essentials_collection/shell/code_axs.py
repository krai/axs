#!/usr/bin/env python3

""" This entry knows how to run an arbitrary shell command in a given environment
    and optionally capture the output.
"""

import logging
import os
import subprocess
import sys

def run(shell_cmd, env=None, in_dir=None, capture_output=False, errorize_output=False, capture_stderr=False, split_to_lines=False, return_saved_record_entry=False, return_this_entry=None, get_and_return_on_success=None, __record_entry__=None):
    """Run the given shell command in the given environment

Usage examples:
            axs byname shell , run 'echo This is a test.'

    # execute a shell command in a specific directory:
            axs work_collection , in_dir: get_path , , byname shell , run 'ls -l'

    # dynamically create a tool and use it:
            axs fresh_entry , plant _parent_entries --,:=AS^IS:^:byname:shell , plant tool_path --:=^^:which:wget , plant shell_cmd '--:=AS^IS:^^:substitute:#{tool_path}# -O #{target_path}# #{url}#' , run --url=https://example.com --target_path=example.html

    # first create a downloading tool, then use it:
            axs fresh_entry ---own_data='{"_parent_entries":[["AS^IS","^","byname","shell"]]}' , plant tool_name wget tool_path --:=^^:which:wget shell_cmd '--:=AS^IS:^^:substitute:#{tool_path}# -O #{target_path}# #{url}#' tags --,=shell_tool,can_download_url , save wget_tool
            axs bypath wget_tool , run --url=https://example.com --target_path=example.html

    """
    if type(shell_cmd)==list:   # making sure all components are strings
        shell_cmd = [str(x) for x in shell_cmd]

    logging.warning(f"shell.run() about to execute (with env={env}, in_dir={in_dir}, capture_output={capture_output}, errorize_output={errorize_output}, capture_stderr={capture_stderr}, split_to_lines={split_to_lines}):\n\t{shell_cmd}\n" + (' '*8 + '^'*len(shell_cmd)) )

    if in_dir:
        prev_dir = os.getcwd()
        os.chdir( in_dir )

    if capture_output:
        stdout_target = subprocess.PIPE
    elif errorize_output:
        stdout_target = sys.stderr.buffer
    else:
        stdout_target = None

    stderr_target = subprocess.PIPE if capture_stderr else None

    if env:
        env = { k: str(env[k]) for k in env }   # cast all env's values to strings

    completed_process = subprocess.run(shell_cmd, shell = (type(shell_cmd)!=list), env=env, stdout=stdout_target, stderr=stderr_target)

    if in_dir:
        os.chdir( prev_dir )

    if capture_output or capture_stderr:    # FIXME: assuming XOR at the moment
        output  = (completed_process.stderr if capture_stderr else completed_process.stdout).decode('utf-8').rstrip()

        if split_to_lines:
            output = output.split('\n')

        return output
    elif return_saved_record_entry:
        return __record_entry__.save()
    elif return_this_entry:
        return return_this_entry
    elif get_and_return_on_success and not completed_process.returncode:
        return __entry__[get_and_return_on_success]
    else:
        return completed_process.returncode


if __name__ == '__main__':

    # When the entry's code is run as a script, perform local tests:
    #
    return_code = run( "echo Hello, world!" )
    print(f"ReturnCode = {return_code}\n")

    return_code = run( shell_cmd='env', env={'FOO':12345, 'BAR':23456, 'BAZ':34567} )
    print(f"ReturnCode = {return_code}\n")

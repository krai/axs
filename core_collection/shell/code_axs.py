#!/usr/bin/env python3

""" This entry knows how to run an arbitrary shell command in a given environment
    and optionally capture the output.
"""

import subprocess

def run(shell_cmd, env=None, capture_output=False, split_to_lines=False):
    """Run the given shell command in the given environment

Usage examples:
            axs byname shell , run 'echo This is a test.'
    """
    env = env or {}
    if env:
        shell_cmd = 'env ' + ' '.join([ f"{k}={env[k]}" for k in env]) + ' ' + shell_cmd

    completed_process = subprocess.run(shell_cmd, shell = True, stdout=(subprocess.PIPE if capture_output else None) )
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

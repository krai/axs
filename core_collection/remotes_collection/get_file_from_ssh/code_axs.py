"""An axs-way of integrating a command run via a remote ssh session.

    Since we generate an axs entry on the host machine for each experiment,
    we use this entry to contain an "exchange" directory into which we secure-copy (scp) the results of the main command.

    A reverse SSH tunnel is established for the duration of the ssh session to enable such secure copying.
    Please note: for this mechanism to work you need to have set up bidirectional password-less operation beforehand
    (public keys copied across into authorized_keys).

Usage examples :
                    # all default parameters:
                axs byquery ran_in_ssh,file_from_ssh

                    # run on a different machine
                axs byquery ran_in_ssh,file_from_ssh,ssh_hostname=velociti.a

                    # ask for a different file:
                axs byquery ran_in_ssh,file_from_ssh,full_filepath=/etc/passwd
"""

"""An axs-way of integrating a command run in a docker container.

    Since we generate an axs entry on the host machine for each experiment,
    we use this entry to contain an "exchange" directory which we map between the host and the container.

    The example "cp" command is used to copy a file from inside the container into the "exchange" directory,
    which then becomes visible to the host's axs, and stays around even after the container gets destroyed.

Usage examples :
                    # all default parameters:
                axs byquery run_remotely,remote_type=docker,exchange_type=files

                    # run in a different image (which in this case affects the contents of /etc/lsb-release file)
                axs byquery run_remotely,remote_type=docker,exchange_type=files,docker_image=ubuntu:jammy

                    # ask for a different file:
                axs byquery run_remotely,remote_type=docker,exchange_type=files,full_filepath=/etc/passwd
"""

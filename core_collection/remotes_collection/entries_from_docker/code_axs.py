"""An example for "remote" axs execution in docker:

Make sure docker daemon is running on your host.

Build the image (make sure you don't have an outdated axs kernel in docker's build cache!) :
    axs byquery shell_tool,can_docker , run --cmd_key=build --docker_image=axs_kernel

To run a pipeline in that docker image, run the following on the host:
    axs byquery program_output,remote_type=docker,exchange_type=entries,task=image_classification,framework=onnxrt
"""

import os


def docker_mounts(host_entries_to_pass_down, host_paths_to_pass_down, host_kernel_path, in_docker_kernel_path):
    """The single source of truth on what is mounted where: a list of (path_on_host, path_in_docker) pairs.

Usage examples :
    axs byname entries_from_docker , get docker_mounts
    """
    return [ (host_kernel_path, in_docker_kernel_path) ] + [ (he.get_path(), f"/mnt/{he.get_name()}") for he in host_entries_to_pass_down ] + [ (hp, hp) for hp in host_paths_to_pass_down ]


def host_to_docker_path(host_path, docker_mounts):
    """Translate a host path into the container's view of it, via the most specific mount that covers it.

Usage examples :
    axs byname entries_from_docker , host_to_docker_path --host_path=/path/to/axs/core_collection
    """
    real_path = os.path.realpath(host_path)
    for path_on_host, path_in_docker in sorted(docker_mounts, key=lambda m: len(os.path.realpath(m[0])), reverse=True):
        real_path_on_host = os.path.realpath(path_on_host)
        if real_path == real_path_on_host or real_path.startswith(real_path_on_host + os.path.sep):
            return path_in_docker + real_path[len(real_path_on_host):]
    raise ValueError(f"Host path '{host_path}' is not mounted into the container")


def host_entries_mapping(docker_mounts):

    return ' '.join( [ f"-v {path_on_host}:{path_in_docker}" for path_on_host, path_in_docker in docker_mounts ] )


def container_entries_access(host_entries_to_pass_down, host_kernel_path, docker_mounts):

    in_docker_axs = host_to_docker_path( os.path.join(host_kernel_path, 'axs'), docker_mounts )
    return f'{in_docker_axs} work_collection ' + ( ' '.join( [ f", add_entry_path {host_to_docker_path(he.get_path(), docker_mounts)}" for he in host_entries_to_pass_down ] ) )

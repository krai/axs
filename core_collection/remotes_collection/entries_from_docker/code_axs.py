"""An example for "remote" axs execution in docker:

Make sure docker daemon is running on your host.

Build the image (make sure you don't have an outdated axs kernel in docker's build cache!) :
    axs byquery shell_tool,can_docker , run --cmd_key=build --docker_image=axs_kernel

To run a pipeline in that docker image, run the following on the host:
    axs byquery program_output,remote_type=docker,exchange_type=entries,task=image_classification,framework=onnxrt
"""

def host_entries_mapping(host_entries_to_pass_down, host_paths_to_pass_down, host_kernel_path):

    return ' '.join( [ f"-v {host_kernel_path}:/mnt/axs" ] + [ f"-v {he.get_path()}:/mnt/{he.get_name()}" for he in host_entries_to_pass_down ] + [ f"-v {hp}:{hp}" for hp in host_paths_to_pass_down ] )


def container_entries_access(host_entries_to_pass_down, in_docker_kernel_path):

    return f'{in_docker_kernel_path}/axs work_collection ' + ( ' '.join( [ f", add_entry_path /mnt/{he.get_name()}" for he in host_entries_to_pass_down ] ) )

"""An example for "remote" axs execution in docker:

Make sure docker daemon is running on your host.

Build the image (make sure you don't have an outdated axs kernel in docker's build cache!) :
    axs byquery shell_tool,can_docker , run --cmd_key=build --docker_image=axs_kernel

To run a pipeline in that docker image, run the following on the host:
    axs byquery program_output,remote_type=docker,exchange_type=entries,task=image_classification,framework=onnxrt
"""

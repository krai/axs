FROM ubuntu:20.04

SHELL ["/bin/bash", "-c"]

ENTRYPOINT ["/bin/bash", "-c"]

# Install system dependencies for axs:
ENV DEBIAN_FRONTEND=noninteractive
RUN apt update -y\
 && apt install -y apt-utils\
 && apt upgrade -y\
 && apt install -y\
 git wget zip libz-dev\
 python3 python3-pip\
 vim sudo curl\
 && apt clean

# Optional, if commits from containers are expected:
RUN git config --global user.name "krai"\
 && git config --global user.email "info@krai.ai"

# Install the axs kernel:
RUN git clone https://github.com/krai/axs
ENV PATH="$PATH:$HOME/axs"

# Trigger pre-creation of an (initially empty) work_collection:
RUN axs work_collection

CMD [ "/bin/bash" ]

FROM ubuntu:20.04

SHELL ["/bin/bash", "-c"]

ENTRYPOINT ["/bin/bash", "-c"]

# Download system dependencies
ENV DEBIAN_FRONTEND=noninteractive
RUN apt update -y\
 && apt install -y apt-utils\
 && apt upgrade -y\
 && apt install -y\
 git wget zip libz-dev\
 python3 python3-pip\
 vim sudo curl\
 && apt clean

# Create user 'krai' in group 'kraig'.
ARG GROUP_ID=1500
ARG USER_ID=2000
RUN groupadd -g ${GROUP_ID} kraig\
 && useradd -u ${USER_ID} -g kraig --create-home --shell /bin/bash krai
USER krai:kraig
RUN git config --global user.name "krai"\
 && git config --global user.email "info@krai.ai"

WORKDIR /home/krai

# Install the kernel of the X workflow automation framework.
RUN git clone https://github.com/krai/axs
ENV PATH="$PATH:/home/krai/axs"

# Trigger pre-creation of an (initially empty) work_collection
RUN axs work_collection

CMD [ "/bin/bash" ]

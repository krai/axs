# How to install and set up CUDA 11.7 and CUDNN 8.5.* on chai

## 1. Check python version 
```
maria@chai:/usr/local$ python3 --version
Python 3.9.13
```
By default  `python3`  is  `Python 3.10.4` on `chai`.
If ```python3``` is not ```Python 3.9.* ``` then create symbolic link:
```
maria@chai:~$ ln -s /usr/bin/python3.9 /usr/bin/python3
```
## 2. Install CUDA on Ubuntu 22.04

### Download CUDA package for ubuntu22.04
```
maria@chai:~$ wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin 
```
### Move downloaded package:
```
maria@chai:~$ sudo mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600
```
### Add a GPG key

```
maria@chai:~$ sudo apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/3bf863cc.pub
```
### Install package for `add-apt-repository`

```
maria@chai:~$ sudo apt-get install software-properties-common
```

### Create symbolic link for `apt_pkg.cpython-39-x86_64-linux-gnu.so` 

It is necessary if `Python 3.10.*` is set by default like on chai.

```
maria@chai:~$ cd /usr/lib/python3/dist-packages/
maria@chai:/usr/lib/python3/dist-packages$ sudo ln -s apt_pkg.cpython-310-x86_64-linux-gnu.so apt_pkg.cpython-39-x86_64-linux-gnu.so
```

### Add repository to the setting of apt-get
```
maria@chai:~$ sudo add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/ /"
```

### Update all packages and repositories
```
maria@chai:~$ sudo apt-get update
```
## 3. Install CUDNN on Ubuntu 22.04

```
maria@chai:~$ sudo apt-get install libcudnn8=8.5.0.*-1+cuda11.7

Get:1 https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64  libcudnn8 8.5.0.96-1+cuda11.7 [347 MB]
Fetched 347 MB in 30s (11.5 MB/s)
(Reading database ... 199136 files and directories currently installed.)
Preparing to unpack .../libcudnn8_8.5.0.96-1+cuda11.7_amd64.deb ...
Unpacking libcudnn8 (8.5.0.96-1+cuda11.7) over (8.4.1.50-1+cuda11.6) ...
Setting up libcudnn8 (8.5.0.96-1+cuda11.7) ...
...
```

```
maria@chai:~$ sudo apt-get install libcudnn8-dev=8.5.0.*-1+cuda11.7

Get:1 https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64  libcudnn8-dev 8.5.0.96-1+cuda11.7 [356 MB]
Fetched 356 MB in 31s (11.6 MB/s)
Selecting previously unselected package libcudnn8-dev.
(Reading database ... 199136 files and directories currently installed.)
Preparing to unpack .../libcudnn8-dev_8.5.0.96-1+cuda11.7_amd64.deb ...
Unpacking libcudnn8-dev (8.5.0.96-1+cuda11.7) ...
Setting up libcudnn8-dev (8.5.0.96-1+cuda11.7) ...
update-alternatives: using /usr/include/x86_64-linux-gnu/cudnn_v8.h to provide /usr/include/cudnn.h (libcudnn) in auto mode
...
```
## 4. Check CUDA and CUDNN

```
maria@chai:~/axs/core_collection/onnx_image_classifier$ nvidia-smi
...
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 515.65.01    Driver Version: 515.65.01    CUDA Version: 11.7     |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|                               |                      |               MIG M. |
|===============================+======================+======================|
|   0  NVIDIA RTX A5000    Off  | 00000000:17:00.0 Off |                  Off |
| 30%   33C    P8    12W / 230W |      5MiB / 24564MiB |      0%      Default |
|                               |                      |                  N/A |
+-------------------------------+----------------------+----------------------+
|   1  NVIDIA RTX A5000    Off  | 00000000:B3:00.0 Off |                  Off |
| 30%   34C    P8    15W / 230W |    121MiB / 24564MiB |      0%      Default |
|                               |                      |                  N/A |
+-------------------------------+----------------------+----------------------+

+-----------------------------------------------------------------------------+
| Processes:                                                                  |
|  GPU   GI   CI        PID   Type   Process name                  GPU Memory |
|        ID   ID                                                   Usage      |
|=============================================================================|
|    0   N/A  N/A      2425      G   /usr/lib/xorg/Xorg                  4MiB |
|    1   N/A  N/A      2425      G   /usr/lib/xorg/Xorg                 89MiB |
|    1   N/A  N/A      2805      G   /usr/bin/gnome-shell                5MiB |
+-----------------------------------------------------------------------------+

maria@chai:~/axs/core_collection/onnx_image_classifier$  nvidia-smi | grep Driver
| NVIDIA-SMI 515.65.01    Driver Version: 515.65.01    CUDA Version: 11.7     |
```
Example in axs:
```
maria@chai:~$ axs byname onnx_image_classifier , run ---capture_output=false --output_file_path=
...
Session execution provider:  ['CUDAExecutionProvider', 'CPUExecutionProvider']
Device: GPU
input_layer_names=['input_tensor:0']
output_layer_names=['softmax_tensor:0']
model_input_shape=['unk__524', 3, 224, 224]
model_output_shape=['unk__525', 1001]
batch 1/1: (1..20) [65, 795, 230, 809, 516, 67, 334, 415, 674, 332, 109, 286, 370, 757, 595, 147, 327, 23, 478, 517]
0
```

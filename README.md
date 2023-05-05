axs (pronounced like "access")
==============================

Travis: [![Travis Build Status](https://api.travis-ci.com/krai/axs.svg?branch=master&status=passed)](https://app.travis-ci.com/github/krai/axs)
AppVeyor: [![Appveyor Build status](https://ci.appveyor.com/api/projects/status/lrfwjca630klbku3/branch/master?svg=true)](https://ci.appveyor.com/project/ens-lg4/axs/branch/master)

Following the success of [CK (Collective Knowledge) framework](https://github.com/ctuning/ck)
and based on the experience of using it in scientific experimentation
here we attempt to re-design certain assumptions central to the CK framework's kernel
which cannot be simply evolved from its current state due to the requirement of code's backwards compatibility.

The goal here is to retain compatibility with the core ideas and the spirit of CK.

# Installation
Simply download the repository.
```
git clone --branch stable https://github.com/krai/axs ~/axs
```

Add the path to `bashrc`.
```
echo "export PATH='$PATH:$HOME/axs'" >> ~/.bashrc
```

And source it.
```
source ~/.bashrc
```

Upon sucessful installation.
```
user@laptop:~/axs$ axs
DefaultKernel{}
```
The dependencies of various components are managed through `axs` entries. To start with, entries can be found in `~/axs/core_collection`. When programs are being executed for the first time, new entries will be automatically stored in work collection. By default, they are located at `~/work_collection`.
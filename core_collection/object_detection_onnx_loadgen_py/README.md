# MLPerf Inference - Object Detection - ONNX

This Python implementation runs ONNX models for Object Detection. Currently it only supports COCO dataset.
The two supported models for it are SSD-ResNet34 (as offered by MLPerf) and RetinaNet (retrained by Krai for COCO).

## Prerequisites

This workflow is a designed showcase for `axs` workflow management system.
So the only prerequisite from the user's point of view is a sufficiently fresh version of `axs` system.


Dependencies of various components (on Python code and external utilities) as well as interdependencies of the workflow's main components (original dataset, preprocessed dataset, model and its parameters) have been described in `axs`'s internal language to achieve the fullest automation we could.

Please note that due to this automation (automatic recursive installation of all dependent components) the external timing of the initial runs (when new components have to be downloaded and/or installed) may not be very useful. The internal timing measured by LoadGen library should be trusted instead, which is not affected by these changes in external infrastructure.


## Initial clean-up (optional)

In some cases it may be desirable to "start from a clean slate" - i.e. clean up all the cached `axs` entries,
which includes the model with weights, the original COCO dataset and its' pre-resized versions
(different pre-resizing resolution is needed for different models), as well as all the necessary python packages.

On the other hand, since all those components may take considerable time to be installed, we do not recommend cleaning up between individual runs.
The entry cache is there for a reason.


## Performing a short accuracy run (specifying the number of samples to run on) :

The following test run will trigger downloading and installation of the necessary Python packages, the default model (SSD-ResNet34), the original COCO dataset and a short partial pre-resized subset of 20 images:
```
axs byquery loadgen_output,detected_coco,framework=onnx,loadgen_dataset_size=20 , get mAP
```
The mAP value should be printed after a succesful run.


## Performing a short accuracy run (specifying the model) :

The following test run will trigger (in addition to the above) downloading and installation of the RetinaNet model:
```
axs byquery loadgen_output,detected_coco,framework=onnx,loadgen_dataset_size=20,model_name=retinanet , get mAP
```
The mAP value should be printed after a succesful run.


## Benchmarking the program in AccuracyOnly mode:

The following command will trigger (in addition to the above) pre-resizing of the whole 5000-image COCO dataset to the resolution needed by SSD ResNet34 model (1200x1200) and will run on the whole dataset. Please note that depending on whether both the hardware and the software supports running on GPU, the run may be performed either on GPU or on CPU.
There are ways to constrain this to CPU only.
```
axs byquery loadgen_output,detected_coco,framework=onnx,model_name=ssd_resnet34,loadgen_dataset_size=5000,loadgen_buffer_size=100,loadgen_scenario=Offline
```
The mAP value should be printed after a succesful run.


## Benchmarking the program in PerformanceOnly mode:

Two important changes for performance mode should be takein into account:
1. there is no way to measure mAP (LoadGen's constraint)
2. you need to "guess" the `loadgen_target_qps` parameter, from which the testing regime will be generated in order to measure the actual QPS.

So `TargetQPS` is the input, whereas `QPS` is the output of this benchmark:
```
axs byquery loadgen_output,detected_coco,framework=onnx,model_name=ssd_resnet34,loadgen_dataset_size=5000,loadgen_buffer_size=100,loadgen_scenario=Offline,loadgen_mode=PerformanceOnly,loadgen_target_qps=32,verbosity=1
```

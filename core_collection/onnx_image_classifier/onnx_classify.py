#!/usr/bin/env python3

"""An example Python script that is given its data, necessary Python environment and the output path by wrapping it into an Entry.

Usage examples :
                    # execution_device can be cpu, gpu, cuda.
                    # as a side-effect, automatically downloads and extracts Imagenet500:
                axs byname onnx_image_classifier , run --execution_device=cpu --num_of_images=100

                    # reuses the Imagenet500 already downloaded & extracted:
                axs byname onnx_image_classifier , run --execution_device=gpu --num_of_images=500

                    # quick removal of Imagenet500:
                axs byquery preprocessed,imagenet , remove
                axs byquery extracted,imagenet,dataset_size=500 , remove

                    # assuming Imagenet50k in a tarball:
                axs byname extractor , extract --archive_path=/datasets/dataset-imagenet-ilsvrc2012-val.tar --tags,=extracted,imagenet --strip_components=1
                axs byname onnx_image_classifier , run --num_of_images=1000

                    # quick removal of Imagenet500 (again):
                axs byquery preprocessed,imagenet , remove
                axs byquery extracted,imagenet,dataset_size=500 , remove

                    # preprocessing Imagenet50k manually:
                axs byquery preprocessed,imagenet,imagenet_directory=/datasets/imagenet/imagenet

                    # should use previously preprocessed dataset:
                axs byname onnx_image_classifier , run --num_of_images=800

                    # save output to file experiment.json:
                axs byname onnx_image_classifier , run --execution_device=cpu --num_of_images=100 --output_file_path=experiment.json

                    # set top_n_max ( number of predictions for each image ) which is added to output_file. By default top_n_max = 10
                axs byquery script_output,classified_imagenet,framework=onnx,num_of_images=32 , top_n_max=6

                    # get accuracy
                axs byquery script_output,classified_imagenet,framework=onnx,num_of_images=32 , get accuracy

                    # get n predictions for each image
                axs byquery script_output,classified_imagenet,framework=onnx,num_of_images=32 , get print_top_n_predictions

"""

import os
import sys

print(f"\n**\nRUNNING {__file__} under {sys.executable} with sys.path={sys.path}\n**\n", file=sys.stderr)

import json
import math
from time import time

import numpy as np
import onnxruntime as rt
from imagenet_loader import ImagenetLoader


model_path                  = sys.argv[1]
preprocessed_imagenet_dir   = sys.argv[2]
num_of_images               = int(sys.argv[3])
max_batch_size              = int(sys.argv[4])
cpu_threads                 = int(sys.argv[5])
output_file_path            = sys.argv[6]
model_name                  = sys.argv[7]
normalize_data_bool         = eval(sys.argv[8])     # FIXME: currently we are passing a stringified form of a data structure,
subtract_mean_bool          = eval(sys.argv[9])    # it would be more flexible to encode/decode through JSON instead.
given_channel_means         = eval(sys.argv[10])
execution_device            = sys.argv[11]         # if empty, it will be autodetected
top_n_max                   = int(sys.argv[12])

batch_count                 = math.ceil(num_of_images / max_batch_size)
data_layout                 = "NCHW"

sess_options = rt.SessionOptions()
if cpu_threads > 0:
    sess_options.enable_sequential_execution = False
    sess_options.session_thread_pool_size = cpu_threads

if execution_device == "cpu":
    requested_provider = "CPUExecutionProvider"
elif execution_device in ["gpu", "cuda"]:
    requested_provider = "CUDAExecutionProvider"
elif execution_device in ["tensorrt", "trt"]:
    requested_provider = "TensorrtExecutionProvider"

sess = rt.InferenceSession(model_path, sess_options, providers= [requested_provider] if execution_device else rt.get_available_providers())

session_execution_provider=sess.get_providers()
print("Session execution provider: ", sess.get_providers(), file=sys.stderr)

ts_before_model_loading = time()

if "CUDAExecutionProvider" in session_execution_provider or "TensorrtExecutionProvider" in session_execution_provider:
    print("Device: GPU", file=sys.stderr)
else:
    print("Device: CPU", file=sys.stderr)

input_layer_names   = [ x.name for x in sess.get_inputs() ]
input_layer_name    = input_layer_names[0]
output_layer_names  = [ x.name for x in sess.get_outputs() ]
output_layer_name   = output_layer_names[0]
model_input_shape   = sess.get_inputs()[0].shape
model_output_shape  = sess.get_outputs()[0].shape
height              = model_input_shape[2]
width               = model_input_shape[3]

loader_object       = ImagenetLoader(preprocessed_imagenet_dir, height, width, normalize_data_bool, subtract_mean_bool, given_channel_means, data_layout)


print(f"input_layer_names={input_layer_names}", file=sys.stderr)
print(f"output_layer_names={output_layer_names}", file=sys.stderr)
print(f"model_input_shape={model_input_shape}", file=sys.stderr)
print(f"model_output_shape={model_output_shape}", file=sys.stderr)


model_loading_s = time() - ts_before_model_loading

predictions             = {}
sum_loading_s           = 0
sum_inference_s         = 0
list_batch_loading_s    = []
list_batch_inference_s  = []
weight_id               = {}
top_n_predictions       = {}
batch_num               = 0

for batch_start in range(0, num_of_images, max_batch_size):

    ts_before_data_loading  = time()

    batch_num                   = batch_num + 1
    batch_open_end              = min(batch_start+max_batch_size, num_of_images)
    batch_global_indices        = range(batch_start, batch_open_end)
    batch_data, batch_filenames = loader_object.load_preprocessed_batch_from_indices( batch_global_indices )

    ts_before_inference = time()

    batch_predictions   = sess.run([output_layer_name], {input_layer_name: batch_data})[0]

    ts_after_inference  = time()

    class_numbers               = (np.argmax( batch_predictions, axis=1) - 1).tolist()
    stripped_batch_filenames    = [file_name.rsplit('.', 1)[0] for file_name in batch_filenames]
    predictions.update( dict(zip(stripped_batch_filenames, class_numbers)) )

    batch_loading_s     = ts_before_inference - ts_before_data_loading
    batch_inference_s   = ts_after_inference - ts_before_inference
    list_batch_loading_s.append ( batch_loading_s )
    list_batch_inference_s.append( batch_inference_s )
    sum_loading_s   += batch_loading_s
    sum_inference_s += batch_inference_s

    print(f"batch {batch_num}/{batch_count}: ({batch_start+1}..{batch_open_end}) {class_numbers}")

    for i in range(batch_open_end-batch_start):
        softmax_vector      = batch_predictions[i][-1000:]
        top_n_indices       = list(reversed(softmax_vector.argsort()))[:top_n_max]

        for class_idx in top_n_indices:
            weight_id[str(class_idx)] = str(softmax_vector[class_idx])
        top_n_predictions[stripped_batch_filenames[i]] = weight_id
        weight_id = {}

if output_file_path:
        output_dict = {
            "execution_device": execution_device,
            "model_name": model_name,
            "framework": "onnx",
            "max_batch_size":   max_batch_size,
            "times": {
                "model_loading_s":          model_loading_s,
                "sum_loading_s":            sum_loading_s,
                "sum_inference_s":          sum_inference_s,
                "per_inference_s":          sum_inference_s / num_of_images,
                "fps":                      num_of_images / sum_inference_s,

                "list_batch_loading_s":     list_batch_loading_s,
                "list_batch_inference_s":   list_batch_inference_s,
            },
            "predictions": predictions,
            "top_n": top_n_predictions
        }
        json_string = json.dumps( output_dict , indent=4)
        with open(output_file_path, "w") as json_fd:
            json_fd.write( json_string+"\n" )
        print(f'Predictions for {num_of_images} images written into "{output_file_path}"')

#!/usr/bin/env python3

"""An example Python script that is given its data, necessary Python environment and the output path by wrapping it into an Entry.

Usage examples :
                    # execution_device can be cpu, gpu, cuda.
                    # as a side-effect, automatically downloads and extracts Imagenet500:
                axs byname image_classification_using_onnxrt_py , run --execution_device=cpu --num_of_images=100

                    # reuses the Imagenet500 already downloaded & extracted:
                axs byname image_classification_using_onnxrt_py , run --execution_device=gpu --num_of_images=500

                    # quick removal of Imagenet500:
                axs byquery preprocessed,imagenet , remove
                axs byquery extracted,imagenet,dataset_size=500 , remove

                    # assuming Imagenet50k in a tarball:
                axs byname extractor , extract --archive_path=/datasets/dataset-imagenet-ilsvrc2012-val.tar --tags,=extracted,imagenet --strip_components=1
                axs byname image_classification_using_onnxrt_py , run --num_of_images=1000

                    # quick removal of Imagenet500 (again):
                axs byquery preprocessed,imagenet , remove
                axs byquery extracted,imagenet,dataset_size=500 , remove

                    # preprocessing Imagenet50k manually:
                axs byquery preprocessed,imagenet,imagenet_directory=/datasets/imagenet/imagenet

                    # should use previously preprocessed dataset:
                axs byname image_classification_using_onnxrt_py , run --num_of_images=800

                    # save output to file experiment.json:
                axs byname image_classification_using_onnxrt_py , run --execution_device=cpu --num_of_images=100 --output_file_path=experiment.json

                    # set top_n_max ( number of predictions for each image ) which is added to output_file. By default top_n_max = 10
                axs byquery program_output,task=image_classification,framework=onnxrt,num_of_images=32 , top_n_max=6

                    # get accuracy
                axs byquery program_output,task=image_classification,framework=onnxrt,num_of_images=32 , get accuracy

                    # get n predictions for each image
                axs byquery program_output,task=image_classification,framework=onnxrt,num_of_images=32 , get print_top_n_predictions

"""

import os
import sys

print(f"\n**\nRUNNING {__file__} under {sys.executable} with sys.path={sys.path}\n**\n", file=sys.stderr)

import json
import math
from time import time

import numpy as np
import onnxruntime
from imagenet_loader import ImagenetLoader

input_file_path = sys.argv[1]
output_file_path =  sys.argv[2]

with open(input_file_path) as f:
    input_parameters = json.load(f)


model_path                    = input_parameters["model_path"]
preprocessed_images_dir       = input_parameters["preprocessed_images_dir"]
num_of_images                 = input_parameters["num_of_images"]
max_batch_size                = input_parameters["max_batch_size"]
cpu_threads                   = input_parameters["cpu_threads"]
model_name                    = input_parameters["model_name"]
normalize_symmetric           = eval(input_parameters["normalize_symmetric"])
subtract_mean_bool            = eval(input_parameters["subtract_mean_bool"])
given_channel_means           = eval(input_parameters["given_channel_means"])
output_layer_name             = input_parameters["output_layer_name"]
supported_execution_providers = input_parameters["supported_execution_providers"]          # if empty, it will be autodetected
top_n_max                     = input_parameters["top_n_max"]
input_file_list               = input_parameters["input_file_list"]

batch_count                   = math.ceil(num_of_images / max_batch_size)
data_layout                   = "NCHW"
given_channel_stds            = []

sess_options = onnxruntime.SessionOptions()
if cpu_threads > 0:
    sess_options.enable_sequential_execution = False
    sess_options.session_thread_pool_size = cpu_threads

sess = onnxruntime.InferenceSession(model_path, sess_options, providers=list(set(supported_execution_providers) & set(onnxruntime.get_available_providers())))

session_execution_provider=sess.get_providers()
print("Session execution provider: ", sess.get_providers(), file=sys.stderr)

ts_before_model_loading = time()

if "CUDAExecutionProvider" in session_execution_provider or "TensorrtExecutionProvider" in session_execution_provider:
    print("Device: GPU", file=sys.stderr)
else:
    print("Device: CPU", file=sys.stderr)

input_layer_names   = [ x.name for x in sess.get_inputs() ]
input_layer_name    = input_layer_names[0]

if output_layer_name:
    for i, output_layer in enumerate(sess.get_outputs()):
        if output_layer.name == output_layer_name:
            output_layer_index = i
            break
else:
    output_layer_index  = 0
    output_layer_name   = sess.get_outputs()[output_layer_index].name

model_input_shape   = sess.get_inputs()[0].shape
height              = model_input_shape[2]
width               = model_input_shape[3]
model_output_shape  = sess.get_outputs()[output_layer_index].shape

loader_object       = ImagenetLoader(preprocessed_images_dir, input_file_list, height, width, data_layout, normalize_symmetric, subtract_mean_bool, given_channel_means, given_channel_stds)


print(f"input_layer_names={input_layer_names}", file=sys.stderr)
print(f"output_layer_name={output_layer_name}", file=sys.stderr)
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

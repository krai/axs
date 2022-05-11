#!/usr/bin/env python3

import os
import sys

import numpy as np
from PIL import Image
import onnxruntime as rt
from time import time
import json
import math


model_path          = sys.argv[1]
imagenet_dir        = sys.argv[2]
num_of_images       = int(sys.argv[3])
max_batch_size      = int(sys.argv[4])
cpu_threads         = int(sys.argv[5])
output_file_path    = sys.argv[6]
model_name          = sys.argv[7]

normalize_data_bool = eval(sys.argv[8])     # FIXME: currently we are passing a stringified form of a data structure,
subtract_mean_bool  = eval(sys.argv[9])    # it would be more flexible to encode/decode through JSON instead.
given_channel_means = eval(sys.argv[10])
execution_device    = sys.argv[11]         # if empty, it will be autodetected

requested_provider  = sys.argv[12]

batch_count         = math.ceil(num_of_images / max_batch_size)

file_pattern        = 'ILSVRC2012_val_000{:05d}.JPEG'
data_layout         = "NCHW"

sess_options = rt.SessionOptions()
if cpu_threads > 0:
    sess_options.enable_sequential_execution = False
    sess_options.session_thread_pool_size = cpu_threads
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

print(f"input_layer_names={input_layer_names}", file=sys.stderr)
print(f"output_layer_names={output_layer_names}", file=sys.stderr)
print(f"model_input_shape={model_input_shape}", file=sys.stderr)
print(f"model_output_shape={model_output_shape}", file=sys.stderr)


def load_and_resize_image(image_filepath, height, width):
    pillow_img = Image.open(image_filepath).convert('RGB').resize((width, height)) # sic! The order of dimensions in resize is (W,H)

    input_data = np.float32(pillow_img)

    # Normalize
    if normalize_data_bool:
        input_data = input_data/127.5 - 1.0

    # Subtract mean value
    if subtract_mean_bool:
        if len(given_channel_means):
            input_data -= given_channel_means
        else:
            input_data -= np.mean(input_data)

#    print(np.array(pillow_img).shape)
    nhwc_data = np.expand_dims(input_data, axis=0)

    if data_layout == 'NHWC':
        # print(nhwc_data.shape)
        return nhwc_data
    else:
        nchw_data = nhwc_data.transpose(0,3,1,2)
        # print(nchw_data.shape)
        return nchw_data


def load_a_batch(batch_filenames):
    unconcatenated_batch_data = []
    for image_filename in batch_filenames:
        image_filepath = os.path.join( imagenet_dir, image_filename )
        nchw_data = load_and_resize_image( image_filepath, height, width )
        unconcatenated_batch_data.append( nchw_data )
    batch_data = np.concatenate(unconcatenated_batch_data, axis=0)

    return batch_data

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
    batch_num = batch_num + 1
    batch_open_end = min(batch_start+max_batch_size, num_of_images)

    ts_before_data_loading  = time()

    batch_global_indices = range(batch_start, batch_open_end)
    batch_filenames     = [ file_pattern.format(g+1) for g in batch_global_indices ]
    batch_data          = load_a_batch( batch_filenames )

    ts_before_inference = time()

    batch_predictions   = sess.run([output_layer_name], {input_layer_name: batch_data})[0]

    ts_after_inference      = time()

    class_numbers       = (np.argmax( batch_predictions, axis=1) - 1).tolist()
    predictions.update (dict(zip(batch_filenames, class_numbers)) )

    batch_loading_s     = ts_before_inference - ts_before_data_loading
    batch_inference_s   = ts_after_inference - ts_before_inference
    list_batch_loading_s.append ( batch_loading_s )
    list_batch_inference_s.append( batch_inference_s )
    sum_loading_s   += batch_loading_s
    sum_inference_s += batch_inference_s

    print(f"batch {batch_num}/{batch_count}: ({batch_start+1}..{batch_open_end}) {class_numbers}")

    for i in range(batch_open_end-batch_start):
        softmax_vector      = batch_predictions[i][-1000:]
        top10_indices        = list(reversed(softmax_vector.argsort()))[:10]
        #predictions[ batch_filenames[i] ] = top5_indices[0]

        for class_idx in top10_indices:
            weight_id[str(class_idx)] = str(softmax_vector[class_idx])
        top_n_predictions[batch_filenames[i]] = weight_id
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

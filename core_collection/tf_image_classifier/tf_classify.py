#!/usr/bin/env python3

import os
import sys

print(f"\n**\nRUNNING {__file__} under {sys.executable} with sys.path={sys.path}\n**\n", file=sys.stderr)

import tensorflow as tf
import numpy as np
from time import time
import json
import math

model_name                  = sys.argv[1]
model_path                  = sys.argv[2]
preprocessed_imagenet_dir   = sys.argv[3]
resolution                  = int(sys.argv[4])
num_of_images               = int(sys.argv[5])
max_batch_size              = int(sys.argv[6])
output_file_path            = sys.argv[7]
top_n_max                   = int(sys.argv[8])

batch_count                 = math.ceil(num_of_images / max_batch_size)
file_pattern                = 'ILSVRC2012_val_000{:05d}.rgb8'
data_layout                 = "NHWC"
input_layer_name            = "input"
output_layer_name           = "MobilenetV2/Predictions/Reshape_1"
normalize_data_bool         = True
subtract_mean_bool          = False


def load_graph(model_path):

    with tf.compat.v1.gfile.GFile(model_path, "rb") as f:
        graph_def = tf.compat.v1.GraphDef()
        graph_def.ParseFromString(f.read())

    # import the graph_def into a new Graph and return it
    with tf.Graph().as_default() as graph:
        # The value of name variable will prefix every op/node name. The default is "import".
        # Since we don't want any prefix, we have to override it with an empty string.
        tf.import_graph_def(graph_def, name="")

    return graph


def load_preprocessed_and_normalize(image_filepath, height, width):
    img_rgb8 = np.fromfile(image_filepath, np.uint8)
    img_rgb8 = img_rgb8.reshape((height, width, 3))

    input_data = np.float32(img_rgb8)

    # Normalize
    if normalize_data_bool:
        input_data = input_data/127.5 - 1.0

    # Subtract mean value
    if subtract_mean_bool:
        if len(given_channel_means):
            input_data -= given_channel_means
        else:
            input_data -= np.mean(input_data)

#    print(np.array(img_rgb8).shape)
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
        image_filepath = os.path.join( preprocessed_imagenet_dir, image_filename )
        nchw_data = load_preprocessed_and_normalize( image_filepath, resolution, resolution )
        unconcatenated_batch_data.append( nchw_data )
    batch_data = np.concatenate(unconcatenated_batch_data, axis=0)

    return batch_data



# Prepare TF config options
config = tf.compat.v1.ConfigProto()
config.gpu_options.allow_growth = True
config.gpu_options.allocator_type = 'BFC'
config.gpu_options.per_process_gpu_memory_fraction = float(os.getenv('CK_TF_GPU_MEMORY_PERCENT', 33)) / 100.0
num_processors = int(os.getenv('CK_TF_CPU_NUM_OF_PROCESSORS', 0))
if num_processors > 0:
    config.device_count["CPU"] = num_processors


ts_before_model_loading = time()

# Load the TF model from ProtoBuf file
graph = load_graph(model_path)
input_layer = graph.get_tensor_by_name(input_layer_name+':0')
output_layer = graph.get_tensor_by_name(output_layer_name+':0')

model_input_shape = input_layer.shape
model_output_shape = output_layer.shape
model_classes = model_output_shape[1]
num_labels = 1000
bg_class_offset = model_classes-num_labels

print("Data layout: {}".format(data_layout), file=sys.stderr)
print("Input layer: {}".format(input_layer), file=sys.stderr)
print("Output layer: {}".format(output_layer), file=sys.stderr)
print("Expected input shape: {}".format(model_input_shape), file=sys.stderr)
print("Output layer shape: {}".format(model_output_shape), file=sys.stderr)
print("Number of labels: {}".format(num_labels), file=sys.stderr)
print("Background/unlabelled classes to skip: {}".format(bg_class_offset), file=sys.stderr)
print("Data normalization: {}".format(normalize_data_bool), file=sys.stderr)
print("Mean substraction: {}".format(subtract_mean_bool), file=sys.stderr)
print("", file=sys.stderr)

model_loading_s = time() - ts_before_model_loading

predictions             = {}
sum_loading_s           = 0
sum_inference_s         = 0
list_batch_loading_s    = []
list_batch_inference_s  = []
weight_id               = {}
top_n_predictions       = {}
batch_num               = 0

with tf.compat.v1.Session(graph=graph, config=config) as sess:

    for batch_start in range(0, num_of_images, max_batch_size):
        batch_num = batch_num + 1
        batch_open_end = min(batch_start+max_batch_size, num_of_images)

        ts_before_data_loading  = time()

        batch_global_indices = range(batch_start, batch_open_end)
        batch_filenames     = [ file_pattern.format(g+1) for g in batch_global_indices ]
        batch_data          = load_a_batch( batch_filenames )

        ts_before_inference = time()

        batch_predictions   = sess.run(output_layer, feed_dict={ input_layer: batch_data } )

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
                weight_id[str(class_idx)] = float(softmax_vector[class_idx])
            top_n_predictions[stripped_batch_filenames[i]] = weight_id
            weight_id = {}

if output_file_path:
        output_dict = {
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

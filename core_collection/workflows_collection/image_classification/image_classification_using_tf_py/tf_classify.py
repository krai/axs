#!/usr/bin/env python3

""" Imagenet Classifier using TensorFlow.

Usage examples :
                    # Compute accuracy on the full ImageNet50k preprocessed dataset:
                axs byquery program_output,task=image_classification,framework=tf,preprocessed_imagenet_dir=/datasets/imagenet/pillow_sq.224_cropped_resized_imagenet50000,num_of_images=50000,max_batch_size=1000 , get accuracy
"""

import sys

print(f"\n**\nRUNNING {__file__} under {sys.executable} with sys.path={sys.path}\n**\n", file=sys.stderr)

import json
import math
from time import time

import numpy as np
import tensorflow as tf
from imagenet_loader import ImagenetLoader

input_file_path        = sys.argv[1]
output_file_path       = sys.argv[2]

input_parameters = {}

with open(input_file_path) as f:
    input_parameters = json.load(f)


model_name                  = input_parameters["model_name"]
model_path                  = input_parameters["model_path"]
preprocessed_imagenet_dir   = input_parameters["preprocessed_images_dir"]
input_file_list             = input_parameters["input_file_list"]
resolution                  = input_parameters["resolution"]
input_layer_name            = input_parameters["input_layer_name"]
output_layer_name           = input_parameters["output_layer_name"]
normalize_symmetric         = input_parameters["normalization"]["normalize_symmetric"]
subtract_mean_bool          = input_parameters["normalization"]["subtract_mean_bool"]
given_channel_means         = input_parameters["normalization"]["given_channel_means"]
given_channel_stds          = input_parameters["normalization"]["given_channel_stds"]
data_layout                 = input_parameters["normalization"]["data_layout"]

num_of_images               = input_parameters["num_of_images"]
max_batch_size              = input_parameters["max_batch_size"]
top_n_max                   = input_parameters["top_n_max"]

gpu_memory_percent          = input_parameters["gpu_memory_percent"]
num_of_cpus                 = input_parameters["num_of_cpus"]

batch_count                 = math.ceil(num_of_images / max_batch_size)

loader_object               = ImagenetLoader(preprocessed_imagenet_dir, input_file_list, resolution, resolution, data_layout, normalize_symmetric, subtract_mean_bool, given_channel_means, given_channel_stds)


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


# Prepare TF config options
config = tf.compat.v1.ConfigProto()
config.gpu_options.allow_growth = True
config.gpu_options.allocator_type = 'BFC'
config.gpu_options.per_process_gpu_memory_fraction = float(gpu_memory_percent) / 100.0
if num_of_cpus > 0:
    config.device_count["CPU"] = num_of_cpus

ts_before_model_loading = time()

# Load the TF model from ProtoBuf file
graph = load_graph(model_path)
input_layer = graph.get_tensor_by_name(input_layer_name+':0')
output_layer = graph.get_tensor_by_name(output_layer_name+':0')

model_input_shape = input_layer.shape
model_output_shape = output_layer.shape
model_classes = model_output_shape[1]

print("Data layout: {}".format(data_layout), file=sys.stderr)
print("Input layer: {}".format(input_layer), file=sys.stderr)
print("Output layer: {}".format(output_layer), file=sys.stderr)
print("Expected input shape: {}".format(model_input_shape), file=sys.stderr)
print("Output layer shape: {}".format(model_output_shape), file=sys.stderr)
print("Data normalization (None, False=asymmeteric or True=symmetric) : {}".format(normalize_symmetric), file=sys.stderr)
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

        ts_before_data_loading  = time()

        batch_num                   = batch_num + 1
        batch_open_end              = min(batch_start+max_batch_size, num_of_images)
        batch_global_indices        = range(batch_start, batch_open_end)
        batch_data, batch_filenames = loader_object.load_preprocessed_batch_from_indices( batch_global_indices )

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
            "framework": "tf",
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

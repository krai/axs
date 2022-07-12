#!/usr/bin/env python3

""" Imagenet Classifier using TensorFlow.

Usage examples :
                    # Compute accuracy on the full ImageNet50k preprocessed dataset:
                axs byquery script_output,classified_imagenet,framework=tf,preprocessed_imagenet_dir=/datasets/imagenet/pillow_sq.224_cropped_resized_imagenet50000,num_of_images=50000,max_batch_size=1000 , get accuracy
"""

import os
import sys

print(f"\n**\nRUNNING {__file__} under {sys.executable} with sys.path={sys.path}\n**\n", file=sys.stderr)

import json
import math
from time import time

import numpy as np
import tensorflow as tf
from imagenet_loader import ImagenetLoader


model_name                  = sys.argv[1]
model_path                  = sys.argv[2]
preprocessed_imagenet_dir   = sys.argv[3]
resolution                  = int(sys.argv[4])
num_of_images               = int(sys.argv[5])
max_batch_size              = int(sys.argv[6])
output_file_path            = sys.argv[7]
top_n_max                   = int(sys.argv[8])

batch_count                 = math.ceil(num_of_images / max_batch_size)
input_layer_name            = "input"
output_layer_name           = "MobilenetV2/Predictions/Reshape_1"
normalize_symmetric         = True
subtract_mean_bool          = False
given_channel_means         = []
given_channel_stds          = []
data_layout                 = "NHWC"

loader_object               = ImagenetLoader(preprocessed_imagenet_dir, resolution, resolution, data_layout, normalize_symmetric, subtract_mean_bool, given_channel_means, given_channel_stds)


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

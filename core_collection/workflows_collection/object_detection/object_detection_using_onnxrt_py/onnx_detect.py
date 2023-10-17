#!/usr/bin/env python3

"""A standalone Object Detection program based on ONNX.

Usage examples  :

                    # a short accuracy run:
                axs byquery program_output,task=object_detection,framework=onnxrt,num_of_images=20 , mAP

                    # a short accuracy run with RetinaNet model:
                axs byquery program_output,task=object_detection,framework=onnxrt,model_name=retinanet_coco , mAP

                    # running without a model_entry (all relevant data specified directly) :
                axs byname object_detection_using_onnxrt_py , run --num_of_images=1 --model_name=RetinaNet --model_path=/Users/lg4/tmp/retinanet/retinanet_resnext50_32x4d_model_12.onnx --model_resolution=800 --model_output_scale=800 --model_input_layer_name=images --model_output_layers_bls="['boxes','labels','scores']" --model_skipped_classes="[]" --normalize_symmetric=False --subtract_mean_bool=False --given_channel_means="[]" --given_channel_stds="[]"

"""

import os
import json
import sys
import math
from time import time

import numpy as np
import onnxruntime
from coco_loader import CocoLoader

input_file_path  = sys.argv[1]
output_file_path =  sys.argv[2]

with open(input_file_path) as f:
     input_parameters = json.load(f)

model_name                    = input_parameters["model_name"]
model_path                    = input_parameters["model_path"]
model_resolution              = input_parameters["model_resolution"]
model_output_scale            = input_parameters["model_output_scale"]
model_input_layer_name        = input_parameters["model_input_layer_name"]
model_output_layers_bls       = eval(input_parameters["model_output_layers_bls"])
model_skipped_classes         = eval(input_parameters["model_skipped_classes"])
normalize_symmetric           = eval(input_parameters["normalize_symmetric"])
subtract_mean_bool            = eval(input_parameters["subtract_mean_bool"])
given_channel_means           = eval(input_parameters["given_channel_means"])
given_channel_stds            = eval(input_parameters["given_channel_stds"])

preprocessed_images_dir       = input_parameters["preprocessed_images_dir"]
num_of_images                 = input_parameters["num_of_images"]
max_batch_size                = input_parameters["max_batch_size"]
supported_execution_providers = input_parameters["supported_execution_providers"]
cpu_threads                   = input_parameters["cpu_threads"]
labels_file_path              = input_parameters["labels_file_path"]

minimal_class_id              = input_parameters["minimal_class_id"]


### RetinaNet:
### num_of_images=1  : mAP=0.33182702885673176
### num_of_images=10 : mAP=0.3836621714436375


## Image normalization:
#
data_layout                 = "NCHW"

# Program parameters:
#
SCORE_THRESHOLD             = 0

## Preprocessed input images' properties:
#
IMAGE_LIST_FILE_NAME    = "original_dimensions.txt"
original_dims_file_path = os.path.join(preprocessed_images_dir, IMAGE_LIST_FILE_NAME)
loader_object           = CocoLoader(preprocessed_images_dir, original_dims_file_path, model_resolution, model_resolution, data_layout, normalize_symmetric, subtract_mean_bool, given_channel_means, given_channel_stds)

def load_labels(labels_filepath):
    my_labels = []
    input_file = open(labels_filepath, 'r')
    for l in input_file:
        my_labels.append(l.strip())
    return my_labels

class_labels    = load_labels(labels_file_path)
num_classes     = len(class_labels)
class_map       = None
if (model_skipped_classes):
    class_map = []
    for i in range(num_classes + minimal_class_id):
        if i not in model_skipped_classes:
            class_map.append(i)


def main():
    global model_input_layer_name, max_batch_size

    ts_before_model_loading = time()

    sess_options = onnxruntime.SessionOptions()
    if cpu_threads > 0:
        sess_options.enable_sequential_execution = False
        sess_options.session_thread_pool_size = cpu_threads

    sess = onnxruntime.InferenceSession(model_path, sess_options, providers = list(set(supported_execution_providers) & set(onnxruntime.get_available_providers())))

    session_execution_provider=sess.get_providers()
    print("Session execution provider: ", sess.get_providers(), file=sys.stderr)

    if "CUDAExecutionProvider" in session_execution_provider or "TensorrtExecutionProvider" in session_execution_provider:
        print("Device: GPU", file=sys.stderr)
    else:
        print("Device: CPU", file=sys.stderr)

    model_loading_s = time() - ts_before_model_loading

    input_layer_names = [x.name for x in sess.get_inputs()]     # FIXME: check that model_input_layer_name belongs to this list
    model_input_layer_name = model_input_layer_name or input_layer_names[0]

    output_layer_names = [x.name for x in sess.get_outputs()]    # FIXME: check that OUTPUT_LAYER_NAME belongs to this list


    for inp in sess.get_inputs():
        print(f"inp.name={inp.name} , inp.shape={inp.shape} , inp.type={inp.type}")

    model_input_shape = sess.get_inputs()[0].shape
    model_input_type  = sess.get_inputs()[0].type
    model_input_type  = np.uint8 if model_input_type == 'tensor(uint8)' else np.float32     # FIXME: there must be a more humane way!

    for output in sess.get_outputs():
        print(f"output.name={output.name} , output.shape={output.shape} , output.type={output.type}")
        if output.name == model_output_layers_bls[0]:
            extra_dimension_needed = len(output.shape)<3

    print(f"Data layout: {data_layout}", file=sys.stderr)
    print(f"Input layers: {input_layer_names}", file=sys.stderr)
    print(f"Output layers: {output_layer_names}", file=sys.stderr)
    print(f"Input layer name: {model_input_layer_name}", file=sys.stderr)
    print(f"Expected input shape: {model_input_shape}", file=sys.stderr)
    print(f"Expected input type: {model_input_type}", file=sys.stderr)
    print(f"Output layer names: {model_output_layers_bls}", file=sys.stderr)
    print(f"Background/unlabelled classes to skip: {minimal_class_id}", file=sys.stderr)
    print("", file=sys.stderr)

    try:
        expected_batch_size = int(model_input_shape[0])
        if max_batch_size!=expected_batch_size:
            raise Exception(f"expected_batch_size={expected_batch_size}, desired max_batch_size={max_batch_size}, they do not match - exiting.")
    except ValueError:
        max_batch_size = None

    # Run batched mode
    next_batch_offset       = 0

    batch_count             = math.ceil(num_of_images / max_batch_size)
    batch_num               = 0

    sum_loading_s           = 0
    sum_inference_s         = 0
    list_batch_loading_s    = []
    list_batch_inference_s  = []
    detection_results       = {}

    for batch_start in range(0, num_of_images, max_batch_size):

        ts_before_data_loading  = time()

        batch_num                   = batch_num + 1
        batch_open_end              = min(batch_start+max_batch_size, num_of_images)
        batch_global_indices        = range(batch_start, batch_open_end)
        batch_data, batch_filenames = loader_object.load_preprocessed_batch_from_indices( batch_global_indices )

        ts_before_inference = time()

        run_options = onnxruntime.RunOptions()
        batch_results = sess.run(model_output_layers_bls, {model_input_layer_name: batch_data}, run_options)

        if extra_dimension_needed:  # adding an extra dimension (on for RetinaNet, off for Resnet34-SSD)
            batch_results = [[br] for br in batch_results]

        ts_after_inference  = time()

        batch_loading_s     = ts_before_inference - ts_before_data_loading
        batch_inference_s   = ts_after_inference - ts_before_inference
        list_batch_loading_s.append ( batch_loading_s )
        list_batch_inference_s.append( batch_inference_s )
        sum_loading_s      += batch_loading_s
        sum_inference_s    += batch_inference_s

        print(f"[batch {batch_num} of {batch_count}] loading={batch_loading_s*1000:.2f} ms, inference={batch_inference_s*1000:.2f} ms", file=sys.stderr)

        # Process results
        for index_in_batch, global_image_index in enumerate(batch_global_indices):
            width_orig, height_orig = loader_object.original_w_h[global_image_index]

            filename_orig = loader_object.image_filenames[global_image_index]
            image_name = os.path.splitext(filename_orig)[0]

            detections = []
            for i in range(len(batch_results[2][index_in_batch])):
                confidence = batch_results[2][index_in_batch][i]
                if confidence > SCORE_THRESHOLD:
                    class_number = int(batch_results[1][index_in_batch][i])
                    if class_map:
                        class_number = class_map[class_number]
                    else:
                        class_number = class_number

                    box = batch_results[0][index_in_batch][i]
                    x1 = box[0] / model_output_scale * width_orig
                    y1 = box[1] / model_output_scale * height_orig
                    x2 = box[2] / model_output_scale * width_orig
                    y2 = box[3] / model_output_scale * height_orig
                    class_label = class_labels[class_number - minimal_class_id]

                    detections.append({
                        "bbox":         [ round(float(x1),2), round(float(y1),2), round(float(x2),2), round(float(y2),2) ],
                        "score":        round(float(confidence),3),
                        "class_id":     class_number,
                        "class_name":   class_label,
                    })

            detection_results[image_name] = {
                "image_height": height_orig,
                "image_width":  width_orig,
                "detections":   detections,
            }

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
            "detections": detection_results,
        }
        json_string = json.dumps( output_dict , indent=4)
        with open(output_file_path, "w") as json_fd:
            json_fd.write( json_string+"\n" )
        print(f'Predictions for {num_of_images} images written into "{output_file_path}"', file=sys.stderr)

if __name__ == '__main__':
    main()

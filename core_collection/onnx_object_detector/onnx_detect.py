#!/usr/bin/env python3

"""A standalone Object Detection program based on ONNX.

Usage examples  :

                    # a short accuracy run:
                axs byquery script_output,detected_coco,framework=onnx,num_of_images=20 , mAP
"""

import os
import json
import sys
import math
from time import time

import numpy as np
import onnxruntime as rt
from coco_loader import CocoLoader

model_name                  = sys.argv[1]
model_path                  = sys.argv[2]
preprocessed_coco_dir       = sys.argv[3]
num_of_images               = int(sys.argv[4])
max_batch_size              = int(sys.argv[5])
execution_device            = sys.argv[6]           # if empty, it will be autodetected
cpu_threads                 = int(sys.argv[7])
coco_labels_file_path       = sys.argv[8]
output_file_path            = sys.argv[9]


## Model properties:
#
INPUT_LAYER_NAME    = "image"
OUTPUT_LAYER_BBOXES = "bboxes"
OUTPUT_LAYER_LABELS = "labels"
OUTPUT_LAYER_SCORES = "scores"

# Program parameters
SCORE_THRESHOLD     = 0


## Model properties:
#
MODEL_IMAGE_HEIGHT      = 1200
MODEL_IMAGE_WIDTH       = 1200
MODEL_IMAGE_CHANNELS    = 3
SKIPPED_CLASSES         = [12,26,29,30,45,66,68,69,71,83]


## Image normalization:
#
data_layout             = "NCHW"
normalize_symmetric     = False
subtract_mean_bool      = True
given_channel_means     = [0.485, 0.456, 0.406]
given_channel_stds      = [0.229, 0.224, 0.225]


## Preprocessed input images' properties:
#
IMAGE_LIST_FILE_NAME    = "original_dimensions.txt"
original_dims_file_path = os.path.join(preprocessed_coco_dir, IMAGE_LIST_FILE_NAME)
loader_object           = CocoLoader(preprocessed_coco_dir, original_dims_file_path, MODEL_IMAGE_HEIGHT, MODEL_IMAGE_WIDTH, data_layout, normalize_symmetric, subtract_mean_bool, given_channel_means, given_channel_stds)


def load_labels(labels_filepath):
    my_labels = []
    input_file = open(labels_filepath, 'r')
    for l in input_file:
        my_labels.append(l.strip())
    return my_labels

class_labels    = load_labels(coco_labels_file_path)
num_classes     = len(class_labels)
bg_class_offset = 1
class_map       = None
if (SKIPPED_CLASSES):
    class_map = []
    for i in range(num_classes + bg_class_offset):
        if i not in SKIPPED_CLASSES:
            class_map.append(i)


def main():
    global INPUT_LAYER_NAME, max_batch_size

    ts_before_model_loading = time()

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

    if "CUDAExecutionProvider" in session_execution_provider or "TensorrtExecutionProvider" in session_execution_provider:
        print("Device: GPU", file=sys.stderr)
    else:
        print("Device: CPU", file=sys.stderr)

    model_loading_s = time() - ts_before_model_loading

    input_layer_names = [x.name for x in sess.get_inputs()]     # FIXME: check that INPUT_LAYER_NAME belongs to this list
    INPUT_LAYER_NAME = INPUT_LAYER_NAME or input_layer_names[0]

    output_layer_names = [x.name for x in sess.get_outputs()]    # FIXME: check that OUTPUT_LAYER_NAME belongs to this list

    model_input_shape = sess.get_inputs()[0].shape
    model_input_type  = sess.get_inputs()[0].type
    model_input_type  = np.uint8 if model_input_type == 'tensor(uint8)' else np.float32     # FIXME: there must be a more humane way!

        # a more portable way to detect the number of classes
    for output in sess.get_outputs():
        if output.name == OUTPUT_LAYER_LABELS:
            model_classes = output.shape[1]


    print(f"Data layout: {data_layout}", file=sys.stderr)
    print(f"Input layers: {input_layer_names}", file=sys.stderr)
    print(f"Output layers: {output_layer_names}", file=sys.stderr)
    print(f"Input layer name: {INPUT_LAYER_NAME}", file=sys.stderr)
    print(f"Expected input shape: {model_input_shape}", file=sys.stderr)
    print(f"Expected input type: {model_input_type}", file=sys.stderr)
    print(f"Output layer names: {[OUTPUT_LAYER_BBOXES, OUTPUT_LAYER_LABELS, OUTPUT_LAYER_SCORES]}", file=sys.stderr)
    print(f"Background/unlabelled classes to skip: {bg_class_offset}", file=sys.stderr)
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

        run_options = rt.RunOptions()
        batch_results = sess.run([OUTPUT_LAYER_BBOXES, OUTPUT_LAYER_LABELS, OUTPUT_LAYER_SCORES], {INPUT_LAYER_NAME: batch_data}, run_options)

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
                    x1 = box[0] * width_orig
                    y1 = box[1] * height_orig
                    x2 = box[2] * width_orig
                    y2 = box[3] * height_orig
                    class_label = class_labels[class_number - bg_class_offset]

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
            "execution_device": execution_device,
            "model_name": model_name,
            "framework": "onnx",
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

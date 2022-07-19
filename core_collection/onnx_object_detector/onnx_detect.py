#!/usr/bin/env python3

import os
import json
import sys
import math
from time import time

import numpy as np
import onnxruntime as rt

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

## Processing in batches:
#
BATCH_SIZE              = 1
BATCH_COUNT             = 20
SKIP_IMAGES             = 0


## Model properties:
#
MODEL_IMAGE_HEIGHT      = 1200
MODEL_IMAGE_WIDTH       = 1200
MODEL_IMAGE_CHANNELS    = 3
MODEL_DATA_TYPE         = "(unknown)"
MODEL_DATA_LAYOUT       = "NCHW"
MODEL_COLOURS_BGR       = False
MODEL_INPUT_DATA_TYPE   = "float32"
MODEL_USE_DLA           = False
SKIPPED_CLASSES         = [12,26,29,30,45,66,68,69,71,83]


## Internal processing:
#
INTERMEDIATE_DATA_TYPE  = np.float32    # default for internal conversion
#INTERMEDIATE_DATA_TYPE  = np.int8       # affects the accuracy a bit


## Image normalization:
#
MODEL_NORMALIZE_DATA    = True
MODEL_NORMALIZE_LOWER   = 0
MODEL_NORMALIZE_UPPER   = 1
SUBTRACT_MEAN           = True
GIVEN_CHANNEL_MEANS     = [0.485, 0.456, 0.406]
GIVEN_CHANNEL_STDS      = [0.229, 0.224, 0.225]

## Preprocessed input images' properties:
#
IMAGE_LIST_FILE_NAME    = "original_dimensions.txt"
original_dims_file_path = os.path.join(preprocessed_coco_dir, IMAGE_LIST_FILE_NAME)
IMAGE_DATA_TYPE         = 'uint8'


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


# Load preprocessed image filenames:
with open(original_dims_file_path, 'r') as f:
    image_list = [s.strip() for s in f]

# Trim the input list of preprocessed files:
image_list = image_list[SKIP_IMAGES: BATCH_COUNT * BATCH_SIZE + SKIP_IMAGES]

# Creating a local list of processed files and parsing it:
image_filenames = []
original_w_h    = []
for line in image_list:
    file_name, width, height = line.split(";")
    image_filenames.append( file_name )
    original_w_h.append( (int(width), int(height)) )


def load_image_by_index_and_normalize(image_filename):
    img = np.fromfile(image_filename, np.dtype(IMAGE_DATA_TYPE))
    img = img.reshape((MODEL_IMAGE_HEIGHT, MODEL_IMAGE_WIDTH, MODEL_IMAGE_CHANNELS))
    if MODEL_COLOURS_BGR:
        img = img[...,::-1]     # swapping Red and Blue colour channels

    if IMAGE_DATA_TYPE != 'float32':
        img = img.astype(np.float32)

        # Normalize
        if MODEL_NORMALIZE_DATA:
            img = img*(MODEL_NORMALIZE_UPPER-MODEL_NORMALIZE_LOWER)/255.0+MODEL_NORMALIZE_LOWER

        # Subtract mean value
        if SUBTRACT_MEAN:
            if len(GIVEN_CHANNEL_MEANS):
                img -= GIVEN_CHANNEL_MEANS
            else:
                img -= np.mean(img, axis=(0,1), keepdims=True)

        if len(GIVEN_CHANNEL_STDS):
            img /= GIVEN_CHANNEL_STDS

    if MODEL_INPUT_DATA_TYPE == 'int8' or INTERMEDIATE_DATA_TYPE==np.int8:
        img = np.clip(img, -128, 127).astype(INTERMEDIATE_DATA_TYPE)

    if MODEL_DATA_LAYOUT == 'NCHW':
        img = img.transpose(2,0,1)
    elif MODEL_DATA_LAYOUT == 'CHW4':
        img = np.pad(img, ((0,0), (0,0), (0,1)), 'constant')

    # Add img to batch
    return img.astype(MODEL_INPUT_DATA_TYPE)


def load_preprocessed_batch(batch_filenames):
    batch_data = None
    for index_in_batch, image_filename in enumerate(batch_filenames):
        img = load_image_by_index_and_normalize(image_filename)
        if batch_data is None:
            batch_data = np.empty( (max_batch_size, *img.shape), dtype=MODEL_INPUT_DATA_TYPE)
        batch_data[index_in_batch] = img

    #print('Data shape: {}'.format(batch_data.shape))

    if MODEL_USE_DLA and MODEL_MAX_BATCH_SIZE>len(batch_data):
        return np.pad(batch_data, ((0,MODEL_MAX_BATCH_SIZE-len(batch_data)), (0,0), (0,0), (0,0)), 'constant')
    else:
        return batch_data



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


    print(f"Data layout: {MODEL_DATA_LAYOUT}", file=sys.stderr)
    print(f"Input layers: {input_layer_names}", file=sys.stderr)
    print(f"Output layers: {output_layer_names}", file=sys.stderr)
    print(f"Input layer name: {INPUT_LAYER_NAME}", file=sys.stderr)
    print(f"Expected input shape: {model_input_shape}", file=sys.stderr)
    print(f"Expected input type: {model_input_type}", file=sys.stderr)
    print(f"Output layer names: {[OUTPUT_LAYER_BBOXES, OUTPUT_LAYER_LABELS, OUTPUT_LAYER_SCORES]}", file=sys.stderr)
    print(f"Data normalization: {MODEL_NORMALIZE_DATA}", file=sys.stderr)
    print(f"Background/unlabelled classes to skip: {bg_class_offset}", file=sys.stderr)
    print("", file=sys.stderr)

    try:
        expected_batch_size = int(model_input_shape[0])
        if max_batch_size!=expected_batch_size:
            raise Exception(f"expected_batch_size={expected_batch_size}, desired max_batch_size={max_batch_size}, they do not match - exiting.")
    except ValueError:
        max_batch_size = None

    # Run batched mode
    images_loaded           = 0
    next_batch_offset       = 0

    batch_count             = math.ceil(num_of_images / max_batch_size)
    batch_num               = 0

    sum_loading_s           = 0
    sum_inference_s         = 0
    list_batch_loading_s    = []
    list_batch_inference_s  = []
    detection_results       = {}

    for batch_start in range(0, num_of_images, max_batch_size):
        batch_num = batch_num + 1
        batch_open_end = min(batch_start+max_batch_size, num_of_images)

        ts_before_data_loading  = time()

        batch_global_indices = range(batch_start, batch_open_end)
        batch_filenames      = [ os.path.join(preprocessed_coco_dir, image_filenames[g]) for g in batch_global_indices ]

        batch_data           = load_preprocessed_batch(batch_filenames)
        images_loaded       += batch_open_end - batch_start

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
            width_orig, height_orig = original_w_h[global_image_index]

            filename_orig = image_filenames[global_image_index]
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

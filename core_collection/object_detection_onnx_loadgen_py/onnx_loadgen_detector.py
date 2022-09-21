#!/usr/bin/env python3

"""Loadgen-wired Object Detection program based on ONNX.

Usage examples  :

                    # a short accuracy run:
                axs byquery loadgen_output,detected_coco,framework=onnx,loadgen_dataset_size=20 , get mAP

                    # a short accuracy run with RetinaNet model:
                axs byquery loadgen_output,detected_coco,framework=onnx,loadgen_dataset_size=20,model_name=retinanet_coco , get mAP
"""

import array
import os
import sys
import time

import numpy as np
import onnxruntime as rt
from coco_loader import CocoLoader

import mlperf_loadgen as lg


scenario_str                = sys.argv[1]
mode_str                    = sys.argv[2]
dataset_size                = int(sys.argv[3])
buffer_size                 = int(sys.argv[4])
count_override_str          = sys.argv[5]
mlperf_conf_path            = sys.argv[6]
user_conf_path              = sys.argv[7]
verbosity                   = int( sys.argv[8] )

model_name                  = sys.argv[9]
model_path                  = sys.argv[10]
model_resolution            = int(sys.argv[11])
model_output_scale          = float(sys.argv[12])
model_input_layer_name      = sys.argv[13]
model_output_layers_bls     = eval(sys.argv[14])
model_skipped_classes       = eval(sys.argv[15])
normalize_symmetric         = eval(sys.argv[16])    # FIXME: currently we are passing a stringified form of a data structure,
subtract_mean_bool          = eval(sys.argv[17])    # it would be more flexible to encode/decode through JSON instead.
given_channel_means         = eval(sys.argv[18])
given_channel_stds          = eval(sys.argv[19])

preprocessed_coco_dir       = sys.argv[20]
coco_labels_file_path       = sys.argv[21]
execution_device            = sys.argv[22]          # if empty, it will be autodetected
batch_size                  = int( sys.argv[23])
cpu_threads                 = int( sys.argv[24])

minimal_class_id            = int( sys.argv[25])


## Model parameters:
#
data_layout                 = "NCHW"
MODEL_INPUT_DATA_TYPE       = 'float32'


# Program parameters:
#
SCORE_THRESHOLD             = 0


## Preprocessed input images' properties:
#
IMAGE_LIST_FILE_NAME    = "original_dimensions.txt"
original_dims_file_path = os.path.join(preprocessed_coco_dir, IMAGE_LIST_FILE_NAME)
loader_object           = CocoLoader(preprocessed_coco_dir, original_dims_file_path, model_resolution, model_resolution, data_layout, normalize_symmetric, subtract_mean_bool, given_channel_means, given_channel_stds)


def load_labels(labels_filepath):
    my_labels = []
    input_file = open(labels_filepath, 'r')
    for l in input_file:
        my_labels.append(l.strip())
    return my_labels

class_labels    = load_labels(coco_labels_file_path)
num_classes     = len(class_labels)
class_map       = None
if (model_skipped_classes):
    class_map = []
    for i in range(num_classes + minimal_class_id):
        if i not in model_skipped_classes:
            class_map.append(i)

preprocessed_image_buffer   = None
preprocessed_image_map      = np.empty(dataset_size, dtype=np.int)   # this type should be able to hold indices in range 0:dataset_size


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


for output in sess.get_outputs():
    print(f"output.name={output.name} , output.shape={output.shape} , output.type={output.type}")
    if output.name == model_output_layers_bls[0]:
        extra_dimension_needed = len(output.shape)<3



def tick(letter, quantity=1):
    if verbosity:
        print(letter + (str(quantity) if quantity>1 else ''), end='')


def load_query_samples(sample_indices):     # 0-based indices in our whole dataset
    global preprocessed_image_buffer

    if verbosity > 1:
        print("load_query_samples({})".format(sample_indices))

    len_sample_indices = len(sample_indices)

    tick('B', len_sample_indices)

    if preprocessed_image_buffer is None:     # only do this once, once we know the expected size of the buffer
        preprocessed_image_buffer = np.empty((len_sample_indices, 3, model_resolution, model_resolution), dtype=MODEL_INPUT_DATA_TYPE)

    for buffer_index, sample_index in zip(range(len_sample_indices), sample_indices):
        preprocessed_image_map[sample_index] = buffer_index
        preprocessed_image_buffer[buffer_index] = np.array( loader_object.load_image_by_index_and_normalize(sample_index)[0] )

        tick('l')

    if verbosity:
        print('')


def unload_query_samples(sample_indices):
    #print("unload_query_samples({})".format(sample_indices))
    tick('U')

    if verbosity:
        print('')


def issue_queries(query_samples):

    if verbosity > 2:
        printable_query = [(qs.index, qs.id) for qs in query_samples]
        print("issue_queries( {} )".format(printable_query))
    tick('Q', len(query_samples))

    run_options = rt.RunOptions()

    for j in range(0, len(query_samples), batch_size):
        batch       = query_samples[j:j+batch_size]   # NB: the last one may be shorter than batch_size in length
        batch_data  = preprocessed_image_buffer[preprocessed_image_map[ [qs.index for qs in batch] ]]

        begin_time = time.time()

        batch_results = sess.run(model_output_layers_bls, {model_input_layer_name: batch_data}, run_options)

        if extra_dimension_needed:  # adding an extra dimension (on for RetinaNet, off for Resnet34-SSD)
            batch_results = [[br] for br in batch_results]

        inference_time_s = time.time() - begin_time

        actual_batch_size = len(batch)
        if verbosity > 1:
            print("[batch of {}] inference={:.2f} ms".format(actual_batch_size, inference_time_s*1000))

        tick('p', actual_batch_size)
        if verbosity > 2:
            print("predicted_batch_results = {}".format(batch_results))

        response = []
        response_array_refs = []    # This is needed to guarantee that the individual buffers to which we keep extra-Pythonian references, do not get garbage-collected.

        for index_in_batch, qs in enumerate(batch):
            global_image_index      = qs.index

            reformed_active_boxes_for_this_sample = []
            for i in range(len(batch_results[2][index_in_batch])):
                confidence_score = batch_results[2][index_in_batch][i]
                if confidence_score > SCORE_THRESHOLD:
                    class_number = int(batch_results[1][index_in_batch][i])
                    if class_map:
                        class_number = class_map[class_number]

                    (x1, y1, x2, y2) = batch_results[0][index_in_batch][i]

                    reformed_active_boxes_for_this_sample += [
                        float(global_image_index), y1/model_output_scale, x1/model_output_scale, y2/model_output_scale, x2/model_output_scale, confidence_score, class_number ]

            response_array = array.array("B", np.array(reformed_active_boxes_for_this_sample, np.float32).tobytes())
            response_array_refs.append(response_array)
            bi = response_array.buffer_info()
            response.append(lg.QuerySampleResponse(qs.id, bi[0], bi[1]))
        lg.QuerySamplesComplete(response)
        #tick('R', len(response))
    sys.stdout.flush()


def flush_queries():
    pass


def benchmark_using_loadgen():
    "Perform the benchmark using python API for the LoadGen library"

    scenario = {
        'SingleStream':     lg.TestScenario.SingleStream,
        'MultiStream':      lg.TestScenario.MultiStream,
        'Server':           lg.TestScenario.Server,
        'Offline':          lg.TestScenario.Offline,
    }[scenario_str]

    mode = {
        'AccuracyOnly':     lg.TestMode.AccuracyOnly,
        'PerformanceOnly':  lg.TestMode.PerformanceOnly,
        'SubmissionRun':    lg.TestMode.SubmissionRun,
    }[mode_str]

    ts = lg.TestSettings()
    if(mlperf_conf_path):
        ts.FromConfig(mlperf_conf_path, model_name, scenario_str)
    if(user_conf_path):
        ts.FromConfig(user_conf_path, model_name, scenario_str)

    ts.scenario = scenario
    ts.mode     = mode

    if count_override_str:
        ts.min_query_count = int(count_override_str)
        ts.max_query_count = int(count_override_str)

    sut = lg.ConstructSUT(issue_queries, flush_queries)
    qsl = lg.ConstructQSL(dataset_size, buffer_size, load_query_samples, unload_query_samples)

    log_settings = lg.LogSettings()
    log_settings.enable_trace = False
    lg.StartTestWithLogSettings(sut, qsl, ts, log_settings)

    lg.DestroyQSL(qsl)
    lg.DestroySUT(sut)


try:
    benchmark_using_loadgen()
except Exception as e:
    print('{}'.format(e))


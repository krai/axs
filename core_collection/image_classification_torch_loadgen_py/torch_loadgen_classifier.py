#!/usr/bin/env python3

"""Loadgen-based Image Classification program based on Pytorch.

Usage examples  :

                    # full Accuracy run (query mode) :
                axs byquery loadgen_output,classified_imagenet,framework=pytorch,preprocessed_imagenet_dir=/datasets/imagenet/pillow_sq.224_cropped_resized_imagenet50000,loadgen_scenario=Offline,loadgen_dataset_size=50000,loadgen_buffer_size=1000,batch_size=1000 , get accuracy
"""

import array
import os
import sys
import time

import numpy as np
import torch
from imagenet_loader import ImagenetLoader
import mlperf_loadgen as lg


scenario_str                = sys.argv[1]
mode_str                    = sys.argv[2]
dataset_size                = int(sys.argv[3])
buffer_size                 = int(sys.argv[4])
multistreamness_str         = sys.argv[5]
count_override_str          = sys.argv[6]
config_filepath             = sys.argv[7]
verbosity                   = int( sys.argv[8] )
model_name                  = sys.argv[9]
batch_size                  = int( sys.argv[10] )
preprocessed_imagenet_dir   = sys.argv[11]


use_cuda                    = torch.cuda.is_available()
MODEL_IMAGE_CHANNELS        = 3
MODEL_IMAGE_HEIGHT          = 224
MODEL_IMAGE_WIDTH           = 224
MODEL_INPUT_DATA_TYPE       = 'float32'
data_layout                 = 'NCHW'

normalize_symmetric         = False # ternary choice (False means "asymmetric normalization ON")
subtract_mean_bool          = True
given_channel_means         = [0.485, 0.456, 0.406]
given_channel_stds          = [0.229, 0.224, 0.225]

loader_object               = ImagenetLoader(preprocessed_imagenet_dir, MODEL_IMAGE_HEIGHT, MODEL_IMAGE_WIDTH, data_layout, normalize_symmetric, subtract_mean_bool, given_channel_means, given_channel_stds)
preprocessed_image_buffer   = None
preprocessed_image_map      = np.empty(dataset_size, dtype=np.int)   # this type should be able to hold indices in range 0:dataset_size
model                       = None


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
        preprocessed_image_buffer = np.empty((len_sample_indices, MODEL_IMAGE_CHANNELS, MODEL_IMAGE_HEIGHT, MODEL_IMAGE_WIDTH), dtype=MODEL_INPUT_DATA_TYPE)

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

    global model

    if verbosity > 2:
        printable_query = [(qs.index, qs.id) for qs in query_samples]
        print("issue_queries( {} )".format(printable_query))
    tick('Q', len(query_samples))

    for j in range(0, len(query_samples), batch_size):
        batch       = query_samples[j:j+batch_size]   # NB: the last one may be shorter than batch_size in length
        batch_data  = preprocessed_image_buffer[preprocessed_image_map[ [qs.index for qs in batch] ]]
        torch_batch = torch.from_numpy( batch_data )

        begin_time = time.time()

        # move the input to GPU for speed if available
        if use_cuda:
            torch_batch = torch_batch.to('cuda')

        with torch.no_grad():
            trimmed_batch_results = model( torch_batch )

        inference_time_s = time.time() - begin_time

        actual_batch_size = len(trimmed_batch_results)

        if verbosity > 1:
            print("[batch of {}] inference={:.2f} ms".format(actual_batch_size, inference_time_s*1000))

        batch_predicted_labels  = torch.argmax(trimmed_batch_results, dim=1).tolist()

        tick('p', len(batch))
        if verbosity > 2:
            print("predicted_batch_results = {}".format(batch_predicted_labels))

        response = []
        response_array_refs = []    # This is needed to guarantee that the individual buffers to which we keep extra-Pythonian references, do not get garbage-collected.
        for qs, predicted_label in zip(batch, batch_predicted_labels):

            response_array = array.array("B", np.array(predicted_label, np.float32).tobytes())
            response_array_refs.append(response_array)
            bi = response_array.buffer_info()
            response.append(lg.QuerySampleResponse(qs.id, bi[0], bi[1]))
        lg.QuerySamplesComplete(response)
        #tick('R', len(response))
    sys.stdout.flush()



def flush_queries():
    pass



def process_latencies(latencies_ns):
    latencies_ms = [ (ns * 1e-6) for ns in latencies_ns ]
    print("LG called process_latencies({})".format(latencies_ms))

    if scenario_str == 'Offline':
        latencies_ms   = (np.asarray(latencies_ms) - np.asarray([0] + latencies_ms[:-1])).tolist()
        print("Offline latencies transformed to absolute time: {}".format(latencies_ms))

    latencies_size      = len(latencies_ms)
    latencies_avg       = int(sum(latencies_ms)/latencies_size)
    latencies_sorted    = sorted(latencies_ms)
    latencies_p50       = int(latencies_size * 0.5);
    latencies_p90       = int(latencies_size * 0.9);
    latencies_p99       = int(latencies_size * 0.99);

    print("--------------------------------------------------------------------")
    print("|                LATENCIES (in milliseconds and fps)               |")
    print("--------------------------------------------------------------------")
    print("Number of samples run:       {:9d}".format(latencies_size))
    print("Min latency:                 {:9.2f} ms   ({:.3f} fps)".format(latencies_sorted[0], 1e3/latencies_sorted[0]))
    print("Median latency:              {:9.2f} ms   ({:.3f} fps)".format(latencies_sorted[latencies_p50], 1e3/latencies_sorted[latencies_p50]))
    print("Average latency:             {:9.2f} ms   ({:.3f} fps)".format(latencies_avg, 1e3/latencies_avg))
    print("90 percentile latency:       {:9.2f} ms   ({:.3f} fps)".format(latencies_sorted[latencies_p90], 1e3/latencies_sorted[latencies_p90]))
    print("99 percentile latency:       {:9.2f} ms   ({:.3f} fps)".format(latencies_sorted[latencies_p99], 1e3/latencies_sorted[latencies_p99]))
    print("Max latency:                 {:9.2f} ms   ({:.3f} fps)".format(latencies_sorted[-1], 1e3/latencies_sorted[-1]))
    print("--------------------------------------------------------------------")



def benchmark_using_loadgen():
    "Perform the benchmark using python API for the LoadGen library"

    global model

    # Load the [cached] Torch model
    torchvision_version = ''    # master by default
    try:
        import torchvision
        torchvision_version = ':v' + torchvision.__version__.split('+')[0]
    except Exception:
        pass

    model = torch.hub.load('pytorch/vision' + torchvision_version, model_name, pretrained=True)
    model.eval()

    # move the model to GPU for speed if available
    if use_cuda:
        model.to('cuda')


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
    if(config_filepath):
        ts.FromConfig(config_filepath, model_name, scenario_str)
    ts.scenario = scenario
    ts.mode     = mode

    if multistreamness_str:
        ts.multi_stream_samples_per_query = int(multistreamness_str)

    if count_override_str:
        ts.min_query_count = int(count_override_str)
        ts.max_query_count = int(count_override_str)

    sut = lg.ConstructSUT(issue_queries, flush_queries, process_latencies)
    qsl = lg.ConstructQSL(dataset_size, buffer_size, load_query_samples, unload_query_samples)


    sut = lg.ConstructSUT(issue_queries, flush_queries, process_latencies)
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


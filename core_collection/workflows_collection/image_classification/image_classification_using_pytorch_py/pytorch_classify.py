#!/usr/bin/env python3

"""An example Python script that is given its data, necessary Python environment and the output path by wrapping it into an Entry.

Usage examples :
                    # execution_device can be cpu, gpu, cuda.
                    # as a side-effect, automatically downloads and extracts Imagenet500:
                axs byname pytorch_image_classifier , run --execution_device=cpu --num_of_images=100

                    # reuses the Imagenet500 already downloaded & extracted:
                axs byname pytorch_image_classifier , run --num_of_images=500

                    # quick removal of Imagenet500:
                axs byquery extracted,imagenet,dataset_size=500 , remove

                    # assuming Imagenet50k in a directory:
                axs byname pytorch_image_classifier , run --preprocessed_imagenet_dir=/datasets/imagenet/pillow_sq.224_cropped_resized_imagenet50000 --num_of_images=800 --dataset_size=50000

                    # same, but in query mode (full dataset), computing the accuracy as well:
                axs byquery program_output,classified_imagenet,framework=pytorch,preprocessed_imagenet_dir=/datasets/imagenet/pillow_sq.224_cropped_resized_imagenet50000,num_of_images=50000,max_batch_size=1000 , get accuracy

                    # assuming Imagenet50k in a tarball:
                axs byname extractor , extract --archive_path=/datasets/dataset-imagenet-ilsvrc2012-val.tar --tags,=extracted,imagenet --strip_components=1 --dataset_size=50000
                axs byname pytorch_image_classifier , run --num_of_images=1000

                    # assuming Imagenet50k is already installed from a tarball, but still wanting to use Imagenet500:
                axs byname pytorch_image_classifier , run --imagenet_query+=dataset_size=500 --num_of_images=350

                    # as a side-effect, automatically downloads and extracts Imagenet500 and save output to file experiment.json:
                axs byname pytorch_image_classifier , run --execution_device=gpu --num_of_images=100 --output_file_path=experiment.json

                    # set top_n_max ( number of predictions for each image ) which is added to output_file. By default top_n_max = 10
                axs byquery program_output,task=image_classification,framework=pytorch,num_of_images=32 , top_n_max=6

                    # get accuracy
                axs byquery program_output,task=image_classification,framework=pytorch,num_of_images=32 , get accuracy

                    # get n predictions for each image
                axs byquery program_output,task=image_classification,framework=pytorch,num_of_images=32 , get print_top_n_predictions

"""

import os
import sys

print(f"\n**\nRUNNING {__file__} under {sys.executable} with sys.path={sys.path}\n**\n", file=sys.stderr)

import json
import math
from time import time, sleep
from urllib.error import HTTPError

input_file_path = sys.argv[1]
output_file_path =  sys.argv[2]

with open(input_file_path) as f:
    input_parameters = json.load(f)


preprocessed_imagenet_dir   = input_parameters["preprocessed_images_dir"]
resolution                  = input_parameters["resolution"]
num_of_images               = input_parameters["num_of_images"]
model_name                  = input_parameters["model_name"]

execution_device            = input_parameters["execution_device"]       # if empty, it will be autodetected
max_batch_size              = input_parameters["max_batch_size"]
top_n_max                   = input_parameters["top_n_max"]
input_file_list             = input_parameters["input_file_list"]

file_pattern                = 'ILSVRC2012_val_000{:05d}.rgb8'
max_attempts                = 3
retry_in_seconds            = 20
batch_count                 = math.ceil(num_of_images / max_batch_size)

# sample execution (requires torchvision)
import torch
import torchvision
from torchvision import transforms
import numpy as np
from imagenet_loader import ImagenetLoader

if execution_device == "gpu":
    execution_device = ('cuda' if torch.cuda.is_available() else 'cpu')
else:
    execution_device = execution_device or ('cuda' if torch.cuda.is_available() else 'cpu')  # autodetection

torchvision_version = ':v' + torchvision.__version__.split('+')[0]

if execution_device == "cuda":
    print("Device: GPU", file=sys.stderr)
else:
    print("Device: CPU", file=sys.stderr)

data_layout         = 'NCHW'
normalize_symmetric = False # ternary choice (False means "asymmetric normalization ON")
subtract_mean_bool  = True
given_channel_means = [0.485, 0.456, 0.406]
given_channel_stds  = [0.229, 0.224, 0.225]
loader_object       = ImagenetLoader(preprocessed_imagenet_dir, input_file_list, resolution, resolution, data_layout, normalize_symmetric, subtract_mean_bool, given_channel_means, given_channel_stds)


ts_before_model_loading = time()

for retry in range(max_attempts):
    try:
        if retry>0:
            print(f"Retry #{retry} in {retry_in_seconds} seconds", file=sys.stderr)
            sleep(retry_in_seconds)
            print("Retrying now", file=sys.stderr)

        model = torch.hub.load('pytorch/vision' + torchvision_version, model_name, pretrained=True)
        break
    except HTTPError as e:
        print(str(e), file=sys.stderr)


model.eval()
model.to( execution_device )

model_loading_s = time() - ts_before_model_loading

predictions             = {}
sum_loading_s           = 0
sum_inference_s         = 0
list_batch_loading_s    = []
list_batch_inference_s  = []
top_n_predictions       = {}
batch_num = 0

for batch_start in range(0,num_of_images, max_batch_size):
    batch_num = batch_num + 1
    batch_open_end = min(batch_start+max_batch_size, num_of_images)
    ts_before_data_loading  = time()

    pre_batch, batch_filenames = loader_object.load_preprocessed_batch_from_indices( range(batch_start, batch_open_end) )
    input_batch = torch.from_numpy( pre_batch )
    input_batch = input_batch.to( execution_device )

    ts_before_inference     = time()

    with torch.no_grad():
        output = model(input_batch)

    # The output has unnormalized scores. To get probabilities, you can run a softmax on it.
    #print(torch.nn.functional.softmax(output[0], dim=0))
    
    class_numbers = torch.argmax(output, dim=1).tolist()
    ts_after_inference      = time()

    stripped_batch_filenames    = [file_name.rsplit('.', 1)[0] for file_name in batch_filenames]
    predictions.update( dict(zip(stripped_batch_filenames, class_numbers)) )
    
    batch_loading_s     = ts_before_inference - ts_before_data_loading
    batch_inference_s   = ts_after_inference - ts_before_inference

    list_batch_loading_s.append ( batch_loading_s )
    list_batch_inference_s.append( batch_inference_s )

    sum_loading_s   += batch_loading_s
    sum_inference_s += batch_inference_s

    weight_norm_batch = torch.nn.functional.softmax(output, dim=1)
    top_weight_1000, top_classId_1000 = torch.topk(weight_norm_batch, top_n_max, dim=1)
    top_weight_1000 = top_weight_1000.cpu().tolist()
    top_classId_1000 = top_classId_1000.cpu().tolist()

    print(f"batch {batch_num}/{batch_count}: ({batch_start+1}..{batch_open_end}) {class_numbers}")

    for i in range(batch_open_end-batch_start):
        top_n_predictions[stripped_batch_filenames[i]] = dict(zip(top_classId_1000[i], top_weight_1000[i]))


if output_file_path:
    output_dict = {
        "execution_device": execution_device,
        "model_name": model_name,
        "framework": "pytorch",
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

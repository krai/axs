#!/usr/bin/env python3

import json
import math
import os
import pickle
import subprocess
import sys
import numpy as np
import onnxruntime

bert_code_root      = sys.argv[1]
bert_squad_code_dir = sys.argv[2]

sys.path.insert(0, bert_code_root)
sys.path.insert(0, bert_squad_code_dir)

## SQuAD dataset - original and tokenized
#
squad_dataset_original_path     = sys.argv[3]
squad_dataset_tokenized_path    = sys.argv[4]

## BERT model:
#
bert_model_path                 = sys.argv[5]
model_input_layers_tms          = eval(sys.argv[6])

## Processing by batches:
#
batch_size       = int(sys.argv[7])
batch_count      = int(sys.argv[8])
execution_device = sys.argv[9]
output_file_path = sys.argv[10]

output_logits_dict = {}

sess_options = onnxruntime.SessionOptions()

if execution_device == "cpu":
    requested_provider = "CPUExecutionProvider"
elif execution_device in ["gpu", "cuda"]:
    requested_provider = "CUDAExecutionProvider"

print("Loading BERT model and weights from {} ...".format(bert_model_path))
sess = onnxruntime.InferenceSession(bert_model_path, sess_options, providers= [requested_provider] if execution_device else onnxruntime.get_available_providers())

session_execution_provider=sess.get_providers()
print("Session execution provider: ", sess.get_providers(), file=sys.stderr)

if "CUDAExecutionProvider" in session_execution_provider or "TensorrtExecutionProvider" in session_execution_provider:
    print("Device: GPU", file=sys.stderr)
else:
    print("Device: CPU", file=sys.stderr)

print("Loading tokenized SQuAD dataset as features from {} ...".format(squad_dataset_tokenized_path))
with open(squad_dataset_tokenized_path, 'rb') as tokenized_features_file:
    eval_features = pickle.load(tokenized_features_file)

print("Example width: {}".format(len(eval_features[0].input_ids)))

total_examples  = len(eval_features)
print("Total examples available: {}".format(total_examples))
if batch_count<1:
    batch_count = math.ceil(total_examples/batch_size)
    selected_size = total_examples
else:
    selected_size = batch_count * batch_size

encoded_accuracy_log = []
for batch_index in range(batch_count):

    if (batch_index+1)*batch_size <= total_examples:    # regular batch
        this_batch_size = batch_size
    else:
        this_batch_size = total_examples % batch_size   # last incomplete batch of a full dataset run

    input_ids_stack     = []
    input_mask_stack    = []
    segment_ids_stack   = []

    for index_in_batch in range(this_batch_size):
        global_index = batch_index * batch_size + index_in_batch
        selected_feature = eval_features[global_index]

        input_ids_stack.append( np.array(selected_feature.input_ids) )
        input_mask_stack.append( np.array(selected_feature.input_mask) )
        segment_ids_stack.append( np.array(selected_feature.segment_ids) )

    batch_input_dict = dict(zip(
        model_input_layers_tms,
        [
            np.stack( input_ids_stack ).astype(np.int64),
            np.stack( input_mask_stack ).astype(np.int64),
            np.stack( segment_ids_stack ).astype(np.int64),
        ]
    ))
    scores = sess.run([o.name for o in sess.get_outputs()], batch_input_dict)
    output_logits = np.stack(scores, axis=-1)

    for index_in_batch in range(this_batch_size):
        global_index = batch_index * batch_size + index_in_batch
        output_logits_dict[ global_index ] = output_logits[index_in_batch].tolist()

if output_file_path:
    output_dict = {
        "squad_dataset_original_path": squad_dataset_original_path ,
        "squad_dataset_tokenized_path": squad_dataset_tokenized_path ,
        "selected_size": selected_size,
        "output_logits": output_logits_dict
        }

    json_string = json.dumps( output_dict , indent=4)
    with open(output_file_path, "w") as json_fd:
        json_fd.write( json_string+"\n" )

#!/usr/bin/env python3

import json
import math
import os
import pickle
import subprocess
import sys
import numpy as np
import onnxruntime

bert_code_root = sys.argv[1] +'/language/bert'

sys.path.insert(0, bert_code_root)
sys.path.insert(0, bert_code_root + '/DeepLearningExamples/TensorFlow/LanguageModeling/BERT')


## SQuAD dataset - original and tokenized
#
squad_dataset_original_path  = sys.argv[2]
squad_dataset_tokenized_path = sys.argv[3]

## BERT model:
#
bert_model_path = sys.argv[4]

## Processing by batches:
#
batch_size       = int(sys.argv[5])
batch_count      = int(sys.argv[6])
execution_device = sys.argv[7]

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

    batch_input_dict = {
        "input_ids":    np.stack( input_ids_stack ).astype(np.int64),
        "input_mask":   np.stack( input_mask_stack ).astype(np.int64),
        "segment_ids":  np.stack( segment_ids_stack ).astype(np.int64),
    }
    scores = sess.run([o.name for o in sess.get_outputs()], batch_input_dict)

    batch_output = np.stack(scores, axis=-1)

    for index_in_batch in range(this_batch_size):
        global_index = batch_index * batch_size + index_in_batch
        encoded_accuracy_log.append({'qsl_idx': global_index, 'data': batch_output[index_in_batch].tobytes().hex()})

    print("Batch[{}] #{}/{} done".format(this_batch_size, batch_index+1, batch_count))


with open('accuracy_log.json', 'w') as accuracy_log_file:
    json.dump(encoded_accuracy_log, accuracy_log_file)

cmd = "python3 "+bert_code_root+"/accuracy-squad.py --val_data={} --features_cache_file={} --log_file=accuracy_log.json --out_file=predictions.json --max_examples={}".format(squad_dataset_original_path, squad_dataset_tokenized_path, selected_size)
subprocess.check_call(cmd, shell=True)

#!/usr/bin/env python3

import os
import sys

from transformers import BertTokenizer

# Input and output file paths:
squad_original_path             = sys.argv[1]
tokenization_vocab_path         = sys.argv[2]
tokenized_squad_dir             = sys.argv[3]
tokenized_squad_files_prefix    = sys.argv[4]

# Tokenization parameters:
max_seq_length                  = int(sys.argv[5])
max_query_length                = int(sys.argv[6])
doc_stride                      = int(sys.argv[7])

calibration                     = sys.argv[10] == "yes"
if calibration:
    calibration_option          = sys.argv[11]
    calibration_data_path       = sys.argv[12]

from create_squad_data import read_squad_examples, convert_examples_to_features

print("Creating the tokenizer from {} ...".format(tokenization_vocab_path))
tokenizer = BertTokenizer(tokenization_vocab_path)

print("Reading examples from {} ...".format(squad_original_path))
examples = read_squad_examples(input_file=squad_original_path, is_training=False, version_2_with_negative=False)

if calibration:
    print("Calibrating dataset with examples in ", calibration_data_path)
    if calibration_option == "features":
        calib_examples = []
        with open(calibration_data_path, 'r') as fp:
            for example in fp:
                calib_examples.append(examples[int(example)])
            examples = calib_examples
    else: #qas_id
        examples_ids_dict = {}
        for candidate in examples:
            examples_ids_dict[candidate.qas_id] = candidate

        calib_examples = []
        with open(calibration_data_path, 'r') as fp:
            for example in fp:
                qas_id = example.strip()
                try:
                    calib_examples.append(examples_ids_dict[qas_id])
                except:
                    print(f"qas_id {qas_id} from calibration file doesn't exist in original dataset")
                    continue
            examples = calib_examples

eval_features = []
def append_feature(feature):
    eval_features.append(feature)

print("Tokenizing examples to features (max_seq_length={}, max_query_length={}, doc_stride={}) ...".format(max_seq_length, max_query_length, doc_stride))
convert_examples_to_features(
    examples=examples,
    tokenizer=tokenizer,
    max_seq_length=max_seq_length,
    doc_stride=doc_stride,
    max_query_length=max_query_length,
    is_training=False,
    output_fn=append_feature,
    verbose_logging=False)


# raw

import numpy as np

print("Recording features to {} ...".format(tokenized_squad_dir + "*.raw"))

num_features = len(eval_features)
input_ids = np.zeros((num_features, max_seq_length), dtype=np.int64)
input_mask = np.zeros((num_features, max_seq_length), dtype=np.int64)
segment_ids = np.zeros((num_features, max_seq_length), dtype=np.int64)

for idx, feature in enumerate(eval_features):

    if len(feature.input_ids) != 384:
        print(len(feature.input_ids))
    input_ids[idx, :] = np.array(feature.input_ids, dtype=np.int64)
    input_mask[idx, :] = np.array(feature.input_mask, dtype=np.int64)
    segment_ids[idx, :] = np.array(feature.segment_ids, dtype=np.int64)

input_ids.astype('int64').tofile(tokenized_squad_dir + tokenized_squad_files_prefix + "_input_ids.raw")
input_mask.astype('int64').tofile(tokenized_squad_dir + tokenized_squad_files_prefix + "_input_mask.raw")
segment_ids.astype('int64').tofile(tokenized_squad_dir + tokenized_squad_files_prefix + "_segment_ids.raw")

# pickle

import pickle
    
print("Recording features to {} ...".format(tokenized_squad_dir + tokenized_squad_files_prefix + ".pickled"))
with open(tokenized_squad_dir + tokenized_squad_files_prefix + ".pickled", 'wb') as cache_file:
    pickle.dump(eval_features, cache_file)



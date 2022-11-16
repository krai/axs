#!/usr/bin/env python3

#import numpy as np
import os
import sys
import torch
from transformers import BertConfig, BertForQuestionAnswering, BertTokenizer

## Model config and weights, loaded from the transformers' hub by name:
#
BERT_MODEL_NAME          = sys.argv[1]

## Text inputs (not optional):
#
BERT_DATA_CONTEXT_PATH   = sys.argv[2]
BERT_DATA_QUESTIONS_PATH = sys.argv[3]

# DEBUG availability
#
DEBUG_LEVEL              = int(sys.argv[4])

EXECUTION_DEVICE         = sys.argv[5] 
## Enabling GPU if available and not disabled:
#
#USE_CUDA                = torch.cuda.is_available() and (os.getenv('CK_DISABLE_CUDA', '0') in ('NO', 'no', 'OFF', 'off', '0'))
#TORCH_DEVICE            = 'cuda:0' if USE_CUDA else 'cpu'
#print("Torch execution device: "+TORCH_DEVICE)

if EXECUTION_DEVICE == "gpu":
    EXECUTION_DEVICE = ('cuda' if torch.cuda.is_available() else 'cpu')
else:
    EXECUTION_DEVICE = EXECUTION_DEVICE or ('cuda' if torch.cuda.is_available() else 'cpu')  # autodetection

if EXECUTION_DEVICE == "cuda":
    TORCH_DEVICE = 'cuda:0'
    print("Torch execution device: GPU", file=sys.stderr)
else:
    TORCH_DEVICE = 'cpu'
    print("Torch execution device: CPU", file=sys.stderr)

print(f"Loading BERT model '{BERT_MODEL_NAME}' from the HuggingFace transformers' hub ...", file=sys.stderr)
model = BertForQuestionAnswering.from_pretrained(BERT_MODEL_NAME)
tokenizer = BertTokenizer.from_pretrained(BERT_MODEL_NAME)
bert_config_obj = model.config
model.eval()
#model.to(TORCH_DEVICE)
model.to(EXECUTION_DEVICE)
print(f"Vocabulary size: {bert_config_obj.vocab_size}", file=sys.stderr)

with open(BERT_DATA_CONTEXT_PATH, 'r') as context_file:
    context = ''.join( context_file.readlines() ).rstrip()
print(f"\nContext taken from '{BERT_DATA_CONTEXT_PATH}':", file=sys.stderr)
print(context, file=sys.stderr)
print('-'*64, file=sys.stderr)

with open(BERT_DATA_QUESTIONS_PATH, 'r') as questions_file:
    questions = questions_file.readlines()
print(f"Questions taken from '{BERT_DATA_QUESTIONS_PATH}':\n", file=sys.stderr)

with torch.no_grad():
    for i, question in enumerate( questions ):
        question = question.rstrip()
        print(f"Question_{i+1}: {question}")

        sample_encoding         = tokenizer.encode_plus( question, context, return_token_type_ids=True, return_attention_mask=False )
        sample_input_ids        = sample_encoding["input_ids"]
        if DEBUG_LEVEL>0:
            print( len(sample_input_ids) )
            print(sample_encoding)
        if DEBUG_LEVEL>1:
            print(tokenizer.convert_ids_to_tokens(sample_input_ids))

        prediction = model.forward(
            input_ids=torch.LongTensor(sample_encoding["input_ids"]).unsqueeze(0).to(TORCH_DEVICE),
            token_type_ids=torch.LongTensor(sample_encoding["token_type_ids"]).unsqueeze(0).to(TORCH_DEVICE),
#            attention_mask=torch.LongTensor(sample_encoding["attention_mask"]).unsqueeze(0).to(TORCH_DEVICE),
        )

        answer_start, answer_stop = prediction.start_logits.argmax(), prediction.end_logits.argmax()
        answer_ids = sample_input_ids[answer_start:answer_stop + 1]
        answer_tokens = tokenizer.convert_ids_to_tokens(answer_ids, skip_special_tokens=True)
        answer = tokenizer.convert_tokens_to_string(answer_tokens)

        if DEBUG_LEVEL>1:
            print(f"Answer_{i+1}: [{answer_start}..{answer_stop}] -> {answer_tokens} -> '{answer}'\n")
        elif DEBUG_LEVEL>0:
            print(f"Answer_{i+1}: [{answer_start}..{answer_stop}] -> {answer}\n")
        else:
            print(f"Answer_{i+1}: {answer}\n")


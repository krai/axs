#!/usr/bin/env python3.9

# The main dependencies:
#
# axs byname gptj_demo_torch_py , run --execution_device=cuda:1 --dtype=float16
# axs byname gptj_demo_torch_py , run --execution_device=cpu --dtype=bfloat16

import sys
from time import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

model_name          = sys.argv[1]               # "EleutherAI/gpt-j-6B", "gpt2", "EleutherAI/gpt-neo-2.7B"
revision            = sys.argv[2] or None       # "float32" or "float16" for GPT-J, none for others
dtype               = sys.argv[3] or "float32"  #
prompt              = sys.argv[4]
generate_length     = int(sys.argv[5])
execution_device    = sys.argv[6] or ('cuda' if torch.cuda.is_available() else 'cpu')

print(f"Selected torch execution_device: {execution_device}", file=sys.stderr)

# NB: execution_device=="cpu" does not support torch.float16, only torch.float32 !

torch_dtype = {
    "float32": torch.float32,
    "float16": torch.float16,
    "bfloat16": torch.bfloat16,
}[dtype]

ts_before_model_loading = time()
model = AutoModelForCausalLM.from_pretrained(model_name, revision=revision, torch_dtype=torch_dtype, low_cpu_mem_usage=True ).to(execution_device)
model_loading_s = time() - ts_before_model_loading
print(f"Model '{model_name}', revision={revision} loaded as {dtype} in {model_loading_s:.2f} sec\n", file=sys.stderr)

ts_before_tokenization = time()
tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenized_input = tokenizer(prompt, return_tensors="pt")
tokenization_s = time() - ts_before_tokenization
print(f"Prompt '{prompt}' tokenized in {tokenization_s:.2f} sec\n", file=sys.stderr)

torch.manual_seed(124)
ts_before_generation = time()
gen_tokens      = model.generate(
    tokenized_input["input_ids"].to(execution_device),
    attention_mask=tokenized_input["attention_mask"].to(execution_device),
    do_sample=True,
    temperature=0.9,
    max_length=generate_length
)
generation_s = time() - ts_before_generation
decoded_output  = tokenizer.batch_decode(gen_tokens)[0]
print(f"Generation of {generate_length} tokens took {generation_s:.2f} sec\n", file=sys.stderr)
print(decoded_output)

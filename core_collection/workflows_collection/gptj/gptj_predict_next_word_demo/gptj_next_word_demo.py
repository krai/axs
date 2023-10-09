import sys
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from datasets import load_dataset
import numpy as np

from tqdm import tqdm


model_name = sys.argv[1]
dataset_name = sys.argv[2]

execution_device = sys.argv[3] or ('cuda' if torch.cuda.is_available() else 'cpu')

dtype    = sys.argv[4] #or "float32"
verbosity =  int(sys.argv[5])

torch_dtype = {
    "float32": torch.float32,
    "float16": torch.float16,
    "bfloat16": torch.bfloat16,
}[dtype]

def tokenize_function(examples):
    example = tokenizer(examples['text'])
    return example

print("\nNext-word prediction: ")

tokenizer = AutoTokenizer.from_pretrained(model_name)
print("Tokenizer has been done.")
model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch_dtype).to(execution_device)
print("Model has been done.")


# create dataset
dataset = load_dataset('lambada', split='validation')

dataset = dataset.map(tokenize_function, batched=True)
dataset.set_format(type='torch', columns=['input_ids'])

num_of_correct_answers = 0
total_num_passages = len(dataset['text'])
pbar = tqdm(total=total_num_passages, desc='Processing')

for passage in dataset['text']:
    inpts = tokenizer(passage, return_tensors="pt")
    input_ids   = inpts["input_ids"].to(execution_device)
    split_input_ids = torch.split(input_ids, [len(input_ids[0])-1 , 1], 1)

    attention_mask = inpts["attention_mask"].to(execution_device)
    split_attention_mask = torch.split(attention_mask, [len(attention_mask[0])-1 , 1], 1)

    new_inpts = {
        "input_ids": split_input_ids[0],
        "attention_mask": split_attention_mask[0]
    }

    answer_inpts = {
        "input_ids": split_input_ids[1],
        "attention_mask": split_attention_mask[1]
    }
    answer_word = tokenizer.decode(answer_inpts["input_ids"][0])
    if verbosity == 2:
        print("answer_word = ", answer_word)
    inpt_ids = new_inpts["input_ids"]

    for id in inpt_ids[0]:
        word = tokenizer.decode(id)
        if verbosity == 2:
            print(id, word)

    with torch.no_grad():
        logits = model(**new_inpts).logits[:, -1, :]
    if verbosity == 2:
        print("\nAll logits for next word: ")
        print(logits)
        print(logits.shape)

    pred_id = torch.argmax(logits).item()
    if verbosity == 2:
        print("\nPredicted token ID of next word ")
        print(pred_id)

    pred_word = tokenizer.decode(pred_id)
    if verbosity == 2:
        print("\nPredicted next word for passage: ")
        print(pred_word)

    if pred_word == answer_word:
        num_of_correct_answers = num_of_correct_answers + 1
    pbar.update(1)
pbar.close()

print("Done.")

print("\nResults: ")
print("Number of correct answers = ", num_of_correct_answers)
print("Total number of passages = ",  total_num_passages)

accuracy = num_of_correct_answers / total_num_passages * 100
print("Accuracy = ", accuracy)


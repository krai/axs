#!/usr/bin/env python3

import json
import os
import sys

imagenet_dir        = sys.argv[1]
num_of_images       = int(sys.argv[2])
model_name          = sys.argv[3]
output_file_path    = sys.argv[4]       # if empty, recording of the output will be skipped
file_pattern        = 'ILSVRC2012_val_000{:05d}.JPEG'

# sample execution (requires torchvision)
from PIL import Image
import torch
import torchvision
from torchvision import transforms

torchvision_version = ':v' + torchvision.__version__.split('+')[0]

model = torch.hub.load('pytorch/vision' + torchvision_version, model_name, pretrained=True)
model.eval()

preprocess = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

file_names  = []
pre_batch   = []
for i in range(num_of_images):
    file_name = file_pattern.format(i+1)
    file_path   = os.path.join( imagenet_dir, file_name )
    input_image = Image.open( file_path ).convert('RGB')
    input_tensor = preprocess(input_image)
    file_names.append( file_name )
    pre_batch.append(input_tensor)

input_batch = torch.stack(pre_batch, dim=0)
#print(input_batch.size())

# move the input and model to GPU for speed if available
if torch.cuda.is_available():
    input_batch = input_batch.to('cuda')
    model.to('cuda')

with torch.no_grad():
    output = model(input_batch)

# The output has unnormalized scores. To get probabilities, you can run a softmax on it.
#print(torch.nn.functional.softmax(output[0], dim=0))

class_numbers = torch.argmax(output, dim=1).tolist()

if output_file_path:
    output_dict = {
        "predictions": dict( zip(file_names, class_numbers) )
    }
    json_string = json.dumps( output_dict , indent=4)
    with open(output_file_path, "w") as json_fd:
        json_fd.write( json_string+"\n" )
    print(f'Predictions for {num_of_images} images written into "{output_file_path}"')
else:
    print(class_numbers)

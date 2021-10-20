#!/usr/bin/env python3

import os

imagenet_dir    = os.getenv('IMAGENET_DIR', '/datasets/dataset-imagenet-ilsvrc2012-val')
filepattern     = os.path.join( imagenet_dir, 'ILSVRC2012_val_000{:05d}.JPEG')
model_name      ='resnet50'

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

pre_batch = []
for i in range(1,21):
    input_image = Image.open(filepattern.format(i))
    input_tensor = preprocess(input_image)
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

print(torch.argmax(output, dim=1).tolist())

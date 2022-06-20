#!/usr/bin/env python3

import errno
import os
import sys
import json
import numpy as np
import PIL.Image

# Load and preprocess image:
def load_image(image_path,            # Full path to processing image
               resolution,            # Desired size of resulting image
               data_type = 'uint8'   # Data type to store
               ):
    image = PIL.Image.open(image_path)
    original_width, original_height = image.size

    out_height, out_width = resolution, resolution

    if image.mode != 'RGB':
        image = image.convert('RGB')

    image = image.resize((out_width, out_height), resample=PIL.Image.BILINEAR)

    # Conver to NumPy array
    img_data = np.array(image.getdata())
    img_data = img_data.astype(np.uint8)

    # Make batch from single image
    batch_shape = (1, out_height, out_width, 3)
    batch_data = img_data.reshape(batch_shape)

    return batch_data, original_width, original_height

def preprocess(coco_images_directory, resolution, supported_extensions, data_type, new_file_extension, file_name, tags=None, entry_name=None, __record_entry__=None):
    "Go through the selected_filenames and preprocess all the files"

    __record_entry__["tags"] = tags or [ "preprocessed", "coco_images" ]
    if not entry_name:
        entry_name = f'pillow_sq.{resolution}_cropped_resized_coco_images'
    __record_entry__.save( entry_name )
    output_directory     = __record_entry__.get_path(file_name)

    os.makedirs( output_directory )

    sorted_filenames = [filename for filename in sorted(os.listdir(coco_images_directory)) if any(filename.lower().endswith(extension) for extension in supported_extensions) ]

    for current_idx, input_filename in enumerate(sorted_filenames):

        full_input_path     = os.path.join(coco_images_directory, input_filename)

        image_data, original_width, original_height = load_image(image_path = full_input_path,
                              resolution = resolution,
                              data_type = data_type)

        output_filename = input_filename.rsplit('.', 1)[0] + '.' + new_file_extension if new_file_extension else input_filename

        full_output_path    = os.path.join(output_directory, output_filename)
        image_data.tofile(full_output_path)

        print("[{}]:  Stored {}".format(current_idx+1, full_output_path) )

    return __record_entry__

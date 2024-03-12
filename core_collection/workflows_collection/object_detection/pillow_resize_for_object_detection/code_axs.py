#!/usr/bin/env python3

import errno
import os
import sys
import json
import numpy as np
import PIL.Image


def generate_file_list(annotation_data, src_images_dir, supported_extensions, first_n=None):

    if annotation_data:
        sorted_filenames = [ ann_record['file_name'] for ann_record in annotation_data ]
    else:
        sorted_filenames = [filename for filename in sorted(os.listdir(src_images_dir)) if any(filename.lower().endswith(extension) for extension in supported_extensions) ]

    return sorted_filenames[:first_n] if first_n is not None else sorted_filenames


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


def preprocess(src_images_dir, input_file_list, resolution, supported_extensions, data_type, new_file_extension, fof_name, abs_install_dir, stored_newborn_entry):
    "Go through the input_file_list and preprocess all the files"

    output_signatures = []

    for current_idx, input_filename in enumerate(input_file_list):

        full_input_path     = os.path.join(src_images_dir, input_filename)

        image_data, original_width, original_height = load_image(image_path = full_input_path,
                              resolution = resolution,
                              data_type = data_type)

        output_filename = input_filename.rsplit('.', 1)[0] + '.' + new_file_extension if new_file_extension else input_filename

        full_output_path    = os.path.join(abs_install_dir, output_filename)
        image_data.tofile(full_output_path)

        print("[{}]:  Stored {}".format(current_idx+1, full_output_path) )

        output_signatures.append( f'{output_filename};{original_width};{original_height}' )

    fof_full_path = os.path.join(abs_install_dir, fof_name)
    with open(fof_full_path, 'w') as fof:
        for filename in output_signatures:
            fof.write(filename + '\n')

    return stored_newborn_entry.save()

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


def preprocess(dataset_name, images_directory, images_annotation, resolution, supported_extensions, data_type, new_file_extension, file_name,  fof_name, first_n=None, tags=None, entry_name=None, __record_entry__=None):
    "Go through the selected_filenames and preprocess all the files"

    output_signatures = []

    __record_entry__["tags"] = tags or [ "preprocessed", dataset_name ]
    if not entry_name:
        first_n_insert = f'first.{first_n}_' if first_n else ''
        entry_name = f'pillow_{dataset_name}_resized_for_detection_sq.{resolution}_{first_n_insert}images'
    __record_entry__.save( entry_name )
    output_directory     = __record_entry__.get_path(file_name)

    os.makedirs( output_directory )

    if images_annotation:
        sorted_filenames = [ ann_record['file_name'] for ann_record in images_annotation ]
    else:
        sorted_filenames = [filename for filename in sorted(os.listdir(images_directory)) if any(filename.lower().endswith(extension) for extension in supported_extensions) ]

    selected_filenames = sorted_filenames[:first_n] if first_n is not None else sorted_filenames

    for current_idx, input_filename in enumerate(selected_filenames):

        full_input_path     = os.path.join(images_directory, input_filename)

        image_data, original_width, original_height = load_image(image_path = full_input_path,
                              resolution = resolution,
                              data_type = data_type)

        output_filename = input_filename.rsplit('.', 1)[0] + '.' + new_file_extension if new_file_extension else input_filename

        full_output_path    = os.path.join(output_directory, output_filename)
        image_data.tofile(full_output_path)

        print("[{}]:  Stored {}".format(current_idx+1, full_output_path) )

        output_signatures.append('{};{};{}'.format(output_filename, original_width, original_height) )

    fof_full_path = os.path.join(output_directory, fof_name)
    with open(fof_full_path, 'w') as fof:
        for filename in output_signatures:
            fof.write(filename + '\n')

    return __record_entry__

#!/usr/bin/env python3

import os
import sys
import numpy as np
from PIL import Image

# Load and preprocess image:
# Mimic preprocessing steps from the official reference code.
def load_image(image_path,            # Full path to processing image
               square_size,           # Desired size of resulting image
               intermediate_size = 0, # Scale to this size then crop to target size
               crop_percentage = 0,   # Crop to this percentage then scale to target size
               data_type = 'uint8',   # Data type to store
               convert_to_bgr = False # Swap image channel RGB -> BGR
               ):

    out_height  = square_size
    out_width   = square_size

    def resize_with_aspectratio(img):
        width, height = img.size
        new_height = int(100. * out_height / crop_percentage)   # intermediate oversized image from which to crop
        new_width = int(100. * out_width / crop_percentage)     # ---------------------- ,, ---------------------
        if height > width:
            w = new_width
            h = int(new_height * height / width)
        else:
            h = new_height
            w = int(new_width * width / height)

        img = img.resize((w, h), Image.BILINEAR)
        return img

    def center_crop(img):
        width, height = img.size
        left = (width - out_width) / 2
        right = (width + out_width) / 2
        top = (height - out_height) / 2
        bottom = (height + out_height) / 2
        img = img.crop((left, top, right, bottom))
        return img

    img = np.asarray(Image.open(image_path))

    # check if grayscale and convert to RGB
    if len(img.shape) == 2:
        img = np.dstack((img,img,img))

    # drop alpha-channel if present
    if img.shape[2] > 3:
        img = img[:,:,:3]

    # Resize and crop
    img = Image.fromarray(img)  # numpy image to PIL image
    img = resize_with_aspectratio(img)
    img = center_crop(img)
    img = np.asarray(img, dtype=data_type)

    # Convert to BGR
    if convert_to_bgr:
        swap_img = np.array(img)
        tmp_img = np.array(swap_img)
        tmp_img[:, :, 0] = swap_img[:, :, 2]
        tmp_img[:, :, 2] = swap_img[:, :, 0]
        img = tmp_img

    return img


def preprocess(imagenet_directory, square_size, supported_extensions, crop_percentage, inter_size, convert_to_bgr, data_type, new_file_extension, file_name, tags=None, entry_name=None, __record_entry__=None):

    __record_entry__["tags"] = tags or [ "preprocessed", "imagenet" ]
    if not entry_name:
        entry_name = f'pillow_sq.{square_size}_cropped_resized_imagenet'
    __record_entry__.save( entry_name )
    output_directory     = __record_entry__.get_path(file_name)

    os.makedirs( output_directory )

    sorted_filenames = [filename for filename in sorted(os.listdir(imagenet_directory)) if any(filename.lower().endswith(extension) for extension in supported_extensions) ]

    for current_idx, input_filename in enumerate(sorted_filenames):

        full_input_path     = os.path.join(imagenet_directory, input_filename)

        image_data = load_image(image_path = full_input_path,
                              square_size = square_size,
                              intermediate_size = inter_size,
                              crop_percentage = crop_percentage,
                              data_type = data_type,
                              convert_to_bgr = convert_to_bgr)

        output_filename = input_filename.rsplit('.', 1)[0] + '.' + new_file_extension if new_file_extension else input_filename

        full_output_path    = os.path.join(output_directory, output_filename)
        image_data.tofile(full_output_path)

        print("[{}]:  Stored {}".format(current_idx+1, full_output_path) )

    return __record_entry__

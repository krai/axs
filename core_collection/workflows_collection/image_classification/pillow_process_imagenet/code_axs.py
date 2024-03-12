#!/usr/bin/env python3

import os
import sys
import numpy as np
from PIL import Image

"""An example Python script that is given its data, necessary Python environment and the output path by wrapping it into an Entry.

Usage examples :
                    # using all defaults triggers downloading of a 500-sample subset of ImageNet:
                axs byquery preprocessed,dataset_name=imagenet

                    # overriding the input directory to preprocess all 50k of pre-stored ImageNet:
                axs byquery preprocessed,dataset_name=imagenet,src_images_dir=/datasets/dataset-imagenet-ilsvrc2012-val,entry_name=pillow_imagenet50k_cropped_resized_to_sq.224
"""
def generate_file_list(src_images_dir, supported_extensions, first_n=None):
    original_file_list = os.listdir(src_images_dir)
    sorted_filenames = [filename for filename in sorted(original_file_list) if any(filename.lower().endswith(extension) for extension in supported_extensions) ]

    if first_n:
        sorted_filenames = sorted_filenames[:first_n] #if first_n is not None else sorted_filenames
        assert len(sorted_filenames) == first_n

    return sorted_filenames


# Load and preprocess image:
# Mimic preprocessing steps from the official reference code.
def load_image(image_path,            # Full path to processing image
               resolution,            # Desired size of resulting image
               intermediate_size = 0, # Scale to this size then crop to target size
               crop_percentage = 0,   # Crop to this percentage then scale to target size
               data_type = 'uint8',   # Data type to store
               convert_to_bgr = False # Swap image channel RGB -> BGR
               ):

    out_height  = resolution
    out_width   = resolution

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


def preprocess(src_images_dir, input_file_list, resolution, supported_extensions, crop_percentage, inter_size, convert_to_bgr, data_type, new_file_extension, abs_install_dir, stored_newborn_entry):
    "Go through the input_file_list and preprocess all the files"

    for current_idx, input_filename in enumerate(input_file_list):

        full_input_path     = os.path.join(src_images_dir, input_filename)

        image_data = load_image(image_path = full_input_path,
                              resolution = resolution,
                              intermediate_size = inter_size,
                              crop_percentage = crop_percentage,
                              data_type = data_type,
                              convert_to_bgr = convert_to_bgr)

        output_filename = input_filename.rsplit('.', 1)[0] + '.' + new_file_extension if new_file_extension else input_filename

        full_output_path    = os.path.join(abs_install_dir, output_filename)
        image_data.tofile(full_output_path)

        print("[{}]:  Stored {}".format(current_idx+1, full_output_path) )

    return stored_newborn_entry

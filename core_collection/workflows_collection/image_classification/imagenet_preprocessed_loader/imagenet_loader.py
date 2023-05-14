#!/usr/bin/env python3

import os
import numpy as np


class ImagenetLoader:

    def __init__(self, preprocessed_imagenet_dir, input_file_list, height, width, data_layout, normalize_symmetric=None, subtract_mean_bool=None, given_channel_means=None, given_channel_stds=None):
        "A trivial constructor"

        self.preprocessed_imagenet_dir  = preprocessed_imagenet_dir
        self.input_file_list            = input_file_list
        self.height                     = height
        self.width                      = width
        self.data_layout                = data_layout
        self.normalize_symmetric        = normalize_symmetric   # ternary: None = no normalization, False = asymmetric, True = symmetric
        self.subtract_mean_bool         = subtract_mean_bool  or False
        self.given_channel_means        = given_channel_means or []
        self.given_channel_stds         = given_channel_stds  or []


    def load_image_by_index_and_normalize(self, image_index):
        image_filename = (self.input_file_list[image_index]).split(".")[0] + ".rgb8"

        image_filepath = os.path.join( self.preprocessed_imagenet_dir, image_filename )

        img_rgb8 = np.fromfile(image_filepath, np.uint8)
        img_rgb8 = img_rgb8.reshape((self.height, self.width, 3))

        input_data = np.float32(img_rgb8)

        # Normalize
        if self.normalize_symmetric is not None:
            if self.normalize_symmetric:
                input_data = input_data/127.5 - 1.0
            else:
                input_data = input_data/255.0

        # Subtract mean value
        if self.subtract_mean_bool:
            if len(self.given_channel_means):
                input_data -= self.given_channel_means
            else:
                input_data -= np.mean(input_data)

        if len(self.given_channel_stds):
            input_data /= self.given_channel_stds

    #    print(np.array(img_rgb8).shape)
        nhwc_data = np.expand_dims(input_data, axis=0)

        if self.data_layout == 'NHWC':
            # print(nhwc_data.shape)
            return nhwc_data, image_filename
        else:
            nchw_data = nhwc_data.transpose(0,3,1,2)
            # print(nchw_data.shape)
            return nchw_data, image_filename


    def load_preprocessed_batch_from_indices(self, batch_global_indices):
        unconcatenated_batch_data   = []
        batch_filenames             = []
        for image_index in batch_global_indices:
            image_data, image_filename = self.load_image_by_index_and_normalize( image_index )
            unconcatenated_batch_data.append( image_data )
            batch_filenames.append( image_filename )
        batch_data = np.concatenate(unconcatenated_batch_data, axis=0)

        return batch_data, batch_filenames


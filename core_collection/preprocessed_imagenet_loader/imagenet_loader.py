#!/usr/bin/env python3

import os
import numpy as np


class ImagenetLoader:

    file_pattern                        = 'ILSVRC2012_val_000{:05d}.rgb8'

    def __init__(self, preprocessed_imagenet_dir, height, width, normalize_data_bool, subtract_mean_bool, given_channel_means, data_layout):
        "A trivial constructor"

        self.preprocessed_imagenet_dir  = preprocessed_imagenet_dir
        self.height                     = height
        self.width                      = width
        self.normalize_data_bool        = normalize_data_bool
        self.subtract_mean_bool         = subtract_mean_bool
        self.given_channel_means        = given_channel_means
        self.data_layout                = data_layout


    def load_preprocessed_and_normalize(self, image_filepath):
        img_rgb8 = np.fromfile(image_filepath, np.uint8)
        img_rgb8 = img_rgb8.reshape((self.height, self.width, 3))

        input_data = np.float32(img_rgb8)

        # Normalize
        if self.normalize_data_bool:
            input_data = input_data/127.5 - 1.0

        # Subtract mean value
        if self.subtract_mean_bool:
            if len(self.given_channel_means):
                input_data -= self.given_channel_means
            else:
                input_data -= np.mean(input_data)

    #    print(np.array(img_rgb8).shape)
        nhwc_data = np.expand_dims(input_data, axis=0)

        if self.data_layout == 'NHWC':
            # print(nhwc_data.shape)
            return nhwc_data
        else:
            nchw_data = nhwc_data.transpose(0,3,1,2)
            # print(nchw_data.shape)
            return nchw_data


    def load_a_batch(self, batch_filenames):
        unconcatenated_batch_data = []
        for image_filename in batch_filenames:
            image_filepath = os.path.join( self.preprocessed_imagenet_dir, image_filename )
            nchw_data = self.load_preprocessed_and_normalize( image_filepath )
            unconcatenated_batch_data.append( nchw_data )
        batch_data = np.concatenate(unconcatenated_batch_data, axis=0)

        return batch_data


    def generate_batch_filenames(self, batch_global_indices):
        return [ self.file_pattern.format(g+1) for g in batch_global_indices ]


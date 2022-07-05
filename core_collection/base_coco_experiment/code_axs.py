#!/usr/bin/env python3

import os
import json
import sys
from time import time

import axs_utils
import converter_results
import calc_metrics_coco_pycocotools

def postprocess(num_of_images, detections_dir_path, postprocess_file_path, annotations_dir, results_out_dir, preprocessed_files, times_file_path):

  FULL_REPORT           = True

  axs_utils.prepare_dir(results_out_dir)

  def evaluate(processed_image_ids, categories_list):

    # Convert detection results from our universal text format
    # to a format specific for a tool that will calculate metrics
    print('\nConvert results to {} ...'.format('coco'))
    results = converter_results.convert(detections_dir_path, 
                                        results_out_dir)

    # Run evaluation tool
    print('\nEvaluate metrics as {} ...'.format('coco'))
    mAP, recall, all_metrics = calc_metrics_coco_pycocotools.evaluate(processed_image_ids, results, annotations_dir)

    OPENME['mAP'] = mAP
    OPENME['recall'] = recall
    OPENME['metrics'] = all_metrics

    return

  OPENME = {}

  with open(preprocessed_files, 'r') as f:
    processed_image_filenames = [x.split(';')[0] for x in f.readlines()]

  processed_image_ids = [ axs_utils.filename_to_id(image_filename) for image_filename in processed_image_filenames ]

  if os.path.isfile(times_file_path):
    with open(times_file_path, 'r') as f:
      OPENME = json.load(f)

  # Run evaluation
  axs_utils.print_header('Process results')
  
  categories_list = []

  evaluate(processed_image_ids, categories_list)

  OPENME['frame_predictions'] = converter_results.convert_to_frame_predictions(detections_dir_path)
  OPENME['execution_time'] = OPENME['times'].get('sum_inference_s',0) + OPENME['times'].get('model_loading_s',0) + OPENME['times'].get('sum_loading_s',0)

  # Store benchmark results
  with open(postprocess_file_path, 'w') as o:
    json.dump(OPENME, o, indent=2, sort_keys=True)

  # Print metrics
  print('\nSummary:')
  print('-------------------------------')
  print('All images loaded in {:.6f}s'.format(OPENME['times'].get('sum_loading_s', 0)))
  print('Average image load time: {:.6f}s'.format(OPENME['times'].get('sum_loading_s', 0)/int(num_of_images)))
  print('All images detected in {:.6f}s'.format(OPENME['times'].get('sum_inference_s', 0)))
  print('Average detection time: {:.6f}s'.format(OPENME['times'].get('per_inference_s', 0)))
  print('Total NMS time: {:.6f}s'.format(OPENME['times'].get('non_max_suppression_time_total_s', 0)))
  print('Average NMS time: {:.6f}s'.format(OPENME['times'].get('non_max_suppression_time_avg_s', 0)))
  print('mAP: {}'.format(OPENME['mAP']))
  print('Recall: {}'.format(OPENME['recall']))
  print('--------------------------------\n')


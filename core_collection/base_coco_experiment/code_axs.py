#!/usr/bin/env python3

import os
import json
import sys
from time import time

import calc_metrics_coco_pycocotools

def filename_to_id(file_name):
  '''
  Returns identitifer of image in dataset.

  Each dataset has its own way how to identify
  particular image in detection results or annotations.
  '''
  short_name = os.path.splitext(file_name)[0]

  # In COCO dataset ID is a number which is a part of filename
    # COCO 2017: 000000000139.jpg
    # COCO 2014: COCO_val2014_000000000042.jpg
  if short_name[0] == '0':
    return int(short_name)
  else:
    return int(re.split(r'_', short_name)[2])


def generate_coco_detection_list( detection_results ):
    result_full_list = []
    image_ids = detection_results.keys()

    for image_id in image_ids:
        for detection in detection_results[image_id]["detections"]:
            x1, y1, x2, y2 = detection["bbox"]
            h = y2 - y1
            w = x2 - x1
            one_detection = {
                "image_id":     int( image_id ),
                "category_id":  detection["class_id"],
                "bbox":         [ x1, y1, round(w, 2), round(h, 2) ],
                "score":        detection["score"]
            }
            result_full_list.append(one_detection)

    return result_full_list

def save_to_json(structure, json_file_name):
    with open(json_file_name, 'w') as f:
        f.write(json.dumps( structure, indent=2, sort_keys=False))
    return json_file_name

def postprocess(num_of_images, postprocess_file_path, annotations_dir, results_out_dir, preprocessed_files, times_file_path, detection_results ):

  def evaluate(processed_image_ids, categories_list):

    # Convert detection results from our universal text format
    # to a format specific for a tool that will calculate metrics
    results = generate_coco_detection_list( detection_results )

    # Run evaluation tool
    all_metrics = calc_metrics_coco_pycocotools.evaluate(processed_image_ids, results, annotations_dir)
    mAP = all_metrics['DetectionBoxes_Precision/mAP']
    recall = all_metrics['DetectionBoxes_Recall/AR@100']

    postpocess_result['mAP'] = mAP
    postpocess_result['recall'] = recall
    postpocess_result['metrics'] = all_metrics
    return

  postpocess_result = {}

  with open(preprocessed_files, 'r') as f:
    processed_image_filenames = [x.split(';')[0] for x in f.readlines()]

  processed_image_ids = [ filename_to_id(image_filename) for image_filename in processed_image_filenames ]

  if os.path.isfile(times_file_path):
    with open(times_file_path, 'r') as f:
      postpocess_result = json.load(f)

  # Run evaluation
  
  categories_list = []

  evaluate(processed_image_ids, categories_list)

  postpocess_result['frame_predictions'] = generate_coco_detection_list( detection_results )
  postpocess_result['execution_time'] = postpocess_result['times'].get('sum_inference_s',0) + postpocess_result['times'].get('model_loading_s',0) + postpocess_result['times'].get('sum_loading_s',0)

  # Store benchmark results
  save_to_json(postpocess_result, postprocess_file_path)

  return postpocess_result

def mAP(num_of_images, postprocess_file_path, annotations_dir, results_out_dir, preprocessed_files, times_file_path, detection_results):
    r = postprocess(num_of_images, postprocess_file_path, annotations_dir, results_out_dir, preprocessed_files, times_file_path, detection_results )
    return r['mAP']

def recall(num_of_images, postprocess_file_path, annotations_dir, results_out_dir, preprocessed_files, times_file_path, detection_results):
    r = postprocess(num_of_images, postprocess_file_path, annotations_dir, results_out_dir, preprocessed_files, times_file_path, detection_results )
    return r['recall']

def execution_time(num_of_images, postprocess_file_path, annotations_dir, results_out_dir, preprocessed_files, times_file_path, detection_results):
     r = postprocess(num_of_images, postprocess_file_path, annotations_dir, results_out_dir, preprocessed_files, times_file_path, detection_results )
     return r['execution_time']

def print_times(detection_times):
    print ('\nmodel_loading_s        = ', detection_times['model_loading_s'])
    print ('sum_loading_s          = ', detection_times['sum_loading_s'])
    print ('sum_inference_s        = ', detection_times['sum_inference_s'])
    print ('per_inference_s        = ', detection_times['per_inference_s'])
    print ('fps                    = ', detection_times['fps'])
    print ('\nlist_batch_loading_s   = ', detection_times['list_batch_loading_s'])
    print ('\nlist_batch_inference_s = ', detection_times['list_batch_inference_s'])

def print_metrics(num_of_images, postprocess_file_path, annotations_dir, results_out_dir, preprocessed_files, times_file_path, detection_results):
    r = postprocess(num_of_images, postprocess_file_path, annotations_dir, results_out_dir, preprocessed_files, times_file_path, detection_results )
    # Print metrics
    print('\nSummary:')
    print('-------------------------------')
    print('All images loaded in {:.6f}s'.format(r['times'].get('sum_loading_s', 0)))
    print('Average image load time: {:.6f}s'.format(r['times'].get('sum_loading_s', 0)/int(num_of_images)))
    print('All images detected in {:.6f}s'.format(r['times'].get('sum_inference_s', 0)))
    print('Average detection time: {:.6f}s'.format(r['times'].get('per_inference_s', 0)))
    print('Total NMS time: {:.6f}s'.format(r['times'].get('non_max_suppression_time_total_s', 0)))
    print('Average NMS time: {:.6f}s'.format(r['times'].get('non_max_suppression_time_avg_s', 0)))
    print('mAP: {}'.format(r['mAP']))
    print('Recall: {}'.format(r['recall']))
    print('--------------------------------\n')

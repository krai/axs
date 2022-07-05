#!/usr/bin/env python3

import os
import json

import axs_utils as helper

def convert(detections_dir, target_dir ):
  '''
  Convert detection results from our universal text format
  to a format specific for a tool that will calculate metrics.

  Returns whether results directory or path to the new results file,
  depending on target results format.
  '''

  detection_files = helper.get_files(detections_dir)

  return convert_to_coco(detection_files, detections_dir, target_dir)

def convert_to_coco(detection_files, detections_dir, target_dir):
  res_array = []
  for file_name in detection_files:
    read_file = os.path.join(detections_dir, file_name)
    file_id = helper.filename_to_id(file_name)
    with open(read_file, 'r') as rf:
      rf.readline() # first line is image size
      for line in rf:
        det = helper.Detection(line)
        res = detection_to_coco_object(det, file_id)
        if (res):
          res_array.append(res)
  results_file = os.path.join(target_dir, 'coco_results.json')
  with open(results_file, 'w') as f:
    f.write(json.dumps(res_array, indent=2, sort_keys=False))
  return results_file

def detection_to_coco_object(det, file_id):
  '''
  Returns result object in COCO format
  '''
  category_id = int(det.class_id)

  if not category_id: return None
    
  x = det.x1
  y = det.y1
  w = round(det.x2 - x, 2)
  h = round(det.y2 - y, 2)
  return {
    "image_id" : file_id,
    "category_id" : category_id,
    "bbox" : [x, y, w, h],
    "score" : det.score,
  }


def convert_to_frame_predictions(detections_dir):
  result = {}
  detection_files = helper.get_files(detections_dir)

  for file_name in detection_files:
    read_file = os.path.join(detections_dir, file_name)

    with open(read_file, 'r') as rf:
      file_info = {}
      width, height = [int(i) for i in rf.readline().split()] # first line is image size
      file_info["image_height"] = height
      file_info["image_width"] = width
      file_info["detections"] = []

      for line in rf:
        det = helper.Detection(line)
        detection = {}
        detection["bbox"] = [det.x1, det.y1, det.x2, det.y2]
        detection["prob"] = det.score
        detection["class"] = str(det.class_id) + " " + det.class_name
        file_info["detections"].append(detection)
      
      result[file_name] = file_info
  
  return result

#!/usr/bin/env python3

import os
import json
import sys
from time import time
from contextlib import redirect_stdout

from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval


def generate_coco_detection_list( detection_results, fileroot_2_id ):
    result_full_list = []
    image_ids = detection_results.keys()

    for image_id in image_ids:
        for detection in detection_results[image_id]["detections"]:
            x1, y1, x2, y2 = detection["bbox"]
            h = y2 - y1
            w = x2 - x1
            one_detection = {
                "image_id":     fileroot_2_id[image_id],
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


def postprocess(num_of_images, annotation_file, preprocessed_files, times_file_path, detection_results ):

    with open(preprocessed_files, 'r') as f:
        processed_image_fileroots = [ os.path.splitext(x.split(';')[0])[0] for x in f.readlines() ]

    # Calculate COCO metrics via evaluator from pycocotool package.
    # MSCOCO evaluation protocol: http://cocodataset.org/#detections-eval
    # This method uses original COCO json-file annotations
    # and results of detection converted into json file too.
    cocoGt = COCO(annotation_file)

    image_map = cocoGt.dataset["images"]
    fileroot_2_id = { os.path.splitext(x["file_name"])[0]: x["id"] for x in image_map }
    processed_image_ids = [ fileroot_2_id[x] for x in processed_image_fileroots ]

    # Convert detection results from our universal text format
    # to a format specific for a tool that will calculate metrics
    frame_predictions = generate_coco_detection_list( detection_results, fileroot_2_id )

    cocoDt = cocoGt.loadRes(frame_predictions)
    cocoEval = COCOeval(cocoGt, cocoDt, iouType='bbox')
    cocoEval.params.imgIds = processed_image_ids
    cocoEval.evaluate()
    cocoEval.accumulate()
    cocoEval.summarize()

    # These are the same names as object returned by CocoDetectionEvaluator has
    all_metrics = {
        "DetectionBoxes_Precision/mAP": cocoEval.stats[0],
        "DetectionBoxes_Precision/mAP@.50IOU": cocoEval.stats[1],
        "DetectionBoxes_Precision/mAP@.75IOU": cocoEval.stats[2],
        "DetectionBoxes_Precision/mAP (small)": cocoEval.stats[3],
        "DetectionBoxes_Precision/mAP (medium)": cocoEval.stats[4],
        "DetectionBoxes_Precision/mAP (large)": cocoEval.stats[5],
        "DetectionBoxes_Recall/AR@1": cocoEval.stats[6],
        "DetectionBoxes_Recall/AR@10": cocoEval.stats[7],
        "DetectionBoxes_Recall/AR@100": cocoEval.stats[8],
        "DetectionBoxes_Recall/AR@100 (small)": cocoEval.stats[9],
        "DetectionBoxes_Recall/AR@100 (medium)": cocoEval.stats[10],
        "DetectionBoxes_Recall/AR@100 (large)": cocoEval.stats[11]
    }

    if os.path.isfile(times_file_path):
        with open(times_file_path, 'r') as f:
            postpocess_result = json.load(f)
    else:
        postpocess_result = {}

    postpocess_result['mAP'] = all_metrics['DetectionBoxes_Precision/mAP']
    postpocess_result['recall'] = all_metrics['DetectionBoxes_Recall/AR@100']
    postpocess_result['metrics'] = all_metrics

    postpocess_result['frame_predictions'] = frame_predictions
    postpocess_result['execution_time'] = postpocess_result['times'].get('sum_inference_s',0) + postpocess_result['times'].get('model_loading_s',0) + postpocess_result['times'].get('sum_loading_s',0)

    return postpocess_result


def mAP(num_of_images, annotation_file, preprocessed_files, times_file_path, detection_results):
    with redirect_stdout(sys.stderr):
        r = postprocess(num_of_images, annotation_file, preprocessed_files, times_file_path, detection_results )
    return float(r['mAP'])

def recall(num_of_images, annotation_file, preprocessed_files, times_file_path, detection_results):
    with redirect_stdout(sys.stderr):
        r = postprocess(num_of_images, annotation_file, preprocessed_files, times_file_path, detection_results )
    return float(['recall'])

def execution_time(num_of_images, annotation_file, preprocessed_files, times_file_path, detection_results):
    with redirect_stdout(sys.stderr):
        r = postprocess(num_of_images, annotation_file, preprocessed_files, times_file_path, detection_results )
    return r['execution_time']

def print_times(detection_times):
    print ('\nmodel_loading_s        = ', detection_times['model_loading_s'])
    print ('sum_loading_s          = ', detection_times['sum_loading_s'])
    print ('sum_inference_s        = ', detection_times['sum_inference_s'])
    print ('per_inference_s        = ', detection_times['per_inference_s'])
    print ('fps                    = ', detection_times['fps'])
    print ('\nlist_batch_loading_s   = ', detection_times['list_batch_loading_s'])
    print ('\nlist_batch_inference_s = ', detection_times['list_batch_inference_s'])

def print_metrics(num_of_images, annotation_file, preprocessed_files, times_file_path, detection_results):
    r = postprocess(num_of_images, annotation_file, preprocessed_files, times_file_path, detection_results )
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

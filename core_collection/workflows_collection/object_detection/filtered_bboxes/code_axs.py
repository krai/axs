#!/usr/bin/env python3

import os
import operator
import numpy as np

from PIL import ImageFont,Image, ImageDraw

def add_bboxes_to_image(input_file_path, output_file_path, bboxes, n):
    im = Image.open(input_file_path)
    draw_detected_image = ImageDraw.Draw(im)
    font = ImageFont.load_default()
    for j in range(0, n):
        bbox = bboxes[j]
        (x1, y1, x2, y2) = bbox["bbox"]
        
        class_id =  bbox["class_id"]
        class_name = bbox["class_name"]
        score = bbox["score"]
        text = f" { class_id } / { class_name} / { score }"
        draw_detected_image.text((x1,y1),text, fill ="blue", font=font, align ="right")
        draw_detected_image.rectangle(((x1, y1), (x2, y2)), outline="blue", width=1)

    im.save(output_file_path)

def clamp(n, minn, maxn):
    return max(min(maxn, n), minn)

def postprocess_add_detections(input_images_directory, data_detections, file_name, num_of_bboxes, __record_entry__=None):

    filtered_data_detections = filter(data_detections)
    __record_entry__.plant("filtered_data_detections", filtered_data_detections)
    __record_entry__.save()

    output_directory     = __record_entry__.get_path(file_name)

    os.makedirs( output_directory )

    data_detections = filtered_data_detections

    list_images = data_detections.keys()
    for i in list_images:
        bboxes = data_detections[i]["detections"]
        input_file_path = os.path.join(input_images_directory, i + ".jpg")
        output_file_path = os.path.join(output_directory , i + "_bboxed" + ".jpg")
        if num_of_bboxes:
            n = clamp(int(num_of_bboxes), 0, len(bboxes))
        else:
            n = len(bboxes)
        add_bboxes_to_image(input_file_path, output_file_path, bboxes, n)

    return __record_entry__

def filter(initial_data_detections, target_class = "Man"):
    list_images = initial_data_detections.keys()

    results = {}
    for i in list_images:
        detections = initial_data_detections[i]["detections"]

        most_probable_detection = None
        max_area = 0
        filtered_detections = []
        for detection in detections:
            (x1, y1, x2, y2) = detection["bbox"]
            area = abs(x1-x2)*abs(y1-y2)
            if area > max_area:
                most_probable_detection = detection
            if detection["class_name"] == target_class:
                detection["area"] = area # Also save area info
                filtered_detections.append(detection)

        print(filtered_detections)
        if filtered_detections:
            filtered_detections = sorted(filtered_detections, key=operator.itemgetter('score')) # sort by score quite good
            # filtered_detections = sorted(filtered_detections, key=operator.itemgetter("area")) # sort by area not as good as score but doable
            most_probable_detection = filtered_detections[-1]

            # joint all boxes, not good at all
            # boxes = np.array([elem['bbox'] for elem in filtered_detections])
            # x1, _, y1, _ = np.amax(boxes, axis=0)
            # _, x2, _, y2 = np.amin(boxes, axis=0)
            # print(x1,x2,y1,y2)
            # joint_detection = {
            #             "bbox":         [ round(float(x1),2), round(float(y1),2), round(float(x2),2), round(float(y2),2) ],
            #             "score":        100,
            #             "class_id":     filtered_detections[0]["class_id"],
            #             "class_name":   filtered_detections[0]["class_name"],
            # }
            # most_probable_detection = joint_detection
        
        filtered_detections = [most_probable_detection]
        results[i] = {
                    "image_height": initial_data_detections[i]["image_height"],
                    "image_width":  initial_data_detections[i]["image_width"],
                    "detections":   filtered_detections,
                }

    return results



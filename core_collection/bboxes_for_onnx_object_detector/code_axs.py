#!/usr/bin/env python3

import os

from PIL import ImageFont,Image, ImageDraw

def add_bboxes_to_image(input_file_path, output_file_path, bboxes, n):
    im = Image.open(input_file_path)
    draw_detected_image = ImageDraw.Draw(im)
    font = ImageFont.load_default()       
    for j in range(0,n):
        bbox = bboxes[j]
        (x1, y1, x2, y2) = bbox["bbox"]
        
        class_id =  bbox["class_id"]
        class_name = bbox["class_name"]
        score = bbox["score"]
        text = f" { class_id } / { class_name} / { score }"
        draw_detected_image.text((x1,y1),text, fill ="blue", font=font, align ="right")
        draw_detected_image.rectangle(((x1, y1), (x2, y2)), outline="blue", width=1)

    im.save(output_file_path)

def postprocess_add_detections(input_images_directory, data_detections, file_name, n, __record_entry__=None):

    __record_entry__.save()

    output_directory     = __record_entry__.get_path(file_name)

    os.makedirs( output_directory )
    list_images = data_detections.keys()
    for i in list_images:
        bboxes = data_detections[i]["detections"]
        input_file_path = os.path.join(input_images_directory, i + ".jpg")
        output_file_path = os.path.join(output_directory , i + "_bboxed" + ".jpg")
        add_bboxes_to_image(input_file_path, output_file_path, bboxes, n)

    return __record_entry__

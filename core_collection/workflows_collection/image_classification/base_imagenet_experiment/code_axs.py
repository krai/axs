#!/usr/bin/env python3

"""This entry knows where to download the ImageNet metadata (ground truth, class labels, etc) from, how to unpack it and how to interpret it.

Usage examples :
                axs byname base_imagenet_experiment , get ground_truth_path
                axs byname base_imagenet_experiment , get class_names_path
                axs byname base_imagenet_experiment , dig class_mapping.1000
                axs byname base_imagenet_experiment , dig '---=["class_names",["^^","dig",[["ground_truth","ILSVRC2012_val_00050000.JPEG"]]]]'
"""

def load_ground_truth(ground_truth_path):

    ground_truth = {}
    with open( ground_truth_path ) as ground_truth_fd:
        for line in ground_truth_fd:
            file_name, class_number = line.rstrip().split(' ')
            image_name = file_name.rsplit('.', 1)[0]
            ground_truth[image_name] = int(class_number)

    return ground_truth


def load_class_names(class_names_path):

    class_names = []
    with open( class_names_path ) as class_names_fd:
        for line in class_names_fd:
            label, class_name = line.rstrip().split(' ', 1)
            class_names.append( class_name )

    return class_names


def show_table(ground_truth, class_names, n_from=1, n_to=20):
    """Print a human-readable ordered slice of ground_truth table.
        NB: image indices are 1-based (1-50000), class labels are 0-based (0-999).
        Returns the number of lines printed.

Usage examples :
                axs byname base_imagenet_experiment , show_table
                axs byname base_imagenet_experiment , show_table --n_from=21 --n_to=40
    """
    for i, image_name in enumerate(sorted( ground_truth.keys() )):
        n = i+1
        if n_from <= n <= n_to:
            print(f"{n:>5}    {image_name}    {ground_truth[image_name]:>3}    {class_names[ground_truth[image_name]]}")

    return n_to - n_from + 1


def measure_accuracy(predictions, ground_truth):
    """Compare how many times a value in predictions maps to the same value in ground_truth.
    """
    correct_count = 0.0
    total_count   = 0.0
    for image_name in predictions:
        if predictions[image_name]==ground_truth[image_name]:
            correct_count += 1.0
        total_count += 1.0

    return correct_count/total_count if total_count else None


def full_print_predictions(top_n, class_names, ground_truth, top_number=1):
    count = 0
    for image_name in top_n.keys():
        list_keys = list(top_n[image_name].keys())
        print(f"\t{image_name + ':'}\t{ground_truth[image_name]}\t{class_names[ground_truth[image_name]]}")
        for i in range(0,min(top_number, len(list_keys))):
            print(f"\t{top_n[image_name][list_keys[i]]}\t{list_keys[i]}\t{class_names[int(list_keys[i])]} ")
            count = count + 1
        print("")
    return count

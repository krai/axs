#!/usr/bin/env python3

import os


def create_collection(collection_name, output_entry):
    output_directory = output_entry.get_path("")
    os.makedirs( output_directory )

    return output_entry.save()

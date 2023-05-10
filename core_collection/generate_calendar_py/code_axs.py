#!/usr/bin/env python3

"""Example of a Python-based workflow that (internally) performs all parameter exchange with the script via JSON files.
    This is the recommended method of parameter exchange that simplifies internal interfaces, storage and later access to this data.

    During execution the script is passed two names on the command line:
        <python3> generate_calendar.py <input_json_file_path> <output_json_file_path>

    Internally, the script has to know how to read its input data from <input_json_file_path>
    and how to produce a valid JSON file given output_json_file_path .

Usage examples:
        # find the program, explicitly run it with specific arguments, reach for the output:
                axs byname generate_calendar_py , run --year=2023 --month=1 , dig program_output.calendar

        # use the tag/attribute-based query to benefit from caching (will not re-run fully if called with the same query twice):
                axs byquery program_output,calendar,year=2023,month=4 , dig program_output.calendar
"""

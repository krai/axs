#!/usr/bin/env python3

import sys
import calendar
import json

input_json_filepath     = sys.argv[1]
output_json_filepath    = sys.argv[2]

with open(input_json_filepath, 'r') as openfile:
    input_dict = json.load(openfile)

cal = calendar.TextCalendar(input_dict["first_weekday"])
output_month = cal.formatmonth(input_dict["year"], input_dict["month"])

if output_json_filepath:
    output_dict = {
        "calendar": output_month,
    }
    with open(output_json_filepath, "w") as outfile:
        json.dump(output_dict, outfile, indent=4)
else:
    print(output_month)

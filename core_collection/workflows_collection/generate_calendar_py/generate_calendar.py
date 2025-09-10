#!/usr/bin/env python3

import calendar
import json
import os
import sys

script_name             = os.path.basename( sys.argv[0] )
input_json_filepath     = sys.argv[1]
output_json_filepath    = sys.argv[2]

print(f"[{script_name}] Running under {sys.executable} ...", file=sys.stderr)

with open(input_json_filepath, 'r') as openfile:
    input_dict = json.load(openfile)

first_weekday   = input_dict["first_weekday"]
year            = input_dict["year"]
month           = input_dict["month"]

print(f"[{script_name}] Generating calendar for year={year}, month={month}, first_weekday={first_weekday}, outputting to {output_json_filepath or 'STDOUT'}\n", file=sys.stderr)

cal = calendar.TextCalendar(first_weekday)
output_month = cal.formatmonth(year, month)

if output_json_filepath:
    output_dict = {
        "calendar": output_month,
    }
    with open(output_json_filepath, "w") as outfile:
        json.dump(output_dict, outfile, indent=4)
else:
    print(output_month)

#!/usr/bin/env python3

from function_access import to_num_or_not_to_num

def parse_summary(abs_log_summary_path):

    parsed_summary = {}
    with open( abs_log_summary_path ) as log_summary_fd:
        for line in log_summary_fd:
            if ':' in line:     # for now, ignore all other lines
                k, v = (x.strip() for x in line.split(':', 1))
                k = k.replace(' ', '_').replace(')', '').replace('(', '')

                parsed_summary[k] = to_num_or_not_to_num(v)
    return parsed_summary

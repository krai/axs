#!/usr/bin/env python3

import ufun as uf

def generate_accuracy_log(output_logits, accuracy_log_path):
    import numpy as np

    encoded_accuracy_log = []
    for k in output_logits.keys():
        encoded_accuracy_log.append({'qsl_idx': int(k), 'data': np.array(output_logits[k], np.float32).tobytes().hex()})

    uf.save_json(encoded_accuracy_log, accuracy_log_path)
    return accuracy_log_path

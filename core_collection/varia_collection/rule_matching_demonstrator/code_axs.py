#!/usr/bin/env python3

""" This code is to demonstrate how the components of the query end up being passed into the producing function.
"""

def entry_producer(alpha, beta, gamma, delta=400, epsilon=500, zeta=600, tags=None, __record_entry__=None):

    print(f"Running entry_producer with alpha={alpha}, beta={beta}, gamma={gamma}, delta={delta}, epsilon={epsilon}, zeta={zeta}, __record_entry__={__record_entry__}")

    return __record_entry__.save()

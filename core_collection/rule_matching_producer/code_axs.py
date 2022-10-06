#!/usr/bin/env python3

def producer_function(m, n, c='c:C', rap='rap:C', ra='ra:C', rp='rp:C', r='r:C', ap='ap:C', a='a:C', p='p:C', i='i:C', tags=None, __record_entry__=None):
    """ This fuction demonstrates how the components of the query end up being passed into the producing function.
    """

    print("Running entry_producer with m={m}, n={n}, c={c}, rap={rap}, ra={ra}, rp={rp}, r={r}, ap={ap}, a={a}, p={p}, i={i}")

    entry_name = f"produced_entry_m.{m}_n.{n}_c.{c}_rap.{rap}_ra.{ra}_rp.{rp}_r.{r}_ap.{ap}_a.{a}_p.{p}_i.{i}"
    return __record_entry__.save( entry_name )

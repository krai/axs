#!/bin/bash

source assert.sh

assert 'axs version' '0.2.40'
assert 'axs get xyz --xyz=123' 123
assert 'axs dig greek.2 --greek,=alpha,beta,gamma,delta' 'gamma'
assert 'axs substitute "Hello, #{x}#" --x=mate' 'Hello, mate'
assert_end on_the_fly_data_access

echo "axs tests done"


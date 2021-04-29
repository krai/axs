#!/bin/bash

source assert.sh

assert 'axs get xyz --xyz=123' 123
assert 'axs dig greek.2 --greek,=alpha,beta,gamma,delta' 'gamma'
assert 'axs substitute "Hello, #{x}#" --x=mate' 'Hello, mate'
assert_end on_the_fly_data_access

axs bypath foo , save --greeting=Hello --address=mate --n=42
assert 'axs bypath foo , get n' 42
assert 'axs bypath foo , substitute "#{greeting}#, #{address}#!"' 'Hello, mate!'
rm -rf foo
assert_end entry_creation_and_data_access

axs bypath grandma  , save --alpha=10 --beta=20  --gamma=30
axs bypath mum      , save            --beta=200 --gamma=300 --parent_entries^,=^bypath:grandma
assert 'axs bypath mum , substitute "#{alpha}# and #{beta}#"' '10 and 200'
axs bypath granddad , save --gamma=31 --delta=41  --epsilon=51  --zeta=60
axs bypath dad      , save            --delta=410 --epsilon=510 --parent_entries^,=^bypath:granddad
axs bypath child    , save --lambda=7000 --mu=8000 --parent_entries^,=^bypath:dad,^bypath:mum
assert 'axs bypath child , substitute "#{alpha}#+#{beta}#, #{gamma}#-#{delta}#, #{epsilon}#*#{lambda}#"' '10+200, 31-410, 510*7000'
axs bypath child    , remove
axs bypath mum      , remove
axs bypath grandma  , remove
axs bypath dad      , remove
axs bypath granddad , remove
assert_end entry_creation_multiple_inheritance_and_removal

axs byname git , pull counting_collection , attach
assert 'axs byname French , dig number_mapping.5' 'cinq'
axs byname counting_collection , pull
axs byname counting_collection , remove
assert_end git_cloning_collection_access_and_removal

echo "axs tests done"


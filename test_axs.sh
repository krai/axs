#!/bin/bash

source assert.sh

if [ `uname` = 'Darwin' ]; then
    MD5CMD="md5 -r"
else
    MD5CMD="md5sum"
fi

assert 'axs get xyz --xyz=123' 123
assert 'axs dig greek.2 --greek,=alpha,beta,gamma,delta' 'gamma'
assert 'axs substitute "Hello, #{x}#" --x=mate' 'Hello, mate'
assert_end on_the_fly_data_access

axs bypath foo , save --greeting=Hello --address=mate --n=42
assert 'axs bypath foo , get n' 42
assert 'axs bypath foo , substitute "#{greeting}#, #{address}#!"' 'Hello, mate!'
rm -rf foo
assert_end entry_creation_and_data_access

axs bypath grandma  , save --alpha=10 --beta=20  --gamma=30  --multisub^^substitute="#{alpha}#, #{beta}# and #{gamma}#"
axs bypath mum      , save            --beta=200 --gamma=300 --_parent_entries,:=^:bypath:grandma
assert 'axs bypath mum , substitute "#{alpha}# and #{beta}#"' '10 and 200'
assert 'axs bypath mum , get multisub --beta=2000' '10, 2000 and 300'
axs bypath granddad , save --gamma=31 --delta=41  --epsilon=51  --zeta=60 --multisub2,:="^^substitute:#{gamma}#-#{delta}#,^^substitute:#{epsilon}#-#{zeta}#"
axs bypath dad      , save            --delta=410 --epsilon=510 --_parent_entries,:=^:bypath:granddad
axs bypath child    , save --lambda=7000 --mu=8000 --_parent_entries,:=^:bypath:dad,^:bypath:mum
assert 'axs bypath child , substitute "#{alpha}#+#{beta}#, #{gamma}#-#{delta}#, #{epsilon}#*#{lambda}#"' '10+200, 31-410, 510*7000'
assert 'axs bypath dad , get multisub2 --delta=411 --zeta=611' "['31-411', '510-611']"
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

axs bypath examplepage_recipe , --url=http://example.com/ --entry_name=examplepage_downloaded --file_name=example.html --_parent_entries,:=^:byname:downloader save , attach
axs byname examplepage_recipe , download
assert '$MD5CMD `axs byname examplepage_downloaded , get_path` | cut -f 1 -d" "' '84238dfc8092e5d9c0dac8ef93371a07'
axs byname examplepage_downloaded , remove
axs byname examplepage_recipe , remove
assert_end url_downloading_recipe_activation_and_removal

echo "axs tests done"


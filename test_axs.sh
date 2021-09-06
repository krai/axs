#!/bin/bash

source assert.sh

if [ `uname` = 'Darwin' ]; then
    MD5CMD="md5 -r"
else
    MD5CMD="md5sum"
fi

assert 'echo "Hello, world!"' 'Hello, world!'
assert_end testing_assert_itself

assert 'axs get xyz --xyz=123' 123
assert 'axs dig greek.2 --greek,=alpha,beta,gamma,delta' 'gamma'
assert 'axs substitute "Hello, #{x}#" --x=mate' 'Hello, mate'
assert_end on_the_fly_data_access

axs empty , plant greeting Hello , plant address mate , plant n 42 , save foo
assert 'axs bypath foo , get n' 42
assert 'axs bypath foo , substitute "#{greeting}#, #{address}#!"' 'Hello, mate!'
rm -rf foo
assert_end entry_creation_and_data_access

assert "axs mi: bypath missing , plant alpha 10 , plant beta 20 , plant formula --:='^^:substitute:#{alpha}#-#{beta}#' , own_data" "{'alpha': 10, 'beta': 20, 'formula': '10-20'}"
assert "axs mi: bypath missing , plant alpha 10 , plant beta 20 , plant formula --:='AS^IS:^^:substitute:#{alpha}#-#{beta}#' , own_data" "{'alpha': 10, 'beta': 20, 'formula': ['^^', 'substitute', '#{alpha}#-#{beta}#']}"
assert "axs mi: bypath missing , plant alpha 10 , plant beta 20 , plant formula --:='AS^IS:^^:substitute:#{alpha}#-#{beta}#' , get formula --alpha=30" "30-20"
assert "axs mi: bypath missing , plant alpha 10 , plant beta 20 , plant formula --:='AS^IS:^^:substitute:#{alpha}#-#{beta}#' , get formula --alpha=30 , get mi , own_data" "{'alpha': 10, 'beta': 20, 'formula': ['^^', 'substitute', '#{alpha}#-#{beta}#']}"
assert_end escaping_nested_calls_immediate_execution

axs empty , plant alpha 10 , plant beta 20 , plant gamma 30 , plant multisub --:="AS^IS:^^:substitute:#{alpha}#, #{beta}# and #{gamma}#" , save grandma
axs empty , plant beta 200 , plant gamma 300 , plant _parent_entries --,:=AS^IS:^:bypath:grandma , save mum
assert 'axs bypath mum , substitute "#{alpha}# and #{beta}#"' '10 and 200'
assert 'axs bypath mum , get multisub --beta=2000' '10, 2000 and 300'
axs empty , plant gamma 31 , plant delta 41 , plant epsilon 51 , plant zeta 60 , plant multisub2 --,:="AS^IS:^^:substitute:#{gamma}#-#{delta}#,AS^IS:^^:substitute:#{epsilon}#-#{zeta}#" , save granddad
axs empty , plant delta 410 , plant epsilon 510 , plant _parent_entries --,:=AS^IS:^:bypath:granddad , save dad
axs empty , plant lambda 7000 , plant mu 8000 , plant _parent_entries --,:=AS^IS:^:bypath:dad,AS^IS:^:bypath:mum , save child
assert 'axs bypath child , substitute "#{alpha}#+#{beta}#, #{gamma}#-#{delta}#, #{epsilon}#*#{lambda}#"' '10+200, 31-410, 510*7000'
assert 'axs bypath dad , get multisub2 --delta=411 --zeta=611' "['31-411', '510-611']"
assert 'axs d: bypath dad , dig d.multisub2.1 --epsilon=3333' "3333-60"
assert 'axs d: bypath dad , dig d.multisub2.1 --epsilon=3333 , get d , clear_cache , dig d.multisub2.1 --epsilon=4444' "4444-60"
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

axs empty , plant url http://example.com/ , plant entry_name examplepage_downloaded , plant file_name example.html , plant _parent_entries --,:=AS^IS:^:byname:downloader , attach examplepage_recipe
axs byname examplepage_recipe , download
echo "-----------------"
axs byname examplepage_downloaded , get_path
echo "+++++++++++++++++"
$MD5CMD `axs byname examplepage_downloaded , get_path` | cut -f 1 -d " "
echo "_________________"
$MD5CMD `axs byname examplepage_downloaded , get_path` | cut -f 1 -d " " | sed "s/\\\\//g"
echo "================="
assert '$MD5CMD `axs byname examplepage_downloaded , get_path` | cut -f 1 -d " " | sed "s/\\\\//g"' '84238dfc8092e5d9c0dac8ef93371a07'
axs byname examplepage_downloaded , remove
axs byname examplepage_recipe , remove
assert_end url_downloading_recipe_activation_and_removal

echo "axs tests done"


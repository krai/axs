#!/bin/bash

source assert.sh

# To enable compilation of source-only pip wheels on Intel Macs:
#   https://github.com/facebookresearch/detectron2/issues/2288
#   https://github.com/gorakhargosh/watchdog/issues/689
if [ `axs func platform.system` == "Darwin" ] && [ `axs func platform.machine` == "x86_64" ]; then
    export ARCHFLAGS="-arch x86_64"
    # avoid compiling broken "ml_dtypes" package:
    export PIP_ONLY_BINARY=ml_dtypes
fi

# On Windows: avoid compiling "tokenizers" package that needs Rust compiler
if [ `axs func platform.system` == "Windows" ]; then
    export PIP_ONLY_BINARY=tokenizers
fi

assert 'echo "Hello, world!"' 'Hello, world!'
assert_end testing_assert_itself

assert 'axs get xyz --xyz=123' 123
assert 'axs dig greek.2 --greek,=alpha,beta,gamma,delta' 'gamma'
assert 'axs substitute "Hello, #{x}#" --x=mate' 'Hello, mate'
assert_end on_the_fly_data_access

axs fresh_entry , plant greeting Hello address mate n 42 , save foo
assert 'axs bypath foo , get n' 42
assert 'axs bypath foo , substitute "#{greeting}#, #{address}#!"' 'Hello, mate!'
rm -rf foo
assert_end entry_creation_and_data_access

assert "axs mi: bypath missing , plant alpha 10 beta 20 , plant formula --:='^^:substitute:#{alpha}#-#{beta}#' , own_data" "{'alpha': 10, 'beta': 20, 'formula': '10-20'}"
assert "axs mi: bypath missing , plant alpha 10 beta 20 , plant formula --:='AS^IS:^^:substitute:#{alpha}#-#{beta}#' , own_data" "{'alpha': 10, 'beta': 20, 'formula': ['^^', 'substitute', '#{alpha}#-#{beta}#']}"
assert "axs mi: bypath missing , plant alpha 10 beta 20 , plant formula --:='AS^IS:^^:substitute:#{alpha}#-#{beta}#' , get formula --alpha=30" "30-20"
assert "axs mi: bypath missing , plant alpha 10 beta 20 , plant formula --:='AS^IS:^^:substitute:#{alpha}#-#{beta}#' , get formula --alpha=30 , , get mi , own_data" "{'alpha': 10, 'beta': 20, 'formula': ['^^', 'substitute', '#{alpha}#-#{beta}#']}"
assert_end escaping_nested_calls_immediate_execution

axs fresh_entry ---own_data='{ "n": 5, "_subs1": [ "AS^IS", "AS^IS", "^^", "substitute", "N: #{n}#" ], "_subs2": [ "AS^IS", "AS^IS", "^^", "execute", [[ [ "substitute", "N: #{n}#" ] ]] ], "_subs3": [ "AS^IS", "AS^IS", "^^", "execute", [[ [ "get_kernel" ], [ "substitute", "N: #{n}#" ] ]] ] }' , save varisubs2
assert 'axs bypath varisubs2 , get _subs1' 'N: 5'
assert 'axs bypath varisubs2 , get _subs2' 'N: 5'
assert 'axs bypath varisubs2 , get _subs3' 'N: None'
assert 'axs bypath varisubs2 , get _subs1 --n=1' 'N: 1'
assert 'axs bypath varisubs2 , get _subs2 --n=2' 'N: 2'
assert 'axs bypath varisubs2 , get _subs3 --n=3' 'N: None'
axs bypath varisubs2 , remove
axs fresh_entry ---own_data='{ "n": 5, "_subs1": [ "AS^IS", "AS^IS", "^", "substitute", "N: #{n}#", {}, ["n"] ], "_subs2": [ "AS^IS", "AS^IS", "^", "execute", [[ [ "substitute", "N: #{n}#" ] ]], {}, ["n"] ], "_subs3": [ "AS^IS", "AS^IS", "^", "execute", [[ [ "get_kernel" ], [ "substitute", "N: #{n}#" ] ]], {}, ["n"] ] }' , save varisubs1
assert 'axs bypath varisubs1 , get _subs1' 'N: 5'
assert 'axs bypath varisubs1 , get _subs2' 'N: 5'
assert 'axs bypath varisubs1 , get _subs3' 'N: 5'
assert 'axs bypath varisubs1 , get _subs1 --n=1' 'N: 1'
assert 'axs bypath varisubs1 , get _subs2 --n=2' 'N: 2'
assert 'axs bypath varisubs1 , get _subs3 --n=3' 'N: 3'
axs bypath varisubs1 , remove
assert_end overriding_formula_variables

axs fresh_entry , plant alpha 10 beta 20 gamma 30 multisub --:="AS^IS:^^:substitute:#{alpha}#, #{beta}# and #{gamma}#" , save grandma
axs fresh_entry , plant beta 200 gamma 300 _parent_entries --,:=AS^IS:^:bypath:grandma , save mum
assert 'axs bypath mum , substitute "#{alpha}# and #{beta}#"' '10 and 200'
assert 'axs bypath mum , get multisub --beta=2000' '10, 2000 and 300'
axs fresh_entry , plant gamma 31 delta 41 epsilon 51 zeta 60 multisub2 --,:="AS^IS:^^:substitute:#{gamma}#-#{delta}#,AS^IS:^^:substitute:#{epsilon}#-#{zeta}#" , save granddad
axs fresh_entry , plant delta 410 epsilon 510 _parent_entries --,:=AS^IS:^:bypath:granddad , save dad
axs fresh_entry , plant lambda 7000 mu 8000 _parent_entries --,:=AS^IS:^:bypath:dad,AS^IS:^:bypath:mum , save child
assert 'axs bypath child , substitute "#{alpha}#+#{beta}#, #{gamma}#-#{delta}#, #{epsilon}#*#{lambda}#"' '10+200, 31-410, 510*7000'
assert 'axs bypath dad , get multisub2 --delta=411 --zeta=611' "['31-411', '510-611']"
assert 'axs d: bypath dad , dig d.multisub2.1 --epsilon=3333' "3333-60"
assert 'axs d: bypath dad , dig d.multisub2.1 --epsilon=3333 , , get d , dig d.multisub2.1 --epsilon=4444' "4444-60"
axs bypath child    , remove
axs bypath mum      , remove
axs bypath grandma  , remove
axs bypath dad      , remove
axs bypath granddad , remove
assert_end entry_creation_multiple_inheritance_and_removal

assert 'axs byname base_for_editing , get number' '7'
assert 'axs byname base_for_editing , get number --number+=980' '987'
assert 'axs byname base_for_editing , get string' 'abc'
assert 'axs byname base_for_editing , get string --string+=de' 'abcde'
assert 'axs byname base_for_editing , get list' '[10, 20, 30]'
assert 'axs byname base_for_editing , get list --list+,=40,50' '[10, 20, 30, 40, 50]'
assert 'axs byname base_for_editing , get dic' "{'alpha': 100, 'gamma': 200}"
assert 'axs byname base_for_editing , get dic --dic+,::=gamma:300,delta:400' "{'alpha': 100, 'gamma': 300, 'delta': 400}"
assert_end editing_override

assert 'axs byname child_for_editing , get number' '907'
assert 'axs byname child_for_editing , get string' 'abcde'
assert 'axs byname child_for_editing , get list' '[10, 20, 30, 40, 50]'
assert 'axs byname child_for_editing , get dic' "{'alpha': 100, 'gamma': 300, 'delta': 400}"
assert 'axs byname child_for_editing , get number --number+=980' '1887'
assert 'axs byname child_for_editing , get number --number+=90' '997'
assert 'axs byname child_for_editing , get string --string+=fgh' 'abcdefgh'
assert 'axs byname child_for_editing , get list --list+,=60,70' '[10, 20, 30, 40, 50, 60, 70]'
assert 'axs byname child_for_editing , get dic --dic+,::=gamma:500,delta:600' "{'alpha': 100, 'gamma': 500, 'delta': 600}"
assert 'axs byname child_for_editing , get dic --dic+,::=beta:800' "{'alpha': 100, 'gamma': 300, 'delta': 400, 'beta': 800}"
assert 'axs byname child_for_editing , get dic --empty_dic+,::=beta:500' "{'alpha': 100, 'gamma': 300, 'delta': 400}"
assert 'axs byname child_for_editing , get empty_dic --empty_dic+,::=beta:500' "{'beta': 500}"
assert 'axs byname child_for_editing , get empty_list --empty_list+,=100,200' "[100, 200]"
assert_end editing_child_override

#axs byname git , clone --repo_name=counting_collection
axs byquery git_repo,collection,repo_name=counting_collection,url_prefix=https://github.com/ens-lg4
export REPO_DIG_OUTPUT=`axs byname French , dig number_mapping.5`
assert "echo $REPO_DIG_OUTPUT" 'cinq'
axs byquery git_repo,collection,repo_name=counting_collection , pull
axs byname counting_collection , remove
axs byquery shell_tool,can_git --- , remove
assert_end git_cloning_collection_access_and_removal

axs work_collection , attached_entry examplepage_recipe , plant url http://example.com/ newborn_entry_name examplepage_downloaded file_path example.html _parent_entries --,:=AS^IS:^:byname:downloader , save
axs byname examplepage_recipe , download
assert 'axs byquery downloaded,file_name:=example.html , file_path: get_path , , byquery shell_tool,can_compute_md5 , run' '84238dfc8092e5d9c0dac8ef93371a07'
axs byquery shell_tool,can_compute_md5 --- , remove

#axs byquery downloaded,file_path=example.html , get _replay --entry_name=replay_examplepage_downloaded
#assert 'diff -r examplepage_downloaded replay_examplepage_downloaded' ''
#assert 'diff examplepage_downloaded/example.html replay_examplepage_downloaded/example.html' ''

#axs byname replay_examplepage_downloaded , remove

axs byquery downloaded,file_name:=example.html --- , remove
axs byname examplepage_recipe , remove
axs byquery shell_tool,can_download_url --- , remove
assert_end url_downloading_recipe_activation_replay_and_removal


export KERNEL_PYTHON_VERSION=`axs kernel_python_major_dot_minor`
echo "kernel Python version: $KERNEL_PYTHON_VERSION"
export KERNEL_PYTHON_MINOR_VERSION=`axs kernel_python_major_dot_minor , split . , __getitem__ 1`

if [ "$PACKAGE_INSTALL_AND_IMPORT" == "on" ]; then
    if [ "$KERNEL_PYTHON_MINOR_VERSION" -lt "10" ]; then    # compare MINOR versions numerically
        export DESIRED_NUMPY_VERSION="1.19.4"
    else
        export DESIRED_NUMPY_VERSION="1.22.4"
    fi
    export NUMPY_QUERY_MOD="--numpy_query+,=package_version=${DESIRED_NUMPY_VERSION}"

    axs byname numpy_import_test , deps_versions $NUMPY_QUERY_MOD #
    assert "axs byname numpy_import_test , deps_versions ${NUMPY_QUERY_MOD}" "numpy==${DESIRED_NUMPY_VERSION}, pillow==8.1.2"

    assert 'axs byname numpy_import_test , kernel_python_major_dot_minor' "$KERNEL_PYTHON_VERSION"
    assert 'axs byname numpy_import_test , multiply 1 2 3 4 5 6' '[17, 39]'
    axs byquery --,=python_package,package_name=pillow --- , remove
    axs byquery --:=python_package:package_name=numpy --- , remove
    axs byquery --/=shell_tool/can_python --- , remove
    assert_end dependency_installation_and_resolution_for_internal_code
else
    echo "Skipping the PACKAGE_INSTALL_AND_IMPORT test"
fi


if [ "$C_COMPILE_AND_RUN" == "on" ]; then
    # square root
    assert 'axs byquery compiled,square_root , run --area=64' "When square's area is 64.0 its side is 8.00"
    axs byquery compiled,square_root --- , remove
    assert_end c_code_compilation_and_execution

    # generate primes
    axs byquery compiled,generate_primes
    axs byquery program_output,generate_primes,up_to=20
    assert 'axs byname primes_up_to_20 , dig program_output.primes' '[2, 3, 5, 7, 11, 13, 17, 19]'
    axs byquery program_output,generate_primes,up_to=20 --- , remove
    axs byquery compiled,generate_primes --- , remove
    assert_end generate_primes

    # factorized numbers
    axs byquery program_output,factorizer,up_to=172
    export FACTORIZED_NUM=`axs byquery program_output,factorizer,up_to=172 , dig program_output`
    assert "echo $FACTORIZED_NUM" "{factorized_number: [2, 2, 43]}"
    axs byquery program_output,factorizer,up_to=172 --- , remove
    axs byquery compiled,factorizer --- , remove
    axs byquery program_output,generate_primes,up_to=172 --- , remove
    axs byquery compiled,generate_primes --- , remove

    axs byquery lib,lib_name=cjson --- , remove
    axs byquery shell_tool,can_compile_c --- , remove
    axs byquery git_repo,repo_name=cjson_source_git --- , remove
    axs byquery shell_tool,can_git --- , remove

    assert_end factorized_numbers

else
    echo "Skipping the C_COMPILE_AND_RUN test"
fi

if [ "$PYTORCH_CLASSIFY" == "on" ] || [ "$ONNX_CLASSIFY" == "on" ] || [ "$TF_CLASSIFY" == "on" ]; then
    if [ "$PYTORCH_CLASSIFY" == "on" ]; then
        # The following line is split into two to provide more insight into what is going on.
        # Otherwise assert() blocks all the error output and the command looks "stuck" for quite a while.

        if [ "$KERNEL_PYTHON_MINOR_VERSION" -lt "10" ]; then    # compare MINOR versions numerically
            export TORCH_VISION_QUERY_MOD="--torchvision_query+=package_version=0.9.0"
        else
            export TORCH_VISION_QUERY_MOD=""
        fi

        axs byname image_classification_using_pytorch_py , run $TORCH_VISION_QUERY_MOD ---capture_output=false --output_file_path=
        export INFERENCE_OUTPUT=`axs byname image_classification_using_pytorch_py , run $TORCH_VISION_QUERY_MOD ---capture_output=true --output_file_path=`
        assert 'echo $INFERENCE_OUTPUT' 'batch 1/1: (1..20) [65, 795, 230, 809, 520, 65, 334, 852, 674, 332, 109, 286, 370, 757, 595, 147, 327, 23, 478, 517]'
        axs byquery program_output,task=image_classification,framework=pytorch,num_of_images=32
        export ACCURACY_OUTPUT=`axs byquery program_output,task=image_classification,framework=pytorch,num_of_images=32 , get accuracy`
        echo "Accuracy: $ACCURACY_OUTPUT"
        assert 'echo $ACCURACY_OUTPUT' '0.71875'

        axs byquery python_package,package_name=torchvision --- , remove

        assert_end image_classification_using_pytorch_py
    else
        echo "Skipping the PYTORCH_CLASSIFY test"
    fi

    if [ "$ONNX_CLASSIFY" == "on" ]; then
        # The following line is split into two to provide more insight into what is going on.
        # Otherwise assert() blocks all the error output and the command looks "stuck" for quite a while.

        if [ "$KERNEL_PYTHON_MINOR_VERSION" -le "6" ]; then    # compare MINOR versions numerically
            export ONNXRUNTIME_QUERY_MOD="--onnxruntime_query+=package_version=1.9.0"
        elif [ "$KERNEL_PYTHON_MINOR_VERSION" -lt "10" ]; then
            export ONNXRUNTIME_QUERY_MOD="--onnxruntime_query+=package_version=1.10.0"
        else
            export ONNXRUNTIME_QUERY_MOD=""
        fi

        axs byname image_classification_using_onnxrt_py , run $ONNXRUNTIME_QUERY_MOD ---capture_output=false --output_file_path=
        export INFERENCE_OUTPUT=`axs byname image_classification_using_onnxrt_py , run $ONNXRUNTIME_QUERY_MOD ---capture_output=true --output_file_path=`
        assert 'echo $INFERENCE_OUTPUT' 'batch 1/1: (1..20) [65, 795, 230, 809, 516, 67, 334, 415, 674, 332, 109, 286, 370, 757, 595, 147, 327, 23, 478, 517]'

        axs byquery program_output,task=image_classification,framework=onnxrt,num_of_images=32

        export ACCURACY_OUTPUT=`axs byquery program_output,task=image_classification,framework=onnxrt,num_of_images=32 , get accuracy`
        echo "Accuracy: $ACCURACY_OUTPUT"
        assert 'echo $ACCURACY_OUTPUT' '0.84375'

        axs byquery downloaded,onnx_model --- , remove
        axs byquery shell_tool,can_uncompress_gz --- , remove

        axs byquery python_package,package_name=onnxruntime --- , remove
        axs byquery python_package,package_name=onnxruntime-gpu --- , remove

        assert_end image_classification_using_onnxrt_py
    else
        echo "Skipping the ONNX_CLASSIFY test"
    fi

    if [ "$TF_CLASSIFY" == "on" ]; then
        # The following line is split into two to provide more insight into what is going on.
        # Otherwise assert() blocks all the error output and the command looks "stuck" for quite a while.

        axs byname image_classification_using_tf_py , run ---capture_output=false --output_file_path=
        export INFERENCE_OUTPUT=`axs byname image_classification_using_tf_py , run ---capture_output=true --output_file_path=`
        assert 'echo $INFERENCE_OUTPUT' 'batch 1/1: (1..20) [65, 795, 230, 809, 529, 57, 334, 434, 674, 332, 109, 286, 370, 757, 595, 147, 327, 23, 478, 517]'

        axs byquery program_output,task=image_classification,framework=tf,num_of_images=32

        export ACCURACY_OUTPUT=`axs byquery program_output,task=image_classification,framework=tf,num_of_images=32 , get accuracy`
        echo "Accuracy: $ACCURACY_OUTPUT"
        assert 'echo $ACCURACY_OUTPUT' '0.8125'

        axs byquery extracted,tf_model --- , remove
        axs byquery downloaded,tf_model --- , remove

        axs byquery python_package,package_name=tensorflow --- , remove

        assert_end image_classification_using_tf_py
    else
        echo "Skipping the TF_CLASSIFY test"
    fi

    axs byquery preprocessed,dataset_name=imagenet --- , remove
    axs byquery python_package,package_name=pillow --- , remove
    axs byquery python_package,package_name=numpy --- , remove

    axs byquery program_output,task=image_classification --- , remove
    axs byquery imagenet_annotation,extracted --- , remove
    axs byquery imagenet_annotation,downloaded --- , remove

    axs byquery extracted,archive_name=ILSVRC2012_img_val_500.tar --- , remove

    axs byquery shell_tool,can_extract_tar --- , remove

    axs byquery downloaded,file_name:=ILSVRC2012_img_val_500.tar --- , remove
    axs byquery shell_tool,can_compute_md5 --- , remove
    axs byquery shell_tool,can_download_url --- , remove

    axs byquery shell_tool,can_python --- , remove
    axs byquery shell_tool,can_gpu --- , remove
fi

#axs byquery program_output,calendar , get program_output
#assert `axs byquery program_output,calendar , get program_output` "{'calendar': '    October 2022\nMo Tu We Th Fr Sa Su\n                1  2\n 3  4  5  6  7  8  9\n10 11 12 13 14 15 16\n17 18 19 20 21 22 23\n24 25 26 27 28 29 30\n31\n'}"
#axs byquery program_output,calendar --- , remove

if [ "$ONNX_DETECTION" == "on" ]; then
    axs byquery program_output,task=object_detection,framework=onnxrt
    #export ACCURACY_OUTPUT=$(eval "axs byquery program_output,task=object_detection,framework=onnxrt , get accuracy" | tail -1)
    export ACCURACY_OUTPUT=`axs byquery program_output,task=object_detection,framework=onnxrt , get accuracy ,0 func round 4`
    echo "Accuracy: $ACCURACY_OUTPUT"
    assert 'echo $ACCURACY_OUTPUT' '0.2302'
    axs byquery program_output,task=object_detection,framework=onnxrt --- , remove
    assert_end object_detection_using_onnxrt_py
fi

if [ "$PYTORCH_BERT_DEMO" == "on" ]; then
    axs byname bert_demo_torch_py , run
    export BERT_DEMO_OUTPUT=`axs byname bert_demo_torch_py , run --capture_output+`
    assert "echo $BERT_DEMO_OUTPUT" "Question_1: Which country has Moscow as the capital? Answer_1: the soviet union Question_2: How old is the capital of the Soviet Union? Answer_2: more than 800 years Question_3: Where is the Bolshoi Theater? Answer_3: moscow Question_4: How many museums are there in the capital of the Soviet Union? Answer_4: 150 Question_5: What is the Kremlin? Answer_5: a fortress surrounded by red stone walls Question_6: Where is the Kremlin? Answer_6: in the heart of moscow Question_7: What is inside the Kremlin? Answer_7: palaces , cathedrals and buildings housing the seat of the soviet government Question_8: What colour are the stones of the Kremlin? Answer_8: red"
    assert_end pytorch_bert_demo
fi

if [ "$ONNX_BERT_SQUAD" == "on" ]; then
    #axs byquery preprocessed,dataset_name=squad_v1_1
    axs byquery program_output,task=bert,framework=onnxrt,batch_count=20
    export ACCURACY_OUTPUT=`axs byquery program_output,task=bert,framework=onnxrt,batch_count=20 , get accuracy_dict`
    echo "Accuracy: $ACCURACY_OUTPUT"
    assert 'echo $ACCURACY_OUTPUT' "{'exact_match': 85.0, 'f1': 85.0}"
    axs byquery program_output,task=bert,framework=onnxrt,batch_count=20 --- , remove
    axs byquery preprocessed,dataset_name=squad_v1_1 --- , remove
    assert_end bert_using_onnxrt_py
fi


echo "axs tests done"


def generate_user_conf(loadgen_param_dictionary, model_name, loadgen_scenario, target_user_conf_path):

    param_to_conf_pair = {
        "loadgen_multistreamness":      ("samples_per_query", 1),
        "loadgen_max_query_count":      ("max_query_count", 1),
        "loadgen_buffer_size":          ("performance_sample_count_override", 1),
        "loadgen_samples_per_query":    ("samples_per_query", 1),
        "loadgen_target_latency":       ("target_latency", 1),
        "loadgen_target_qps":           ("target_qps", 1),
        "loadgen_max_duration_s":       ("max_duration_ms", 1000),
        "loadgen_offline_expected_qps": ("offline_expected_qps", 1),
    }

    user_conf   = []
    for param_name in loadgen_param_dictionary.keys():
        if param_name in param_to_conf_pair:
            orig_value = loadgen_param_dictionary[param_name]
            if orig_value is not None:
                (config_category_name, multiplier) = param_to_conf_pair[param_name]
                new_value = orig_value if multiplier==1 else float(orig_value)*multiplier
                user_conf.append("{}.{}.{} = {}\n".format(model_name, loadgen_scenario, config_category_name, new_value))

    with open(target_user_conf_path, 'w') as user_conf_file:
         user_conf_file.writelines(user_conf)

    return target_user_conf_path


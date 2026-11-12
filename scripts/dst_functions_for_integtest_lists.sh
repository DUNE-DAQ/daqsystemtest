# This script needs to be sourced.
#
# Its purpose is to define functions that are useful in manipulating lists
# of integration tests.

# function to check for a specific string in a list
string_in_list() {
    # get the search string from the first argument
    local search_string="$1"
    shift

    # read the remaining positional arguments into a local array
    local local_arr=( "$@" )

    # check for the presence of the search string
    local item
    for item in "${local_arr[@]}"; do
        if [[ "${item}" == "${search_string}" ]]; then
            return 0
        fi
    done
    return 1
}

# Adds elements to a specified list, unless they are already present.
# Usage:  add_unique_elements_to_list target_list list_of_new_items
# Note the absence of "$" and "[@]" for the list names.  This is
# because this function expects references to the lists.
# The function returns 1 if invalid arguments were provided, zero otherwise.
add_unique_elements_to_list() {
    if [[ $# -ne 2 ]]; then return 1; fi
    local -n target_list_ref=$1
    local -n new_item_list_ref=$2
    local new_item
    for new_item in "${new_item_list_ref[@]}"; do
        if ! string_in_list "$new_item" "${target_list_ref[@]}"; then
            target_list_ref+=("$new_item")
        fi
    done
    return 0
}

# Removes elements from a specified list.
# Usage:  remove_elements_from_list target_list list_of_unwanted_items
# Note the absence of "$" and "[@]" for the list names.  This is
# because this function expects references to the lists.
# The function returns 1 if invalid arguments were provided, zero otherwise.
remove_elements_from_list() {
    if [[ $# -ne 2 ]]; then return 1; fi
    local -n target_list_ref=$1
    local -n unwanted_item_list_ref=$2
    local unwanted_item idx
    for unwanted_item in "${unwanted_item_list_ref[@]}"; do
        for idx in "${!target_list_ref[@]}"; do
            if [[ "${target_list_ref[$idx]}" == "${unwanted_item}" ]]; then
                unset 'target_list_ref[idx]'
            fi
        done
    done
    # re-index the array to remove gaps
    target_list_ref=("${target_list_ref[@]}")
    return 0
}

# Removes tests from a list of tests based on a list of unwanted repositories.
# Usage:  remove_tests_by_repo target_list list_of_unwanted_repos
# Note the absence of "$" and "[@]" for the list names.  This is
# because this function expects references to the lists.
# The function returns 1 if invalid arguments were provided, zero otherwise.
remove_tests_by_repo() {
    if [[ $# -ne 2 ]]; then return 1; fi
    local -n target_list_ref=$1
    local -n unwanted_repo_list_ref=$2
    local unwanted_repo idx
    for unwanted_repo in "${unwanted_repo_list_ref[@]}"; do
        for idx in "${!target_list_ref[@]}"; do
            local repo_name="`dirname ${target_list_ref[$idx]}`"
            if [[ "${repo_name}" == "${unwanted_repo}" ]]; then
                unset 'target_list_ref[idx]'
            fi
        done
    done
    # re-index the array to remove gaps
    target_list_ref=("${target_list_ref[@]}")
    return 0
}

# Removes tests from a list of tests based on a pipe-delimited string
# of unwanted substrings and matches to the test names.
# Usage:  remove_tests_with_egrep target_list egrep_search_string
# Note the absence of "$" and "[@]" for the list names.  This is
# because this function expects references to the lists.
# The function returns 1 if invalid arguments were provided, zero otherwise.
remove_tests_with_egrep() {
    if [[ $# -ne 2 ]]; then return 1; fi
    local -n target_list_ref=$1
    local -n egrep_search_string_ref=$2
    if [[ -z "${egrep_search_string_ref}" ]]; then return 1; fi
    local idx
    for idx in "${!target_list_ref[@]}"; do
        local test_name="`basename ${target_list_ref[$idx]}`"
        if [[ "`echo ${test_name} | egrep -i ${egrep_search_string_ref:-nullnullnull}`" != "" ]]; then
            unset 'target_list_ref[idx]'
        fi
    done
    # re-index the array to remove gaps
    target_list_ref=("${target_list_ref[@]}")
    return 0
}

# Keeps tests from a list of tests based on a pipe-delimited string
# of desired substrings and matches to the test names.
# Usage:  filter_tests_with_egrep target_list egrep_search_string
# Note the absence of "$" and "[@]" for the list names.  This is
# because this function expects references to the lists.
# The function returns 1 if invalid arguments were provided, zero otherwise.
filter_tests_with_egrep() {
    if [[ $# -ne 2 ]]; then return 1; fi
    local -n target_list_ref=$1
    local -n egrep_search_string_ref=$2
    if [[ -z "${egrep_search_string_ref}" ]]; then return 1; fi
    local idx
    for idx in "${!target_list_ref[@]}"; do
        local test_name="`basename ${target_list_ref[$idx]}`"
        if [[ "`echo ${test_name} | egrep -i ${egrep_search_string_ref:-nullnullnull}`" == "" ]]; then
            unset 'target_list_ref[idx]'
        fi
    done
    # re-index the array to remove gaps
    target_list_ref=("${target_list_ref[@]}")
    return 0
}

# **********************************************
# run self-tests of the functions defined above
# **********************************************

# only run the self-tests the first time that this file is sourced
if [[ "${dst_tmp_list1}" != "" ]]; then
    return
fi
echo "CCCDDD" >&2

# check add_unique_elements_to_list()
dst_tmp_list1=(a b c d)
dst_tmp_str="b"
dst_tmp_listb=($dst_tmp_str)
add_unique_elements_to_list dst_tmp_list1 dst_tmp_listb
dst_tmp_str="q"
dst_tmp_listb=($dst_tmp_str)
add_unique_elements_to_list dst_tmp_list1 dst_tmp_listb
if [[ "${#dst_tmp_list1[@]}" -ne 5 ]] || [[ "${dst_tmp_list1[0]}" != "a" ]] || [[ "${dst_tmp_list1[-1]}" != "q" ]]; then
    echo ""
    echo -e "\U1f7e1 WARNING: A self-check of the 'add_unique_elements_to_list' function failed."
    echo -e "\U1f7e1 WARNING: The (5) expected results of the test are 'a b c d q', but the (${#dst_tmp_list1[@]}) actual results were '${dst_tmp_list1[@]}'."
    echo ""
fi

# check add_unique_elements_to_list() more
dst_tmp_list1=(a b c d)
dst_tmp_list2=(b c d e f)
add_unique_elements_to_list dst_tmp_list1 dst_tmp_list2
if [[ "${#dst_tmp_list1[@]}" -ne 6 ]] || [[ "${dst_tmp_list1[0]}" != "a" ]] || [[ "${dst_tmp_list1[-1]}" != "f" ]]; then
    echo ""
    echo -e "\U1f7e1 WARNING: A self-check of the 'add_unique_elements_to_list' function failed."
    echo -e "\U1f7e1 WARNING: The (6) expected results of the test are 'a b c d e f', but the (${#dst_tmp_list1[@]}) actual results were '${dst_tmp_list1[@]}'."
    echo ""
fi

# check remove_elements_from_list()
dst_tmp_list2=(a d f)
remove_elements_from_list dst_tmp_list1 dst_tmp_list2
if [[ "${#dst_tmp_list1[@]}" -ne 3 ]] || [[ "${dst_tmp_list1[0]}" != "b" ]] || [[ "${dst_tmp_list1[-1]}" != "e" ]]; then
    echo ""
    echo -e "\U1f7e1 WARNING: A self-check of the 'remove_elements_from_list' function failed."
    echo -e "\U1f7e1 WARNING: The (3) expected results of the test are 'b c e', but the (${#dst_tmp_list1[@]}) actual results were '${dst_tmp_list1[@]}'."
    echo ""
fi

# check remove_tests_by_repo()
dst_tmp_list_of_tests=(crtmodules/crt_frame_builder_test.py daqsystemtest/minimal_system_quick_test.py daqsystemtest/small_footprint_quick_test.py dfmodules/disabled_output_test.py dfmodules/offline_prod_run_test.py drunc/basic_multiapp_test.py drunc/failure_mode_fsm_cmd_timeout_nest_app_test.py drunc/pmaas_test.py listrev/listrev_test.py trigger/change_rate_test.py)
dst_tmp_repo_list=(dfmodules crtmodules)
remove_tests_by_repo dst_tmp_list_of_tests dst_tmp_repo_list
if [[ "${#dst_tmp_list_of_tests[@]}" -ne 7 ]] \
       || [[ "${dst_tmp_list_of_tests[0]}" != "daqsystemtest/minimal_system_quick_test.py" ]] || \
       [[ "${dst_tmp_list_of_tests[-1]}" != "trigger/change_rate_test.py" ]]; then
    echo ""
    echo -e "\U1f7e1 WARNING: A self-check of the 'remove_tests_by_repo' function failed."
    echo -e "\U1f7e1 WARNING: The (7) expected results of the test are 'daqsystemtest/minimal_system_quick_test.py daqsystemtest/small_footprint_quick_test.py drunc/basic_multiapp_test.py drunc/failure_mode_fsm_cmd_timeout_nest_app_test.py drunc/pmaas_test.py listrev/listrev_test.py trigger/change_rate_test.py', but the (${#dst_tmp_list_of_tests[@]}) actual results were '${dst_tmp_list_of_tests[@]}'."
    echo ""
fi

# check remove_tests_with egrep()
dst_tmp_list_of_tests=(crtmodules/crt_frame_builder_test.py daqsystemtest/minimal_system_quick_test.py daqsystemtest/small_footprint_quick_test.py dfmodules/disabled_output_test.py dfmodules/offline_prod_run_test.py drunc/basic_multiapp_test.py drunc/failure_mode_fsm_cmd_timeout_nest_app_test.py drunc/pmaas_test.py listrev/listrev_test.py trigger/change_rate_test.py)
dst_tmp_egrep_string="ui|aa|ff"
remove_tests_with_egrep dst_tmp_list_of_tests dst_tmp_egrep_string
if [[ "${#dst_tmp_list_of_tests[@]}" -ne 5 ]] \
       || [[ "${dst_tmp_list_of_tests[0]}" != "dfmodules/disabled_output_test.py" ]] || \
       [[ "${dst_tmp_list_of_tests[-1]}" != "trigger/change_rate_test.py" ]]; then
    echo ""
    echo -e "\U1f7e1 WARNING: A self-check of the 'remove_tests_with_egrep' function failed."
    echo -e "\U1f7e1 WARNING: The (5) expected results of the test are 'dfmodules/disabled_output_test.py drunc/basic_multiapp_test.py drunc/failure_mode_fsm_cmd_timeout_nest_app_test.py listrev/listrev_test.py trigger/change_rate_test.py', but the (${#dst_tmp_list_of_tests[@]}) actual results were '${dst_tmp_list_of_tests[@]}'."
    echo ""
fi

# check filter_tests_with egrep()
dst_tmp_list_of_tests=(crtmodules/crt_frame_builder_test.py daqsystemtest/minimal_system_quick_test.py daqsystemtest/small_footprint_quick_test.py dfmodules/disabled_output_test.py dfmodules/offline_prod_run_test.py drunc/basic_multiapp_test.py drunc/failure_mode_fsm_cmd_timeout_nest_app_test.py drunc/pmaas_test.py listrev/listrev_test.py trigger/change_rate_test.py)
dst_tmp_egrep_string="ui|aa|ff"
filter_tests_with_egrep dst_tmp_list_of_tests dst_tmp_egrep_string
if [[ "${#dst_tmp_list_of_tests[@]}" -ne 5 ]] \
       || [[ "${dst_tmp_list_of_tests[0]}" != "crtmodules/crt_frame_builder_test.py" ]] || \
       [[ "${dst_tmp_list_of_tests[-1]}" != "drunc/pmaas_test.py" ]]; then
    echo ""
    echo -e "\U1f7e1 WARNING: A self-check of the 'filter_tests_with_egrep' function failed."
    echo -e "\U1f7e1 WARNING: The (5) expected results of the test are 'crtmodules/crt_frame_builder_test.py daqsystemtest/minimal_system_quick_test.py daqsystemtest/small_footprint_quick_test.py dfmodules/offline_prod_run_test.py drunc/pmaas_test.py', but the (${#dst_tmp_list_of_tests[@]}) actual results were '${dst_tmp_list_of_tests[@]}'."
    echo ""
fi

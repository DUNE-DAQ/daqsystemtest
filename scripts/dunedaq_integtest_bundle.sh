#!/bin/bash
# 10-Oct-2023, KAB

initial_integtest_list=()

# function to display usage hints
usage() {
    declare -r script_name=$(basename "$0")
    echo """
Usage:
"${script_name}" [option(s)]

Options:
    -h, --help : prints out usage information
    -r <the list of repositories for which integtests will be run>
       - this can be the name of a single repo; it defaults to \"daqsystemtest\"
       - it can be a pipe-delimited string with a list of repos, e.g. 'dfmodules|trigger'
       - it can have the special value of \"all\" - integtests in all repos will be run
       - it can have the special value of \"local\" - integtests in locally-cloned repos will be run
    -R <the list of repositories to be excluded>
       - this can be the name of a single repo
       - it can be a pipe-delimited string with a list of repos, e.g. 'dfmodules|trigger'
    -k, --include <pipe-delimited string to select the tests that will be run ('egrep -i' match to test name)>
    -x, --exclude <pipe-delimited string to specify tests to be excluded ('egrep -i' match to test name)>
    --random-subset <count> : randomly picks the specified number of tests from the results of -r/-k/-x
    --list-only : list the tests that match the requested patterns without running them
    --verbosity <level> : requested level of console messages, in range 1-6, where 1 is least, 6 is DRUNC debug
    --stop-on-failure : causes the script to stop when one of the integtests reports a failure
    --tmpdir <dir> : specifies a root directory to use for test output, e.g. a directory instead of '/tmp'
    --concise-output : suppresses run control and DAQApp messages in order to focus on test results
       - this is equivalent to \"--verbosity 1\", and this option may be removed at some point in time
    -n <number of times to run each individual test, default=1>
    -N <number of times to run the full set of selected tests, default=1>
    --pytest-options <options> : string with one or more dunedaq-specific command-line options to pass to Pytest
       - available options include the following:
         --dunerc-path <path> : Path to DUNE run control. Default is to search in \$PATH
         --skip-resource-checks : Whether to skip the node resource (CPU/Memory) checks for this test
         --process-manager-type <type> : The run control process manager type to use for this test, e.g. ssh-standalone
         --no-integtest-connsvc : Whether to disable the Connectivity Service for this test
         --remove-hdf5-files <choice> : 'always' forces files to be removed, 'never' forces files to be kept
         --dunerc-option <option-name> <option-value> : Repeatable, run control arguments without leading dashes
             for example, --dunerc-option log-level debug
       - example: --pytest-options \"--skip-resource-checks --process-manager-type ssh-standalone --dunerc-option no-override-logs\"
"""
}

# function to report a problem with an invalid option value
invalid_option_value() {
    declare -r script_name=$(basename "$0")
    echo ""
    echo "*** ERROR: Option '$1' requires an argument, but received '$2'"
    echo ">>> Reminder: running '${script_name} --help' will list the supported options"
    echo ""
}

# function to report a problem with an invalid numeric option value
invalid_numeric_option_value() {
    declare -r script_name=$(basename "$0")
    echo ""
    echo "*** ERROR: Option '$1' requires a numeric argument, but received '$2'"
    echo ">>> Reminder: running '${script_name} --help' will list the supported options"
    echo ""
}

# function to check for a specific string in a list
string_in_list() {
    # get the search string from the first argument
    local search_string="$1"
    shift

    # read the remaining positional arguments into a local array
    local local_arr=( "$@" )

    # check for the presence of the search string
    for item in "${local_arr[@]}"; do
        if [[ "${item}" == "${search_string}" ]]; then
            return 0
        fi
    done
    return 1
}

# 29-Dec-2025, KAB: Determine if a non-standard pytest tmpdir has been specified
# in the linux shell environment in which this script is being run. We need to know
# this value in order to direct functionality in this script to the right place.
# A user-specified command-line value for the tmpdir over-rides the value determined here.
tmpdir_root=`dst_get_pytest_tmpdir`

# Removes the ANSI characters associated with formatting, including color coding and font styling
CaptureOutputNoANSI() {
    tee -a >(sed -u 's/\x1b\[[0-9;]*m//g' >> "$1")
}
# Captures the output to the specified file, without changing the output
CaptureOutput() {
    tee -a $1
}

GETOPT_TEMP=$(getopt -o hr:R:k:x:n:N: --long help,stop-on-failure,concise-output,include:,exclude:,tmpdir:,verbosity:,random-subset:,list-only,pytest-options: -n "$0" -- "$@")
if [ $? -ne 0 ]; then
    usage
    exit 1
fi
eval set -- "$GETOPT_TEMP"

let individual_test_requested_iterations=1
let full_set_requested_interations=1
let stop_on_failure=0
requested_repo_list=()
excluded_repo_names=""
requested_test_names=""
excluded_test_names=""
let random_subset_count=0
only_list_tests=""
PYTEST_BASE_COMMAND=(pytest -s --tb=short)  # our core pytest command, with DAQ printout included and short pytest traceback
PYTEST_OPTIONS=()

while true; do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        -r)
            # check that a valid value was passed to this option
            if [[ "$2" =~ ^- ]]; then
                invalid_option_value $1 $2
                exit 1
            fi
            # split a pipe-delimited string into individual elements, if needed
            IFS='|' read -ra tmp_list <<< "$2"
            for repo in "${tmp_list[@]}"; do
                read -rd '' trimmed <<< "$repo"
                requested_repo_list+=("${trimmed}")
            done
            shift 2
            ;;
        -R)
            # check that a valid value was passed to this option
            if [[ "$2" =~ ^- ]]; then
                invalid_option_value $1 $2
                exit 1
            fi
            if [[ "${excluded_repo_names}" == "" ]]; then
                excluded_repo_names="$2"
            else
                excluded_repo_names="${excluded_repo_names}|$2"
            fi
            shift 2
            ;;
        -k|--include)
            # check that a valid value was passed to this option
            if [[ "$2" =~ ^- ]]; then
                invalid_option_value $1 $2
                exit 1
            fi
            if [[ "${requested_test_names}" == "" ]]; then
                requested_test_names="$2"
            else
                requested_test_names="${requested_test_names}|$2"
            fi
            shift 2
            ;;
        -x|--exclude)
            # check that a valid value was passed to this option
            if [[ "$2" =~ ^- ]]; then
                invalid_option_value $1 $2
                exit 1
            fi
            if [[ "${excluded_test_names}" == "" ]]; then
                excluded_test_names=$2
            else
                excluded_test_names="${excluded_test_names}|$2"
            fi
            shift 2
            ;;
        -n)
            # check that a valid value was passed to this option
            if [[ "$2" =~ ^- ]] || ! [[ $2 =~ ^[0-9]+$ ]]; then
                invalid_numeric_option_value $1 $2
                exit 1
            fi
            let individual_test_requested_iterations=$2
            shift 2
            ;;
        -N)
            # check that a valid value was passed to this option
            if [[ "$2" =~ ^- ]] || ! [[ $2 =~ ^[0-9]+$ ]]; then
                invalid_numeric_option_value $1 $2
                exit 1
            fi
            let full_set_requested_interations=$2
            shift 2
            ;;
        --stop-on-failure)
            let stop_on_failure=1
            PYTEST_BASE_COMMAND+=(-x)  # add the -x option to our pytest command to have it exit on first error
            shift
            ;;
        --concise-output)
            PYTEST_OPTIONS+=(--integtest-verbosity 1)
            shift
            ;;
        --tmpdir)
            # check that a valid value was passed to this option
            if [[ "$2" =~ ^- ]]; then
                invalid_option_value $1 $2
                exit 1
            fi
            tmpdir_root=$2
            export PYTEST_DEBUG_TEMPROOT=${tmpdir_root}
            shift 2
            ;;
        --verbosity)
            # check that a valid value was passed to this option
            if [[ "$2" =~ ^- ]] || ! [[ $2 =~ ^[0-9]+$ ]]; then
                invalid_numeric_option_value $1 $2
                exit 1
            fi
            PYTEST_OPTIONS+=(--integtest-verbosity $2)
            let level=$2
            if [[ $level -ge 6 ]]; then
                # enable printout of Pytest 'skip' reasons and turn on drunc debugging
                PYTEST_OPTIONS+=(-rs --dunerc-option log-level debug)
            fi
            shift 2
            ;;
        --random-subset)
            # check that a valid value was passed to this option
            if [[ "$2" =~ ^- ]] || ! [[ $2 =~ ^[0-9]+$ ]]; then
                invalid_numeric_option_value $1 $2
                exit 1
            fi
            let random_subset_count=$2
            shift 2
            ;;
        --pytest-options)
            # use xargs to correctly parse substrings with spaces
            IFS=$'\n' read -rd '' -a the_list < <(xargs -n1 <<< "$2")
            PYTEST_OPTIONS+=("${the_list[@]}")
            shift 2
            ;;
        --list-only)
            only_list_tests="yes"
            shift
            ;;
        --)
            shift
            break
            ;;
    esac
done

# assemgle the basic elements for the pytest command that we will use
if [[ "${#PYTEST_OPTIONS[@]}" -gt 0 ]]; then
    PYTEST_BASE_COMMAND+=("${PYTEST_OPTIONS[@]}" "--")  # Add the requested options to the pytest command
fi

# remove any spurious spaces from test and repo name strings (these will be used in 'egrep' expressions)
requested_test_names=`echo ${requested_test_names} | sed 's/\s//g'`
excluded_test_names=`echo ${excluded_test_names} | sed 's/\s//g'`
excluded_repo_names=`echo ${excluded_repo_names} | sed 's/\s//g'`

# run the integtests from the daqsystemtest repo if no repo was specified
if [[ "${#requested_repo_list}" -eq 0 ]]; then
    requested_repo_list+=("daqsystemtest")
    echo ""
    echo "Integtests from the _daqsystemtest_ repo will be run..."
fi

# provide feedback to the user when a group of tests will be run
if string_in_list "all" "${requested_repo_list[@]}"; then
    echo ""
    echo "Building the list of _all_ integtests..."
else
    if string_in_list "local" "${requested_repo_list[@]}"; then
        echo ""
        echo "Building the list of _local_ integtests..."
    fi
fi

# determine the list of tests
if [[ "${excluded_repo_names}" == "" ]]; then
    initial_integtest_list=(`list_available_integtests.sh ${requested_repo_list[@]} 2>/dev/null`)
else
    initial_integtest_list=(`list_available_integtests.sh ${requested_repo_list[@]} -x "${excluded_repo_names}" 2>/dev/null`)
fi
if [[ ${#initial_integtest_list[@]} -eq 0 ]]; then
    echo ""
    echo "*** No integtests were found in the \"${requested_repo_list[@]}\" repo(s) [with \"${excluded_repo_names}\" repos excluded]."
    echo ""
    exit 3
fi

# check if the numad daemon is running
numad_grep_output=`ps -ef | grep numad | grep -v grep`
if [[ "${numad_grep_output}" != "" ]]; then
    echo "*********************************************************************"
    echo "*** DANGER, DANGER, 'numad' appears to be running on this computer!"
    echo "*** 'ps' output:  ${numad_grep_output}"
    echo "*** <ctrl-c> now if you want to abort this testing."
    echo "*********************************************************************"
    sleep 3
fi

# other setup
INITIAL_TIMESTAMP=`date '+%Y%m%d%H%M%S'`
# 30-Dec-2025, KAB: check that the specified tmpdir exists and is writeable
if [[ ! -d ${tmpdir_root} ]]; then
    echo ""
    echo "*** ERROR: directory \"${tmpdir_root}\" does not exist."
    echo ""
    exit 1
fi
if [[ ! -w ${tmpdir_root} ]]; then
    echo ""
    echo "*** ERROR: directory \"${tmpdir_root}\" is not writeable in the current environment."
    echo ""
    exit 1
fi
pytest_user_dir=${tmpdir_root}/pytest-of-${USER}
mkdir -p ${pytest_user_dir}
ITGRUNNER_LOG_FILE="${pytest_user_dir}/dunedaq_integtest_bundle_${INITIAL_TIMESTAMP}.log"
CURRENT_PID=$$

# do the first level of test filtering
filtered_integtest_list=()
let test_index=0
for FULL_TEST_NAME in "${initial_integtest_list[@]}"; do
    test_name=`basename ${FULL_TEST_NAME}`
    requested_test=`echo ${test_name} | egrep -i ${requested_test_names:-${test_name}}`
    excluded_test=`echo ${test_name} | egrep -i ${excluded_test_names:-nullnullnull}`
    if [[ "${requested_test}" != "" ]] && [[ "${excluded_test}" == "" ]]; then
        filtered_integtest_list+=("${FULL_TEST_NAME}")
    fi
    let test_index=${test_index}+1
done

# reduce the list of tests to a random subset, if requested
if [[ $random_subset_count -gt 0 ]]; then
    filtered_integtest_list=($(shuf -n "$random_subset_count" -e "${filtered_integtest_list[@]}"))
fi

# check if any tests remain; provide hints to the user if not
if [[ ${#filtered_integtest_list[@]} -eq 0 ]]; then
    matching_integtest_list=()
    if  [[ "${requested_test_names}" != "" ]]; then
        echo "...Looking for integtests..."
        full_integtest_list=(`list_available_integtests.sh 2>/dev/null`)
        for repo_test in "${full_integtest_list[@]}"; do
            test_name=`basename ${repo_test}`
            match_string=`echo ${test_name} | egrep ${requested_test_names}`
            if [[ "${match_string}" != "" ]]; then
                matching_integtest_list+=(${repo_test})
            fi
        done
    fi
    echo ""
    echo "*** No integtests were found that matched the specified command-line options."
    if [[ ${#matching_integtest_list[@]} -gt 0 ]]; then
        sleep 1
        repo_name=`dirname ${matching_integtest_list[0]}`
        test_name=`basename ${matching_integtest_list[0]}`
        echo ""
        echo "*** Consider adding '-r ${repo_name}' to the option list to pick up the '${test_name}' test."
        if [[ ${#matching_integtest_list[@]} -gt 1 ]]; then
            for match in "${matching_integtest_list[@]:1}"; do
                repo_name=`dirname ${match}`
                test_name=`basename ${match}`
                echo "*** And/or '-r ${repo_name}' to pick up the '${test_name}' test."
            done
            echo "*** Or '-r all' to pick up all of these tests."
        fi
    fi
    sleep 1
    echo ""
    echo "*** 'list_available_integtests.sh' will list all available tests."
    echo ""
    exit 5
fi

if [[ "$only_list_tests" != "" ]]; then
    let idx=0
    echo ""
    echo "The following tests will be run:"
    for FULL_TEST_NAME in "${filtered_integtest_list[@]}"; do
        let idx+=1
        echo "  ${idx} ${FULL_TEST_NAME}"
    done
    exit 0
fi
let number_of_individual_tests=${#filtered_integtest_list[@]}
let total_number_of_tests=${number_of_individual_tests}*${individual_test_requested_iterations}*${full_set_requested_interations}

# run the tests
let overall_test_index=0  # this is only used for user feedback
let full_set_loop_count=0
while [[ ${full_set_loop_count} -lt ${full_set_requested_interations} ]]; do
    let test_index=0
    for FULL_TEST_NAME in "${filtered_integtest_list[@]}"; do
        test_repo=`dirname ${FULL_TEST_NAME}`
        test_name=`basename ${FULL_TEST_NAME}`
        CURRENT_TIMESTAMP=`date '+%Y%m%d%H%M%S'`
        # 15-Dec-2025, KAB: added the export of the following enviromental variable.  This is used
        # by the integrationtest infrastructure to put a bread-crumb file in the directory where
        # the test results are located.  That file, in turn, allows this script to find the directory
        # for the current test, and make a copy of it if the test fails.
        export DUNEDAQ_INTEGTEST_BUNDLE_INFO="${INITIAL_TIMESTAMP};${CURRENT_PID};${CURRENT_TIMESTAMP}"
        let individual_loop_count=0
        while [[ ${individual_loop_count} -lt ${individual_test_requested_iterations} ]]; do
            let overall_test_index=${overall_test_index}+1
            echo ""
            echo -e "\U0001F535 \033[0;34mStarting test ${overall_test_index} of ${total_number_of_tests}...\033[0m \U0001F535" | CaptureOutput ${ITGRUNNER_LOG_FILE}

            echo -e "\u2B95 \033[0;1mRunning ${FULL_TEST_NAME}\033[0m \u2B05" | CaptureOutput ${ITGRUNNER_LOG_FILE}
            PYTEST_COMMAND=("${PYTEST_BASE_COMMAND[@]}")

            # First, check if the test is found in the Python virtual environment.
            # This picks up tests from our Python-only software packages.
            if [[ "`ls ${DBT_AREA_ROOT}/.venv/lib/python*/site-packages/${test_repo}/integtest/${test_name} 2>/dev/null`" != "" ]]; then
                PYTEST_COMMAND+=(${DBT_AREA_ROOT}/.venv/lib/python*/site-packages/${test_repo}/integtest/${test_name})
                "${PYTEST_COMMAND[@]}" | CaptureOutputNoANSI ${ITGRUNNER_LOG_FILE}

            # Next, check if the test exists in the current working directory.
            # This is a convenience for developers when they are working on an integtest
            # in a C++ package (the test is found without rebuilding the software).
            elif [[ -e "./${test_name}" ]]; then
                PYTEST_COMMAND+=(./${test_name})
                "${PYTEST_COMMAND[@]}" | CaptureOutputNoANSI ${ITGRUNNER_LOG_FILE}

            # Next, check if the test exists in the local software area.
            elif [[ -e "${DBT_AREA_ROOT}/sourcecode/${test_repo}/integtest/${test_name}" ]]; then
                if [[ -w "${DBT_AREA_ROOT}" ]]; then
                    PYTEST_COMMAND+=(${DBT_AREA_ROOT}/sourcecode/${test_repo}/integtest/${test_name})
                    "${PYTEST_COMMAND[@]}" | CaptureOutputNoANSI ${ITGRUNNER_LOG_FILE}
                else
                    # remove any trailing "--" in PYTEST_COMMAND since we are adding more pytest options here
                    if [[ "${PYTEST_COMMAND[-1]}" == "--" ]]; then
                        unset 'PYTEST_COMMAND[-1]'
                    fi
                    PYTEST_COMMAND+=(-p no:cacheprovider --no-summary ${DBT_AREA_ROOT}/sourcecode/${test_repo}/integtest/${test_name})
                    "${PYTEST_COMMAND[@]}" | CaptureOutputNoANSI ${ITGRUNNER_LOG_FILE}
                fi

            # Lastly, we assume that the test can be found in the installed software
            # area (for C++ packages).
            else
                share_envvar_name="${test_repo^^}_SHARE"  # double caret converts env var to uppercase
                # remove any trailing "--" in PYTEST_COMMAND since we are adding more pytest options here
                if [[ "${PYTEST_COMMAND[-1]}" == "--" ]]; then
                    unset 'PYTEST_COMMAND[-1]'
                fi
                PYTEST_COMMAND+=(-p no:cacheprovider --no-summary ${!share_envvar_name}/integtest/${test_name})
                "${PYTEST_COMMAND[@]}" | CaptureOutputNoANSI ${ITGRUNNER_LOG_FILE}
            fi
            let pytest_return_code=${PIPESTATUS[0]}

            let individual_loop_count=${individual_loop_count}+1

            # check if the test failed
            if [[ ${pytest_return_code} -ne 0 ]]; then
                # 15-Dec-2025, KAB: if the test failed for a reason other than it
                # couldn't be found, make a copy of the pytest directory. This allows
                # testers to take a look at the results within a reasonable time frame.
                # (If we can't find the "jq" JSON utility, we simply note that fact
                # and continue.)
                # This code makes use of a bread-crumb file that is created by the
                # integrationtest infrastructure.
                if [[ ${pytest_return_code} -ne 4 ]]; then
                    if [[ "`which jq 2>/dev/null`" != "" ]]; then
                        current_pytest_rundir=""
                        mapfile -t bundle_info_files < <(find "${pytest_user_dir}" -type f -name "bundle_script_info.json" -printf '%T@ %p\n' | grep -v 'failed-' | sort -nr | awk '{print $2}')
                        for info_file in "${bundle_info_files[@]}"; do
                            script_start_time=`jq -r .bundle_script_start_time ${info_file}`
                            script_pid=`jq -r .bundle_script_process_id ${info_file}`
                            individual_test_start_time=`jq -r .individual_test_start_time ${info_file}`
                            if [[ ${script_start_time} -eq ${INITIAL_TIMESTAMP} ]] && \
                                   [[ ${script_pid} -eq ${CURRENT_PID} ]] && \
                                   [[ ${individual_test_start_time} -eq ${CURRENT_TIMESTAMP} ]]; then
                                current_pytest_rundir=$info_file
                                break
                            fi
                        done

                        was_successfully_copied=""
                        if [[ "${current_pytest_rundir}" != "" ]]; then
                            pytest_tmpdir=`echo ${current_pytest_rundir} | xargs -r dirname | xargs -r dirname`
                            if [[ "${pytest_tmpdir}" != "" ]]; then
                                pytest_rootdir=`echo ${pytest_tmpdir} | xargs -r dirname`
                                pytest_basedir=`echo ${pytest_tmpdir} | xargs -r basename`
                                if [[ "${pytest_rootdir}" != "" ]] && [[ "${pytest_basedir}" != "" ]]; then
                                    new_dir="${pytest_rootdir}/failed-${pytest_basedir}"
                                    echo ""
                                    echo -e "\U1F535 Copying the files from failed test ${pytest_tmpdir} to ${new_dir}. \U1F535"
                                    echo -e "\U1F535 Please note that copied directories from failed tests typically get cleaned up after 26 hours, \U1F535"
                                    echo -e "\U1F535 or when 10 newer failures happen, whichever comes first. \U1F535"
                                    cp -pR "${pytest_tmpdir}" "${new_dir}"
                                    if [[ $? == 0 ]]; then
                                        was_successfully_copied="yes"
                                        # 18-Dec-2025, KAB: added the removal of the "current" symbolic links
                                        # from inside the copied directory (since they get broken in the copying)
                                        rm -f "${new_dir}/configcurrent"
                                        rm -f "${new_dir}/runcurrent"
                                    fi
                                fi
                            fi
                        fi
                        if [[ "${was_successfully_copied}" == "" ]]; then
                            echo ""
                            echo -e "\U1f7e1 WARNING: Unable to copy the pytest directory for this failed test (${current_pytest_rundir}). \U1f7e1"
                        fi
                    else
                        echo ""
                        echo -e "\U1f7e1 WARNING: Unable to find the 'jq' utility which is needed to help identify which pytest directory to copy for this failed test. \U1f7e1"
                    fi

                    # remove stale and surplus directories from failed tests
                    test_dirs_to_remove=()
                    mapfile -t all_failed_test_dirs < <(find ${pytest_user_dir} -maxdepth 1 -type d -printf '%T@ %p\n' | sort -nr | awk '{print $2}' | grep 'failed-')
                    surplus_dirs=("${all_failed_test_dirs[@]:10}")
                    for test_dir in "${surplus_dirs[@]}"; do
                        test_dirs_to_remove+=(${test_dir})
                    done
                    stale_failed_test_dirs=(`find ${pytest_user_dir} -maxdepth 1 -type d -name 'failed-*' -cmin +1560 -print`)
                    for test_dir in "${stale_failed_test_dirs[@]}"; do
                        test_dirs_to_remove+=(${test_dir})
                    done
                    if [[ ${#test_dirs_to_remove[@]} -gt 0 ]];then
                        echo ""
                        echo -e "\U1F535 Removing ${#test_dirs_to_remove[@]} old failed test directory(ies). \U1F535"
                        for test_dir in "${test_dirs_to_remove[@]}"; do
                            if [[ -e "${test_dir}" ]]; then
                                rm -rf "${test_dir}"
                            fi
                        done
                    fi
                fi

                # exit out of this script if the user has requested that we stop on a failure
                if [[ ${stop_on_failure} -gt 0 ]]; then
                    break 3
                fi
            fi
        done
        let test_index=${test_index}+1
    done

    let full_set_loop_count=${full_set_loop_count}+1
done

# print out summary information
echo ""                                                   | CaptureOutput ${ITGRUNNER_LOG_FILE}
echo "+++++++++++++++++++++++++++++++++++++++++++++++++"  | CaptureOutput ${ITGRUNNER_LOG_FILE}
echo "++++++++++++++++++++ SUMMARY ++++++++++++++++++++"  | CaptureOutput ${ITGRUNNER_LOG_FILE}
echo "+++++++++++++++++++++++++++++++++++++++++++++++++"  | CaptureOutput ${ITGRUNNER_LOG_FILE}
echo ""                                                   | CaptureOutput ${ITGRUNNER_LOG_FILE}
date                                                      | CaptureOutput ${ITGRUNNER_LOG_FILE}
echo "Log file is: ${ITGRUNNER_LOG_FILE}"                 | CaptureOutput ${ITGRUNNER_LOG_FILE}
echo ""                                                   | CaptureOutput ${ITGRUNNER_LOG_FILE}
summary_string="`egrep $'=====|\u2B95' ${ITGRUNNER_LOG_FILE} | egrep ' in |Running'`"
colorized_summary_string="`echo \"${summary_string}\" | sed 's/passed/passed \\\\U2705/' | sed 's/failed/failed \\\\U274c/' | sed 's/\(errors\?\)/\1 \\\\U1F6A8/' | sed 's/no tests ran/no tests ran \\\\U1F6A8/' | sed 's/skipped/skipped \\\\U1f7e1/'`"
echo -e "${colorized_summary_string}" | CaptureOutput ${ITGRUNNER_LOG_FILE}

# check again if the numad daemon is running
numad_grep_output=`ps -ef | grep numad | grep -v grep`
if [[ "${numad_grep_output}" != "" ]]; then
    echo ""                                                                                 | CaptureOutput ${ITGRUNNER_LOG_FILE}
    echo "********************************************************************************" | CaptureOutput ${ITGRUNNER_LOG_FILE}
    echo "*** WARNING: 'numad' appears to be running on this computer!"                     | CaptureOutput ${ITGRUNNER_LOG_FILE}
    echo "*** 'ps' output:  ${numad_grep_output}"                                           | CaptureOutput ${ITGRUNNER_LOG_FILE}
    echo "*** This daemon can adversely affect the running of these tests, especially ones" | CaptureOutput ${ITGRUNNER_LOG_FILE}
    echo "*** that are resource intensive in the Readout Apps. This is because numad moves" | CaptureOutput ${ITGRUNNER_LOG_FILE}
    echo "*** processes (threads?) to different cores/numa nodes periodically, and that"    | CaptureOutput ${ITGRUNNER_LOG_FILE}
    echo "*** context switch can disrupt the stable running of the DAQ processes."          | CaptureOutput ${ITGRUNNER_LOG_FILE}
    echo "********************************************************************************" | CaptureOutput ${ITGRUNNER_LOG_FILE}
fi
echo ""

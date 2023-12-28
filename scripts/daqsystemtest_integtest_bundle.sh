#!/bin/bash
# 10-Oct-2023, KAB

integtest_list=( "minimal_system_quick_test.py" "readout_type_scan.py" "3ru_3df_multirun_test.py" "fake_data_producer_test.py" "long_window_readout_test.py" "3ru_1df_multirun_test.py" "tpstream_writing_test.py" )

usage() {
    declare -r script_name=$(basename "$0")
    echo """
Usage:
"${script_name}" [option(s)]

Options:
    -h, --help : prints out usage information
    -s <DAQ session number (formerly known as partition number), default=1)>
    -f <zero-based index of the first test to be run, default=0>
    -l <zero-based index of the last test to be run, default=999>
    -n <number of times to run each individual test, default=1>
    -N <number of times to run the full set of selected tests, default=1>
    --stop-on-failure : causes the script to stop when one of the integtests reports a failure
"""
    let counter=0
    echo "List of available tests:"
    for tst in ${integtest_list[@]}; do
        echo "    ${counter}: $tst"
        let counter=${counter}+1
    done
    echo ""
}

TEMP=`getopt -o hs:f:l:n:N: --long help,stop-on-failure -- "$@"`
eval set -- "$TEMP"

let session_number=1
let first_test_index=0
let last_test_index=999
let individual_run_count=1
let overall_run_count=1
let stop_on_failure=0

while true; do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        -s)
            let session_number=$2
            shift 2
            ;;
        -f)
            let first_test_index=$2
            shift 2
            ;;
        -l)
            let last_test_index=$2
            shift 2
            ;;
        -n)
            let individual_run_count=$2
            shift 2
            ;;
        -N)
            let overall_run_count=$2
            shift 2
            ;;
        --stop-on-failure)
            let stop_on_failure=1
            shift
            ;;
        --)
            shift
            break
            ;;
    esac
done

# check if the numad daemon is running
numad_grep_output=`ps -ef | grep numad | grep -v grep`
if [[ "${numad_grep_output}" != "" ]]; then
   echo "*******************************************************"
   echo "*** DANGER, DANGER, numad is running on this computer!"
   echo "*** <ctrl-c> now if you want to abort this testing."
   echo "*******************************************************"
   sleep 3
fi

# other setup
TIMESTAMP=`date '+%Y%m%d%H%M%S'`
mkdir -p /tmp/pytest-of-${USER}
ITGRUNNER_LOG_FILE="/tmp/pytest-of-${USER}/daqsystemtest_integtest_bundle_${TIMESTAMP}.log"

# run the tests
let overall_loop_count=0
while [[ ${overall_loop_count} -lt ${overall_run_count} ]]; do

  let test_index=0
  for TEST_NAME in ${integtest_list[@]}; do
    if [[ ${test_index} -ge ${first_test_index} && ${test_index} -le ${last_test_index} ]]; then

      let individual_loop_count=0
      while [[ ${individual_loop_count} -lt ${individual_run_count} ]]; do
        echo "===== Running ${TEST_NAME}" >> ${ITGRUNNER_LOG_FILE}
        if [[ -e "./${TEST_NAME}" ]]; then
          pytest -s ./${TEST_NAME} --nanorc-option partition-number ${session_number} | tee -a ${ITGRUNNER_LOG_FILE}
        elif [[ -e "${DBT_AREA_ROOT}/sourcecode/daqsystemtest/integtest/${TEST_NAME}" ]]; then
          pytest -s ${DBT_AREA_ROOT}/sourcecode/daqsystemtest/integtest/${TEST_NAME} --nanorc-option partition-number ${session_number} | tee -a ${ITGRUNNER_LOG_FILE}
        else
          pytest -s ${DAQSYSTEMTEST_SHARE}/integtest/${TEST_NAME} --nanorc-option partition-number ${session_number} | tee -a ${ITGRUNNER_LOG_FILE}
        fi
        let pytest_return_code=${PIPESTATUS[0]}

        let individual_loop_count=${individual_loop_count}+1

        if [[ ${stop_on_failure} -gt 0 ]]; then
            if [[ ${pytest_return_code} -ne 0 ]]; then
                break 3
            fi
        fi
      done

    fi
    let test_index=${test_index}+1
  done

  let overall_loop_count=${overall_loop_count}+1
done

# print out summary information
echo ""                                                   | tee -a ${ITGRUNNER_LOG_FILE}
echo ""                                                   | tee -a ${ITGRUNNER_LOG_FILE}
echo "+++++++++++++++++++++++++++++++++++++++++++++++++"  | tee -a ${ITGRUNNER_LOG_FILE}
echo "++++++++++++++++++++ SUMMARY ++++++++++++++++++++"  | tee -a ${ITGRUNNER_LOG_FILE}
echo "+++++++++++++++++++++++++++++++++++++++++++++++++"  | tee -a ${ITGRUNNER_LOG_FILE}
echo ""                                                   | tee -a ${ITGRUNNER_LOG_FILE}
date                                                      | tee -a ${ITGRUNNER_LOG_FILE}
echo "Log file is: ${ITGRUNNER_LOG_FILE}"                 | tee -a ${ITGRUNNER_LOG_FILE}
echo ""                                                   | tee -a ${ITGRUNNER_LOG_FILE}
grep '=====' ${ITGRUNNER_LOG_FILE} | egrep ' in |Running' | tee -a ${ITGRUNNER_LOG_FILE}

# check again if the numad daemon is running
numad_grep_output=`ps -ef | grep numad | grep -v grep`
if [[ "${numad_grep_output}" != "" ]]; then
   echo ""                                                                                 | tee -a ${ITGRUNNER_LOG_FILE}
   echo "********************************************************************************" | tee -a ${ITGRUNNER_LOG_FILE}
   echo "*** WARNING: numad is running on this computer!"                                  | tee -a ${ITGRUNNER_LOG_FILE}
   echo "*** This daemon can adversely affect the running of these tests, especially ones" | tee -a ${ITGRUNNER_LOG_FILE}
   echo "*** that are resource intensive in the Readout Apps. This is because numad moves" | tee -a ${ITGRUNNER_LOG_FILE}
   echo "*** processes (threads?) to different cores/numa nodes periodically, and that"    | tee -a ${ITGRUNNER_LOG_FILE}
   echo "*** context switch is bad for the stable running of the DAQ processes."           | tee -a ${ITGRUNNER_LOG_FILE}
   echo "********************************************************************************" | tee -a ${ITGRUNNER_LOG_FILE}
fi

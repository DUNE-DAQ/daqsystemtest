# 01-May-2026, KAB: the goal of this test is to check whether configurations that, A) have
# most/all of the components of the system that are needed for TriggerPrimitive generation
# included and B) have all of the configuration parameters that control TPG set to values
# that enable TPG (except for two), run correctly.  The two parameters that are set to values
# that disable TPG are the tp_generation_enabled and ta_generation_enabled flags in the ReadoutApp.
#
# This situation happens in production occasionally (everything enabled for TPG except a couple
# of parameters), and this integtest attempts to verify the correct running of the system in
# situations like that.
#
import pytest
import copy
import os

import integrationtest.data_file_checks as data_file_checks
import integrationtest.log_file_checks as log_file_checks
import integrationtest.data_classes as data_classes
import integrationtest.resource_validation as resource_validation
import integrationtest.utility_functions as utility_functions
from integrationtest.get_pytest_tmpdir import get_pytest_tmpdir
from integrationtest.verbosity_helper import IntegtestVerbosityLevels

import functools
print = functools.partial(print, flush=True)  # always flush print() output

pytest_plugins = "integrationtest.integrationtest_drunc"

# Values that help determine the running conditions
run_duration = 20  # seconds

# Default values for validation parameters
check_for_logfile_errors = True
expected_event_count = run_duration * (1.0 + 3.0) # 1 from RTCM, 3 from FakeHSI
expected_event_count_tolerance = expected_event_count / 10.0

wibeth_frag_params = {
    "fragment_type_description": "WIBEth",
    "fragment_type": "WIBEth",
    "expected_fragment_count": 4,
    "min_size_bytes": 7272,
    "max_size_bytes": 28872,
}
# sizes: 128 is for one TC with zero TAs inside it (72+56)
#        208 is for one TC with one TA inside it (72+56+80)
#        264 is for two TCs with one TA in one of them (72+56+80+56)
triggercandidate_frag_params = {
    "fragment_type_description": "Trigger Candidate",
    "fragment_type": "Trigger_Candidate",
    "expected_fragment_count": 1,
    "min_size_bytes": 128,
    "max_size_bytes": 128,
    "debug_mask": 0x0,
}
triggerprimitive_frag_params = {
    "fragment_type_description": "Trigger Primitive",
    "fragment_type": "Trigger_Primitive",
    "expected_fragment_count": 0,
    "min_size_bytes": 72,
    "max_size_bytes": 168,
}
hsi_frag_params = {
    "fragment_type_description": "HSI",
    "fragment_type": "Hardware_Signal",
    "expected_fragment_count": 1,
    "min_size_bytes": 72,
    "max_size_bytes": 100,
    "frag_sizes_by_TC_type": {"kTiming": {"min_size_bytes": 100, "max_size_bytes": 100},
                              "default": {"min_size_bytes":  72, "max_size_bytes": 100} }
}
ignored_logfile_problems = {
    "-controller": [
    ],
    "local-connection-server": [
        "errorlog: -",
    ],
    # 04-Mar-2026, KAB: added the absl::InitializeLog warning message to the ignored list for
    # all DAQ processes, given that we currently don't have a way suppress it at its source.
    r".*": [
        r"WARNING: All log messages before absl::InitializeLog\(\) is called are written to STDERR"
    ]
}

# Determine if this computer has enough resources for these tests
resource_validator = resource_validation.ResourceValidator()
resource_validator.cpu_count_needs(30, 60)  # 3 for each data source (incl TPG) plus 6 more for everything else
resource_validator.free_memory_needs(15, 24)  # 25% more than what we observe being used ('free -h')
actual_output_path = get_pytest_tmpdir()
resource_validator.free_disk_space_needs(actual_output_path, 1)  # more than what we observe

# The arguments to pass to the config generator, excluding the json
# output directory (the test framework handles that)

common_config_obj = data_classes.integtest_params_for_predefined_dunedaq_config()
common_config_obj.op_env = "test"
common_config_obj.predefined_config_db = (
    os.path.dirname(__file__) + "/../config/daqsystemtest/example-configs.data.xml"
)
common_config_obj.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="TCDataProcessor",     # 12-Nov-2025, KAB: turned off the merging of
        obj_id="def-tc-processor",       # overlapping TCs so that we get more consistent
        updates={                        # numbers of TriggerRecords in the output files.
            "merge_overlapping_tcs": False
        },)
)
common_config_obj.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="ReadoutApplication",
        obj_id="ru-01",
        updates={
            "tp_generation_enabled": 0,
            "ta_generation_enabled": 0,
        },)
)

onebyone_local_conf = copy.deepcopy(common_config_obj)
onebyone_local_conf.config_session_name = "local-1x1-config"

confgen_arguments = {
    "Local 1x1 Conf": onebyone_local_conf,
}

# The commands to run in dunerc, as a list
dunerc_command_list = (
    "boot wait 2 conf start --run-number 101 wait 1 enable-triggers wait ".split()
    + [str(run_duration)]
    + "disable-triggers wait 2 drain-dataflow wait 2 stop-trigger-sources stop scrap terminate".split()
)

# The tests themselves


def test_dunerc_success(run_dunerc, caplog):
    # check for run control success, problems during pytest setup, etc.
    utility_functions.basic_checks(run_dunerc, caplog, print_test_name=True)


def test_log_files(run_dunerc):
    # Check that at least some of the expected log files are present
    assert any(
        f"{run_dunerc.daq_session_name}_df-01" in str(logname)
        for logname in run_dunerc.log_files
    )
    assert any(
        f"{run_dunerc.daq_session_name}_dfo" in str(logname) for logname in run_dunerc.log_files
    )
    assert any(
        f"{run_dunerc.daq_session_name}_mlt" in str(logname) for logname in run_dunerc.log_files
    )
    assert any(
        f"{run_dunerc.daq_session_name}_ru" in str(logname) for logname in run_dunerc.log_files
    )

    if check_for_logfile_errors:
        # Check that there are no warnings or errors in the log files
        assert log_file_checks.logs_are_error_free(
            run_dunerc.log_files, True, True, ignored_logfile_problems,
            verbosity_helper=run_dunerc.verbosity_helper
        )


def test_data_files(run_dunerc):
    expected_file_count = 1

    # Run some tests on the output data file
    assert len(run_dunerc.data_files) == expected_file_count, f"Unexpected file count: Actual: {len(run_dunerc.data_files)}, Expected: {expected_file_count}"

    fragment_check_list = [triggercandidate_frag_params, hsi_frag_params]
    fragment_check_list.append(wibeth_frag_params)
    fragment_check_list.append(triggerprimitive_frag_params)

    all_ok = True
    for idx in range(len(run_dunerc.data_files)):
        data_file = data_file_checks.DataFile(run_dunerc.data_files[idx], run_dunerc.verbosity_helper)
        all_ok &= data_file_checks.sanity_check(data_file)
        all_ok &= data_file_checks.check_file_attributes(data_file)
        all_ok &= data_file_checks.check_event_count(
            data_file, expected_event_count, expected_event_count_tolerance
        )
        for jdx in range(len(fragment_check_list)):
            all_ok &= data_file_checks.check_fragment_count(
                data_file, fragment_check_list[jdx]
            )
            all_ok &= data_file_checks.check_fragment_sizes(
                data_file, fragment_check_list[jdx]
            )

    assert all_ok


def test_cleanup(run_dunerc):
    utility_functions.remove_hdf5_files_if_requested(run_dunerc, this_test_requests_hdf5_file_removal=False)

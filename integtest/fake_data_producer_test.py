import pytest
import os
import copy
import urllib.request
import math

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
# baseline_fragment_size_bytes=72+(464*81) # 81 frames of 464 bytes each with 72-byte Fragment header # ProtoWIB
# baseline_fragment_size_bytes=72+(472*math.ceil(2001/32)) # 63 frames of 472 bytes each with 72-byte Fragment header # DuneWIB
baseline_fragment_size_bytes = 72 + (
    7200 * math.ceil(2001 / 2048)
)  # 1 frame of 7200 bytes with 72-byte Fragment header # WIBEth
baseline_fragment_size_bytes_max = 72 + (
    7200 * (1 + math.ceil(2001 / 2048))
)  # 1 frame of 7200 bytes with 72-byte Fragment header # WIBEth
number_of_data_producers = 2

# Default values for validation parameters
expected_number_of_data_files = 3
check_for_logfile_errors = True
expected_event_count = run_duration
expected_event_count_tolerance = 2

wibeth_frag_params = {
    "fragment_type_description": "WIBEth",
    "fragment_type": "WIBEth",
    "expected_fragment_count": number_of_data_producers,
    "min_size_bytes": baseline_fragment_size_bytes,
    "max_size_bytes": baseline_fragment_size_bytes_max,
}
ignored_logfile_problems = {
    "-controller": [
        "Worker with pid \\d+ was terminated due to signal",
        "Connection '.*' not found on the application registry",
    ],
    "connectivity-service": [
        "errorlog: -",
    ],
}

# Determine if this computer has enough resources for these tests
resource_validator = resource_validation.ResourceValidator()
resource_validator.cpu_count_needs(4, 8)  # 4 for everything
resource_validator.free_memory_needs(4)  # double what we observe being used ('free -h')
actual_output_path = get_pytest_tmpdir()
resource_validator.free_disk_space_needs(actual_output_path, 1)  # more than what we observe

# The next three variable declarations *must* be present as globals in the test
# file. They're read by the "fixtures" in conftest.py to determine how
# to run the config generation and dunerc


conf_dict = data_classes.integtest_params_for_generated_dunedaq_config()
conf_dict.object_databases = ["config/daqsystemtest/integrationtest-objects.data.xml"]
conf_dict.op_env = "integtest"
conf_dict.config_session_name = "fakedata"
conf_dict.use_fakedataprod = True
conf_dict.dro_map_config.n_streams = number_of_data_producers

conf_dict.config_substitutions.append(
    data_classes.attribute_substitution(
     obj_id="random-tc-generator",
     obj_class="RandomTCMakerConf",
        updates={"trigger_rate_hz": 1},
    )
)

doublewindow_conf = copy.deepcopy(conf_dict)

doublewindow_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="RandomTCMakerConf",
        obj_id = "random-tc-generator",
        updates={
            "candidate_backshift_ts": 0,
            "candidate_window_before_ts": 2000,
            "candidate_window_after_ts": 2001,
        },
    )
)

confgen_arguments = {
    "Baseline_Window_Size": conf_dict,
    "Double_Window_Size": doublewindow_conf,
}

# The commands to run in dunerc, as a list
dunerc_command_list = "boot conf".split()
dunerc_command_list += (
    "start --run-number 101 wait 5 enable-triggers wait ".split()
    + [str(run_duration)]
    + "disable-triggers wait 1 drain-dataflow wait 2 stop-trigger-sources wait 1 stop wait 2".split()
)
dunerc_command_list += (
    "start --run-number 102 wait 1 enable-triggers wait ".split()
    + [str(run_duration)]
    + "disable-triggers wait 1 drain-dataflow wait 2 stop-trigger-sources wait 1 stop wait 2".split()
)
dunerc_command_list += (
    "start --run-number 103 wait 1 enable-triggers wait ".split()
    + [str(run_duration)]
    + "disable-triggers wait 1 drain-dataflow wait 2 stop-trigger-sources wait 1 stop wait 2".split()
)
dunerc_command_list += "scrap terminate".split()


# The tests themselves

def test_dunerc_success(run_dunerc, caplog):
    # checks for run control success, problems during pytest setup, etc.
    utility_functions.basic_checks(run_dunerc, caplog, print_test_name=True)


def test_log_files(run_dunerc):
    if check_for_logfile_errors:
        # Check that there are no warnings or errors in the log files
        assert log_file_checks.logs_are_error_free(
            run_dunerc.log_files, True, True, ignored_logfile_problems,
            verbosity_helper=run_dunerc.verbosity_helper
        )


def test_data_files(run_dunerc):
    local_expected_event_count = expected_event_count
    local_event_count_tolerance = expected_event_count_tolerance
    frag_params = wibeth_frag_params
    current_test = os.environ.get("PYTEST_CURRENT_TEST")
    if "Double" in current_test:
        # frag_params["min_size_bytes"]=72+(464*161) # 161 frames of 464 bytes each with 72-byte Fragment header # ProtoWIB
        # frag_params["max_size_bytes"]=72+(464*161)
        # frag_params["min_size_bytes"]=72+(472*math.ceil(4001/32)) # 126 frames of 472 bytes each with 72-byte Fragment header # DuneWIB
        # frag_params["max_size_bytes"]=72+(472*math.ceil(4001/32))
        frag_params["min_size_bytes"] = 72 + (
            7200 * math.ceil(4001 / 2048)
        )  # 2 frames of 7200 bytes each with 72-byte Fragment header # WIBEth
        frag_params["max_size_bytes"] = 72 + (7200 * (1 + math.ceil(4001 / 2048)))
    fragment_check_list = [frag_params]

    # Run some tests on the output data file
    all_ok = len(run_dunerc.data_files) == expected_number_of_data_files
    if all_ok:
        if run_dunerc.verbosity_helper.compare_level(IntegtestVerbosityLevels.drunc_transitions):
            print(f"\n\N{WHITE HEAVY CHECK MARK} The correct number of raw data files was found ({expected_number_of_data_files})")
    else:
        print(f"\n\N{POLICE CARS REVOLVING LIGHT} An incorrect number of raw data files was found, expected {expected_number_of_data_files}, found {len(run_dunerc.data_files)} \N{POLICE CARS REVOLVING LIGHT}")

    for idx in range(len(run_dunerc.data_files)):
        data_file = data_file_checks.DataFile(run_dunerc.data_files[idx], run_dunerc.verbosity_helper)
        all_ok &= data_file_checks.sanity_check(data_file)
        all_ok &= data_file_checks.check_file_attributes(data_file)
        all_ok &= data_file_checks.check_event_count(
            data_file, local_expected_event_count, local_event_count_tolerance
        )
        for jdx in range(len(fragment_check_list)):
            all_ok &= data_file_checks.check_fragment_count(
                data_file, fragment_check_list[jdx]
            )
            all_ok &= data_file_checks.check_fragment_sizes(
                data_file, fragment_check_list[jdx]
            )

    assert all_ok

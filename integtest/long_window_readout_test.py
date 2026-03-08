# The goal of this test is to verify that triggers that have long readout windows are
# handled correctly by the system, including the splitting of the resulting "trigger record"
# into a "sequence" of TriggerRecords.
#
# This test requires a non-trivial amount of disk space to write its raw data files,
# and there are safety checks to verify that sufficient space is available for these files.
# In addition, the raw data files that are produced are removed at the end of the test
# so that they don't fill up the available space.
# *** If you are running on a computer that does not have sufficient space in /tmp, and you would
#     like to instead use a directory on a disk that *does* have sufficient space, you can specify
#     a non-standard pytest output directory using the "--tmpdir <dir_path>" to the
#     dunedaq_integtest_bundle.sh script.  (This test will clean up the large data files that are
#     produced independent of which output directory is used.)
#
import pytest
import os
import re
import copy
import shutil
import psutil

import integrationtest.data_file_checks as data_file_checks
import integrationtest.log_file_checks as log_file_checks
import integrationtest.data_classes as data_classes
import integrationtest.resource_validation as resource_validation
from integrationtest.get_pytest_tmpdir import get_pytest_tmpdir

pytest_plugins = "integrationtest.integrationtest_drunc"

# 20-May-2025, KAB: tweak the print() statement default behavior so that it always flushes the output.
import functools
print = functools.partial(print, flush=True)

# Values that help determine the running conditions
output_path_parameter = "."
number_of_data_producers = 4
run_duration = 40  # seconds
number_of_readout_apps = 3
number_of_dataflow_apps = 1
trigger_rate = 0.05  # Hz
token_count = 1
readout_window_time_before = 100000000  # 1.616 second is the intention for b+a
readout_window_time_after = 1000000
trigger_record_sequence_length = 500000  # intention is 8 msec
tr_queue_size = token_count * (readout_window_time_before + readout_window_time_after) / trigger_record_sequence_length /  number_of_dataflow_apps
latency_buffer_size = 600000

# Default values for validation parameters
expected_number_of_data_files = 4 * number_of_dataflow_apps
check_for_logfile_errors = True
expected_event_count = 202
expected_event_count_tolerance = 9

wibeth_frag_params = {
    "fragment_type_description": "WIBEth",
    "fragment_type": "WIBEth",
    "expected_fragment_count": number_of_data_producers * number_of_readout_apps,
    "min_size_bytes": 1764072,
    "max_size_bytes": 1771272,
}
triggercandidate_frag_params = {
    "fragment_type_description": "Trigger Candidate",
    "fragment_type": "Trigger_Candidate",
    "expected_fragment_count": 1,
    "min_size_bytes": 72,
    "max_size_bytes": 216,
}

ignored_logfile_problems = {
    "-controller": [
        "Worker with pid \\d+ was terminated due to signal 1",
        "Connection '.*' not found on the application registry",
    ],
    "connectivity-service": [
        "errorlog: -",
    ],
}

# Determine if this computer has enough resources for these tests
resource_validator = resource_validation.ResourceValidator()
resource_validator.cpu_count_needs(30, 60)  # 2 for each data source plus 6 more for everything else
resource_validator.free_memory_needs(64, 116)  # 10% more than what we observe being used ('free -h')
resource_validator.total_memory_needs()  # no specific request, but it's useful to see how much is available
actual_output_path = get_pytest_tmpdir()
resource_validator.free_disk_space_needs(actual_output_path, 25)  # 25% more than what we need
resource_validator.total_disk_space_needs(actual_output_path, recommended_total_disk_space=40)  # double what we need
resval_debug_string = resource_validator.get_debug_string()
print(f"{resval_debug_string}")

# The next three variable declarations *must* be present as globals in the test
# file. They're read by the "fixtures" in conftest.py to determine how
# to run the config generation and nanorc

object_databases = ["config/daqsystemtest/integrationtest-objects.data.xml"]

conf_dict = data_classes.drunc_config()
conf_dict.dro_map_config.n_streams = number_of_data_producers
conf_dict.dro_map_config.n_apps = number_of_readout_apps
conf_dict.op_env = "integtest"
conf_dict.config_session_name = "longwindow"
conf_dict.tpg_enabled = False
conf_dict.n_df_apps = number_of_dataflow_apps
conf_dict.fake_hsi_enabled = False

conf_dict.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="LatencyBuffer", updates={"size": latency_buffer_size}
    )
)


conf_dict.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="RandomTCMakerConf",
        updates={"trigger_rate_hz": trigger_rate},
    )
)
conf_dict.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="RandomTCMakerConf",
        obj_id = "random-tc-generator",
        updates={
            "candidate_backshift_ts": 0,
            "candidate_window_before_ts": readout_window_time_before,
            "candidate_window_after_ts": readout_window_time_after,
        },
    )
)
conf_dict.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="DataStoreConf",
        obj_id="default",
        updates={"max_file_size": 4 * 1024 * 1024 * 1024},
    )
)
conf_dict.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="DataStoreConf",
        obj_id="default",
        updates={"directory_path": output_path_parameter},
    )
)

trsplit_conf = copy.deepcopy(conf_dict)
trsplit_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="TRBConf",
        updates={
            "max_sequence_length_ticks": trigger_record_sequence_length,
            "trigger_record_timeout_ms": 1000 / trigger_rate
        },
    )
)

trsplit_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="QueueDescriptor",
        obj_id="trigger-records",
        updates={"capacity": tr_queue_size},
    )
)

confgen_arguments = {  # "No_TR_Splitting": conf_dict,
    "With_TR_Splitting": trsplit_conf,
}

# The commands to run in nanorc, as a list
nanorc_command_list = "boot conf".split()
nanorc_command_list += (
    "start --trigger-rate ".split()
    + [str(trigger_rate)]
    + "--run-number 101 wait 15 enable-triggers wait ".split()
    + [str(run_duration)]
    + "disable-triggers wait 2 drain-dataflow wait 2 stop-trigger-sources stop wait 2".split()
)
nanorc_command_list += (
    "start --trigger-rate ".split()
    + [str(trigger_rate)]
    + "--run-number 102 wait 15 enable-triggers wait ".split()
    + [str(run_duration)]
    + "disable-triggers wait 2 drain-dataflow wait 2 stop-trigger-sources stop wait 2".split()
)
nanorc_command_list += "scrap terminate".split()

# The tests themselves


def test_nanorc_success(run_nanorc):
    # print the name of the current test
    current_test = os.environ.get("PYTEST_CURRENT_TEST")
    match_obj = re.search(r".*\[(.+)-run_.*rc.*\d].*", current_test)
    if match_obj:
        current_test = match_obj.group(1)
    banner_line = re.sub(".", "=", current_test)
    print(banner_line)
    print(current_test)
    print(banner_line)

    # Check that nanorc completed correctly
    assert run_nanorc.completed_process.returncode == 0


def test_log_files(run_nanorc):
    if check_for_logfile_errors:
        # Check that there are no warnings or errors in the log files
        assert log_file_checks.logs_are_error_free(
            run_nanorc.log_files, True, True, ignored_logfile_problems
        )


def test_data_files(run_nanorc):
    local_expected_event_count = expected_event_count
    local_event_count_tolerance = expected_event_count_tolerance
    fragment_check_list = [triggercandidate_frag_params]
    fragment_check_list.append(wibeth_frag_params)  # WIBEth

    all_ok = True
    # Run some tests on the output data file
    all_ok &= len(run_nanorc.data_files) == expected_number_of_data_files
    print("") # Clear potential dot from pytest
    if all_ok:
        print(f"\N{WHITE HEAVY CHECK MARK} The correct number of raw data files was found ({expected_number_of_data_files})")
    else:
        print(f"\N{POLICE CARS REVOLVING LIGHT} An incorrect number of raw data files was found, expected {expected_number_of_data_files}, found {len(run_nanorc.data_files)} \N{POLICE CARS REVOLVING LIGHT}")

    for idx in range(len(run_nanorc.data_files)):
        data_file = data_file_checks.DataFile(run_nanorc.data_files[idx])
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
    assert all_ok, "\N{POLICE CARS REVOLVING LIGHT} One or more data file checks failed! \N{POLICE CARS REVOLVING LIGHT}"


def test_cleanup(run_nanorc):
    pathlist_string = ""
    filelist_string = ""
    for data_file in run_nanorc.data_files:
        filelist_string += " " + str(data_file)
        if str(data_file.parent) not in pathlist_string:
            pathlist_string += " " + str(data_file.parent)

    if pathlist_string and filelist_string:
        print("============================================")
        print("Listing the hdf5 files before deleting them:")
        print("============================================")

        os.system(f"df -h {pathlist_string}")
        print("--------------------")
        os.system(f"ls -alF {filelist_string}")

        for data_file in run_nanorc.data_files:
            data_file.unlink()

        print("--------------------")
        os.system(f"df -h {pathlist_string}")
        print("============================================")

import pytest
import os
import re
import math
import urllib.request

import integrationtest.data_file_checks as data_file_checks
import integrationtest.log_file_checks as log_file_checks
import integrationtest.data_classes as data_classes

pytest_plugins = "integrationtest.integrationtest_drunc"

# Values that help determine the running conditions
number_of_data_producers = 2
number_of_readout_apps = 1
number_of_dataflow_apps = 2
pulser_trigger_rate = 1.0  # Hz
run_duration = 30  # seconds
data_rate_slowdown_factor = 1
output_dir = "."

# Default values for validation parameters
expected_number_of_data_files = 2 * number_of_dataflow_apps
check_for_logfile_errors = True
expected_event_count = run_duration * pulser_trigger_rate / number_of_dataflow_apps
expected_event_count_tolerance = expected_event_count / 10

wibeth_frag_params = {
    "fragment_type_description": "WIBEth",
    "fragment_type": "WIBEth",
    "expected_fragment_count": (number_of_data_producers * number_of_readout_apps),
    "min_size_bytes": 7272,
    "max_size_bytes": 14472,
    "debug_mask": 0x0,
}
wibeth_tpset_params = {
    "fragment_type_description": "TP Stream",
    "fragment_type": "Trigger_Primitive",
    "expected_fragment_count": number_of_readout_apps * 3,
    "frag_counts_by_record_ordinal": {"first": {"min_count": 1, "max_count": number_of_readout_apps * 3},
                                      "default": {"min_count": number_of_readout_apps * 3, "max_count": number_of_readout_apps * 3} },
    "min_size_bytes": 72,
    "max_size_bytes": 300000,
    "debug_mask": 0x0,
    "frag_sizes_by_record_ordinal": {  "first": {"min_size_bytes":    128, "max_size_bytes": 275000},
                                      "second": {"min_size_bytes":    128, "max_size_bytes": 275000},
                                        "last": {"min_size_bytes":    128, "max_size_bytes": 275000},
                                     "default": {"min_size_bytes": 190000, "max_size_bytes": 275000} }
}
triggercandidate_frag_params = {
    "fragment_type_description": "Trigger Candidate",
    "fragment_type": "Trigger_Candidate",
    "expected_fragment_count": 1,
    "min_size_bytes": 128,
    "max_size_bytes": 264,
    "debug_mask": 0x0,
    "frag_sizes_by_TC_type": {"kPrescale": {"min_size_bytes": 208, "max_size_bytes": 264},
                                "kRandom": {"min_size_bytes": 128, "max_size_bytes": 264},
                                "default": {"min_size_bytes": 128, "max_size_bytes": 264} }
}
triggeractivity_frag_params = {
    "fragment_type_description": "Trigger Activity",
    "fragment_type": "Trigger_Activity",
    "expected_fragment_count": 1,
    "min_size_bytes": 72,
    "max_size_bytes": 504,
    "debug_mask": 0x0,
    "frag_sizes_by_TC_type": {"kPrescale": {"min_size_bytes": 216, "max_size_bytes": 504},
                                "kRandom": {"min_size_bytes":  72, "max_size_bytes": 360},
                                "default": {"min_size_bytes":  72, "max_size_bytes": 504} }
}
triggerprimitive_frag_params = {
    "fragment_type_description": "Trigger Primitive",
    "fragment_type": "Trigger_Primitive",
    "expected_fragment_count": number_of_readout_apps * 3,
    "min_size_bytes": 72,
    "max_size_bytes": 184,
}
hsi_frag_params = {
    "fragment_type_description": "HSI",
    "fragment_type": "Hardware_Signal",
    "expected_fragment_count": 0,
    "min_size_bytes": 72,
    "max_size_bytes": 100,
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

object_databases = ["config/daqsystemtest/integrationtest-objects.data.xml"]

conf_dict = data_classes.drunc_config()
conf_dict.dro_map_config.n_streams = number_of_data_producers
conf_dict.dro_map_config.n_apps = number_of_readout_apps
conf_dict.op_env = "integtest"
conf_dict.session = "tpstream"
conf_dict.tpg_enabled = True
conf_dict.n_df_apps = number_of_dataflow_apps
conf_dict.frame_file = (
    "asset://?checksum=dd156b4895f1b06a06b6ff38e37bd798"  # WIBEth All Zeros
)

conf_dict.config_substitutions.append(
    data_classes.config_substitution(
        obj_id=conf_dict.session,
        obj_class="Session",
        updates={"data_rate_slowdown_factor": data_rate_slowdown_factor},
    )
)
conf_dict.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="RandomTCMakerConf",
        updates={"trigger_rate_hz": pulser_trigger_rate},
    )
)
conf_dict.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="LatencyBuffer", updates={"size": 200000}
    )
)
conf_dict.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="TAMakerPrescaleAlgorithm",
        obj_id="dummy-ta-maker",
        updates={"prescale": 25},
    )
)
conf_dict.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="TCDataProcessor",
        obj_id="def-tc-processor",
        updates={"merge_overlapping_tcs": 0},
    )
)
conf_dict.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="DataStoreConf",
        obj_id="default",
        updates={"directory_path": output_dir},
    )
)
conf_dict.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="DataStoreConf",
        obj_id="default_tp_store_conf",
        updates={"directory_path": output_dir},
    )
)

confgen_arguments = {"Software_TPG_System": conf_dict}

# The commands to run in nanorc, as a list
nanorc_command_list = (
    "boot conf wait 5".split()
    + "start --run-number 101 wait 1 enable-triggers wait ".split()
    + [str(run_duration)]
    + "disable-triggers wait 2 drain-dataflow wait 2 stop-trigger-sources stop ".split()
    + "start --run-number 102 wait 1 enable-triggers wait ".split()
    + [str(run_duration)]
    + "disable-triggers wait 2 drain-dataflow wait 2 stop-trigger-sources stop ".split()
    + " scrap terminate".split()
)

# The tests themselves


def test_nanorc_success(run_nanorc):
    current_test = os.environ.get("PYTEST_CURRENT_TEST")
    match_obj = re.search(r".*\[(.+)\].*", current_test)
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
    low_number_of_files = expected_number_of_data_files
    high_number_of_files = expected_number_of_data_files
    fragment_check_list = [triggercandidate_frag_params, hsi_frag_params]
    local_expected_event_count += (
        250
        * number_of_data_producers
        * number_of_readout_apps
        * run_duration
        / (100 * number_of_dataflow_apps)
    )
    local_event_count_tolerance += (
        10
        * number_of_data_producers
        * number_of_readout_apps
        * run_duration
        / (100 * number_of_dataflow_apps)
    )
    fragment_check_list.append(wibeth_frag_params)
    fragment_check_list.append(triggerprimitive_frag_params)
    fragment_check_list.append(triggeractivity_frag_params)

    # Run some tests on the output data file
    assert (
        len(run_nanorc.data_files) == high_number_of_files
        or len(run_nanorc.data_files) == low_number_of_files
    )

    for idx in range(len(run_nanorc.data_files)):
        data_file = data_file_checks.DataFile(run_nanorc.data_files[idx])
        assert data_file_checks.sanity_check(data_file)
        assert data_file_checks.check_file_attributes(data_file)
        assert data_file_checks.check_event_count(
            data_file, local_expected_event_count, local_event_count_tolerance
        )
        for jdx in range(len(fragment_check_list)):
            assert data_file_checks.check_fragment_count(
                data_file, fragment_check_list[jdx]
            )
            assert data_file_checks.check_fragment_sizes(
                data_file, fragment_check_list[jdx]
            )


def test_tpstream_files(run_nanorc):
    tpstream_files = run_nanorc.tpset_files
    local_expected_event_count = (
        run_duration + 8
    )  # TPStreamWriterModule is currently configured to write at 1 Hz, addl TimeSlices expected because of wait times in drunc command list
    local_event_count_tolerance = local_expected_event_count / 10
    fragment_check_list = [wibeth_tpset_params]  # WIBEth

    assert len(tpstream_files) == 2  # one for each run

    for idx in range(len(tpstream_files)):
        data_file = data_file_checks.DataFile(tpstream_files[idx])
        # assert data_file_checks.sanity_check(data_file) # Sanity check doesn't work for stream files
        assert data_file_checks.check_file_attributes(data_file)
        assert data_file_checks.check_event_count(
            data_file, local_expected_event_count, local_event_count_tolerance
        )
        for jdx in range(len(fragment_check_list)):
            assert data_file_checks.check_fragment_count(
                data_file, fragment_check_list[jdx]
            )
            assert data_file_checks.check_fragment_sizes(
                data_file, fragment_check_list[jdx]
            )

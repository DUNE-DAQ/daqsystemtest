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
wib1_frag_hsi_trig_params = {
    "fragment_type_description": "WIB",
    "fragment_type": "ProtoWIB",
    "hdf5_source_subsystem": "Detector_Readout",
    "expected_fragment_count": (number_of_data_producers * number_of_readout_apps),
    "min_size_bytes": 37192,
    "max_size_bytes": 37192,
}
wib1_frag_multi_trig_params = {
    "fragment_type_description": "WIB",
    "fragment_type": "ProtoWIB",
    "hdf5_source_subsystem": "Detector_Readout",
    "expected_fragment_count": (number_of_data_producers * number_of_readout_apps),
    "min_size_bytes": 72,
    "max_size_bytes": 54000,
}
wib1_tpset_params = {
    "fragment_type_description": "TP Stream",
    "fragment_type": "Trigger_Primitive",
    "hdf5_source_subsystem": "Trigger",
    "expected_fragment_count": (number_of_data_producers * number_of_readout_apps),
    "min_size_bytes": 72,
    "max_size_bytes": 3291080,
}
wib2_frag_hsi_trig_params = {
    "fragment_type_description": "WIB",
    "fragment_type": "WIB",
    "hdf5_source_subsystem": "Detector_Readout",
    "expected_fragment_count": (number_of_data_producers * number_of_readout_apps),
    "min_size_bytes": 29808,
    "max_size_bytes": 30280,
}
wib2_frag_multi_trig_params = {
    "fragment_type_description": "WIB",
    "fragment_type": "WIB",
    "hdf5_source_subsystem": "Detector_Readout",
    "expected_fragment_count": (number_of_data_producers * number_of_readout_apps),
    "min_size_bytes": 72,
    "max_size_bytes": 54000,
}
wib2_tpset_params = {
    "fragment_type_description": "TP Stream",
    "fragment_type": "Trigger_Primitive",
    "hdf5_source_subsystem": "Trigger",
    "expected_fragment_count": (number_of_data_producers * number_of_readout_apps),
    "min_size_bytes": 72,
    "max_size_bytes": 3291080,
}
wibeth_frag_hsi_trig_params = {
    "fragment_type_description": "WIBEth",
    "fragment_type": "WIBEth",
    "hdf5_source_subsystem": "Detector_Readout",
    "expected_fragment_count": (number_of_data_producers * number_of_readout_apps),
    "min_size_bytes": 7272,
    "max_size_bytes": 14472,
}
wibeth_frag_multi_trig_params = {
    "fragment_type_description": "WIBEth",
    "fragment_type": "WIBEth",
    "hdf5_source_subsystem": "Detector_Readout",
    "expected_fragment_count": (number_of_data_producers * number_of_readout_apps),
    "min_size_bytes": 72,
    "max_size_bytes": 14472,
}
wibeth_tpset_params = {
    "fragment_type_description": "TP Stream",
    "fragment_type": "Trigger_Primitive",
    "hdf5_source_subsystem": "Trigger",
    "expected_fragment_count": number_of_readout_apps,
    "min_size_bytes": 72,
    "max_size_bytes": 3291080,
}
triggercandidate_frag_params = {
    "fragment_type_description": "Trigger Candidate",
    "fragment_type": "Trigger_Candidate",
    "hdf5_source_subsystem": "Trigger",
    "expected_fragment_count": 1,
    "min_size_bytes": 72,
    "max_size_bytes": 280,
}
triggeractivity_frag_params = {
    "fragment_type_description": "Trigger Activity",
    "fragment_type": "Trigger_Activity",
    "hdf5_source_subsystem": "Trigger",
    "expected_fragment_count": number_of_readout_apps,
    "min_size_bytes": 72,
    "max_size_bytes": 216,
}
triggertp_frag_params = {
    "fragment_type_description": "Trigger with TPs",
    "fragment_type": "Trigger_Primitive",
    "hdf5_source_subsystem": "Trigger",
    "expected_fragment_count": (number_of_data_producers * number_of_readout_apps),
    "min_size_bytes": 72,
    "max_size_bytes": 16000,
}
hsi_frag_params = {
    "fragment_type_description": "HSI",
    "fragment_type": "Hardware_Signal",
    "hdf5_source_subsystem": "HW_Signals_Interface",
    "expected_fragment_count": 0,
    "min_size_bytes": 72,
    "max_size_bytes": 100,
}
ignored_logfile_problems = {
    "rulocalhost": [
        'Encountered new error, name="MISSING_FRAMES"',
        'Encountered new error, name="SEQUENCE_ID_JUMP"',
    ],
    "-controller": [
        "Propagating take_control to children",
        "There is no broadcasting service",
        "Could not understand the BroadcastHandler technology you want to use",
        "Worker with pid \\d+ was terminated due to signal 1",
    ],
    "local-connection-server": [
        "errorlog: -",
        "Worker with pid \\d+ was terminated due to signal 1",
    ],
    "log_.*_tpstream_": ["connect: Connection refused"],
}

object_databases = ["config/daqsystemtest/integrationtest-objects.data.xml"]

conf_dict = data_classes.drunc_config()
conf_dict.dro_map_config.n_streams = number_of_data_producers
conf_dict.dro_map_config.n_apps = number_of_readout_apps
conf_dict.op_env = "integtest"
conf_dict.session = "tpstream"
conf_dict.tpg_enabled = True
conf_dict.n_df_apps = number_of_dataflow_apps

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
        updates={"trigger_interval_ticks": 62500000 / pulser_trigger_rate},
    )
)
conf_dict.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="LatencyBuffer", updates={"size": 200000}
    )
)

confgen_arguments = {"Software_TPG_System": conf_dict}

# The commands to run in nanorc, as a list
nanorc_command_list = (
    "boot conf ".split()
    + "start 101 wait 1 enable-triggers wait ".split()
    + [str(run_duration)]
    + "disable-triggers wait 2 drain-dataflow wait 2 stop-trigger-sources stop ".split()
    + "start 102 wait 1 enable-triggers wait ".split()
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
    if run_nanorc.confgen_config.tpg_enabled:
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
        # fragment_check_list.append(wib1_frag_multi_trig_params) # ProtoWIB
        # fragment_check_list.append(wib2_frag_multi_trig_params) # DuneWIB
        fragment_check_list.append(wibeth_frag_multi_trig_params)  # WIBEth
        fragment_check_list.append(triggertp_frag_params)
        fragment_check_list.append(triggeractivity_frag_params)
    else:
        low_number_of_files -= number_of_dataflow_apps
        if low_number_of_files < 1:
            low_number_of_files = 1
        # fragment_check_list.append(wib1_frag_hsi_trig_params) # ProtoWIB
        # fragment_check_list.append(wib2_frag_hsi_trig_params) # DuneWIB
        fragment_check_list.append(wibeth_frag_hsi_trig_params)  # WIBEth

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
        run_duration + 2
    )  # TPStreamWriterModule is currently configured to write at 1 Hz
    local_event_count_tolerance = local_expected_event_count / 10
    # fragment_check_list=[wib1_tpset_params] # ProtoWIB
    # fragment_check_list=[wib2_tpset_params] # DuneWIB
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

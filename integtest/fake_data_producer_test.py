import pytest
import os
import re
import copy
import urllib.request
import math

import integrationtest.data_file_checks as data_file_checks
import integrationtest.log_file_checks as log_file_checks
import integrationtest.data_classes as data_classes

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
data_rate_slowdown_factor = 10
number_of_data_producers = 2

# Default values for validation parameters
expected_number_of_data_files = 3
check_for_logfile_errors = True
expected_event_count = run_duration
expected_event_count_tolerance = 2
wib1_frag_hsi_trig_params = {
    "fragment_type_description": "WIB",
    "fragment_type": "ProtoWIB",
    "hdf5_source_subsystem": "Detector_Readout",
    "expected_fragment_count": number_of_data_producers,
    "min_size_bytes": baseline_fragment_size_bytes,
    "max_size_bytes": baseline_fragment_size_bytes_max,
}
wib2_frag_params = {
    "fragment_type_description": "WIB2",
    "fragment_type": "WIB",
    "hdf5_source_subsystem": "Detector_Readout",
    "expected_fragment_count": number_of_data_producers,
    "min_size_bytes": baseline_fragment_size_bytes,
    "max_size_bytes": baseline_fragment_size_bytes_max,
}
wibeth_frag_params = {
    "fragment_type_description": "WIBEth",
    "fragment_type": "WIBEth",
    "hdf5_source_subsystem": "Detector_Readout",
    "expected_fragment_count": number_of_data_producers,
    "min_size_bytes": baseline_fragment_size_bytes,
    "max_size_bytes": baseline_fragment_size_bytes_max,
}
hsi_frag_params = {
    "fragment_type_description": "HSI",
    "fragment_type": "Hardware_Signal",
    "hdf5_source_subsystem": "HW_Signals_Interface",
    "expected_fragment_count": 1,
    "min_size_bytes": 72,
    "max_size_bytes": 100,
}
ignored_logfile_problems = {}

# The next three variable declarations *must* be present as globals in the test
# file. They're read by the "fixtures" in conftest.py to determine how
# to run the config generation and nanorc

object_databases = ["config/daqsystemtest/integrationtest-objects.data.xml"]


conf_dict = data_classes.drunc_config()

# conf_dict["daq_common"]["data_rate_slowdown_factor"] = data_rate_slowdown_factor
# conf_dict["readout"]["use_fake_data_producers"] = True
# conf_dict["readout"]["clock_speed_hz"] = 50000000 # ProtoWIB
# conf_dict["detector"]["clock_speed_hz"] = 62500000 # DuneWIB/WIBEth
# ttcm_conf = [{'signal': 1, 'tc_type_name': 'kTiming', 'time_before': 1000, 'time_after': 1001}]
# conf_dict["trigger"]["ttcm_input_map"] = ttcm_conf
# conf_dict["hsi"]["use_hsi"] = True
# conf_dict["trigger"]["segment_config"] = "INTEGTEST_CONFDIR/trigger-segment-fakehsi.data.xml"

# doublewindow_conf = copy.deepcopy(conf_dict)
# ttcm_conf2 = [{'signal': 1, 'tc_type_name': 'kTiming', 'time_before': 2000, 'time_after': 2001}]
# doublewindow_conf["trigger"]["ttcm_input_map"] = ttcm_conf2

confgen_arguments = {
    "Baseline_Window_Size": conf_dict,
    # "Double_Window_Size": doublewindow_conf,
}
# The commands to run in nanorc, as a list
# (the first run [#100] is included to warm up the DAQ processes and avoid warnings and errors caused by
# startup sluggishness seen on slower test computers)
# nanorc_command_list="boot conf".split()
# nanorc_command_list+="start_run          101 wait ".split() + [str(run_duration)] + "stop_run --wait 2 wait 2".split()
# nanorc_command_list+="start_run --wait 1 102 wait ".split() + [str(run_duration)] + "stop_run          wait 2".split()
# nanorc_command_list+="start_run --wait 2 103 wait ".split() + [str(run_duration)] + "stop_run --wait 1 wait 2".split()
# nanorc_command_list+="scrap terminate".split()
nanorc_command_list = ["boot", "terminate"]
# Don't require the --frame-file option since we don't need it
frame_file_required = False

# The tests themselves


def test_nanorc_success(run_nanorc):
    pytest.skip("FakeDataApplication is not currently implemented.")
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
    pytest.skip("FakeDataApplication is not currently implemented.")
    local_check_flag = check_for_logfile_errors

    if local_check_flag:
        # Check that there are no warnings or errors in the log files
        assert log_file_checks.logs_are_error_free(
            run_nanorc.log_files, True, True, ignored_logfile_problems
        )


def test_data_files(run_nanorc):
    pytest.skip("FakeDataApplication is not currently implemented.")
    local_expected_event_count = expected_event_count
    local_event_count_tolerance = expected_event_count_tolerance
    # frag_params=wib1_frag_hsi_trig_params # ProtoWIB
    # frag_params=wib2_frag_params # DuneWIB
    frag_params = wibeth_frag_params
    if run_nanorc.confgen_config["trigger"]["ttcm_input_map"][0]["time_before"] == 2000:
        # frag_params["min_size_bytes"]=72+(464*161) # 161 frames of 464 bytes each with 72-byte Fragment header # ProtoWIB
        # frag_params["max_size_bytes"]=72+(464*161)
        # frag_params["min_size_bytes"]=72+(472*math.ceil(4001/32)) # 126 frames of 472 bytes each with 72-byte Fragment header # DuneWIB
        # frag_params["max_size_bytes"]=72+(472*math.ceil(4001/32))
        frag_params["min_size_bytes"] = 72 + (
            7200 * math.ceil(4001 / 2048)
        )  # 2 frames of 7200 bytes each with 72-byte Fragment header # WIBEth
        frag_params["max_size_bytes"] = 72 + (7200 * (1 + math.ceil(4001 / 2048)))
    fragment_check_list = [frag_params, hsi_frag_params]

    # Run some tests on the output data file
    assert len(run_nanorc.data_files) == expected_number_of_data_files

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

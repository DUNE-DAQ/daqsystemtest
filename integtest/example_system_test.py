import pytest
import os
import copy

import integrationtest.data_file_checks as data_file_checks
import integrationtest.log_file_checks as log_file_checks
import integrationtest.data_classes as data_classes

pytest_plugins = "integrationtest.integrationtest_drunc"

# Values that help determine the running conditions
run_duration = 20  # seconds

# Default values for validation parameters
check_for_logfile_errors = True
hostname = os.uname().nodename

wibeth_frag_params = {
    "fragment_type_description": "WIBEth",
    "fragment_type": "WIBEth",
    "hdf5_source_subsystem": "Detector_Readout",
    "expected_fragment_count": 0,
    "min_size_bytes": 7272,
    "max_size_bytes": 289440,
}
triggercandidate_frag_params = {
    "fragment_type_description": "Trigger Candidate",
    "fragment_type": "Trigger_Candidate",
    "hdf5_source_subsystem": "Trigger",
    "expected_fragment_count": 1,
    "min_size_bytes": 72,
    "max_size_bytes": 216,
}
triggertp_frag_params = {
    "fragment_type_description": "Trigger with TPs",
    "fragment_type": "Trigger_Primitive",
    "hdf5_source_subsystem": "Trigger",
    "expected_fragment_count": 0,
    "min_size_bytes": 72,
    "max_size_bytes": 16000,
}
hsi_frag_params = {
    "fragment_type_description": "HSI",
    "fragment_type": "Hardware_Signal",
    "hdf5_source_subsystem": "HW_Signals_Interface",
    "expected_fragment_count": 1,
    "min_size_bytes": 72,
    "max_size_bytes": 100,
}
ignored_logfile_problems = {
    "-controller": [
        'ERROR    "Broadcast": Propagating take_control to children',
        'WARNING  "Broadcast": There is no broadcasting service!',
        "Worker with pid \\d+ was terminated due to signal",
        'WARNING  "BroadcastHandler": Could not understand the BroadcastHandler technology you want to use',
    ],
    "local-connection-server": [
        "errorlog: -",
        "Worker with pid \\d+ was terminated due to signal",
    ],
    "log_.*": ["connect: Connection refused"],
}

# The arguments to pass to the config generator, excluding the json
# output directory (the test framework handles that)

common_config_obj = data_classes.drunc_config()
common_config_obj.attempt_cleanup = True
common_config_obj.op_env = "test"
common_config_obj.config_db = (
    os.path.dirname(__file__) + "/../config/daqsystemtest/example-configs.data.xml"
)

onebyone_local_conf = copy.deepcopy(common_config_obj)
onebyone_local_conf.session = "local-1x1-config"

twobythree_local_conf = copy.deepcopy(common_config_obj)
twobythree_local_conf.session = "local-2x3-config"

onebyone_ehn1_conf = copy.deepcopy(common_config_obj)
onebyone_ehn1_conf.session = "ehn1-local-1x1-config"

twobythree_ehn1_conf = copy.deepcopy(common_config_obj)
twobythree_ehn1_conf.session = "ehn1-local-2x3-config"

confgen_arguments = {
        "Local 1x1 Conf": onebyone_local_conf,
        "Local 2x3 Conf": twobythree_local_conf,
}

if "cern.ch" in hostname:
    confgen_arguments["EHN1 1x1 Conf"] = onebyone_ehn1_conf
    confgen_arguments["EHN1 2x3 Conf"] = twobythree_ehn1_conf

# The commands to run in nanorc, as a list
nanorc_command_list = (
    "boot wait 5 conf start 101 wait 1 enable-triggers wait ".split()
    + [str(run_duration)]
    + "disable-triggers wait 2 drain-dataflow wait 2 stop-trigger-sources stop scrap terminate".split()
)

# The tests themselves


def test_nanorc_success(run_nanorc):
    current_test = os.environ.get("PYTEST_CURRENT_TEST")

    if "cern.ch" not in hostname and "EHN1" in current_test:
        pytest.skip(
            f"This computer ({hostname}) is not at CERN, not running EHN1 sessions"
        )

    # Check that nanorc completed correctly
    assert run_nanorc.completed_process.returncode == 0


def test_log_files(run_nanorc):
    current_test = os.environ.get("PYTEST_CURRENT_TEST")

    if "cern.ch" not in hostname and "EHN1" in current_test:
        pytest.skip(
            f"This computer ({hostname}) is not at CERN, not running EHN1 sessions"
        )

    # Check that at least some of the expected log files are present
    assert any(
        f"{run_nanorc.session}_df-01" in str(logname)
        for logname in run_nanorc.log_files
    )
    assert any(
        f"{run_nanorc.session}_dfo" in str(logname) for logname in run_nanorc.log_files
    )
    assert any(
        f"{run_nanorc.session}_mlt" in str(logname) for logname in run_nanorc.log_files
    )
    assert any(
        f"{run_nanorc.session}_ru" in str(logname) for logname in run_nanorc.log_files
    )

    if check_for_logfile_errors:
        # Check that there are no warnings or errors in the log files
        assert log_file_checks.logs_are_error_free(
            run_nanorc.log_files, True, True, ignored_logfile_problems
        )


def test_data_files(run_nanorc):
    current_test = os.environ.get("PYTEST_CURRENT_TEST")

    if "cern.ch" not in hostname and "EHN1" in current_test:
        pytest.skip(
            f"This computer ({hostname}) is not at CERN, not running EHN1 sessions"
        )

    datafile_params = {
        "Local 1x1 Conf": {"readout_apps": 1, "expected_file_count": 1},
        "Local 2x3 Conf": {"readout_apps": 2, "expected_file_count": 3},
        "EHN1 1x1 Conf": {"readout_apps": 1, "expected_file_count": 1},
        "EHN1 2x3 Conf": {"readout_apps": 2, "expected_file_count": 3},
    }
    current_params = None
    for key in datafile_params.keys():
        if key in current_test:
            current_params = datafile_params[key]

    # Run some tests on the output data file
    assert len(run_nanorc.data_files) == current_params["expected_file_count"]

    local_expected_fragment_count = 4 * current_params["readout_apps"]
    wibeth_frag_params["expected_fragment_count"] = local_expected_fragment_count
    triggertp_frag_params["expected_fragment_count"] = 3 * current_params["readout_apps"]

    # Taking event count check out for now. Calculated event count is consistently 2x actual
    #randomTCMaker_events = run_duration * 0.5
    #hsi_events = run_duration * 3
    #ta_prescale = 1000
    #tpg_events = (6250 / ta_prescale) * local_expected_fragment_count * run_duration / 100

    #expected_event_count = (randomTCMaker_events + hsi_events + tpg_events) // current_params["expected_file_count"]
    #expected_event_count_tolerance = expected_event_count // 8.0
    fragment_check_list = [triggercandidate_frag_params, hsi_frag_params,wibeth_frag_params,triggertp_frag_params]

    all_ok = True
    for idx in range(len(run_nanorc.data_files)):
        data_file = data_file_checks.DataFile(run_nanorc.data_files[idx])
        all_ok &= data_file_checks.sanity_check(data_file)
        all_ok &= data_file_checks.check_file_attributes(data_file)
        #all_ok &= data_file_checks.check_event_count(
        #    data_file, expected_event_count, expected_event_count_tolerance
        #)
        for jdx in range(len(fragment_check_list)):
            all_ok &= data_file_checks.check_fragment_count(
                data_file, fragment_check_list[jdx]
            )
            all_ok &= data_file_checks.check_fragment_sizes(
                data_file, fragment_check_list[jdx]
            )

    assert all_ok, "One or more data file checks failed!"

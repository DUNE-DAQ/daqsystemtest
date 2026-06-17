import pytest
import urllib.request

import integrationtest.data_file_checks as data_file_checks
import integrationtest.log_file_checks as log_file_checks
import integrationtest.data_classes as data_classes
import integrationtest.resource_validation as resource_validation
import integrationtest.opmon_metric_checks as opmon_metric_checks
import integrationtest.utility_functions as utility_functions
from integrationtest.get_pytest_tmpdir import get_pytest_tmpdir
from integrationtest.verbosity_helper import IntegtestVerbosityLevels

import functools
print = functools.partial(print, flush=True)  # always flush print() output

pytest_plugins = "integrationtest.integrationtest_drunc"

# Values that help determine the running conditions
number_of_data_producers = 2
run_duration = 20  # seconds
readout_window_time_before = 1000
readout_window_time_after = 1001

# Default values for validation parameters
expected_number_of_data_files = 1
check_for_logfile_errors = True
expected_event_count = run_duration
expected_event_count_tolerance = 2
wibeth_frag_params = {
    "fragment_type_description": "WIBEth",
    "fragment_type": "WIBEth",
    "expected_fragment_count": number_of_data_producers,
    "min_size_bytes": 7272,
    "max_size_bytes": 14472,
}
triggercandidate_frag_params = {
    "fragment_type_description": "Trigger Candidate",
    "fragment_type": "Trigger_Candidate",
    "expected_fragment_count": 1,
    "min_size_bytes": 128,
    "max_size_bytes": 216,
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
        "Worker with pid \\d+ was terminated due to signal",
        "Connection '.*' not found on the application registry",
    ],
    "connectivity-service": [
        "errorlog: -",
    ],
}

# Determine if this computer has enough resources for these tests
resource_validator = resource_validation.ResourceValidator()
resource_validator.cpu_count_needs(6, 12)  # 2 for each data source plus 2 more for everything else
resource_validator.free_memory_needs(5, 8)  # 25% more than what we observe being used ('free -h')
actual_output_path = get_pytest_tmpdir()
resource_validator.free_disk_space_needs(actual_output_path, 1)  # more than what we observe

# The next three variable declarations *must* be present as globals in the test
# file. They're read by the "fixtures" in conftest.py to determine how
# to run the config generation and dunerc

# The arguments to pass to the config generator, excluding the json
# output directory (the test framework handles that)

conf_dict = data_classes.integtest_params_for_generated_dunedaq_config()
conf_dict.object_databases = ["config/daqsystemtest/integrationtest-objects.data.xml"]
conf_dict.dro_map_config.n_streams = number_of_data_producers
conf_dict.op_env = "integtest"
conf_dict.config_session_name = "minimal"
conf_dict.tpg_enabled = False

# For testing, allow drunc to manage ConnectivityService
#conf_dict.connsvc_control = ConnSvcControl.RUNCONTROL
# For testing, specify connectivity service port (default is 0, a random port is chosen for the Connectivity Service)
#conf_dict.connsvc_port = 12345

substitution = data_classes.attribute_substitution(
    obj_id="random-tc-generator",
    obj_class="RandomTCMakerConf",
    updates={"trigger_rate_hz": 1},
)
conf_dict.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="TCReadoutMap",
        obj_id = "def-random-readout",
        updates={
            "time_before": readout_window_time_before,
            "time_after": readout_window_time_after,
        },
    )
)
conf_dict.config_substitutions.append(substitution)


confgen_arguments = {"MinimalSystem": conf_dict}
# The commands to run in dunerc, as a list
dunerc_command_list = (
    "boot conf start --run-number 101 wait 1 enable-triggers wait ".split()
    + [str(run_duration)]
    + "disable-triggers wait 2 drain-dataflow wait 2 stop-trigger-sources stop scrap terminate".split()
)

# The tests themselves


def test_dunerc_success(run_dunerc, caplog):
    # checks for run control success, problems during pytest setup, etc.
    utility_functions.basic_checks(run_dunerc, caplog, print_test_name=False)


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
    # Run some tests on the output data file
    all_ok = len(run_dunerc.data_files) == expected_number_of_data_files
    if all_ok:
        if run_dunerc.verbosity_helper.compare_level(IntegtestVerbosityLevels.drunc_transitions):
            print(f"\n\N{WHITE HEAVY CHECK MARK} The correct number of raw data files was found ({expected_number_of_data_files})")
    else:
        print(f"\n\N{POLICE CARS REVOLVING LIGHT} An incorrect number of raw data files was found, expected {expected_number_of_data_files}, found {len(run_dunerc.data_files)} \N{POLICE CARS REVOLVING LIGHT}")

    fragment_check_list = [triggercandidate_frag_params, hsi_frag_params]
    fragment_check_list.append(wibeth_frag_params)
    nontrig_fragment_check_list = [hsi_frag_params, wibeth_frag_params]

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
        for kdx in range(len(nontrig_fragment_check_list)):
            all_ok &= data_file_checks.check_fragment_error_flags( data_file, nontrig_fragment_check_list[kdx])

    assert all_ok


# 26-Nov-2025, KAB: added some sample opmon metric checks, for demonstration purposes
def test_metric_files(run_dunerc):
    if run_dunerc.verbosity_helper.compare_level(IntegtestVerbosityLevels.drunc_transitions):
        print("") # Clear potential dot from pytest

    # 10-Dec-2025, KAB: we have noticed that sometimes drunc transitions (or other parts of
    # a run control session) take a little longer than expected.  This can cause extra metric
    # samples to be created.  This section of code takes that into account by increasing
    # the max allowed sample count by the amount of extra time taken, divided by 10
    # (metric samples are produced every 10 seconds, by default).
    # I've tried to make this code backward compatible by handling cases in which the
    # daq_session_overall_time is not available (e.g. the try/catch).
    #
    # The expected DAQ session time is the sum of the time spent in the "running" state
    # (specified in the run control commands above [run_duration]) plus the "wait" times in
    # the RC commands plus the time spent in RC transitions.  With a run duration of 20 sec,
    # the session time has been measured to be ~40 seconds, so we take the extra 20 seconds
    # into account.
    expected_daq_session_time = run_duration + 20
    #
    # To calculate the expected number of metric samples, we subtract a small-ish amount of
    # time that the DAQ session spends in state(s) that don't produce metrics (say 3 seconds)
    # and divide by 10, where 10 seconds is the interval between each reporting of metrics.
    expected_metric_sample_count = int((expected_daq_session_time - 3) / 10)
    #
    # We'll set the maximum allowed sample count slightly higher than the expected value.
    max_metric_sample_count = expected_metric_sample_count + 2
    try:
        #print(f"\nDAQ session overall time: {run_dunerc.daq_session_overall_time} seconds")
        if run_dunerc.daq_session_overall_time is not None:
            extra_time_taken = run_dunerc.daq_session_overall_time - expected_daq_session_time
            if extra_time_taken > 10:
                extra_sample_count_allowance = int(extra_time_taken / 10)
                max_metric_sample_count += extra_sample_count_allowance
    except AttributeError:
        pass

    metric_data = opmon_metric_checks.collate_opmon_data_from_files(run_dunerc.opmon_files)

    metric_key_list = [run_dunerc.daq_session_name, "df-01", "df-01-trb", "dfmodules.TRBInfo", "generated_trigger_records"]
    all_ok = True
    # a 20-second run will likely result in 3 metric samples (at 10-second intervals), so a range
    # of 1..5 should always succeed
    all_ok &= opmon_metric_checks.check_metric_sample_count(metric_data, metric_key_list, min_count=1,
                                                            max_count=max_metric_sample_count,
                                                            verbosity_helper=run_dunerc.verbosity_helper)
    # the number of triggers expected in this test is based on the run duration, so we check for
    # a reported number of generated trigger records between slightly above/below that
    all_ok &= opmon_metric_checks.check_metric_value_sum(metric_data, metric_key_list,
                                                         min_value_sum=run_duration-3,
                                                         max_value_sum=run_duration+3,
                                                         verbosity_helper=run_dunerc.verbosity_helper)

    assert all_ok

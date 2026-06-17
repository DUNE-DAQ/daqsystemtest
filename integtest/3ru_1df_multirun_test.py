import pytest
import copy
import math
import urllib.request

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
number_of_data_producers = 3
number_of_readout_apps = 3
run_duration = 20  # seconds
trigger_rate = 1  # Hz
ta_prescale = 100

# Default values for validation parameters
expected_number_of_data_files = 3
check_for_logfile_errors = True
expected_event_count = trigger_rate * run_duration
expected_event_count_tolerance = math.ceil(expected_event_count / 10)

wibeth_frag_params = {
    "fragment_type_description": "WIBEth",
    "fragment_type": "WIBEth",
    "expected_fragment_count": (number_of_data_producers * number_of_readout_apps),
    "min_size_bytes": 7272,
    "max_size_bytes": 14472,
}
# sizes: 128 is for one TC with zero TAs inside it (72+56)
#        208 is for one TC with one TA inside it (72+56+80)
#        264 is for two TCs with one TA in one of them (72+56+80+56)
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
# sizes:  72 is for an empty TA fragment
#        184 is for one TA with one TP inside it (72+88+24)
#        296 is for two TAs with one TP in each of them (72+88+24+88+24)
#        408 is for three TAs with one TP in each of them (72+88+24+88+24+88+24)
triggeractivity_frag_params = {
    "fragment_type_description": "Trigger Activity",
    "fragment_type": "Trigger_Activity",
    "expected_fragment_count": 1,
    "min_size_bytes": 72,
    "max_size_bytes": 408,
    "debug_mask": 0x0,
    "frag_sizes_by_TC_type": {"kPrescale": {"min_size_bytes": 184, "max_size_bytes": 408},
                                "kRandom": {"min_size_bytes":  72, "max_size_bytes": 296},
                                "default": {"min_size_bytes":  72, "max_size_bytes": 408} }
}
# sizes:  72 is for an empty TP fragment
#        144 is for a fragment with three TPs in it (72+24+24+24)
triggerprimitive_frag_params = {
    "fragment_type_description": "Trigger Primitive",
    "fragment_type": "Trigger_Primitive",
    "expected_fragment_count": number_of_readout_apps * 3,
    "min_size_bytes": 72,
    "max_size_bytes": 144,
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

# Determine if this computer has enough resources for these tests
resource_validator = resource_validation.ResourceValidator()
resource_validator.cpu_count_needs(30, 60)  # 3 for each data source (incl TPG) plus 3 more for everything else
resource_validator.free_memory_needs(20, 32)  # 25% more than what we observe being used ('free -h')
actual_output_path = get_pytest_tmpdir()
resource_validator.free_disk_space_needs(actual_output_path, 1)  # more than what we observe


conf_dict = data_classes.integtest_params_for_generated_dunedaq_config()
conf_dict.object_databases = ["config/daqsystemtest/integrationtest-objects.data.xml"]
conf_dict.dro_map_config.n_streams = number_of_data_producers
conf_dict.dro_map_config.n_apps = number_of_readout_apps
conf_dict.op_env = "integtest"
conf_dict.config_session_name = "3ru1df"
conf_dict.tpg_enabled = False
# To verify that the ability to have run control start the Connectivity Service continues to
# work, we include that option in this integtest.
conf_dict.connsvc_control = data_classes.ConnSvcControl.RUNCONTROL

conf_dict.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="RandomTCMakerConf",
        updates={"trigger_rate_hz": trigger_rate},
    )
)
conf_dict.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="LatencyBuffer", updates={"size": 200000}
    )
)
conf_dict.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="DFOConf",
        updates={"busy_threshold": 3, "free_threshold": 2}
    )
)

swtpg_conf = copy.deepcopy(conf_dict)
swtpg_conf.tpg_enabled = True
swtpg_conf.frame_file = (
    "asset://?checksum=dd156b4895f1b06a06b6ff38e37bd798"  # WIBEth All Zeros
)
swtpg_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="TAMakerPrescaleAlgorithm",
        obj_id="dummy-ta-maker",
        updates={"prescale": ta_prescale},
    )
)

confgen_arguments = {
    "WIBEth_System": conf_dict,
    "WIBEth_TPG_System": swtpg_conf,
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
    # Check that the ConnSvc log file has the name that run control uses
    if not any(
        f"{run_dunerc.daq_session_name}_local-connection-server" in str(logname) for logname in run_dunerc.log_files
    ):
        fail_msg = "It appears that something other than run control started the Connectivity Service, based on the name of the ConnSvc log file, and one of the conditions of this integtest is to have RC start the ConnSvc."
        pytest.fail(fail_msg, pytrace=False)

    if check_for_logfile_errors:
        # Check that there are no warnings or errors in the log files
        assert log_file_checks.logs_are_error_free(
            run_dunerc.log_files, True, True, ignored_logfile_problems,
            verbosity_helper=run_dunerc.verbosity_helper
        )


def test_data_files(run_dunerc):
    local_expected_event_count = expected_event_count
    local_event_count_tolerance = expected_event_count_tolerance
    fragment_check_list = [triggercandidate_frag_params, hsi_frag_params, wibeth_frag_params]
    if run_dunerc.confgen_config.tpg_enabled:
        local_expected_event_count += (
            (6250 / ta_prescale)
            * number_of_data_producers
            * number_of_readout_apps
            * run_duration
            / 100
        )
        local_event_count_tolerance += (
            (250 / ta_prescale)
            * number_of_data_producers
            * number_of_readout_apps
            * run_duration
            / 100
        )
        fragment_check_list.append(triggerprimitive_frag_params)
        fragment_check_list.append(triggeractivity_frag_params)

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


def test_cleanup(run_dunerc):
    utility_functions.remove_hdf5_files_if_requested(run_dunerc, this_test_requests_hdf5_file_removal=False)

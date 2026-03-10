import pytest
import os
import re
import copy
import urllib.request

import integrationtest.data_file_checks as data_file_checks
import integrationtest.log_file_checks as log_file_checks
import integrationtest.data_classes as data_classes
import integrationtest.resource_validation as resource_validation
from integrationtest.get_pytest_tmpdir import get_pytest_tmpdir

pytest_plugins = "integrationtest.integrationtest_drunc"

# tweak the print() statement default behavior so that it always flushes the output.
import functools
print = functools.partial(print, flush=True)

# Values that help determine the running conditions
number_of_data_producers = 2
number_of_readout_apps = 3
number_of_dataflow_apps = 3
trigger_rate = 3.0  # Hz
run_duration = 20  # seconds
ta_prescale = 100

# Default values for validation parameters
expected_number_of_data_files = 3 * number_of_dataflow_apps
check_for_logfile_errors = True
expected_event_count = run_duration * trigger_rate / number_of_dataflow_apps
expected_event_count_tolerance = expected_event_count / 10

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

# Introduction: the basic pattern used in the DUNE DAQ integration tests is to set up and
# run one or more instances of the DAQ system ("DAQ sessions") and then verify that the
# results of each test run (which often use emulated data sources) match what is expected,
# given the configuration(s) of the DAQ system that the test writer provided.
#
# In all of this, the word "test" is a bit over-loaded.
# * The pytest framework refers to the functions that are run to check the results of the
#   data-taking as "tests". We tend to call those "validations" or "checks".  When we
#   see the summary at the end of an integtest report that 'N tests were run', that
#   means N validation functions were run by the pytest framework to check the results
#   of the data taking in various ways.
# * Distinct from that, we tend to use the word "test" to refer to one of our integtests.
#   That is, the set of DAQ sessions and validation checks that are in one of these *_test.py
#   files.
#
# In each of these integtest files, there are two categories of information that are required
# to be provided to our integtest infrastructure and one optional type. These are used to
# set up and loop through the desired DAQ sessions. The categories are the following:
# 1. the configuration of the DAQ system (system topology, application parameters, etc.)
# 2. the list of process managers that should be used [optional]
# 3. the list of run control commands that should be executed
# More information is provided about each of these below [coming soon!].
#

# Determine if this computer has enough resources for these tests
resource_validator = resource_validation.ResourceValidator()
resource_validator.cpu_count_needs(22, 44)  # 3 for each data source (incl TPG) plus 4 more for everything else
resource_validator.free_memory_needs(15, 24)  # 25% more than what we observe being used ('free -h')
actual_output_path = get_pytest_tmpdir()
resource_validator.free_disk_space_needs(actual_output_path, 1)  # more than what we observe
resval_debug_string = resource_validator.get_debug_string()
print(f"{resval_debug_string}")

# 29-Dec-2025, KAB: The following comment about three variables is out-of-date.
# It will be replaced soon, and the comment block above is a start on that.
#
# The next three variable declarations *must* be present as globals in the test
# file. They're read by the "fixtures" in conftest.py to determine how
# to run the config generation and nanorc

object_databases = ["config/daqsystemtest/integrationtest-objects.data.xml"]

conf_dict = data_classes.drunc_config()
conf_dict.dro_map_config.n_streams = number_of_data_producers
conf_dict.dro_map_config.n_apps = number_of_readout_apps
conf_dict.op_env = "integtest"
conf_dict.config_session_name = "3ru3df"
conf_dict.tpg_enabled = False
conf_dict.n_df_apps = number_of_dataflow_apps

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
    "Software_TPG_System": swtpg_conf,
}

# 29-Dec-2025, KAB: added sample process manager choices.
process_manager_choices = {
    "StandAloneSSH_PM" : "ssh-standalone",
#   "ParamikoClient_PM" : "ssh-standalone-paramiko-client",
}

# The commands to run in nanorc, as a list
nanorc_command_list = "boot conf".split()
nanorc_command_list += (
    "start --run-number 101 wait 5 enable-triggers wait ".split()
    + [str(run_duration)]
    + "disable-triggers wait 1 drain-dataflow wait 2 stop-trigger-sources wait 1 stop wait 2".split()
)
nanorc_command_list += (
    "start --run-number 102 wait 1 enable-triggers wait ".split()
    + [str(run_duration)]
    + "disable-triggers wait 1 drain-dataflow wait 2 stop-trigger-sources wait 1 stop wait 2".split()
)
nanorc_command_list += (
    "start --run-number 103 wait 1 enable-triggers wait ".split()
    + [str(run_duration)]
    + "disable-triggers wait 1 drain-dataflow wait 2 stop-trigger-sources wait 1 stop wait 2".split()
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
    low_number_of_files = expected_number_of_data_files
    high_number_of_files = expected_number_of_data_files
    fragment_check_list = [triggercandidate_frag_params, hsi_frag_params, wibeth_frag_params]
    if run_nanorc.confgen_config.tpg_enabled:
        local_expected_event_count += (
            (6250 / ta_prescale)
            * number_of_data_producers
            * number_of_readout_apps
            * run_duration
            / (100 * number_of_dataflow_apps)
        )
        local_event_count_tolerance += (
            (250 / ta_prescale)
            * number_of_data_producers
            * number_of_readout_apps
            * run_duration
            / (100 * number_of_dataflow_apps)
        )
        fragment_check_list.append(triggerprimitive_frag_params)
        fragment_check_list.append(triggeractivity_frag_params)
    else:
        low_number_of_files -= number_of_dataflow_apps
        if low_number_of_files < 1:
            low_number_of_files = 1
    nontrig_fragment_check_list = [hsi_frag_params, wibeth_frag_params]

    # Run some tests on the output data file
    assert (
        len(run_nanorc.data_files) == high_number_of_files
        or len(run_nanorc.data_files) == low_number_of_files
    )

    all_ok = True
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
        for kdx in range(len(nontrig_fragment_check_list)):
            all_ok &= data_file_checks.check_fragment_error_flags( data_file, nontrig_fragment_check_list[kdx])
    assert all_ok

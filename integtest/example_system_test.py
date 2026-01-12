import pytest
import os
import copy
import re
import random
import string
import pathlib

import integrationtest.data_file_checks as data_file_checks
import integrationtest.log_file_checks as log_file_checks
import integrationtest.data_classes as data_classes

pytest_plugins = "integrationtest.integrationtest_drunc"

# Values that help determine the running conditions
run_duration = 20  # seconds

# Default values for validation parameters
check_for_logfile_errors = True
expected_event_count = run_duration * (1.0 + 3.0) # 1 from RTCM, 3 from FakeHSI
ta_prescale = 1000
expected_event_count_tolerance = expected_event_count / 10.0
hostname = os.uname().nodename

wibeth_frag_params = {
    "fragment_type_description": "WIBEth",
    "fragment_type": "WIBEth",
    "expected_fragment_count": 0,  # determined later
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
    "max_size_bytes": 264,
    "debug_mask": 0x0,
    "frag_sizes_by_TC_type": {"kPrescale": {"min_size_bytes": 208, "max_size_bytes": 264},
                                "kRandom": {"min_size_bytes": 128, "max_size_bytes": 264},
                                "default": {"min_size_bytes": 128, "max_size_bytes": 264} }
}
# sizes:  72 is for an empty TP fragment
#        168 is for a fragment with four TPs in it (72+24+24+24+24)
triggerprimitive_frag_params = {
    "fragment_type_description": "Trigger Primitive",
    "fragment_type": "Trigger_Primitive",
    "expected_fragment_count": 0,  # determined later
    "min_size_bytes": 72,
    "max_size_bytes": 168,
}
# 03-Jul-2025, KAB: changing the default max size from 72 to 100 to handle cases in which there
# was a Random or Prescale trigger along with a coincidental HSI event within the readout window.
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
    ]
}

# The arguments to pass to the config generator, excluding the json
# output directory (the test framework handles that)

common_config_obj = data_classes.drunc_config()
common_config_obj.op_env = "test"
common_config_obj.config_db = (
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

onebyone_local_conf = copy.deepcopy(common_config_obj)
onebyone_local_conf.session = "local-1x1-config"

twobythree_local_conf = copy.deepcopy(common_config_obj)
twobythree_local_conf.session = "local-2x3-config"

username=os.environ.get("USER")
onebyone_ehn1_conf = copy.deepcopy(common_config_obj)
onebyone_ehn1_conf.session = "ehn1-local-1x1-config"
onebyone_ehn1_conf.session_name = f"ehn1-local-1x1-config-{username}-{''.join(random.choices(string.ascii_letters, k=4))}"
onebyone_ehn1_conf.connsvc_port = None

twobythree_ehn1_conf = copy.deepcopy(common_config_obj)
twobythree_ehn1_conf.session = "ehn1-local-2x3-config"
twobythree_ehn1_conf.session_name = f"ehn1-local-2x3-config-{username}-{''.join(random.choices(string.ascii_letters, k=4))}"
twobythree_ehn1_conf.connsvc_port = None

def host_is_at_ehn1(hostname):
    return re.match(r"^(np02|np04)-srv-\d{3}$", hostname) or re.match(r"^(np02|np04)-srv-\d{3}.cern.ch$", hostname)


if host_is_at_ehn1(hostname):
    confgen_arguments = {
        "Local 1x1 Conf": onebyone_local_conf,
        "Local 2x3 Conf": twobythree_local_conf,
        "EHN1 1x1 Conf": onebyone_ehn1_conf,
        "EHN1 2x3 Conf": twobythree_ehn1_conf,
    }
else:
    confgen_arguments = {
        "Local 1x1 Conf": onebyone_local_conf,
        "Local 2x3 Conf": twobythree_local_conf,
    }


# The commands to run in nanorc, as a list
nanorc_command_list = (
    "boot wait 2 conf start --run-number 101 wait 1 enable-triggers wait ".split()
    + [str(run_duration)]
    + "disable-triggers wait 2 drain-dataflow wait 2 stop-trigger-sources stop scrap terminate".split()
)

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

    if not host_is_at_ehn1(hostname) and "EHN1" in current_test:
        pytest.skip(
            f"This computer ({hostname}) is not at EHN1, not running EHN1 sessions"
        )

    # Check that nanorc completed correctly
    assert run_nanorc.completed_process.returncode == 0


def test_log_files(run_nanorc):
    current_test = os.environ.get("PYTEST_CURRENT_TEST")

    if not host_is_at_ehn1(hostname) and "EHN1" in current_test:
        pytest.skip(
            f"This computer ({hostname}) is not at EHN1, not running EHN1 sessions"
        )

    session_name = run_nanorc.session_name if run_nanorc.session_name is not None else run_nanorc.session

    if host_is_at_ehn1(hostname) and "EHN1" in current_test:
        log_dir = pathlib.Path("/log")
        run_nanorc.log_files += list(log_dir.glob(f"log_*_{session_name}*.txt"))

    # Check that at least some of the expected log files are present
    assert any(
        f"{session_name}_df-01" in str(logname)
        for logname in run_nanorc.log_files
    )
    assert any(
        f"{session_name}_dfo" in str(logname) for logname in run_nanorc.log_files
    )
    assert any(
        f"{session_name}_mlt" in str(logname) for logname in run_nanorc.log_files
    )
    assert any(
        f"{session_name}_ru" in str(logname) for logname in run_nanorc.log_files
    )

    if check_for_logfile_errors:
        # Check that there are no warnings or errors in the log files
        assert log_file_checks.logs_are_error_free(
            run_nanorc.log_files, True, True, ignored_logfile_problems
        )


def test_data_files(run_nanorc):
    current_test = os.environ.get("PYTEST_CURRENT_TEST")

    if not host_is_at_ehn1(hostname) and "EHN1" in current_test:
        pytest.skip(
            f"This computer ({hostname}) is not at EHN1, not running EHN1 sessions"
        )

    datafile_params = {
        "Local 1x1 Conf": {"expected_fragment_count": 4, "expected_file_count": 1},
        "Local 2x3 Conf": {"expected_fragment_count": 8, "expected_file_count": 3},
        "EHN1 1x1 Conf": {"expected_fragment_count": 4, "expected_file_count": 1},
        "EHN1 2x3 Conf": {"expected_fragment_count": 8, "expected_file_count": 3},
    }

    expected_file_count = 0
    expected_fragment_count = 0
    for key in datafile_params.keys():
        if key in current_test:
            expected_file_count = datafile_params[key]["expected_file_count"]
            expected_fragment_count = datafile_params[key]["expected_fragment_count"]
    assert expected_file_count != 0,f"Unable to locate test parameters for {current_test}"

    # Run some tests on the output data file
    assert len(run_nanorc.data_files) == expected_file_count, f"Unexpected file count: Actual: {len(run_nanorc.data_files)}, Expected: {expected_file_count}"

    local_expected_fragment_count = expected_fragment_count
    wibeth_frag_params["expected_fragment_count"] = local_expected_fragment_count
    triggerprimitive_frag_params["expected_fragment_count"] = 3 * local_expected_fragment_count / 4
    local_expected_event_count = expected_event_count
    local_event_count_tolerance = expected_event_count_tolerance
    fragment_check_list = [triggercandidate_frag_params, hsi_frag_params]

    local_expected_event_count += (
            (6250.0 / ta_prescale)
            * expected_fragment_count
            * run_duration
            / 100.0
        )
    local_event_count_tolerance += (
            (250.0 / ta_prescale)
            * expected_fragment_count
            * run_duration
            / 100.0
        )

    local_expected_event_count = local_expected_event_count / expected_file_count
    local_event_count_tolerance = local_event_count_tolerance / expected_file_count

    fragment_check_list.append(wibeth_frag_params)
    fragment_check_list.append(triggerprimitive_frag_params)

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

    assert all_ok

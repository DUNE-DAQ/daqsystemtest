# 29-Jan-2026, KAB: Steps to run this test:
# - Log into any np04-srv-XYZ computer and set up a software area with the
#     appropriate branch of daqsystemtest.
# - 'cd $DBT_AREA_ROOT/sourcecode/daqsystemtest/integtest'
# - 'mkdir -p $HOME/dunedaq/scratch'  # only need to do this once per user account
# - 'export PYTEST_DEBUG_TEMPROOT=$HOME/dunedaq/scratch'  # once per login/shell
# - 'pytest -s ./sample_ehn1_multihost_test.py'
#
# This test currently puts the various DAQ processes on the following computers:
# - np04-srv-021:  ru-01, ru-controller
# - np04-srv-022:  mlt, tc-maker-1, trg-controller
# - np04-srv-028:  local-connection-server, tp-stream-writer
# - np04-srv-029:  dfo-01, df-01, df-controller
# - localhost:  hsi-fake-01, hsi-fake-to-tc-app, root-controller
#
# The choice of running the tp-stream-writer on a different computer than the other
# Dataflow apps was just to show that it works.  And, running the ConnectivityServer
# on a computer other than "localhost" was also to show that it can be done.
#
# To enable the capturing of TRACE messages on all of the computers...
# - 'export TRACE_FILE=/tmp/pytest-of-${USER}/log/${USER}_dunedaq.trace'  # once per login/shell
# - 'mkdir -p /tmp/pytest-of-${USER}/log'  # only need to do this once per computer
# - 'ssh np04-srv-021 "mkdir -p /tmp/pytest-of-${USER}/log"'  # only once per user
# - 'ssh np04-srv-022 "mkdir -p /tmp/pytest-of-${USER}/log"'  # only once per user
# - 'ssh np04-srv-028 "mkdir -p /tmp/pytest-of-${USER}/log"'  # only once per user
# - 'ssh np04-srv-029 "mkdir -p /tmp/pytest-of-${USER}/log"'  # only once per user
# - 'pytest -s ./sample_ehn1_multihost_test.py'

import pytest
import os
import copy
import re
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
wibeth_tpset_params = {
    "fragment_type_description": "TP Stream",
    "fragment_type": "Trigger_Primitive",
    "expected_fragment_count": 1 * 3,  # number of readout apps times 3 planes per APA/CRP
    "frag_counts_by_record_ordinal": {"first": {"min_count": 1, "max_count": 1 * 3},
                                      "default": {"min_count": 1 * 3, "max_count": 1 * 3} },
    "min_size_bytes": 72,
    "max_size_bytes": 120000,
    "debug_mask": 0x0,
    "frag_sizes_by_record_ordinal": {  "first": {"min_size_bytes":     96, "max_size_bytes": 240000},
                                      "second": {"min_size_bytes":     96, "max_size_bytes": 240000},
                                        "last": {"min_size_bytes":     96, "max_size_bytes": 240000},
                                     "default": {"min_size_bytes": 170000, "max_size_bytes": 230000} }
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

# Set up the software environment on each of the 4 computers needed for this test.
# This serves two purposes: it verifies that we can ssh to
# those computers (so we know that we are running at EHN1, etc.), and it pre-loads
# the software release from CVMFS onto all of those computers (so the startup of
# DAQ apps such as the ConnectivityServer don't take a long time initially).
import subprocess
computers_that_are_unreachable = []
sw_area_root = os.environ.get("DBT_AREA_ROOT")
if sw_area_root is not None:
    print("")
    needed_computer="np04-srv-021"
    print(f"Confirming that we can ssh to {needed_computer}...")
    proc = subprocess.Popen(f"ssh {needed_computer} 'cd {sw_area_root}; . ./env.sh'", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    retval = proc.returncode
    if retval != 0:
        computers_that_are_unreachable.append(needed_computer)
    needed_computer="np04-srv-022"
    print(f"Confirming that we can ssh to {needed_computer}...")
    proc = subprocess.Popen(f"ssh {needed_computer} 'cd {sw_area_root}; . ./env.sh'", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    retval = proc.returncode
    if retval != 0:
        computers_that_are_unreachable.append(needed_computer)
    needed_computer="np04-srv-028"
    print(f"Confirming that we can ssh to {needed_computer}...")
    proc = subprocess.Popen(f"ssh {needed_computer} 'cd {sw_area_root}; . ./env.sh'", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    retval = proc.returncode
    if retval != 0:
        computers_that_are_unreachable.append(needed_computer)
    needed_computer="np04-srv-029"
    print(f"Confirming that we can ssh to {needed_computer}...")
    proc = subprocess.Popen(f"ssh {needed_computer} 'cd {sw_area_root}; . ./env.sh'", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    retval = proc.returncode
    if retval != 0:
        computers_that_are_unreachable.append(needed_computer)
else:
    computers_that_are_unreachable = ["Unable to determine the value of the DBT_AREA_ROOT env var"]

# verify that the pytest tmpdir has been set to a multi-host (NFS) location
pytest_tmpdir_looks_reasonable = False
pytest_tmpdir = os.environ.get("PYTEST_DEBUG_TEMPROOT")
if pytest_tmpdir is not None:
    if os.path.isdir(pytest_tmpdir):
        pytest_tmpdir_looks_reasonable = True
    else:
        print("")
        print("")
        print(f"*** WARNING: the directory referenced by PYTEST_DEBUG_TEMPROOT ({pytest_tmpdir}) does not exist!")
        print("")

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
common_config_obj.config_substitutions.append(
    data_classes.relationship_substitution(
        obj_class="ReadoutApplication",
        obj_id="ru-01",
        rel_name="runs_on",
        replacement_object_class="VirtualHost",
        replacement_object_id="vnp04-srv-021"
    )
)
common_config_obj.config_substitutions.append(
    data_classes.relationship_substitution(
        obj_class="RCApplication",
        obj_id="ru-controller",
        rel_name="runs_on",
        replacement_object_class="VirtualHost",
        replacement_object_id="vnp04-srv-021"
    )
)
common_config_obj.config_substitutions.append(
    data_classes.relationship_substitution(
        obj_class="MLTApplication",
        obj_id="mlt",
        rel_name="runs_on",
        replacement_object_class="VirtualHost",
        replacement_object_id="vnp04-srv-022"
    )
)
common_config_obj.config_substitutions.append(
    data_classes.relationship_substitution(
        obj_class="TriggerApplication",
        obj_id="tc-maker-1",
        rel_name="runs_on",
        replacement_object_class="VirtualHost",
        replacement_object_id="vnp04-srv-022"
    )
)
common_config_obj.config_substitutions.append(
    data_classes.relationship_substitution(
        obj_class="RCApplication",
        obj_id="trg-controller",
        rel_name="runs_on",
        replacement_object_class="VirtualHost",
        replacement_object_id="vnp04-srv-022"
    )
)
common_config_obj.config_substitutions.append(
    data_classes.relationship_substitution(
        obj_class="DFOApplication",
        obj_id="dfo-01",
        rel_name="runs_on",
        replacement_object_class="VirtualHost",
        replacement_object_id="vnp04-srv-029"
    )
)
common_config_obj.config_substitutions.append(
    data_classes.relationship_substitution(
        obj_class="DFApplication",
        obj_id="df-01",
        rel_name="runs_on",
        replacement_object_class="VirtualHost",
        replacement_object_id="vnp04-srv-029"
    )
)
common_config_obj.config_substitutions.append(
    data_classes.relationship_substitution(
        obj_class="TPStreamWriterApplication",
        obj_id="tp-stream-writer",
        rel_name="runs_on",
        replacement_object_class="VirtualHost",
        replacement_object_id="vnp04-srv-028"
    )
)
common_config_obj.config_substitutions.append(
    data_classes.relationship_substitution(
        obj_class="RCApplication",
        obj_id="df-controller",
        rel_name="runs_on",
        replacement_object_class="VirtualHost",
        replacement_object_id="vnp04-srv-029"
    )
)
common_config_obj.config_substitutions.append(
    data_classes.relationship_substitution(
        obj_class="ConnectionService",
        obj_id="local-connection-server",
        rel_name="runs_on",
        replacement_object_class="VirtualHost",
        replacement_object_id="vnp04-srv-028"
    )
)
common_config_obj.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="ConnectivityService",
        obj_id="local-connectivity-service-config",
        updates={"host": "np04-srv-028"}
    )
)

ehn1_multihost_1x1_conf = copy.deepcopy(common_config_obj)
ehn1_multihost_1x1_conf.session = "local-1x1-config"
ehn1_multihost_1x1_conf.connsvc_port = 0  # random

confgen_arguments = {"EHN1 MultiHost 1x1 Conf": ehn1_multihost_1x1_conf}


# The commands to run in dunerc, as a list
if len(computers_that_are_unreachable) == 0 and pytest_tmpdir_looks_reasonable:
    dunerc_command_list = (
        "boot wait 2 conf start --run-number 101 wait 1 enable-triggers wait ".split()
        + [str(run_duration)]
        + "disable-triggers wait 2 drain-dataflow wait 2 stop-trigger-sources stop scrap terminate".split()
    )
else:
    dunerc_command_list = ["wait", "1"]

# The tests themselves


def test_dunerc_success(run_dunerc, capsys):
    if len(computers_that_are_unreachable) > 0:
        with capsys.disabled():
            print(f"\n\n\N{LARGE YELLOW CIRCLE} The following computers are needed for this test but are unreachable from this computer ({hostname}) via ssh:")
            print(f"      {computers_that_are_unreachable}")
        pytest.skip(f"One or more needed computers are unreachable ({computers_that_are_unreachable}).")
    if not pytest_tmpdir_looks_reasonable:
        with capsys.disabled():
            print("\n\n\N{LARGE YELLOW CIRCLE} The PYTEST_DEBUG_TEMPROOT env var has not been set to point to a valid directory.")
            print("\N{LARGE YELLOW CIRCLE} This is needed for this integtest to run.")
            print("\N{LARGE YELLOW CIRCLE} Suggested steps: 'mkdir -p $HOME/dunedaq/scratch; export PYTEST_DEBUG_TEMPROOT=$HOME/dunedaq/scratch'")
            print("\N{LARGE YELLOW CIRCLE} And you may want to consider 'unset PYTEST_DEBUG_TEMPROOT' after running the test.")
            print("\N{LARGE YELLOW CIRCLE} Please see the comments at the top of this integtest for more information.")
        pytest.skip("The PYTEST_DEBUG_TEMPROOT env var has not been set to point to a valid directory.")

    with capsys.disabled():
        print("")
        print("\n\n\N{LARGE YELLOW CIRCLE} PLEASE NOTE: this script is cleaning up stale _gunicorn_ processes on np04-srv-028...")
        print("")
    proc = subprocess.Popen(f"ssh np04-srv-028 killall gunicorn", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate()
    retval = proc.returncode
    if retval != 0:
        print("*** WARNING: the cleanup of stale _gunicorn_ process on np04-srv-028 did not succeed...")

    current_test = os.environ.get("PYTEST_CURRENT_TEST")
    match_obj = re.search(r".*\[(.+)-run_dunerc0\].*", current_test)
    if match_obj:
        current_test = match_obj.group(1)
    banner_line = re.sub(".", "=", current_test)
    print(banner_line)
    print(current_test)
    print(banner_line)

    # Check that dunerc completed correctly
    assert run_dunerc.completed_process.returncode == 0


def test_log_files(run_dunerc):
    if len(computers_that_are_unreachable) > 0:
        pytest.skip(f"One or more needed computers are unreachable ({computers_that_are_unreachable}).")
    if not pytest_tmpdir_looks_reasonable:
        pytest.skip("The PYTEST_DEBUG_TEMPROOT env var has not been set to point to a valid directory.")

    # Check that at least some of the expected log files are present
    session_name = run_dunerc.session_name if run_dunerc.session_name is not None else run_dunerc.session
    assert any(
        f"{session_name}_df-01" in str(logname)
        for logname in run_dunerc.log_files
    )
    assert any(
        f"{session_name}_dfo" in str(logname) for logname in run_dunerc.log_files
    )
    assert any(
        f"{session_name}_mlt" in str(logname) for logname in run_dunerc.log_files
    )
    assert any(
        f"{session_name}_ru" in str(logname) for logname in run_dunerc.log_files
    )

    if check_for_logfile_errors:
        # Check that there are no warnings or errors in the log files
        assert log_file_checks.logs_are_error_free(
            run_dunerc.log_files, True, True, ignored_logfile_problems
        )


def test_data_files(run_dunerc):
    if len(computers_that_are_unreachable) > 0:
        pytest.skip(f"One or more needed computers are unreachable ({computers_that_are_unreachable}).")
    if not pytest_tmpdir_looks_reasonable:
        pytest.skip("The PYTEST_DEBUG_TEMPROOT env var has not been set to point to a valid directory.")

    current_test = os.environ.get("PYTEST_CURRENT_TEST")
    datafile_params = {
        "EHN1 MultiHost 1x1 Conf": {"expected_fragment_count": 4, "expected_file_count": 1},
    }

    expected_file_count = 0
    expected_fragment_count = 0
    for key in datafile_params.keys():
        if key in current_test:
            expected_file_count = datafile_params[key]["expected_file_count"]
            expected_fragment_count = datafile_params[key]["expected_fragment_count"]
    assert expected_file_count != 0,f"Unable to locate test parameters for {current_test}"

    # Run some tests on the output data file
    assert len(run_dunerc.data_files) == expected_file_count, f"Unexpected file count: Actual: {len(run_dunerc.data_files)}, Expected: {expected_file_count}"

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

    for idx in range(len(run_dunerc.data_files)):
        data_file = data_file_checks.DataFile(run_dunerc.data_files[idx])
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


def test_tpstream_files(run_dunerc):
    if len(computers_that_are_unreachable) > 0:
        pytest.skip(f"One or more needed computers are unreachable ({computers_that_are_unreachable}).")
    if not pytest_tmpdir_looks_reasonable:
        pytest.skip("The PYTEST_DEBUG_TEMPROOT env var has not been set to point to a valid directory.")

    tpstream_files = run_dunerc.tpset_files
    local_expected_event_count = (
        run_duration + 8
    )  # TPStreamWriterModule is currently configured to write at 1 Hz, addl TimeSlices expected because of wait times in drunc command list
    local_event_count_tolerance = local_expected_event_count / 10
    fragment_check_list = [wibeth_tpset_params]  # WIBEth

    assert len(tpstream_files) == 1  # one for each run

    print("")
    all_ok = True
    for idx in range(len(tpstream_files)):
        base_filename = os.path.basename(tpstream_files[idx])
        print(f"Checking {base_filename}...")
        data_file = data_file_checks.DataFile(tpstream_files[idx])
        # all_ok &= data_file_checks.sanity_check(data_file) # Sanity check doesn't work for stream files
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

"""
Integration test configuration and test suite for TPReplay in the DAQ system.

This script sets up temporary configurations for two environments:
    - np02-tpreplay
    - np04-tpreplay

It does the following:
1. Creates a temporary configuration DB file (via OKS) for each session.
2. Populates the config DB with TPStream and SourceID objects.
3. Customizes runtime configuration through deep config substitutions.
4. Runs a pre-defined dunerc command sequence (boot → start → stop → terminate).
5. Validates:
    - DuneRC command success
    - Presence and correctness of log files
    - Data file contents (number of SIDs, file count)

Tests are structured using `pytest` and use fixtures provided via
`integrationtest.integrationtest_drunc`.

Temporary config directories are cleaned up using `atexit` once the test completes.
"""

import atexit
import copy
import conffwk
import os
import pathlib
import pytest
import random
import shutil
import string
import tempfile

import integrationtest.data_classes as data_classes
import integrationtest.data_file_checks as data_file_checks
import integrationtest.log_file_checks as log_file_checks
import integrationtest.basic_checks as basic_checks
import integrationtest.resource_validation as resource_validation
import integrationtest.utility_functions2 as utility_functions
from integrationtest.get_pytest_tmpdir import get_pytest_tmpdir
from integrationtest.verbosity_helper import IntegtestVerbosityLevels

from daqconf.consolidate import copy_configuration
from pathlib import Path

# Register cleanup for tmpdirname
def _cleanup_tmpdir():
    if os.path.exists(tmpdirname):
        shutil.rmtree(tmpdirname)

import functools
print = functools.partial(print, flush=True)  # always flush print() output

pytest_plugins = "integrationtest.integrationtest_drunc"

# Run setup
run_duration = 20  # seconds
check_for_logfile_errors = True
ignored_logfile_problems = {
    "local-connection-server": [
        "errorlog: -",
    ],
    "config_mlt": [
        "Trigger is inhibited",
        "failures to insert data into the latency buffer out of"
    ],
    "config_dfo": [
        "that was busy with"
    ],
    "config_tpreplay": [
        "Request on empty buffer",
        "Postprocessing has too much backlog"
    ],
    "-controller": [
    ]
}

# Determine if this computer has enough resources for these tests
resource_validator = resource_validation.ResourceValidator()
resource_validator.cpu_count_needs(6, 12)  # 3 for ConnSvc threads plus 3 more for everything else
resource_validator.free_memory_needs(3, 4)  # 50% more than what we observe being used ('free -h')
actual_output_path = get_pytest_tmpdir()
resource_validator.free_disk_space_needs(actual_output_path, 1)  # more than what we observe

### Config setup
# Create temp config
tmpdirname = tempfile.mkdtemp()
path = Path(tmpdirname).resolve()

# Resolve the source config file
config_src = Path(__file__).parent / "../config/daqsystemtest/example-configs.data.xml"
config_src = config_src.resolve()

copy_configuration(path, [os.path.dirname(__file__) + "/../config/daqsystemtest/example-configs.data.xml"])
local_db = conffwk.Configuration("oksconflibs:" + tmpdirname + "/example-configs.data.xml")

common_config_obj = data_classes.integtest_params_for_predefined_dunedaq_config()
common_config_obj.op_env = "test"
common_config_obj.tpg_enabled = False
common_config_obj.predefined_config_db = ( tmpdirname + "/example-configs.data.xml" )

# Get default tpreplay config
tpreplay_local_conf = copy.deepcopy(common_config_obj)
tpreplay_local_conf.config_session_name = "local-tpreplay-config"

# Get necessary dal objects
a_source_id_dal = local_db.get_dal(class_name="SourceIDConf", uid="tpreplay-tp-srcid-100000")
a_tpstream_conf_dal = local_db.get_dal(class_name="TPStreamConf", uid="def-tp-stream-1")

## setup TPStream files
first_tpstream_file = copy.deepcopy(a_tpstream_conf_dal)
second_tpstream_file = copy.deepcopy(a_tpstream_conf_dal)
first_tpstream_file.id = "tp-stream-1"
first_tpstream_file.filename = "/cvmfs/dunedaq.opensciencegrid.org/assets/files/7/8/4/np02vd_tp_run037001_0000_tp-stream-writer_tpw_0_20250702T094514.hdf5"
first_tpstream_file.index = 1
second_tpstream_file.id = "tp-stream-2"
second_tpstream_file.filename = "/cvmfs/dunedaq.opensciencegrid.org/assets/files/8/1/3/np02vd_tp_run037002_0000_tp-stream-writer_tpw_0_20250702T094747.hdf5"
second_tpstream_file.index = 2
local_db.update_dal(first_tpstream_file)
local_db.update_dal(second_tpstream_file)

## setup SourceIDs
all_sourceIDs = []
for a_sid_counter in range(1, 4):
    a_sid = copy.deepcopy(a_source_id_dal)
    a_sid.id = "tpreplay-tp-srcid-10000" + str(a_sid_counter)
    a_sid.sid = a_sid_counter
    a_sid.subsystem = "Trigger"
    all_sourceIDs.append(a_sid)

# commit new dal objects
for a_sid in all_sourceIDs:
    local_db.update_dal(a_sid)
local_db.commit()

## update TP Replay Module
tpreplay_local_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="TPReplayModuleConf",
        obj_id="tpreplay-tp-maker",
        updates={
            "number_of_loops": 1,
            "channel_map": "PD2VDBottomTPCChannelMap",
            "total_planes": 2,
            "tp_streams": [first_tpstream_file, second_tpstream_file],
            "filter_out_plane": [0, 1]
            },)
)

## update replay session SourceIDs
tpreplay_local_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="TPReplayApplication",
        obj_id="tpreplay",
        updates={
            "tp_source_ids": all_sourceIDs[:2]
            },)
)

## update random TC maker
utility_functions.set_RTCM_trigger_params(tpreplay_local_conf, trigger_rate=0)

## update HSI
utility_functions.set_fake_hsi_trigger_params(tpreplay_local_conf, trigger_rate=0)

# prep NP04 conf
tpreplay_np04_conf = copy.deepcopy(tpreplay_local_conf)
# update
tpreplay_np04_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="TPReplayApplication",
        obj_id="tpreplay",
        updates={
            "tp_source_ids": all_sourceIDs
            },)
)
tpreplay_np04_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="TPReplayModuleConf",
        obj_id="tpreplay-tp-maker",
        updates={
            "number_of_loops": 1,
            "channel_map": "PD2HDTPCChannelMap",
            "total_planes": 3,
            "tp_streams": [first_tpstream_file, second_tpstream_file],
            "filter_out_plane": [0, 1]
            },)
)
tpreplay_np04_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="TPStreamConf",
        obj_id="tp-stream-1",
        updates={
            "filename": "/cvmfs/dunedaq.opensciencegrid.org/assets/files/c/c/d/np04hd_tp_run035722_0000_tp-stream-writer_tpw_0_20250403T131152.hdf5"
            },)
)
tpreplay_np04_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="TPStreamConf",
        obj_id="tp-stream-2",
        updates={
            "filename": "/cvmfs/dunedaq.opensciencegrid.org/assets/files/b/a/4/np04hd_tp_run035723_0000_tp-stream-writer_tpw_0_20250403T143941.hdf5"
            },)
)
tpreplay_np04_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="TAMakerPrescaleAlgorithm",
        obj_id="dummy-ta-maker",
        updates={
            "prescale": "1"
            },)
)
tpreplay_np04_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="TCMakerPrescaleAlgorithm",
        obj_id="tc-pass-through-algo",
        updates={
            "prescale": "1"
            },)
)

# Finally store configs in map
confgen_arguments = {
  "np02-tpreplay": tpreplay_local_conf,
  "np04-tpreplay": tpreplay_np04_conf
}

# The commands to run in dunerc, as a list
dunerc_command_list = "boot conf wait 5".split()
dunerc_command_list += (
    "start ".split()
    + "--run-number 101 enable-triggers wait ".split()
    + [str(run_duration)]
    + "disable-triggers drain-dataflow wait 2 stop-trigger-sources wait 2 stop wait 2".split()
)
dunerc_command_list += "scrap terminate".split()

atexit.register(_cleanup_tmpdir)

### Tests
# Run control
def test_dunerc_success(run_dunerc, caplog):
    # checks for run control success, problems during pytest setup, etc.
    basic_checks.basic_checks(run_dunerc, caplog, print_test_name=True)

# Log files
def test_log_files(run_dunerc):
    session_name = run_dunerc.daq_session_name

    log_dir = pathlib.Path("/log")
    run_dunerc.log_files += [
        f for f in log_dir.glob(f"log_*_{session_name}*.txt") if f.exists()
    ]

    # Check that at least some of the expected log files are present
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
        f"{session_name}_tpreplay" in str(logname) for logname in run_dunerc.log_files
    )

    if check_for_logfile_errors:
        # Check that there are no warnings or errors in the log files
        assert log_file_checks.logs_are_error_free(
            run_dunerc.log_files, True, True, ignored_logfile_problems,
            verbosity_helper=run_dunerc.verbosity_helper
        ), f"Errors found in log files: {run_dunerc.log_files}"

# Data files
def test_data_files(run_dunerc):
    current_test = os.environ.get("PYTEST_CURRENT_TEST")

    datafile_params = {
        "np02-tpreplay": {"n_data_files": 1, "n_sids_tp": 2, "n_sids_ta": 1, "n_sids_tc": 1},
        "np04-tpreplay": {"n_data_files": 1, "n_sids_tp": 3, "n_sids_ta": 1, "n_sids_tc": 1}
    }

    # Match run to checks
    # 29-Dec-2025, KAB: modified this block of code to work with the addition of
    # the process-manager-choice fixture.
    selected_params = {}
    for key in datafile_params.keys():
        if key in current_test:
            selected_params = datafile_params[key]
            if run_dunerc.verbosity_helper.compare_level(IntegtestVerbosityLevels.integtest_debug):
                print("Selected params for", key, ":", selected_params)
            break
    if not selected_params:
        print(f"\n*** ERROR: unable to determine the datafile_params for test {current_test}.")

    ### Run some tests on the output data file
    all_ok = len(run_dunerc.data_files) == selected_params["n_data_files"]
    if all_ok:
        if run_dunerc.verbosity_helper.compare_level(IntegtestVerbosityLevels.drunc_transitions):
            print(f"\n\N{WHITE HEAVY CHECK MARK} The correct number of raw data files was found ({selected_params['n_data_files']})")
    else:
        print(f"\n\N{POLICE CARS REVOLVING LIGHT} An incorrect number of raw data files was found, expected {selected_params['n_data_files']}, found {len(run_dunerc.data_files)} \N{POLICE CARS REVOLVING LIGHT}")

    ## Other test
    # number of SIDs
    data_file = data_file_checks.DataFile(run_dunerc.data_files[0], run_dunerc.verbosity_helper)
    all_ok &= data_file_checks.check_n_unique_sids(data_file, selected_params['n_sids_tp'], selected_params['n_sids_ta'], selected_params['n_sids_tc'] )
    if all_ok:
        if run_dunerc.verbosity_helper.compare_level(IntegtestVerbosityLevels.drunc_transitions):
            print(f"\N{WHITE HEAVY CHECK MARK} The expected number of unique Source IDs was found ({selected_params['n_sids_tp'], selected_params['n_sids_ta'], selected_params['n_sids_tc']})")
    else:
        print(f"\N{POLICE CARS REVOLVING LIGHT} The number of unique Source IDs is NOT as expected ({selected_params['n_sids_tp'], selected_params['n_sids_ta'], selected_params['n_sids_tc']})! \N{POLICE CARS REVOLVING LIGHT}")

    assert all_ok, "\N{POLICE CARS REVOLVING LIGHT} One or more data file checks failed! \N{POLICE CARS REVOLVING LIGHT}"


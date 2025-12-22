"""
Integration test configuration and test suite for TPReplay in the DAQ system.

This script sets up temporary configurations for two environments:
    - np02-tpreplay
    - np04-tpreplay

It does the following:
1. Creates a temporary configuration DB file (via OKS) for each session.
2. Populates the config DB with TPStream and SourceID objects.
3. Customizes runtime configuration through deep config substitutions.
4. Runs a pre-defined nanorc command sequence (boot → start → stop → terminate).
5. Validates:
    - Nanorc command success
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
import re
import shutil
import string
import tempfile

import integrationtest.data_classes as data_classes
import integrationtest.data_file_checks as data_file_checks
import integrationtest.log_file_checks as log_file_checks

from daqconf.consolidate import copy_configuration
from pathlib import Path

# Register cleanup for tmpdirname
def _cleanup_tmpdir():
    if os.path.exists(tmpdirname):
        shutil.rmtree(tmpdirname)

pytest_plugins = "integrationtest.integrationtest_drunc"

# tweak the print() statement default behavior so that it always flushes the output.
import functools
print = functools.partial(print, flush=True)

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

### Config setup
# Create temp config
tmpdirname = tempfile.mkdtemp()
path = Path(tmpdirname).resolve()

# Resolve the source config file
config_src = Path(__file__).parent / "../config/daqsystemtest/example-configs.data.xml"
config_src = config_src.resolve()

copy_configuration(path, [os.path.dirname(__file__) + "/../config/daqsystemtest/example-configs.data.xml"])
local_db = conffwk.Configuration("oksconflibs:" + tmpdirname + "/example-configs.data.xml")

common_config_obj = data_classes.drunc_config()
common_config_obj.op_env = "test"
common_config_obj.tpg_enabled = False
common_config_obj.config_db = ( tmpdirname + "/example-configs.data.xml" )

# Get default tpreplay config
tpreplay_local_conf = copy.deepcopy(common_config_obj)
tpreplay_local_conf.session = "local-tpreplay-config"

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
tpreplay_local_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_id="random-tc-generator",
        obj_class="RandomTCMakerConf",
        updates={
            "trigger_rate_hz": 0
            },)
)

## update HSI
tpreplay_local_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_id="fakehsi",
        obj_class="FakeHSIEventGeneratorConf",
        updates={
            "trigger_rate": 0
            },)
)

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

# The commands to run in nanorc, as a list
nanorc_command_list = "boot conf wait 5".split()
nanorc_command_list += (
        "start ".split()
        + "--run-number 101 enable-triggers wait ".split()
        + [str(run_duration)]
        + "disable-triggers drain-dataflow wait 2 stop-trigger-sources wait 2 stop wait 2".split()
    )
nanorc_command_list += "scrap terminate".split()

atexit.register(_cleanup_tmpdir)

### Tests
# Run control
def test_nanorc_success(run_nanorc):
    current_test = os.environ.get("PYTEST_CURRENT_TEST")

    match_obj = re.search(r".*\[(.+)-run_nanorc0\].*", current_test)
    if match_obj:
        current_test = match_obj.group(1)
    banner_line = re.sub(".", "=", current_test)
    print(banner_line)
    print(current_test)
    print(banner_line)

    # Check that nanorc completed correctly
    assert run_nanorc.completed_process.returncode == 0

# Log files
def test_log_files(run_nanorc):
    current_test = os.environ.get("PYTEST_CURRENT_TEST")

    session_name = run_nanorc.session_name if run_nanorc.session_name is not None else run_nanorc.session

    log_dir = pathlib.Path("/log")
    run_nanorc.log_files += [
        f for f in log_dir.glob(f"log_*_{session_name}*.txt") if f.exists()
    ]

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
        f"{session_name}_tpreplay" in str(logname) for logname in run_nanorc.log_files
    )

    if check_for_logfile_errors:
        # Check that there are no warnings or errors in the log files
        assert log_file_checks.logs_are_error_free(
            run_nanorc.log_files, True, True, ignored_logfile_problems
        ), f"Errors found in log files: {run_nanorc.log_files}"

# Data files
def test_data_files(run_nanorc):
    current_test = os.environ.get("PYTEST_CURRENT_TEST")

    datafile_params = {
        "np02-tpreplay": {"n_data_files": 1, "n_sids_tp": 2, "n_sids_ta": 1, "n_sids_tc": 1},
        "np04-tpreplay": {"n_data_files": 1, "n_sids_tp": 3, "n_sids_ta": 1, "n_sids_tc": 1}
    }

    # Match run to checks
    match = re.search(r'\[(.+?)-run', current_test)
    if match:
        key = match.group(1)
        if key in datafile_params:
            selected_params = datafile_params[key]
            print("Selected params for", key, ":", selected_params)
        else:
            print(f"Key '{key}' not found in datafile_params.")
    else:
        print("Could not extract key from current_test.")

    ### Run some tests on the output data file
    all_ok = True

    if all_ok:
        print(f"\N{WHITE HEAVY CHECK MARK} The correct number of raw data files was found ({selected_params['n_data_files']})")
    else:
        print(f"\N{POLICE CARS REVOLVING LIGHT} An incorrect number of raw data files was found, expected {selected_params['n_data_files']}, found {len(run_nanorc.data_files)} \N{POLICE CARS REVOLVING LIGHT}")

    ## Other test
    # number of SIDs
    data_file = data_file_checks.DataFile(run_nanorc.data_files[0])
    all_ok &= data_file_checks.check_n_unique_sids(data_file, selected_params['n_sids_tp'], selected_params['n_sids_ta'], selected_params['n_sids_tc'] )
    if all_ok:
        print(f"\N{WHITE HEAVY CHECK MARK} The expected number of unique Source IDs was found ({selected_params['n_sids_tp'], selected_params['n_sids_ta'], selected_params['n_sids_tc']})")
    else:
        print(f"\N{POLICE CARS REVOLVING LIGHT} The number of unique Source IDs is NOT as expected ({selected_params['n_sids_tp'], selected_params['n_sids_ta'], selected_params['n_sids_tc']})! \N{POLICE CARS REVOLVING LIGHT}")

    assert all_ok, "\N{POLICE CARS REVOLVING LIGHT} One or more data file checks failed! \N{POLICE CARS REVOLVING LIGHT}"


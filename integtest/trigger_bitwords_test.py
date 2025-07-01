"""
Integration Test for Trigger Bitword Configurations

Reminder: 
Trigger bitwords are used to control which triggers are allowed to be promoted to trigger decisions.
The bitwords functionality is independent of whatever sources are producing the triggers (TCs).

This test module validates DAQ system behavior under various trigger bitword configurations.
It uses multiple configuration variants (e.g., no bitword, prescale, timing, supernova, etc.)
and runs a controlled run control session to verify:
- Successful execution of the run using the run control
- Correct generation of log files and absence of unexpected errors
- Proper creation and content of output data files
- Expected trigger types and trigger multiplicity checks
  (Multiplicity here refers to a Trigger Decision composed of multiple different
   Trigger Candidate types that have been merged)
Detailed case descriptions:
- No bits: A default case with no trigger bitwords configured; all TC types in the config should appear.
- Prescale / Timing bits: A single specific bitword is enabled; only the corresponding TC type should be present.
- Supernova bit: A bitword not expected to participate in the run; no raw data should be produced.
- Series bit: Two independent trigger bitwords enabled; both TC types should appear in the data.
- Coincidence bit: A composite bitword combining two TC types; this triggers merged TDs, resulting in
  multiplicity due to the TC coincidence mechanism.
"""

import copy
import conffwk
import os
import pathlib
import pytest
import random
import re
import string

import integrationtest.data_classes as data_classes
import integrationtest.data_file_checks as data_file_checks
import integrationtest.log_file_checks as log_file_checks

pytest_plugins = "integrationtest.integrationtest_drunc"

# Run setup
run_duration = 15  # seconds
check_for_logfile_errors = True
ignored_logfile_problems = {
    "-controller": [
        "Worker with pid \\d+ was terminated due to signal",
        "Connection '.*' not found on the application registry",
    ],
    "local-connection-server": [
        "errorlog: -",
        "Worker with pid \\d+ was terminated due to signal",
        r"Worker \(pid:\d+\) was sent SIGHUP"
    ],
    "config_mlt": [
        "Trigger is inhibited"
    ],
    "config_dfo": [
        "that was busy with"
    ]
#    "log_.*": ["connect: Connection refused", "Connection reset by peer", "end of stream"],
}

### Config setup
common_config_obj = data_classes.drunc_config()
common_config_obj.op_env = "test"
common_config_obj.tpg_enabled = False
common_config_obj.config_db = (
    os.path.dirname(__file__) + "/../config/daqsystemtest/example-configs.data.xml"
)

# Get default 1x1 config
onebyone_local_conf = copy.deepcopy(common_config_obj)
onebyone_local_conf.session = "local-1x1-config"

# Get necessary dal objects
db = conffwk.Configuration("oksconflibs:" + str(common_config_obj.config_db))
prescale_bitword = db.get_dal(class_name="TriggerBitword", uid="test-bitword")
timing_bitword = db.get_dal(class_name="TriggerBitword", uid="test-bitword2")

# Prep to turn of tp-stream-writer 
local_conf = db.get_dal(class_name="Session", uid="local-1x1-config")
tpstream_writer = db.get_dal(class_name="TPStreamWriterApplication", uid="tp-stream-writer")
# Append the TPStreamWriter to the disabled list
local_conf.disabled.append(tpstream_writer)
disabled_list = [db.get_dal(class_name=obj.className(), uid=obj.id) for obj in local_conf.disabled]
onebyone_local_conf.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="Session",
        obj_id="local-1x1-config",
        updates={"disabled": []},
    )
)
# Disable TC merging
onebyone_local_conf.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="TCDataProcessor",
        obj_id="def-tc-processor",
        updates={
            "merge_overlapping_tcs": False
            "buffer_timeout": 100},
    )
)

# Prep configs
no_bitword_conf = copy.deepcopy(onebyone_local_conf)
prescale_bitword_conf = copy.deepcopy(onebyone_local_conf)
timing_bitword_conf = copy.deepcopy(onebyone_local_conf)
supernova_bitword_conf = copy.deepcopy(onebyone_local_conf)
series_bitword_conf = copy.deepcopy(onebyone_local_conf)
coincidence_bitword_conf = copy.deepcopy(onebyone_local_conf)

configs = [
    no_bitword_conf,
    prescale_bitword_conf,
    timing_bitword_conf,
    supernova_bitword_conf,
    series_bitword_conf,
    coincidence_bitword_conf]

# Actually disable tp-stream-writer
for conf in configs:
    for sub in conf.config_substitutions:
        if sub.obj_id == "local-1x1-config":
            sub.updates["disabled"] = disabled_list

### Bitwords configs
# Prescale
prescale_bitword_conf.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="TCDataProcessor",
        obj_id="def-tc-processor",
        updates={
            "trigger_bitwords": [prescale_bitword]
            },)
)

# Timing
timing_bitword_conf.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="TCDataProcessor",
        obj_id="def-tc-processor",
        updates={
            "trigger_bitwords": [timing_bitword]
            },)
)

# Supernova
supernova_bitword_conf.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="TriggerBitword",
        obj_id="test-bitword",
        updates={
          "bitword": ["kSupernova"]
        },)
)
supernova_bitword = db.get_dal(class_name="TriggerBitword", uid="test-bitword")
supernova_bitword_conf.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="TCDataProcessor",
        obj_id="def-tc-processor",
        updates={
            "trigger_bitwords": [supernova_bitword]
            },)
)

# Seriers
series_bitword_conf.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="TCDataProcessor",
        obj_id="def-tc-processor",
        updates={
            "trigger_bitwords": [prescale_bitword, timing_bitword]
            },)
)

# Coincidence
coincidence_bitword_conf.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="TriggerBitword",
        obj_id="test-bitword",
        updates={
          "bitword": ["kTiming", "kRandom"]
        },)
)
coincidence_bitword = db.get_dal(class_name="TriggerBitword", uid="test-bitword")
coincidence_bitword_conf.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="TCDataProcessor",
        obj_id="def-tc-processor",
        updates={
            "trigger_bitwords": [coincidence_bitword],
            "merge_overlapping_tcs": True
            },)
)
coincidence_bitword_conf.config_substitutions.append(
    data_classes.config_substitution(
        obj_id="random-tc-generator",
        obj_class="RandomTCMakerConf",
        updates={"trigger_rate_hz": 40},)
)
coincidence_bitword_conf.config_substitutions.append(
    data_classes.config_substitution(
        obj_id="def-random-readout",
        obj_class="TCReadoutMap",
        updates={"time_before": 62500, "time_after": 62500},)
)
coincidence_bitword_conf.config_substitutions.append(
    data_classes.config_substitution(
        obj_id="fakehsi",
        obj_class="FakeHSIEventGeneratorConf",
        updates={"trigger_rate": 30},)
)
coincidence_bitword_conf.config_substitutions.append(
    data_classes.config_substitution(
        obj_id="def-tc-map",
        obj_class="TCReadoutMap",
        updates={"time_before": 62500, "time_after": 62500},)
)
coincidence_bitword_conf.config_substitutions.append(
    data_classes.config_substitution(
        obj_id="def-hsi-tc-map",
        obj_class="TCReadoutMap",
        updates={"time_before": 62500, "time_after": 62500},)
)

# Finally store configs in map
confgen_arguments = { 
  "No bits": no_bitword_conf,
  "Prescale bit": prescale_bitword_conf,
  "Timing bit": timing_bitword_conf,
  "Supernova bit": supernova_bitword_conf,
  "Series bit": series_bitword_conf,
  "Coincidence bit": coincidence_bitword_conf
}

# The commands to run in nanorc, as a list
nanorc_command_list = "boot conf".split()
nanorc_command_list += (
        "start ".split()
        + "--run-number 101 enable-triggers wait ".split()
        + [str(run_duration)]
        + "disable-triggers drain-dataflow wait 2 stop-trigger-sources wait 2 stop wait 2".split()
    )
nanorc_command_list += "scrap terminate".split()

### Tests
# Run control
def test_nanorc_success(run_nanorc):
    current_test = os.environ.get("PYTEST_CURRENT_TEST")

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
        f"{session_name}_ru" in str(logname) for logname in run_nanorc.log_files
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
        "No bits": {"n_data_files": 1, "expected_trigger_types": ["kTiming", "kPrescale", "kRandom"], "multi_required": False},
        "Prescale bit": {"n_data_files": 1, "expected_trigger_types": ["kPrescale"], "multi_required": False},
        "Timing bit": {"n_data_files": 1, "expected_trigger_types": ["kTiming"], "multi_required": False},
        "Supernova bit": {"n_data_files": 0, "expected_trigger_types": [], "multi_required": False},
        "Series bit": {"n_data_files": 1, "expected_trigger_types": ["kTiming", "kPrescale"], "multi_required": False},
        "Coincidence bit": {"n_data_files": 1, "expected_trigger_types": ["kTiming", "kRandom"], "multi_required": True}
    }

    # Match run to checks
    match = re.search(r'\[(.+?)-', current_test)
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

    ## N of data files
    all_ok &= len(run_nanorc.data_files) == selected_params["n_data_files"]

    if all_ok:
        print(f"\N{WHITE HEAVY CHECK MARK} The correct number of raw data files was found ({selected_params['n_data_files']})")
    else:
        print(f"\N{POLICE CARS REVOLVING LIGHT} An incorrect number of raw data files was found, expected {selected_params['n_data_files']}, found {len(run_nanorc.data_files)} \N{POLICE CARS REVOLVING LIGHT}")

    ## Other test
    if selected_params["n_data_files"] > 0:
        data_file = data_file_checks.DataFile(run_nanorc.data_files[0])
        # TR types
        all_ok &= data_file_checks.check_tr_trigger_types(data_file, selected_params['expected_trigger_types'])
        if all_ok:
            print(f"\N{WHITE HEAVY CHECK MARK} All expected TC bits were found ({selected_params['expected_trigger_types']})")
        else:
            print(f"\N{POLICE CARS REVOLVING LIGHT} The extracted TC bits do not correspond to the expected ones! \N{POLICE CARS REVOLVING LIGHT}")

        # TR multiplicity
        all_ok &= data_file_checks.check_tr_type_multiplicity(data_file, selected_params['multi_required'])
        if all_ok:
            print(f"\N{WHITE HEAVY CHECK MARK} The TR type multiplicity was found as expected ({selected_params['multi_required']})")
        else:
            print(f"\N{POLICE CARS REVOLVING LIGHT} The TR type multiplicity is NOT as expected ({selected_params['multi_required']})! \N{POLICE CARS REVOLVING LIGHT}")

    assert all_ok, "\N{POLICE CARS REVOLVING LIGHT} One or more data file checks failed! \N{POLICE CARS REVOLVING LIGHT}"


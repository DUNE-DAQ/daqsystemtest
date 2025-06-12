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
run_duration = 10  # seconds
check_for_logfile_errors = True
expected_number_of_data_files = 1
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
    ]
#    "log_.*": ["connect: Connection refused", "Connection reset by peer", "end of stream"],
}

# Config setup
common_config_obj = data_classes.drunc_config()
common_config_obj.op_env = "test"
common_config_obj.tpg_enabled = False
common_config_obj.config_db = (
    os.path.dirname(__file__) + "/../config/daqsystemtest/example-configs.data.xml"
)

onebyone_local_conf = copy.deepcopy(common_config_obj)
onebyone_local_conf.session = "local-1x1-config"

### Get necessary dal objects
db = conffwk.Configuration("oksconflibs:" + str(common_config_obj.config_db))
prescale_bitword = db.get_dal(class_name="TriggerBitword", uid="test-bitword")
timing_bitword = db.get_dal(class_name="TriggerBitword", uid="test-bitword2")

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

### Prep configs
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
            "buffer_timeout": 100,
            "trigger_bitwords": [prescale_bitword]
            },)
)

# Timing
timing_bitword_conf.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="TCDataProcessor",
        obj_id="def-tc-processor",
        updates={
            "buffer_timeout": 100,
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
            "buffer_timeout": 100,
            "trigger_bitwords": [supernova_bitword]
            },)
)

# Seriers
series_bitword_conf.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="TCDataProcessor",
        obj_id="def-tc-processor",
        updates={
            "buffer_timeout": 100,
            "trigger_bitwords": [prescale_bitword, timing_bitword]
            },)
)

# Coincidence
coincidence_bitword_conf.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="TriggerBitword",
        obj_id="test-bitword",
        updates={
          "bitword": ["kTiming", "kPrescale"]
        },)
)
coincidence_bitword = db.get_dal(class_name="TriggerBitword", uid="test-bitword")
coincidence_bitword_conf.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="TCDataProcessor",
        obj_id="def-tc-processor",
        updates={
            "buffer_timeout": 100,
            "trigger_bitwords": [coincidence_bitword]
            },)
)

confgen_arguments = { 
  "No bits": no_bitword_conf,
  "Prescale bit": prescale_bitword_conf,
  "Timing bit": timing_bitword_conf,
  "Supernova bit": supernova_bitword_conf,
  "Series bit": series_bitword_conf,
  "Coincidence bit": coincidence_bitword_conf
}

##### OVERWRITE FOR TESTING #####
confgen_arguments = {
  "No bits": no_bitword_conf,
  "Prescale bit": prescale_bitword_conf
}

# The commands to run in nanorc, as a list
nanorc_command_list = "boot conf".split()
nanorc_command_list += (
        "start ".split()
        + "--run-number 101 wait 2 enable-triggers wait ".split()
        + [str(run_duration)]
        + "disable-triggers wait 2 drain-dataflow wait 2 stop-trigger-sources stop wait 2".split()
    )
nanorc_command_list += "scrap terminate".split()

# Tests
def test_nanorc_success(run_nanorc):
    current_test = os.environ.get("PYTEST_CURRENT_TEST")

    # Check that nanorc completed correctly
    assert run_nanorc.completed_process.returncode == 0

def test_log_files(run_nanorc):
    current_test = os.environ.get("PYTEST_CURRENT_TEST")
    
    session_name = run_nanorc.session_name if run_nanorc.session_name is not None else run_nanorc.session

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

    datafile_params = {
        "No bits": {"expected_trigger_types": ["kTiming", "kPrescale"], "min_tr_count": 1, "max_tr_count": 100, "multi_required": 0},
        "Prescale bit": {"expected_trigger_types": ["kPrescale"], "min_tr_count": 1, "max_tr_count": 100, "multi_required": 0},
        "Timing bit": {"expected_trigger_types": ["kTiming"], "min_tr_count": 1, "max_tr_count": 100, "multi_required": 0},
        "Supernova bit": {"expected_trigger_types": [], "min_tr_count": 0, "max_tr_count": 0, "multi_required": 0},
        "Series bit": {"expected_trigger_types": ["kTiming", "kPrescale"], "min_tr_count": 1, "max_tr_count": 100, "multi_required": 0},
        "Coincidence bit": {"expected_trigger_types": ["kTiming", "kPrescale"], "min_tr_count": 1, "max_tr_count": 100, "multi_required": 1}
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

    # Run some tests on the output data file
    all_ok = True
    
    ## N of data files
    all_ok &= len(run_nanorc.data_files) == expected_number_of_data_files

    if all_ok:
        print(f"\N{WHITE HEAVY CHECK MARK} The correct number of raw data files was found ({expected_number_of_data_files})")
    else:
        print(f"\N{POLICE CARS REVOLVING LIGHT} An incorrect number of raw data files was found, expected {expected_number_of_data_files}, found {len(run_nanorc.data_files)} \N{POLICE CARS REVOLVING LIGHT}")

    ## Other
        

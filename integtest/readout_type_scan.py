import pytest
import os
import re
import copy
import urllib.request

import integrationtest.data_file_checks as data_file_checks
import integrationtest.log_file_checks as log_file_checks
import integrationtest.data_classes as data_classes

pytest_plugins = "integrationtest.integrationtest_drunc"

# Don't require frames file
frame_file_required = False

# Values that help determine the running conditions
number_of_data_producers = 2
run_duration = 20  # seconds
data_rate_slowdown_factor = 10
ta_prescale = 100

# Default values for validation parameters
expected_number_of_data_files = 1
check_for_logfile_errors = True
expected_event_count = run_duration
expected_event_count_tolerance = 2

wibeth_frag_params = {
    "fragment_type_description": "WIBEth",
    "fragment_type": "WIBEth",
    "hdf5_source_subsystem": "Detector_Readout",
    "expected_fragment_count": number_of_data_producers,
    "min_size_bytes": 7272,
    "max_size_bytes": 14472,
}
wibeth_frag_multi_trig_params = {
    "fragment_type_description": "WIBEth",
    "fragment_type": "WIBEth",
    "hdf5_source_subsystem": "Detector_Readout",
    "expected_fragment_count": number_of_data_producers,
    "min_size_bytes": 7272,
    "max_size_bytes": 14472,
}
tde_frag_params = {
    "fragment_type_description": "TDEEth",
    "fragment_type": "TDEEth",
    "hdf5_source_subsystem": "Detector_Readout",
    "expected_fragment_count": number_of_data_producers,
    "min_size_bytes": 7272,
    "max_size_bytes": 14472,
}

# 1ms readout window = 62512 DTS ticks
# num frames = ro_win / tick diff = 977
# fragment size = num frames * frame size = 461026

pds_stream_frag_params = {
    "fragment_type_description": "PDSStream",
    "fragment_type": "DAPHNEStream",
    "hdf5_source_subsystem": "Detector_Readout",
    "expected_fragment_count": number_of_data_producers,
    "min_size_bytes": 72+461026-20*472,
    "max_size_bytes": 72+461026+20*472,
}  
pds_frag_params = {
    "fragment_type_description": "PDS",
    "fragment_type": "DAPHNE",
    "hdf5_source_subsystem": "Detector_Readout",
    "expected_fragment_count": number_of_data_producers,
    "min_size_bytes": 435912,
    "max_size_bytes": 1133256,
}  # 20 x 21792; 52 x 21792 (+72)
triggercandidate_frag_params = {
    "fragment_type_description": "Trigger Candidate",
    "fragment_type": "Trigger_Candidate",
    "hdf5_source_subsystem": "Trigger",
    "expected_fragment_count": 1,
    "min_size_bytes": 120,
    "max_size_bytes": 150,
}
triggeractivity_frag_params = {
    "fragment_type_description": "Trigger Activity",
    "fragment_type": "Trigger_Activity",
    "hdf5_source_subsystem": "Trigger",
    "expected_fragment_count": 1,
    "min_size_bytes": 72,
    "max_size_bytes": 400,
}
triggertp_frag_params = {
    "fragment_type_description": "Trigger with TPs",
    "fragment_type": "Trigger_Primitive",
    "hdf5_source_subsystem": "Trigger",
    "expected_fragment_count": (3 * 1), # number_of_readout_apps
    "min_size_bytes": 72,
    "max_size_bytes": 16000,
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

# The next three variable declarations *must* be present as globals in the test
# file. They're read by the "fixtures" in conftest.py to determine how
# to run the config generation and nanorc

object_databases = ["config/daqsystemtest/integrationtest-objects.data.xml"]

conf_dict = data_classes.drunc_config()
conf_dict.dro_map_config.n_streams = number_of_data_producers
conf_dict.op_env = "integtest"
conf_dict.session = "readout"
conf_dict.tpg_enabled = False
conf_dict.frame_file = "asset://?label=ProtoWIB&subsystem=readout"  # ProtoWIB

conf_dict.config_substitutions.append(
    data_classes.config_substitution(
        obj_id=conf_dict.session,
        obj_class="Session",
        updates={"data_rate_slowdown_factor": data_rate_slowdown_factor},
    )
)
conf_dict.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="RandomTCMakerConf",
        updates={"trigger_rate_hz": 1},
    )
)

tpg_conf = copy.deepcopy(conf_dict)
tpg_conf.tpg_enabled = True
tpg_conf.frame_file = (
    "asset://?checksum=dd156b4895f1b06a06b6ff38e37bd798"  # WIBEth All Zeros
)
tpg_conf.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="TAMakerPrescaleAlgorithm",
        obj_id="dummy-ta-maker",
        updates={"prescale": ta_prescale},
    )
)

wibeth_conf = copy.deepcopy(conf_dict)
# wibeth_conf.frame_file = "asset://?label=WIBEth&subsystem=readout"
wibeth_conf.frame_file = "asset://?checksum=dd156b4895f1b06a06b6ff38e37bd798"

tde_conf = copy.deepcopy(conf_dict)
tde_conf.dro_map_config.det_id = 11
tde_conf.frame_file = "asset://?checksum=dd156b4895f1b06a06b6ff38e37bd798" # WIBEth All Zeros
#tde_conf.frame_file = "asset://?checksum=759e5351436bead208cf4963932d6327"

pds_stream_conf = copy.deepcopy(conf_dict)
pds_stream_conf.dro_map_config.det_id = 2  # det_id = 2 for HD_PDS
pds_stream_conf.frame_file = "asset://?label=DAPHNEStream&subsystem=readout"

pds_stream_conf.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="TCReadoutMap",
        obj_id = "def-random-readout",
        updates={
            "time_before": 62000,
            "time_after": 500,
        },
    )
)

pds_conf = copy.deepcopy(conf_dict)
pds_conf.dro_map_config.det_id = 2  # det_id = 2 for HD_PDS
pds_conf.frame_file = "asset://?label=DAPHNE&subsystem=readout"
pds_conf.config_substitutions.append(
    data_classes.config_substitution(
        obj_class="TCReadoutMap",
        obj_id = "def-random-readout",
        updates={
            "time_before": 62000,
            "time_after": 500,
        },
    )
)
# pacman_conf = copy.deepcopy(conf_dict)
# pacman_conf.dro_map_config.det_id  = 32  # det_id = 32 for NDLAr_TPC
# pacman_conf.frame_file == "asset://?label=PACMAN&subsystem=readout"

# mpd_conf = copy.deepcopy(conf_dict)
# mpd_conf.dro_map_config.det_id  = 33  # det_id = 33 for NDLAr_PDS
# mpd_conf.frame_file = "asset://?label=MPD&subsystem=readout"


confgen_arguments = {
    # "WIB1_System": wib1_conf,
    "WIBEth_System": wibeth_conf,
    "TPG_System": tpg_conf,
    "PDS_Stream_System": pds_stream_conf,
    # "PDS_System": pds_conf,
    "TDEEth_System": tde_conf,
    # "PACMAN_System": pacman_conf,
    # "MPD_System": mpd_conf
}

# The commands to run in nanorc, as a list
nanorc_command_list = (
    "boot conf start --run-number 101 wait 2 enable-triggers wait ".split()
    + [str(run_duration)]
    + "disable-triggers wait 2 drain-dataflow stop-trigger-sources wait 2 stop scrap terminate".split()
)

# The tests themselves


def test_nanorc_success(run_nanorc):
    current_test = os.environ.get("PYTEST_CURRENT_TEST")
    match_obj = re.search(r".*\[(.+)\].*", current_test)
    if match_obj:
        current_test = match_obj.group(1)
    banner_line = re.sub(".", "=", current_test)
    print(banner_line)
    print(current_test)
    print(banner_line)
    # Check that nanorc completed correctly
    assert run_nanorc.completed_process.returncode == 0


def test_log_files(run_nanorc):
    local_check_flag = check_for_logfile_errors

    if local_check_flag:
        # Check that there are no warnings or errors in the log files
        assert log_file_checks.logs_are_error_free(
            run_nanorc.log_files, True, True, ignored_logfile_problems
        )


def test_data_files(run_nanorc):
    local_expected_event_count = expected_event_count
    local_event_count_tolerance = expected_event_count_tolerance
    fragment_check_list = []
    if run_nanorc.confgen_config.tpg_enabled:
        local_expected_event_count += (
            (6250 / ta_prescale)
            * number_of_data_producers
            * run_duration
            / 100
        )
        local_event_count_tolerance += (
            (250 / ta_prescale)
            * number_of_data_producers
            * run_duration
            / 100
        )
        fragment_check_list.append(wibeth_frag_multi_trig_params)
        fragment_check_list.append(triggeractivity_frag_params)
        fragment_check_list.append(triggertp_frag_params)
    else:
        fragment_check_list.append(triggercandidate_frag_params)
        current_test = os.environ.get("PYTEST_CURRENT_TEST")
        if "PDS_Stream" in current_test:
            fragment_check_list.append(pds_stream_frag_params)
        elif "PDS" in current_test:
            fragment_check_list.append(pds_frag_params)
        elif "WIBEth" in current_test:
            fragment_check_list.append(wibeth_frag_params)
        elif "TDEEth" in current_test:
            fragment_check_list.append(tde_frag_params)

    # Run some tests on the output data file
    all_ok = True
    all_ok &= len(run_nanorc.data_files) == expected_number_of_data_files

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

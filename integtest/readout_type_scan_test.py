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
data_rate_slowdown_factor = 10  # is this still used anywhere?  (KAB, 28-Apr-2050)
ta_prescale = 100

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
tde_frag_params = {
    "fragment_type_description": "TDEEth",
    "fragment_type": "TDEEth",
    "expected_fragment_count": number_of_data_producers,
    "min_size_bytes": 7272,
    "max_size_bytes": 14472,
}
bern_crt_frag_params = {
    "fragment_type_description": "CRTBern",
    "fragment_type": "CRTBern",
    "expected_fragment_count": number_of_data_producers,
    "min_size_bytes": 384,
    "max_size_bytes": 488,
}
grenoble_crt_frag_params = {
    "fragment_type_description": "CRTGrenoble",
    "fragment_type": "CRTGrenoble",
    "expected_fragment_count": number_of_data_producers,
    "min_size_bytes": 1752,
    "max_size_bytes": 2312,
}

# 1ms readout window = 62512 DTS ticks
# num frames = ro_win / tick diff = 977
# fragment size = num frames * frame size = 461026

daphne_stream_frag_params = {
    "fragment_type_description": "DAPHNEStream",
    "fragment_type": "DAPHNEStream",
    "expected_fragment_count": number_of_data_producers,
    "min_size_bytes": 72+461026-20*472,
    "max_size_bytes": 72+461026+20*472,
}  
daphne_frag_params = {
    "fragment_type_description": "DAPHNE",
    "fragment_type": "DAPHNE",
    "expected_fragment_count": number_of_data_producers,
    "min_size_bytes": 1936,
    "max_size_bytes": 120000,
    "frag_sizes_by_TC_type": {"kPrescale": {"min_size_bytes":   1936, "max_size_bytes":  32000},
                                "kRandom": {"min_size_bytes": 112000, "max_size_bytes": 118000},
                                "default": {"min_size_bytes":   1936, "max_size_bytes": 118000} }
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
wibeth_triggerprimitive_frag_params = {
    "fragment_type_description": "Trigger Primitive",
    "fragment_type": "Trigger_Primitive",
    "expected_fragment_count": (1 * 3),  # number of readout apps * 3
    "min_size_bytes": 72,
    "max_size_bytes": 144,
}
daphne_triggerprimitive_frag_params = {
    "fragment_type_description": "Trigger Primitive",
    "fragment_type": "Trigger_Primitive",
    "expected_fragment_count": 1,  # number of readout apps
    "min_size_bytes": 96,
    "max_size_bytes": 4392,
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
    data_classes.attribute_substitution(
        obj_id=conf_dict.session,
        obj_class="Session",
        updates={"data_rate_slowdown_factor": data_rate_slowdown_factor},
    )
)
conf_dict.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="RandomTCMakerConf",
        updates={"trigger_rate_hz": 1},
    )
)

wib_tpg_conf = copy.deepcopy(conf_dict)
wib_tpg_conf.tpg_enabled = True
wib_tpg_conf.frame_file = (
    "asset://?checksum=dd156b4895f1b06a06b6ff38e37bd798"  # WIBEth All Zeros
)
wib_tpg_conf.config_substitutions.append(
    data_classes.attribute_substitution(
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

daphne_stream_conf = copy.deepcopy(conf_dict)
daphne_stream_conf.dro_map_config.det_id = 2  # det_id = 2 for HD_PDS
daphne_stream_conf.frame_file = "asset://?label=DAPHNEStream&subsystem=readout"

daphne_stream_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="TCReadoutMap",
        obj_id = "def-random-readout",
        updates={
            "time_before": 62000,
            "time_after": 500,
        },
    )
)

daphne_conf = copy.deepcopy(conf_dict)
daphne_conf.dro_map_config.det_id = 2  # det_id = 2 for HD_PDS
daphne_conf.frame_file = "asset://?checksum=a8990a9eb3a505d4ded62dfdfa9e2681"
daphne_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="TCReadoutMap",
        obj_id = "def-random-readout",
        updates={
            "time_before": 62000,
            "time_after": 500,
        },
    )
)

daphne_tpg_conf = copy.deepcopy(daphne_conf)
daphne_tpg_conf.tpg_enabled = True
daphne_tpg_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="TAMakerPrescaleAlgorithm",
        obj_id="dummy-ta-maker",
        updates={"prescale": 750},
    )
)

bern_crt_conf = copy.deepcopy(conf_dict)
bern_crt_conf.dro_map_config.det_id = 12
bern_crt_conf.frame_file = "asset://?checksum=dd156b4895f1b06a06b6ff38e37bd798" # WIBEth All Zeros

grenoble_crt_conf = copy.deepcopy(conf_dict)
grenoble_crt_conf.dro_map_config.det_id = 13
grenoble_crt_conf.frame_file = "asset://?checksum=dd156b4895f1b06a06b6ff38e37bd798" # WIBEth All Zeros


confgen_arguments = {
    "WIBEth_System": wibeth_conf,
    "WIBEth_TPG_System": wib_tpg_conf,
    "DAPHNE_Stream_System": daphne_stream_conf,
    "DAPHNE_System": daphne_conf,
    "DAPHNE_TPG_System": daphne_tpg_conf,
    "TDEEth_System": tde_conf,
    "BernCRT_System": bern_crt_conf,
    "GrenobleCRT_System": grenoble_crt_conf
}

# The commands to run in nanorc, as a list
nanorc_command_list = (
    "boot conf start --run-number 101 wait 2 enable-triggers wait ".split()
    + [str(run_duration)]
    + "disable-triggers wait 2 drain-dataflow stop-trigger-sources wait 2 stop scrap terminate".split()
)
#    + "disable-triggers wait 5 drain-dataflow wait 2 stop-trigger-sources wait 2 stop scrap terminate".split()

# The tests themselves


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
    fragment_check_list = [triggercandidate_frag_params]
    current_test = os.environ.get("PYTEST_CURRENT_TEST")
    if "DAPHNE_Stream" in current_test:
        fragment_check_list.append(daphne_stream_frag_params)
    elif "DAPHNE" in current_test:
        fragment_check_list.append(daphne_frag_params)
    elif "WIBEth" in current_test:
        fragment_check_list.append(wibeth_frag_params)
    elif "TDEEth" in current_test:
        fragment_check_list.append(tde_frag_params)
    elif "BernCRT" in current_test:
        fragment_check_list.append(bern_crt_frag_params)
    elif "GrenobleCRT" in current_test:
        fragment_check_list.append(grenoble_crt_frag_params)
    if run_nanorc.confgen_config.tpg_enabled:
        fragment_check_list.append(triggeractivity_frag_params)
        if "WIBEth" in current_test:
            fragment_check_list.append(wibeth_triggerprimitive_frag_params)
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
        if "DAPHNE" in current_test:
            fragment_check_list.append(daphne_triggerprimitive_frag_params)
            local_expected_event_count += (
                (6250 / ta_prescale)
                * number_of_data_producers
                * run_duration * 3
                / 200
            )
            local_event_count_tolerance += (
                (250 / ta_prescale)
                * number_of_data_producers
                * run_duration * 6
                / 250
            )

    # Run some tests on the output data file
    all_ok = True
    all_ok &= len(run_nanorc.data_files) == expected_number_of_data_files
    print("") # Clear potential dot from pytest
    if all_ok:
        print(f"\N{WHITE HEAVY CHECK MARK} The correct number of raw data files was found ({expected_number_of_data_files})")
    else:
        print(f"\N{POLICE CARS REVOLVING LIGHT} An incorrect number of raw data files was found, expected {expected_number_of_data_files}, found {len(run_nanorc.data_files)} \N{POLICE CARS REVOLVING LIGHT}")

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

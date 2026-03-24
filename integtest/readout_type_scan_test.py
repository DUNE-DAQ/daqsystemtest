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
run_duration = 20  # seconds
data_rate_slowdown_factor = 10  # is this still used anywhere?  (KAB, 28-Apr-2050)

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
    "min_size_bytes": 14472,  # 19-Feb-2026, KAB: the time span of a TDEEth frame is 2000 ticks
    "max_size_bytes": 21672,  # With a readout window of 2005 ticks, we'll get 2 or 3 frames
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

# DAPHNEEthStreamFrame: DAQEthHeader(16) + Header(4 x uint64 = 32) + ADC(4ch x 280smp x 14bit/64 = 245 x 8 = 1960) = 2008 bytes/frame
# 1ms readout window = 62512 DTS ticks
# num frames = ro_win / tick diff = 62512/280 = 223 (approximately)
# fragment size = num frames * frame size = 223 * 2008 = 447784
daphne_eth_stream_frag_params = {
    "fragment_type_description": "DAPHNEEthStream",
    "fragment_type": "DAPHNEEthStream",
    "expected_fragment_count": number_of_data_producers,
    "min_size_bytes": 72+447784-20*2008,
    "max_size_bytes": 72+447784+20*2008,
}

# DAPHNEEthFrame: DAQEthHeader(16) + Header(7 x uint64 = 56) + ADC(1024smp x 14bit/64 = 224 x 8 = 1792) = 1864 bytes/frame
# Same frame size as DAPHNEFrame, so fragment size ranges are identical
daphne_eth_frag_params = {
    "fragment_type_description": "DAPHNEEth",
    "fragment_type": "DAPHNEEth",
    "expected_fragment_count": number_of_data_producers,
    "min_size_bytes": 1936,
    "max_size_bytes": 120000,
    "frag_sizes_by_TC_type": {"kPrescale": {"min_size_bytes":   1936, "max_size_bytes":  32000},
                                "kRandom": {"min_size_bytes": 112000, "max_size_bytes": 118000},
                                "default": {"min_size_bytes":   1936, "max_size_bytes": 118000} }
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
tdeeth_triggerprimitive_frag_params = {
    "fragment_type_description": "Trigger Primitive",
    "fragment_type": "Trigger_Primitive",
    "expected_fragment_count": (1 * 3),  # number of readout apps * 3
    "min_size_bytes": 72,
    "max_size_bytes": 144,
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
resource_validator.cpu_count_needs(8, 16)  # 3 for each data source (incl TPG) plus 2 more for everything else
resource_validator.free_memory_needs(6, 10)  # 20% more than what we observe being used ('free -h')
actual_output_path = get_pytest_tmpdir()
resource_validator.free_disk_space_needs(actual_output_path, 1)  # more than what we observe
resval_debug_string = resource_validator.get_debug_string()
print(f"{resval_debug_string}")

# The next three variable declarations *must* be present as globals in the test
# file. They're read by the "fixtures" in conftest.py to determine how
# to run the config generation and dunerc

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
        updates={"prescale": 100},
    )
)

wibeth_conf = copy.deepcopy(conf_dict)
wibeth_conf.frame_file = "asset://?checksum=dd156b4895f1b06a06b6ff38e37bd798" # WIBEth All Zeros

tde_conf = copy.deepcopy(conf_dict)
tde_conf.dro_map_config.det_id = 11
tde_conf.dro_map_config.crate_id_offset = 5
tde_conf.dro_map_config.slot_id = 3
tde_conf.frame_file = "asset://?checksum=1793479772dfef8cb23a071a7383520b"
tde_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="TPCRawDataProcessor",
        obj_id="def-wib-processor",
        updates={"channel_map": "PD2VDTPCChannelMap"},
    )
)

tde_tpg_conf = copy.deepcopy(tde_conf)
tde_tpg_conf.tpg_enabled = True
tde_tpg_conf.config_substitutions.append(
    data_classes.list_element_addition(
        obj_class="TCDataProcessor",
        obj_id="def-tc-processor",
        rel_name="tc_readout_map",
        additional_object_class="TCReadoutMap",
        additional_object_id="prescale-tc-map-entry",
    )
)
tde_tpg_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="AVXThresholdProcessor",
        obj_id="tpg-threshold-proc",
        updates={"plane0": 500, "plane1": 500, "plane2": 500},
    )
)
tde_tpg_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="TAMakerPrescaleAlgorithm",
        obj_id="dummy-ta-maker",
        updates={"prescale": 100},
    )
)
tde_tpg_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="GeoId",
        obj_id="geioId-1",
        updates={"slot_id": 4, "stream_id": 0},
    )
)

daphne_stream_conf = copy.deepcopy(conf_dict)
daphne_stream_conf.dro_map_config.det_id = 2  # det_id = 2 for HD_PDS
daphne_stream_conf.frame_file = "asset://?label=DAPHNEStream&subsystem=readout"

daphne_stream_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="RandomTCMakerConf",
        obj_id = "random-tc-generator",
        updates={
            "candidate_backshift_ts": 0,
            "candidate_window_before_ts": 62000,
            "candidate_window_after_ts": 500,
        },
    )
)

daphne_eth_stream_conf = copy.deepcopy(conf_dict)
daphne_eth_stream_conf.dro_map_config.det_id = 2  # det_id = 2 for HD_PDS
daphne_eth_stream_conf.use_fakedataprod = True
daphne_eth_stream_conf.fake_data_fragment_type = "DAPHNEEthStream"
# TODO: replace use_fakedataprod with asset file once one exists
# daphne_eth_stream_conf.frame_file = "asset://?label=DAPHNEEthStream&subsystem=readout"

daphne_eth_stream_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="RandomTCMakerConf",
        obj_id = "random-tc-generator",
        updates={
            "candidate_backshift_ts": 0,
            "candidate_window_before_ts": 62000,
            "candidate_window_after_ts": 500,
        },
    )
)

daphne_conf = copy.deepcopy(conf_dict)
daphne_conf.dro_map_config.det_id = 2  # det_id = 2 for HD_PDS
daphne_conf.frame_file = "asset://?checksum=a8990a9eb3a505d4ded62dfdfa9e2681" # np02vd_run036012_sample_membrane_pds
daphne_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="RandomTCMakerConf",
        obj_id = "random-tc-generator",
        updates={
            "candidate_backshift_ts": 0,
            "candidate_window_before_ts": 62000,
            "candidate_window_after_ts": 500,
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

daphne_eth_conf = copy.deepcopy(conf_dict)
daphne_eth_conf.dro_map_config.det_id = 2  # det_id = 2 for HD_PDS
daphne_eth_conf.use_fakedataprod = True
daphne_eth_conf.fake_data_fragment_type = "DAPHNEEth"
# TODO: replace use_fakedataprod with asset file once one exists
# daphne_eth_conf.frame_file = "asset://?label=DAPHNEEth&subsystem=readout"
daphne_eth_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="RandomTCMakerConf",
        obj_id = "random-tc-generator",
        updates={
            "candidate_backshift_ts": 0,
            "candidate_window_before_ts": 62000,
            "candidate_window_after_ts": 500,
        },
    )
)

daphne_eth_tpg_conf = copy.deepcopy(daphne_eth_conf)
daphne_eth_tpg_conf.tpg_enabled = True
daphne_eth_tpg_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="TAMakerPrescaleAlgorithm",
        obj_id="dummy-ta-maker",
        updates={"prescale": 750},
    )
)

bern_crt_conf = copy.deepcopy(conf_dict)
bern_crt_conf.dro_map_config.det_id = 12
bern_crt_conf.frame_file = "asset://?checksum=dd156b4895f1b06a06b6ff38e37bd798" # WIBEth All Zeros
bern_crt_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="RandomTCMakerConf",
        obj_id="random-tc-generator",
        updates={"candidate_window_before_ts": 8000, "candidate_window_after_ts": 10},
    )
)

grenoble_crt_conf = copy.deepcopy(conf_dict)
grenoble_crt_conf.dro_map_config.det_id = 13
grenoble_crt_conf.frame_file = "asset://?checksum=dd156b4895f1b06a06b6ff38e37bd798" # WIBEth All Zeros
grenoble_crt_conf.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="RandomTCMakerConf",
        obj_id="random-tc-generator",
        updates={"candidate_window_before_ts": 8000, "candidate_window_after_ts": 10},
    )
)

confgen_arguments = {
    "WIBEth_System": wibeth_conf,
    "WIBEth_TPG_System": wib_tpg_conf,
    "DAPHNE_Stream_System": daphne_stream_conf,
    "DAPHNEEthStream_System": daphne_eth_stream_conf,
    "DAPHNE_System": daphne_conf,
    "DAPHNE_TPG_System": daphne_tpg_conf,
    "DAPHNEEth_System": daphne_eth_conf,
    # TODO: re-enable once realistic asset file exists for DAPHNEEth
    # "DAPHNEEth_TPG_System": daphne_eth_tpg_conf,
    "TDEEth_System": tde_conf,
    "TDEEth_TPG_System": tde_tpg_conf,
    "BernCRT_System": bern_crt_conf,
    "GrenobleCRT_System": grenoble_crt_conf
}

# The commands to run in dunerc, as a list
dunerc_command_list = (
    "boot conf start --run-number 101 wait 2 enable-triggers wait ".split()
    + [str(run_duration)]
    + "disable-triggers wait 2 drain-dataflow stop-trigger-sources wait 2 stop scrap terminate".split()
)
#    + "disable-triggers wait 5 drain-dataflow wait 2 stop-trigger-sources wait 2 stop scrap terminate".split()


# The tests themselves

def test_dunerc_success(run_dunerc):
    # print the name of the current test
    current_test = os.environ.get("PYTEST_CURRENT_TEST")
    match_obj = re.search(r".*\[(.+)-run_.*rc.*\d].*", current_test)
    if match_obj:
        current_test = match_obj.group(1)
    banner_line = re.sub(".", "=", current_test)
    print(banner_line)
    print(current_test)
    print(banner_line)

    # Check that dunerc completed correctly
    assert run_dunerc.completed_process.returncode == 0


def test_log_files(run_dunerc):
    if check_for_logfile_errors:
        # Check that there are no warnings or errors in the log files
        assert log_file_checks.logs_are_error_free(
            run_dunerc.log_files, True, True, ignored_logfile_problems
        )


def test_data_files(run_dunerc):
    local_expected_event_count = expected_event_count
    local_event_count_tolerance = expected_event_count_tolerance
    fragment_check_list = [triggercandidate_frag_params]
    current_test = os.environ.get("PYTEST_CURRENT_TEST")
    if "DAPHNE_Stream" in current_test:
        fragment_check_list.append(daphne_stream_frag_params)
    elif "DAPHNEEthStream" in current_test:
        fragment_check_list.append(daphne_eth_stream_frag_params)
    elif "DAPHNEEth" in current_test:
        fragment_check_list.append(daphne_eth_frag_params)
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
    if run_dunerc.confgen_config.tpg_enabled:
        fragment_check_list.append(triggeractivity_frag_params)
        if "WIBEth" in current_test:
            fragment_check_list.append(wibeth_triggerprimitive_frag_params)
            local_expected_event_count += (
                0.625
                * number_of_data_producers
                * run_duration
            )
            local_event_count_tolerance += (
                0.025
                * number_of_data_producers
                * run_duration
            )
        if "DAPHNEEth" in current_test or "DAPHNE" in current_test:
            fragment_check_list.append(daphne_triggerprimitive_frag_params)
            local_expected_event_count += (
                0.3125
                * number_of_data_producers
                * run_duration * 3
            )
            local_event_count_tolerance += (
                0.01
                * number_of_data_producers
                * run_duration * 6
            )
        if "TDEEth" in current_test:
            fragment_check_list.append(tdeeth_triggerprimitive_frag_params)
            local_expected_event_count += (
                0.70
                * number_of_data_producers
                * run_duration
            )
            local_event_count_tolerance += (
                0.025
                * number_of_data_producers
                * run_duration
            )

    # Run some tests on the output data file
    all_ok = True
    all_ok &= len(run_dunerc.data_files) == expected_number_of_data_files
    print("") # Clear potential dot from pytest
    if all_ok:
        print(f"\N{WHITE HEAVY CHECK MARK} The correct number of raw data files was found ({expected_number_of_data_files})")
    else:
        print(f"\N{POLICE CARS REVOLVING LIGHT} An incorrect number of raw data files was found, expected {expected_number_of_data_files}, found {len(run_dunerc.data_files)} \N{POLICE CARS REVOLVING LIGHT}")

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

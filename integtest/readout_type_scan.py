import pytest
import os
import re
import copy
import urllib.request

import dfmodules.data_file_checks as data_file_checks
import integrationtest.log_file_checks as log_file_checks
import integrationtest.config_file_gen as config_file_gen
import dfmodules.integtest_file_gen as integtest_file_gen

# Don't require frames file
frame_file_required=False

# Values that help determine the running conditions
number_of_data_producers=2
run_duration=20  # seconds
data_rate_slowdown_factor=10

# Default values for validation parameters
expected_number_of_data_files=1
check_for_logfile_errors=True
expected_event_count=run_duration
expected_event_count_tolerance=2
wib1_frag_hsi_trig_params={"fragment_type_description": "WIB", 
                           "fragment_type": "ProtoWIB",
                           "hdf5_source_subsystem": "Detector_Readout",
                           "expected_fragment_count": number_of_data_producers,
                           "min_size_bytes": 37192, "max_size_bytes": 37656}
wib1_frag_multi_trig_params={"fragment_type_description": "WIB",
                             "fragment_type": "ProtoWIB",
                             "hdf5_source_subsystem": "Detector_Readout",
                             "expected_fragment_count": number_of_data_producers,
                             "min_size_bytes": 72, "max_size_bytes": 54000}
wib2_frag_params={"fragment_type_description": "WIB2",
                  "fragment_type": "WIB",
                  "hdf5_source_subsystem": "Detector_Readout",
                  "expected_fragment_count": number_of_data_producers,
                  "min_size_bytes": 29808, "max_size_bytes": 30280}
wibeth_frag_params={"fragment_type_description": "WIBEth",
                  "fragment_type": "WIBEth",
                  "hdf5_source_subsystem": "Detector_Readout",
                  "expected_fragment_count": number_of_data_producers,
                  "min_size_bytes": 7272, "max_size_bytes": 14472}
tde_frag_params={"fragment_type_description": "TDE",
                  "fragment_type": "TDE_AMC",
                  "hdf5_source_subsystem": "Detector_Readout",
                  "expected_fragment_count": number_of_data_producers,
                  "min_size_bytes": 575048, "max_size_bytes": 575048}
pds_stream_frag_params={"fragment_type_description": "PDSStream",
                        "fragment_type": "DAPHNEStream",
                        "hdf5_source_subsystem": "Detector_Readout",
                        "expected_fragment_count": number_of_data_producers,
                        "min_size_bytes": 118072, "max_size_bytes": 306872}  # 250 x 472; 650 * 472 (+72)
pds_frag_params={"fragment_type_description": "PDS",
                 "fragment_type": "DAPHNE",
                 "hdf5_source_subsystem": "Detector_Readout",
                 "expected_fragment_count": number_of_data_producers,
                 "min_size_bytes": 479496, "max_size_bytes": 1198632}  # 22 x 21792; 55 x 21792 (+72)
triggercandidate_frag_params={"fragment_type_description": "Trigger Candidate",
                              "fragment_type": "Trigger_Candidate",
                              "hdf5_source_subsystem": "Trigger",
                              "expected_fragment_count": 1,
                              "min_size_bytes": 120, "max_size_bytes": 150}
triggertp_frag_params={"fragment_type_description": "Trigger with TPs",
                       "fragment_type": "Trigger_Primitive",
                       "hdf5_source_subsystem": "Trigger",
                       "expected_fragment_count": number_of_data_producers,
                       "min_size_bytes": 72, "max_size_bytes": 16000}
ignored_logfile_problems={"dqm": ["client will not be able to connect to Kafka cluster",
                                  "Unexpected Trigger Decision", "Unexpected Fragment"],
                          "trigger": ["zipped_tpset_q: Unable to push within timeout period"],
                          "rulocalhost": ["Configuration Error: Binary file contains more data than expected"],
                         }

# The next three variable declarations *must* be present as globals in the test
# file. They're read by the "fixtures" in conftest.py to determine how
# to run the config generation and nanorc

# The name of the python module for the config generation
confgen_name="daqconf_multiru_gen"
# The arguments to pass to the config generator, excluding the json
# output directory (the test framework handles that)
dro_map_contents = integtest_file_gen.generate_dromap_contents(n_streams=number_of_data_producers, det_id = 3) # default HD_TPC

conf_dict = config_file_gen.get_default_config_dict()
conf_dict["readout"]["dro_map"] = dro_map_contents
conf_dict["daq_common"]["data_rate_slowdown_factor"] = data_rate_slowdown_factor
conf_dict["readout"]["default_data_file"] = "asset://?label=ProtoWIB&subsystem=readout"
conf_dict["readout"]["use_fake_cards"] = True
conf_dict["trigger"]["trigger_window_before_ticks"] = 1000
conf_dict["trigger"]["trigger_window_after_ticks"] = 1000

swtpg_conf = copy.deepcopy(conf_dict)
swtpg_conf["readout"]["enable_tpg"] = True
swtpg_conf["detector"]["clock_speed_hz"] = 50000000
swtpg_conf["readout"]["default_data_file"] = "asset://?label=ProtoWIB&subsystem=readout"

dqm_conf = copy.deepcopy(conf_dict)
dqm_conf["dqm"]["enable_dqm"] = True
dqm_conf["detector"]["clock_speed_hz"] = 62500000
dqm_conf["readout"]["default_data_file"] = "asset://?label=DuneWIB&subsystem=readout"
dqm_conf["readout"]["dro_map"] = integtest_file_gen.generate_dromap_contents(n_streams=number_of_data_producers, det_id=3, app_type='flx')

wib1_conf = copy.deepcopy(conf_dict)
wib1_conf["detector"]["clock_speed_hz"] = 50000000
wib1_conf["readout"]["default_data_file"] = "asset://?label=ProtoWIB&subsystem=readout"

wib2_conf = copy.deepcopy(conf_dict)
wib2_conf["readout"]["dro_map"] = integtest_file_gen.generate_dromap_contents(n_streams=number_of_data_producers, det_id=3, app_type='flx')
wib2_conf["detector"]["clock_speed_hz"] = 62500000
wib2_conf["readout"]["default_data_file"] = "asset://?label=DuneWIB&subsystem=readout"

wibeth_conf = copy.deepcopy(conf_dict)
wibeth_conf["readout"]["dro_map"] = integtest_file_gen.generate_dromap_contents(n_streams=number_of_data_producers, det_id =10)
wibeth_conf["detector"]["clock_speed_hz"] = 62500000
#wibeth_conf["readout"]["data_rate_slowdown_factor"] = 1
wibeth_conf["readout"]["default_data_file"] = "asset://?label=WIBEth&subsystem=readout"

tde_conf = copy.deepcopy(conf_dict)
tde_conf["readout"]["dro_map"] = integtest_file_gen.generate_dromap_contents(n_streams=number_of_data_producers, det_id = 11)
tde_conf["detector"]["clock_speed_hz"] = 62500000
tde_conf["readout"]["default_data_file"] = "asset://?checksum=759e5351436bead208cf4963932d6327"

pds_stream_conf = copy.deepcopy(conf_dict)
pds_stream_conf["readout"]["dro_map"] = integtest_file_gen.generate_dromap_contents(n_streams=number_of_data_producers, n_apps=1, det_id=2, app_type='flx', flx_mode='fix_rate', flx_protocol='half') # det_id = 2 for HD_PDS
pds_stream_conf["readout"]["default_data_file"] = "asset://?label=DAPHNEStream&subsystem=readout"
pds_stream_conf["trigger"]["trigger_window_before_ticks"] = 62000
pds_stream_conf["trigger"]["trigger_window_after_ticks"] = 500

pds_conf = copy.deepcopy(conf_dict)
pds_conf["readout"]["dro_map"] = integtest_file_gen.generate_dromap_contents(n_streams=number_of_data_producers, n_apps=1, det_id=2, app_type='flx', flx_mode='var_rate', flx_protocol='half') # det_id = 2 for HD_PDS
pds_conf["readout"]["default_data_file"] = "asset://?label=DAPHNE&subsystem=readout"
pds_conf["trigger"]["trigger_window_before_ticks"] = 62000
pds_conf["trigger"]["trigger_window_after_ticks"] = 500

#pacman_conf = copy.deepcopy(conf_dict)
#pacman_conf["readout"]["dro_map"] = integtest_file_gen.generate_dromap_contents(number_of_data_producers, 1, 32) # det_id = 32 for NDLAr_TPC
#pacman_conf["readout"]["default_data_file"] = "asset://?label=PACMAN&subsystem=readout"

#mpd_conf = copy.deepcopy(conf_dict)
#mpd_conf["readout"]["dro_map"] = integtest_file_gen.generate_dromap_contents(number_of_data_producers, 1, 33) # det_id = 33 for NDLAr_PDS
#mpd_conf["readout"]["default_data_file"] = "asset://?label=MPD&subsystem=readout"


confgen_arguments={
                   #"WIB1_System": wib1_conf,
                   "WIBEth_System": wibeth_conf,
                   #"Software_TPG_System": swtpg_conf,
                   "DQM_System": dqm_conf,
                   "WIB2_System": wib2_conf,
                   "PDS_Stream_System": pds_stream_conf,
                   "PDS_System": pds_conf,
                   "TDE_System": tde_conf,
                   #"PACMAN_System": pacman_conf,
                   #"MPD_System": mpd_conf
                  }

# The commands to run in nanorc, as a list
nanorc_command_list="integtest-partition boot conf start 101 wait 2 enable_triggers wait ".split() + [str(run_duration)] + "disable_triggers wait 2 stop_run wait 2 scrap terminate".split()

# The tests themselves

def test_nanorc_success(run_nanorc):
    current_test=os.environ.get('PYTEST_CURRENT_TEST')
    match_obj = re.search(r".*\[(.+)\].*", current_test)
    if match_obj:
        current_test = match_obj.group(1)
    banner_line = re.sub(".", "=", current_test)
    print(banner_line)
    print(current_test)
    print(banner_line)
    # Check that nanorc completed correctly
    assert run_nanorc.completed_process.returncode==0

def test_log_files(run_nanorc):
    local_check_flag=check_for_logfile_errors

    if local_check_flag:
        # Check that there are no warnings or errors in the log files
        assert log_file_checks.logs_are_error_free(run_nanorc.log_files, True, True, ignored_logfile_problems)

def test_data_files(run_nanorc):
    local_expected_event_count=expected_event_count
    local_event_count_tolerance=expected_event_count_tolerance
    fragment_check_list=[]
    if "enable_tpg" in run_nanorc.confgen_config["readout"].keys() and run_nanorc.confgen_config["readout"]["enable_tpg"]:
        local_expected_event_count+=(285*number_of_data_producers*run_duration/100)
        local_event_count_tolerance+=(10*number_of_data_producers*run_duration/100)
        fragment_check_list.append(wib1_frag_multi_trig_params)
        fragment_check_list.append(triggertp_frag_params)
    else:
        fragment_check_list.append(triggercandidate_frag_params)
        current_test=os.environ.get('PYTEST_CURRENT_TEST')
        if "PDS_Stream" in current_test:
            fragment_check_list.append(pds_stream_frag_params)
        elif "PDS" in current_test:
            fragment_check_list.append(pds_frag_params)
        elif "DQM" in current_test:
            fragment_check_list.append(wib2_frag_params)
        elif "WIB2" in current_test:
            fragment_check_list.append(wib2_frag_params)
        elif "WIBEth" in current_test:
            fragment_check_list.append(wibeth_frag_params)
        elif "TDE" in current_test:
            fragment_check_list.append(tde_frag_params)    
        else:
            fragment_check_list.append(wib1_frag_hsi_trig_params)

    # Run some tests on the output data file
    assert len(run_nanorc.data_files)==expected_number_of_data_files

    for idx in range(len(run_nanorc.data_files)):
        data_file=data_file_checks.DataFile(run_nanorc.data_files[idx])
        assert data_file_checks.sanity_check(data_file)
        assert data_file_checks.check_file_attributes(data_file)
        assert data_file_checks.check_event_count(data_file, local_expected_event_count, local_event_count_tolerance)
        for jdx in range(len(fragment_check_list)):
            assert data_file_checks.check_fragment_count(data_file, fragment_check_list[jdx])
            assert data_file_checks.check_fragment_sizes(data_file, fragment_check_list[jdx])

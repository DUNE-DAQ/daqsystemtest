import pytest
import os
import re
import psutil
import copy

import dfmodules.data_file_checks as data_file_checks
import integrationtest.log_file_checks as log_file_checks
import integrationtest.config_file_gen as config_file_gen
import dfmodules.integtest_file_gen as integtest_file_gen

# Values that help determine the running conditions
number_of_data_producers=2
number_of_readout_apps=2
number_of_dataflow_apps=1
base_trigger_rate=1.0 # Hz
trigger_rate_factor=3.5
run_duration=20  # seconds

# Default values for validation parameters
expected_number_of_data_files=3*number_of_dataflow_apps
check_for_logfile_errors=True
expected_event_count=run_duration*base_trigger_rate/number_of_dataflow_apps
expected_event_count_tolerance=expected_event_count/10
wib2_frag_hsi_trig_params={"fragment_type_description": "WIB2",
                           "fragment_type": "WIB",
                           "hdf5_source_subsystem": "Detector_Readout",
                           "expected_fragment_count": (number_of_data_producers*number_of_readout_apps),
                           "min_size_bytes": 29816, "max_size_bytes": 29816}
triggercandidate_frag_params={"fragment_type_description": "Trigger Candidate",
                              "fragment_type": "Trigger_Candidate",
                              "hdf5_source_subsystem": "Trigger",
                              "expected_fragment_count": 1,
                              "min_size_bytes": 120, "max_size_bytes": 150}

# Determine if the conditions are right for these tests
we_are_running_on_an_iceberg_computer=False
hostname=os.uname().nodename
#if "iceberg01" in hostname or "protodune-daq02" in hostname:
if "iceberg01" in hostname:
    we_are_running_on_an_iceberg_computer=True
the_global_timing_partition_is_running=False
username=os.environ.get('USER')
for proc in psutil.process_iter(['pid', 'name', 'username']):
    if proc.username() == username and "nanotimingrc" in proc.name():
        the_global_timing_partition_is_running=True
print(f"DEBUG: hostname is {hostname}, iceberg-computer flag is {we_are_running_on_an_iceberg_computer} and global-timing-running flag is {the_global_timing_partition_is_running}.")

# The next three variable declarations *must* be present as globals in the test
# file. They're read by the "fixtures" in conftest.py to determine how
# to run the config generation and nanorc

# The name of the python module for the config generation
confgen_name="daqconf_multiru_gen"

# The arguments to pass to the config generator, excluding the json
# output directory (the test framework handles that)
hardware_map_contents = integtest_file_gen.generate_hwmap_file(number_of_data_producers, number_of_readout_apps)

conf_dict = config_file_gen.get_default_config_dict()
conf_dict["hsi"] = {}
conf_dict["readout"]["clock_speed_hz"] = 62500000
conf_dict["readout"]["latency_buffer_size"] = 200000
conf_dict["readout"]["use_fake_data_producers"] = True
conf_dict["trigger"]["trigger_window_before_ticks"] = 1000
conf_dict["trigger"]["trigger_window_after_ticks"] = 1000

conf_dict["dataflow"]["apps"] = [] # Remove preconfigured dataflow0 app
for df_app in range(number_of_dataflow_apps):
    dfapp_conf = {}
    dfapp_conf["app_name"] = f"dataflow{df_app}"
    conf_dict["dataflow"]["apps"].append(dfapp_conf)


if we_are_running_on_an_iceberg_computer and the_global_timing_partition_is_running:
    conf_dict["trigger"]["ttcm_s1"] = 1
    conf_dict["trigger"]["hsi_trigger_type_passthrough"] = True
    conf_dict["trigger"]["trigger_rate_hz"] = base_trigger_rate
    conf_dict["hsi"]["control_hsi_hw"]= True
    conf_dict["hsi"]["hsi_device_name"]= "BOREAS_TLU_ICEBERG"
    conf_dict["hsi"]["hsi_source"] = 1
    conf_dict["hsi"]["use_hsi_hw"] = True
    conf_dict["hsi"]["host_hsi"] = "iceberg01-priv"
    conf_dict["hsi"]["hsi_re_mask"] = 1
    conf_dict["timing"]["host_timing"] = "iceberg01-priv"
    conf_dict["timing"]["host_tprtc"] =  "iceberg01-priv"
    conf_dict["timing"]["control_timing_partition"]  = True
    conf_dict["timing"]["timing_partition_master_device_name"] = "BOREAS_TLU_ICEBERG"

    trigger_factor_conf = copy.deepcopy(conf_dict)
    trigger_factor_conf["trigger"]["trigger_rate_hz"] = base_trigger_rate*trigger_rate_factor
    confgen_arguments={"Base_Trigger_Rate": conf_dict,
                       "Trigger_Rate_with_Factor": trigger_factor_conf
                      }
else:
    conf_dict["readout"]["data_rate_slowdown_factor"] = 10
    confgen_arguments={"Not on ICEBERG, cannot run test": conf_dict}

# The commands to run in nanorc, as a list
if we_are_running_on_an_iceberg_computer and the_global_timing_partition_is_running:
    nanorc_command_list="integtest-partition boot conf".split()
    nanorc_command_list+="start 101 enable_triggers wait ".split() + [str(run_duration)] + "stop_run wait 2".split()
    nanorc_command_list+="start 102 wait 1 enable_triggers wait ".split() + [str(run_duration)] + "disable_triggers wait 1 stop_run".split()
    nanorc_command_list+="start_run 103 wait ".split() + [str(run_duration)] + "disable_triggers wait 1 drain_dataflow wait 1 stop_trigger_sources wait 1 stop wait 2".split()
    nanorc_command_list+="scrap terminate".split()
else:
    nanorc_command_list=["integtest-partition", "boot", "terminate"]

# Don't require the --frame-file option since we don't need it
frame_file_required=False

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
    if check_for_logfile_errors:
        # Check that there are no warnings or errors in the log files
        assert log_file_checks.logs_are_error_free(run_nanorc.log_files, True, True)

def test_data_files(run_nanorc):
    if not we_are_running_on_an_iceberg_computer:
        print(f"This computer ({hostname}) is not part of the ICEBERG DAQ cluster and therefore can not run this test.")
        return
    if not the_global_timing_partition_is_running:
        print(f"The global timing partition does not appear to be running on this computer ({hostname}).")
        print("    Please check whether it is, and start it, if needed.")
        print("Hints: daqconf_timing_gen --host-thi iceberg01-priv --host-tmc iceberg01-priv --master-device-name BOREAS_TLU_ICEBERG --clock-speed-hz 62500000 timing_partition_config")
        print("       nanotimingrc timing_partition_config ${USER}-timing-partition boot conf wait 1200 scrap terminate")
        return

    fragment_check_list=[]
    fragment_check_list.append(wib2_frag_hsi_trig_params)
    fragment_check_list.append(triggercandidate_frag_params)

    local_expected_event_count=expected_event_count
    local_event_count_tolerance=expected_event_count_tolerance
    current_test=os.environ.get('PYTEST_CURRENT_TEST')
    match_obj = re.search(r"Factor", current_test)
    if match_obj:
        local_expected_event_count*=trigger_rate_factor
        local_event_count_tolerance*=trigger_rate_factor

    # Run some tests on the output data files
    assert len(run_nanorc.data_files)==expected_number_of_data_files

    for idx in range(len(run_nanorc.data_files)):
        data_file=data_file_checks.DataFile(run_nanorc.data_files[idx])
        assert data_file_checks.sanity_check(data_file)
        assert data_file_checks.check_file_attributes(data_file)
        assert data_file_checks.check_event_count(data_file, local_expected_event_count, local_event_count_tolerance)
        for jdx in range(len(fragment_check_list)):
            assert data_file_checks.check_fragment_count(data_file, fragment_check_list[jdx])
            assert data_file_checks.check_fragment_sizes(data_file, fragment_check_list[jdx])

# ### also test the expected trigger bit ###


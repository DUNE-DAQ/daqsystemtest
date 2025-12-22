import pytest
import urllib.request

import integrationtest.data_file_checks as data_file_checks
import integrationtest.log_file_checks as log_file_checks
import integrationtest.data_classes as data_classes
import integrationtest.resource_validation as resource_validation

pytest_plugins = "integrationtest.integrationtest_drunc"

# Values that help determine the running conditions
number_of_data_producers = 1
data_rate_slowdown_factor = 1  # 10 for ProtoWIB/DuneWIB
run_duration = 20  # seconds

# Default values for validation parameters
expected_number_of_data_files = 1
check_for_logfile_errors = True
expected_event_count = run_duration
expected_event_count_tolerance = 2
wibeth_frag_params = {
    "fragment_type_description": "WIBEth",
    "fragment_type": "WIBEth",
    "expected_fragment_count": number_of_data_producers,
    "min_size_bytes": 14472,
    "max_size_bytes": 21672,
}
triggercandidate_frag_params = {
    "fragment_type_description": "Trigger Candidate",
    "fragment_type": "Trigger_Candidate",
    "expected_fragment_count": 1,
    "min_size_bytes": 128,
    "max_size_bytes": 216,
}
hsi_frag_params = {
    "fragment_type_description": "HSI",
    "fragment_type": "Hardware_Signal",
    "expected_fragment_count": 1,
    "min_size_bytes": 100,
    "max_size_bytes": 100,
}
ignored_logfile_problems = {
    "connectionservice": [
        "Searching for connections matching uid_regex<errored_frames_q> and data_type Unknown"
    ],
    "-controller": [
        "Worker with pid \\d+ was terminated due to signal 1",
        "Connection '.*' not found on the application registry",
    ],
    "connectivity-service": [
        "errorlog: -",
    ],
}

# Determine if this computer has enough resources for these tests
resval = resource_validation.ResourceValidator()
resval.require_cpu_count(2)  # two for each data source plus 2 more for everything else
resval.require_free_memory_gb(4)  # double what we observe being used ('free -h')
resval.require_total_memory_gb(8)  # double what we need; trying to be kind to others
actual_output_path = "/tmp"
resval.require_free_disk_space_gb(actual_output_path, 1)  # more than what we observe
resval_debug_string = resval.get_debug_string()
print(f"{resval_debug_string}")

# The next three variable declarations *must* be present as globals in the test
# file. They're read by the "fixtures" in conftest.py to determine how
# to run the config generation and nanorc

# The arguments to pass to the config generator, excluding the json
# output directory (the test framework handles that)

object_databases = ["config/daqsystemtest/integrationtest-objects.data.xml"]

conf_dict = data_classes.drunc_config()
conf_dict.dro_map_config.n_streams = number_of_data_producers
conf_dict.op_env = "integtest"
conf_dict.session = "smallfootprint"
conf_dict.tpg_enabled = False
conf_dict.fake_hsi_enabled = True

conf_dict.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_id=conf_dict.session,
        obj_class="Session",
        updates={"data_rate_slowdown_factor": data_rate_slowdown_factor},
    )
)
conf_dict.config_substitutions.append(
    data_classes.attribute_substitution(obj_class="LatencyBuffer", updates={"size": 50000})
)
conf_dict.config_substitutions.append(
    data_classes.attribute_substitution(
        obj_class="FakeHSIEventGeneratorConf",
        updates={"trigger_rate": 1.0},
    )
)
confgen_arguments = {"SmallFootprint": conf_dict}

# The commands to run in nanorc, as a list
if resval.this_computer_has_sufficient_resources:
    nanorc_command_list = (
        "boot conf start --run-number 101 wait 1 enable-triggers wait ".split()
        + [str(run_duration)]
        + "disable-triggers wait 2 drain-dataflow stop-trigger-sources stop wait 2 scrap terminate".split()
    )
else:
    nanorc_command_list = ["wait", "1"]

# The tests themselves


def test_nanorc_success(run_nanorc, capsys):
    if not resval.this_computer_has_sufficient_resources:
        resval_report_string = resval.get_insufficient_resources_report()
        with capsys.disabled():
            print(f"\n\N{LARGE YELLOW CIRCLE} {resval_report_string}")
        resval_summary_string = resval.get_insufficient_resources_summary()
        pytest.skip(f"{resval_summary_string}")

    # Check that nanorc completed correctly
    assert run_nanorc.completed_process.returncode == 0


def test_log_files(run_nanorc):
    if not resval.this_computer_has_sufficient_resources:
        resval_summary_string = resval.get_insufficient_resources_summary()
        pytest.skip(f"\n{resval_summary_string}")

    if check_for_logfile_errors:
        # Check that there are no warnings or errors in the log files
        assert log_file_checks.logs_are_error_free(
            run_nanorc.log_files, True, True, ignored_logfile_problems
        )


def test_data_files(run_nanorc):
    if not resval.this_computer_has_sufficient_resources:
        resval_summary_string = resval.get_insufficient_resources_summary()
        pytest.skip(f"\n{resval_summary_string}")

    # Run some tests on the output data file
    assert len(run_nanorc.data_files) == expected_number_of_data_files

    fragment_check_list = [triggercandidate_frag_params, hsi_frag_params]
    fragment_check_list.append(wibeth_frag_params)  # WIBEth

    all_ok = True
    for idx in range(len(run_nanorc.data_files)):
        data_file = data_file_checks.DataFile(run_nanorc.data_files[idx])
        all_ok &= data_file_checks.sanity_check(data_file)
        all_ok &= data_file_checks.check_file_attributes(data_file)
        all_ok &= data_file_checks.check_event_count(
            data_file, expected_event_count, expected_event_count_tolerance
        )
        for jdx in range(len(fragment_check_list)):
            all_ok &= data_file_checks.check_fragment_count(
                data_file, fragment_check_list[jdx]
            )
            all_ok &= data_file_checks.check_fragment_sizes(
                data_file, fragment_check_list[jdx]
            )
    assert all_ok

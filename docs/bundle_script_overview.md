# Scripts to help with the running of integtests

The following scripts are intended to help developers find and run _integtests_ (regression and integration tests) in all repositories:

* `dunedaq_integtest_bundle.sh` - runs sets ("bundles") of integtests. This script supports the running of integtests from repositories that have been cloned into a local software area as well as repositories that are being used from a base release on CVMFS.
* `list_available_integtests.sh`
* `list_repos_with_integtests.sh`

Users may choose to primarily use the `dunedaq_integtest_bundle.sh` script, but the two "`list`" scripts may be occasionally useful, so they are also described here.

All of these scripts support the "`--help`" command-line option to provide information on how they should be run. Here is what is currently shown for each of the three scripts:

### dunedaq_integtest_bundle.sh --help

```
Usage:
dunedaq_integtest_bundle.sh [option(s)]

Options:
    -h, --help : prints out usage information
    -r <the list of repositories for which integtests will be run>
       - this can be the name of a single repo; it defaults to "daqsystemtest"
       - it can be a pipe-delimited string with a list of repos, e.g. 'dfmodules|trigger'
       - it can have the special value of "all" - integtests in all repos will be run
       - it can have the special value of "local" - integtests in locally-cloned repos will be run
    -R <the list of repositories to be excluded>
       - this can be the name of a single repo
       - it can be a pipe-delimited string with a list of repos, e.g. 'dfmodules|trigger'
    -k, --include <pipe-delimited string to select the tests that will be run ('egrep -i' match to test name)>
    -x, --exclude <pipe-delimited string to specify tests to be excluded ('egrep -i' match to test name)>
    --random-subset <count> : randomly picks the specified number of tests from the results of -r/-k/-x
    --list-only : list the tests that match the requested patterns without running them
    --verbosity <level> : requested level of console messages, in range 1-6, where 1 is least, 6 is DRUNC debug
    --stop-on-failure : causes the script to stop when one of the integtests reports a failure
    --tmpdir <dir> : specifies a root directory to use for test output, e.g. a directory instead of '/tmp'
    --trigger-full-rc-output <phrase that will trigger the full printout of run control messages>
       - the phrase can be a Python regex, which can be useful in handling colorized text
    --concise-output : suppresses run control and DAQApp messages in order to focus on test results
       - this is equivalent to "--verbosity 1", and this option may be removed at some point in time
    -n <number of times to run each individual test, default=1>
    -N <number of times to run the full set of selected tests, default=1>
    --pytest-options <options> : string with one or more dunedaq-specific command-line options to pass to Pytest
       - available options include the following:
         --dunerc-path <path> : Path to DUNE run control. Default is to search in $PATH
         --skip-resource-checks : Whether to skip the node resource (CPU/Memory) checks for this test
         --process-manager-type <type> : The run control process manager type to use for this test, e.g. ssh-standalone
         --dunerc-option <option-name> <option-value> : Repeatable, run control arguments without leading dashes
             for example, --dunerc-option log-level debug
       - example: --pytest-options "--skip-resource-checks --process-manager-type ssh-standalone --dunerc-option no-override-logs"
```

### list_available_integtests.sh --help

```
Usage:
list_available_integtests.sh [option(s)] [optional list of repo names]

    Example: list_available_integtests.sh daqsystemtest
    If no repo name is specified, integtests for all repos are listed.
    If a special repo name of "local" is specified, integtests for repos in the
        local software area are listed.
    If a special repo name of "all" is specified, integtests for all repos are listed.

Options:
    -h, --help : prints out usage information
    -x, --exclude <pipe-delimited string with names of repos to be excluded ('egrep -i' match to match name)>
```

### list_repos_with_integtests.sh --help 

```
Usage: list_repos_with_integtests.sh [optional "local" keyword]
  Lists the software repositories that have integration tests (integtests) in them.
  Searches the base releases, local install dir, and local sourcecode dir,
  unless "local" is passed as an argument. In that case, only the local
  install and sourcecode directories are searched.
```

Here are examples of using each of the scripts:

### dunedaq_integtest_bundle.sh

```
(dbt) [biery@daq]$ dunedaq_integtest_bundle.sh --list-only

Integtests from the _daqsystemtest_ repo will be run...

The following tests will be run:
  daqsystemtest/3ru_1df_multirun_test.py
  daqsystemtest/3ru_3df_multirun_test.py
  daqsystemtest/example_system_test.py
  daqsystemtest/fake_data_producer_test.py
  daqsystemtest/long_window_readout_test.py
  daqsystemtest/minimal_system_quick_test.py
  daqsystemtest/readout_type_scan_test.py
  daqsystemtest/small_footprint_quick_test.py
  daqsystemtest/tpg_state_collection_test.py
  daqsystemtest/tpreplay_test.py
  daqsystemtest/tpstream_writing_test.py
  daqsystemtest/trigger_bitwords_test.py

(dbt) [biery@daq]$ dunedaq_integtest_bundle.sh -r listrev --list-only

The following tests will be run:
  listrev/listrev_test.py

(dbt) [biery@daq]$ dunedaq_integtest_bundle.sh -r local --list-only

Building the list of _local_ integtests...

The following tests will be run:
  daqsystemtest/3ru_1df_multirun_test.py
  daqsystemtest/3ru_3df_multirun_test.py
  daqsystemtest/example_system_test.py
  daqsystemtest/fake_data_producer_test.py
  daqsystemtest/long_window_readout_test.py
  daqsystemtest/minimal_system_quick_test.py
  daqsystemtest/readout_type_scan_test.py
  daqsystemtest/small_footprint_quick_test.py
  daqsystemtest/tpg_state_collection_test.py
  daqsystemtest/tpreplay_test.py
  daqsystemtest/tpstream_writing_test.py
  daqsystemtest/trigger_bitwords_test.py
  dfmodules/disabled_output_test.py
  dfmodules/hdf5_compression_test.py
  dfmodules/insufficient_disk_space_test.py
  dfmodules/large_trigger_record_test.py
  dfmodules/max_file_size_test.py
  dfmodules/multiple_data_writers_test.py
  dfmodules/offline_prod_run_test.py
  dfmodules/trmonrequestor_test.py

(dbt) [biery@daq]$ dunedaq_integtest_bundle.sh -r "asiolibs|crtmodules" --list-only

The following tests will be run:
  asiolibs/socket_reader_test.py
  crtmodules/crt_frame_builder_test.py

(dbt) [biery@daq]$ dunedaq_integtest_bundle.sh -r local -k tp --list-only

Building the list of _local_ integtests...

The following tests will be run:
  daqsystemtest/small_footprint_quick_test.py
  daqsystemtest/tpg_state_collection_test.py
  daqsystemtest/tpreplay_test.py
  daqsystemtest/tpstream_writing_test.py
  dfmodules/disabled_output_test.py

(dbt) [biery@daq]$ dunedaq_integtest_bundle.sh -r local -k tp -x "disabled|tpreplay" --list-only

Building the list of _local_ integtests...

The following tests will be run:
  daqsystemtest/small_footprint_quick_test.py
  daqsystemtest/tpg_state_collection_test.py
  daqsystemtest/tpstream_writing_test.py
```

### list_available_integtests.sh

```
(dbt) [biery@daq]$ list_available_integtests.sh

Looking for integtests in _all_ repos...

asiolibs/socket_reader_test.py
crtmodules/crt_frame_builder_test.py
daqsystemtest/3ru_1df_multirun_test.py
daqsystemtest/3ru_3df_multirun_test.py
daqsystemtest/example_system_test.py
daqsystemtest/fake_data_producer_test.py
daqsystemtest/long_window_readout_test.py
daqsystemtest/minimal_system_quick_test.py
daqsystemtest/readout_type_scan_test.py
daqsystemtest/small_footprint_quick_test.py
daqsystemtest/tpg_state_collection_test.py
daqsystemtest/tpreplay_test.py
daqsystemtest/tpstream_writing_test.py
daqsystemtest/trigger_bitwords_test.py
dfmodules/disabled_output_test.py
dfmodules/hdf5_compression_test.py
dfmodules/insufficient_disk_space_test.py
dfmodules/large_trigger_record_test.py
dfmodules/max_file_size_test.py
dfmodules/multiple_data_writers_test.py
dfmodules/offline_prod_run_test.py
dfmodules/trmonrequestor_test.py
hsilibs/iceberg_real_hsi_test.py
listrev/listrev_test.py
snbmodules/simple_transform_test.py
snbmodules/snb_1node_1app_rclone_http_system_quick_test.py
snbmodules/snb_1node_1app_torrent_system_quick_test.py
snbmodules/snb_1node_multiclientapps_rclone_http_system_quick_test.py
snbmodules/snb_minimal_system_test.py
trigger/change_rate_test.py
trigger/tc_time_outside_window_test.py
trigger/td_leakage_between_runs_test.py

(dbt) [biery@daq]$ list_available_integtests.sh local

Looking for integtests in _local_ repos...

daqsystemtest/3ru_1df_multirun_test.py
daqsystemtest/3ru_3df_multirun_test.py
daqsystemtest/example_system_test.py
daqsystemtest/fake_data_producer_test.py
daqsystemtest/long_window_readout_test.py
daqsystemtest/minimal_system_quick_test.py
daqsystemtest/readout_type_scan_test.py
daqsystemtest/small_footprint_quick_test.py
daqsystemtest/tpg_state_collection_test.py
daqsystemtest/tpreplay_test.py
daqsystemtest/tpstream_writing_test.py
daqsystemtest/trigger_bitwords_test.py
dfmodules/disabled_output_test.py
dfmodules/hdf5_compression_test.py
dfmodules/insufficient_disk_space_test.py
dfmodules/large_trigger_record_test.py
dfmodules/max_file_size_test.py
dfmodules/multiple_data_writers_test.py
dfmodules/offline_prod_run_test.py
dfmodules/trmonrequestor_test.py

(dbt) [biery@daq]$ list_available_integtests.sh asiolibs crtmodules

Looking for integtests in the _asiolibs crtmodules_ repo(s)...

asiolibs/socket_reader_test.py
crtmodules/crt_frame_builder_test.py

(dbt) [biery@daq]$ list_available_integtests.sh asdf jklp

Looking for integtests in the _asdf jklp_ repo(s)...

-> "asdf" does not appear to be a valid repository name.
-> "jklp" does not appear to be a valid repository name.
```

### list_repos_with_integtests.sh

```
(dbt) [biery@daq]$ list_repos_with_integtests.sh 

Looking for _all_ repositories with integtests in them...

asiolibs
crtmodules
daqsystemtest
dfmodules
hsilibs
listrev
snbmodules
trigger

(dbt) [biery@daq]$ list_repos_with_integtests.sh local

Looking for _local_ repositories with integtests in them...

daqsystemtest
dfmodules

(dbt) [biery@daq]$ list_repos_with_integtests.sh asdf

Looking for _all_ repositories with integtests in them...

asiolibs
crtmodules
daqsystemtest
dfmodules
hsilibs
listrev
snbmodules
trigger
```

import pytest
import copy
import urllib.request

import dfmodules.data_file_checks as data_file_checks
import integrationtest.log_file_checks as log_file_checks
import integrationtest.config_file_gen as config_file_gen
import dfmodules.integtest_file_gen as integtest_file_gen

# Values that help determine the running conditions
number_of_data_producers=2
data_rate_slowdown_factor=10

# The next three variable declarations *must* be present as globals in the test
# file. They're read by the "fixtures" in conftest.py to determine how
# to run the config generation and nanorc

# The name of the python module for the config generation
confgen_name="daqconf_multiru_gen"
# The arguments to pass to the config generator, excluding the json
# output directory (the test framework handles that)
hardware_map_contents = integtest_file_gen.generate_hwmap_file(number_of_data_producers)

conf_dict = config_file_gen.get_default_config_dict()
try:
  urllib.request.urlopen('http://localhost:5000').status
  conf_dict["boot"]["use_connectivity_service"] = True
except:
  conf_dict["boot"]["use_connectivity_service"] = False
conf_dict["readout"]["data_rate_slowdown_factor"] = data_rate_slowdown_factor
conf_dict["readout"]["latency_buffer_size"] = 200000
conf_dict["readout"]["enable_software_tpg"] = True
conf_dict["dqm"]["enable_dqm"] = True

confgen_arguments={"Test_System": conf_dict
                  }
# The commands to run in nanorc, as a list
nanorc_command_list=[

# No commands are valid before boot
["integtest-partition", "conf"],
["integtest-partition", "start_run", "100"],
["integtest-partition", "start", "101"],
["integtest-partition", "enable_triggers"],
["integtest-partition", "stop_run"],
["integtest-partition", "disable_triggers"],
["integtest-partition", "drain_dataflow"],
["integtest-partition", "stop_trigger_sources"],
["integtest-partition", "stop"],
["integtest-partition", "scrap"],

# Only conf after boot
"integtest-partition boot boot".split(),
"integtest-partition boot start 101".split(),
"integtest-partition boot stop_run".split(),
"integtest-partition boot disable_triggers".split(),
"integtest-partition boot drain_dataflow".split(),
"integtest-partition boot stop_trigger_sources".split(),
"integtest-partition boot stop".split(),
"integtest-partition boot scrap".split(),

# Only start, start_run and scrap after conf
"integtest-partition boot conf boot".split(),
"integtest-partition boot conf conf".split(),
"integtest-partition boot conf enable_triggers".split(),
"integtest-partition boot conf stop_run".split(),
"integtest-partition boot conf disable_triggers".split(),
"integtest-partition boot conf drain_dataflow".split(),
"integtest-partition boot conf stop_trigger_sources".split(),
"integtest-partition boot conf stop".split(),

# Only drain_dataflow and enable_triggers after start
"integtest-partition boot conf start 100 boot".split(),
"integtest-partition boot conf start 101 conf".split(),
"integtest-partition boot conf start 102 start_run 100".split(),
"integtest-partition boot conf start 103 start 100".split(),
"integtest-partition boot conf start 104 disable_triggers".split(),
"integtest-partition boot conf start 105 stop_trigger_sources".split(),
"integtest-partition boot conf start 106 stop".split(),

# Only disable_triggers after enable_triggers
"integtest-partition boot conf start 200 enable_triggers boot".split(),
"integtest-partition boot conf start 201 enable_triggers conf".split(),
"integtest-partition boot conf start 202 enable_triggers start_run".split(),
"integtest-partition boot conf start 203 enable_triggers start".split(),
"integtest-partition boot conf start 204 enable_triggers enable_triggers".split(),
"integtest-partition boot conf start 205 enable_triggers drain_dataflow".split(),
"integtest-partition boot conf start 206 enable_triggers stop_trigger_sources".split(),
"integtest-partition boot conf start 207 enable_triggers stop".split(),
"integtest-partition boot conf start 208 enable_triggers scrap".split(),

# Only stop_trigger_sources after drain_dataflow
"integtest-partition boot conf start 300 drain_dataflow boot".split(),
"integtest-partition boot conf start 301 drain_dataflow conf".split(),
"integtest-partition boot conf start 302 drain_dataflow start_run".split(),
"integtest-partition boot conf start 303 drain_dataflow start".split(),
"integtest-partition boot conf start 304 drain_dataflow enable_triggers".split(),
"integtest-partition boot conf start 305 drain_dataflow disable_triggers".split(),
"integtest-partition boot conf start 306 drain_dataflow drain_dataflow".split(),
"integtest-partition boot conf start 307 drain_dataflow stop".split(),
"integtest-partition boot conf start 308 drain_dataflow scrap".split(),

# Only stop after stop_trigger_sources
"integtest-partition boot conf start 400 drain_dataflow stop_trigger_sources boot".split(),
"integtest-partition boot conf start 401 drain_dataflow stop_trigger_sources conf".split(),
"integtest-partition boot conf start 402 drain_dataflow stop_trigger_sources start_run".split(),
"integtest-partition boot conf start 403 drain_dataflow stop_trigger_sources start".split(),
"integtest-partition boot conf start 404 drain_dataflow stop_trigger_sources enable_triggers".split(),
"integtest-partition boot conf start 405 drain_dataflow stop_trigger_sources disable_triggers".split(),
"integtest-partition boot conf start 406 drain_dataflow stop_trigger_sources drain_dataflow".split(),
"integtest-partition boot conf start 407 drain_dataflow stop_trigger_sources stop_trigger_sources".split(),
"integtest-partition boot conf start 408 drain_dataflow stop_trigger_sources scrap".split(),

# Only start and scrap after stop
"integtest-partition boot conf start 500 drain_dataflow stop_trigger_sources stop boot".split(),
"integtest-partition boot conf start 501 drain_dataflow stop_trigger_sources stop conf".split(),
"integtest-partition boot conf start 502 drain_dataflow stop_trigger_sources stop enable_triggers".split(),
"integtest-partition boot conf start 503 drain_dataflow stop_trigger_sources stop disable_triggers".split(),
"integtest-partition boot conf start 504 drain_dataflow stop_trigger_sources stop drain_dataflow".split(),
"integtest-partition boot conf start 505 drain_dataflow stop_trigger_sources stop stop_trigger_sources".split(),
"integtest-partition boot conf start 506 drain_dataflow stop_trigger_sources stop scrap".split(),
"integtest-partition boot conf start 507 drain_dataflow stop_trigger_sources stop stop_run".split(),

# Only terminate after scrap
"integtest-partition boot conf start 600 drain_dataflow stop_trigger_sources stop scrap boot".split(),
"integtest-partition boot conf start 601 drain_dataflow stop_trigger_sources stop scrap start".split(),
"integtest-partition boot conf start 602 drain_dataflow stop_trigger_sources stop scrap enable_triggers".split(),
"integtest-partition boot conf start 603 drain_dataflow stop_trigger_sources stop scrap disable_triggers".split(),
"integtest-partition boot conf start 604 drain_dataflow stop_trigger_sources stop scrap drain_dataflow".split(),
"integtest-partition boot conf start 605 drain_dataflow stop_trigger_sources stop scrap stop_trigger_sources".split(),
"integtest-partition boot conf start 606 drain_dataflow stop_trigger_sources stop scrap stop".split(),
"integtest-partition boot conf start 607 drain_dataflow stop_trigger_sources stop scrap scrap".split(),

# Test valid command after invalid (should still fail)
# "integtest-partition boot boot conf start 121 stop scrap".split(),
# "integtest-partition boot stop conf start 122 stop scrap".split(),
# "integtest-partition boot conf stop start 123 stop scrap".split(),
# "integtest-partition boot conf start 124 conf stop scrap".split(),
# "integtest-partition boot conf start 125 stop scrap".split(),
# "integtest-partition boot conf start 125 stop scrap boot conf".split(),
# "integtest-partition boot stop start 126 stop scrap boot conf".split()
]

# The tests themselves
def test_result(run_nanorc):
    assert run_nanorc.completed_process.returncode!=0
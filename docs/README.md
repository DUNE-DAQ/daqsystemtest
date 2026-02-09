# daqsystemtest

This repository contains configurations and `pytest` test modules for system-level DAQ tests. Currently, there are two relevant subdirectories:
* `integtest/`: `pytest`-based integration tests, often use for regression testing
* `config/`: OKS-based configuration files that demonstrate various features of our configuration system

The `pytest` test modules (a.k.a. `integtests`) are meant to be run as part of the release testing procedure to ensure that all of the functionality needed by DUNE-DAQ is present.  

For a short summary of the `pytest` integration tests that are currently available, click [here](../integtest/README.md).

For a description of a script that can be used to run multiple integtests from multiple repositories, please see [this page](bundle_script_overview.md).

To see some of the "OKS Session" objects that are at the top level of our example configurations, please see [this file](../config/daqsystemtest/example-configs.data.xml).

# daq-systemtest

This repository contains configurations for system-level DAQ tests. Currently, there are two subdirectories:
* integtest: Pytest-based integration tests
* config: JSON configurations for `daqconf_multiru_gen` (and `daqconf_timing_gen`)

These tests are meant to be run as part of the release testing procedure to ensure that all of the functionality needed by DUNE-DAQ is present.

Version v1.0.0

# Test Inventory

## Default System
These tests are "default" configurations as much as possible, to ensure that the software functions correctly when run in the "runtime" context.

* default_system.json
* default_system_with_tpg.json:
SW TPG enabled
* default_system_with_tpg_s10.json:
SW TPG enabled, data_rate_slowdown_factor of 10

## Emulated Systems
These configurations use real hardware in data emulation mode, to test the full readout and dataflow chains.

* emulated_daphne_system.json: Test DAPHNE readout (i.e. PDS)
* emulated_daphne_system_k8s.json: Same, but in a containerized environment
* emulated_daphne_system_flx_ctrl.json: Test DAPHNE readout, using a FELIX control app to configure
* emulated_daphne_system_flx_ctrl_k8s.json: Same, but in a containerized environment
* emulated_pacman_system.json:
**Not Implemented for v3.2.0** Test PACMAN readout (Near Detector)
* emulated_tde_system.json:
Test VD TDE readout
* emulated_wib2_system.json:
Test WIB2 readout
* emulated_wib2_system_k8s.json:
Same, but in a containerized environment
* emulated_wib2_system_flx_ctrl.json:
Test WIB2 readout, using a FELIX control app to configure
* emulated_wib2_system_flx_ctrl_k8s.json:
Same, but in a containerized environment

## Timing Tests
These configurations are designed to test the interaction of the DAQ with the real timing hardware.

* timing_system_bristol:
2 JSON files, `_daq.json` and `_timing.json`, the first is for a simple `daqconf_multiru_system`, and the second is for `daqconf_timing_gen` to configure the hardware.
* timing_system_bristol_ouroboros:
2 JSON files, `_daq.json` and `_timing.json`, the first is for a simple `daqconf_multiru_system`, and the second is for `daqconf_timing_gen` to configure the hardware.
* timing_system_cern:
2 JSON files, `_daq.json` and `_timing.json`, the first is for a simple `daqconf_multiru_system`, and the second is for `daqconf_timing_gen` to configure the hardware.
* timing_system_iceberg:
2 JSON files, `_daq.json` and `_timing.json`, the first is for a simple `daqconf_multiru_system`, and the second is for `daqconf_timing_gen` to configure the hardware.

## Scale Tests
These tests use fake data producers to attempt to scale the system to 10x or 100x the number of nodes available, to see how the system performs under high load.

* medium_scale_system.json:
A system with 10 fake data links on each of 13 readout hosts (currently)
* medium_scale_system_k8s.json:
Same, but in a containerized environment
* large_scale_system.json:
A system with 100 fake data links on each of 13 readout hosts (currently)
* large_scale_system_k8s.json:
Same, but in a containerized environment

## K8s Tests
Tests of the DAQ in a Kubernetes environment

* simple_k8s_test.json:
Default system in containers
* tpg_dqm_k8s_test.json:
Default system with SW TPG and DQM apps in containers

## Hardware Tests
Tests with actual hardware, reading real data, but not an entire detector configuration.

* wib2_system.json:
Readout a DUNEWIB in a single module.

## Detector Configurations
These entries are intended to be as close as possible to the actual configurations run on the detector, to the point where they can/should be starting points for detector running.

* <details><summary>wib_hd_coldbox.json: </summary>Test configuration used for the HD Coldbox at NP04. This JSON file is designed for `wibconf_gen`.</details>


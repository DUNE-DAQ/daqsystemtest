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
* <details><summary>default_system_with_tpg.json: </summary>
  SW TPG enabled</details>
* <details><summary>default_system_with_tpg_s10.json: </summary>
  SW TPG enabled, data_rate_slowdown_factor of 10</details>

## Emulated Systems
These configurations use real hardware in data emulation mode, to test the full readout and dataflow chains.

* <details><summary>emulated_daphne_system.json: </summary>
  Test DAPHNE readout (i.e. PDS)</details>
* <details><summary>emulated_daphne_system_k8s.json: </summary>
  Same, but in a containerized environment</details>
* <details><summary>emulated_daphne_system_flx_ctrl.json: </summary>
  Test DAPHNE readout, using a FELIX control app to configure</details>
* <details><summary>emulated_daphne_system_flx_ctrl_k8s.json: </summary>
  Same, but in a containerized environment
* <details><summary>emulated_pacman_system.json: 
  **Not Implemented for v3.2.0** Test PACMAN readout (Near Detector)</details>
* <details><summary>emulated_tde_system.json: </summary>
  Test VD TDE readout</details>
* <details><summary>emulated_wib2_system.json: </summary>
  Test WIB2 readout</details>
* <details><summary>emulated_wib2_system_k8s.json: </summary>
  Same, but in a containerized environment</details>
* <details><summary>emulated_wib2_system_flx_ctrl.json: </summary>
  Test WIB2 readout, using a FELIX control app to configure</details>
* <details><summary>emulated_wib2_system_flx_ctrl_k8s.json: </summary>
  Same, but in a containerized environment</details>

## Timing Tests
These configurations are designed to test the interaction of the DAQ with the real timing hardware.

* <details><summary>timing_system_bristol: </summary>
  2 JSON files, `_daq.json` and `_timing.json`, the first is for a simple `daqconf_multiru_system`, and the second is for `daqconf_timing_gen` to configure the hardware.</details>
* <details><summary>timing_system_bristol_ouroboros: </summary>
  2 JSON files, `_daq.json` and `_timing.json`, the first is for a simple `daqconf_multiru_system`, and the second is for `daqconf_timing_gen` to configure the hardware.</details>
* <details><summary>timing_system_cern: </summary>
  2 JSON files, `_daq.json` and `_timing.json`, the first is for a simple `daqconf_multiru_system`, and the second is for `daqconf_timing_gen` to configure the hardware.</details>
* <details><summary>timing_system_iceberg: </summary>
  2 JSON files, `_daq.json` and `_timing.json`, the first is for a simple `daqconf_multiru_system`, and the second is for `daqconf_timing_gen` to configure the hardware.</details>

## Scale Tests
These tests use fake data producers to attempt to scale the system to 10x or 100x the number of nodes available, to see how the system performs under high load.

* <details><summary>medium_scale_system.json: </summary>
  A system with 10 fake data links on each of 13 readout hosts (currently)</details>
* <details><summary>medium_scale_system_k8s.json: </summary>
  Same, but in a containerized environment</details>
* <details><summary>large_scale_system.json: </summary>
  A system with 100 fake data links on each of 13 readout hosts (currently)</details>
* <details><summary>large_scale_system_k8s.json: </summary>
  Same, but in a containerized environment</details>

## K8s Tests
Tests of the DAQ in a Kubernetes environment

* <details><summary>simple_k8s_test.json: </summary>
  Default system in containers</details>
* <details><summary>tpg_dqm_k8s_test.json: </summary>
  Default system with SW TPG and DQM apps in containers</details>

## Hardware Tests
Tests with actual hardware, reading real data, but not an entire detector configuration.

* <details><summary>wib2_system.json: </summary>
  Readout a DUNEWIB in a single module.</details>

## Detector Configurations
These entries are intended to be as close as possible to the actual configurations run on the detector, to the point where they can/should be starting points for detector running.

* <details><summary>wib_hd_coldbox.json: </summary>
  Test configuration used for the HD Coldbox at NP04. This JSON file is designed for `wibconf_gen`.</details>


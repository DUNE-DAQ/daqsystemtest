#!/usr/bin/env python

import sys
import sh
import pathlib
from rich import print

script_path = pathlib.Path(__file__).parent

cfg_dir = script_path.parent / "config" / "timing_systems"

commands = [
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/timing_system_local_DetReadoutMap.json -c {cfg_dir}/timing_system_bristol_daq.json test",
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/timing_system_local_DetReadoutMap.json -c {cfg_dir}/timing_system_bristol_ouroboros_daq.json test",
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/timing_system_local_DetReadoutMap.json -c {cfg_dir}/timing_system_bristol_daq.json --force-pm k8s test",
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/timing_system_local_DetReadoutMap.json -c {cfg_dir}/timing_system_bristol_ouroboros_daq.json --force-pm k8s test",
    f"daqconf_timing_gen  -n -c {cfg_dir}/timing_system_bristol_ouroboros_timing.json test",
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/timing_system_cern_DetReadoutMap.json  -c {cfg_dir}/timing_system_cern_daq.json test",
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/timing_system_cern_DetReadoutMap.json  -c {cfg_dir}/timing_system_cern_daq.json --force-pm k8s test",
    f"daqconf_timing_gen  -n -c {cfg_dir}/timing_system_cern_timing.json test",
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/timing_system_local_DetReadoutMap.json -c {cfg_dir}/timing_system_iceberg_daq.json test",
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/timing_system_local_DetReadoutMap.json -c {cfg_dir}/timing_system_iceberg_daq.json --force-pm k8s test",
    f"daqconf_timing_gen  -n -c {cfg_dir}/timing_system_iceberg_timing.json test",
] ## only k8s for daq

failed = {}
success = []
for cmd in commands:
    print(f"Executing '{cmd}'")
    cmd_tokens = cmd.split()
    try:
        exe = getattr(sh, cmd_tokens[0])
        exe(*cmd_tokens[1:], _out=sys.stdout, _err=sys.stderr)
    except Exception as e:
        failed[cmd] = str(e)
        continue

    success.append(cmd)


print(f"Successful {success}")
print(f"Failed {failed}")

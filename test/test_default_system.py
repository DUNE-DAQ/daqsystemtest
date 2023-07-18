#!/usr/bin/env python

import sys
import sh
import pathlib
from rich import print

script_path = pathlib.Path(__file__).parent

cfg_dir = script_path.parent / "config" / "default_system"

commands = [
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/default_system_eth_DetReadoutMap.json -c {cfg_dir}/default_system_eth.json test",
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/default_system_eth_DetReadoutMap.json -c {cfg_dir}/default_system_eth.json --force-pm k8s test",
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/default_system_eth_DetReadoutMap.json -c {cfg_dir}/default_system_fake.json test",
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/default_system_eth_DetReadoutMap.json -c {cfg_dir}/default_system_fake.json --force-pm k8s test",
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/default_system_eth_DetReadoutMap.json -c {cfg_dir}/default_system_with_tpg.json test",
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/default_system_eth_DetReadoutMap.json -c {cfg_dir}/default_system_with_tpg.json --force-pm k8s test",
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/default_system_flx_DetReadoutMap.json -c {cfg_dir}/default_system_flx.json test",
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/default_system_flx_DetReadoutMap.json -c {cfg_dir}/default_system_flx.json --force-pm k8s test",
]

failed = {}
success = []
for cmd in commands:
    print(f"\nExecuting '{cmd}'\n")
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
# import IPython
# IPython.embed(colors="neutral")

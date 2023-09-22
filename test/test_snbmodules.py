#!/usr/bin/env python

import sys
import sh
import pathlib
from rich import print

script_path = pathlib.Path(__file__).parent

cfg_dir = script_path.parent / "config" / "snbmodules_systems"
default_readout_map = script_path.parent / "default_system" / "default_system_eth_DetReadoutMap.json"

commands = [
    f"snbmodules_multiru_multisnb_gen -n --detector-readout-map-file {default_readout_map} -c {cfg_dir}/snbmodules_multiple_hosts.json test",
    f"snbmodules_multiru_multisnb_gen -n --detector-readout-map-file {default_readout_map} -c {cfg_dir}/snbmodules_only_bookkeeper_host.json test",
    f"snbmodules_multiru_multisnb_gen -n --detector-readout-map-file {default_readout_map} -c {cfg_dir}/snbmodules_only_client_host.json test",
    f"snbmodules_multiru_multisnb_gen -n --detector-readout-map-file {default_readout_map} -c {cfg_dir}/snbmodules_single_host_multiple_clients.json test",
    f"snbmodules_multiru_multisnb_gen -n --detector-readout-map-file {default_readout_map} -c {cfg_dir}/snbmodules_single_host.json test",
    
]

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

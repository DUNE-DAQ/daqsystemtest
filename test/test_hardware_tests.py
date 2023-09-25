#!/usr/bin/env python

import sys
import sh
import pathlib
from rich import print

script_path = pathlib.Path(__file__).parent

cfg_dir = script_path.parent / "config" / "hardware_tests"

commands = [
    # WIB2
    f"fddaqconf_gen -n --detector-readout-map-file {cfg_dir}/wib2_system_DetReadoutMap.json -c {cfg_dir}/wib2_system.json test",
    f"fddaqconf_gen -n --detector-readout-map-file {cfg_dir}/wib2_system_DetReadoutMap.json -c {cfg_dir}/wib2_system.json --force-pm k8s test",
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

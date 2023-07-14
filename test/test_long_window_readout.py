#!/usr/bin/env python

import sys
import sh
import pathlib
from rich import print

script_path = pathlib.Path(__file__).parent

cfg_dir = script_path.parent / "config" / "long_window_readout"

commands = [
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/long_window_readout_DetReadoutMap.json -c {cfg_dir}/long_window_readout.json test",
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/long_window_readout_DetReadoutMap.json -c {cfg_dir}/long_window_readout.json --force-pm k8s test",
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

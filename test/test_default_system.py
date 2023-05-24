#!/usr/bin/env python

import sys
import sh
import pathlib
from rich import print

script_path = pathlib.Path(__file__).parent

cfg_dir = script_path.parent / "config" / "default_system"

commands = [
    f"daqconf_multiru_gen -n --detector-readout-map-file  {cfg_dir}/default_system_DetReadoutMap.json -c  {cfg_dir}/default_system.json test",
    f"daqconf_multiru_gen -n --detector-readout-map-file  {cfg_dir}/default_system_DetReadoutMap.json -c  {cfg_dir}/default_system_with_tpg.json test",
    f"daqconf_multiru_gen -n --detector-readout-map-file  {cfg_dir}/default_system_DetReadoutMap.json -c  {cfg_dir}/default_system_with_tpg_s10.json test"
]

failed = []
success = []
for cmd in commands:
    print(f"\nExecuting '{cmd}'\n")
    cmd_tokens = cmd.split()
    exe = getattr(sh, cmd_tokens[0])
    try:
        exe(*cmd_tokens[1:], _out=sys.stdout, _err=sys.stderr)
    except RuntimeError:
        failed.append(cmd)
        continue

    success.append(cmd)


print(f"Successful {success}")
print(f"Failed {failed}")
# import IPython
# IPython.embed(colors="neutral")

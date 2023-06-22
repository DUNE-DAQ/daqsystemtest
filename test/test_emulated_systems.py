#!/usr/bin/env python

import sys
import sh
import pathlib
from rich import print

script_path = pathlib.Path(__file__).parent

cfg_dir = script_path.parent / "config" / "emulated_systems"

commands = [
    # Daphne
    f"flx_ctrl_gen.py -n -m {cfg_dir}/emulated_daphne_system_DetReadoutMap.json -c {cfg_dir}/emulated_daphne_system_flx_ctrl.json test",
    f"flx_ctrl_gen.py -n -m {cfg_dir}/emulated_daphne_system_DetReadoutMap.json -c {cfg_dir}/emulated_daphne_system_flx_ctrl_k8s.json test",
    f"daqconf_multiru_gen -n -m {cfg_dir}/emulated_daphne_system_DetReadoutMap.json -c {cfg_dir}/emulated_daphne_system.json test",
    f"daqconf_multiru_gen -n -m {cfg_dir}/emulated_daphne_system_DetReadoutMap.json -c {cfg_dir}/emulated_daphne_system_k8s.json test",
    # Packman
    f"daqconf_multiru_gen -n -m {cfg_dir}/emulated_pacman_system_DetReadoutMap.json -c {cfg_dir}/emulated_pacman_system.json test",

]

failed = []
success = []
for cmd in commands:
    print(f"Executing '{cmd}'")
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

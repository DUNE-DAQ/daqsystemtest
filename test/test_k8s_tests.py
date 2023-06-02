#!/usr/bin/env python

import sys
import sh
import pathlib
from rich import print

script_path = pathlib.Path(__file__).parent

cfg_dir = script_path.parent / "config" / "k8s_tests"

common_flags = [
    '-n',
]

flx_commands = [
    f"felixcardcontrollerconf_gen.py {' '.join(common_flags)} -m {cfg_dir}/hd_coldbox_DetReadoutMap.json -c {cfg_dir}/flx_card_hd_coldbox.json test",
]

daq_commands = [
    f"daqconf_multiru_gen {' '.join(common_flags)} --force-pm k8s -c {cfg_dir}/np04_daq.json -m {cfg_dir}/np04_APA1_DetReadoutMap.json --debug daq_APA1_k8s"
    f"daqconf_multiru_gen {' '.join(common_flags)} --force-pm ssh -c {cfg_dir}/np04_daq.json -m {cfg_dir}/np04_APA1_DetReadoutMap.json --debug daq_APA1_ssh"
]

commands = daq_commands


failed = []
success = []
for cmd in commands:
    print(f"Executing '{cmd}'")
    cmd_tokens = cmd.split()
    exe = getattr(sh, cmd_tokens[0])
    try:
        exe(*cmd_tokens[1:], _out=sys.stdout, _err=sys.stderr)
    except sh.ErrorReturnCode:
        failed.append(cmd)
        continue

    success.append(cmd)


print(f"Successful {success}")
print(f"Failed {failed}")

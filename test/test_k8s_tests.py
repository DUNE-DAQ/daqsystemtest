#!/usr/bin/env python

import sys
import sh
import pathlib
from rich import print

script_path = pathlib.Path(__file__).parent

cfg_dir = script_path.parent / "config" / "k8s_tests"

commands = [
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/simple_k8s_test_DetReadoutMap.json -c {cfg_dir}/simple_k8s_test.json test",
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/tpg_dqm_k8s_test_DetReadoutMap.json -c {cfg_dir}/tpg_dqm_k8s_test.json test",
]

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

#!/usr/bin/env python

import sys
import sh
import pathlib
from rich import print

script_path = pathlib.Path(__file__).parent

cfg_dir = script_path.parent / "config" / "emulated_systems"

commands = [
    # Daphne
    f"flx_ctrl_gen.py -n --detector-readout-map-file {cfg_dir}/emulated_daphne_system_DetReadoutMap.json -c {cfg_dir}/emulated_daphne_system_flx_ctrl.json test",
    f"flx_ctrl_gen -n --detector-readout-map-file {cfg_dir}/emulated_daphne_system_DetReadoutMap.json -c {cfg_dir}/emulated_daphne_system_flx_ctrl.json --force-pm k8s test",
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/emulated_daphne_system_DetReadoutMap.json -c {cfg_dir}/emulated_daphne_system.json test",
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/emulated_daphne_system_DetReadoutMap.json -c {cfg_dir}/emulated_daphne_system.json --force-pm k8s test",
    # Pacman
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/emulated_pacman_system_DetReadoutMap.json -c {cfg_dir}/emulated_pacman_system.json test",
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/emulated_pacman_system_DetReadoutMap.json -c {cfg_dir}/emulated_pacman_system.json --force-pm k8s test",
    # TDE
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/emulated_tde_system_DetReadoutMap.json -c {cfg_dir}/emulated_tde_system.json test",
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/emulated_tde_system_DetReadoutMap.json -c {cfg_dir}/emulated_tde_system.json --force-pm k8s test",
    # WIB2
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/emulated_wib2_system_DetReadoutMap.json -c {cfg_dir}/emulated_wib2_system.json test",
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/emulated_wib2_system_DetReadoutMap.json -c {cfg_dir}/emulated_wib2_system.json --force-pm k8s test",
    # WIBEth
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/emulated_wibeth_system_DetReadoutMap.json -c {cfg_dir}/emulated_wibeth_system.json test",
    f"daqconf_multiru_gen -n --detector-readout-map-file {cfg_dir}/emulated_wibeth_system_DetReadoutMap.json -c {cfg_dir}/emulated_wibeth_system.json --force-pm k8s test",
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

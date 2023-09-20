#!/usr/bin/env python

import sys
import sh
import pathlib
from rich import print

script_path = pathlib.Path(__file__).parent

cfg_dir = script_path.parent / "config" / "hd_coldbox_tests"

commands = [
    f"fddaqconf_gen -n --detector-readout-map-file {cfg_dir}/hd_coldbox_DetReadoutMap.json -c {cfg_dir}/daq_hd_coldbox.json test",
    f"felixcardcontrollerconf_gen.py -n --detector-readout-map-file {cfg_dir}/hd_coldbox_DetReadoutMap.json -c {cfg_dir}/flx_card_hd_coldbox.json test",
    f"wibconf_gen -c {cfg_dir}/wib_hd_coldbox.json hd_coldbox_wib"
    f"fddaqconf_gen -n --detector-readout-map-file {cfg_dir}/hd_coldbox_DetReadoutMap.json -c {cfg_dir}/daq_hd_coldbox.json --force-pm k8s test",
    f"felixcardcontrollerconf_gen.py -n --detector-readout-map-file {cfg_dir}/hd_coldbox_DetReadoutMap.json -c {cfg_dir}/flx_card_hd_coldbox.json --force-pm k8s test",
    f"wibconf_gen -c {cfg_dir}/wib_hd_coldbox.json --force-pm k8s hd_coldbox_wib"
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

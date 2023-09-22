#!/usr/bin/env python

import sys
import sh
import pathlib
from rich import print

script_path = pathlib.Path(__file__).parent

cfg_dir = script_path.parent / "config" / "k8s_tests"

common_flags = [
    # '-n',
    '-f'
]

wib_commands = [
    f"wibconf_gen {' '.join(common_flags)} --force-pm k8s -c {cfg_dir}/wib_apas1.json wib_APA1_k8s",
    f"wibconf_gen {' '.join(common_flags)} --force-pm ssh -c {cfg_dir}/wib_apas1.json wib_APA1_ssh",
]

wib_commands = [
    f"wibconf_gen {' '.join(common_flags)} --force-pm k8s -c {cfg_dir}/wib_apas12.json wib_APA12_k8s",
    f"wibconf_gen {' '.join(common_flags)} --force-pm ssh -c {cfg_dir}/wib_apas12.json wib_APA12_ssh",
]


flx_commands = [
    f"flx_ctrl_gen {' '.join(common_flags)} --force-pm k8s -c {cfg_dir}/np04_flx.json -m {cfg_dir}/np04_APA1_DetReadoutMap.json flx_APA1_k8s",
    f"flx_ctrl_gen {' '.join(common_flags)} --force-pm ssh -c {cfg_dir}/np04_flx.json -m {cfg_dir}/np04_APA1_DetReadoutMap.json flx_APA1_ssh",
]

daq_commands = [
    f"fddaqconf_gen {' '.join(common_flags)} --force-pm k8s -c {cfg_dir}/np04_daq_tpg_slim.json -m {cfg_dir}/np04_APA1_DetReadoutMap.json --debug daq_APA1_k8s",
    f"fddaqconf_gen {' '.join(common_flags)} --force-pm ssh -c {cfg_dir}/np04_daq_tpg_slim.json -m {cfg_dir}/np04_APA1_DetReadoutMap.json --debug daq_APA1_ssh",
]

hermes_commands = [
    f"hermesmodules_gen {' '.join(common_flags)} --force-pm k8s -c {cfg_dir}/hermes_default.json -m {cfg_dir}/np04_APA3_DetReadoutMap.json --debug hermes_APA3_k8s",
    f"hermesmodules_gen {' '.join(common_flags)} --force-pm ssh -c {cfg_dir}/hermes_default.json -m {cfg_dir}/np04_APA3_DetReadoutMap.json --debug hermes_APA3_ssh",
]

commands = daq_commands + flx_commands + wib_commands
# commands = daq_commands
# commands = flx_commands
# commands = wib_commands
# commands = hermes_commands



failed = {}
success = []
for cmd in commands:
    print(f"Executing '{cmd}'")
    cmd_tokens = cmd.split()
    try:
        exe = getattr(sh, cmd_tokens[0])
        exe(*cmd_tokens[1:], _out=sys.stdout, _err=sys.stderr,  _new_session=False)
    except Exception as e:
        failed[cmd] = str(e)
        failed.append(cmd)
        continue

    success.append(cmd)


print(f"Successful {success}")
print(f"Failed {failed}")


import json
import getpass
import os, stat

user = getpass.getuser()


top_ssh = {
    "apparatus_id":"np04_apa12",
    "wib": "wib_APA12_ssh",
    "flx": "flx_APA1_ssh",
    "daq": "daq_APA1_ssh"
}

with open("top_apa12_ssh.json", "w") as outfile:
    json.dump(top_ssh, outfile)


top_k8s = {
    "apparatus_id":"np04_apa12",
    "wib": f"db://wib-apa12-{user}",
    "flx": f"db://flx-apa1-{user}",
    "daq": f"db://daq-apa1-{user}"
}


with open("top_apa12_k8s.json", "w") as outfile:
    json.dump(top_k8s, outfile)

with open("upload_apa12_mongo.sh", "w") as outfile:
    outfile.write(f"upload-conf wib_APA12_k8s wib-apa12-{user}\n")
    outfile.write(f"upload-conf flx_APA1_k8s flx-apa1-{user}\n")
    outfile.write(f"upload-conf daq_APA1_k8s daq-apa1-{user}\n")
    os.fchmod(outfile.fileno(), stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)

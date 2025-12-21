#!/bin/bash
# 19-Dec-2025, KAB

if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]] || [[ "$1" == "-?" ]]; then
    echo
    echo "Usage: $0 [optional_repo_name]"
    echo "  e.g. $0 daqsystemtest"
    echo "  If no repo name is specified, integtests for all repos are listed."
    echo
    exit
fi

repo_list=()
if [ $# -ge 1 ]; then
    repo_list=("$1")
else
    echo
    echo "Finding the repositories that have integtests..."
    repo_list=("`list_all_repos_with_integtests.sh`")
fi

for repo in ${repo_list[@]}; do
    echo
    echo "*** ${repo} ***"
    echo
    share_envvar_name="${repo^^}_SHARE"
    if [[ -e ${!share_envvar_name}/integtest ]]; then
        ls -1 ${!share_envvar_name}/integtest/*_test.py | xargs -n 1 basename
    else
        echo "-> No integtest directory was found in \$${share_envvar_name}."
    fi
done

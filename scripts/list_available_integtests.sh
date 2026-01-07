#!/bin/bash
# 19-Dec-2025, KAB

if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]] || [[ "$1" == "-?" ]]; then
    echo
    echo "Usage: `basename $0` [optional_repo_name]"
    echo "  e.g. `basename $0` daqsystemtest"
    echo "  If no repo name is specified, integtests for all repos are listed."
    echo
    exit
fi

repo_list=()
if [ $# -ge 1 ]; then
    repo_list=("$@")
else
    repo_list=(`list_all_repos_with_integtests.sh`)
fi

for repo_name in "${repo_list[@]}"; do
    share_envvar_name="${repo_name^^}_SHARE"  # double caret converts env var to uppercase
    # ${!var} returns what var points to
    if [[ -e "${!share_envvar_name}/integtest" ]] || [[ -e "${DBT_AREA_ROOT}/sourcecode/${repo_name}/integtest" ]]; then
        integtest_list=(`ls -1 ${!share_envvar_name}/integtest/*_test.py ${DBT_AREA_ROOT}/sourcecode/${repo_name}/integtest/*_test.py 2>/dev/null | xargs -r -n 1 basename | sort -u`)
        echo "KAB ${#integtest_list[@]}"
        if [[ ${#integtest_list[@]} -gt 0 ]]; then
            for test_name in "${integtest_list[@]}"; do
                echo "${repo_name}/${test_name}"
            done
        else
            echo "-> No integtests were found for repository \"${repo_name}\"."
        fi
    else
        if [[ -e "${DBT_AREA_ROOT}/sourcecode/${repo_name}" ]]; then
            echo "-> No integtest directory was found in ${DBT_AREA_ROOT}/sourcecode/${repo_name}."
        fi
        echo "-> No integtest directory was found in ${share_envvar_name} (${!share_envvar_name})."
    fi
done

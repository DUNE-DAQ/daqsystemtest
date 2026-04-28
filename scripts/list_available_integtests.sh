#!/bin/bash
# 19-Dec-2025, KAB

if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]] || [[ "$1" == "-?" ]]; then
    echo
    echo "Usage: `basename $0` [optional list of repo names]"
    echo "  e.g. `basename $0` daqsystemtest"
    echo "  If no repo name is specified, integtests for all repos are listed."
    echo "  If a special repo name of \"local\" is specified, integtests for repos in the"
    echo "      local software area are listed."
    echo "  If a special repo name of \"all\" is specified, integtests for all repos are listed."
    echo
    exit
fi

echo "" >&2
repo_list=()
if [[ $# -ge 1 ]]; then
    for arg in "$@"
    do
        # create a string that we'll use to check if a repo is already in the list
        repo_list_string=$(IFS=\| ; echo "${repo_list[*]}")
        repo_list_string="|${repo_list_string}|"

        if [[ "$arg" == "local" ]] || [[ "$arg" == "all" ]]; then
            echo "Looking for integtests in _${arg}_ repos..." >&2
            echo "" >&2
            temp_list=(`list_repos_with_integtests.sh ${arg} 2>/dev/null`)
            for candidate_repo in "${temp_list[@]}"; do
                if [[ "`echo \"${repo_list_string}\" | grep \"|${candidate_repo}|\"`" == "" ]]; then
                    repo_list+=("${candidate_repo}")
                fi
            done
        else
            candidate_repo=$arg
            if [[ "`echo \"${repo_list_string}\" | grep \"|${candidate_repo}|\"`" == "" ]]; then
                repo_list+=("${candidate_repo}")
            fi
        fi
    done
else
    echo "Looking for integtests in _all_ repos..." >&2
    echo "" >&2
    repo_list=(`list_repos_with_integtests.sh 2>/dev/null`)
fi

echo "Looking for integtests in the _${repo_list[@]}_ repo(s)..." >&2
echo "" >&2

for repo_name in "${repo_list[@]}"; do
    share_envvar_name="${repo_name^^}_SHARE"  # double caret converts env var to uppercase
    # ${!var} returns what var points to
    if [[ -e "${!share_envvar_name}/integtest" ]] || [[ -e "${DBT_AREA_ROOT}/sourcecode/${repo_name}/integtest" ]]; then
        integtest_list=(`ls -1 ${!share_envvar_name}/integtest/*_test.py ${DBT_AREA_ROOT}/sourcecode/${repo_name}/integtest/*_test.py 2>/dev/null | xargs -r -n 1 basename | sort -u`)
        if [[ ${#integtest_list[@]} -gt 0 ]]; then
            for test_name in "${integtest_list[@]}"; do
                echo "${repo_name}/${test_name}"
            done
        else
            echo "-> No integtests were found for repository \"${repo_name}\"." >&2
        fi
    else
        if [[ -e "${DBT_AREA_ROOT}/sourcecode/${repo_name}" ]]; then
            echo "-> No integtest directory was found in ${DBT_AREA_ROOT}/sourcecode/${repo_name}." >&2
        fi
        if [[ "${!share_envvar_name}" == "" ]]; then
            echo "-> \"${repo_name}\" does not appear to be a valid repository name." >&2
        else
            echo "-> No integtest directory was found in ${share_envvar_name} (${!share_envvar_name})." >&2
        fi
    fi
done

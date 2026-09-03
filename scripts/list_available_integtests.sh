#!/bin/bash
# 19-Dec-2025, KAB

usage() {
    declare -r script_name=$(basename "$0")
    echo """
Usage:
"${script_name}" [option(s)] [optional list of repo names]

    Example: `basename $0` daqsystemtest
    If no repo name is specified, integtests for all repos are listed.
    If a special repo name of \"local\" is specified, integtests for repos in the
        local software area are listed.
    If a special repo name of \"all\" is specified, integtests for all repos are listed.

Options:
    -h, --help : prints out usage information
    -x, --exclude <pipe-delimited string with names of repos to be excluded ('egrep -i' match to match name)>
"""
}

GETOPT_TEMP=`getopt -o hx: --long help,exclude: -- "$@"`
if [ $? -ne 0 ]; then
    usage
    exit 1
fi
eval set -- "$GETOPT_TEMP"

excluded_repo_names=""
while true; do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        -x|--exclude)
            if [[ "${excluded_repo_names}" == "" ]]; then
                excluded_repo_names=$2
            else
                excluded_repo_names="${excluded_repo_names}|$2"
            fi
            shift 2
            ;;
        --)
            shift
            break
            ;;
    esac
done

# remove any spurious spaces from the excluded repo names (these will be used in an 'egrep' expression)
excluded_repo_names=`echo ${excluded_repo_names} | sed 's/\s//g'`

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

# filter out excluded repos
filtered_repo_list=()
for REPO_NAME in "${repo_list[@]}"; do
    excluded_repo=`echo ${REPO_NAME} | egrep -i ${excluded_repo_names:-nullnullnull}`
    if [[ "${excluded_repo}" == "" ]]; then
        filtered_repo_list+=("${REPO_NAME}")
    fi
done
repo_list=("${filtered_repo_list[@]}")

echo "Looking for integtests in the _${repo_list[@]}_ repo(s)..." >&2
echo "" >&2

for repo_name in "${repo_list[@]}"; do
    share_envvar_name="${repo_name^^}_SHARE"  # double caret converts env var to uppercase

    # Here, we list all integtests that exist either in the installed software area (C++ packages),
    # the local software area, or the Python virtual environment (the .venv subdir).
    # ${!var} returns what var points to
    integtest_list=(`ls -1 ${!share_envvar_name}/integtest/*_test.py ${DBT_AREA_ROOT}/sourcecode/${repo_name}/integtest/*_test.py ${DBT_AREA_ROOT}/.venv/lib/python*/site-packages/${repo_name}/integtest/*_test.py 2>/dev/null | xargs -r -n 1 basename | sort -u`)
    if [[ ${#integtest_list[@]} -gt 0 ]]; then
        for test_name in "${integtest_list[@]}"; do
            echo "${repo_name}/${test_name}"
        done
    else
        echo "-> No integtests were found for repository \"${repo_name}\"." >&2

        # The following logic is simply an attempt to provide a little more information
        # about *why* the integtest was not found.  It attemts to take into account
        # differences between C++ packages and Python packages.
        if [[ -e "${DBT_AREA_ROOT}/sourcecode/${repo_name}" ]]; then
            echo "-> No integtest directory was found in ${DBT_AREA_ROOT}/sourcecode/${repo_name}." >&2
        fi
        if [[ "${!share_envvar_name}" == "" ]] && [[ `pip list | grep "^${repo_name} "` == "" ]]; then
            echo "-> \"${repo_name}\" does not appear to be a valid repository name." >&2
        else
            if [[ "${!share_envvar_name}" != "" ]]; then
                echo "-> No integtest directory was found in ${share_envvar_name} (${!share_envvar_name})." >&2
            fi
            if [[ `pip list | grep "^${repo_name} "` != "" ]]; then
                echo "-> No integtest directory was found in ${DBT_AREA_ROOT}/venv for repo \"${repo_name}\"." >&2
            fi
        fi
    fi
done

#!/bin/bash
# 19-Dec-2025, KAB

# function to display usage hints
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

# function to check for a specific string in a list
string_in_list() {
    # get the search string from the first argument
    local search_string="$1"
    shift

    # read the remaining positional arguments into a local array
    local local_arr=( "$@" )

    # check for the presence of the search string
    for item in "${local_arr[@]}"; do
        if [[ "${item}" == "${search_string}" ]]; then
            return 0
        fi
    done
    return 1
}

# function to find integtests in a local sourcecode area
list_local_sourcecode_tests() {
    # check if a local software area exists; return empty list if not
    if [[ "$DBT_AREA_ROOT" == "" ]] || [[ "`echo $DBT_AREA_ROOT | grep '^/cvmfs'`" != "" ]]; then
        return 1
    fi
    local repo_name="$1"
    tmp_list=(`ls -1 ${DBT_AREA_ROOT}/sourcecode/${repo_name}/integtest/*_test.py 2>/dev/null | xargs -r -n 1 basename | sort -u`)
    if [[ ${#tmp_list[@]} -gt 0 ]]; then
        integtest_list=(${tmp_list[@]})
        return 0
    fi
    return 1
}

# function to find integtests in a local pythoncode area
list_local_pythoncode_tests() {
    # check if a local software area exists; return empty list if not
    if [[ "$DBT_AREA_ROOT" == "" ]] || [[ "`echo $DBT_AREA_ROOT | grep '^/cvmfs'`" != "" ]]; then
        return 1
    fi
    local repo_name="$1"
    tmp_list=(`ls -1 ${DBT_AREA_ROOT}/pythoncode/${repo_name}/src/${repo_name}/integtest/*_test.py 2>/dev/null | xargs -r -n 1 basename | sort -u`)
    if [[ ${#tmp_list[@]} -gt 0 ]]; then
        integtest_list=(${tmp_list[@]})
        return 0
    fi
    return 1
}

# function to find integtests in base release C++ repos
base_rel_dir=""
list_baserel_cpp_tests() {
    if [[ "${base_rel_dir}" == "" ]]; then
        dbt_info_output=`dbt-info release`
        base_rel_dir=`echo "${dbt_info_output}" | grep 'Release dir' | awk '{print $3}'`
    fi

    local repo_name="$1"
    tmp_list=(`ls -1d ${base_rel_dir}/sourcecode/${repo_name}/integtest/*_test.py 2>/dev/null | xargs -r -n 1 basename | sort -u`)
    if [[ ${#tmp_list[@]} -gt 0 ]]; then
        integtest_list=(${tmp_list[@]})
        return 0
    fi
    return 1
}

# function to find integtests in local or base release Python virtual environment
base_rel_dir=""
list_venv_py_tests() {
    if [[ "${base_rel_dir}" == "" ]]; then
        dbt_info_output=`dbt-info release`
        base_rel_dir=`echo "${dbt_info_output}" | grep 'Release dir' | awk '{print $3}'`
    fi

    local repo_name="$1"
    if [[ -e ${DBT_AREA_ROOT}/.venv ]]; then
        tmp_list=(`ls -1d ${DBT_AREA_ROOT}/.venv/lib/python*/site-packages/${repo_name}/integtest/*_test.py 2>/dev/null | xargs -r -n 1 basename | sort -u`)
    else
        tmp_list=(`ls -1d ${base_rel_dir}/.venv/lib/python*/site-packages/${repo_name}/integtest/*_test.py 2>/dev/null | xargs -r -n 1 basename | sort -u`)
    fi
    if [[ ${#tmp_list[@]} -gt 0 ]]; then
        integtest_list=(${tmp_list[@]})
        return 0
    fi
    return 1
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
        if [[ "$arg" == "local" ]] || [[ "$arg" == "all" ]]; then
            echo "Looking for integtests in _${arg}_ repos..." >&2
            echo "" >&2
            temp_list=(`list_repos_with_integtests.sh ${arg} 2>/dev/null`)
            for candidate_repo in "${temp_list[@]}"; do
                if ! string_in_list "$candidate_repo" "${repo_list[@]}"; then
                    repo_list+=("${candidate_repo}")
                fi
           done
        else
            candidate_repo=$arg
            if ! string_in_list "$candidate_repo" "${repo_list[@]}"; then
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
    # We look for tests in several places and stop looking as soon as we find some.
    # The functions that are called in this "if" statement modify the integtest_list
    # when tests are found, and return "true" when they do, so the contents of the
    # "if" block can simply print out what is in the integtest_list.
    integtest_list=()
    if list_local_sourcecode_tests ${repo_name} || \
            list_local_pythoncode_tests ${repo_name} || \
            list_baserel_cpp_tests ${repo_name} || \
            list_venv_py_tests ${repo_name}; then
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
        elif [[ -e "${DBT_AREA_ROOT}/pythoncode/${repo_name}" ]]; then
            echo "-> No integtest directory was found in ${DBT_AREA_ROOT}/pythoncode/${repo_name}/src/${repo_name}." >&2
        elif [[ -e "${base_rel_dir}/sourcecode/${repo_name}" ]]; then
            echo "-> No integtest directory was found in ${base_rel_dir}/sourcecode/${repo_name}." >&2
        fi
    fi
done

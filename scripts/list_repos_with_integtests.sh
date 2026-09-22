#!/bin/bash
# 19-Dec-2025, KAB

if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]] || [[ "$1" == "-?" ]]; then
    echo
    echo "Usage: `basename $0` [optional \"local\" keyword]"
    echo
    echo "  Lists the software repositories that have integration tests (integtests) in them."
    echo
    echo "  For C++ packages, the local sourcecode dir (if any) and the base release "
    echo "  are searched, unless \"local\" is passed as an argument. In that case, only the"
    echo "  local sourcecode directory is searched."
    echo
    echo "  For Python packages, the \$DBT_AREA_ROOT/.venv area is searched, independent of"
    echo "  whether that area is part of a local software area or a base release. If the"
    echo "  \"local\" flag is specified, an attempt is made to limit the results to packages"
    echo "  that have been cloned into the local 'pythoncode' directory."
    echo
    exit
fi

# initialization
all_integtest_paths=()

# provide feedback to the user
echo "" >&2
if [[ $# -eq 0 ]] || [[ "$1" != "local" ]]; then
    echo "Looking for _all_ repositories with integtests in them..." >&2
else
    echo "Looking for _local_ repositories with integtests in them..." >&2
fi
echo "" >&2

# look in a local software area first
if [[ "$DBT_AREA_ROOT" != "" ]] && [[ "`echo $DBT_AREA_ROOT | grep '^/cvmfs'`" == "" ]]; then

    # add in the paths of the C++ integtests
    sourcecode_dir_repo_paths=(`ls -1 ${DBT_AREA_ROOT}/sourcecode/*/integtest/*_test.py 2>/dev/null`)
    all_integtest_paths+=("${sourcecode_dir_repo_paths[@]}")

    # add in the paths of the Python integtests
    pythoncode_dir_repo_paths=(`ls -1 ${DBT_AREA_ROOT}/pythoncode/*/src/*/integtest/*_test.py 2>/dev/null`)
    all_integtest_paths+=("${pythoncode_dir_repo_paths[@]}")
fi

# include repos in the base release, unless the user has specified "local"
if [[ $# -eq 0 ]] || [[ "$1" != "local" ]]; then
    dbt_info_output=`dbt-info release`
    base_rel_dir=`echo "${dbt_info_output}" | grep 'Release dir' | awk '{print $3}'`

    # add in the paths of the C++ integtests in the base release
    base_rel_cpp_repos=(`ls -1d ${base_rel_dir}/sourcecode/*/integtest/*_test.py 2>/dev/null`)
    all_integtest_paths+=("${base_rel_cpp_repos[@]}")

    # add in the paths of the Python integtests from the current virtual environment
    if [[ -e ${DBT_AREA_ROOT}/.venv ]]; then
        venv_py_repos=(`ls -1d ${DBT_AREA_ROOT}/.venv/lib/python*/site-packages/*/integtest/*_test.py 2>/dev/null`)
    else
        venv_py_repos=(`ls -1d ${base_rel_dir}/.venv/lib/python*/site-packages/*/integtest/*_test.py 2>/dev/null`)
    fi
    all_integtest_paths+=("${venv_py_repos[@]}")
fi

repos_with_integtests=(`echo "${all_integtest_paths[@]}" | sed 's,/share,,g' | xargs -r -n 1 dirname | xargs -r -n 1 dirname | xargs -r -n 1 basename | cut -d'-' -f1 | sort -u`)

for repo in "${repos_with_integtests[@]}"; do
    echo "$repo"
done

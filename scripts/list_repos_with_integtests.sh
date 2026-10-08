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

# check if a software environment has been set up
if [[ "$DBT_AREA_ROOT" == "" ]]; then
    echo
    echo "Please set up a valid DUNE-DAQ software area before running this script."
    exit
fi

# initialization
all_integtest_paths=()
source $DAQSYSTEMTEST_SHARE/../bin/dst_set_useful_env_vars.sh

# let the user know what is happening
echo "" >&2
if [[ $# -eq 0 ]] || [[ "$1" != "local" ]]; then
    echo "Looking for _all_ repositories with integtests in them..." >&2
else
    echo "Looking for _local_ repositories with integtests in them..." >&2
fi
echo "" >&2

# look in a local software area first
# -> C++ repositories
if [[ "${DST_LOCAL_CPP_SOURCE_DIR}" != "" ]]; then
    sourcecode_dir_repo_paths=(`ls -1 ${DST_LOCAL_CPP_SOURCE_DIR}/*/integtest/*_test.py 2>/dev/null`)
    all_integtest_paths+=("${sourcecode_dir_repo_paths[@]}")
fi
# -> Python repositories
if [[ "${DST_LOCAL_PYTHON_SOURCE_DIR}" != "" ]]; then
    pythoncode_dir_repo_paths=(`ls -1 ${DST_LOCAL_PYTHON_SOURCE_DIR}/*/src/*/integtest/*_test.py 2>/dev/null`)
    all_integtest_paths+=("${pythoncode_dir_repo_paths[@]}")
fi

# include additional areas, unless the user has specified "local"
if [[ $# -eq 0 ]] || [[ "$1" != "local" ]]; then

    # include a local Python virtual environment, if it exists
    if [[ "${DST_LOCAL_PYTHON_VENV_DIR}" != "" ]]; then
        venv_py_repos=(`ls -1d ${DST_LOCAL_PYTHON_VENV_DIR}/*/integtest/*_test.py 2>/dev/null`)
        all_integtest_paths+=("${venv_py_repos[@]}")
    fi
    
    # add in the paths of the C++ integtests in the base release
    if [[ "${DST_BASEREL_CPP_SOURCE_DIR}" != "" ]]; then
        base_rel_cpp_repos=(`ls -1d ${DST_BASEREL_CPP_SOURCE_DIR}/*/integtest/*_test.py 2>/dev/null`)
        all_integtest_paths+=("${base_rel_cpp_repos[@]}")
    fi

    # add in the paths of the Python integtests in the base release virtual environment
    if [[ "${DST_BASEREL_PYTHON_VENV_DIR}" != "" ]]; then
        venv_py_repos=(`ls -1d ${DST_BASEREL_PYTHON_VENV_DIR}/*/integtest/*_test.py 2>/dev/null`)
        all_integtest_paths+=("${venv_py_repos[@]}")
    fi
fi

repos_with_integtests=(`echo "${all_integtest_paths[@]}" | sed 's,/share,,g' | xargs -r -n 1 dirname | xargs -r -n 1 dirname | xargs -r -n 1 basename | cut -d'-' -f1 | sort -u`)

for repo in "${repos_with_integtests[@]}"; do
    echo "$repo"
done

#!/bin/bash
# 19-Dec-2025, KAB

if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]] || [[ "$1" == "-?" ]]; then
    echo
    echo "Usage: `basename $0` [optional \"local\" keyword]"
    echo "  Lists the software repositories that have integration tests (integtests) in them."
    echo "  For C++ packages, the base release, local install dir, and local sourcecode dir"
    echo "  are searched, unless \"local\" is passed as an argument. In that case, only the"
    echo "  local install and sourcecode directories are searched."
    echo "  For Python packages, the \$DBT_AREA_ROOT/.venv area is searched, independent of"
    echo "  whether that area is part of a local software area or a base release. If the"
    echo "  \"local\" flag is specified, an attempt is made to limit the results to packages"
    echo "  that have been cloned into the local 'pythoncode' directory."
    echo
    exit
fi

# initialization
all_repo_paths=()

# skip repos in the base release, if the user has specified "local"
echo "" >&2
if [[ $# -eq 0 ]] || [[ "$1" != "local" ]]; then
    echo "Looking for _all_ repositories with integtests in them..." >&2
    echo "" >&2

    # determine the base release directory
    release_dir=`dbt-info release | grep 'Release dir:' | cut -d' ' -f3`
    base_release_name=`dbt-info release | grep 'Base release name:' | cut -d' ' -f4`
    base_release_dir="${release_dir}/../${base_release_name}"

    # look up the paths of all of the C++ repositories in the core and detector-specific categories with integtests
    det_rel_repo_paths=(`ls -1d ${release_dir}/spack-installation/opt/spack/*linux*/gcc-*/*/*/integtest/*_test.py 2>/dev/null`)
    base_rel_repo_paths=(`ls -1d ${base_release_dir}/spack-installation/opt/spack/*linux*/gcc-*/*/*/integtest/*_test.py 2>/dev/null`)
    all_repo_paths=("${det_rel_repo_paths[@]}" "${base_rel_repo_paths[@]}")

    # add in the paths of the Python repositories with integtests
    if [[ "${DBT_AREA_ROOT}" != "" ]]; then
        venv_dir_repo_paths=(`ls -1 ${DBT_AREA_ROOT}/.venv/lib/python*/site-packages/*/integtest/*_test.py`)
        all_repo_paths=("${all_repo_paths[@]}" "${venv_dir_repo_paths[@]}")
    fi
else
    echo "Looking for _local_ repositories with integtests in them..." >&2
    echo "" >&2
fi

# add in the paths of the C++ repositories in the local install and sourcecode dirs
if [[ "$DBT_AREA_ROOT" != "" ]]; then
    install_dir_repo_paths=(`ls -1 ${DBT_AREA_ROOT}/install/*/share/integtest/*_test.py 2>/dev/null`)
    sourcecode_dir_repo_paths=(`ls -1 ${DBT_AREA_ROOT}/sourcecode/*/integtest/*_test.py 2>/dev/null`)
    all_repo_paths=("${all_repo_paths[@]}" "${install_dir_repo_paths[@]}" "${sourcecode_dir_repo_paths[@]}")
fi

# add in the paths of the Python repositories that have integtests and are cloned locally
if [[ "`echo $DBT_AREA_ROOT | grep '^/cvmfs'`" == "" ]]; then
    venv_dir_repo_paths=(`ls -1 ${DBT_AREA_ROOT}/.venv/lib/python*/site-packages/*/integtest/*_test.py 2>/dev/null`)
    for path in "${venv_dir_repo_paths[@]}"; do
        repo_name=`echo ${path} | cut -d'/' -f 11`
        if [[ -e $DBT_AREA_ROOT/pythoncode/${repo_name} ]]; then
            all_repo_paths=("${all_repo_paths[@]}" "${path}")
        fi
    done
fi

repos_with_integtests=(`echo "${all_repo_paths[@]}" | sed 's,/share,,g' | xargs -r -n 1 dirname | xargs -r -n 1 dirname | xargs -r -n 1 basename | cut -d'-' -f1 | sort -u`)

for repo in "${repos_with_integtests[@]}"; do
    echo "$repo"
done

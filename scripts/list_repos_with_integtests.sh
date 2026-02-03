#!/bin/bash
# 19-Dec-2025, KAB

if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]] || [[ "$1" == "-?" ]]; then
    echo
    echo "Usage: `basename $0` [optional \"local\" keyword]"
    echo "  Lists the software repositories that have integration tests (integtests) in them."
    echo "  Searches the base releases, local install dir, and local sourcecode dir,"
    echo "  unless \"local\" is passed as an argument. In that case, only the local"
    echo "  install and sourcecode directories are searched."
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

    # look up the paths of all of the repositories in the core and detector-specific categories
    det_rel_repo_paths=(`ls -1d ${release_dir}/spack-installation/opt/spack/*linux*/gcc-*/*/*/integtest/*_test.py`)
    base_rel_repo_paths=(`ls -1d ${base_release_dir}/spack-installation/opt/spack/*linux*/gcc-*/*/*/integtest/*_test.py`)
    all_repo_paths=("${det_rel_repo_paths[@]}" "${base_rel_repo_paths[@]}")
else
    echo "Looking for _local_ repositories with integtests in them..." >&2
    echo "" >&2
fi

# add in the paths of the repositories in the local install and sourcecode dirs
if [[ "$DBT_AREA_ROOT" != "" ]]; then
    install_dir_repo_paths=(`ls -1 ${DBT_AREA_ROOT}/install/*/share/integtest/*_test.py`)
    sourcecode_dir_repo_paths=(`ls -1 ${DBT_AREA_ROOT}/sourcecode/*/integtest/*_test.py`)
    all_repo_paths=("${all_repo_paths[@]}" "${install_dir_repo_paths[@]}" "${sourcecode_dir_repo_paths[@]}")
fi

repos_with_integtests=(`echo "${all_repo_paths[@]}" | sed 's,/share,,g' | xargs -r -n 1 dirname | xargs -r -n 1 dirname | xargs -r -n 1 basename | cut -d'-' -f1 | sort -u`)

for repo in "${repos_with_integtests[@]}"; do
    echo "$repo"
done

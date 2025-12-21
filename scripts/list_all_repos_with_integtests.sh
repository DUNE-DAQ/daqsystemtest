#!/bin/bash
# 19-Dec-2025, KAB

release_dir=`dbt-info release | grep 'Release dir:' | cut -d' ' -f3`
base_release_name=`dbt-info release | grep 'Base release name:' | cut -d' ' -f4`
base_release_dir="${release_dir}/../${base_release_name}"

groupA="(`ls -1d ${release_dir}/spack-installation/opt/spack/*almalinux9*/gcc-*/*/*/integtest`)"
groupB="(`ls -1d ${base_release_dir}/spack-installation/opt/spack/*almalinux9*/gcc-*/*/*/integtest`)"
groupC=("${groupA}"+" "+"${groupB}")

the_list=("`echo ${groupC} | xargs -r -n 1 dirname | xargs -r -n 1 dirname | xargs -r -n 1 basename | cut -d'-' -f1 | sort`")

for pkg in ${the_list[@]}; do
    echo $pkg
done

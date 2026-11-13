# This script needs to be sourced.
#
# Its purpose is to set values for various environmental variables that are
# useful for looking up integration tests in our C++ and Python repositories.

# check if a software environment has been set up
if [[ "$DBT_AREA_ROOT" == "" ]]; then
    echo
    echo "Please set up a valid DUNE-DAQ software area before running this script."
    return
fi

# check if this script has already been run, and exit early if yes
if [[ "${DST_DAR_COPY}" != "" ]] && \
   [[ "${DST_DAR_COPY}" == "${DBT_AREA_ROOT}" ]]; then
    return
fi
export DST_DAR_COPY="${DBT_AREA_ROOT}"

# default all of the env vars that we might set to empty strings
export DST_LOCAL_CPP_SOURCE_DIR=""
export DST_LOCAL_PYTHON_SOURCE_DIR=""
export DST_LOCAL_PYTHON_VENV_DIR=""
export DST_LOCAL_SPACK_INSTALL_DIR=""
export DST_BASEREL_CPP_SOURCE_DIR=""
export DST_BASEREL_PYTHON_VENV_DIR=""
export DST_CORE_BASEREL_SPACK_DIR=""
export DST_DETSPEC_BASEREL_SPACK_DIR=""

if [[ "${DBT_AREA_ROOT}" != "" ]] && [[ "`echo ${DBT_AREA_ROOT} | grep '^/cvmfs'`" == "" ]] && \
   [[ -w "${DBT_AREA_ROOT}" ]] && [[ -w "${DBT_AREA_ROOT}/sourcecode" ]]; then
    export DST_LOCAL_CPP_SOURCE_DIR="${DBT_AREA_ROOT}/sourcecode"
fi

if [[ "${DBT_AREA_ROOT}" != "" ]] && [[ "`echo ${DBT_AREA_ROOT} | grep '^/cvmfs'`" == "" ]] && \
   [[ -w "${DBT_AREA_ROOT}" ]] && [[ -w "${DBT_AREA_ROOT}/pythoncode" ]]; then
    export DST_LOCAL_PYTHON_SOURCE_DIR="${DBT_AREA_ROOT}/pythoncode"
fi

if [[ "${DBT_AREA_ROOT}" != "" ]] && [[ "`echo ${DBT_AREA_ROOT} | grep '^/cvmfs'`" == "" ]] && \
   [[ -w "${DBT_AREA_ROOT}" ]] && [[ -w "${DBT_AREA_ROOT}/.venv" ]]; then
    export DST_LOCAL_PYTHON_VENV_DIR="`ls -1d ${DBT_AREA_ROOT}/.venv/lib/python*/site-packages 2>/dev/null | head -1`"
fi

if [[ "${DBT_AREA_ROOT}" != "" ]] && [[ "`echo ${DBT_AREA_ROOT} | grep '^/cvmfs'`" == "" ]] && \
   [[ -w "${DBT_AREA_ROOT}" ]] && [[ -w "${DBT_AREA_ROOT}/install" ]]; then
    export DST_LOCAL_SPACK_INSTALL_DIR="${DBT_AREA_ROOT}/install"
fi

dbt_info_output=`dbt-info release`
detector_specific_release_dir=`echo "${dbt_info_output}" | grep 'Release dir' | awk '{print $3}'`
detector_specific_release_name=`echo "${dbt_info_output}" | grep 'Release name:' | awk '{print $3}'`
core_release_name=`echo "${dbt_info_output}" | grep 'Base release name:' | awk '{print $4}'`
core_release_dir=`echo "${detector_specific_release_dir}" | sed "s/${detector_specific_release_name}/${core_release_name}/g"`

export DST_BASEREL_CPP_SOURCE_DIR="${detector_specific_release_dir}/sourcecode"

export DST_BASEREL_PYTHON_VENV_DIR="`ls -1d ${detector_specific_release_dir}/.venv/lib/python*/site-packages 2>/dev/null | head -1`"

export DST_CORE_BASEREL_SPACK_DIR="`ls -1d ${core_release_dir}/spack-installation/opt/spack/linux-*/gcc-* 2>/dev/null | head -1`"

export DST_DETSPEC_BASEREL_SPACK_DIR="`ls -1d ${detector_specific_release_dir}/spack-installation/opt/spack/linux-*/gcc-* 2>/dev/null | head -1`"

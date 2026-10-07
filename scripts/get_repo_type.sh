#!/bin/bash

if [[ $# -eq 0 ]] || [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]] || [[ "$1" == "-?" ]]; then
    echo
    echo "Usage: `basename $0` <repo name>"
    echo
    echo "  Determines the type of the specified repo, \"CPP\" or \"Python\"."
    echo "  Prints out \"Unknown\" if the type can't be determined."
    echo
    exit
fi
repo_name=$1

# check if a software environment has been set up
if [[ "$DBT_AREA_ROOT" == "" ]]; then
    echo
    echo "Please set up a valid DUNE-DAQ software area before running this script."
    exit
fi

source $DAQSYSTEMTEST_SHARE/../bin/dst_set_useful_env_vars.sh

if [[ "${DST_LOCAL_SPACK_INSTALL_DIR}" != "" ]] && \
       [[ -e "${DST_LOCAL_SPACK_INSTALL_DIR}/${repo_name}" ]]; then
    echo "CPP"
elif [[ "${DST_CORE_BASEREL_SPACK_DIR}" != "" ]] && \
     [[ "`ls -1d ${DST_CORE_BASEREL_SPACK_DIR}/${repo_name}* 2>/dev/null | head -1`" != "" ]]; then
    echo "CPP"
elif [[ "${DST_DETSPEC_BASEREL_SPACK_DIR}" != "" ]] && \
     [[ "`ls -1d ${DST_DETSPEC_BASEREL_SPACK_DIR}/${repo_name}* 2>/dev/null | head -1`" != "" ]]; then
    echo "CPP"
elif [[ "${DST_LOCAL_PYTHON_VENV_DIR}" != "" ]] && \
     [[ -e ${DST_LOCAL_PYTHON_VENV_DIR}/${repo_name} ]]; then
    echo "Python"
elif [[ "${DST_PYTHON_PYTHON_VENV_DIR}" != "" ]] && \
     [[ -e ${DST_PYTHON_PYTHON_VENV_DIR}/${repo_name} ]]; then
    echo "Python"
else
    echo "Unknown"
fi

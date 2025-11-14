#!/bin/bash

BOOTUP=color
RES_COL=0
MOVE_TO_COL="echo -en \\033[${RES_COL}G"
SETCOLOR_SUCCESS="echo -en \\033[1;32m"
SETCOLOR_FAILURE="echo -en \\033[1;31m"
SETCOLOR_NORMAL="echo -en \\033[0;39m"
if [ "$CONSOLETYPE" = "serial" ]; then
    BOOTUP=serial
    MOVE_TO_COL=
    SETCOLOR_SUCCESS=
    SETCOLOR_FAILURE=
    SETCOLOR_NORMAL=
fi

function echo_success() {
    [ "$BOOTUP" = "color" ] && $MOVE_TO_COL
    echo -n "["
    [ "$BOOTUP" = "color" ] && $SETCOLOR_SUCCESS
    echo -n $"  OK  "
    [ "$BOOTUP" = "color" ] && $SETCOLOR_NORMAL
    echo -n "]"
    echo -ne "\r"
    return 0
}

function echo_failure() {
  [ "$BOOTUP" = "color" ] && $MOVE_TO_COL
  echo -n "["
  [ "$BOOTUP" = "color" ] && $SETCOLOR_FAILURE
  echo -n $"FAILED"
  [ "$BOOTUP" = "color" ] && $SETCOLOR_NORMAL
  echo -n "]"
  echo -ne "\r"
  return 1
}

function check_config() {
    config_file=$1
    
    get_apps "$config_file" | while IFS= read -r LINE; do

        session_name=$(echo "$LINE" | grep -oE 'in session [^:]*:' | awk '{print $3}' | tr -d ':')
        app_list_string=$(echo "$LINE" | awk -F "[" '{print $2}' | sed "s/'//g; s/ //g; s/\]//g")

        IFS=',' read -ra app_list <<< "$app_list_string"

        # Print header for the current session
        echo -e "\n--- Processing SESSION: $session_name (${#app_list[@]} apps) ---"

        for app in "${app_list[@]}"; do
            echo -n "         Running generate_modules_test for app '$app' in session '$session_name'"
            if generate_modules_test "$session_name" "$app" "$config_file" &>/dev/null; then
                echo_success
            else
                echo_failure
            fi
            echo
        done
    done
}

echo "Checking config/daqsystemtest/example-configs.data.xml Sessions and Applications"
check_config "config/daqsystemtest/example-configs.data.xml"
echo 

echo "Checking config/daqsystemtest/example-hsi-configs.data.xml Sessions and Applications"
check_config "config/daqsystemtest/example-hsi-configs.data.xml"
echo

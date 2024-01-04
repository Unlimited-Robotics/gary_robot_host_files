RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

ENV_FILE_PATH=/opt/raya_os/env

if [ -f "${ENV_FILE_PATH}" ]; then
    source ${ENV_FILE_PATH}
    if [[ -z "${ROBOT_ID}" ]]; then
        echo -e "${YELLOW}WARNING:${NC} Variable ROBOTS_ID does not exist in file ${ENV_FILE_PATH}"
    else
        PS1='\n${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@${ROBOT_ID}\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\n\$ '
    fi
else
    echo -e "${YELLOW}WARNING:${NC} Environment file ${ENV_FILE_PATH} does not exist"
fi

alias collect_logs='/home/gary/ur_dev/env_robot/collect_logs.py'

display_output=$(ps e -u $USER | grep -Po "DISPLAY=:[\.0-9A-Za-z:]* " | sort -u)
if ! [ -z "$display_output" ]; then
    first_display=$(echo "$display_output" | head -n 1)
    export DISPLAY=$(echo "$first_display" | grep -Po "(?<=DISPLAY=)[\.0-9A-Za-z:]*")
fi

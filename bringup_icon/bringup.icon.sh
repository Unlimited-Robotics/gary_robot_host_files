#!/bin/bash

cleanup() {
    docker stop raya_os
    exit
}


# Check if the container is running
if docker ps --format '{{.Names}}' | grep -q "^raya_os$"; 
then
    echo "Container 'raya_os' is already running."
    echo "Press any key to exit..."
    read -n 1 -s
else
    # Trap the exit signal and call the cleanup function
    trap cleanup EXIT
    /home/gary/ur_dev/env_robot/run.bringup.sh "$@"
fi

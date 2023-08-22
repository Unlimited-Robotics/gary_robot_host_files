#!/bin/bash

export DISPLAY=$(cat /tmp/display_result.txt)
pkill vino
/usr/lib/vino/vino-server --display=$DISPLAY